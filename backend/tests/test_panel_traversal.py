"""Regression test suite for Phase 2: Narrative Planning & Panel Traversal.

Validates that:
1. Standard grid templates (six_panel, four_panel_cinematic, dynamic_shonen) order panels
   monotonically from Left-to-Right under LTR, and Right-to-Left under RTL.
2. Panel boundary clamping gate catches and rejects out-of-bounds geometries.
"""
import pytest
from app.canvas.models import CanvasSpec, PageSpec, ReadingDirection, LayoutTemplateId
from app.canvas.engine import CanvasEngine
from app.contracts.geometry import Rect
from app.agent.registry import CapabilityRegistry, ToolError


def test_six_panel_ltr_vs_rtl_panel_ordering():
    canvas_spec = CanvasSpec(width_px=900, height_px=1200)

    # 1. LTR Generation
    page_ltr = PageSpec(page_id="p_ltr", reading_direction=ReadingDirection.LTR)
    layout_ltr = CanvasEngine.generate_layout(canvas_spec, page_ltr, LayoutTemplateId.SIX_PANEL_CLASSIC)
    p1_ltr = layout_ltr.get_panel("panel_01")
    p2_ltr = layout_ltr.get_panel("panel_02")
    p3_ltr = layout_ltr.get_panel("panel_03")
    p4_ltr = layout_ltr.get_panel("panel_04")

    # In Row 1 under LTR: Panel 1 must be to the LEFT of Panel 2
    assert p1_ltr.rect.x < p2_ltr.rect.x
    assert abs(p1_ltr.rect.y - p2_ltr.rect.y) < 1.0

    # In Row 2 under LTR: Panel 3 must be to the LEFT of Panel 4
    assert p3_ltr.rect.x < p4_ltr.rect.x
    assert p3_ltr.rect.y > p1_ltr.rect.y

    # 2. RTL Generation
    page_rtl = PageSpec(page_id="p_rtl", reading_direction=ReadingDirection.RTL)
    layout_rtl = CanvasEngine.generate_layout(canvas_spec, page_rtl, LayoutTemplateId.SIX_PANEL_CLASSIC)
    p1_rtl = layout_rtl.get_panel("panel_01")
    p2_rtl = layout_rtl.get_panel("panel_02")

    # In Row 1 under RTL: Panel 1 must be to the RIGHT of Panel 2
    assert p1_rtl.rect.x > p2_rtl.rect.x
    assert abs(p1_rtl.rect.y - p2_rtl.rect.y) < 1.0


def test_four_panel_cinematic_ltr_vs_rtl():
    canvas_spec = CanvasSpec(width_px=900, height_px=1200)

    # 1. LTR
    page_ltr = PageSpec(page_id="p_ltr", reading_direction=ReadingDirection.LTR)
    layout_ltr = CanvasEngine.generate_layout(canvas_spec, page_ltr, LayoutTemplateId.FOUR_PANEL_CINEMATIC)
    p1 = layout_ltr.get_panel("panel_01")
    p2 = layout_ltr.get_panel("panel_02")
    p3 = layout_ltr.get_panel("panel_03")
    p4 = layout_ltr.get_panel("panel_04")

    # Tier 1 is top panoramic
    assert p1.rect.y < p2.rect.y
    # Tier 2 under LTR traverses left to right: p2 < p3 < p4
    assert p2.rect.x < p3.rect.x < p4.rect.x

    # 2. RTL
    page_rtl = PageSpec(page_id="p_rtl", reading_direction=ReadingDirection.RTL)
    layout_rtl = CanvasEngine.generate_layout(canvas_spec, page_rtl, LayoutTemplateId.FOUR_PANEL_CINEMATIC)
    p2_r = layout_rtl.get_panel("panel_02")
    p3_r = layout_rtl.get_panel("panel_03")
    p4_r = layout_rtl.get_panel("panel_04")

    # Tier 2 under RTL traverses right to left: p2 > p3 > p4
    assert p2_r.rect.x > p3_r.rect.x > p4_r.rect.x


def test_dynamic_shonen_middle_row_diagonal_ordering():
    canvas_spec = CanvasSpec(width_px=900, height_px=1200)

    # 1. LTR: Panel 2 on left, Panel 3 on right
    page_ltr = PageSpec(page_id="p_ltr", reading_direction=ReadingDirection.LTR)
    layout_ltr = CanvasEngine.generate_layout(canvas_spec, page_ltr, LayoutTemplateId.DYNAMIC_SHONEN)
    p2_ltr = layout_ltr.get_panel("panel_02")
    p3_ltr = layout_ltr.get_panel("panel_03")
    assert p2_ltr.rect.center.x < p3_ltr.rect.center.x

    # 2. RTL: Panel 2 on right, Panel 3 on left
    page_rtl = PageSpec(page_id="p_rtl", reading_direction=ReadingDirection.RTL)
    layout_rtl = CanvasEngine.generate_layout(canvas_spec, page_rtl, LayoutTemplateId.DYNAMIC_SHONEN)
    p2_rtl = layout_rtl.get_panel("panel_02")
    p3_rtl = layout_rtl.get_panel("panel_03")
    assert p2_rtl.rect.center.x > p3_rtl.rect.center.x


def test_panel_boundary_clamping_gate():
    from app.agent.schemas import ToolCall

    registry = CapabilityRegistry()
    create_call = ToolCall(
        call_id="call_create",
        tool_id="canvas.create_page_from_template",
        arguments={
            "layout_template": "six_panel_classic",
            "reading_direction": "ltr",
            "width_px": 900,
            "height_px": 1200,
        },
    )
    res_create = registry.dispatch(create_call, context={})
    assert res_create.status == "success"
    page_id = res_create.output["page_id"]
    rev = res_create.output["revision"]

    # Attempt to reshape panel beyond page boundary (right = 500 + 600 = 1100 > 900)
    reshape_call = ToolCall(
        call_id="call_reshape",
        tool_id="canvas.reshape_panel",
        arguments={
            "page_id": page_id,
            "expected_revision": rev,
            "panel_id": "panel_01",
            "rect": {"x": 500, "y": 100, "width": 600, "height": 300},
        },
    )
    res_reshape = registry.dispatch(reshape_call, context={})
    assert res_reshape.status == "failed"
    assert res_reshape.error_code == "ERR_PANEL_OUT_OF_BOUNDS"
