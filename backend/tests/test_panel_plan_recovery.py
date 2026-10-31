from app.agent.coordinator import _requested_single_page_panel_count, _tools_for_turn
from app.agent.panel_plan_recovery import (
    collapse_incomplete_planner_retries,
    panel_plan_retry_is_duplicate,
    recover_panel_plan_arguments,
)
from app.agent.schemas import ToolCall, ToolDefinition, ToolResult
from app.agent.coordinator import (
    AgentCoordinator,
    _latest_current_turn_panel_plan,
    _latest_current_turn_panel_plan_failure,
)
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import AgentMessage, AgentSession
from app.planning.panel_planner import PanelPlanningRequest, plan_panels


SOURCE = """# The $150 Mistake
I found an announcement for the Meta Global AI Developer Hackathon.
I applied without expecting anything to happen.
A few days later I received preliminary selection and saw $150 in model credits.
I first thought I had won a cash prize.
Then I opened the rules channel and learned the credits were for building a project.
The rules said the project had to be new and submitted before November 4.
I realized my existing medical education project could make me ineligible.
Muse suggested building a Visual QA Agent, and I decided to verify the rules first."""


def test_short_spellings_route_one_page_eight_pannel_story_to_object_aware_planner():
    request = "1 PAGE 8 PANNELS RESHAPE STORY IF NEDDED"
    assert _requested_single_page_panel_count(request) == 8
    tools = [
        ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan."),
        ToolDefinition(tool_id="generation.generate_image", name="Generate", domain="generation", purpose="Generate."),
        ToolDefinition(tool_id="canvas.create_page_from_template", name="Create", domain="canvas", purpose="Create."),
    ]
    offered = _tools_for_turn(tools, request)
    assert [tool.tool_id for tool in offered] == ["planning.plan_panels"]
    schema = offered[0].parameters_schema
    assert schema["properties"]["page_count"]["enum"] == [1]
    assert schema["$defs"]["StoryPageDraft"]["properties"]["beats"]["minItems"] == 8
    assert schema["$defs"]["StoryPageDraft"]["properties"]["beats"]["maxItems"] == 8
    assert "recurring_objects" in schema["properties"]


def test_malformed_duplicate_planner_calls_are_collapsed_to_the_most_complete_call():
    incomplete = ToolCall(call_id="first", tool_id="planning.plan_panels", arguments={"project_id": "p"})
    richer = ToolCall(call_id="second", tool_id="planning.plan_panels", arguments={
        "project_id": "p", "scene_id": "scene_one", "scene_summary": "Story summary",
    })
    unrelated = ToolCall(call_id="third", tool_id="canon.inspect_characters", arguments={"project_id": "p"})

    collapsed = collapse_incomplete_planner_retries([incomplete, richer, unrelated])
    assert [call.call_id for call in collapsed] == ["second", "third"]


def test_compact_planner_retry_prefers_later_count_matched_18_panel_outline():
    first = ToolCall(call_id="first_5", tool_id="planning.plan_panels", arguments={
        "project_id": "real_one_6675e532",
        "scene_id": "wrong_five_panel_scene",
        "scene_summary": "A stale short version.",
        "reading_direction": "rtl",
        "panel_count": 5,
        "panel_outline": [f"Stale beat {index}" for index in range(1, 6)],
    })
    corrected = ToolCall(call_id="corrected_18", tool_id="planning.plan_panels", arguments={
        "project_id": "real_one_6675e532",
        "scene_id": "the_150_mistake_part_one",
        "scene_summary": "The full 18-panel story.",
        "reading_direction": "ltr",
        "panel_count": 18,
        "panel_outline": [f"Creator supplied beat {index}" for index in range(1, 19)],
    })

    collapsed = collapse_incomplete_planner_retries([first, corrected])

    assert [call.call_id for call in collapsed] == ["corrected_18"]


def test_distinct_panel_plan_correction_is_allowed_but_identical_repeat_is_blocked():
    original = ToolCall(call_id="plan_5", tool_id="planning.plan_panels", arguments={
        "project_id": "p", "scene_id": "scene_5", "scene_summary": "Five beats", "reading_direction": "rtl",
        "panel_count": 5, "panel_outline": [f"Beat {index}" for index in range(1, 6)],
    })
    corrected_args = {
        "project_id": "p", "scene_id": "scene_18", "scene_summary": "Eighteen beats", "reading_direction": "ltr",
        "panel_count": 18, "panel_outline": [f"Beat {index}" for index in range(1, 19)],
    }
    success = ToolResult(call_id=original.call_id, tool_id="planning.plan_panels", status="success", output={"plans": [{}]})

    assert panel_plan_retry_is_duplicate(original.arguments, [success], [original]) is True
    assert panel_plan_retry_is_duplicate(corrected_args, [success], [original]) is False

    second_success = ToolResult(call_id="plan_18", tool_id="planning.plan_panels", status="success", output={"plans": [{}]})
    corrected_call = ToolCall(call_id="plan_18", tool_id="planning.plan_panels", arguments=corrected_args)
    assert panel_plan_retry_is_duplicate({"scene_id": "third_revision"}, [success, second_success], [original, corrected_call]) is True


def test_current_turn_plan_is_preferred_to_older_plan_result():
    older = ToolResult(call_id="old", tool_id="planning.plan_panels", status="success", output={"plans": [{"scene_id": "old"}]})
    current = ToolResult(call_id="new", tool_id="planning.plan_panels", status="success", output={"plans": [{"scene_id": "current"}]})
    blocked_retry = ToolResult(call_id="retry", tool_id="planning.plan_panels", status="blocked", error="duplicate")

    assert _latest_current_turn_panel_plan([older, current, blocked_retry]) is current


def test_failed_current_turn_plan_is_detected_so_it_cannot_fall_back_to_old_plan():
    failure = ToolResult(
        call_id="current_failed",
        tool_id="planning.plan_panels",
        status="failed",
        error="Authored dialogue was rejected before planning.",
    )
    assert _latest_current_turn_panel_plan_failure([failure]) is failure


def test_coordinator_accepts_a_distinct_18_panel_correction_and_saves_it_over_stale_plan(monkeypatch):
    story = (
        "Gomaa discovers a hackathon notice after browsing late at night. "
        "He applies without expecting a reply. "
        "A selection message arrives and lists one hundred fifty dollars in credits. "
        "He realizes the credits are for a new project, not a cash prize. "
        "Muse proposes verifying the rules before they build anything."
    )
    first_call = ToolCall(call_id="stale_five", tool_id="planning.plan_panels", arguments={
        "project_id": "real_one_6675e532",
        "scene_id": "stale_five_panel_scene",
        "scene_summary": "Short stale plan.",
        "reading_direction": "rtl",
        "panel_count": 5,
        "panel_outline": [f"Short outline beat {index}" for index in range(1, 6)],
    })
    corrected_call = ToolCall(call_id="creator_eighteen", tool_id="planning.plan_panels", arguments={
        "project_id": "real_one_6675e532",
        "scene_id": "the_150_mistake_part_one",
        "scene_summary": "The complete 18-panel story.",
        "reading_direction": "ltr",
        "panel_count": 18,
        "panel_outline": [f"Creator-authored panel beat {index}" for index in range(1, 19)],
    })

    class _Model:
        def plan_next_action(self, *, iteration, **_kwargs):
            if iteration == 1:
                return [first_call], None, None
            if iteration == 2:
                return [corrected_call], None, None
            return None, "The corrected 18-panel outline is saved.", None

        def _synthesize_grounded_response(self, *_args):
            return "The corrected outline is saved."

    class _SessionStore:
        def __init__(self):
            stale_plan = {
                "project_id": "real_one_6675e532",
                "scene_id": "stale_five_panel_scene",
                "reading_direction": "rtl",
                "plans": [{"panel_id": f"old_{index}"} for index in range(1, 6)],
            }
            self.session = AgentSession(
                project_id="real_one_6675e532",
                session_id="plan_revision_session",
                messages=[AgentMessage(message_id="source", role="user", text=story)],
                metadata={"pending_story_action": {
                    "schema_version": "1.0.0",
                    "action_type": "adapt_story_to_comic",
                    "source_message_id": "source",
                    "source_story_hash": "story_hash",
                    "source_title": "The $150 Mistake",
                    "status": "plan_ready",
                    "panel_count": 5,
                    "plan": stale_plan,
                    "plan_call_id": "old_plan_call",
                }},
            )

        def get_session(self, _session_id):
            return self.session

        def create_session(self, project_id, session_id):
            self.session = AgentSession(project_id=project_id, session_id=session_id)
            return self.session

        def append_message(self, _session_id, message):
            self.session.messages.append(message)

        def save_session(self, session):
            self.session = session
            return session

    from types import SimpleNamespace
    from app.agent import coordinator as coordinator_module
    bible = SimpleNamespace(project_id="real_one_6675e532", canon_hash="canon", bible_version=1, characters={})
    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: bible)
    registry = CapabilityRegistry.get_instance()
    session_store = _SessionStore()
    coordinator = AgentCoordinator(registry=registry, model_client=_Model(), session_store=session_store)

    message = coordinator.process_chat_turn(
        project_id="real_one_6675e532",
        user_text="Revise the story outline to 18 panels.",
        session_id="plan_revision_session",
        offline_mode=True,
    )

    plans = [result for result in message.tool_results if result.tool_id == "planning.plan_panels"]
    assert [result.status for result in plans] == ["failed", "success"]
    assert "request needs 18 panels" in plans[0].error
    assert len(plans[1].output["plans"]) == 18
    saved_action = session_store.session.metadata["pending_story_action"]
    assert saved_action["panel_count"] == 18
    assert saved_action["plan_call_id"] == "creator_eighteen"
    assert saved_action["plan"]["scene_id"] == "the_150_mistake_part_one"
    assert saved_action["plan"]["reading_direction"] == "ltr"


def test_incomplete_planner_call_recovers_eight_extractive_beats_from_user_story():
    args, warning, error = recover_panel_plan_arguments(
        {"project_id": "real_one_6675e532", "scene_id": "part_one_150_mistake", "scene_summary": "Part One: I Thought I Won"},
        current_request="1 PAGE 8 PANNELS RESHAPE STORY IF NEDDED",
        recent_user_texts=[("source_story_message", SOURCE)],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
    )

    assert error is None
    assert warning["source_message_id"] == "source_story_message"
    assert warning["panel_count"] == 8
    assert len(args["beats"]) == 8
    assert [beat["panel_id"] for beat in args["beats"]] == [f"panel_{i:02d}" for i in range(1, 9)]
    assert all(beat["text"]["content_kind"] == "none" for beat in args["beats"])
    assert all(beat["text"]["carrier"] == "none" for beat in args["beats"])
    assert all(beat["text"].get("text_content") is None for beat in args["beats"])
    assert all(beat["text"].get("speaker_id") is None for beat in args["beats"])
    assert "story text" in warning["resolution"]
    planned = plan_panels(PanelPlanningRequest.model_validate(args))
    assert len(planned.plans) == 8
    assert all(panel.scene_id == "part_one_150_mistake" for panel in planned.plans)


def test_compact_outline_expands_to_registered_schema_and_consumes_private_fields():
    args, warning, error = recover_panel_plan_arguments(
        {
            "project_id": "real_one_6675e532",
            "scene_id": "150_mistake_part_one",
            "selected_character_ids": ["char_gomaa", "char_muse"],
            "scene_summary": "Gomaa's hackathon misunderstanding and Muse's new direction.",
            "panel_count": 2,
            "panel_outline": [
                "Gomaa sees the $150 hackathon credits and thinks he has won.",
                "Muse reframes the credits as a chance to build a Visual QA Agent.",
            ],
            "panel_dialogue": [{
                "panel_index": 2,
                "speaker_id": "char_muse",
                "text_content": "Let's verify the rules first.",
            }],
        },
        current_request="1 page 2 panels; reshape the supplied story",
        recent_user_texts=[("story", SOURCE)],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
    )
    assert error is None
    assert warning and "visual panel beats" in warning["resolution"]
    assert "panel_count" not in args and "panel_outline" not in args
    plan = PanelPlanningRequest.model_validate(args)
    result = plan_panels(plan)
    assert len(result.plans) == 2
    assert result.plans[0].character_ids == ["char_gomaa"]
    assert result.plans[1].character_ids == ["char_muse"]
    assert result.plans[0].text.content_kind.value == "none"
    assert result.plans[0].text.carrier.value == "none"
    assert result.plans[1].text.content_kind.value == "spoken_dialogue"
    assert result.plans[1].text.carrier.value == "speech_bubble"
    assert result.plans[1].text.speaker_id == "char_muse"
    assert result.plans[1].text.text_content == "Let's verify the rules first."


def test_screenshot_style_scene_description_never_becomes_spoken_dialogue_or_filler_caption():
    args, warning, error = recover_panel_plan_arguments(
        {"project_id": "real_one_6675e532", "scene_id": "hackathon_notice"},
        current_request="1 page 1 panel",
        recent_user_texts=[("story", "Gomaa receives preliminary selection with $150 in Meta AI credits, briefly thinking he won something lucky. He checks the rules, realizes the credits are for building, and decides to verify the requirements before acting.")],
        character_names={"gomaa": "Gomaa"},
    )

    assert error is None
    assert warning is not None
    text = args["beats"][0]["text"]
    assert text["content_kind"] == "none"
    assert text["carrier"] == "none"
    assert "Gomaa receives preliminary selection" in args["beats"][0]["story_event"]


def test_newly_drafted_dialogue_over_type_limit_is_preserved_with_warning():
    long_line = "I found the notice and now I think we should verify every rule before acting."
    args = {
        "project_id": "real_one_6675e532",
        "scene_id": "dialogue_limit",
        "panel_count": 1,
        "panel_outline": ["Muse studies the notice."],
        "panel_dialogue": [{"panel_index": 1, "speaker_id": "muse", "text_content": long_line}],
    }
    recovered, warning, error = recover_panel_plan_arguments(
        args,
        current_request="1 page 1 panel",
        recent_user_texts=[("story", "Muse arrives and studies the notice. She pauses to consider the announcement, then decides to read every condition before she acts.")],
        character_names={"muse": "Muse"},
    )
    assert error is None
    corrected = recovered["beats"][0]["text"]["text_content"]
    assert corrected == long_line
    assert warning and "no automatic condensation was applied" in warning["dialogue_corrections"][0]

    exact = "You did not win the prize; the credits are for building a project before November fourth."
    args["panel_dialogue"][0]["text_content"] = exact
    recovered, warning, error = recover_panel_plan_arguments(
        args,
        current_request="1 page 1 panel",
        recent_user_texts=[("story", f'Muse says, "{exact}". She points to the deadline and explains why they need to read the rules carefully before they begin building anything.')],
        character_names={"muse": "Muse"},
    )
    assert error is None
    assert recovered["beats"][0]["text"]["text_content"] == exact
    assert warning and "preserved exact planned speech" in warning["dialogue_corrections"][0]


def test_markdown_emphasis_and_smart_quotes_do_not_hide_exact_creator_dialogue():
    authored_line = (
        'There\'s a catch. The prohibited list bans "Simple Image Analyzers." '
        'How do we ensure judges don\'t lump this in as another vision wrapper?'
    )
    source_story = (
        "Gomaa reads a long hackathon announcement and studies its strict eligibility rules before he talks to Muse. "
        "* **GOMAA:** There’s a catch. The prohibited list bans *\"Simple Image Analyzers.\"* "
        "How do we ensure judges don’t lump this in as another vision wrapper?* "
        "Muse listens while Gomaa considers how to make their project clearly different from a prohibited analyzer."
    )
    args, _, error = recover_panel_plan_arguments(
        {
            "project_id": "real_one_6675e532",
            "scene_id": "eligibility_question",
            "panel_count": 1,
            "panel_outline": ["Gomaa points at the prohibited-project rules while Muse listens."],
            "panel_dialogue": [{
                "panel_index": 1,
                "speaker_id": "char_gomaa",
                "text_content": authored_line,
            }],
        },
        current_request="1 page 1 panel",
        recent_user_texts=[("story", source_story)],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
        selected_character_ids=["char_gomaa", "char_muse"],
    )

    assert error is None
    assert args["beats"][0]["text"]["text_content"] == authored_line


def test_chat_session_project_mismatch_fails_before_creating_messages_or_context(monkeypatch):
    session = AgentSession(
        project_id="previous_project",
        session_id="remembered_old_project_chat",
        messages=[],
    )

    class _SessionStore:
        def get_session(self, _session_id):
            return session

        def create_session(self, **_kwargs):
            raise AssertionError("A mismatched chat must not be replaced or mutated implicitly.")

    class _Model:
        def plan_next_action(self, **_kwargs):
            raise AssertionError("No model call should run for a project-mismatched session.")

    from app.agent import coordinator as coordinator_module
    monkeypatch.setattr(
        coordinator_module,
        "_get_project_bible",
        lambda _project_id: (_ for _ in ()).throw(AssertionError("Project context must not load.")),
    )
    coordinator = AgentCoordinator(
        registry=CapabilityRegistry.get_instance(),
        model_client=_Model(),
        session_store=_SessionStore(),
    )

    try:
        coordinator.process_chat_turn(
            project_id="active_project",
            user_text="Create a one-page story.",
            session_id=session.session_id,
            offline_mode=True,
        )
    except ValueError as exc:
        assert "different project" in str(exc)
        assert "not saved" in str(exc)
    else:
        raise AssertionError("Project/session mismatch should stop the turn.")
    assert session.messages == []


def test_failed_new_plan_does_not_execute_an_older_pending_story_plan(monkeypatch):
    story = (
        "Gomaa reviews a long eligibility announcement and considers whether his proposed visual quality tool qualifies. "
        "Muse listens while they compare the requirements with the project idea and prepare to decide what to build."
    )
    stale_plan = {
        "project_id": "plan_scope_project",
        "scene_id": "old_scene",
        "reading_direction": "ltr",
        "plans": [{"panel_id": "old_panel_01"}],
    }
    session = AgentSession(
        project_id="plan_scope_project",
        session_id="failed_new_plan_session",
        messages=[AgentMessage(message_id="source", role="user", text=story)],
        metadata={"pending_story_action": {
            "schema_version": "1.0.0",
            "action_type": "adapt_story_to_comic",
            "source_message_id": "source",
            "source_story_hash": "source-hash",
            "source_title": "Eligibility check",
            "status": "plan_ready",
            "panel_count": 1,
            "plan": stale_plan,
            "plan_call_id": "old_plan_call",
        }},
    )
    long_dialogue = "This newly drafted dialogue is much too long and was never written by the creator."
    current_call = ToolCall(
        call_id="bad_new_plan",
        tool_id="planning.plan_panels",
        arguments={
            "project_id": "plan_scope_project",
            "scene_id": "new_scene",
            "scene_summary": "A new draft from the current request.",
            "panel_count": 1,
            "panel_outline": ["Gomaa points at the eligibility requirements while Muse listens."],
            "panel_dialogue": [{
                "panel_index": 1,
                "speaker_id": "char_gomaa",
                "text_content": long_dialogue,
            }],
        },
    )

    class _Model:
        def plan_next_action(self, *, iteration, **_kwargs):
            if iteration == 1:
                return [current_call], None, None
            return None, "The newly drafted line needs shortening before planning.", None

        def _synthesize_grounded_response(self, *_args):
            return "The new plan needs a shorter line."

    class _SessionStore:
        def get_session(self, _session_id):
            return session

        def create_session(self, **_kwargs):
            raise AssertionError("The existing project session should be reused.")

        def append_message(self, _session_id, message):
            session.messages.append(message)

        def save_session(self, saved):
            assert saved is session
            return saved

    from types import SimpleNamespace
    from app.agent import coordinator as coordinator_module
    bible = SimpleNamespace(
        project_id="plan_scope_project",
        canon_hash="canon",
        bible_version=1,
        characters={"char_gomaa": SimpleNamespace(name="Gomaa")},
    )
    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: bible)

    class _ForbiddenWorkflow:
        def __init__(self, **_kwargs):
            raise AssertionError("A failed current plan must not start production from an older plan.")

    monkeypatch.setattr(coordinator_module, "StoryToCanvasWorkflow", _ForbiddenWorkflow)
    coordinator = AgentCoordinator(
        registry=CapabilityRegistry.get_instance(),
        model_client=_Model(),
        session_store=_SessionStore(),
    )
    result = coordinator.process_chat_turn(
        project_id="plan_scope_project",
        user_text="Revise the existing story plan from this story.",
        session_id=session.session_id,
        selected_character_ids=["char_gomaa"],
        offline_mode=True,
    )

    planner_results = [item for item in result.tool_results if item.tool_id == "planning.plan_panels"]
    assert planner_results and planner_results[0].status == "success"
    corrected = planner_results[0].output["plans"][0]["text"]["text_content"]
    assert corrected == long_dialogue
    assert planner_results[0].output["input_warnings"]
    assert result.production_job is None
    assert session.metadata["pending_story_action"]["plan"]["plans"][0]["text"]["text_content"] == corrected


def test_compact_dialogue_uses_supplied_18_panel_count_when_current_command_has_no_count():
    outline = [f"Gomaa and Muse panel beat {index}." for index in range(1, 19)]
    dialogue = [
        {"panel_index": 1, "speaker_id": "char_gomaa", "text_content": "Why not? Let’s see what happens."},
        {"panel_index": 18, "speaker_id": "char_muse", "text_content": "Evidence wins over ambition."},
    ]
    args, warning, error = recover_panel_plan_arguments(
        {
            "project_id": "real_one_6675e532",
            "scene_id": "150_mistake_part_one",
            "scene_summary": "Gomaa and Muse prepare to build.",
            "reading_direction": "ltr",
            "panel_count": 18,
            "panel_outline": outline,
            "panel_dialogue": dialogue,
        },
        current_request=(
            "Continue with this outline.\n"
            + ("Older script notes repeat the source context. " * 10)
            + "Legacy note: Panel Count: 5 Panels."
        ),
        recent_user_texts=[("story", SOURCE)],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
        selected_character_ids=["char_gomaa", "char_muse"],
    )

    assert error is None
    assert warning["panel_count"] == 18
    assert len(args["beats"]) == 18
    assert args["beats"][0]["text"]["text_content"] == dialogue[0]["text_content"]
    assert args["beats"][17]["text"]["text_content"] == dialogue[1]["text_content"]
    assert args["beats"][17]["character_ids"] == ["char_gomaa", "char_muse"]


def test_compact_dialogue_rejects_unknown_or_unselected_speaker():
    base = {
        "project_id": "real_one_6675e532",
        "scene_id": "dialogue_scope",
        "panel_count": 1,
        "panel_outline": ["Gomaa reads the rules."],
        "panel_dialogue": [{"panel_index": 1, "speaker_id": "char_muse", "text_content": "Read the rules first."}],
    }
    _, _, unknown_error = recover_panel_plan_arguments(
        base,
        current_request="Continue this outline.",
        recent_user_texts=[("story", SOURCE)],
        character_names={"char_gomaa": "Gomaa"},
        selected_character_ids=["char_gomaa"],
    )
    _, _, unselected_error = recover_panel_plan_arguments(
        base,
        current_request="Continue this outline.",
        recent_user_texts=[("story", SOURCE)],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
        selected_character_ids=["char_gomaa"],
    )

    assert unknown_error and "unknown speaker ID" in unknown_error
    assert unselected_error and "outside the creator-selected cast" in unselected_error


def test_creator_count_rebuilds_stale_model_outline_from_story_source():
    args, warning, error = recover_panel_plan_arguments(
        {
            "project_id": "real_one_6675e532",
            "scene_id": "stale_eighteen_panel_plan",
            "panel_count": 18,
            "panel_outline": [f"Stale unrelated beat {index}" for index in range(1, 19)],
        },
        current_request="Create one page with 6 panels from this story.",
        recent_user_texts=[("story", SOURCE)],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
    )

    assert error is None
    assert warning["panel_count"] == 6
    assert "Discarded a stale outline" in warning["resolution"]
    assert len(args["beats"]) == 6
    assert "Stale unrelated beat" not in " ".join(beat["story_event"] for beat in args["beats"])


def test_saved_panel_count_wins_over_stale_outline_after_short_start_command():
    args, warning, error = recover_panel_plan_arguments(
        {
            "project_id": "real_one_6675e532",
            "scene_id": "saved_six_panel_plan",
            "panel_count": 18,
            "panel_outline": [f"Stale beat {index}" for index in range(1, 19)],
        },
        current_request="start",
        recent_user_texts=[("story", SOURCE)],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
        expected_panel_count=6,
    )

    assert error is None
    assert warning["panel_count"] == 6
    assert len(args["beats"]) == 6


def test_creator_requested_count_is_not_reduced_when_source_has_too_few_beats():
    _, _, error = recover_panel_plan_arguments(
        {
            "project_id": "real_one_6675e532",
            "scene_id": "too_short_for_six",
            "panel_count": 18,
            "panel_outline": [f"Stale beat {index}" for index in range(1, 19)],
        },
        current_request="Create one page with 6 panels.",
        recent_user_texts=[("story", "Gomaa reads the announcement at his desk while Muse waits beside him. They only have a moment to decide what the announcement requires.")],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
    )

    assert error and "request needs 6 panels" in error
    assert "count will not be reduced silently" in error


def test_affirmation_does_not_claim_plan_ready_when_source_cannot_support_requested_count(monkeypatch):
    from types import SimpleNamespace

    short_story = (
        "Gomaa reads one announcement at the desk while Muse waits beside him. "
        "They only have a moment to decide what the announcement requires."
    )
    session = AgentSession(
        project_id="short_story_project",
        session_id="short_story_session",
        messages=[AgentMessage(message_id="source", role="user", text=short_story)],
        metadata={"pending_story_action": {
            "schema_version": "1.0.0",
            "action_type": "adapt_story_to_comic",
            "source_message_id": "source",
            "source_story_hash": "story-hash",
            "source_title": "Short Story",
            "status": "plan_ready",
            "panel_count": 6,
            "panel_count_source": "creator_request",
            "plan": None,
            "plan_call_id": None,
        }},
    )

    class _SessionStore:
        def get_session(self, _session_id):
            return session

        def create_session(self, **_kwargs):
            raise AssertionError("The existing session should be reused.")

        def append_message(self, _session_id, message):
            session.messages.append(message)

        def save_session(self, _session):
            return _session

    class _Model:
        def plan_next_action(self, **_kwargs):
            raise AssertionError("The affirmative plan-review path should return before the model loop.")

    from app.agent import coordinator as coordinator_module
    monkeypatch.setattr(
        coordinator_module,
        "_get_project_bible",
        lambda _project_id: SimpleNamespace(
            project_id="short_story_project",
            canon_hash="canon",
            bible_version=1,
            characters={},
        ),
    )
    coordinator = AgentCoordinator(
        registry=CapabilityRegistry.get_instance(),
        model_client=_Model(),
        session_store=_SessionStore(),
    )

    result = coordinator.process_chat_turn(
        project_id="short_story_project",
        user_text="yes pls",
        session_id=session.session_id,
        offline_mode=True,
    )

    assert result.pending_story_action.status == "offer_made"
    assert "Comic Adaptation Plan Ready" not in result.text
    assert "couldn't prepare a valid panel plan" in result.text
    assert result.tool_calls == []
    assert result.tool_results == []


def test_requested_count_is_not_reduced_when_source_has_too_few_extractable_beats():
    _, _, error = recover_panel_plan_arguments(
        {"project_id": "real_one_6675e532", "scene_id": "too_few_source_beats", "panel_count": 18},
        current_request="Continue this outline.",
        recent_user_texts=[("story", "Gomaa reads the announcement at his desk and realizes the credits are not a cash prize. Muse suggests checking the submission rules before they begin building anything for the deadline.")],
        character_names={"char_gomaa": "Gomaa", "char_muse": "Muse"},
    )

    assert error and "request needs 18 panels" in error
    assert "count will not be reduced silently" in error

def test_incomplete_plan_without_count_or_source_fails_without_inventing_beats():
    args, warning, error = recover_panel_plan_arguments(
        {"project_id": "real_one_6675e532"},
        current_request="MAKE PANELS",
        recent_user_texts=[],
        character_names={},
    )
    assert args == {"project_id": "real_one_6675e532"}
    assert warning is None
    assert error and "panel count" in error


def test_incomplete_plan_with_count_but_no_story_source_fails_truthfully():
    _, warning, error = recover_panel_plan_arguments(
        {"project_id": "real_one_6675e532"},
        current_request="1 page 8 panels",
        recent_user_texts=[],
        character_names={},
    )
    assert warning is None
    assert error and "story text or outline" in error
