"""The discoverable preset catalogue must map to real, deterministic Canvas behavior."""
from app.canvas.catalogue import (
    BUBBLE_PRESETS,
    PANEL_LAYOUT_PRESETS,
    get_bubble_preset,
    get_panel_layout_preset,
    list_bubble_presets,
    list_panel_layout_presets,
)
from app.canvas.engine import CanvasEngine
from app.canvas.models import CanvasSpec, PageSpec, ReadingDirection
from app.canvas.speech_bubble import SpeechBubbleEngine
from app.canvas.bubble_models import BubbleShape, TailType, BubbleAccent
from app.contracts.geometry import Point, Rect


def test_catalogue_has_100_panel_recipes_and_50_bubble_presets_with_stable_ids():
    assert len(PANEL_LAYOUT_PRESETS) == 100
    assert len({item["id"] for item in PANEL_LAYOUT_PRESETS}) == 100
    assert len(BUBBLE_PRESETS) == 50
    assert len({item["id"] for item in BUBBLE_PRESETS}) == 50
    for item in [*PANEL_LAYOUT_PRESETS, *BUBBLE_PRESETS]:
        assert item["id"]
        assert item["use_case"].strip()
        assert item["pinterest_search_url"].startswith("https://www.pinterest.com/search/pins/")
        assert item["version"] == 1


def test_panel_presets_resolve_search_and_generate_valid_geometry():
    spec = CanvasSpec(
        width_px=900,
        height_px=1200,
        margins={"top": 45, "bottom": 45, "left": 45, "right": 45},
        gutters={"horizontal": 18, "vertical": 18},
    )
    page = PageSpec(page_id="page_catalogue_test", reading_direction=ReadingDirection.RTL)
    results = list_panel_layout_presets("suspense", limit=5)
    assert results
    assert any("suspense" in item["category"].lower() for item in results)
    for preset in PANEL_LAYOUT_PRESETS:
        assert get_panel_layout_preset(preset["id"]) is preset
        layout = CanvasEngine.generate_layout(
            spec,
            page,
            template_id=preset["template_id"],
            **preset["template_parameters"],
        )
        assert layout.panel_slots
        assert len({panel.panel_id for panel in layout.panel_slots}) == len(layout.panel_slots)
        assert layout.reading_order_panel_ids == [panel.panel_id for panel in layout.panel_slots]


def test_bubble_presets_resolve_to_implemented_vector_geometry():
    engine = SpeechBubbleEngine()
    results = list_bubble_presets("whisper secret", limit=5)
    assert results
    assert any(item["shape"] == "whisper_cloud_soft" for item in results)
    for preset in BUBBLE_PRESETS:
        assert get_bubble_preset(preset["id"]) is preset
        geometry = engine.generate_vector_geometry(
            bounds=Rect(x=20, y=30, width=240, height=120),
            shape=BubbleShape(preset["shape"]),
            tail_type=TailType(preset["tail_type"]),
            tail_target=Point(x=130, y=190) if preset["tail_type"] != "none" else None,
            accent=BubbleAccent(preset["accent"]),
            inverted_dark_mode=preset["inverted_dark_mode"],
        )
        assert geometry.bubble_path.startswith("M ")
        assert "nan" not in geometry.bubble_path.lower()
