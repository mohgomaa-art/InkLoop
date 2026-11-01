"""
InkLoop Text Generation Engine - Acceptance & Integration Test Suite (Milestone M5 / Workstream E4).
Validates structured script contracts, exact user-authored text preservation,
Story Bible canon speaker verification, narrative state timeline consistency,
offline simulated generation, and shared engine contracts.
"""
import pytest
from fastapi.testclient import TestClient

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
    TextGenerationRequest,
    TextGenerationResult,
    compute_sha256,
)
from app.text.validator import TextDomainValidator
from app.text.adapters import (
    SimulatedTextGenerationAdapter,
    MetaTextGenerationAdapter,
)
from app.text.engine import TextGenerationEngine
from app.project.story_state import StoryStateEvent
from app.contracts.engine import (
    EngineId,
    EngineStatus,
    QualityVerdict,
    TextGenerationParams,
    TextGenerationOutput,
)
from app.api.server import app
from app.project.bible import StoryBible as ProjectStoryBible
from app.project.canon import CanonSnapshot, StyleDefinition, CharacterDefinition
from tests.fixtures.benchmark_fixtures import CANONICAL_M0_STORY_BIBLE


@pytest.fixture
def canonical_snapshot() -> CanonSnapshot:
    style = StyleDefinition(
        style_id="bw_ink_screentone",
        name="Black and White Ink & Screentone",
        medium="black and white comic ink",
        rendering_approach="black and white ink with screentone shading",
        line_art_rules=["crisp contours"],
        tonal_rules=["solid blacks"],
    )
    nour_char = CharacterDefinition(
        character_id="nour",
        name="Nour",
        canon_version=1,
        attributes=[],
        clothing_attributes=["oversized hooded jacket, lightning-bolt patch"],
        visual_invariants=["round wireframe glasses"],
        approval_status="approved",
    )
    pb = ProjectStoryBible(
        project_id="inkloop",
        schema_version="1.0.0",
        bible_version=1,
        created_at="2026-10-29T00:00:00Z",
        updated_at="2026-10-29T00:00:00Z",
        status="validated",
        style=style,
        characters={"nour": nour_char},
        locations={},
        props={},
    )
    return pb.get_canon_snapshot()


@pytest.fixture
def engine() -> TextGenerationEngine:
    return TextGenerationEngine()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ==============================================================================
# 1. Structured Contracts & Schema Constraints
# ==============================================================================

def test_dialogue_block_valid_and_schema_constraints():
    """Verifies valid DialogueBlock creation and schema invariants."""
    block = ScriptBlock(
        block_id="blk_01",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.DIALOGUE,
        reading_order_index=0,
        text_content="أهلاً بك في إنكلوب!",
        language=TextLanguage.AR,
        direction=TextDirection.RTL,
        provenance=TextProvenance(
            provenance_id="prov_01",
            source_mode=SourceMode.MODEL_GENERATED,
        ),
        speaker=SpeakerRef(speaker_id="nour", display_name="Nour"),
        delivery=DialogueDelivery.NORMAL,
    )
    assert block.block_id == "blk_01"
    assert block.speaker.speaker_id == "nour"
    assert block.word_count == 4
    assert block.character_count == 19
    assert block.length_guidance["word_count"] == 4

    # Dialogue without speaker must fail validation
    with pytest.raises(ValueError, match="requires a 'speaker'"):
        ScriptBlock(
            block_id="blk_err_01",
            project_id="inkloop",
            scene_id="scene_01",
            panel_id="panel_01",
            block_kind=ScriptBlockKind.DIALOGUE,
            text_content="Valid text without speaker",
            provenance=TextProvenance(
                provenance_id="prov_err",
                source_mode=SourceMode.MODEL_GENERATED,
            ),
            speaker=None,
        )

    # Empty text must fail validation
    with pytest.raises(ValueError, match="cannot be empty or purely whitespace"):
        ScriptBlock(
            block_id="blk_err_02",
            project_id="inkloop",
            scene_id="scene_01",
            panel_id="panel_01",
            block_kind=ScriptBlockKind.DIALOGUE,
            text_content="   \n\t  ",
            provenance=TextProvenance(
                provenance_id="prov_err",
                source_mode=SourceMode.MODEL_GENERATED,
            ),
            speaker=SpeakerRef(speaker_id="nour"),
        )


def test_narration_caption_monologue_and_sfx_blocks():
    """Verifies specialized block kinds and their specific invariants."""
    prov = TextProvenance(provenance_id="prov_common", source_mode=SourceMode.MODEL_GENERATED)

    # Narration Block
    narration = ScriptBlock(
        block_id="blk_narr_01",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.NARRATION,
        text_content="The sun rose over the quiet alleyway.",
        language=TextLanguage.EN,
        direction=TextDirection.LTR,
        provenance=prov,
    )
    assert narration.block_kind == ScriptBlockKind.NARRATION
    assert narration.speaker is None

    # Caption Block
    caption = ScriptBlock(
        block_id="blk_cap_01",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.CAPTION,
        text_content="القاهرة — خريف ١٩٨٤",
        language=TextLanguage.AR,
        direction=TextDirection.RTL,
        provenance=prov,
        caption_kind=CaptionKind.SCENE_SETTING,
    )
    assert caption.caption_kind == CaptionKind.SCENE_SETTING

    # Monologue Block (internal thought)
    monologue = ScriptBlock(
        block_id="blk_mono_01",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.MONOLOGUE,
        text_content="هل يراني أحد هنا؟",
        language=TextLanguage.AR,
        direction=TextDirection.RTL,
        provenance=prov,
        speaker=SpeakerRef(speaker_id="nour"),
    )
    assert monologue.block_kind == ScriptBlockKind.MONOLOGUE

    # SFX Block
    sfx = ScriptBlock(
        block_id="blk_sfx_01",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.SFX,
        text_content="طاااااخ!",
        language=TextLanguage.AR,
        direction=TextDirection.RTL,
        provenance=prov,
        sfx_category=SFXCategory.IMPACT,
    )
    assert sfx.sfx_category == SFXCategory.IMPACT

    # SFX with character speaker must fail validation
    with pytest.raises(ValueError, match="cannot specify a character speaker"):
        ScriptBlock(
            block_id="blk_sfx_err",
            project_id="inkloop",
            scene_id="scene_01",
            panel_id="panel_01",
            block_kind=ScriptBlockKind.SFX,
            text_content="BOOM!",
            provenance=prov,
            speaker=SpeakerRef(speaker_id="nour"),
        )


# ==============================================================================
# 2. Exact User Text Preservation & Unicode Integrity
# ==============================================================================

def test_exact_user_text_preservation_arabic_and_diacritics(engine):
    """
    Verifies that user-supplied Arabic text with full diacritics (tashkeel),
    punctuation, and whitespace is preserved code-point by code-point.
    """
    arabic_exact = "«نُورٌ يُضِيءُ دَرْبَ المَدِينَةِ... أَلَيْسَ كَذَلِكَ؟!»"

    block = engine.ingest_exact_user_text(
        project_id="inkloop",
        story_id="story_01",
        scene_id="scene_01",
        panel_id="panel_01",
        user_text=arabic_exact,
        speaker_id="nour",
        language=TextLanguage.AR,
        direction=TextDirection.RTL,
    )

    # Byte-for-byte and code-point equality
    assert block.text_content == arabic_exact
    assert block.is_exact_user_text is True
    assert block.provenance.source_mode == SourceMode.USER_EXACT
    assert block.provenance.source_text_hash == compute_sha256(arabic_exact)
    assert block.provenance.generated_text_hash == compute_sha256(arabic_exact)


def test_exact_user_text_preservation_mixed_language_and_symbols(engine):
    """
    Verifies that mixed Arabic/English text, symbols, and numerals
    are preserved without reversal, normalization, or punctuation damage.
    """
    mixed_exact = "Nour said: 'أنا جاهزة الآن!' with 100% confidence. #Chapter_01"

    block = engine.ingest_exact_user_text(
        project_id="inkloop",
        story_id="story_01",
        scene_id="scene_01",
        panel_id="panel_01",
        user_text=mixed_exact,
        speaker_id="nour",
        language=TextLanguage.MIXED,
        direction=TextDirection.RTL,
    )

    assert block.text_content == mixed_exact
    assert "100%" in block.text_content
    assert "#Chapter_01" in block.text_content


def test_exact_user_text_alteration_rejected_by_validator(engine):
    """
    If a block claims is_exact_user_text=True but the text content has been
    altered from the original user text, validation must fail with EXACT_ALTERATION_DETECTED.
    """
    original_text = "هذا النص الأصلي للمستخدم دون تعديل."
    altered_text = "هذا النص الأصلي للمستخدم مع تعديل."

    block = engine.ingest_exact_user_text(
        project_id="inkloop",
        story_id="story_01",
        scene_id="scene_01",
        panel_id="panel_01",
        user_text=original_text,
        speaker_id="nour",
    )

    # Tamper with text content
    tampered_block = block.model_copy(update={"text_content": altered_text})

    val_res = engine.validate_blocks(
        blocks=[tampered_block],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        exact_user_text=original_text,
    )

    assert val_res.is_valid is False
    assert len(val_res.rejected_blocks) == 1
    diag = next(d for d in val_res.diagnostics if d.code == DiagnosticCode.EXACT_TEXT_ALTERATION)
    assert diag.severity == DiagnosticSeverity.ERROR


# ==============================================================================
# 3. Story Bible & Canon Verification
# ==============================================================================

def test_undeclared_speaker_rejected_against_story_bible(engine):
    """
    Dialogue spoken by a character not declared in the Story Bible
    must be rejected with DiagnosticCode.UNDECLARED_SPEAKER.
    """
    block = ScriptBlock(
        block_id="blk_spk_err",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.DIALOGUE,
        text_content="لن تفلت مني!",
        provenance=TextProvenance(
            provenance_id="prov_test",
            source_mode=SourceMode.MODEL_GENERATED,
        ),
        speaker=SpeakerRef(speaker_id="unknown_villain_99"),
    )

    val_res = engine.validate_blocks(
        blocks=[block],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        allow_undeclared_entities=False,
    )

    assert val_res.is_valid is False
    assert len(val_res.rejected_blocks) == 1
    diag = next(d for d in val_res.diagnostics if d.code == DiagnosticCode.UNDECLARED_SPEAKER)
    assert diag.severity == DiagnosticSeverity.ERROR
    assert "unknown_villain_99" in diag.message


def test_declared_character_speaker_accepted_against_canon_snapshot(engine, canonical_snapshot):
    """
    Dialogue spoken by declared character 'nour' in deep CanonSnapshot passes.
    Built-in 'narrator' is also accepted.
    """
    snapshot = canonical_snapshot

    block1 = ScriptBlock(
        block_id="blk_nour_ok",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.DIALOGUE,
        text_content="أنا هنا.",
        provenance=TextProvenance(provenance_id="p1", source_mode=SourceMode.MODEL_GENERATED),
        speaker=SpeakerRef(speaker_id="nour"),
    )
    block2 = ScriptBlock(
        block_id="blk_narr_ok",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.NARRATION,
        text_content="ساد الصمت.",
        provenance=TextProvenance(provenance_id="p2", source_mode=SourceMode.MODEL_GENERATED),
    )

    val_res = engine.validate_blocks(
        blocks=[block1, block2],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        story_bible=snapshot,
    )

    assert val_res.is_valid is True
    assert len(val_res.accepted_blocks) == 2
    assert not any(d.severity == DiagnosticSeverity.ERROR for d in val_res.diagnostics)


def test_canon_snapshot_immutability_preserved_during_text_operations(engine, canonical_snapshot):
    """
    Verifies that passing a CanonSnapshot to TextGenerationEngine
    does not and cannot mutate canonical state or mappings.
    """
    snapshot = canonical_snapshot
    initial_hash = snapshot.canon_hash

    # Run generation and validation
    req = TextGenerationRequest(
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        scene_action="Nour speaks",
        character_ids=["nour"],
        story_bible=snapshot,
    )
    res = engine.generate_panel_text(req)
    assert res.success is True

    # Check canon snapshot remains completely intact
    assert snapshot.canon_hash == initial_hash
    assert "nour" in snapshot.characters


# ==============================================================================
# 4. Narrative Timeline & Continuity Verification
# ==============================================================================

def test_narrative_timeline_state_consistency_unconscious_speaking_fails(engine):
    """
    If a character is declared 'unconscious' in the active timeline state,
    dialogue speech by that character must trigger CANON_STATE_CONTRADICTION.
    Internal monologue (thoughts) is evaluated separately.
    """
    # Event marking Nour unconscious in panel_01
    event = StoryStateEvent(
        event_id="evt_nour_knocked_out",
        sequence_number=1,
        scene_id="scene_01",
        panel_id="panel_01",
        entity_type="character",
        entity_id="nour",
        property_path="status",
        new_value="unconscious",
        timestamp="2026-10-29T00:00:00Z",
    )

    # 1. Dialogue while unconscious -> REJECTED
    dialogue_block = ScriptBlock(
        block_id="blk_nour_unconscious_dialogue",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.DIALOGUE,
        text_content="أنا بخير، لا تقلقوا!",
        provenance=TextProvenance(provenance_id="p_unc1", source_mode=SourceMode.MODEL_GENERATED),
        speaker=SpeakerRef(speaker_id="nour"),
    )

    val_res_dialogue = engine.validate_blocks(
        blocks=[dialogue_block],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        timeline_events=[event],
    )
    assert val_res_dialogue.is_valid is False
    assert len(val_res_dialogue.rejected_blocks) == 1
    diag = next(d for d in val_res_dialogue.diagnostics if d.code == DiagnosticCode.CANON_STATE_CONTRADICTION)
    assert diag.severity == DiagnosticSeverity.ERROR
    assert "cannot speak dialogue while state is 'unconscious'" in diag.message

    # 2. Internal thought / monologue while unconscious -> PERMITTED
    monologue_block = ScriptBlock(
        block_id="blk_nour_unconscious_mono",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.MONOLOGUE,
        text_content="أين... أين أنا؟ كل شيء مظلم...",
        provenance=TextProvenance(provenance_id="p_unc2", source_mode=SourceMode.MODEL_GENERATED),
        speaker=SpeakerRef(speaker_id="nour"),
    )

    val_res_mono = engine.validate_blocks(
        blocks=[monologue_block],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        timeline_events=[event],
    )
    assert val_res_mono.is_valid is True
    assert len(val_res_mono.accepted_blocks) == 1


# ==============================================================================
# 5. Panel Linkage, Reading Order & Language Metadata
# ==============================================================================

def test_panel_scene_mismatch_and_reading_order_discontinuity(engine):
    """Verifies detection of panel mismatch and duplicate reading order indices."""
    prov = TextProvenance(provenance_id="p_mismatch", source_mode=SourceMode.MODEL_GENERATED)

    b1 = ScriptBlock(
        block_id="blk_wrong_panel",
        project_id="inkloop",
        scene_id="scene_02",  # Mismatch: validating against scene_01
        panel_id="panel_05",  # Mismatch: validating against panel_01
        block_kind=ScriptBlockKind.DIALOGUE,
        reading_order_index=0,
        text_content="Hello",
        language=TextLanguage.EN,
        direction=TextDirection.LTR,
        provenance=prov,
        speaker=SpeakerRef(speaker_id="nour"),
    )

    val_res = engine.validate_blocks(
        blocks=[b1],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        story_bible=CANONICAL_M0_STORY_BIBLE,
    )
    assert val_res.is_valid is False
    diag = next(d for d in val_res.diagnostics if d.code == DiagnosticCode.MISSING_PANEL_LINKAGE)
    assert diag.severity == DiagnosticSeverity.ERROR


def test_text_length_guidance_and_excessive_length_warning(engine):
    """Verifies reading duration calculation and excessive length warnings."""
    long_speech = "هذه جملة طويلة جداً جداً جداً " * 35 # > 600 characters
    block = ScriptBlock(
        block_id="blk_long",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.DIALOGUE,
        reading_order_index=0,
        text_content=long_speech,
        provenance=TextProvenance(provenance_id="p_long", source_mode=SourceMode.MODEL_GENERATED),
        speaker=SpeakerRef(speaker_id="nour"),
    )

    assert block.character_count > 600
    assert block.length_guidance["estimated_reading_seconds"] > 5.0

    val_res = engine.validate_blocks(
        blocks=[block],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        story_bible=CANONICAL_M0_STORY_BIBLE,
    )
    # Excessive length is a WARNING, does not block validation
    assert val_res.is_valid is True
    assert val_res.needs_human_review is True
    diag = next(d for d in val_res.diagnostics if d.code == DiagnosticCode.EXCESSIVE_LENGTH)
    assert diag.severity == DiagnosticSeverity.WARNING


def test_arabic_rtl_direction_handling(engine):
    """Verifies that Arabic text requires RTL direction and is never reversed."""
    arabic_text = "صباح الخير يا نور"
    block = ScriptBlock(
        block_id="blk_dir_test",
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.DIALOGUE,
        text_content=arabic_text,
        language=TextLanguage.AR,
        direction=TextDirection.LTR, # Inappropriate LTR for Arabic
        provenance=TextProvenance(provenance_id="p_dir", source_mode=SourceMode.MODEL_GENERATED),
        speaker=SpeakerRef(speaker_id="nour"),
    )

    val_res = engine.validate_blocks(
        blocks=[block],
        target_scene_id="scene_01",
        target_panel_id="panel_01",
        story_bible=CANONICAL_M0_STORY_BIBLE,
    )
    # Emits script direction mismatch warning
    diag = next(d for d in val_res.diagnostics if d.code == DiagnosticCode.LANGUAGE_SCRIPT_MISMATCH)
    assert diag.severity == DiagnosticSeverity.WARNING
    # Text string must remain in original logical order
    assert block.text_content == arabic_text


# ==============================================================================
# 6. Generation Path & Adapter Isolation
# ==============================================================================

def test_simulated_adapter_deterministic_generation_multiple_kinds(engine):
    """
    Tests offline simulated generation producing CAPTION, DIALOGUE, and SFX
    blocks with correct sequential reading orders and zero provider spend ($0.00).
    """
    req = TextGenerationRequest(
        project_id="inkloop",
        story_id="story_01",
        scene_id="scene_01",
        panel_id="panel_01",
        scene_action="Nour bursts through the door into the cafe",
        character_ids=["nour"],
        block_kinds_requested=[
            ScriptBlockKind.CAPTION,
            ScriptBlockKind.DIALOGUE,
            ScriptBlockKind.SFX,
        ],
        target_language=TextLanguage.AR,
        story_bible=CANONICAL_M0_STORY_BIBLE,
    )

    res = engine.generate_panel_text(req)

    assert res.success is True
    assert res.status == EngineStatus.SUCCESS
    assert len(res.blocks) == 3
    assert res.is_simulated is True
    assert res.cost_usd == 0.0

    kinds = [b.block_kind for b in res.blocks]
    assert kinds == [ScriptBlockKind.CAPTION, ScriptBlockKind.DIALOGUE, ScriptBlockKind.SFX]

    # Verify sequential reading orders
    indices = [b.reading_order_index for b in res.blocks]
    assert indices == [0, 1, 2]

    # Verify manifest creation
    assert res.manifest is not None
    assert res.manifest.total_word_count > 0
    assert "ar" in res.manifest.languages_present


def test_simulated_adapter_scriptable_failure(engine):
    """Verifies that adapter failures are handled cleanly without unhandled crashes."""
    sim_adapter = SimulatedTextGenerationAdapter()
    sim_adapter.script_panel_failure(
        panel_id="panel_02",
        status=EngineStatus.FAILED,
        error_message="Simulated text model context length exceeded"
    )
    custom_engine = TextGenerationEngine(simulated_adapter=sim_adapter)

    req = TextGenerationRequest(
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_02",
        scene_action="Any action",
        character_ids=["nour"],
    )

    res = custom_engine.generate_panel_text(req)
    assert res.success is False
    assert res.status == EngineStatus.FAILED
    assert res.error_message == "Simulated text model context length exceeded"


def test_meta_live_adapter_unconfigured_fails_closed_blocked(engine):
    """
    When live Meta LLM credentials are not configured,
    the adapter must fail closed with EngineStatus.BLOCKED without fabricating AI generation.
    """
    req = TextGenerationRequest(
        project_id="inkloop",
        scene_id="scene_01",
        panel_id="panel_01",
        scene_action="Action",
        character_ids=["nour"],
        adapter_name="meta_llm",
    )

    res = engine.generate_panel_text(req)
    assert res.success is False
    assert res.status in (EngineStatus.BLOCKED, EngineStatus.NOT_IMPLEMENTED)
    assert "not configured" in res.error_message.lower() or "contract is pending" in res.error_message.lower()


# ==============================================================================
# 7. Engine Contracts Adaptation & API Integration
# ==============================================================================

def test_adaptation_to_engine_run_request_and_response_contracts(engine):
    """
    Verifies that run_engine_request() adapts to shared EngineRunResponse[TextGenerationOutput]
    from backend/app/contracts/engine.py.
    """
    params = TextGenerationParams(
        story_id="story_01",
        scene_id="scene_01",
        panel_id="panel_01",
        text_type="dialogue",
        speaker_id="nour",
        script_beat="Nour speaks with determination",
        language="ar",
    )

    resp = engine.run_engine_request(
        params=params,
        project_id="inkloop",
        story_bible=CANONICAL_M0_STORY_BIBLE,
    )

    assert resp.engine_id == EngineId.E4_TEXT_GENERATION
    assert resp.status == EngineStatus.SUCCESS
    assert resp.quality_verdict == QualityVerdict.PASSED
    assert resp.output is not None
    assert isinstance(resp.output, TextGenerationOutput)
    assert resp.output.speaker_id == "nour"
    assert resp.output.character_count > 0
    assert resp.output.language == "ar"


def test_text_api_endpoints_roundtrip(client):
    """Verifies REST endpoints for /api/v1/text/ingest, /validate, and /generate."""
    # 1. Ingest Exact User Text
    ingest_payload = {
        "project_id": "inkloop",
        "story_id": "story_01",
        "scene_id": "scene_01",
        "panel_id": "panel_01",
        "user_text": "هذا نص تجريبي من المؤلف.",
        "speaker_id": "nour",
        "language": "ar",
        "direction": "rtl",
        "block_kind": "dialogue",
    }
    res_ing = client.post("/api/v1/text/ingest", json=ingest_payload)
    assert res_ing.status_code == 200
    block_data = res_ing.json()
    assert block_data["text_content"] == "هذا نص تجريبي من المؤلف."
    assert block_data["is_exact_user_text"] is True

    # 2. Validate Blocks
    val_payload = {
        "project_id": "inkloop",
        "target_scene_id": "scene_01",
        "target_panel_id": "panel_01",
        "blocks": [block_data],
        "allow_undeclared_entities": True,
    }
    res_val = client.post("/api/v1/text/validate", json=val_payload)
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["is_valid"] is True
    assert len(val_data["accepted_blocks"]) == 1

    # 3. Generate Text via Adapter
    gen_payload = {
        "project_id": "inkloop",
        "story_id": "story_01",
        "scene_id": "scene_01",
        "panel_id": "panel_01",
        "scene_action": "Nour speaks to the shopkeeper",
        "character_ids": ["nour"],
        "block_kinds_requested": ["dialogue"],
        "target_language": "ar",
        "adapter_name": "offline_simulated",
    }
    res_gen = client.post("/api/v1/text/generate", json=gen_payload)
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["success"] is True
    assert len(gen_data["blocks"]) == 1
    assert gen_data["is_simulated"] is True


def test_text_api_blocks_simulation_without_explicit_offline_mode(client, monkeypatch):
    """The product API does not silently serve deterministic dialogue as model output."""
    monkeypatch.setenv("INKLOOP_OFFLINE_MODE", "0")
    response = client.post("/api/v1/text/generate", json={
        "project_id": "inkloop",
        "scene_id": "scene_01",
        "panel_id": "panel_01",
        "scene_action": "Nour greets the shopkeeper",
        "character_ids": ["nour"],
        "block_kinds_requested": ["dialogue"],
        "adapter_name": "offline_simulated",
    })
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ERR_OFFLINE_MODE_NOT_ENABLED"
