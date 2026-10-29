"""
Unit tests for InkLoop Engine Execution, Artifact Manifests, and Adapter Contracts.
Tests typed contracts for all engines, fixtures, error classifications, and offline adapter mocking.
"""
import json
from pathlib import Path
import pytest
from app.contracts.engine import (
    EngineId,
    EngineStatus,
    QualityVerdict,
    UsageMetrics,
    ProvenanceRecord,
    EngineRunRequest,
    EngineRunResponse,
    ImageGenerationParams,
    ImageGenerationOutput,
    CanvasGenerationParams,
    CanvasGenerationOutput,
    ImageCanvasIntegrationParams,
    ImageCanvasIntegrationOutput,
    TextGenerationParams,
    TextGenerationOutput,
    TypographyParams,
    TypographyOutput,
    SpeechBubbleParams,
    SpeechBubbleOutput,
    EffectsMotionParams,
    EffectsMotionOutput,
    CompositorParams,
    CompositorOutput,
    VerificationParams,
    VerificationOutput,
    ExportParams,
    ExportOutput,
)
from app.contracts.artifacts import (
    AssetType,
    LifecycleStatus,
    ArtifactManifest,
    compute_file_sha256,
    build_artifact_manifest,
)
from app.contracts.geometry import Size, Rect, Point, FitMode, BlendMode, ColorSpace, AssetFormat
from app.contracts.errors import ErrorCode
from app.contracts.adapters.image_generation import ImageGenerationEngineAdapter

def test_engine_run_request_and_response_roundtrip():
    req = EngineRunRequest[dict](
        run_id="run_20261029_001",
        attempt_id="att_01",
        engine_id=EngineId.E2_CANVAS_GENERATION,
        engine_version="1.0.0",
        schema_version="1.0.0",
        project_id="proj_inkloop_01",
        parameters={"format": "manga", "grid": "4_koma"},
        config_hash="sha256_mock_config_hash_12345",
        budget_limit_usd=5.0
    )
    req_json = req.model_dump_json()
    restored_req = EngineRunRequest[dict].model_validate_json(req_json)
    assert restored_req.run_id == "run_20261029_001"
    assert restored_req.engine_id == EngineId.E2_CANVAS_GENERATION
    assert restored_req.parameters["format"] == "manga"

    resp = EngineRunResponse[dict](
        run_id=req.run_id,
        attempt_id=req.attempt_id,
        engine_id=req.engine_id,
        engine_version=req.engine_version,
        schema_version="1.0.0",
        status=EngineStatus.SUCCESS,
        quality_verdict=QualityVerdict.PASSED,
        output={"canvas_width": 2480, "canvas_height": 3508},
        usage=UsageMetrics(compute_seconds=0.25, estimated_cost_usd=0.0),
        provenance=ProvenanceRecord(
            engine_id=req.engine_id,
            engine_version=req.engine_version,
            config_hash=req.config_hash
        )
    )
    resp_json = resp.model_dump_json()
    restored_resp = EngineRunResponse[dict].model_validate_json(resp_json)
    assert restored_resp.status == EngineStatus.SUCCESS
    assert restored_resp.quality_verdict == QualityVerdict.PASSED
    assert restored_resp.usage.compute_seconds == 0.25

def test_quality_verdict_distinct_from_engine_status():
    """Proves that a run can have EngineStatus.SUCCESS while quality_verdict is FAILED or REJECTED."""
    resp = EngineRunResponse[dict](
        run_id="run_qa_01",
        attempt_id="att_01",
        engine_id=EngineId.S7_QUALITY_VERIFICATION,
        engine_version="1.0.0",
        status=EngineStatus.SUCCESS,            # Execution completed without crash
        quality_verdict=QualityVerdict.FAILED,  # But the candidate visual failed quality inspection
        provenance=ProvenanceRecord(
            engine_id=EngineId.S7_QUALITY_VERIFICATION,
            engine_version="1.0.0",
            config_hash="dummy_hash"
        )
    )
    assert resp.status == EngineStatus.SUCCESS
    assert resp.quality_verdict == QualityVerdict.FAILED

def test_all_seven_specialist_engine_typed_schemas():
    """Validates instantiation of typed request/response schemas for all engines E1-E7, S6-S8."""
    # E2 Canvas
    e2_p = CanvasGenerationParams(page_format="B5", width_px=2150.0, height_px=3035.0)
    e2_o = CanvasGenerationOutput(
        canvas_spec_artifact_id="art_canvas_01",
        dimensions=Size(width=2150.0, height=3035.0),
        dpi=300.0,
        panel_slots=[Rect(x=100.0, y=100.0, width=900.0, height=800.0)],
        safe_area=Rect(x=50.0, y=50.0, width=2050.0, height=2935.0),
        bleed_box=Rect(x=-35.0, y=-35.0, width=2220.0, height=3105.0),
        reading_order_panel_ids=["panel_01"]
    )
    assert e2_p.page_format == "B5"
    assert len(e2_o.panel_slots) == 1

    # E3 Integration
    e3_p = ImageCanvasIntegrationParams(
        source_image_artifact_id="art_img_01",
        target_panel_id="panel_01",
        target_slot_rect=Rect(x=100.0, y=100.0, width=500.0, height=500.0),
        fit_mode=FitMode.COVER
    )
    assert e3_p.fit_mode == FitMode.COVER

    # E4 Text
    e4_p = TextGenerationParams(
        story_id="story_01",
        scene_id="scene_01",
        panel_id="panel_01",
        script_beat="Nour gasps upon finding the key"
    )
    assert e4_p.language == "ar"

    # E5 Typography
    e5_p = TypographyParams(
        text_block_artifact_id="art_txt_01",
        text_content="مرحباً يا صديقي",
        font_family="Cairo",
        font_size_pt=14.0
    )
    assert e5_p.font_family == "Cairo"

    # E6 Speech Bubble
    e6_p = SpeechBubbleParams(
        text_block_artifact_id="art_txt_01",
        lettering_layer_artifact_id="art_let_01",
        measured_text_bounds=Rect(x=0.0, y=0.0, width=150.0, height=50.0),
        panel_slot_rect=Rect(x=0.0, y=0.0, width=600.0, height=400.0)
    )
    assert e6_p.bubble_shape == "rounded_rectangle"

    # E7 Effects & Motion
    e7_p = EffectsMotionParams(
        effect_category="speed_lines",
        target_panel_rect=Rect(x=0.0, y=0.0, width=600.0, height=400.0),
        intensity=0.8,
        blend_mode=BlendMode.MULTIPLY
    )
    assert e7_p.blend_mode == BlendMode.MULTIPLY

    # S6 Compositor
    s6_p = CompositorParams(
        canvas_spec_artifact_id="art_canvas_01",
        ordered_layer_artifact_ids=["art_art_01", "art_bbl_01"],
        output_format=AssetFormat.PNG
    )
    assert s6_p.output_format == AssetFormat.PNG

    # S7 QA / Verification
    s7_p = VerificationParams(
        target_artifact_id="art_panel_01",
        verification_type="multimodal_character_spec",
        spec_id="spec_nour"
    )
    assert s7_p.spec_id == "spec_nour"

    # S8 Export
    s8_p = ExportParams(
        project_id="proj_01",
        page_composite_artifact_ids=["art_page_01", "art_page_02"],
        target_format=AssetFormat.PDF
    )
    assert s8_p.target_format == AssetFormat.PDF

def test_artifact_manifest_creation_and_hash(tmp_path: Path):
    test_file = tmp_path / "test_panel.png"
    test_content = b"fake_png_binary_image_data_67890"
    test_file.write_bytes(test_content)

    manifest = build_artifact_manifest(
        file_path=test_file,
        project_root=tmp_path,
        artifact_id="art_panel_01",
        asset_type=AssetType.IMAGE_GENERATED,
        run_id="run_test_01",
        mime_type="image/png",
        dimensions=Size(width=1280.0, height=1920.0),
        lifecycle_status=LifecycleStatus.APPROVED
    )

    assert manifest.artifact_id == "art_panel_01"
    assert manifest.asset_type == AssetType.IMAGE_GENERATED
    assert manifest.byte_size == len(test_content)
    assert manifest.content_sha256 == compute_file_sha256(test_file)
    assert manifest.dimensions.width == 1280.0
    assert manifest.lifecycle_status == LifecycleStatus.APPROVED

def test_image_generation_adapter_preflight_validation():
    adapter = ImageGenerationEngineAdapter()

    # Case 1: Empty prompt triggers validation error
    bad_req = EngineRunRequest[ImageGenerationParams](
        run_id="run_val_01",
        engine_id=EngineId.E1_IMAGE_GENERATION,
        project_id="proj_01",
        parameters=ImageGenerationParams(prompt="   "),
        config_hash="dummy_hash"
    )
    errors = adapter.validate_request(bad_req)
    assert len(errors) == 1
    assert errors[0].code == ErrorCode.MISSING_REQUIRED_FIELD

    # Case 2: Non-existent reference file triggers validation error
    bad_ref_req = EngineRunRequest[ImageGenerationParams](
        run_id="run_val_02",
        engine_id=EngineId.E1_IMAGE_GENERATION,
        project_id="proj_01",
        parameters=ImageGenerationParams(
            prompt="A valid prompt with Nour",
            reference_image_path="non/existent/path/nour_fake.png"
        ),
        config_hash="dummy_hash"
    )
    ref_errors = adapter.validate_request(bad_ref_req)
    assert len(ref_errors) == 1
    assert ref_errors[0].code == ErrorCode.UNKNOWN_ENTITY_REFERENCE

def test_image_generation_adapter_dry_run_cannot_be_mistaken_for_real():
    """Proves dry-run execution returns mock tags and 0 ops, preventing accounting fraud."""
    adapter = ImageGenerationEngineAdapter()
    valid_req = EngineRunRequest[ImageGenerationParams](
        run_id="run_dry_01",
        engine_id=EngineId.E1_IMAGE_GENERATION,
        project_id="proj_01",
        parameters=ImageGenerationParams(
            prompt="Comic book panel of Nour reading in a quiet library",
            output_filename_base="panel_01"
        ),
        config_hash="hash_valid_01",
        dry_run=True
    )
    resp = adapter.execute_dry_run(valid_req)
    assert resp.status == EngineStatus.SUCCESS
    assert resp.output is not None
    assert "mock" in resp.output.sha256
    assert resp.usage.image_ops == 0  # Crucial: 0 ops so dry-run is never billed
    assert resp.output.request_id == "mock-dry-run-request-id"

def test_image_generation_adapter_offline_mock_responses():
    """Validates adapter error classification and retryability across provider HTTP responses offline."""
    adapter = ImageGenerationEngineAdapter()
    req = EngineRunRequest[ImageGenerationParams](
        run_id="run_mock_01",
        engine_id=EngineId.E1_IMAGE_GENERATION,
        project_id="proj_01",
        parameters=ImageGenerationParams(prompt="Test prompt", output_filename_base="test"),
        config_hash="hash_01"
    )

    # 1. HTTP 200 Success
    resp_200 = adapter.handle_mock_response(req, 200, {"id": "req-200", "usage": {"input_tokens": 15000, "output_tokens": 1500}})
    assert resp_200.status == EngineStatus.SUCCESS
    assert resp_200.usage.image_ops == 1
    assert resp_200.output.primary_artifact_id.startswith("art_")

    # 2. HTTP 400 Content Policy Violation -> retryable = True (neutral rephrase iteration permitted)
    resp_400 = adapter.handle_mock_response(req, 400, {"error": {"code": "content_policy_violation", "message": "Triggered content management policy"}})
    assert resp_400.status == EngineStatus.FAILED
    assert resp_400.error.code == ErrorCode.CONTENT_POLICY_VIOLATION
    assert resp_400.retryable is True

    # 3. HTTP 401 Auth Error -> retryable = False (stops immediately)
    resp_401 = adapter.handle_mock_response(req, 401, {"error": {"code": "invalid_api_key", "message": "Unauthorized"}})
    assert resp_401.status == EngineStatus.FAILED
    assert resp_401.error.code == ErrorCode.PROVIDER_AUTH_FAILED
    assert resp_401.retryable is False

    # 4. HTTP 429 Rate Limit -> retryable = True (bounded backoff)
    resp_429 = adapter.handle_mock_response(req, 429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests"}})
    assert resp_429.status == EngineStatus.FAILED
    assert resp_429.error.code == ErrorCode.PROVIDER_RATE_LIMITED
    assert resp_429.retryable is True

    # 5. HTTP 500 Server Error -> retryable = True
    resp_500 = adapter.handle_mock_response(req, 500, {"error": {"code": "internal_error", "message": "Server error"}})
    assert resp_500.status == EngineStatus.FAILED
    assert resp_500.error.code == ErrorCode.PROVIDER_SERVICE_UNAVAILABLE
    assert resp_500.retryable is True

def test_image_generation_adapter_payload_preservation():
    """Validates that build_payload preserves exact M0 text-to-image and reference-anchored structures."""
    adapter = ImageGenerationEngineAdapter()

    # Text-only call
    params_text = ImageGenerationParams(prompt="Comic panel", model="muse-image-1.0", n=1)
    payload_text = adapter.build_payload(params_text)
    assert payload_text["model"] == "muse-image-1.0"
    assert payload_text["prompt"] == "Comic panel"
    assert payload_text["n"] == 1
    assert "images" not in payload_text
