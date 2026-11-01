from types import SimpleNamespace

from app.agent import coordinator as coordinator_module
from app.agent.coordinator import AgentCoordinator
from app.agent.production import production_action_requested
from app.agent.schemas import AgentSession, ToolCall, ToolDefinition, ToolResult


class _SessionStore:
    def __init__(self):
        self.session = None

    def get_session(self, _session_id):
        return self.session

    def create_session(self, project_id, session_id):
        self.session = AgentSession(project_id=project_id, session_id=session_id)
        return self.session

    def append_message(self, _session_id, message):
        self.session.messages.append(message)


class _Model:
    def __init__(self):
        self.histories = []

    def plan_next_action(self, **kwargs):
        self.histories.append(kwargs["messages"])
        available_ids = {tool.tool_id for tool in kwargs["available_tools"]}
        assert "generation.generate_image" in available_ids
        assert "canvas.place_panel_artwork" in available_ids
        assert "editor.add_text_layer" not in available_ids
        page = kwargs["project_context"].get("canvas_page_context")
        assert page["panels"][1]["panel_id"] == "panel_02"
        if kwargs["iteration"] == 1:
            return [ToolCall(
                call_id="generate_muse",
                tool_id="generation.generate_image",
                arguments={"prompt": "Muse eats a sandwich", "character_ids": ["nour"]},
            )], None, None
        return None, "The Muse picture was placed on the selected Canvas panel.", None

    def _synthesize_grounded_response(self, *_args):
        return "Generation completed."


class _ModelWithFailedFinalReply(_Model):
    def plan_next_action(self, **kwargs):
        if kwargs["iteration"] == 1:
            return super().plan_next_action(**kwargs)
        return None, "The model provider returned HTTP 400. No action was taken.", None


class _Registry:
    def __init__(self, panel_has_artwork=False):
        self.calls = []
        from app.editor.models import LayerKind
        self.panel_has_artwork = panel_has_artwork
        def rect(x, y, width, height):
            return SimpleNamespace(
                x=x, y=y, width=width, height=height,
                model_dump=lambda **_kwargs: {"x": x, "y": y, "width": width, "height": height},
            )
        panel_slots = [
            SimpleNamespace(panel_id="panel_01", reading_order=0, rect=rect(0, 0, 200, 200), polygon=None),
            SimpleNamespace(panel_id="panel_02", reading_order=1, rect=rect(220, 0, 258, 601), polygon=None),
        ]
        self.canvas_document = SimpleNamespace(
            page_id="page_01",
            project_id="muse_test",
            revision=3,
            layout=SimpleNamespace(
                get_panel=lambda panel_id: next((slot for slot in panel_slots if slot.panel_id == panel_id), None),
                reading_order_panel_ids=["panel_01", "panel_02"],
                panel_slots=panel_slots,
            ),
            layers=([SimpleNamespace(layer_id="existing_image", kind=LayerKind.IMAGE, panel_id="panel_02", source_asset_id="old_art", metadata={})] if panel_has_artwork else []),
        )

    def list_tools(self):
        return []

    def list_image_chat_tools(self):
        return [
            ToolDefinition(
                tool_id="generation.generate_image",
                name="Generate Image Panel",
                domain="generation",
                purpose="Generate artwork.",
            ),
            ToolDefinition(
                tool_id="canvas.place_panel_artwork",
                name="Place Panel Artwork",
                domain="canvas",
                purpose="Place generated artwork.",
            ),
        ]

    def get_tool(self, _tool_id):
        return None

    def _editor_page(self, page_id, context):
        assert page_id == "page_01"
        assert context["project_id"] == "muse_test"
        return object(), self.canvas_document

    def dispatch(self, tool_call, _context):
        self.calls.append(tool_call)
        if tool_call.tool_id == "generation.generate_image":
            output = {"asset_id": "art_muse_01", "character_ids": tool_call.arguments["character_ids"]}
        else:
            assert tool_call.tool_id == "canvas.place_panel_artwork"
            assert tool_call.arguments["page_id"] == "page_01"
            assert tool_call.arguments["expected_revision"] == 3
            assert tool_call.arguments["panel_id"] == "panel_02"
            assert tool_call.arguments["asset_id"] == "art_muse_01"
            assert tool_call.arguments["replace_existing"] is self.panel_has_artwork
            output = {"page_id": "page_01", "panel_id": "panel_02", "asset_id": "art_muse_01", "revision": 4}
        return ToolResult(
            call_id=tool_call.call_id,
            tool_id=tool_call.tool_id,
            status="success",
            output=output,
            duration_seconds=0.01,
        )


class _ExecutionManager:
    def __init__(self):
        self.budget_manager = SimpleNamespace(get_available_budget=lambda: 25.0)
        self.db = SimpleNamespace(get_run=lambda _run_id: None)

    def create_run(self, **_kwargs):
        pass

    def _log_event(self, **_kwargs):
        pass


def test_agent_uses_selected_cast_and_places_generated_asset_into_active_canvas(monkeypatch):
    registry = _Registry()
    model = _Model()
    bible = SimpleNamespace(
        project_id="muse_test",
        canon_hash="canon_hash",
        bible_version=1,
        characters={"muse": SimpleNamespace(name="Muse"), "nour": SimpleNamespace(name="Nour")},
    )
    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: bible)
    monkeypatch.setattr("app.api.routers.execution.get_execution_manager", _ExecutionManager)
    session_store = _SessionStore()
    coordinator = AgentCoordinator(
        registry=registry,
        model_client=model,
        session_store=session_store,
    )

    message = coordinator.process_chat_turn(
        project_id="muse_test",
        user_text="Make Muse eat a sandwich",
        session_id="muse_canvas_test_session",
        selected_character_ids=["muse"],
        canvas_page_id="page_01",
        canvas_panel_id="panel_02",
        canvas_expected_revision=3,
        offline_mode=True,
    )

    assert [call.tool_id for call in registry.calls] == [
        "generation.generate_image",
        "canvas.place_panel_artwork",
    ]
    assert registry.calls[0].arguments["character_ids"] == ["muse"]
    assert registry.calls[0].arguments["width"] == 258
    assert registry.calls[0].arguments["height"] == 601
    assert [call.tool_id for call in message.tool_calls] == [
        "generation.generate_image",
        "canvas.place_panel_artwork",
    ]
    assert message.tool_results[-1].output["revision"] == 4
    assert len(model.histories) == 1
    assert message.model_usage.status == "unavailable"
    assert message.model_usage.total_tokens is None
    saved_context = session_store.session.messages[0].request_context
    assert saved_context["selected_character_ids"] == ["muse"]
    assert saved_context["canvas_page_id"] == "page_01"
    assert saved_context["canvas_panel_id"] == "panel_02"
    assert saved_context["canvas_expected_revision"] == 3


def test_agent_replaces_art_in_selected_panel_using_current_canvas_revision(monkeypatch):
    registry = _Registry(panel_has_artwork=True)
    bible = SimpleNamespace(
        project_id="muse_test",
        canon_hash="canon_hash",
        bible_version=1,
        characters={"muse": SimpleNamespace(name="Muse"), "nour": SimpleNamespace(name="Nour")},
    )
    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: bible)
    monkeypatch.setattr("app.api.routers.execution.get_execution_manager", _ExecutionManager)
    coordinator = AgentCoordinator(registry=registry, model_client=_Model(), session_store=_SessionStore())

    coordinator.process_chat_turn(
        project_id="muse_test",
        user_text="Replace the selected panel art with Muse eating a sandwich",
        session_id="muse_canvas_replace_test",
        selected_character_ids=["muse"],
        canvas_page_id="page_01",
        canvas_panel_id="panel_02",
        canvas_expected_revision=3,
        offline_mode=True,
    )

    assert registry.calls[-1].tool_id == "canvas.place_panel_artwork"
    assert registry.calls[-1].arguments["replace_existing"] is True


def test_explicit_six_panel_story_continuation_assembles_saved_canvas_without_another_model_call(monkeypatch):
    """A resumed six-panel request must join prior and new assets on a real editable page."""
    from app.agent.schemas import AgentMessage

    panel_ids = [f"panel_{index:02d}" for index in range(1, 7)]
    plans = [{"panel_id": panel_id, "scene_id": "muse_lighthouse_1"} for panel_id in panel_ids]
    first_asset = ToolResult(
        call_id="prior_image_01",
        tool_id="generation.generate_image",
        status="success",
        output={"panel_id": "panel_01", "asset_id": "art_panel_01"},
    )

    class _ContinuationRegistry:
        def __init__(self):
            self.calls = []
            self.revision = 1
            self.pages = {}

        def list_image_chat_tools(self):
            return [
                ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan story."),
                ToolDefinition(tool_id="generation.generate_image", name="Generate", domain="generation", purpose="Generate art."),
                ToolDefinition(tool_id="canvas.create_page_from_template", name="Create page", domain="canvas", purpose="Create page."),
                ToolDefinition(tool_id="canvas.inspect_page_spacing", name="Inspect spacing", domain="canvas", purpose="Measure persisted gutters and margins."),
                ToolDefinition(tool_id="canvas.place_panel_artwork", name="Place art", domain="canvas", purpose="Place art."),
                ToolDefinition(tool_id="canvas.verify_page", name="Verify page", domain="canvas", purpose="Verify persisted page."),
            ]

        def list_tools(self, callable_only=False):
            return self.list_image_chat_tools()

        def get_tool(self, _tool_id):
            if _tool_id == "generation.generate_image":
                return SimpleNamespace(estimated_cost_usd=0.01)
            return None

        def dispatch(self, call, _context):
            self.calls.append(call)
            if call.tool_id == "generation.generate_image":
                output = {"panel_id": call.arguments["panel_id"], "asset_id": f"art_{call.arguments['panel_id']}"}
            elif call.tool_id == "canvas.create_page_from_template":
                assert call.arguments["layout_template"] == "six_panel_classic"
                assert len(call.arguments["panel_plans"]) == 6
                page_id = call.arguments["page_id"]
                output = {"page_id": page_id, "revision": self.revision, "panel_ids": panel_ids}
                self.pages[page_id] = SimpleNamespace(
                    page_id=page_id, project_id="muse_test", revision=self.revision,
                    layout=SimpleNamespace(get_panel=lambda _panel_id: None), layers=[],
                )
            elif call.tool_id == "canvas.place_panel_artwork":
                assert call.arguments["expected_revision"] == self.revision
                self.revision += 1
                page_id = call.arguments["page_id"]
                self.pages[page_id].revision = self.revision
                output = {"page_id": page_id, "panel_id": call.arguments["panel_id"], "revision": self.revision}
            elif call.tool_id == "canvas.inspect_page_spacing":
                output = {
                    "page_id": call.arguments["page_id"],
                    "minimum_edge_gap_px": 18.0,
                    "overlapping_panel_pairs": [],
                    "margin_clearance_valid": True,
                    "panels": [
                        {
                            "panel_id": panel_id,
                            "measured_margins_px": {"top": 45, "right": 45, "bottom": 45, "left": 45},
                            "margin_clearance_valid": True,
                        }
                        for panel_id in panel_ids
                    ],
                }
            else:
                assert call.tool_id == "canvas.verify_page"
                output = {"page_id": call.arguments["page_id"], "revision": self.revision, "passed": True,
                          "failures": [], "visual_verification": "not_run",
                          "expected_artworks": call.arguments["expected_artworks"]}
            return ToolResult(call_id=call.call_id, tool_id=call.tool_id, status="success", output=output)

    class _ContinueModel:
        def __init__(self):
            self.calls = 0

        def plan_next_action(self, **_kwargs):
            self.calls += 1
            return [ToolCall(
                call_id=f"continue_{panel_id}",
                tool_id="generation.generate_image",
                arguments={"panel_id": panel_id, "prompt": f"Muse story {panel_id}", "character_ids": ["muse"]},
            ) for panel_id in panel_ids[1:5]], None, None

        def _synthesize_grounded_response(self, *_args):
            return "The remaining artwork is ready."

    from app.agent.production import PanelProduction, PageProduction, StoryProductionJob, stable_job_id, stable_page_id
    store = _SessionStore()
    job_id = stable_job_id("muse_test", "muse_story_session", "prior_plan")
    checkpoint = StoryProductionJob(
        job_id=job_id,
        run_id=job_id,
        project_id="muse_test",
        source_request_message_id="original_request",
        source_plan_call_id="prior_plan",
        status="generating",
        plan={"plans": plans, "recommended_template_id": "six_panel_classic", "reading_direction": "rtl"},
        page_panel_count=6,
        pages=[PageProduction(page_number=1, page_id=stable_page_id(job_id, 1), panel_ids=panel_ids)],
        panels={panel_id: PanelProduction(
            panel_id=panel_id,
            page_number=1,
            status="generated" if panel_id == "panel_01" else "pending",
            character_ids=["muse"],
            asset_id="art_panel_01" if panel_id == "panel_01" else None,
        ) for panel_id in panel_ids},
        selected_character_ids=["muse"],
    )
    store.session = AgentSession(project_id="muse_test", session_id="muse_story_session", messages=[
        AgentMessage(message_id="original_request", role="user", text="make quick story 1 page 6 panels about Muse"),
        AgentMessage(message_id="first_image_turn", role="assistant", text="Panel one is ready.", tool_results=[first_asset]),
    ], metadata={"story_production_jobs": {job_id: checkpoint.model_dump(mode="json")}})
    registry = _ContinuationRegistry()
    from app.agent.story_to_canvas import StoryToCanvasWorkflow
    monkeypatch.setattr(
        StoryToCanvasWorkflow,
        "_page_document",
        lambda self, page_id: registry.pages.get(page_id),
    )
    monkeypatch.setattr(
        StoryToCanvasWorkflow,
        "_asset_matches_panel",
        lambda self, output, panel, **_kwargs: output.get("panel_id") == panel.panel_id and bool(output.get("asset_id")),
    )
    model = _ContinueModel()
    bible = SimpleNamespace(project_id="muse_test", canon_hash="canon", bible_version=1, characters={"muse": SimpleNamespace(name="Muse")})
    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: bible)
    monkeypatch.setattr("app.api.routers.execution.get_execution_manager", _ExecutionManager)
    coordinator = AgentCoordinator(registry=registry, model_client=model, session_store=store)

    result = coordinator.process_chat_turn(
        project_id="muse_test",
        user_text="do it autonomously + continue the remaining 5",
        session_id="muse_story_session",
        selected_character_ids=["muse"],
        offline_mode=False,
    )

    assert model.calls == 0
    assert [call.tool_id for call in registry.calls] == [
        "canvas.create_page_from_template",
        "canvas.inspect_page_spacing",
        *(["generation.generate_image"] * 5),
        *(["canvas.place_panel_artwork"] * 6),
        "canvas.verify_page",
    ], result.text
    assert any(call.tool_id == "generation.generate_image" and call.arguments.get("panel_id") == "panel_06" for call in registry.calls)
    assert len([call for call in registry.calls if call.tool_id == "canvas.place_panel_artwork"]) == 6
    assert "6/6 panels placed across 1/1 persisted Canvas pages" in result.text
    assert all(result_item.status == "success" for result_item in result.tool_results)


def test_panel_count_parser_requires_explicit_single_page_count():
    assert coordinator_module._requested_single_page_panel_count("make quick story 1 page 6 panels about Muse") == 6
    assert coordinator_module._requested_single_page_panel_count("make one page with six panels") == 6
    assert coordinator_module._requested_single_page_panel_count("make 6 panels") is None
    assert coordinator_module._requested_single_page_panel_count("make 2 pages with 6 panels") is None


def test_add_to_canvas_resumes_story_even_if_a_page_was_already_verified():
    from app.agent.schemas import AgentMessage

    messages = [
        AgentMessage(message_id="plan", role="assistant", text="Approved two-page plan.", tool_results=[ToolResult(
            call_id="plan_call", tool_id="planning.plan_panels", status="success",
            output={"plans": [{"panel_id": f"p{i}"} for i in range(1, 13)]},
        )]),
        AgentMessage(message_id="page_one", role="assistant", text="Page one was assembled.", tool_results=[ToolResult(
            call_id="verify_page_one", tool_id="canvas.verify_page", status="success",
            output={"page_id": "page_one", "passed": True},
        )]),
    ]
    session = AgentSession(project_id="muse_test", session_id="s", messages=messages)
    assert coordinator_module._is_pending_page_story_continuation(session, "add to canvas", "muse_test") is True


def test_make_panels_starts_a_new_plan_while_explicit_resume_uses_saved_story():
    from app.agent.schemas import AgentMessage

    session = AgentSession(
        project_id="muse_test",
        session_id="saved_four_panel_story",
        messages=[AgentMessage(
            message_id="saved_plan",
            role="assistant",
            text="Four panel plan saved and added to Canvas.",
            tool_results=[ToolResult(
                call_id="plan_four_panels",
                tool_id="planning.plan_panels",
                status="success",
                output={"plans": [{"panel_id": f"panel_{index}"} for index in range(1, 5)]},
            )],
        )],
    )

    assert production_action_requested("MAKE PANELS") is True
    assert coordinator_module._is_pending_page_story_continuation(
        session, "MAKE PANELS", "muse_test"
    ) is False
    assert coordinator_module._is_pending_page_story_continuation(
        session, "Continue production", "muse_test"
    ) is True
    assert coordinator_module._is_pending_page_story_continuation(
        session, "Retry failed panel p3", "muse_test"
    ) is True
    available = coordinator_module._tools_for_turn([
        ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan story."),
        ToolDefinition(tool_id="generation.generate_image", name="Generate", domain="generation", purpose="Generate art."),
        ToolDefinition(tool_id="canvas.create_page_from_template", name="Create", domain="canvas", purpose="Create page."),
    ], "MAKE PANELS")
    assert [tool.tool_id for tool in available] == ["planning.plan_panels"]


def test_selected_cast_repair_routes_directly_to_saved_job_without_model_planning():
    from app.agent.schemas import AgentMessage

    session = AgentSession(
        project_id="muse_test",
        session_id="saved_cast_repair",
        messages=[AgentMessage(
            message_id="saved_plan",
            role="assistant",
            text="A six-panel story plan is saved.",
            tool_results=[ToolResult(
                call_id="plan_call",
                tool_id="planning.plan_panels",
                status="success",
                output={"plans": [{"panel_id": f"panel_{index:02d}"} for index in range(1, 7)]},
            )],
        )],
    )

    request = "Regenerate panels missing the selected character references."
    assert coordinator_module._is_pending_page_story_continuation(session, request, "muse_test") is True


def test_interrupted_story_checkpoint_is_a_resumable_plan_without_transcript_result():
    session = AgentSession(
        project_id="muse_test",
        session_id="interrupted_story",
        metadata={"story_production_jobs": {"job": {
            "project_id": "muse_test",
            "source_plan_call_id": "plan_before_crash",
            "source_request_message_id": "request_before_crash",
            "updated_at": "2026-10-30T12:00:00+00:00",
            "plan": {"plans": [{"panel_id": "panel_01"}]},
        }}},
    )

    assert coordinator_module._is_pending_page_story_continuation(session, "continue", "muse_test") is True
    checkpoint = coordinator_module._latest_saved_story_job(session, "muse_test")
    assert checkpoint["source_plan_call_id"] == "plan_before_crash"
    assert checkpoint["plan"]["plans"][0]["panel_id"] == "panel_01"


def test_interrupted_story_checkpoint_is_scoped_to_owning_project():
    session = AgentSession(
        project_id="muse_test",
        session_id="wrong_project_story",
        metadata={"story_production_jobs": {"job": {
            "project_id": "another_project",
            "source_plan_call_id": "plan_other_project",
            "plan": {"plans": [{"panel_id": "panel_01"}]},
        }}},
    )
    assert coordinator_module._is_pending_page_story_continuation(session, "continue", "muse_test") is False


def test_explicit_new_page_story_offers_only_the_planner_to_the_model():
    tools = [
        ToolDefinition(tool_id="planning.plan_panels", name="Plan", domain="planning", purpose="Plan story."),
        ToolDefinition(tool_id="generation.generate_image", name="Generate", domain="generation", purpose="Generate art."),
        ToolDefinition(tool_id="canvas.create_page_from_template", name="Create page", domain="canvas", purpose="Create."),
        ToolDefinition(tool_id="canvas.place_panel_artwork", name="Place", domain="canvas", purpose="Place."),
        ToolDefinition(tool_id="canon.inspect_characters", name="Inspect", domain="canon", purpose="Inspect."),
    ]

    offered = coordinator_module._tools_for_turn(tools, "make quick story 1 page 6 panels about Muse")

    assert [tool.tool_id for tool in offered] == ["planning.plan_panels"]
    assert coordinator_module._needs_model_follow_up(
        "make quick story 1 page 6 panels about Muse",
        [ToolResult(call_id="plan", tool_id="planning.plan_panels", status="success", output={"plans": [{}]})],
        None,
    ) is False


def test_agent_rejects_model_tool_call_outside_image_chat_scope(monkeypatch):
    registry = _Registry()
    bible = SimpleNamespace(
        project_id="muse_test",
        canon_hash="canon_hash",
        bible_version=1,
        characters={"muse": SimpleNamespace(name="Muse")},
    )

    class _OutOfScopeModel:
        def plan_next_action(self, **kwargs):
            if kwargs["iteration"] > 1:
                return None, "No change was made.", None
            return [ToolCall(
                call_id="out_of_scope_text",
                tool_id="editor.add_text_layer",
                arguments={"page_id": "page_01", "panel_id": "panel_01", "text": "Hello"},
            )], None, None

        def _synthesize_grounded_response(self, _user_text, results, _context):
            return results[0].error

    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: bible)
    monkeypatch.setattr("app.api.routers.execution.get_execution_manager", _ExecutionManager)
    coordinator = AgentCoordinator(
        registry=registry,
        model_client=_OutOfScopeModel(),
        session_store=_SessionStore(),
    )
    events = []

    message = coordinator.process_chat_turn(
        project_id="muse_test",
        user_text="Add text to the page",
        session_id="muse_out_of_scope_test",
        offline_mode=True,
        activity_callback=events.append,
    )

    assert registry.calls == []
    assert message.tool_results[0].status == "blocked"
    assert message.tool_results[0].error_code == "ERR_TOOL_OUT_OF_SCOPE"
    assert events == [{
        "call_id": "out_of_scope_text",
        "tool_id": "editor.add_text_layer",
        "status": "blocked",
        "error": "This action is outside the image-generator chat's available tools. No change was made.",
    }]


def test_live_model_instructions_include_authoritative_canvas_panel_state(monkeypatch):
    import httpx
    from app.agent.model_client import AgentModelClient

    captured = {}

    class _Response:
        status_code = 200

        @staticmethod
        def json():
            return {"output": [{
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Use panel_02."}],
            }]}

    def fake_post(_url, **kwargs):
        captured.update(kwargs["json"])
        return _Response()

    monkeypatch.setattr(httpx, "post", fake_post)
    client = AgentModelClient(config=SimpleNamespace(
        model_api_key="unit-test-key",
        muse_spark_model="test-model",
        meta_base_url="https://provider.invalid",
    ))
    _calls, response, _label = client._plan_live_action(
        messages=[{"role": "user", "content": "Add a bubble to the selected panel."}],
        available_tools=[],
        project_context={
            "project_id": "muse_test",
            "canvas_target": {"page_id": "page_01", "panel_id": "panel_02", "expected_revision": 3},
            "canvas_page_context": {"page_id": "page_01", "revision": 3, "panels": [{"panel_id": "panel_02"}]},
        },
    )

    assert response == "Use panel_02."
    assert '"panel_id": "panel_02"' in captured["instructions"]
    assert "Active Canvas page state" in captured["instructions"]


def test_live_model_does_not_inject_project_id_outside_tool_schema(monkeypatch):
    import httpx
    from app.agent.model_client import AgentModelClient

    class _Response:
        status_code = 200

        @staticmethod
        def json():
            return {"output": [{
                "type": "function_call",
                "call_id": "search_call",
                "name": "canvas.search_panel_layout_presets",
                "arguments": '{"query":"four-beat decision scene","limit":5}',
            }]}

    monkeypatch.setattr(httpx, "post", lambda *_args, **_kwargs: _Response())
    client = AgentModelClient(config=SimpleNamespace(
        model_api_key="unit-test-key",
        muse_spark_model="test-model",
        meta_base_url="https://provider.invalid",
    ))
    tool = ToolDefinition(
        tool_id="canvas.search_panel_layout_presets",
        name="Search panel presets",
        domain="canvas",
        purpose="Search panel layout recipes.",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )

    calls, response, _label = client._plan_live_action(
        messages=[{"role": "user", "content": "Find a layout."}],
        available_tools=[tool],
        project_context={"project_id": "default_project"},
    )

    assert response is None
    assert calls[0].arguments == {"query": "four-beat decision scene", "limit": 5}


def test_grounded_tool_success_does_not_pay_for_redundant_final_model_call(monkeypatch):
    registry = _Registry()
    bible = SimpleNamespace(
        project_id="muse_test",
        canon_hash="canon_hash",
        bible_version=1,
        characters={"muse": SimpleNamespace(name="Muse"), "nour": SimpleNamespace(name="Nour")},
    )
    monkeypatch.setattr(coordinator_module, "_get_project_bible", lambda _project_id: bible)
    monkeypatch.setattr("app.api.routers.execution.get_execution_manager", _ExecutionManager)
    coordinator = AgentCoordinator(
        registry=registry,
        model_client=_Model(),
        session_store=_SessionStore(),
    )

    result = coordinator.process_chat_turn(
        project_id="muse_test",
        user_text="Make Muse eat a sandwich",
        session_id="muse_final_reply_failure_test",
        selected_character_ids=["muse"],
        canvas_page_id="page_01",
        canvas_panel_id="panel_02",
        canvas_expected_revision=3,
        offline_mode=True,
    )

    assert any(item.status == "success" for item in result.tool_results)
    assert "Generation completed." in result.text
    assert len(coordinator.model_client.histories) == 1


def test_generation_summary_reports_tool_estimate_when_provider_billing_is_absent():
    from app.agent.model_client import AgentModelClient

    response = AgentModelClient()._synthesize_grounded_response(
        "Generate a panel",
        [ToolResult(
            call_id="generate_panel",
            tool_id="generation.generate_image",
            status="success",
            output={"success": True, "panel_id": "panel_01", "is_simulated": False, "duration_seconds": 20.0, "asset_id": "art_01", "url": "/api/v1/assets/art_01/file"},
            cost_usd=0.01,
        )],
        {"project_id": "default_project"},
    )

    assert "**Estimated cost:** `$0.0100 USD`" in response
    assert "provider billing details were not returned" in response
    assert "Billed Spend: `$0.0000" not in response
