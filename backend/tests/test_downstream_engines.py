"""
Deterministic unit tests for downstream specialist engines:
E5 (Typography), E6 (Speech Bubbles), E7 (Effects & Motion),
S6 (Final Compositor), S7 (Page Verification), S8 (Export & Delivery).
"""
import pytest
from io import BytesIO
from pathlib import Path
from PIL import Image

from app.contracts.geometry import Rect, Point, Size, BlendMode, AssetFormat
from app.contracts.artifacts import AssetType
from app.contracts.engine import (
    TypographyParams,
    SpeechBubbleParams,
    EffectsMotionParams,
    CompositorParams,
    VerificationParams,
    ExportParams,
    QualityVerdict,
)
from app.storage.registry import AssetRegistry
from app.text.typography import TypographyEngine, shape_arabic
from app.canvas.speech_bubble import SpeechBubbleEngine
from app.canvas.effects import EffectsMotionEngine
from app.canvas.compositor import FinalCompositor
from app.verification.page_verifier import PageVerifierEngine
from app.export.delivery import ExportDeliveryEngine


@pytest.fixture
def test_registry(tmp_path):
    return AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")


def test_e5_arabic_shaping_and_measurement(test_registry):
    engine = TypographyEngine()
    params = TypographyParams(
        text_block_artifact_id="text_01",
        text_content="مرحبا بك في InkLoop",
        font_family="Cairo",
        font_size_pt=18.0,
        max_width_px=300.0,
        language="ar",
    )
    output = engine.shape_and_measure_text(params, asset_registry=test_registry)

    assert output.lettering_layer_artifact_id is not None
    assert output.line_count >= 1
    assert output.measured_bounds.width > 0
    assert output.measured_bounds.height > 0
    assert not output.text_overflow
    resolved = test_registry.resolve_asset(output.lettering_layer_artifact_id)
    assert resolved.absolute_path.exists()


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Let's verify the rules first.", "en"),
        ("لنراجع القواعد أولاً.", "ar"),
        ("Let's verify القواعد أولاً.", "mixed"),
    ],
)
def test_e5_agent_speech_at_24px_renders_short_english_arabic_and_mixed_text(test_registry, text, language):
    engine = TypographyEngine()
    params = TypographyParams(
        text_block_artifact_id=f"speech_{language}",
        text_content=text,
        font_family="Cairo",
        font_size_pt=24.0,
        max_width_px=320.0,
        language=language,
    )
    output = engine.shape_and_measure_text(params, asset_registry=test_registry)

    assert output.lettering_layer_artifact_id
    assert output.actual_font_used
    assert output.line_count >= 1
    assert output.measured_bounds.width > 0
    assert output.measured_bounds.height > 0
    assert output.text_overflow is False


def test_e5_overflow_detection(test_registry):
    engine = TypographyEngine()
    params = TypographyParams(
        text_block_artifact_id="text_long",
        text_content="طويلللللللللللللللللللللللللللللللللللللللللللللللللللللل",
        max_width_px=30.0,  # Unbreakable token exceeds max width
    )
    output = engine.shape_and_measure_text(params, asset_registry=test_registry)
    assert output.text_overflow is True


def test_e6_speech_bubble_placement(test_registry):
    engine = SpeechBubbleEngine()
    params = SpeechBubbleParams(
        text_block_artifact_id="text_01",
        lettering_layer_artifact_id="layer_lettering_01",
        measured_text_bounds=Rect(x=0, y=0, width=120, height=40),
        panel_slot_rect=Rect(x=50, y=50, width=300, height=250),
        bubble_shape="rounded_rectangle",
        tail_target=Point(x=100, y=200),
    )
    output = engine.place_speech_bubble(params, asset_registry=test_registry)

    assert output.bubble_layer_artifact_id is not None
    assert output.bubble_bounds.width >= 120
    assert output.bubble_bounds.height >= 40
    assert output.tail_anchor is not None
    assert not output.collision_detected


def test_e7_effects_motion_generator(test_registry):
    engine = EffectsMotionEngine()
    params = EffectsMotionParams(
        effect_category="speed_lines",
        target_panel_rect=Rect(x=0, y=0, width=400, height=300),
        intensity=1.5,
        direction_deg=45.0,
        blend_mode=BlendMode.NORMAL,
        focal_point=Point(x=200, y=150),
    )
    output = engine.generate_effect(params, asset_registry=test_registry)

    assert output.effect_layer_artifact_id is not None
    assert output.blend_mode == BlendMode.NORMAL
    resolved = test_registry.resolve_asset(output.effect_layer_artifact_id)
    assert resolved.absolute_path.exists()
    img = Image.open(resolved.absolute_path)
    assert img.size == (400, 300)


def test_s6_compositor_assembles_layers(tmp_path, test_registry):
    compositor = FinalCompositor(output_dir=tmp_path / "composites")

    # Ingest a mock art layer
    img1 = Image.new("RGBA", (300, 400), (255, 0, 0, 128))
    buf = BytesIO()
    img1.save(buf, format="PNG")
    art_asset = test_registry.ingest_bytes(
        buf.getvalue(), "art.png", "default_project", AssetType.GENERIC_ARTIFACT
    )

    params = CompositorParams(
        canvas_spec_artifact_id="spec_01",
        ordered_layer_artifact_ids=[art_asset.asset_id],
        dpi=150.0,
    )
    output = compositor.composite_page(
        params,
        asset_registry=test_registry,
        canvas_dimensions=Size(width=300, height=400),
    )

    assert output.composite_page_artifact_id is not None
    assert output.layer_count == 1
    assert output.sha256 is not None
    assert Path(output.output_file_path).exists()


def test_s7_page_verifier(test_registry):
    verifier = PageVerifierEngine()

    img = Image.new("RGBA", (100, 100), (0, 0, 0, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    asset = test_registry.ingest_bytes(
        buf.getvalue(), "page_test.png", "default_project", AssetType.GENERIC_ARTIFACT
    )

    params = VerificationParams(
        target_artifact_id=asset.asset_id,
        verification_type="whole_page_integrity",
        spec_id="spec_v1",
    )
    output = verifier.verify_page(params, asset_registry=test_registry)

    assert output.verdict in (QualityVerdict.PASSED, QualityVerdict.FAILED)
    assert len(output.attribute_verdicts) > 0
    assert output.qa_report_artifact_id is not None


def test_s8_export_delivery_pdf_and_png(tmp_path, test_registry):
    engine = ExportDeliveryEngine(export_dir=tmp_path / "exports")

    img = Image.new("RGB", (600, 800), (240, 240, 240))
    buf = BytesIO()
    img.save(buf, format="PNG")
    page_asset = test_registry.ingest_bytes(
        buf.getvalue(), "comp.png", "default_project", AssetType.GENERIC_ARTIFACT
    )

    params = ExportParams(
        project_id="test_export_project",
        page_composite_artifact_ids=[page_asset.asset_id],
        target_format=AssetFormat.PDF,
    )
    output = engine.export_delivery(params, asset_registry=test_registry, reading_direction="rtl")

    assert output.export_artifact_id is not None
    assert output.page_count == 1
    assert output.byte_size > 0
    assert output.sha256 is not None
    assert Path(output.file_path).exists()
    assert Path(output.file_path).suffix == ".pdf"


def test_e5_e6_script_block_to_speech_bubble_integration(test_registry):
    from app.text.models import ScriptBlock, SpeakerRef, TextProvenance
    from app.text.enums import ScriptBlockKind, DialogueDelivery, TextLanguage, TextDirection, SourceMode

    block = ScriptBlock(
        block_id="blk_test_arabic_01",
        project_id="test_proj",
        scene_id="scene_01",
        panel_id="panel_01",
        block_kind=ScriptBlockKind.DIALOGUE,
        text_content="أهلاً بك في عالم الحبر المتدفق!",
        language=TextLanguage.AR,
        direction=TextDirection.RTL,
        speaker=SpeakerRef(speaker_id="nour", display_name="Nour"),
        delivery=DialogueDelivery.SHOUT,
        provenance=TextProvenance(
            provenance_id="prov_01",
            source_mode=SourceMode.USER_EXACT,
        ),
    )

    typo_engine = TypographyEngine()
    bubble_engine = SpeechBubbleEngine()
    panel_rect = Rect(x=0, y=0, width=500, height=400)

    result = bubble_engine.place_speech_bubble_for_script_block(
        script_block=block,
        panel_slot_rect=panel_rect,
        typography_engine=typo_engine,
        asset_registry=test_registry,
        project_id="test_proj",
        reading_direction="rtl",
    )

    assert result["speech_bubble_output"].bubble_layer_artifact_id is not None
    assert result["typography_output"].lettering_layer_artifact_id is not None
    assert result["typography_output"].line_count >= 1
    assert result["bubble_vector_geometry"].bubble_path.startswith("M")
    assert result["speech_bubble_output"].bubble_bounds.width > 0
    assert result["speech_bubble_output"].bubble_bounds.height > 0

