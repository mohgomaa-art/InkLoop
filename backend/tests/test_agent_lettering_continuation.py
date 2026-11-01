from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agent.production import (
    PanelProduction,
    PageProduction,
    StoryProductionJob,
    lettering_only_requested,
    saved_job_ready_for_lettering,
)
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import AgentSession, ToolCall, ToolResult
from app.agent.story_to_canvas import StoryToCanvasWorkflow
from app.editor.models import LayerKind


class _SessionStore:
    def save_session(self, _session):
        return None


class _ExecutionManager:
    class _DB:
        @staticmethod
        def get_run(_run_id):
            return None

    db = _DB()


def test_lettering_continuation_intent_and_saved_job_gate_are_explicit():
    assert lettering_only_requested("continue bubbles and text")
    assert lettering_only_requested("add dialogue and captions, don't change the images")
    assert not lettering_only_requested("dont edit images or make text ur job only is fix agent")
    assert not lettering_only_requested("regenerate the panels")

    base = {
        "job_id": "storyjob_1",
        "plan": {"plans": [{"panel_id": "panel_01"}]},
        "panels": {"panel_01": {"status": "placed", "asset_id": "art_1"}},
        "pages": [{
            "page_number": 1, "page_id": "page_1", "panel_ids": ["panel_01"],
            "status": "assembled", "revision": 7,
            "verification": {"passed": True},
        }],
    }
    assert saved_job_ready_for_lettering(base)
    incomplete = {**base, "panels": {"panel_01": {"status": "needs_attention", "asset_id": None}}}
    assert not saved_job_ready_for_lettering(incomplete)
    recoverable = {
        **base,
        "panels": {"panel_01": {"status": "needs_attention", "asset_id": "art_1"}},
        "pages": [{**base["pages"][0], "status": "needs_attention", "verification": {"passed": False}}],
    }
    assert saved_job_ready_for_lettering(recoverable)

    from app.agent.coordinator import _needs_model_follow_up, _tools_for_turn
    from app.agent.schemas import ToolResult
    callable_tools = CapabilityRegistry().list_image_chat_tools()
    assert "planning.plan_lettering" not in {
        tool.tool_id for tool in _tools_for_turn(callable_tools, "make a new story with 6 panels")
    }
    assert _needs_model_follow_up("continue bubbles and text", [ToolResult(
        call_id="retry_lettering", tool_id="planning.plan_lettering", status="failed",
        error="Line too long", error_code="ERR_LETTERING_LINE_TOO_LONG",
    )], None)


def test_plan_lettering_registry_validates_saved_panel_and_selected_speaker_scope():
    registry = CapabilityRegistry()
    definition = registry.get_tool("planning.plan_lettering")
    assert definition is not None and definition.is_callable
    assert definition.tool_id in {tool.tool_id for tool in registry.list_image_chat_tools()}
    context = {
        "project_id": "lettering_project",
        "_saved_lettering_context": {
            "project_id": "lettering_project",
            "job_id": "storyjob_1",
            "page_ids": ["page_1"],
            "panels": [{"panel_id": "panel_01", "character_ids": ["char_muse"]}],
        },
    }

    def plan(text, speaker):
        return {
            "job_id": "storyjob_1",
            "decisions": [{
                "panel_id": "panel_01",
                "text": {
                    "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
                    "text_content": text, "speaker_id": speaker,
                },
            }],
        }

    valid = registry.dispatch(
        ToolCall(call_id="valid", tool_id="planning.plan_lettering", arguments=plan("Let's try again.", "char_muse")),
        context,
    )
    assert valid.status == "success"
    assert valid.output["decisions"][0]["text"]["speaker_id"] == "char_muse"

    wrong_speaker = registry.dispatch(
        ToolCall(call_id="wrong", tool_id="planning.plan_lettering", arguments=plan("Let's try again.", "char_unselected")),
        context,
    )
    assert wrong_speaker.status == "failed"
    assert wrong_speaker.error_code == "ERR_LETTERING_SPEAKER_SCOPE"

    overlong = registry.dispatch(
        ToolCall(
            call_id="long", tool_id="planning.plan_lettering",
            arguments=plan("These are thirteen words which exceed the newly drafted speech bubble limit for this panel.", "char_muse"),
        ),
        context,
    )
    assert overlong.status == "failed"
    assert overlong.error_code == "ERR_LETTERING_LINE_TOO_LONG"

    omitted_panel = registry.dispatch(
        ToolCall(call_id="omitted", tool_id="planning.plan_lettering", arguments={"job_id": "storyjob_1", "decisions": []}),
        context,
    )
    assert omitted_panel.status == "failed"
    assert omitted_panel.error_code == "ERR_SCHEMA_VALIDATION_FAILED"


def test_lettering_only_continuation_reuses_saved_page_without_art_or_geometry_calls():
    project_id = "lettering_project"
    page_id = "page_lettering_1"
    panel_id = "panel_01"
    asset_id = "art_original_1"
    character_id = "char_muse"
    layout_slot = SimpleNamespace(panel_id=panel_id, reading_order=1)
    layout = SimpleNamespace(
        panel_slots=[layout_slot], reading_order_panel_ids=[panel_id],
        get_panel=lambda requested: layout_slot if requested == panel_id else None,
    )
    image_layer = SimpleNamespace(
        layer_id="image_original_1", kind=LayerKind.IMAGE, panel_id=panel_id,
        source_asset_id=asset_id, metadata={},
    )
    page_doc = SimpleNamespace(page_id=page_id, project_id=project_id, revision=7, layout=layout, layers=[image_layer])
    plan = {
        "project_id": project_id,
        "plans": [{
            "panel_id": panel_id,
            "page_number": 1,
            "scene_id": "scene_1",
            "story_event": "Muse notices the clinic door is open.",
            "visual_focus": "Muse gestures toward the doorway.",
            "emotional_intent": "curious",
            "character_ids": [character_id],
            "text": {"content_kind": "none", "carrier": "none", "text_content": None, "speaker_id": None},
        }],
        "reading_direction": "ltr",
    }
    job = StoryProductionJob(
        job_id="storyjob_lettering_1", run_id="storyjob_lettering_1", project_id=project_id,
        source_request_message_id="source_request", source_plan_call_id="source_plan",
        status="completed", stage="production_completed", plan=plan, page_panel_count=1,
        target_page_count=1,
        pages=[PageProduction(
            page_number=1, page_id=page_id, panel_ids=[panel_id], revision=7, status="assembled",
            verification={"passed": True, "spacing_valid": True},
        )],
        panels={panel_id: PanelProduction(
            panel_id=panel_id, page_number=1, status="placed", character_ids=[character_id],
            asset_id=asset_id, image_layer_id=image_layer.layer_id,
        )},
        selected_character_ids=[character_id],
    )
    session = AgentSession(
        project_id=project_id, session_id="lettering_session",
        metadata={"story_production_jobs": {job.job_id: job.model_dump(mode="json")}},
    )

    class _TextOnlyRegistry:
        def __init__(self):
            self.calls = []
            self.tools = [SimpleNamespace(tool_id=tool_id) for tool_id in (
                "canvas.verify_page", "canvas.add_speech_bubble",
            )]

        def list_tools(self, callable_only=False):
            assert callable_only is True
            return self.tools

        def _editor_page(self, requested_page, _context):
            assert requested_page == page_id
            return None, page_doc

        def dispatch(self, call, _context):
            self.calls.append(call)
            args = call.arguments
            if call.tool_id == "canvas.add_speech_bubble":
                assert args["page_id"] == page_id and args["panel_id"] == panel_id
                assert args["expected_revision"] == page_doc.revision
                page_doc.revision += 1
                page_doc.layers.append(SimpleNamespace(
                    layer_id=args["layer_id"], kind=LayerKind.TEXT, panel_id=panel_id,
                    source_asset_id=None,
                    metadata={"text": args["text"], "speaker_character_id": args["speaker_character_id"]},
                ))
                return ToolResult(
                    call_id=call.call_id, tool_id=call.tool_id, status="success",
                    output={"layer_id": args["layer_id"], "revision": page_doc.revision},
                )
            assert call.tool_id == "canvas.verify_page"
            assert args["expected_artworks"] == [{"panel_id": panel_id, "asset_id": asset_id}]
            actual_texts = {
                (layer.panel_id, layer.metadata.get("text"), layer.metadata.get("speaker_character_id"))
                for layer in page_doc.layers if layer.kind == LayerKind.TEXT
            }
            assert all((item["panel_id"], item["text"], item.get("speaker_character_id")) in actual_texts
                       for item in args["expected_texts"])
            return ToolResult(
                call_id=call.call_id, tool_id=call.tool_id, status="success",
                output={"page_id": page_id, "revision": page_doc.revision, "passed": True,
                        "failures": [], "visual_verification": "not_run"},
            )

    registry = _TextOnlyRegistry()
    workflow = StoryToCanvasWorkflow(
        registry=registry, session_store=_SessionStore(), session=session, project_id=project_id,
        plan_result=ToolResult(call_id="source_plan", tool_id="planning.plan_panels", status="success", output=plan),
        plan_call_id="source_plan", source_request_message_id="source_request", request_texts=["continue bubbles and text"],
        selected_character_ids=[character_id], selected_style_profile=None, selected_location=None,
        canonical_characters={character_id: SimpleNamespace(name="Muse", canon_version=1, reference_assets=[])},
        execution_manager=_ExecutionManager(), effective_budget_usd=0.0, offline_mode=False,
        lettering_only=True,
        lettering_plan={
            "job_id": job.job_id,
            "decisions": [{
                "panel_id": panel_id,
                "text": {
                    "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
                    "text_content": "The door is open.", "speaker_id": character_id,
                },
                "delivery": "quiet curiosity", "emotional_intent": "curious",
            }],
        },
    )

    completed, summary = workflow.run([], [])

    assert completed.status == "completed"
    assert "Added and verified 1 editable lettering layer" in summary
    assert page_doc.revision > 7
    assert image_layer in page_doc.layers
    assert image_layer.source_asset_id == asset_id
    assert [call.tool_id for call in registry.calls] == [
        "canvas.verify_page", "canvas.add_speech_bubble", "canvas.verify_page",
    ]
    assert not ({"generation.generate_image", "canvas.place_panel_artwork", "canvas.create_custom_page", "canvas.create_page_from_template"}
                & {call.tool_id for call in registry.calls})

    resumed, resumed_summary = workflow.run([], [])
    assert resumed.status == "completed"
    assert "No new lettering was needed" in resumed_summary
    assert sum(call.tool_id == "canvas.add_speech_bubble" for call in registry.calls) == 1


def test_agent_routes_lettering_followup_to_saved_job_context_only(monkeypatch, tmp_path):
    from app.agent.coordinator import AgentCoordinator
    from app.agent.session_store import SessionStore

    project_id = "lettering_project"
    session_id = "lettering_route_session"
    character_id = "char_muse"
    page_id = "page_1"
    panel_id = "panel_01"
    plan = {
        "project_id": project_id,
        "plans": [{
            "panel_id": panel_id, "page_number": 1,
            "story_event": "Muse sees the clinic door open.",
            "visual_focus": "Muse looks toward the open door.",
            "character_ids": [character_id],
            "text": {"content_kind": "none", "carrier": "none", "text_content": None, "speaker_id": None},
        }],
    }
    job = StoryProductionJob(
        job_id="storyjob_1", run_id="storyjob_1", project_id=project_id,
        source_request_message_id="story_request", source_plan_call_id="plan_original",
        status="completed", stage="production_completed", plan=plan, page_panel_count=1,
        target_page_count=1,
        pages=[PageProduction(
            page_number=1, page_id=page_id, panel_ids=[panel_id], revision=5, status="assembled",
            verification={"passed": True},
        )],
        panels={panel_id: PanelProduction(
            panel_id=panel_id, page_number=1, status="placed", character_ids=[character_id], asset_id="art_1",
        )},
        selected_character_ids=[character_id],
    )
    session_store = SessionStore(sessions_dir=tmp_path)
    session = session_store.create_session(project_id=project_id, session_id=session_id)
    session.metadata["story_production_jobs"] = {job.job_id: job.model_dump(mode="json")}
    session_store.save_session(session)
    character = SimpleNamespace(
        name="Muse", entity_kind="creature", canon_version=2,
        visual_invariants=["cream fuzz", "dot eyes"],
    )
    monkeypatch.setattr(
        "app.agent.coordinator._get_project_bible",
        lambda _project_id: SimpleNamespace(canon_hash="canon_hash", bible_version=2, characters={character_id: character}),
    )

    class _Execution:
        class _DB:
            @staticmethod
            def get_run(_run_id):
                return None

        db = _DB()
        budget_manager = SimpleNamespace(get_available_budget=lambda: 3.0)

        @staticmethod
        def create_run(**_kwargs):
            return None

        @staticmethod
        def _log_event(**_kwargs):
            return None

    monkeypatch.setattr("app.api.routers.execution.get_execution_manager", lambda: _Execution())

    class _Model:
        last_usage = None

        def __init__(self):
            self.available_tool_ids = []
            self.saved_context = None

        def plan_next_action(self, *, messages, available_tools, project_context, iteration):
            self.available_tool_ids = [tool.tool_id for tool in available_tools]
            self.saved_context = project_context.get("saved_lettering_context")
            return ([ToolCall(
                call_id="lettering_plan_call", tool_id="planning.plan_lettering",
                arguments={
                    "job_id": "storyjob_1",
                    "decisions": [{
                        "panel_id": panel_id,
                        "text": {
                            "content_kind": "spoken_dialogue", "carrier": "speech_bubble",
                            "text_content": "The door is open.", "speaker_id": character_id,
                        },
                    }],
                },
            )], None, "Planning saved-page lettering")

        @staticmethod
        def _synthesize_grounded_response(*_args, **_kwargs):
            return "The lettering plan failed validation."

    model = _Model()
    captured_workflow_args = {}

    class _Workflow:
        def __init__(self, **kwargs):
            captured_workflow_args.update(kwargs)
            self.calls = []
            self.results = []

        def run(self, _prior_results, _prior_calls):
            return job, "Lettering continuation ran against the saved job."

    monkeypatch.setattr("app.agent.story_to_canvas.StoryToCanvasWorkflow", _Workflow)
    registry = CapabilityRegistry()
    coordinator = AgentCoordinator(registry=registry, model_client=model, session_store=session_store)

    message = coordinator.process_chat_turn(
        project_id=project_id, session_id=session_id, user_text="continue bubbles and text",
        offline_mode=True,
    )

    assert model.available_tool_ids == ["planning.plan_lettering"]
    assert model.saved_context["job_id"] == "storyjob_1"
    assert model.saved_context["panels"][0]["panel_id"] == panel_id
    assert model.saved_context["panels"][0]["character_ids"] == [character_id]
    assert captured_workflow_args
    assert captured_workflow_args["lettering_only"] is True
    assert captured_workflow_args["lettering_plan"]["job_id"] == "storyjob_1"
    assert [call.tool_id for call in message.tool_calls] == ["planning.plan_lettering"]
    assert "generation.generate_image" not in model.available_tool_ids
    assert "Canvas page creation" not in message.text
