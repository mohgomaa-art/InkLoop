"""
Comprehensive tests for InkLoop Asset Registry & Artifact Store (Milestone 1, Task T5.4).
Validates registration, content validation, path traversal defense, lineage tracking,
deterministic manifest export, and Story Bible AssetRef integration.
"""
import io
import json
from pathlib import Path
import pytest
from PIL import Image

from app.contracts.artifacts import AssetType, LifecycleStatus
from app.project.asset_refs import AssetRef, validate_asset_ref
from app.storage.errors import (
    AssetNotFoundError,
    AssetIntegrityError,
    PathTraversalSecurityError,
    InvalidFileFormatError,
    UnregisteredParentError,
    LineageCycleError,
    DuplicateAssetConflictError,
)
from app.storage.registry import AssetRegistry
from app.storage.models import AssetFilter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def temp_store_root(tmp_path) -> Path:
    """Provides a fresh isolated storage root directory."""
    store_dir = tmp_path / "managed_artifacts"
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir


@pytest.fixture
def registry(temp_store_root) -> AssetRegistry:
    """Provides an initialized AssetRegistry backed by SQLite."""
    reg = AssetRegistry(store_root=temp_store_root)
    yield reg
    reg.close()


def create_sample_png_bytes(width: int = 120, height: int = 80, color: str = "blue") -> bytes:
    """Generates valid PNG image bytes with specified dimensions."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_sample_ttf_bytes() -> bytes:
    """Generates minimal mock TrueType font header bytes."""
    # Standard TrueType magic header: 0x00010000 + 4-byte table count + searchRange + ...
    return b"\x00\x01\x00\x00" + b"\x00\x01" + b"\x00" * 32


def create_sample_pdf_bytes() -> bytes:
    """Generates minimal valid PDF header bytes."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF\n"


# ==============================================================================
# 1. Registration and Content Integrity
# ==============================================================================

def test_valid_image_registration_extracts_dimensions(registry):
    """Proves that a valid PNG is ingested with verified dimensions, byte size, and SHA-256."""
    png_data = create_sample_png_bytes(width=200, height=150, color="red")
    meta = registry.ingest_bytes(
        data=png_data,
        filename="nour_panel_01.png",
        project_id="cairo_chronicles",
        asset_type=AssetType.IMAGE_GENERATED,
        name="Nour Establishing Shot",
        run_id="run_01"
    )

    assert meta.asset_id.startswith("art_")
    assert meta.project_id == "cairo_chronicles"
    assert meta.asset_type == AssetType.IMAGE_GENERATED
    assert meta.mime_type == "image/png"
    assert meta.extension == ".png"
    assert meta.width == 200
    assert meta.height == 150
    assert meta.byte_size == len(png_data)
    assert len(meta.content_sha256) == 64

    # Resolve and verify physical file on disk
    resolved = registry.resolve_asset(meta.asset_id, verify_integrity=True)
    assert resolved.absolute_path.is_file()
    assert resolved.absolute_path.read_bytes() == png_data
    assert resolved.is_verified is True


def test_valid_non_image_artifact_registrations(registry):
    """Proves that font files, PDFs, JSON specs, and SVGs register with type-specific validation."""
    # 1. Font file
    ttf_data = create_sample_ttf_bytes()
    font_meta = registry.ingest_bytes(
        data=ttf_data,
        filename="cairo_bold.ttf",
        project_id="cairo_chronicles",
        asset_type=AssetType.FONT_FILE,
        license_info="SIL OFL 1.1"
    )
    assert font_meta.mime_type == "font/ttf"
    assert font_meta.font_metadata is not None
    assert font_meta.font_metadata.get("format") == "TrueType"

    # 2. PDF export
    pdf_data = create_sample_pdf_bytes()
    pdf_meta = registry.ingest_bytes(
        data=pdf_data,
        filename="issue_01.pdf",
        project_id="cairo_chronicles",
        asset_type=AssetType.EXPORT_PDF
    )
    assert pdf_meta.mime_type == "application/pdf"
    assert pdf_meta.extension == ".pdf"

    # 3. JSON Canvas Spec
    json_data = json.dumps({"panels": [{"id": "p1", "w": 800, "h": 600}]}).encode("utf-8")
    canvas_meta = registry.ingest_bytes(
        data=json_data,
        filename="grid_2x2.json",
        project_id="cairo_chronicles",
        asset_type=AssetType.CANVAS_SPEC
    )
    assert canvas_meta.mime_type == "application/json"

    # 4. SVG Lettering Layer
    svg_data = b'<svg width="100" height="50"><text x="10" y="20">Hello</text></svg>'
    svg_meta = registry.ingest_bytes(
        data=svg_data,
        filename="dialogue_bubble.svg",
        project_id="cairo_chronicles",
        asset_type=AssetType.LETTERING_LAYER
    )
    assert svg_meta.mime_type == "image/svg+xml"


def test_repeated_content_deduplication(registry):
    """Proves identical content bytes do not duplicate files on disk and return matching hashes."""
    png_data = create_sample_png_bytes(width=100, height=100)
    meta1 = registry.ingest_bytes(
        data=png_data,
        filename="first.png",
        project_id="p1",
        asset_type=AssetType.IMAGE_GENERATED,
        asset_id="art_fixed_01"
    )

    # Re-registering identical asset_id with identical bytes succeeds idempotently
    meta2 = registry.ingest_bytes(
        data=png_data,
        filename="second.png",
        project_id="p1",
        asset_type=AssetType.IMAGE_GENERATED,
        asset_id="art_fixed_01"
    )
    assert meta1.content_sha256 == meta2.content_sha256
    assert meta1.managed_path == meta2.managed_path


def test_hash_mismatch_detected_on_corrupted_disk_file(registry):
    """Proves that a tampered file on disk triggers AssetIntegrityError upon resolution."""
    png_data = create_sample_png_bytes(width=100, height=100)
    meta = registry.ingest_bytes(
        data=png_data,
        filename="tamper_target.png",
        project_id="p1",
        asset_type=AssetType.IMAGE_GENERATED
    )

    resolved = registry.resolve_asset(meta.asset_id, verify_integrity=False)
    # Deliberately tamper with the stored file content
    resolved.absolute_path.write_bytes(b"CORRUPTED_TAMPERED_BYTES_12345")

    with pytest.raises(AssetIntegrityError) as exc_info:
        registry.resolve_asset(meta.asset_id, verify_integrity=True)
    assert meta.content_sha256 in str(exc_info.value)


def test_missing_files_produce_explicit_errors(registry, tmp_path):
    """Proves that registering a non-existent file produces AssetNotFoundError."""
    ghost_file = tmp_path / "does_not_exist.png"
    with pytest.raises(AssetNotFoundError):
        registry.register_file(
            file_path=ghost_file,
            project_id="p1",
            asset_type=AssetType.IMAGE_GENERATED
        )


def test_prohibited_and_mislabeled_file_types_rejected(registry):
    """Proves that executable payloads or mislabeled extensions are rejected by content validation."""
    # 1. Prohibited extension
    with pytest.raises(InvalidFileFormatError) as exc:
        registry.ingest_bytes(
            data=b"echo 'malicious'",
            filename="hack.sh",
            project_id="p1",
            asset_type=AssetType.GENERIC_ARTIFACT
        )
    assert "PROHIBITED_EXECUTABLE_EXTENSION" in str(exc.value)

    # 2. Text disguised as PNG image
    with pytest.raises(InvalidFileFormatError) as exc:
        registry.ingest_bytes(
            data=b"THIS IS NOT A PNG FILE AT ALL",
            filename="fake_image.png",
            project_id="p1",
            asset_type=AssetType.IMAGE_GENERATED
        )
    assert "INVALID_IMAGE_HEADER" in str(exc.value)

    # 3. SVG with malicious script injection
    with pytest.raises(InvalidFileFormatError) as exc:
        registry.ingest_bytes(
            data=b'<svg><script>alert("xss")</script></svg>',
            filename="injected.svg",
            project_id="p1",
            asset_type=AssetType.LETTERING_LAYER
        )
    assert "PROHIBITED_SVG_SCRIPT_TAG" in str(exc.value)


# ==============================================================================
# 2. Storage Safety and Path Traversal
# ==============================================================================

def test_path_traversal_attempts_rejected(registry):
    """Proves that path traversal characters in relative paths fail security assertions."""
    with pytest.raises(PathTraversalSecurityError):
        registry.store.resolve_managed_path("../../etc/passwd", verify_exists=False)

    with pytest.raises(PathTraversalSecurityError):
        registry.store.resolve_managed_path("/root/secrets.txt", verify_exists=False)


def test_unsafe_filenames_cannot_control_destination(registry):
    """Proves that content-addressed storage sanitizes filenames and places files solely by hash."""
    png_data = create_sample_png_bytes()
    meta = registry.ingest_bytes(
        data=png_data,
        filename="../../escape_attempt.png",
        project_id="p1",
        asset_type=AssetType.IMAGE_GENERATED
    )

    resolved = registry.resolve_asset(meta.asset_id)
    # The file is stored within objects/<hash_prefix>/... strictly inside managed root
    assert registry.store_root in resolved.absolute_path.parents
    assert "escape_attempt" not in str(resolved.absolute_path)


def test_no_secrets_in_metadata_or_logs(registry):
    """Proves that metadata serialization contains no API keys or credentials."""
    png_data = create_sample_png_bytes()
    meta = registry.ingest_bytes(
        data=png_data,
        filename="clean_meta.png",
        project_id="p1",
        asset_type=AssetType.IMAGE_GENERATED,
        source_origin="Generated via Muse Image",
        license_info="Proprietary",
        extra_metadata={"camera_angle": "low_angle"}
    )
    json_dump = meta.model_dump_json()
    assert "api_key" not in json_dump.lower()
    assert "bearer" not in json_dump.lower()
    assert "model_api_key" not in json_dump.lower()


# ==============================================================================
# 3. Lineage and Deterministic Manifests
# ==============================================================================

def test_derivatives_preserve_parent_references_and_lineage_graph(registry):
    """Proves that derivative artifacts preserve parent links, lineage operation, and engine config."""
    # 1. Base generated image
    raw_panel = create_sample_png_bytes(width=800, height=800, color="green")
    parent_meta = registry.ingest_bytes(
        data=raw_panel,
        filename="raw_panel.png",
        project_id="p1",
        asset_type=AssetType.IMAGE_GENERATED,
        name="Raw Generated Panel",
        run_id="run_01"
    )

    # 2. Derivative cropped panel layer
    cropped_bytes = create_sample_png_bytes(width=600, height=600, color="green")
    child_meta = registry.register_derivative(
        parent_asset_ids=[parent_meta.asset_id],
        file_path_or_bytes=cropped_bytes,
        filename="cropped_panel.png",
        project_id="p1",
        asset_type=AssetType.PANEL_LAYER,
        lineage_operation="contain_crop",
        lineage_params={"target_slot": "slot_01", "crop_box": [100, 100, 700, 700]},
        run_id="run_01",
        engine_id="E3_INTEGRATION",
        engine_version="1.0.0"
    )

    assert child_meta.asset_id != parent_meta.asset_id
    assert child_meta.parent_asset_ids == [parent_meta.asset_id]
    assert child_meta.lineage_operation == "contain_crop"
    assert child_meta.lineage_params["target_slot"] == "slot_01"

    # Parent remains unchanged
    parent_after = registry.get_asset(parent_meta.asset_id)
    assert parent_after.content_sha256 == parent_meta.content_sha256

    # Lineage traversal
    children = registry.list_children(parent_meta.asset_id)
    assert len(children) == 1
    assert children[0].asset_id == child_meta.asset_id

    parents = registry.list_parents(child_meta.asset_id)
    assert len(parents) == 1
    assert parents[0].asset_id == parent_meta.asset_id


def test_unregistered_parent_raises_error(registry):
    """Proves that registering a derivative with non-existent parent IDs fails with UnregisteredParentError."""
    with pytest.raises(UnregisteredParentError):
        registry.register_derivative(
            parent_asset_ids=["art_ghost_nonexistent_99"],
            file_path_or_bytes=create_sample_png_bytes(),
            filename="orphan.png",
            project_id="p1",
            asset_type=AssetType.PANEL_LAYER,
            lineage_operation="crop"
        )


def test_lineage_cycle_detection(registry):
    """Proves that circular dependencies in artifact lineage are caught and rejected."""
    # Parent A
    a_bytes = create_sample_png_bytes(10, 10, "black")
    a_meta = registry.ingest_bytes(a_bytes, "a.png", "p1", AssetType.IMAGE_GENERATED, asset_id="art_a_001")

    # Child B derived from A
    b_bytes = create_sample_png_bytes(10, 10, "white")
    b_meta = registry.register_derivative(
        parent_asset_ids=[a_meta.asset_id],
        file_path_or_bytes=b_bytes,
        filename="b.png",
        project_id="p1",
        asset_type=AssetType.PANEL_LAYER,
        lineage_operation="invert"
    )

    # Attempting to make A a child of B (cycle: A -> B -> A) must be rejected
    assert registry.db.check_cycle("art_a_001", [b_meta.asset_id]) is True


def test_deterministic_manifest_export(registry):
    """Proves that export_manifest outputs deterministic content hashes without binary data."""
    png1 = create_sample_png_bytes(50, 50, "yellow")
    png2 = create_sample_png_bytes(60, 60, "purple")

    a1 = registry.ingest_bytes(png1, "p1.png", "proj_manifest_test", AssetType.IMAGE_GENERATED)
    a2 = registry.ingest_bytes(png2, "p2.png", "proj_manifest_test", AssetType.IMAGE_GENERATED)

    manifest_1 = registry.export_manifest("proj_manifest_test")
    manifest_2 = registry.export_manifest("proj_manifest_test")

    # Hashes are deterministic and identical across repeated calls
    assert manifest_1.manifest_sha256 == manifest_2.manifest_sha256
    assert len(manifest_1.manifest_sha256) == 64
    assert manifest_1.asset_count == 2

    # Manifest JSON has zero binary payloads
    dumped = manifest_1.model_dump_json()
    assert "data:image" not in dumped
    assert ";base64," not in dumped


# ==============================================================================
# 4. Story Bible and AssetRef Integration
# ==============================================================================

def test_story_bible_asset_ref_integration(registry):
    """
    Proves that the real M0 Nour reference image integrates cleanly:
    1. Resolves existing AssetRef.
    2. Imports AssetRef into managed content-addressed registry.
    3. Exports AssetMetadata back into valid AssetRef matching Story Bible checks.
    """
    nour_rel_path = "runs/m0_visual/reference/nour_reference.png"
    nour_abs_path = PROJECT_ROOT / nour_rel_path
    assert nour_abs_path.is_file(), "M0 Nour reference file must exist on disk"

    # Create AssetRef using real Nour reference
    expected_hash = "b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644"
    ref = AssetRef(
        asset_id="nour_anchor_asset",
        path=nour_rel_path,
        asset_type="character_sheet",
        expected_hash=expected_hash,
        mime_type="image/png"
    )

    # 1. Resolve AssetRef directly
    resolved_path = registry.resolve_asset_ref(ref, source_root=PROJECT_ROOT)
    assert resolved_path.is_file()

    # 2. Ingest AssetRef into managed registry
    meta = registry.register_from_asset_ref(
        ref=ref,
        project_id="inkloop_m0_nour",
        base_dir=PROJECT_ROOT
    )
    assert meta.asset_id == "nour_anchor_asset"
    assert meta.content_sha256 == expected_hash
    assert meta.asset_type == AssetType.IMAGE_REFERENCE
    assert meta.width is not None and meta.height is not None

    # 3. Convert back to AssetRef and validate with existing Story Bible validator
    exported_ref = meta.to_asset_ref()
    assert exported_ref.asset_id == "nour_anchor_asset"
    assert exported_ref.expected_hash == expected_hash

    # Validate exported ref against registry store root
    validated_path = validate_asset_ref(exported_ref, project_root=registry.store_root, verify_hash=True)
    assert validated_path.is_file()


def test_story_bible_state_operations_do_not_mutate_asset_registry(registry, tmp_path):
    """Proves that narrative state events and Story Bible saves do not mutate registered assets."""
    from app.project.bible import create_canonical_nour_bible, append_state_event, save_bible
    from app.project.story_state import StoryStateEvent

    # Register anchor
    nour_ref = AssetRef(
        asset_id="nour_anchor",
        path="runs/m0_visual/reference/nour_reference.png",
        asset_type="character_sheet",
        expected_hash="b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644",
        mime_type="image/png"
    )
    reg_meta = registry.register_from_asset_ref(nour_ref, project_id="story_iso_test", base_dir=PROJECT_ROOT)
    initial_hash = reg_meta.content_sha256

    # Run Story Bible operations
    bible = create_canonical_nour_bible(project_root=PROJECT_ROOT, project_id="story_iso_test")
    save_bible(bible, target_path=tmp_path)

    event = StoryStateEvent(
        event_id="evt_test",
        sequence_number=1,
        scene_id="s1",
        panel_id="p1",
        entity_type="character",
        entity_id="nour",
        property_path="location",
        new_value="market",
        timestamp="2026-10-29T00:00:00Z"
    )
    append_state_event(tmp_path, event)

    # Re-query registry: asset is 100% untouched
    after_meta = registry.get_asset(reg_meta.asset_id)
    assert after_meta.content_sha256 == initial_hash
    assert registry.verify_asset(reg_meta.asset_id) is True


# ==============================================================================
# 5. Persistence and Restart Reproducibility
# ==============================================================================

def test_registry_persistence_survives_process_restart(temp_store_root):
    """Proves that metadata, lineage, and file resolution survive closing and reopening the registry."""
    png_data = create_sample_png_bytes(150, 75, "cyan")

    # Session 1: Register and close
    reg1 = AssetRegistry(store_root=temp_store_root)
    meta = reg1.ingest_bytes(
        data=png_data,
        filename="persistent_panel.png",
        project_id="restart_project",
        asset_type=AssetType.IMAGE_GENERATED,
        name="Session 1 Panel"
    )
    asset_id = meta.asset_id
    stored_hash = meta.content_sha256
    reg1.close()

    # Session 2: Reopen registry pointing to same store and DB
    reg2 = AssetRegistry(store_root=temp_store_root)
    reloaded_meta = reg2.get_asset(asset_id)
    assert reloaded_meta is not None
    assert reloaded_meta.asset_id == asset_id
    assert reloaded_meta.content_sha256 == stored_hash
    assert reloaded_meta.width == 150
    assert reloaded_meta.height == 75

    # Verification on disk still succeeds
    resolved = reg2.resolve_asset(asset_id, verify_integrity=True)
    assert resolved.absolute_path.read_bytes() == png_data
    assert resolved.is_verified is True
    reg2.close()
