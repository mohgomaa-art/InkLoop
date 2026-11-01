"""Acceptance tests for S5 story-beat planning and S5-to-E2 annotation."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.server import app
from app.canvas.engine import CanvasEngine
from app.canvas.models import CanvasSpec, LayoutTemplateId, PageSpec, ReadingDirection
from app.contracts.geometry import Rect
from app.planning.panel_planner import (
    NarrativeBeat,
    PanelPlanningRequest,
    PanelTextPlan,
    TextCarrier,
    TextContentKind,
    TextRegion,
    plan_panels,
    attach_panel_plans,
)
from app.canvas.descriptors import NarrativeFunction, ShotType
from app.context_builder import build_panel_context_packet
from app.schemas import SceneSpec
from tests.fixtures.benchmark_fixtures import CANONICAL_M0_STORY_BIBLE


def beat(beat_id, function, focus, **overrides):
    function = NarrativeFunction(function)
    data = {
        "beat_id": beat_id,
        "narrative_function": function.value,
        "story_event": f"Nour {function.value.replace('_', ' ')} in the rain.",
        "reader_takeaway": f"The reader understands {function.value}.",
        "character_ids": ["nour"],
        "environment": "A narrow Cairo alley at night",
        "visual_focus": focus,
        "emotional_intent": "Tension giving way to resolve",
        "text": {"content_kind": "none", "carrier": "none"},
    }
    data.update(overrides)
    return data


def test_story_events_drive_distinct_shots_and_compositions_deterministically():
    request = PanelPlanningRequest(
        scene_id="scene_rooftop",
        scene_summary="The storm begins as Nour follows a signal across the rooftops.",
        beats=[
            beat("b1", "establishing", "rooftops and storm clouds"),
            beat("b2", "action_preparation", "Nour's hand reaching toward a rooftop door"),
            beat("b3", "reveal", "a lit signal behind the door"),
            beat("b4", "detail", "the cracked blue transmitter"),
            beat("b5", "reaction", "Nour's shocked expression"),
            beat("b6", "aftermath", "Nour alone beneath the receding storm"),
        ],
    )
    first = plan_panels(request)
    second = plan_panels(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [p.panel_id for p in first.plans] == [f"panel_{i:02d}" for i in range(1, 7)]
    assert first.plans[0].shot_type == ShotType.ESTABLISHING
    assert first.plans[3].shot_type == ShotType.INSERT
    assert first.plans[4].shot_type == ShotType.REACTION
    assert len({p.shot_type for p in first.plans}) >= 5
    assert len({p.composition_type for p in first.plans}) >= 5
    assert all("Do not render dialogue" in p.image_brief for p in first.plans)
    assert first.visual_similarity_check == "NOT_IMPLEMENTED"
    assert first.diagnostics == []


def test_selected_cast_is_default_for_unspecified_panel_cast_but_characterless_is_explicit():
    result = plan_panels(PanelPlanningRequest(
        scene_id="selected_cast_story",
        selected_character_ids=["char_gomaa", "char_muse"],
        beats=[
            beat("b1", "reaction", "Gomaa reacts to the message", character_ids=[]),
            beat("b2", "cutaway", "The message on the laptop", character_ids=[], characterless=True),
        ],
    ))

    assert result.plans[0].character_ids == ["char_gomaa", "char_muse"]
    assert "char_gomaa, char_muse" in result.plans[0].image_brief
    assert "Preserve their reference appearance" in result.plans[0].image_brief
    assert result.plans[1].character_ids == []
    assert "intentionally character-free" in result.plans[1].image_brief


def test_characterless_beat_cannot_also_declare_characters():
    with pytest.raises(ValidationError, match="character-free beat cannot also declare"):
        NarrativeBeat.model_validate(beat(
            "b1", "cutaway", "A laptop screen", characterless=True, character_ids=["char_gomaa"]
        ))


def test_panel_planner_rejects_characters_outside_active_selection():
    with pytest.raises(ValidationError, match="part of the creator-selected cast"):
        PanelPlanningRequest(
            scene_id="selection_guard",
            selected_character_ids=["char_gomaa"],
            beats=[beat("b1", "dialogue", "Muse speaks", character_ids=["char_muse"])],
        )


def test_agent_panel_planner_uses_composer_selection_as_authoritative_cast():
    from app.agent.registry import CapabilityRegistry

    registry = object.__new__(CapabilityRegistry)
    output = registry._plan_panels_adapter(
        {
            "scene_id": "selected_cast_story",
            "selected_character_ids": ["model_invented_id"],
            "beats": [beat("b1", "reaction", "Gomaa reacts", character_ids=[])],
        },
        {"project_id": "test_project", "selected_character_ids": ["char_gomaa", "char_muse"]},
    )

    assert output["plans"][0]["character_ids"] == ["char_gomaa", "char_muse"]
    assert output["plans"][0]["characterless"] is False
    assert "panel_01" in output["input_warnings"][0]


def test_repetition_is_reported_but_can_be_explicitly_intentional():
    repeated = [
        beat("b1", "reaction", "Nour's eyes"),
        beat("b2", "reaction", "Nour's eyes"),
    ]
    unmarked = plan_panels(PanelPlanningRequest(scene_id="s1", beats=repeated))
    assert [d.code for d in unmarked.diagnostics] == ["UNJUSTIFIED_PLANNING_REPETITION"]
    assert unmarked.diagnostics[0].severity == "warning"

    repeated[1]["intentional_repetition_reason"] = "Hold the same close-up while the expression changes from fear to resolve."
    intentional = plan_panels(PanelPlanningRequest(scene_id="s1", beats=repeated))
    assert intentional.diagnostics[0].code == "INTENTIONAL_PLANNING_REPETITION"
    assert intentional.diagnostics[0].severity == "info"


def test_text_semantics_carrier_and_silent_state_are_explicit():
    dialogue = PanelTextPlan(
        content_kind=TextContentKind.SPOKEN_DIALOGUE,
        carrier=TextCarrier.SPEECH_BUBBLE,
        speaker_id="nour",
        reserve_space=True,
        preferred_region=TextRegion.TOP_LEFT,
    )
    assert dialogue.speaker_id == "nour"
    assert dialogue.carrier == TextCarrier.SPEECH_BUBBLE
    narration = PanelTextPlan(content_kind="narration", carrier="narration_box")
    assert narration.reserve_space is True
    caption = PanelTextPlan(content_kind="narration", carrier="caption")
    assert caption.carrier == TextCarrier.CAPTION
    assert caption.reserve_space is True
    with pytest.raises(ValidationError, match="must reserve lettering space"):
        PanelTextPlan(
            content_kind="narration", carrier="narration_box",
            reserve_space=False,
        )
    with pytest.raises(ValidationError, match="not the default"):
        PanelTextPlan(content_kind="spoken_dialogue", carrier="caption", speaker_id="nour")
    with pytest.raises(ValidationError, match="only for audible dialogue"):
        PanelTextPlan(
            content_kind="narration", carrier="speech_bubble",
            override_reason="legacy plan requested this",
        )
    with pytest.raises(ValidationError, match="only for audible dialogue"):
        PanelTextPlan(content_kind="internal_thought", carrier="speech_bubble", speaker_id="nour")
    with pytest.raises(ValidationError, match="must explicitly use text.content_kind='none'"):
        NarrativeBeat.model_validate(beat(
            "silent_with_dialogue", "silent", "an empty doorway",
            text={
                "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
                "speaker_id": "nour", "reserve_space": True,
                "preferred_region": "top_left",
            },
        ))


def test_spoken_text_infers_speaker_only_for_single_character_beats():
    single_character = beat(
        "single_speaker", "dialogue", "Nour speaking",
        text={
            "content_kind": "spoken_dialogue",
            "carrier": "speech_bubble",
            "reserve_space": True,
        },
    )
    parsed = NarrativeBeat.model_validate(single_character)
    assert parsed.text.speaker_id == "nour"

    ambiguous = beat(
        "ambiguous_speaker", "dialogue", "Nour and Maeve talking",
        character_ids=["nour", "maeve"],
        text={
            "content_kind": "spoken_dialogue",
            "carrier": "speech_bubble",
            "reserve_space": True,
        },
    )
    with pytest.raises(ValidationError, match="needs speaker_id set to one of this beat's character_ids"):
        NarrativeBeat.model_validate(ambiguous)

    wrong_speaker = beat(
        "wrong_speaker", "dialogue", "Nour speaking",
        text={
            "content_kind": "spoken_dialogue",
            "carrier": "speech_bubble",
            "speaker_id": "maeve",
            "reserve_space": True,
        },
    )
    with pytest.raises(ValidationError, match="speaker_id must match a character_id"):
        NarrativeBeat.model_validate(wrong_speaker)


def test_spoken_speaker_must_be_in_the_effective_selected_panel_cast():
    selected_default = beat(
        "selected_default_speaker", "dialogue", "Muse speaks", character_ids=[],
        text={
            "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
            "speaker_id": "muse", "text_content": "Let's check the rules.",
        },
    )
    request = PanelPlanningRequest(
        scene_id="selected_speaker",
        selected_character_ids=["muse", "gomaa"],
        beats=[selected_default],
    )
    assert plan_panels(request).plans[0].text.speaker_id == "muse"

    unselected = beat(
        "unselected_speaker", "dialogue", "Nour speaks", character_ids=[],
        text={
            "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
            "speaker_id": "nour", "text_content": "I found the notice.",
        },
    )
    with pytest.raises(ValidationError, match="speaker_id set to a character in that panel's selected cast"):
        PanelPlanningRequest(
            scene_id="unselected_speaker",
            selected_character_ids=["muse", "gomaa"],
            beats=[unselected],
        )

    missing = beat(
        "missing_speaker", "dialogue", "Gomaa and Muse react", character_ids=[],
        text={
            "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
            "text_content": "We should verify first.",
        },
    )
    with pytest.raises(ValidationError, match="speaker_id set to a character in that panel's selected cast"):
        PanelPlanningRequest(
            scene_id="missing_speaker",
            selected_character_ids=["muse", "gomaa"],
            beats=[missing],
        )


def test_planner_tool_defaults_omitted_narration_reservation_and_reports_validation_errors():
    from app.agent.registry import CapabilityRegistry
    from app.agent.schemas import ToolCall

    registry = CapabilityRegistry()
    call = ToolCall(call_id="planner_minimal_text", tool_id="planning.plan_panels", arguments={
        "project_id": "planner_regression",
        "reading_direction": "ltr",
        "scene_id": "quick_story_6p",
        "scene_summary": "Muse finds a wilted seedling and helps it recover.",
        "beats": [{
            "beat_id": "beat_01",
            "panel_id": "panel_01",
            "character_ids": ["muse"],
            "emotional_intent": "gentle concern",
            "environment": "small sunlit hillside clinic exterior",
            "narrative_function": "establishing",
            "reader_takeaway": "Muse opens the clinic at dawn.",
            "story_event": "Muse opens the clinic at dawn.",
            "text": {"content_kind": "narration", "carrier": "narration_box"},
            "visual_focus": "Muse beside the open clinic door",
        }],
    })
    result = registry.dispatch(call, {"project_id": "planner_regression", "offline_mode": False})
    assert result.status == "success", result.error
    assert result.output["plans"][0]["text"]["reserve_space"] is True

    invalid_arguments = call.arguments.copy()
    invalid_arguments["beats"] = [dict(call.arguments["beats"][0], text={
        "content_kind": "narration", "carrier": "narration_box", "reserve_space": False,
    })]
    rejected = registry.dispatch(
        call.model_copy(update={"call_id": "planner_explicit_no_reservation", "arguments": invalid_arguments}),
        {"project_id": "planner_regression", "offline_mode": False},
    )
    assert rejected.status == "failed"
    assert rejected.error_code == "ERR_INVALID_PANEL_PLAN"
    assert "reserve lettering space" in rejected.error


def test_agent_planner_recovers_narrative_label_copied_into_transition_role():
    from app.agent.registry import CapabilityRegistry
    from app.agent.schemas import ToolCall

    registry = CapabilityRegistry()
    beats = [
        beat("symbolic_beat", "symbolic", "credits become an opportunity", transition_role="symbolic"),
        beat("reaction_beat", "reaction", "Muse sees the realization", transition_role="reaction"),
        beat("dialogue_beat", "dialogue", "Muse explains the next step", transition_role="dialogue"),
    ]
    call = ToolCall(call_id="planner_semantic_transition_collision", tool_id="planning.plan_panels", arguments={
        "scene_id": "scene_planner_recovery",
        "beats": beats,
    })

    result = registry.dispatch(call, {"project_id": "planner_recovery", "_agent_chat": True})

    assert result.status == "success", result.error
    assert len(result.output["plans"]) == 3
    assert len(result.output["input_warnings"]) == 3
    assert [warning["supplied_value"] for warning in result.output["input_warnings"]] == ["symbolic", "reaction", "dialogue"]
    assert result.output["plans"][0]["transition_role"] == "first_panel_in_scene"
    strict_result = registry.dispatch(call, {"project_id": "planner_recovery"})
    assert strict_result.status == "failed"
    assert strict_result.error_code == "ERR_SCHEMA_VALIDATION_FAILED"


@pytest.mark.parametrize("encode_beats", [
    lambda beats: __import__("json").dumps(beats),
    lambda beats: "[" + " ".join(__import__("json").dumps(item) for item in beats) + "]",
])
@pytest.mark.parametrize("agent_chat", [True, False])
def test_registered_planner_recovers_model_serialized_beats_array(encode_beats, agent_chat):
    from app.agent.registry import CapabilityRegistry
    from app.agent.schemas import ToolCall
    import json

    registry = CapabilityRegistry()
    source_beats = [
        beat("b1", "establishing", "a desk at night"),
        beat("b2", "reveal", "a surprising message"),
        beat("b3", "transition", "the character checks the deadline"),
        beat("b4", "dialogue", "the companion explains the next step", text={
            "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
        }),
        beat("b5", "reaction", "the character considers the suggestion"),
        beat("b6", "aftermath", "the character begins work"),
    ]
    call = ToolCall(call_id="planner_string_beats", tool_id="planning.plan_panels", arguments={
        "scene_id": "scene_string_beats",
        "beats": encode_beats(source_beats),
    })

    # The same syntactic recovery applies to planner calls routed through the
    # Agent or the registered tool/MCP adapter; no semantic beat repair is
    # enabled outside Agent chat.
    result = registry.dispatch(call, {"project_id": "planner_string_beats", "_agent_chat": agent_chat})

    assert result.status == "success", result.error
    assert [plan["beat_id"] for plan in result.output["plans"]] == ["b1", "b2", "b3", "b4", "b5", "b6"]
    assert result.output["plans"][3]["text"]["speaker_id"] == "nour"
    assert result.output["input_warnings"][0]["field"] == "beats"


def test_planner_retry_is_allowed_after_schema_shape_rejection():
    from app.agent.coordinator import _needs_model_follow_up
    from app.agent.schemas import ToolResult

    failed_plan = ToolResult(
        call_id="plan_schema_error",
        tool_id="planning.plan_panels",
        status="failed",
        error="beats is not of type array",
        error_code="ERR_SCHEMA_VALIDATION_FAILED",
    )
    assert _needs_model_follow_up("start", [failed_plan], None)


def test_plan_descriptors_attach_to_e2_geometry_without_changing_slots():
    request = PanelPlanningRequest(
        scene_id="scene_six",
        reading_direction=ReadingDirection.RTL,
        beats=[
            beat("b1", "establishing", "the market street"),
            beat("b2", "action_preparation", "a hand nearing the bell"),
            beat("b3", "action_continuation", "Nour crossing the street"),
            beat("b4", "impact", "the bell being struck", shape_preference="triangle_wedge"),
            beat("b5", "reaction", "the shopkeeper's face"),
            beat("b6", "aftermath", "the silent market"),
        ],
    )
    planning = plan_panels(request)
    page = PageSpec(page_id="page_six", reading_direction=ReadingDirection.RTL)
    layout = CanvasEngine.generate_layout(
        CanvasSpec(width_px=900, height_px=1200),
        page,
        LayoutTemplateId.SIX_PANEL_CLASSIC,
    )
    original_rects = {slot.panel_id: slot.rect.model_dump() for slot in layout.panel_slots}

    annotated = attach_panel_plans(layout, planning)

    assert {slot.panel_id: slot.rect.model_dump() for slot in annotated.panel_slots} == original_rects
    assert all(slot.descriptor is not None for slot in annotated.panel_slots)
    assert annotated.get_panel("panel_04").descriptor.framing.shot_type == ShotType.IMPACT
    assert annotated.get_panel("panel_04").descriptor.narrative.narrative_function == NarrativeFunction.IMPACT
    assert annotated.get_panel("panel_04").descriptor.shape_type != "triangle_wedge"
    assert "Requested shape preference: triangle_wedge" in annotated.get_panel("panel_04").descriptor.notes
    with pytest.raises(ValueError, match="IDs must match E2 slot IDs exactly"):
        attach_panel_plans(layout, plan_panels(PanelPlanningRequest(scene_id="short", beats=[beat("one", "establishing", "city")])))


def test_panel_plan_flows_through_canonical_e1_context_and_retrieval_fingerprint():
    planned = plan_panels(PanelPlanningRequest(
        scene_id="scene_01",
        beats=[beat(
            "b1", "reveal", "a brass key in Nour's palm",
            protected_visual_elements=["round wireframe glasses", "lightning bolt jacket patch"],
        )],
    )).plans[0]
    scene = SceneSpec(
        scene_id="scene_01",
        scene_index=0,
        title="The key",
        shot_type="legacy scene field",
        action="legacy scene action",
        character_ids=["nour"],
        panel_plan=planned,
    )

    packet = build_panel_context_packet(
        CANONICAL_M0_STORY_BIBLE,
        scene,
        "panel_01",
        enable_catalogue_retrieval=True,
    )

    assert packet.panel_plan["planning_signature"]["shot_type"] == "close_up"
    assert "a brass key in Nour's palm" in packet.generation_prompt
    assert "off_center_reveal" in packet.generation_prompt
    assert "round wireframe glasses" in packet.generation_prompt
    assert packet.reference_assets[0].asset_id == "nour_reference"
    assert len(packet.context_fingerprint) == 64

    with pytest.raises(ValueError, match="panel_id must match"):
        build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene, "panel_02")


def test_panel_planning_api_returns_structured_plan():
    client = TestClient(app)
    response = client.post("/api/v1/planning/panels", json={
        "scene_id": "scene_api",
        "beats": [beat("b1", "establishing", "a quiet harbor")],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["plans"][0]["narrative_function"] == "establishing"
    assert body["plans"][0]["shot_type"] == "establishing"
    assert body["geometry_layout_status"] == "NOT_GENERATED_BY_PLANNER"


def test_planned_layout_api_returns_actual_e2_slots_with_panel_descriptors():
    client = TestClient(app)
    request = PanelPlanningRequest(
        scene_id="scene_planned_layout",
        reading_direction=ReadingDirection.RTL,
        beats=[
            beat("b1", "establishing", "market rooftops"),
            beat("b2", "action_preparation", "Nour's reaching hand"),
            beat("b3", "action_continuation", "Nour crossing the street"),
            beat("b4", "impact", "a dropped lantern"),
            beat("b5", "reaction", "the merchant's face"),
            beat("b6", "aftermath", "the empty street"),
        ],
    )
    response = client.post("/api/v1/planning/panels/layout", json={
        "planning": request.model_dump(mode="json"),
        "canvas_spec": CanvasSpec(width_px=900, height_px=1200).model_dump(mode="json"),
        "page_spec": PageSpec(page_id="page_planned", reading_direction=ReadingDirection.RTL).model_dump(mode="json"),
        "template_id": "six_panel_classic",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["layout"]["panel_slots"]) == 6
    assert body["layout"]["panel_slots"][3]["descriptor"]["framing"]["shot_type"] == "impact"
    assert all(slot["descriptor"] is not None for slot in body["layout"]["panel_slots"])
    assert body["layout"]["canvas_spec"]["width_px"] == 900


def test_panel_planning_tool_is_registered_and_returns_plan_data():
    from app.agent.registry import CapabilityRegistry
    from app.agent.schemas import ToolCall

    registry = CapabilityRegistry()
    call = ToolCall(
        call_id="call_plan_panels",
        tool_id="planning.plan_panels",
        arguments={
            "scene_id": "scene_tool",
            "beats": [beat("b1", "detail", "a brass key")],
        },
    )
    result = registry.dispatch(call, {"project_id": "test"})
    assert result.status == "success", result.error
    assert result.output["plans"][0]["shot_type"] == "insert"
    assert result.output["project_id"] == "test"


def test_panel_planning_tool_accepts_explicit_project_id_without_schema_error():
    from app.agent.registry import CapabilityRegistry
    from app.agent.schemas import ToolCall

    registry = CapabilityRegistry()
    call = ToolCall(
        call_id="call_plan_panels_with_project",
        tool_id="planning.plan_panels",
        arguments={
            "project_id": "inkloop_m0_nour",
            "scene_id": "scene_quiet_day",
            "scene_summary": "Nour quiet day waking tea reading sunset walk",
            "beats": [
                beat("b1", "establishing", "Nour waking in bedroom, morning light"),
                beat("b2", "action_continuation", "Nour in kitchen making tea"),
                beat("b3", "silent", "Nour seated by window reading"),
                beat("b4", "aftermath", "Nour walking outside at sunset"),
            ],
        },
    )
    result = registry.dispatch(call, {"project_id": "inkloop_m0_nour"})
    assert result.status == "success", result.error
    assert result.error_code is None
    assert result.output["project_id"] == "inkloop_m0_nour"
    assert len(result.output["plans"]) == 4
    assert result.output["plans"][0]["shot_type"] == ShotType.ESTABLISHING
    assert result.output["plans"][2]["shot_type"] == ShotType.SILENT


def test_panel_plan_model_validate_with_omitted_internal_fields():
    from app.planning.panel_planner import PanelPlan

    partial = {
        "beat_id": "panel-1-wake",
        "camera_angle": "eye_level",
        "camera_position": "environmental",
        "character_ids": ["nour"],
        "composition_type": "environmental_negative_space",
        "emotional_intent": "Calm, gentle awakening",
        "narrative_function": "establishing",
        "panel_id": "panel_01",
        "reader_takeaway": "A calm morning beginning, Nour starts her quiet day",
        "scene_id": "nour_quiet_day",
        "shot_type": "establishing",
        "story_event": "Nour waking up in her room, morning light",
        "subject_scale": "extreme_long_shot",
        "text": {
            "carrier": "none",
            "content_kind": "none",
            "reading_order_index": 1,
            "reserve_space": False,
            "text_block_ids": [],
        },
        "transition_role": "first_panel_in_scene",
        "visual_focus": "Nour in bedroom waking up, soft morning light",
    }
    plan = PanelPlan.model_validate(partial)
    assert plan.panel_id == "panel_01"
    assert plan.reading_order_index == 1
    assert plan.environment is None
    assert plan.planning_signature["shot_type"] == "establishing"
    assert "Nour waking up in her room" in plan.image_brief
