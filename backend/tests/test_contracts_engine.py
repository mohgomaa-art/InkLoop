"""
Unit tests for InkLoop Engine Execution, Artifact Manifests, and Adapter Contracts.
"""
import json
from pathlib import Path
import pytest
from app.contracts.engine import (
    EngineId,
    EngineStatus,
    UsageMetrics,
    ProvenanceRecord,
    EngineRunRequest,
    EngineRunResponse,
)
from app.contracts.artifacts import (
    AssetType,
    LifecycleStatus,
    ArtifactManifest,
    compute_file_sha256,
    build_artifact_manifest,
)
from app.contracts.geometry import Size
from app.contracts.errors import ErrorCode
from app.contracts.adapters.image_generation import (
    ImageGenerationParams,
    ImageGenerationOutput,
    ImageGenerationEngineAdapter,
)

def test_engine_run_request_and_response_roundtrip():
    req = EngineRunRequest[dict](
        run_id="run_20261029_001",
        attempt_id="att_01",
        engine_id=EngineId.E2_CANVAS_GENERATION,
        engine_version="1.0.0",
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
        status=EngineStatus.SUCCESS,
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
    assert restored_resp.usage.compute_seconds == 0.25

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

def test_image_generation_adapter_dry_run():
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
    assert resp.output.dimensions.width == 1280.0
    assert resp.output.dimensions.height == 1920.0
    assert resp.output.is_reference_anchored is False
    assert len(resp.output_artifact_ids) == 1
