"""
Tests for InkLoop Canvas Engine Multi-Axis Panel Descriptors.
Validates the six orthogonal axes (Layout, Shape, Boundary, Narrative VNG, Framing, Transitions)
and their attachment to PanelSlot contracts.
"""
import pytest
from app.contracts.geometry import Rect
from app.canvas.models import PanelSlot
from app.canvas.descriptors import (
    LayoutRelation,
    PanelShapeType,
    FrameStyle,
    GutterPolicy,
    PanelBoundaryTreatment,
    VNGRole,
    NarrativePlanningTag,
    PanelNarrativeDescriptor,
    FramingScale,
    CameraAngle,
    SubjectOrientation,
    PanelFramingDescriptor,
    PanelTransitionType,
    MultiAxisPanelDescriptor,
)


def test_multi_axis_panel_descriptor_creation_and_defaults():
    desc = MultiAxisPanelDescriptor(
        panel_id="panel_01",
        reading_order_index=1,
        layout_relation=LayoutRelation.TIERED,
        shape_type=PanelShapeType.HORIZONTAL_RECTANGLE,
        narrative=PanelNarrativeDescriptor(
            vng_role=VNGRole.ESTABLISHER,
            function_tags=[NarrativePlanningTag.ESTABLISHING_SHOT],
            scene_beat_description="Wide panoramic establishing shot of coastal city",
        ),
        framing=PanelFramingDescriptor(
            scale=FramingScale.EXTREME_LONG_SHOT,
            angle=CameraAngle.HIGH_ANGLE,
            orientation=SubjectOrientation.FRONTAL,
        ),
        transition_from_previous=PanelTransitionType.FIRST_PANEL_IN_SCENE,
    )

    assert desc.panel_id == "panel_01"
    assert desc.reading_order_index == 1
    assert desc.layout_relation == LayoutRelation.TIERED
    assert desc.shape_type == PanelShapeType.HORIZONTAL_RECTANGLE
    assert desc.narrative.vng_role == VNGRole.ESTABLISHER
    assert desc.framing.scale == FramingScale.EXTREME_LONG_SHOT
    assert desc.transition_from_previous == PanelTransitionType.FIRST_PANEL_IN_SCENE


def test_inset_panel_requires_parent_panel_id():
    # Attempting to create an INSET panel without parent_panel_id must fail validation
    with pytest.raises(ValueError, match="lacks 'parent_panel_id'"):
        MultiAxisPanelDescriptor(
            panel_id="panel_inset_01",
            reading_order_index=2,
            layout_relation=LayoutRelation.INSET,
            parent_panel_id=None,
        )

    # With declared parent_panel_id, it succeeds
    valid_inset = MultiAxisPanelDescriptor(
        panel_id="panel_inset_01",
        reading_order_index=2,
        layout_relation=LayoutRelation.INSET,
        parent_panel_id="panel_main_01",
        z_index=2,
    )
    assert valid_inset.parent_panel_id == "panel_main_01"
    assert valid_inset.z_index == 2


def test_bleed_panel_boundary_propagation():
    desc = MultiAxisPanelDescriptor(
        panel_id="panel_bleed_01",
        reading_order_index=3,
        layout_relation=LayoutRelation.FULL_PAGE_SPLASH,
        shape_type=PanelShapeType.VERTICAL_RECTANGLE,
        boundary=PanelBoundaryTreatment(
            frame_style=FrameStyle.CLOSED,
            full_bleed=True,
        ),
    )
    # Default bleed edges populated
    assert desc.boundary.full_bleed is True
    assert set(desc.boundary.bleed_edges) == {"top", "bottom", "left", "right"}


def test_panel_slot_attachment_and_backward_compatibility():
    # 1. Plain PanelSlot without descriptor (legacy contract compatibility)
    slot_plain = PanelSlot(
        panel_id="panel_01",
        reading_order=1,
        rect=Rect(x=100.0, y=120.0, width=800.0, height=600.0),
    )
    assert slot_plain.descriptor is None

    # 2. PanelSlot with rich multi-axis descriptor attached
    desc = MultiAxisPanelDescriptor(
        panel_id="panel_02",
        reading_order_index=2,
        layout_relation=LayoutRelation.BLOCKAGE,
        shape_type=PanelShapeType.VERTICAL_RECTANGLE,
        narrative=PanelNarrativeDescriptor(
            vng_role=VNGRole.PEAK,
            function_tags=[NarrativePlanningTag.IMPACT_CONTACT],
        ),
        framing=PanelFramingDescriptor(
            scale=FramingScale.CLOSE_UP,
            angle=CameraAngle.LOW_ANGLE,
        ),
        transition_from_previous=PanelTransitionType.ACTION_TO_ACTION,
    )
    slot_rich = PanelSlot(
        panel_id="panel_02",
        reading_order=2,
        rect=Rect(x=940.0, y=120.0, width=500.0, height=1200.0),
        descriptor=desc,
    )
    assert slot_rich.descriptor is not None
    assert slot_rich.descriptor.layout_relation == LayoutRelation.BLOCKAGE
    assert slot_rich.descriptor.narrative.vng_role == VNGRole.PEAK
