"""
InkLoop Text Generation Engine - Domain Validator (Milestone M5 / Workstream E4).
Provides deterministic schema validation, canon speaker verification,
narrative timeline state consistency, exact user text preservation checks,
and bi-directional language handling.
"""
import re
from typing import List, Dict, Any, Optional, Set

from app.text.enums import (
    ScriptBlockKind,
    DialogueDelivery,
    TextLanguage,
    TextDirection,
    SourceMode,
    DiagnosticSeverity,
    DiagnosticCode,
)
from app.text.models import (
    ScriptBlock,
    TextValidationDiagnostic,
    TextValidationRequest,
    TextValidationResult,
    compute_sha256,
)
from app.project.story_state import resolve_timeline_state, StoryStateEvent

# Regex detecting Arabic script characters
ARABIC_CHAR_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
# Regex detecting Latin alphabet characters
LATIN_CHAR_PATTERN = re.compile(r"[a-zA-Z]")

# Maximum text length thresholds (character counts)
MAX_LENGTH_BY_KIND = {
    ScriptBlockKind.DIALOGUE: 600,
    ScriptBlockKind.MONOLOGUE: 600,
    ScriptBlockKind.NARRATION: 800,
    ScriptBlockKind.CAPTION: 400,
    ScriptBlockKind.OFF_PANEL: 600,
    ScriptBlockKind.SFX: 80,
}


class TextDomainValidator:
    """
    Deterministic domain validator for comic script text blocks.
    Enforces strict Story Bible canon, timeline consistency, and exact-preservation invariants.
    """

    @classmethod
    def detect_script_language(cls, text: str) -> TextLanguage:
        """Detects whether text is Arabic, English, or mixed without altering characters."""
        has_arabic = bool(ARABIC_CHAR_PATTERN.search(text))
        has_latin = bool(LATIN_CHAR_PATTERN.search(text))

        if has_arabic and has_latin:
            return TextLanguage.MIXED
        elif has_arabic:
            return TextLanguage.AR
        elif has_latin:
            return TextLanguage.EN
        return TextLanguage.UNSPECIFIED

    @classmethod
    def extract_declared_character_ids(cls, story_bible: Any) -> Set[str]:
        """Extracts declared character IDs from StoryBible, CanonSnapshot, or dictionary."""
        if story_bible is None:
            return set()

        chars = getattr(story_bible, "characters", {})
        if isinstance(chars, dict):
            return {k.lower() for k in chars.keys()}
        return set()

    @classmethod
    def validate_blocks(
        cls,
        blocks: List[ScriptBlock],
        target_scene_id: str,
        target_panel_id: str,
        story_bible: Optional[Any] = None,
        timeline_events: Optional[List[Any]] = None,
        allow_undeclared_entities: bool = False,
        exact_user_text: Optional[str] = None,
    ) -> TextValidationResult:
        """
        Runs comprehensive deterministic checks across a list of script blocks.
        """
        diagnostics: List[TextValidationDiagnostic] = []
        accepted_blocks: List[ScriptBlock] = []
        rejected_blocks: List[ScriptBlock] = []

        declared_chars = cls.extract_declared_character_ids(story_bible)

        # 1. Resolve effective timeline state if events are supplied
        effective_state: Dict[str, Any] = {}
        if timeline_events:
            resolution = resolve_timeline_state(
                events=timeline_events,
                target_scene_or_panel=target_panel_id,
                strict_transitions=False
            )
            effective_state = resolution.effective_state
            if resolution.unresolved_conflicts:
                for conf in resolution.unresolved_conflicts:
                    diagnostics.append(TextValidationDiagnostic(
                        code=DiagnosticCode.CANON_STATE_CONTRADICTION,
                        severity=DiagnosticSeverity.WARNING,
                        message=f"Timeline state conflict: {conf}",
                    ))

        # Track reading order within panel
        seen_reading_indices: Set[int] = set()

        # 2. Validate individual blocks
        for block in blocks:
            block_has_error = False

            # Panel and Scene Linkage
            if block.scene_id != target_scene_id or block.panel_id != target_panel_id:
                diagnostics.append(TextValidationDiagnostic(
                    code=DiagnosticCode.MISSING_PANEL_LINKAGE,
                    severity=DiagnosticSeverity.ERROR,
                    target_block_id=block.block_id,
                    field_name="panel_id",
                    message=f"Block target ({block.scene_id}/{block.panel_id}) does not match context ({target_scene_id}/{target_panel_id}).",
                    observed_value=f"{block.scene_id}/{block.panel_id}",
                    suggested_fix=f"Assign block to target scene '{target_scene_id}' and panel '{target_panel_id}'.",
                ))
                block_has_error = True

            # Reading Order Uniqueness
            if block.reading_order_index in seen_reading_indices:
                diagnostics.append(TextValidationDiagnostic(
                    code=DiagnosticCode.READING_ORDER_DISCONTINUITY,
                    severity=DiagnosticSeverity.WARNING,
                    target_block_id=block.block_id,
                    field_name="reading_order_index",
                    message=f"Duplicate reading_order_index '{block.reading_order_index}' in panel '{block.panel_id}'.",
                    observed_value=str(block.reading_order_index),
                    suggested_fix="Ensure reading order is strictly sequential.",
                ))
            seen_reading_indices.add(block.reading_order_index)

            # Length Limits
            max_len = MAX_LENGTH_BY_KIND.get(block.block_kind, 600)
            if block.character_count > max_len:
                diagnostics.append(TextValidationDiagnostic(
                    code=DiagnosticCode.EXCESSIVE_LENGTH,
                    severity=DiagnosticSeverity.WARNING,
                    target_block_id=block.block_id,
                    field_name="text_content",
                    message=f"Block text length ({block.character_count} chars) exceeds recommended limit of {max_len} chars for {block.block_kind.value}.",
                    observed_value=str(block.character_count),
                    suggested_fix="Split into multiple panels or dialogue beats.",
                ))

            # Speaker Canon Verification
            if block.speaker is not None:
                spk_id = block.speaker.speaker_id.lower()
                # 'narrator' is recognized as a built-in narrative source
                if spk_id != "narrator":
                    if declared_chars and spk_id not in declared_chars:
                        severity = DiagnosticSeverity.WARNING if allow_undeclared_entities else DiagnosticSeverity.ERROR
                        diagnostics.append(TextValidationDiagnostic(
                            code=DiagnosticCode.UNDECLARED_SPEAKER,
                            severity=severity,
                            target_block_id=block.block_id,
                            field_name="speaker",
                            message=f"Speaker '{spk_id}' is not declared in the Story Bible / Canon characters.",
                            observed_value=spk_id,
                            suggested_fix=f"Declare character '{spk_id}' via formal canon proposal or assign to declared character: {sorted(declared_chars)}.",
                        ))
                        if severity == DiagnosticSeverity.ERROR:
                            block_has_error = True

                    # Timeline State Contradictions (e.g. unconscious character speaking)
                    char_state = effective_state.get(spk_id) or effective_state.get(f"character:{spk_id}")
                    if char_state and isinstance(char_state, dict):
                        # Check physical ability to speak
                        is_unconscious = char_state.get("status") in ("unconscious", "asleep", "knocked_out")
                        is_gagged = char_state.get("gagged", False) or char_state.get("mouth_blocked", False) or char_state.get("status") in ("gagged", "muted")

                        if (is_unconscious or is_gagged) and block.block_kind in (ScriptBlockKind.DIALOGUE, ScriptBlockKind.OFF_PANEL):
                            reason = "unconscious" if is_unconscious else "gagged"
                            diagnostics.append(TextValidationDiagnostic(
                                code=DiagnosticCode.CANON_STATE_CONTRADICTION,
                                severity=DiagnosticSeverity.ERROR,
                                target_block_id=block.block_id,
                                field_name="speaker",
                                message=f"Character '{spk_id}' cannot speak dialogue while state is '{reason}'.",
                                observed_value=str(char_state),
                                suggested_fix="Change block to inner monologue or update story state before speech.",
                            ))
                            block_has_error = True

            # Addressee Canon Verification
            if block.addressee is not None:
                addr_id = block.addressee.speaker_id.lower()
                if declared_chars and addr_id not in declared_chars:
                    diagnostics.append(TextValidationDiagnostic(
                        code=DiagnosticCode.UNDECLARED_ENTITY,
                        severity=DiagnosticSeverity.WARNING,
                        target_block_id=block.block_id,
                        field_name="addressee",
                        message=f"Addressee '{addr_id}' is not declared in the Story Bible.",
                        observed_value=addr_id,
                    ))

            # Exact User Text Preservation Invariant
            if block.is_exact_user_text:
                if exact_user_text is not None:
                    # Compare code-point by code-point
                    if block.text_content != exact_user_text:
                        diagnostics.append(TextValidationDiagnostic(
                            code=DiagnosticCode.EXACT_TEXT_ALTERATION,
                            severity=DiagnosticSeverity.ERROR,
                            target_block_id=block.block_id,
                            field_name="text_content",
                            message="Exact user text was altered, normalized, or paraphrased.",
                            observed_value=block.text_content[:50] + "...",
                            suggested_fix="Preserve original user text code-point by code-point.",
                        ))
                        block_has_error = True
                elif block.provenance.source_text_hash:
                    # Verify content hash matches source hash
                    if compute_sha256(block.text_content) != block.provenance.source_text_hash:
                        diagnostics.append(TextValidationDiagnostic(
                            code=DiagnosticCode.EXACT_TEXT_ALTERATION,
                            severity=DiagnosticSeverity.ERROR,
                            target_block_id=block.block_id,
                            field_name="text_content",
                            message="Hash mismatch: exact user text payload does not match recorded source_text_hash.",
                            observed_value=compute_sha256(block.text_content),
                            suggested_fix="Re-ingest original user text without alteration.",
                        ))
                        block_has_error = True

            # Script Direction & Language Matching
            detected_lang = cls.detect_script_language(block.text_content)
            if detected_lang == TextLanguage.AR and block.direction != TextDirection.RTL:
                diagnostics.append(TextValidationDiagnostic(
                    code=DiagnosticCode.LANGUAGE_SCRIPT_MISMATCH,
                    severity=DiagnosticSeverity.WARNING,
                    target_block_id=block.block_id,
                    field_name="direction",
                    message="Arabic text detected but block direction is not set to RTL.",
                    observed_value=block.direction.value,
                    suggested_fix="Set direction to 'rtl'.",
                ))

            if block_has_error:
                rejected_blocks.append(block)
            else:
                accepted_blocks.append(block)

        # 3. Overall Verdict Calculation
        has_errors = any(d.severity == DiagnosticSeverity.ERROR for d in diagnostics)
        has_warnings = any(d.severity == DiagnosticSeverity.WARNING for d in diagnostics)

        is_valid = not has_errors
        needs_human_review = has_warnings or (len(rejected_blocks) > 0)

        return TextValidationResult(
            is_valid=is_valid,
            needs_human_review=needs_human_review,
            diagnostics=diagnostics,
            accepted_blocks=accepted_blocks,
            rejected_blocks=rejected_blocks,
            effective_timeline_state=effective_state,
        )
