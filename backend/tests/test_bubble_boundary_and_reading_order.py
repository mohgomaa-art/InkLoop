import pytest
from types import SimpleNamespace
from app.contracts.geometry import Rect, Point
from app.canvas.character_locator import calculate_safe_bubble_placement
from app.canvas.placement_engine import PlacementEngine, BubblePlacementRequest
from app.agent.registry import CapabilityRegistry
from app.agent.story_to_canvas import StoryToCanvasWorkflow
from app.agent.production import StoryProductionJob, PageProduction, PanelProduction
from app.editor.models import EditablePageDocument, LayerKind
from app.editor.store import PageDocumentStore
from app.storage.registry import AssetRegistry
from app.canvas.models import CanvasSpec, PageSpec, LayoutTemplateId
from app.canvas.engine import CanvasEngine


def test_bubble_strictly_contained_within_panel_rect():
    """Verify that bubble placement on a lower panel (like Panel 6) never escapes into the upper panel."""
    page_trim = Rect(x=48.0, y=49.0, width=720.0, height=1106.0)
    panel_5_rect = Rect(x=48.0, y=675.62, width=720.0, height=273.45)
    panel_6_rect = Rect(x=48.0, y=969.05, width=720.0, height=185.95)

    char_in_panel_6 = Rect(x=150.0, y=975.0, width=200.0, height=160.0)
    bubble_w, bubble_h = 180.0, 50.0

    pos, tail = calculate_safe_bubble_placement(
        panel_rect=panel_6_rect,
        bubble_w=bubble_w,
        bubble_h=bubble_h,
        character_bounds=char_in_panel_6,
        page_trim=page_trim,
    )

    # Bubble must be strictly inside panel 6 boundaries (with max 4px gutter tolerance)
    assert pos.y >= panel_6_rect.y - 4.0, f"pos.y {pos.y} bled into Panel 5 (panel_5 bottom={panel_5_rect.bottom})"
    assert pos.y + bubble_h <= panel_6_rect.bottom + 4.0
    assert pos.x >= panel_6_rect.x - 4.0
    assert pos.x + bubble_w <= panel_6_rect.right + 4.0

    # Bubble must never collide with Panel 5
    bubble_rect = Rect(x=pos.x, y=pos.y, width=bubble_w, height=bubble_h)
    assert bubble_rect.y >= panel_5_rect.bottom, "Bubble penetrated Panel 5's artwork area!"


def test_conversational_reading_order_ltr_staggering():
    """Verify that in LTR, Turn 1 is placed left of Turn 2 (or higher), never inverted."""
    engine = PlacementEngine()
    panel_rect = Rect(x=48.0, y=969.05, width=720.0, height=185.95)
    page_trim = Rect(x=48.0, y=49.0, width=720.0, height=1106.0)

    reqs = [
        BubblePlacementRequest(
            bubble_id="b1",
            type_id="speech.normal",
            text="Tomorrow, we explore?",
            reading_order=1,
            speaker_character_id="char_muse",
        ),
        BubblePlacementRequest(
            bubble_id="b2",
            type_id="speech.normal",
            text="Tomorrow.",
            reading_order=2,
            speaker_character_id="char_gomaa",
        ),
    ]

    results = engine.place_bubbles(
        panel_rect=panel_rect,
        bubbles=reqs,
        protected_regions=[],
        reading_direction="ltr",
        page_safe_margin=page_trim,
        allow_gutter_bleed=True,
    )

    assert len(results) == 2
    r1, r2 = results[0], results[1]

    # Verify both bubbles remain strictly inside panel 6 bounds
    for r in (r1, r2):
        assert r.rect.y >= panel_rect.y - 4.0
        assert r.rect.bottom <= panel_rect.bottom + 4.0

    # Monotonic reading order check: Turn 1 must be read before Turn 2 in LTR
    # Either Turn 1 is higher (r1.rect.y < r2.rect.y - 10) OR Turn 1 is to the left (r1.rect.x < r2.rect.x)
    is_correct_order = (r1.rect.y < r2.rect.y - 10.0) or (r1.rect.x < r2.rect.x)
    assert is_correct_order, f"Reading order inverted! Turn 1 at ({r1.rect.x}, {r1.rect.y}), Turn 2 at ({r2.rect.x}, {r2.rect.y})"


def test_story_to_canvas_page_store_and_logger(tmp_path):
    """Verify that StoryToCanvasWorkflow._page_store works without crashing with NameError or AttributeError."""
    registry = CapabilityRegistry.get_instance()
    asset_reg = AssetRegistry(tmp_path / "assets.db", tmp_path / "artifacts")
    doc_store = PageDocumentStore(tmp_path / "pages.db", asset_reg)

    canvas = CanvasSpec.create_a4(dpi=96.0)
    layout = CanvasEngine.generate_layout(canvas, PageSpec(page_id="page_test_store"), LayoutTemplateId.SIX_PANEL_CLASSIC)
    doc = EditablePageDocument(page_id="page_test_store", project_id="proj_test", layout=layout)
    doc_store.create(doc)

    orig_editor_page = registry._editor_page
    registry._editor_page = lambda pid, ctx: (doc_store, doc_store.get(pid))

    try:
        wf = object.__new__(StoryToCanvasWorkflow)
        wf.project_id = "proj_test"
        wf.registry = registry
        store = wf._page_store("page_test_store")
        assert store is not None
        fetched_doc = wf._page_document("page_test_store")
        assert fetched_doc.page_id == "page_test_store"
    finally:
        registry._editor_page = orig_editor_page


def test_multi_character_facial_clearance_and_balanced_distribution():
    """Verify multi-character panels distribute bubbles without cramming to the left or occluding faces."""
    from app.canvas.placement_engine import ProtectedRegion, _rect_intersects
    engine = PlacementEngine()

    # 1. Panel 5 test: Muse on left, Gomaa in center
    p5_rect = Rect(x=45.0, y=675.6, width=810.0, height=273.5)
    gomaa_head_p5 = ProtectedRegion(x=340.0, y=700.0, width=190.0, height=120.0, label="face", character_id="char_gomaa")
    p5_protected = [gomaa_head_p5]

    reqs_p5 = [
        BubblePlacementRequest(
            bubble_id="b1",
            type_id="speech.normal",
            text="Then let's make something fun!",
            reading_order=1,
            speaker_character_id="char_muse",
            speaker_anchor=Point(x=200.0, y=860.0),
        ),
        BubblePlacementRequest(
            bubble_id="b2",
            type_id="speech.normal",
            text="You know what? Deal.",
            reading_order=2,
            speaker_character_id="char_gomaa",
            speaker_anchor=Point(x=440.0, y=760.0),
        ),
    ]

    res_p5 = engine.place_bubbles(p5_rect, reqs_p5, p5_protected, "ltr", allow_gutter_bleed=False)
    assert len(res_p5) == 2
    # Zero collision with Gomaa's head
    for r in res_p5:
        collides = _rect_intersects(r.rect.x, r.rect.y, r.rect.width, r.rect.height,
                                    gomaa_head_p5.x, gomaa_head_p5.y, gomaa_head_p5.width, gomaa_head_p5.height, margin=4.0)
        assert not collides, f"Bubble {r.bubble_id} occludes character head!"

    # Bubble 1 on left, Bubble 2 on right
    assert res_p5[0].rect.right <= gomaa_head_p5.x + 10.0
    assert res_p5[1].rect.x >= gomaa_head_p5.right - 10.0

    # 2. Panel 6 test: Gomaa on left, Muse at bottom center
    p6_rect = Rect(x=45.0, y=969.1, width=810.0, height=185.9)
    gomaa_head_p6 = ProtectedRegion(x=250.0, y=985.0, width=80.0, height=75.0, label="face", character_id="char_gomaa")
    p6_protected = [gomaa_head_p6]

    reqs_p6 = [
        BubblePlacementRequest(
            bubble_id="b1",
            type_id="speech.normal",
            text="Tomorrow, we explore?",
            reading_order=1,
            speaker_character_id="char_muse",
            speaker_anchor=Point(x=491.0, y=1130.0),
        ),
        BubblePlacementRequest(
            bubble_id="b2",
            type_id="speech.normal",
            text="Tomorrow.",
            reading_order=2,
            speaker_character_id="char_gomaa",
            speaker_anchor=Point(x=280.0, y=1025.0),
        ),
    ]

    res_p6 = engine.place_bubbles(p6_rect, reqs_p6, p6_protected, "ltr", allow_gutter_bleed=False)
    assert len(res_p6) == 2
    # Zero collision with Gomaa's head
    for r in res_p6:
        collides = _rect_intersects(r.rect.x, r.rect.y, r.rect.width, r.rect.height,
                                    gomaa_head_p6.x, gomaa_head_p6.y, gomaa_head_p6.width, gomaa_head_p6.height, margin=4.0)
        assert not collides, f"Bubble {r.bubble_id} in Panel 6 occludes character head!"

    # Muse's bubble is placed centrally near Muse (x between 320 and 500)
    assert 320.0 <= res_p6[0].rect.x <= 500.0, f"Muse's bubble not placed near Muse: x={res_p6[0].rect.x}"
    # Gomaa's bubble is placed to his left off his face
    assert res_p6[1].rect.right <= gomaa_head_p6.x + 10.0, f"Gomaa's bubble not placed cleanly off his face: x={res_p6[1].rect.x}"
    # Reading order: Turn 1 (Muse) is higher than Turn 2 (Gomaa)
    assert res_p6[0].rect.y < res_p6[1].rect.y - 10.0, "Conversational reading hierarchy violated in Panel 6!"
    # Tail direction: Muse's tail points towards Muse (x approx 480-500), never in empty right corner (x > 650)
    assert res_p6[0].tail_target is not None
    assert 460.0 <= res_p6[0].tail_target.x <= 510.0, f"Muse's tail target displaced to empty space: {res_p6[0].tail_target.x}"
    assert res_p6[0].tail_target.x < 650.0, "Muse's tail must not point into empty right corner!"

