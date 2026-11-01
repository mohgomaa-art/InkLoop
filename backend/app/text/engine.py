"""
InkLoop Text Generation Engine - Specialist Engine Service (Milestone M5 / Workstream E4).
Coordinates structured comic text generation, exact-user-text ingestion,
Story Bible canon validation, narrative continuity state verification, and
adaptation to shared engine contracts.
"""
from typing import List, Dict, Optional, Any, Union

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
    TextScriptManifest,
    TextValidationRequest,
    TextValidationResult,
    TextGenerationRequest,
    TextGenerationResult,
    compute_sha256,
    utc_now_iso,
)
from app.text.validator import TextDomainValidator
from app.text.adapters import (
    BaseTextGenerationAdapter,
    SimulatedTextGenerationAdapter,
    MetaTextGenerationAdapter,
)
from app.contracts.engine import (
    EngineId,
    EngineStatus,
    QualityVerdict,
    ProvenanceRecord,
    UsageMetrics,
    TextGenerationParams,
    TextGenerationOutput,
    EngineRunResponse,
)


class TextGenerationEngine:
    """
    Specialist Text Generation Engine for comic book productions.
    Creates, validates, and attributes structured script blocks across dialogue,
    narration, captions, monologue, off-panel speech, and sound-effect words.
    """

    def __init__(
        self,
        simulated_adapter: Optional[SimulatedTextGenerationAdapter] = None,
        live_adapter: Optional[MetaTextGenerationAdapter] = None,
    ):
        self.simulated_adapter = simulated_adapter or SimulatedTextGenerationAdapter(default_success=True)
        self.live_adapter = live_adapter or MetaTextGenerationAdapter()

    def get_adapter(self, adapter_name: str) -> BaseTextGenerationAdapter:
        """Resolves the requested generation adapter."""
        if adapter_name == "meta_llm":
            return self.live_adapter
        return self.simulated_adapter

    def ingest_exact_user_text(
        self,
        project_id: str,
        story_id: str,
        scene_id: str,
        panel_id: str,
        user_text: str,
        speaker_id: Optional[str] = None,
        language: TextLanguage = TextLanguage.AR,
        direction: TextDirection = TextDirection.RTL,
        block_kind: ScriptBlockKind = ScriptBlockKind.DIALOGUE,
        passage_id: Optional[str] = None,
        delivery: Optional[DialogueDelivery] = DialogueDelivery.NORMAL,
        story_bible: Optional[Any] = None,
    ) -> ScriptBlock:
        """
        Ingests user-supplied text in exact-preservation mode.
        Guarantees code-point by code-point preservation without normalization,
        paraphrasing, or translation.
        """
        if not user_text or not user_text.strip():
            raise ValueError("user_text cannot be empty or purely whitespace.")

        text_hash = compute_sha256(user_text)
        block_id = f"blk_{panel_id}_user_{text_hash[:8]}"
        is_dialogue_or_monologue = block_kind in (ScriptBlockKind.DIALOGUE, ScriptBlockKind.MONOLOGUE, ScriptBlockKind.OFF_PANEL)

        resolved_speaker = None
        if is_dialogue_or_monologue:
            spk = speaker_id or "narrator"
            resolved_speaker = SpeakerRef(speaker_id=spk)

        block = ScriptBlock(
            block_id=block_id,
            project_id=project_id,
            story_id=story_id,
            scene_id=scene_id,
            panel_id=panel_id,
            block_kind=block_kind,
            reading_order_index=0,
            text_content=user_text,
            language=language,
            direction=direction,
            is_exact_user_text=True,
            provenance=TextProvenance(
                provenance_id=f"prov_{block_id}",
                source_mode=SourceMode.USER_EXACT,
                source_passage_id=passage_id,
                source_text_hash=text_hash,
                generated_text_hash=text_hash,
            ),
            speaker=resolved_speaker,
            delivery=delivery if is_dialogue_or_monologue else None,
        )

        # Validate against Story Bible if supplied
        if story_bible is not None:
            val_res = TextDomainValidator.validate_blocks(
                blocks=[block],
                target_scene_id=scene_id,
                target_panel_id=panel_id,
                story_bible=story_bible,
                exact_user_text=user_text,
            )
            # If errors found, return diagnostics in error
            errors = [d for d in val_res.diagnostics if d.severity == DiagnosticSeverity.ERROR]
            if errors:
                from app.text.errors import TextValidationError
                raise TextValidationError(
                    message=f"Validation failed for exact user text: {errors[0].message}",
                    details={"diagnostics": [d.model_dump() for d in errors]}
                )

        return block

    def validate_blocks(
        self,
        blocks: List[ScriptBlock],
        target_scene_id: str,
        target_panel_id: str,
        story_bible: Optional[Any] = None,
        timeline_events: Optional[List[Any]] = None,
        allow_undeclared_entities: bool = False,
        exact_user_text: Optional[str] = None,
    ) -> TextValidationResult:
        """Validates a collection of script blocks against canon and story state."""
        return TextDomainValidator.validate_blocks(
            blocks=blocks,
            target_scene_id=target_scene_id,
            target_panel_id=target_panel_id,
            story_bible=story_bible,
            timeline_events=timeline_events,
            allow_undeclared_entities=allow_undeclared_entities,
            exact_user_text=exact_user_text,
        )

    def generate_panel_text(self, request: TextGenerationRequest) -> TextGenerationResult:
        """
        Executes text generation for a panel through the designated adapter,
        then validates all output blocks against Story Bible canon and timeline state.
        """
        adapter = self.get_adapter(request.adapter_name)
        raw_result = adapter.generate(request)

        if not raw_result.success:
            return raw_result

        # Validate generated blocks
        val_result = TextDomainValidator.validate_blocks(
            blocks=raw_result.blocks,
            target_scene_id=request.scene_id,
            target_panel_id=request.panel_id,
            story_bible=request.story_bible,
            timeline_events=request.timeline_events,
            exact_user_text=request.exact_user_text,
        )

        all_diagnostics = raw_result.diagnostics + val_result.diagnostics
        has_errors = any(d.severity == DiagnosticSeverity.ERROR for d in all_diagnostics)

        clean_ts = "".join(c for c in utc_now_iso() if c.isdigit())[:14]
        manifest_id = f"sm_{request.project_id}_{request.panel_id}_{clean_ts}"
        canon_h = getattr(request.story_bible, "canon_hash", None)
        bible_v = str(getattr(request.story_bible, "bible_version", getattr(request.story_bible, "version", "1.0.0")))

        manifest = TextScriptManifest.from_blocks(
            manifest_id=manifest_id,
            project_id=request.project_id,
            story_id=request.story_id,
            scene_id=request.scene_id,
            blocks=val_result.accepted_blocks,
            canon_hash=canon_h,
            bible_version=bible_v,
            diagnostics=all_diagnostics,
        )

        final_status = EngineStatus.SUCCESS if not has_errors else EngineStatus.FAILED

        return TextGenerationResult(
            success=not has_errors,
            status=final_status,
            manifest=manifest,
            blocks=val_result.accepted_blocks,
            diagnostics=all_diagnostics,
            is_exact_user_text=raw_result.is_exact_user_text,
            adapter_used=request.adapter_name,
            is_simulated=adapter.is_simulated,
            cost_usd=raw_result.cost_usd,
            usage=raw_result.usage,
            error_message="Validation errors detected in generated blocks." if has_errors else None,
        )

    def run_engine_request(
        self,
        params: TextGenerationParams,
        project_id: str = "inkloop",
        story_bible: Optional[Any] = None,
        timeline_events: Optional[List[Any]] = None,
    ) -> EngineRunResponse[TextGenerationOutput]:
        """
        Executes text generation adapting to the standardized EngineRunResponse contract
        from backend/app/contracts/engine.py.
        """
        req_kind = ScriptBlockKind.DIALOGUE
        if params.text_type == "narration":
            req_kind = ScriptBlockKind.NARRATION
        elif params.text_type == "caption":
            req_kind = ScriptBlockKind.CAPTION
        elif params.text_type == "inner_monologue":
            req_kind = ScriptBlockKind.MONOLOGUE
        elif params.text_type == "sfx":
            req_kind = ScriptBlockKind.SFX

        lang = TextLanguage.AR if params.language == "ar" else TextLanguage.EN
        direction = TextDirection.RTL if lang == TextLanguage.AR else TextDirection.LTR

        char_ids = [params.speaker_id] if params.speaker_id else []

        gen_req = TextGenerationRequest(
            project_id=project_id,
            story_id=params.story_id,
            scene_id=params.scene_id,
            panel_id=params.panel_id,
            scene_action=params.script_beat,
            character_ids=char_ids,
            block_kinds_requested=[req_kind],
            exact_user_text=params.exact_user_text,
            target_language=lang,
            target_direction=direction,
            tone_guidance=params.tone,
            story_bible=story_bible,
            timeline_events=timeline_events,
            adapter_name="offline_simulated",
        )

        result = self.generate_panel_text(gen_req)

        # Build EngineRunResponse
        primary_text = ""
        spk = params.speaker_id
        if result.blocks:
            primary_text = result.blocks[0].text_content
            spk = result.blocks[0].speaker.speaker_id if result.blocks[0].speaker else None

        output = TextGenerationOutput(
            text_block_artifact_id=result.manifest.manifest_id if result.manifest else f"tb_{params.panel_id}",
            text_content=primary_text,
            speaker_id=spk,
            language=params.language,
            character_count=len(primary_text),
            word_count=len(primary_text.split()),
            is_exact_user_text=result.is_exact_user_text,
        )

        quality = QualityVerdict.PASSED if result.success else QualityVerdict.FAILED

        return EngineRunResponse[TextGenerationOutput](
            run_id=f"run_text_{params.panel_id}",
            attempt_id=f"att_text_{params.panel_id}_01",
            engine_id=EngineId.E4_TEXT_GENERATION,
            engine_version="1.0.0",
            schema_version="1.0.0",
            status=result.status,
            quality_verdict=quality,
            output=output,
            usage=result.usage or UsageMetrics(),
            provenance=ProvenanceRecord(
                engine_id=EngineId.E4_TEXT_GENERATION,
                engine_version="1.0.0",
                config_hash=compute_sha256(f"{params.story_id}_{params.panel_id}_{params.script_beat}"),
                input_artifact_ids=[],
            ),
            output_artifact_ids=[output.text_block_artifact_id],
        )
