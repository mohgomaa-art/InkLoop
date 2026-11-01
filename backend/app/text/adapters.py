"""
InkLoop Text Generation Engine - Generation Adapters (Milestone M5 / Workstream E4).
Provides provider-neutral generation interfaces, deterministic offline simulation,
and fail-closed live provider stubs.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

from app.text.enums import (
    ScriptBlockKind,
    DialogueDelivery,
    CaptionKind,
    SFXCategory,
    TextLanguage,
    TextDirection,
    SourceMode,
    DiagnosticSeverity,
    DiagnosticCode,
)
from app.text.models import (
    ScriptBlock,
    SpeakerRef,
    TextProvenance,
    TextValidationDiagnostic,
    TextGenerationRequest,
    TextGenerationResult,
    compute_sha256,
    utc_now_iso,
)
from app.contracts.engine import EngineStatus, UsageMetrics
from app.config import InkLoopConfig


class BaseTextGenerationAdapter(ABC):
    """Abstract interface for comic script text generation engines."""
    is_simulated: bool = False

    @abstractmethod
    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        """Execute text generation synchronously."""
        pass


class SimulatedTextGenerationAdapter(BaseTextGenerationAdapter):
    """
    Deterministic offline simulated text generation adapter.
    Used for automated unit and integration tests with zero external network or model spend ($0.00).
    Produces structured, typed ScriptBlock instances matching scene action and requested block kinds.
    """
    is_simulated: bool = True

    def __init__(self, default_success: bool = True):
        self.default_success = default_success
        self._scripted_blocks: Dict[str, List[ScriptBlock]] = {}
        self._scripted_failures: Dict[str, Dict[str, Any]] = {}
        self.request_history: List[TextGenerationRequest] = []

    def script_panel_blocks(self, panel_id: str, blocks: List[ScriptBlock]) -> None:
        """Configures predetermined script blocks to return for a specific panel."""
        self._scripted_blocks[panel_id] = blocks

    def script_panel_failure(self, panel_id: str, status: EngineStatus, error_message: str) -> None:
        """Configures a predetermined failure outcome for a specific panel."""
        self._scripted_failures[panel_id] = {
            "status": status,
            "error_message": error_message,
        }

    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        """Generates structured script blocks offline."""
        self.request_history.append(request)

        # Check for scripted failure
        if request.panel_id in self._scripted_failures:
            fail_spec = self._scripted_failures[request.panel_id]
            return TextGenerationResult(
                success=False,
                status=fail_spec["status"],
                blocks=[],
                diagnostics=[
                    TextValidationDiagnostic(
                        code=DiagnosticCode.UNVERIFIED_MODEL_OUTPUT,
                        severity=DiagnosticSeverity.ERROR,
                        message=fail_spec["error_message"],
                    )
                ],
                is_exact_user_text=bool(request.exact_user_text),
                adapter_used="offline_simulated",
                is_simulated=True,
                error_message=fail_spec["error_message"],
            )

        # Check for scripted blocks override
        if request.panel_id in self._scripted_blocks:
            blocks = self._scripted_blocks[request.panel_id]
            return TextGenerationResult(
                success=True,
                status=EngineStatus.SUCCESS,
                blocks=blocks,
                diagnostics=[],
                is_exact_user_text=any(b.is_exact_user_text for b in blocks),
                adapter_used="offline_simulated",
                is_simulated=True,
                cost_usd=0.0,
                usage=UsageMetrics(input_tokens=100, output_tokens=50, total_tokens=150),
            )

        # 1. Exact user text ingestion mode
        if request.exact_user_text:
            clean_text = request.exact_user_text
            content_h = compute_sha256(clean_text)
            speaker_id = request.character_ids[0] if request.character_ids else "narrator"
            is_dialogue = bool(request.character_ids)

            block = ScriptBlock(
                block_id=f"blk_{request.panel_id}_user01",
                project_id=request.project_id,
                story_id=request.story_id,
                scene_id=request.scene_id,
                panel_id=request.panel_id,
                block_kind=ScriptBlockKind.DIALOGUE if is_dialogue else ScriptBlockKind.NARRATION,
                reading_order_index=0,
                text_content=clean_text,
                language=request.target_language,
                direction=request.target_direction,
                is_exact_user_text=True,
                provenance=TextProvenance(
                    provenance_id=f"prov_user_{request.panel_id}",
                    source_mode=SourceMode.USER_EXACT,
                    source_passage_id=f"passage_{request.scene_id}",
                    source_text_hash=content_h,
                    generated_text_hash=content_h,
                ),
                speaker=SpeakerRef(speaker_id=speaker_id) if is_dialogue else None,
                delivery=DialogueDelivery.NORMAL if is_dialogue else None,
            )
            return TextGenerationResult(
                success=True,
                status=EngineStatus.SUCCESS,
                blocks=[block],
                diagnostics=[],
                is_exact_user_text=True,
                adapter_used="offline_simulated",
                is_simulated=True,
                cost_usd=0.0,
                usage=UsageMetrics(input_tokens=50, output_tokens=len(clean_text.split()), total_tokens=50),
            )

        # 2. Synthetic deterministic generation from scene action
        generated_blocks: List[ScriptBlock] = []
        reading_idx = 0

        for kind in request.block_kinds_requested:
            b_id = f"blk_{request.panel_id}_{reading_idx + 1:02d}"

            if kind == ScriptBlockKind.CAPTION:
                text = f"في ذلك الحين... ({request.scene_action})" if request.target_language == TextLanguage.AR else f"Meanwhile... ({request.scene_action})"
                b = ScriptBlock(
                    block_id=b_id,
                    project_id=request.project_id,
                    story_id=request.story_id,
                    scene_id=request.scene_id,
                    panel_id=request.panel_id,
                    block_kind=ScriptBlockKind.CAPTION,
                    reading_order_index=reading_idx,
                    text_content=text,
                    language=request.target_language,
                    direction=request.target_direction,
                    provenance=TextProvenance(
                        provenance_id=f"prov_{b_id}",
                        source_mode=SourceMode.MODEL_GENERATED,
                        model_name="simulated-text-v1",
                        generated_text_hash=compute_sha256(text),
                    ),
                    caption_kind=CaptionKind.SCENE_SETTING,
                )
                generated_blocks.append(b)
                reading_idx += 1

            elif kind == ScriptBlockKind.DIALOGUE:
                spk = request.character_ids[0] if request.character_ids else "nour"
                text = "يجب أن نتحرك الآن قبل فوات الأوان!" if request.target_language == TextLanguage.AR else "We must move now before it's too late!"
                b = ScriptBlock(
                    block_id=b_id,
                    project_id=request.project_id,
                    story_id=request.story_id,
                    scene_id=request.scene_id,
                    panel_id=request.panel_id,
                    block_kind=ScriptBlockKind.DIALOGUE,
                    reading_order_index=reading_idx,
                    text_content=text,
                    language=request.target_language,
                    direction=request.target_direction,
                    provenance=TextProvenance(
                        provenance_id=f"prov_{b_id}",
                        source_mode=SourceMode.MODEL_GENERATED,
                        model_name="simulated-text-v1",
                        generated_text_hash=compute_sha256(text),
                    ),
                    speaker=SpeakerRef(speaker_id=spk),
                    delivery=DialogueDelivery.NORMAL,
                )
                generated_blocks.append(b)
                reading_idx += 1

            elif kind == ScriptBlockKind.SFX:
                text = "طاخ!" if request.target_language == TextLanguage.AR else "CRASH!"
                b = ScriptBlock(
                    block_id=b_id,
                    project_id=request.project_id,
                    story_id=request.story_id,
                    scene_id=request.scene_id,
                    panel_id=request.panel_id,
                    block_kind=ScriptBlockKind.SFX,
                    reading_order_index=reading_idx,
                    text_content=text,
                    language=request.target_language,
                    direction=request.target_direction,
                    provenance=TextProvenance(
                        provenance_id=f"prov_{b_id}",
                        source_mode=SourceMode.MODEL_GENERATED,
                        model_name="simulated-text-v1",
                        generated_text_hash=compute_sha256(text),
                    ),
                    sfx_category=SFXCategory.IMPACT,
                )
                generated_blocks.append(b)
                reading_idx += 1

        return TextGenerationResult(
            success=True,
            status=EngineStatus.SUCCESS,
            blocks=generated_blocks,
            diagnostics=[],
            is_exact_user_text=False,
            adapter_used="offline_simulated",
            is_simulated=True,
            cost_usd=0.0,
            usage=UsageMetrics(input_tokens=150, output_tokens=75, total_tokens=225),
        )


class MetaTextGenerationAdapter(BaseTextGenerationAdapter):
    """
    Live text generation adapter stub.
    Fails closed when API credentials are not configured, returning EngineStatus.BLOCKED or NOT_IMPLEMENTED.
    """
    is_simulated: bool = False

    def __init__(self, config: Optional[InkLoopConfig] = None):
        self.config = config or InkLoopConfig.load()

    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        """
        Attempts to call live text generation model.
        Reports BLOCKED / NOT_IMPLEMENTED honestly when provider credentials are not present.
        """
        # Strict fail-closed: do not claim live capability without credentials
        if not self.config.has_credentials:
            return TextGenerationResult(
                success=False,
                status=EngineStatus.BLOCKED,
                blocks=[],
                diagnostics=[
                    TextValidationDiagnostic(
                        code=DiagnosticCode.UNVERIFIED_MODEL_OUTPUT,
                        severity=DiagnosticSeverity.ERROR,
                        message="Live text generation model credentials are not configured.",
                    )
                ],
                is_exact_user_text=bool(request.exact_user_text),
                adapter_used="meta_llm",
                is_simulated=False,
                error_message="Live text generation model API credentials are not configured.",
            )

        # Production integration point for Meta LLM text endpoint
        return TextGenerationResult(
            success=False,
            status=EngineStatus.NOT_IMPLEMENTED,
            blocks=[],
            diagnostics=[],
            adapter_used="meta_llm",
            is_simulated=False,
            error_message="Live Meta LLM text generation adapter contract is pending production rollout.",
        )
