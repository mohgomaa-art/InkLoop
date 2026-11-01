from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agent.coordinator import _requested_page_count, _story_blueprint_schema, _tools_for_turn
from app.agent.production import PageProduction, PanelProduction, StoryProductionJob, group_panels
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import AgentMessage, AgentSession, ToolCall, ToolDefinition
from app.agent.coordinator import AgentCoordinator
from app.canvas.descriptors import NarrativeFunction
from app.planning.panel_planner import PanelTextPlan, StoryBlueprintDraft, compile_story_blueprint


def _beat(event: str, *, local: bool = True, character_ids=None, text=None):
    return {
        "story_event": event,
        "reader_takeaway": event,
        "visual_focus": event,
        "emotional_intent": "Curiosity builds into a small discovery.",
        "narrative_function": NarrativeFunction.REVEAL.value,
        "character_ids": list(character_ids or []),
        "visible_character_names": ["Pip"] if local else [],
        "characterless": False,
        "text": text or (
            {
                "content_kind": "spoken_dialogue",
                "carrier": "speech_bubble",
                "text_content": "Let's follow the light.",
                **({"speaker_name": "Pip"} if local else {"speaker_id": "char_muse"}),
            }
            if event.endswith(".1.")
            else {"content_kind": "none", "carrier": "none"}
        ),
    }


def _blueprint(counts=(1, 2, 1, 3), *, local=True):
    pages = []
    for page_number, count in enumerate(counts, start=1):
        pages.append({
            "page_number": page_number,
            "summary": f"Page {page_number} advances the discovery.",
            "beats": [_beat(f"Pip finds clue {page_number}.{index}.", local=local) for index in range(1, count + 1)],
        })
    return StoryBlueprintDraft.model_validate({
        "project_id": "story_project",
        "page_count": len(counts),
        "title": "Pip and the Lantern",
        "premise": "A small creature finds a warm light in a quiet forest.",
        "audience_tone": "Gentle, curious, and hopeful.",
        "world_rules": ["The lantern glows only when someone shares."],
        "story_cast": [{
            "name": "Pip",
            "kind_and_form": "round, nonhuman fuzz creature",
            "visual_description": "A tiny teal orb creature with four soft feet and one gold spot.",
            "personality": "Cautious but kind.",
        }] if local else [],
        "story_arc": "Pip follows a light, discovers its rule, and shares it with a friend.",
        "assumptions": ["The story uses a new story-local character; Canon remains unchanged."],
        "reading_direction": "ltr",
        "pages": pages,
    })


def test_ten_page_request_exposes_exact_page_blueprint_schema_and_not_flat_panel_count():
    assert _requested_page_count("Make a story of 10 pages") == 10
    assert _requested_page_count("Make a ten-page story") == 10
    planner = ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan.")
    offered = _tools_for_turn(
        [planner], "Make a story of 10 pages",
        available_object_profiles=[{"prop_id": "hand_lamp", "name": "Hand lamp", "version": "3"}],
    )
    schema = offered[0].parameters_schema
    assert schema["properties"]["page_count"]["enum"] == [10]
    assert schema["properties"]["pages"]["minItems"] == 10
    assert schema["properties"]["pages"]["maxItems"] == 10
    assert "panel_count" not in schema["properties"]
    beat_schema = schema["$defs"]["StoryBeatDraft"]
    assert "text" in beat_schema["required"]
    assert "8 words or fewer" in beat_schema["properties"]["text"]["description"]
    assert "hand_lamp (Hand lamp)@v3" in offered[0].purpose


def test_page_creation_intent_starts_only_for_creation_requests_not_plan_only_requests():
    from app.agent.coordinator import _is_explicit_story_creation_request

    assert _is_explicit_story_creation_request("Make a story of 10 pages")
    assert _is_explicit_story_creation_request("Create a story of 2 pages")
    assert not _is_explicit_story_creation_request("Plan a story of 10 pages")
    assert not _is_explicit_story_creation_request("Make a story plan for 10 pages")
    assert not _is_explicit_story_creation_request("Make a story of 2 pages without images")


def test_selected_canon_schema_accepts_only_selected_display_names_for_normalization():
    planner = ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan.")
    offered = _tools_for_turn(
        [planner], "Make a story of 1 page",
        selected_character_profiles=[
            {"character_id": "char_gomaa", "name": "Gomaa"},
            {"character_id": "char_muse", "name": "Muse"},
        ],
    )[0]
    beat = offered.parameters_schema["$defs"]["StoryBeatDraft"]["properties"]
    text = offered.parameters_schema["$defs"]["PanelTextPlan"]["properties"]
    assert beat["visible_character_names"]["items"]["enum"] == ["Gomaa", "Muse"]
    assert text["speaker_name"]["anyOf"][0]["enum"] == ["Gomaa", "Muse"]


def test_story_without_page_count_gets_one_page_object_aware_review_plan():
    planner = ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan.")
    offered = _tools_for_turn([planner], "Make a story about a lamp that is found, carried, and lit.")
    schema = offered[0].parameters_schema
    assert schema["properties"]["page_count"]["enum"] == [1]
    assert "recurring_objects" in schema["properties"]
    assert "object profiles from the active project's object library" in offered[0].purpose


def test_explicit_one_page_story_uses_blueprint_schema_with_recurring_object_slots():
    planner = ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan.")
    offered = _tools_for_turn([planner], "Make a story of 1 page")
    schema = offered[0].parameters_schema
    assert schema["properties"]["page_count"]["enum"] == [1]
    assert "recurring_objects" in schema["properties"]
    assert "prop_ids" in schema["$defs"]["StoryBeatDraft"]["properties"]


def test_one_page_story_with_explicit_panel_count_keeps_exact_count_in_object_aware_blueprint():
    planner = ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan.")
    offered = _tools_for_turn([planner], "Create a story of 1 page with 6 panels")
    schema = offered[0].parameters_schema
    assert schema["properties"]["page_count"]["enum"] == [1]
    assert schema["$defs"]["StoryPageDraft"]["properties"]["beats"]["minItems"] == 6
    assert schema["$defs"]["StoryPageDraft"]["properties"]["beats"]["maxItems"] == 6
    assert "recurring_objects" in schema["properties"]


def test_ten_page_blueprint_keeps_exact_pages_and_story_driven_nonuniform_panel_counts():
    counts = (1, 2, 3, 1, 4, 2, 5, 1, 3, 2)
    output = compile_story_blueprint(_blueprint(counts))
    assert output["page_count"] == 10
    assert len(output["story_blueprint"]["pages"]) == 10
    assert [output["page_panel_counts"][str(i)] for i in range(1, 11)] == list(counts)
    assert output["total_panel_count"] == sum(counts)


def test_blueprint_compiles_exact_variable_density_pages_and_local_cast_only_into_prompt():
    output = compile_story_blueprint(_blueprint())

    assert output["page_count"] == 4
    assert output["total_panel_count"] == 7
    assert output["page_panel_counts"] == {"1": 1, "2": 2, "3": 1, "4": 3}
    assert [page["page_number"] for page in output["story_blueprint"]["pages"]] == [1, 2, 3, 4]
    assert [len(group) for group in group_panels(output["plans"], [])] == [1, 2, 1, 3]
    assert all("Pip" in plan["image_brief"] for plan in output["plans"])
    assert all("Pip follows a light" in plan["image_brief"] for plan in output["plans"])
    assert output["story_blueprint"]["story_cast_is_canon"] is False
    assert output["story_local_cast"][0]["name"] == "Pip"


def test_selected_canonical_cast_is_used_by_id_and_story_local_cast_is_not_added():
    blueprint = _blueprint((1, 2), local=False)
    for page in blueprint.pages:
        for beat in page.beats:
            beat.character_ids = ["char_muse"]
    blueprint.pages[0].beats[0].character_ids = []
    blueprint.pages[0].beats[0].text.speaker_id = None
    blueprint.pages[0].beats[0].text = PanelTextPlan.model_validate({
        "content_kind": "spoken_dialogue",
        "carrier": "speech_bubble",
        "text_content": "The lantern is warm.",
        "speaker_id": "char_muse",
    })
    output = compile_story_blueprint(
        blueprint,
        selected_character_ids=["char_muse"],
    )
    assert {tuple(plan["character_ids"]) for plan in output["plans"]} == {("char_muse",)}
    assert output["story_local_cast"] == []
    assert output["story_blueprint"]["selected_character_ids"] == ["char_muse"]
    assert output["plans"][0]["text"]["speaker_id"] == "char_muse"
    assert output["plans"][0]["text"]["carrier"] == "speech_bubble"


def test_adapter_normalizes_selected_canon_character_and_speaker_names_but_rejects_outside_cast(monkeypatch):
    from types import SimpleNamespace
    import app.agent.registry as registry_module

    bible = SimpleNamespace(characters={
        "char_gomaa": SimpleNamespace(name="Gomaa"),
        "char_muse": SimpleNamespace(name="Muse"),
        "char_nour": SimpleNamespace(name="Nour"),
    }, props={})
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: bible)
    raw = _blueprint((1,), local=False).model_dump(mode="json")
    beat = raw["pages"][0]["beats"][0]
    beat["visible_character_names"] = ["Gomaa", "Muse"]
    beat["text"] = {
        "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
        "text_content": "Let's check the result.", "speaker_name": "Gomaa",
    }
    registry = object.__new__(CapabilityRegistry)
    output = registry._plan_panels_adapter(raw, {
        "project_id": "story_project", "selected_character_ids": ["char_gomaa", "char_muse"],
    })
    assert output["plans"][0]["character_ids"] == ["char_gomaa", "char_muse"]
    assert output["plans"][0]["text"]["speaker_id"] == "char_gomaa"
    assert output["input_warnings"]

    outside = _blueprint((1,), local=False).model_dump(mode="json")
    outside["pages"][0]["beats"][0]["visible_character_names"] = ["Nour"]
    with pytest.raises(Exception, match="outside the creator-selected cast"):
        registry._plan_panels_adapter(outside, {
            "project_id": "story_project", "selected_character_ids": ["char_gomaa", "char_muse"],
        })

    unknown = _blueprint((1,), local=False).model_dump(mode="json")
    unknown["pages"][0]["beats"][0]["visible_character_names"] = ["A stranger"]
    with pytest.raises(Exception, match="does not match a selected Canon character"):
        registry._plan_panels_adapter(unknown, {
            "project_id": "story_project", "selected_character_ids": ["char_gomaa", "char_muse"],
        })


def test_recurring_object_drafts_must_be_used_in_at_least_two_planned_panels():
    source = _blueprint((2,)).model_dump(mode="json")
    source["recurring_objects"] = [{
        "prop_id": "hand_lamp",
        "name": "Hand lamp",
        "description": "Compact metal and glass lamp.",
        "stable_invariants": ["glass chamber held in a metal frame"],
        "allowed_states": ["lit", "unlit", "carried"],
    }]

    with pytest.raises(ValidationError, match="selected in at least one planned panel"):
        StoryBlueprintDraft.model_validate(source)

    source["pages"][0]["beats"][0]["prop_ids"] = ["hand_lamp"]
    with pytest.raises(ValidationError, match="recur in at least two planned panels"):
        StoryBlueprintDraft.model_validate(source)

    source["pages"][0]["beats"][1]["prop_ids"] = ["hand_lamp"]
    source["pages"][0]["beats"][0]["prop_states"] = {"hand_lamp": "unlit"}
    source["pages"][0]["beats"][1]["prop_states"] = {"hand_lamp": "lit"}
    valid = StoryBlueprintDraft.model_validate(source)
    assert all(beat.prop_ids == ["hand_lamp"] for beat in valid.pages[0].beats)


def test_story_local_dialogue_gets_job_local_speaker_identity_and_stays_out_of_canon():
    blueprint = _blueprint((1, 2), local=True)
    blueprint.pages[0].beats[0].text = PanelTextPlan.model_validate({
        "content_kind": "spoken_dialogue",
        "carrier": "speech_bubble",
        "text_content": "Come closer.",
        "speaker_name": "Pip",
    })

    output = compile_story_blueprint(blueprint)

    speaker = output["story_local_cast"][0]
    text_plan = output["plans"][0]["text"]
    assert speaker["speaker_id"].startswith("story_local_")
    assert text_plan["speaker_id"] == speaker["speaker_id"]
    assert text_plan["speaker_name"] == "Pip"
    assert text_plan["text_content"] == "Come closer."
    assert output["story_blueprint"]["story_cast_is_canon"] is False
    assert "Reserve clear negative space" in output["plans"][0]["image_brief"]
    assert output["story_blueprint"]["pages"][0]["beats"][0]["text"]["text_content"] == "Come closer."


def test_story_local_dialogue_rejects_speaker_not_visible_in_panel():
    blueprint = _blueprint((1, 2), local=True)
    blueprint.pages[0].beats[0].text = PanelTextPlan.model_validate({
        "content_kind": "spoken_dialogue",
        "carrier": "speech_bubble",
        "text_content": "Come closer.",
        "speaker_name": "Other",
    })
    with pytest.raises(ValueError, match="speaker_name must match"):
        compile_story_blueprint(blueprint)


def test_blueprint_rejects_missing_pages_missing_cast_and_uniform_default_density():
    with pytest.raises(ValidationError, match="Expected exactly 4 pages"):
        StoryBlueprintDraft.model_validate({**_blueprint().model_dump(mode="json"), "pages": _blueprint((1, 2, 1)).model_dump(mode="json")["pages"]})

    with pytest.raises(ValueError, match="story-local cast"):
        compile_story_blueprint(_blueprint().model_copy(update={"story_cast": []}))

    with pytest.raises(ValueError, match="same panel count"):
        compile_story_blueprint(_blueprint((2, 2, 2, 2)))


def test_ordinary_story_requires_some_lettering_but_an_explicitly_silent_story_can_omit_it():
    blueprint = _blueprint((1, 2), local=True)
    for page in blueprint.pages:
        for beat in page.beats:
            beat.text = PanelTextPlan(content_kind="none", carrier="none")
    with pytest.raises(ValidationError, match="contains no lettering"):
        StoryBlueprintDraft.model_validate(blueprint.model_dump(mode="json"))

    silent = blueprint.model_dump(mode="json")
    for page in silent["pages"]:
        for beat in page["beats"]:
            beat["narrative_function"] = NarrativeFunction.SILENT.value
    assert StoryBlueprintDraft.model_validate(silent)


def test_adapter_corrects_page_numbers_and_count_scalar_but_rejects_missing_requested_page():
    blueprint = _blueprint((1, 2))
    args = blueprint.model_dump(mode="json")
    args["page_count"] = 1
    args["pages"].reverse()
    registry = object.__new__(CapabilityRegistry)
    output = registry._plan_panels_adapter(args, {
        "project_id": "story_project",
        "selected_character_ids": [],
        "_expected_page_count": 2,
    })
    assert output["page_count"] == 2
    assert output["story_blueprint"]["pages"][0]["summary"].startswith("Page 1")
    assert output["input_warnings"]

    with pytest.raises(Exception, match="exactly 3 pages"):
        registry._plan_panels_adapter(args, {
            "project_id": "story_project",
            "selected_character_ids": [],
            "_expected_page_count": 3,
        })


class _SessionStore:
    def __init__(self, session):
        self.session = session

    def get_session(self, _session_id):
        return self.session

    def create_session(self, project_id, session_id):
        self.session = AgentSession(project_id=project_id, session_id=session_id)
        return self.session

    def append_message(self, _session_id, message):
        self.session.messages.append(message)

    def save_session(self, session):
        assert session is self.session
        return session


class _ExecutionManager:
    class _Budget:
        @staticmethod
        def get_available_budget():
            return 100.0

    class _Db:
        @staticmethod
        def get_run(_run_id):
            return None

    budget_manager = _Budget()
    db = _Db()

    @staticmethod
    def create_run(**_kwargs):
        return None

    @staticmethod
    def _log_event(**_kwargs):
        return None


def _prepare_coordinator(monkeypatch, session, model):
    from types import SimpleNamespace
    from app.agent import coordinator as coordinator_module
    import app.api.routers.execution as execution_router

    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: SimpleNamespace(
        project_id=session.project_id,
        canon_hash="canon-hash",
        bible_version=1,
        characters={},
    ))
    monkeypatch.setattr(execution_router, "get_execution_manager", lambda: _ExecutionManager())
    return AgentCoordinator(
        registry=CapabilityRegistry.get_instance(),
        model_client=model,
        session_store=_SessionStore(session),
    )


def test_explicit_multi_page_creation_starts_after_valid_plan_in_same_turn(monkeypatch):
    from app.agent import coordinator as coordinator_module

    session = AgentSession(project_id="story_project", session_id="new_story_session")
    call = ToolCall(
        call_id="story_plan_4",
        tool_id="planning.plan_panels",
        arguments=_blueprint().model_dump(mode="json"),
    )

    class _Model:
        def plan_next_action(self, **_kwargs):
            return [call], None, "Planning four pages"

        @staticmethod
        def _synthesize_grounded_response(*_args):
            return "Planner response"

    plan = compile_story_blueprint(_blueprint())
    panels = {
        plan_item["panel_id"]: PanelProduction(
            panel_id=plan_item["panel_id"], page_number=plan_item["page_number"],
            status="placed", asset_id=f"asset_{plan_item['panel_id']}",
        )
        for plan_item in plan["plans"]
    }
    pages = [PageProduction(
        page_number=page["page_number"], page_id=f"page_{page['page_number']}",
        panel_ids=page["panel_ids"], revision=2, status="assembled",
        verification={"passed": True},
    ) for page in plan["story_blueprint"]["pages"]]
    job = StoryProductionJob(
        job_id="storyjob_autostart", run_id="storyjob_autostart", project_id="story_project",
        source_request_message_id="source", source_plan_call_id="story_plan_4",
        status="completed", stage="production_completed", target_page_count=4,
        page_panel_counts=plan["page_panel_counts"], plan=plan, pages=pages, panels=panels,
    )
    workflow_args = {}

    class _Workflow:
        calls = []
        results = []

        def __init__(self, **kwargs):
            workflow_args.update(kwargs)

        def run(self, _prior_results, _prior_calls):
            return job, "All four pages are saved and verified."

    monkeypatch.setattr(coordinator_module, "StoryToCanvasWorkflow", _Workflow)

    coordinator = _prepare_coordinator(monkeypatch, session, _Model())
    response = coordinator.process_chat_turn(
        project_id="story_project",
        user_text="Make a story of 4 pages",
        session_id=session.session_id,
        offline_mode=True,
    )

    assert response.pending_story_action.page_count == 4
    assert response.pending_story_action.total_panel_count == 7
    assert response.pending_story_action.page_panel_counts == {"1": 1, "2": 2, "3": 1, "4": 3}
    assert response.pending_story_action.estimated_cost_usd == 0.07
    assert workflow_args["plan_result"].output["page_count"] == 4
    assert response.pending_story_action.status == "completed"
    assert response.production_job["target_page_count"] == 4
    assert "saved and verified" in response.text


def test_plan_only_multi_page_request_remains_reviewable_without_starting(monkeypatch):
    session = AgentSession(project_id="story_project", session_id="plan_only_session")
    call = ToolCall(
        call_id="story_plan_only_4",
        tool_id="planning.plan_panels",
        arguments=_blueprint().model_dump(mode="json"),
    )

    class _Model:
        def plan_next_action(self, **_kwargs):
            return [call], None, "Preparing a reviewable plan"

        @staticmethod
        def _synthesize_grounded_response(*_args):
            return "Planner response"

    response = _prepare_coordinator(monkeypatch, session, _Model()).process_chat_turn(
        project_id="story_project", user_text="Plan a story of 4 pages", session_id=session.session_id,
        offline_mode=True,
    )

    assert response.pending_story_action.status == "plan_ready"
    assert response.pending_story_action.page_count == 4
    assert "Start" in response.text and "Skip" in response.text
    assert all(result.tool_id != "generation.generate_image" for result in response.tool_results)


def test_skip_closes_review_plan_without_model_calls_or_generation(monkeypatch):
    plan = compile_story_blueprint(_blueprint())
    action = {
        "schema_version": "1.1.0",
        "action_type": "produce_story_book",
        "source_message_id": "story_source",
        "source_story_hash": "sha256",
        "source_title": "Pip and the Lantern",
        "status": "plan_ready",
        "panel_count": 7,
        "total_panel_count": 7,
        "page_count": 4,
        "page_panel_counts": plan["page_panel_counts"],
        "estimated_cost_usd": 0.07,
        "assumptions": plan["assumptions"],
        "plan": plan,
        "plan_call_id": "plan_saved_4",
    }
    session = AgentSession(
        project_id="story_project",
        session_id="skip_story_session",
        messages=[AgentMessage(message_id="story_source", role="user", text="A Pip story in four pages.")],
        metadata={"pending_story_action": action},
    )

    class _Model:
        def plan_next_action(self, **_kwargs):
            raise AssertionError("Skip must not call the model or production tools.")

    response = _prepare_coordinator(monkeypatch, session, _Model()).process_chat_turn(
        project_id="story_project",
        user_text="skip",
        session_id=session.session_id,
        offline_mode=True,
    )
    assert response.pending_story_action.status == "skipped"
    assert "No images were generated" in response.text
    assert not response.tool_calls and not response.tool_results


def test_start_is_blocked_when_page_plan_is_invalidated_and_no_job_exists(monkeypatch):
    action = {
        "schema_version": "1.1.0",
        "action_type": "produce_story_book",
        "source_message_id": "story_source",
        "source_story_hash": "sha256",
        "source_title": "Pip and the Lantern",
        "status": "needs_attention",
        "panel_count": 0,
        "page_count": 4,
        "plan": None,
        "plan_invalidated": True,
    }
    session = AgentSession(
        project_id="story_project",
        session_id="invalid_plan_session",
        messages=[AgentMessage(message_id="story_source", role="user", text="A Pip story in four pages.")],
        metadata={"pending_story_action": action},
    )

    class _Model:
        def plan_next_action(self, **_kwargs):
            raise AssertionError("An invalid plan cannot dispatch production.")

    response = _prepare_coordinator(monkeypatch, session, _Model()).process_chat_turn(
        project_id="story_project",
        user_text="start",
        session_id=session.session_id,
        offline_mode=True,
    )
    assert "no validated page plan" in response.text.casefold()
    assert response.production_job is None
    assert not response.tool_calls and not response.tool_results


def test_start_dispatches_saved_complete_plan_with_original_story_source(monkeypatch):
    from app.agent import coordinator as coordinator_module

    plan = compile_story_blueprint(_blueprint())
    action = {
        "schema_version": "1.1.0",
        "action_type": "produce_story_book",
        "source_message_id": "story_source",
        "source_story_hash": "sha256",
        "source_title": "Pip and the Lantern",
        "status": "plan_ready",
        "panel_count": 7,
        "total_panel_count": 7,
        "page_count": 4,
        "page_panel_counts": plan["page_panel_counts"],
        "estimated_cost_usd": 0.07,
        "assumptions": plan["assumptions"],
        "plan": plan,
        "plan_call_id": "plan_saved_4",
    }
    session = AgentSession(
        project_id="story_project",
        session_id="start_story_session",
        messages=[AgentMessage(message_id="story_source", role="user", text="Make a four page Pip story.")],
        metadata={"pending_story_action": action},
    )

    class _Model:
        def plan_next_action(self, **_kwargs):
            raise AssertionError("Start uses the approved saved plan directly.")

    panel_rows = {
        plan_item["panel_id"]: PanelProduction(
            panel_id=plan_item["panel_id"],
            page_number=plan_item["page_number"],
            status="placed",
            asset_id=f"asset_{plan_item['panel_id']}",
        )
        for plan_item in plan["plans"]
    }
    page_rows = []
    for page_number, page in enumerate(plan["story_blueprint"]["pages"], start=1):
        page_rows.append(PageProduction(
            page_number=page_number,
            page_id=f"saved_page_{page_number}",
            panel_ids=page["panel_ids"],
            revision=2,
            status="assembled",
            verification={"passed": True},
        ))
    job = StoryProductionJob(
        job_id="storyjob_test",
        run_id="storyjob_test",
        project_id="story_project",
        source_request_message_id="story_source",
        source_plan_call_id="plan_saved_4",
        status="completed",
        target_page_count=4,
        page_panel_counts=plan["page_panel_counts"],
        plan=plan,
        pages=page_rows,
        panels=panel_rows,
    )
    captured = {}

    class _Workflow:
        calls = []
        results = []

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self, _prior_results, _prior_calls):
            return job, "All four pages are saved and verified."

    monkeypatch.setattr(coordinator_module, "StoryToCanvasWorkflow", _Workflow)
    response = _prepare_coordinator(monkeypatch, session, _Model()).process_chat_turn(
        project_id="story_project",
        user_text="start",
        session_id=session.session_id,
        offline_mode=True,
    )
    assert captured["source_request_message_id"] == "story_source"
    assert captured["plan_result"].output["page_count"] == 4
    assert response.pending_story_action.status == "completed"
    assert response.production_job["target_page_count"] == 4
