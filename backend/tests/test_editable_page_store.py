from app.canvas.engine import CanvasEngine
from app.canvas.models import CanvasSpec, PageSpec, LayoutTemplateId
from app.editor.models import EditablePageDocument
from app.editor.store import PageDocumentStore, PageRevisionConflict
from app.storage.registry import AssetRegistry
from app.image_canvas.models import PlacementSpec
from app.image_canvas.engine import ImageCanvasIntegrationEngine
from app.contracts.geometry import Transform2D
from app.canvas.models import PanelSlot
from app.contracts.geometry import Rect
from PIL import Image
from io import BytesIO
import pytest


def make_doc():
    canvas = CanvasSpec.create_webtoon(width_px=600, height_px=900, dpi=96)
    layout = CanvasEngine.generate_layout(canvas, PageSpec(page_id="page_editor_test"), LayoutTemplateId.MANGA_GRID)
    return EditablePageDocument(page_id="page_editor_test", project_id="project_editor_test", layout=layout)


def test_page_revisions_are_immutable_and_optimistic(tmp_path):
    registry = AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")
    store = PageDocumentStore(tmp_path / "pages.sqlite", registry)
    created = store.create(make_doc())
    assert created.revision == 1
    first_artifact = store.revisions(created.page_id)[0]["artifact_id"]

    edited = store.get(created.page_id)
    edited.layout.panel_slots[0].rect.x += 2
    saved = store.save(created.page_id, 1, edited)
    assert saved.revision == 2
    assert store.get(created.page_id).layout.panel_slots[0].rect.x == edited.layout.panel_slots[0].rect.x
    revisions = store.revisions(created.page_id)
    assert [item["revision"] for item in revisions] == [2, 1]
    assert revisions[1]["artifact_id"] == first_artifact

    stale = store.get(created.page_id)
    try:
        store.save(created.page_id, 1, stale)
    except PageRevisionConflict as exc:
        assert exc.current_revision == 2
    else:
        raise AssertionError("stale page save should conflict")

    restored = store.restore(created.page_id, 2, 1)
    assert restored.revision == 3
    assert store.get(created.page_id).layout.panel_slots[0].rect.x == make_doc().layout.panel_slots[0].rect.x
    assert [item["revision"] for item in store.revisions(created.page_id)] == [3, 2, 1]


def test_page_list_is_newest_first_and_delete_retains_revisions(tmp_path):
    registry = AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")
    store = PageDocumentStore(tmp_path / "pages.sqlite", registry)
    first = make_doc()
    store.create(first)
    second = make_doc()
    second.page_id = "page_editor_newer"
    store.create(second)
    listed = store.list_pages("project_editor_test")
    assert [item["page_id"] for item in listed] == ["page_editor_newer", "page_editor_test"]
    retained_revisions = store.revisions("page_editor_test")
    store.delete("page_editor_test")
    assert [item["page_id"] for item in store.list_pages("project_editor_test")] == ["page_editor_newer"]
    assert store.revisions("page_editor_test") == retained_revisions
    store.restore_deleted("page_editor_test")
    assert {item["page_id"] for item in store.list_pages("project_editor_test")} == {"page_editor_test", "page_editor_newer"}


def test_e3_manual_transform_moves_derived_art_only(tmp_path):
    source = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for y in range(8, 24):
        for x in range(4, 12):
            source.putpixel((x, y), (10, 20, 30, 255))
    buffer = BytesIO(); source.save(buffer, format="PNG"); source_bytes = buffer.getvalue()
    original_hash = __import__("hashlib").sha256(source_bytes).hexdigest()
    slot = PanelSlot(panel_id="panel_transform", reading_order=1, rect=Rect(x=0, y=0, width=32, height=32))
    layer = ImageCanvasIntegrationEngine.place_artwork_in_slot(
        slot,
        PlacementSpec(target_panel_id=slot.panel_id, source_image_bytes=source_bytes,
                      manual_transform=Transform2D(translate_x=10, scale_x=1, scale_y=1)),
    )
    output = Image.open(BytesIO(layer.output_image_bytes))
    alpha = output.getchannel("A")
    assert alpha.getbbox()[0] >= 13
    assert layer.source_content_hash == original_hash
    assert layer.manual_transform_applied.translate_x == 10
    assert __import__("hashlib").sha256(source_bytes).hexdigest() == original_hash


def test_editor_image_layer_rejects_stretch_and_distorted_scale():
    from pydantic import ValidationError
    from app.editor.models import EditorLayer, LayerKind
    with pytest.raises(ValidationError, match="Input should be 'cover' or 'contain'"):
        EditorLayer(
            layer_id="image_stretched",
            kind=LayerKind.IMAGE,
            label="stretched",
            panel_id="panel_01",
            source_asset_id="art_source",
            fit_mode="stretch",
        )
    with pytest.raises(ValidationError, match="preserve aspect ratio"):
        EditorLayer(
            layer_id="image_distorted",
            kind=LayerKind.IMAGE,
            label="distorted",
            panel_id="panel_01",
            source_asset_id="art_source",
            transform=Transform2D(scale_x=1.4, scale_y=0.7),
        )


def test_text_and_line_layers_validate_required_editor_properties():
    from pydantic import ValidationError
    from app.editor.models import EditorLayer, LayerKind
    with pytest.raises(ValidationError, match="non-empty metadata.text"):
        EditorLayer(layer_id="txt_missing", kind=LayerKind.TEXT, label="Text", metadata={})
    with pytest.raises(ValidationError, match="metadata.stroke_width"):
        EditorLayer(layer_id="line_missing", kind=LayerKind.LINE, label="Line", metadata={"x1": 0, "y1": 0, "x2": 10, "y2": 10})


def test_agent_page_editor_adds_and_updates_text_and_line_layers(tmp_path, monkeypatch):
    from app.agent.registry import CapabilityRegistry
    from app.api.routers import assets as asset_router, editor as editor_router
    from app.contracts.artifacts import AssetType

    assets = AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")
    store = PageDocumentStore(tmp_path / "pages.sqlite", assets)
    created = store.create(make_doc())
    panel_id = created.layout.panel_slots[0].panel_id
    monkeypatch.setattr(asset_router, "get_registry", lambda: assets)
    monkeypatch.setattr(editor_router, "get_page_store", lambda: store)
    agent = CapabilityRegistry.get_instance()
    context = {"project_id": "project_editor_test"}
    font = assets.ingest_bytes(
        data=b"\x00\x01\x00\x00test-font-binary", filename="CreatorFont.ttf",
        project_id="project_editor_test", asset_type=AssetType.FONT_FILE,
    )

    text = agent._editor_add_text_adapter({
        "page_id": "page_editor_test", "expected_revision": 1, "panel_id": panel_id,
        "text": "Hello", "font_asset_id": font.asset_id, "font_size": 24, "direction": "ltr",
    }, context)
    assert text["revision"] == 2
    assert store.get("page_editor_test").layers[-1].metadata["font_family"] == "CreatorFont"
    assert store.get("page_editor_test").layers[-1].metadata["font_asset_id"] == font.asset_id

    line = agent._editor_add_line_adapter({
        "page_id": "page_editor_test", "expected_revision": 2, "panel_id": panel_id,
        "x1": 10, "y1": 10, "x2": 80, "y2": 20, "stroke_width": 2,
    }, context)
    assert line["revision"] == 3
    updated = agent._editor_update_vector_adapter({
        "page_id": "page_editor_test", "expected_revision": 3, "layer_id": text["layer_id"],
        "properties": {"text": "مرحبا", "font_family": "Noto Naskh Arabic", "direction": "rtl"},
    }, context)
    assert updated["revision"] == 4
    assert updated["metadata"]["text"] == "مرحبا"
    assert updated["metadata"]["direction"] == "rtl"

    removed = agent._editor_remove_layer_adapter({
        "page_id": "page_editor_test", "expected_revision": 4, "layer_id": line["layer_id"],
    }, context)
    assert removed["revision"] == 5
    assert not any(layer.layer_id == line["layer_id"] for layer in store.get("page_editor_test").layers)


def test_compositor_renders_page_document(tmp_path):
    from pathlib import Path
    from app.canvas.compositor import FinalCompositor
    from app.export.delivery import ExportDeliveryEngine
    from app.contracts.engine import ExportParams
    from app.contracts.geometry import AssetFormat
    from app.editor.models import EditorLayer, LayerKind

    registry = AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")
    store = PageDocumentStore(tmp_path / "pages.sqlite", registry)
    doc = make_doc()

    # Ingest a mock artwork image
    img = Image.new("RGBA", (400, 300), (100, 150, 200, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    from app.contracts.artifacts import AssetType
    art_asset = registry.ingest_bytes(buf.getvalue(), "panel_art.png", "project_editor_test", AssetType.GENERIC_ARTIFACT)

    panel_id = doc.layout.panel_slots[0].panel_id
    doc.layers.append(
        EditorLayer(
            layer_id="layer_img_01",
            kind=LayerKind.IMAGE,
            label="Panel Image",
            panel_id=panel_id,
            source_asset_id=art_asset.asset_id,
            fit_mode="cover",
        )
    )
    doc.layers.append(
        EditorLayer(
            layer_id="layer_txt_01",
            kind=LayerKind.TEXT,
            label="Dialogue Bubble",
            panel_id=panel_id,
            metadata={
                "text": "مرحباً يا بطل!",
                "x": 50,
                "y": 60,
                "width": 180,
                "height": 70,
                "font_size": 18,
                "bubble_shape": "rounded_rectangle",
                "tail_x": 120,
                "tail_y": 160,
            },
        )
    )

    created = store.create(doc)
    compositor = FinalCompositor(output_dir=tmp_path / "composites")
    comp_output = compositor.composite_page_document(created, registry)

    assert comp_output.composite_page_artifact_id is not None
    assert comp_output.dimensions.width == 600
    assert comp_output.dimensions.height == 900
    assert Path(comp_output.output_file_path).exists()
    assert comp_output.layer_count >= 2

    # Verify ExportDeliveryEngine can produce PDF from composite
    export_engine = ExportDeliveryEngine(export_dir=tmp_path / "exports")
    exp_output = export_engine.export_delivery(
        ExportParams(
            project_id="project_editor_test",
            page_composite_artifact_ids=[comp_output.composite_page_artifact_id],
            target_format=AssetFormat.PDF,
        ),
        asset_registry=registry,
        reading_direction="rtl",
    )
    assert exp_output.export_artifact_id is not None
    assert Path(exp_output.file_path).exists()
    assert Path(exp_output.file_path).suffix == ".pdf"

