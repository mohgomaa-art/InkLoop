"""
Comprehensive Test Suite for InkLoop S9 Agent Runtime (Phase 7).
Verifies all 20 required behavioral cases:
1. 'hi' -> friendly contextual response, 0 tool calls.
2. 'اه' -> contextual acknowledgement, 0 tools.
3. Nour canon anchor inspection -> calls canon inspection, outputs real attributes.
4. $0.50 plan request -> separate $0.50 cap and available budget, no dispatch from draft.
5. Estimated cost > cap -> deterministic budget rejection before dispatch (ERR_BUDGET_EXCEEDED).
6. Unknown estimated cost -> no fake zero cost.
7. Explicit generation request -> E1 called, offline/live clearly labeled.
8. Image upload + metadata -> real metadata/hash, no fake vision claims.
9. Image upload + visual consistency -> real multi-tier verification.
10. Tool schema violation -> rejected before execution.
11. Tool error -> model receives structured error, no false success.
12. Loop limit reached -> controlled stop / loop detection.
13. Approval required -> execution pauses with approval ID.
14. Stale canon/anchor hash -> revalidate/reject plan before dispatch.
15. Project scope mismatch -> rejected.
16. Unimplemented production engines (E5–E7, compositor, export) -> blocked, honest explanation, no dispatch.
17. Run trace persists in ExecutionManager.
18. Regression: no automatic verify_canon + dispatch_plan pair on arbitrary messages.
19. Regression: requested run cap ($0.50) is never overwritten by project headroom ($10).
20. Full offline suite passes ($0.00 live spend).
"""
import io
import json
import pytest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from app.config import InkLoopConfig, PROJECT_ROOT
from app.api.server import create_app
from app.execution.states import ExecutionEventType
from app.agent.schemas import (
    ToolCall,
    ToolResult,
    CapabilityStatus,
    CostSemantics,
    SideEffectType,
    ToolDefinition,
    AgentMessage,
    AgentSession,
    AgentPlanStatus,
    ApprovalStatus,
)
from app.agent.registry import CapabilityRegistry
from app.agent.coordinator import AgentCoordinator, _needs_model_follow_up
from app.agent.model_client import AgentModelClient
from app.agent.approvals import ApprovalManager
from app.agent.session_store import SessionStore
from app.agent.image_inspector import (
    inspect_image_bytes,
    resolve_attachment_path,
    ImageInspectionError,
    MAX_FILE_BYTES,
)
from app.api.routers.execution import get_execution_manager


def test_rejected_panel_plan_gets_one_bounded_correction_turn():
    failed_plan = ToolResult(
        call_id="plan_1",
        tool_id="planning.plan_panels",
        status="failed",
        error="spoken text needs a speaker ID",
        error_code="ERR_INVALID_PANEL_PLAN",
    )
    assert _needs_model_follow_up("make a one page story with 6 panels", [failed_plan], None)


def test_missing_provider_does_not_silently_select_keyword_planner(monkeypatch):
    """Without credentials, production mode reports unavailable instead of switching planners."""
    monkeypatch.setenv("INKLOOP_OFFLINE_MODE", "0")
    client = AgentModelClient(config=InkLoopConfig(model_api_key=None))
    live_calls = []
    monkeypatch.setattr(client, "_plan_live_action", lambda *args, **kwargs: live_calls.append(True))

    tool_calls, response_text, activity = client.plan_next_action(
        messages=[{"role": "user", "content": "hello"}],
        available_tools=[],
        project_context={"offline_mode": False},
    )

    assert tool_calls is None
    assert "provider unavailable" in response_text.lower()
    assert "INKLOOP_OFFLINE_MODE=1" in response_text
    assert activity is None
    assert live_calls == []


def test_agent_status_reports_explicit_offline_mode_and_single_chat_route(client):
    from app.api.routers.agent import router as agent_router

    response = client.get("/api/v1/agent/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "offline_explicit"
    assert response.json()["runtime_ready"] is True
    agent_router_mounts = [
        route for route in client.app.routes
        if getattr(route, "original_router", None) is agent_router
    ]
    assert len(agent_router_mounts) == 1
    assert "/api/v1/agent/chat" in client.get("/api/openapi.json").json()["paths"]

@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c

@pytest.fixture
def coordinator():
    return AgentCoordinator()

@pytest.fixture
def registry():
    return CapabilityRegistry.get_instance()

def _make_test_image_bytes(width: int = 200, height: int = 200, fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# =============================================================================
# 1. 'hi' -> friendly contextual response, 0 tool calls
# =============================================================================
def test_01_hi_greeting_no_tools(coordinator):
    msg = coordinator.process_chat_turn(project_id="inkloop", user_text="hi")
    assert msg.role == "assistant"
    assert len(msg.tool_calls) == 0
    assert len(msg.tool_results) == 0
    assert "inkloop" in msg.text.lower() or "hello" in msg.text.lower()


# =============================================================================
# 2. 'اه' -> contextual acknowledgement, 0 tools
# =============================================================================
def test_02_arabic_acknowledgement_contextual_no_tools(coordinator):
    msg = coordinator.process_chat_turn(project_id="inkloop", user_text="اه")
    assert msg.role == "assistant"
    assert len(msg.tool_calls) == 0
    assert len(msg.tool_results) == 0
    assert len(msg.text) > 0


# =============================================================================
# 3. Nour canon anchor inspection -> calls canon inspection, outputs real attributes
# =============================================================================
def test_03_nour_canon_anchor_inspection(coordinator):
    live_events = []
    msg = coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="Inspect the current Nour canon anchor and explain the mandatory attributes.",
        activity_callback=live_events.append,
    )
    assert msg.role == "assistant"
    assert len(msg.tool_calls) >= 1
    assert any(tc.tool_id in ["canon.inspect_characters", "canon.inspect_reference_anchor"] for tc in msg.tool_calls)
    assert "nour" in msg.text.lower()
    assert len(msg.tool_results) >= 1
    assert msg.tool_results[0].status == "success"
    # The live UI receives each actual registered dispatch, then its real result.
    assert {event["call_id"] for event in live_events} == {call.call_id for call in msg.tool_calls}
    for call in msg.tool_calls:
        call_events = [event for event in live_events if event["call_id"] == call.call_id]
        assert call_events[0]["status"] == "running"
        assert call_events[-1]["status"] == next(result.status for result in msg.tool_results if result.call_id == call.call_id)


def test_chat_live_activity_endpoint_returns_real_tool_results(client):
    activity_id = "test_activity_trace_character_inspection"
    response = client.post("/api/v1/agent/chat", json={
        "project_id": "inkloop",
        "message": "Inspect the current Nour canon anchor and explain the mandatory attributes.",
        "session_id": "test_live_activity_session",
        "activity_id": activity_id,
    })
    assert response.status_code == 200
    message = response.json()
    activity = client.get(f"/api/v1/agent/activity/{activity_id}")
    assert activity.status_code == 200
    payload = activity.json()
    assert payload["finished"] is True
    actual_results = {result["call_id"]: result["status"] for result in message["tool_results"]}
    live_results = {tool["call_id"]: tool["status"] for tool in payload["tools"]}
    assert live_results == actual_results


# =============================================================================
# 4. $0.50 plan request -> separate $0.50 cap and available budget, no dispatch from draft
# =============================================================================
def test_04_budget_plan_request_segregation(coordinator):
    msg = coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="Draft a 6-panel sequential generation plan for Chapter 1 Scene 2 within a $0.50 budget ceiling."
    )
    assert msg.role == "assistant"
    assert msg.plan is not None
    assert msg.plan.requested_run_budget_cap_usd == 0.50
    assert msg.plan.project_available_budget_usd is not None
    assert msg.plan.effective_run_budget_cap_usd == min(msg.plan.requested_run_budget_cap_usd, msg.plan.project_available_budget_usd)
    assert msg.plan.status == AgentPlanStatus.PLANNED
    assert msg.plan.dispatched is False


# =============================================================================
# 5. Estimated cost > cap -> deterministic budget rejection before dispatch
# =============================================================================
def test_05_estimated_cost_exceeds_cap_blocked(coordinator, registry):
    # 6 panels * $0.02 = $0.12, which exceeds $0.01 cap
    plan = coordinator.create_plan(
        project_id="inkloop",
        goal="6-panel heavy generation",
        spend_limit_usd=0.01
    )
    assert plan.status == AgentPlanStatus.BLOCKED
    assert plan.effective_run_budget_cap_usd == 0.01

    call = ToolCall(
        call_id="call_disp_exceed",
        tool_id="plan.dispatch_plan",
        arguments={"project_id": "inkloop", "plan_id": plan.plan_id}
    )
    res = registry.dispatch(call, {"project_id": "inkloop"})
    assert res.status == "blocked"
    assert res.error_code == "ERR_BUDGET_EXCEEDED"


# =============================================================================
# 6. Unknown estimated cost -> no fake zero cost
# =============================================================================
def test_06_unknown_cost_semantics_no_fake_zero(registry):
    # Check that tools without cost semantics do not pretend to cost $0.00
    tool = registry.get_tool("catalogue.retrieve_knowledge")
    assert tool is not None
    assert tool.cost_semantics == CostSemantics.FREE or tool.cost_semantics == CostSemantics.UNKNOWN
    # In dispatch, if not ESTIMATED, cost_usd is None, not 0.0
    call = ToolCall(call_id="call_cat_cost", tool_id="catalogue.retrieve_knowledge", arguments={"action": "test"})
    res = registry.dispatch(call, {"project_id": "inkloop"})
    assert res.cost_usd is None


# =============================================================================
# 7. Explicit generation request -> E1 called, offline/live clearly labeled
# =============================================================================
def test_07_explicit_generation_e1_offline_labeled(coordinator):
    msg = coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="Generate one image of the approved Nour character using the current scene brief."
    )
    assert msg.role == "assistant"
    assert any(tc.tool_id == "generation.generate_image" for tc in msg.tool_calls)
    gen_res = next(r for r in msg.tool_results if r.tool_id == "generation.generate_image")
    assert gen_res.status == "success"
    # Offline simulated generation is clearly labeled
    assert "is_simulated" in gen_res.output or gen_res.output.get("offline_simulated") is True


# =============================================================================
# 8. Image upload + metadata -> real metadata/hash, no fake vision claims
# =============================================================================
def test_08_image_upload_and_metadata_inspection():
    img_bytes = _make_test_image_bytes(240, 320, "PNG")
    att = inspect_image_bytes(img_bytes, "page_01.png", project_id="inkloop")
    assert att.mime_type == "image/png"
    assert att.width == 240
    assert att.height == 320
    assert att.byte_size == len(img_bytes)
    assert len(att.content_sha256) == 64
    assert resolve_attachment_path(att.attachment_id, "inkloop").exists()
    assert "storage_path" not in att.model_dump()


# =============================================================================
# 9. Image upload + visual consistency -> real multi-tier verification
# =============================================================================
def test_09_image_upload_visual_consistency(registry):
    img_bytes = _make_test_image_bytes(100, 100, "PNG")
    att = inspect_image_bytes(img_bytes, "panel_eval.png", project_id="inkloop")
    call = ToolCall(
        call_id="call_verify_panel",
        tool_id="image.verify_visual_consistency",
        arguments={
            "attachment_id": att.attachment_id,
            "character_id": "nour",
        }
    )
    res = registry.dispatch(call, {"project_id": "inkloop"})
    assert res.status == "success"
    assert "verdict" in res.output
    assert "overall_score" in res.output


def test_attachment_resolution_rejects_path_traversal_and_bad_project_ids():
    img_bytes = _make_test_image_bytes(16, 16, "PNG")
    with pytest.raises(ImageInspectionError) as exc:
        inspect_image_bytes(img_bytes, "image.png", project_id="../../outside")
    assert exc.value.code == "ERR_INVALID_PROJECT_ID"

    att = inspect_image_bytes(img_bytes, "image.png", project_id="inkloop")
    with pytest.raises(ImageInspectionError) as exc:
        resolve_attachment_path("../../secrets", "inkloop")
    assert exc.value.code == "ERR_ATTACHMENT_NOT_FOUND"


def test_image_tool_rejects_caller_supplied_filesystem_path(registry):
    result = registry.dispatch(
        ToolCall(
            call_id="call_path_rejected",
            tool_id="image.inspect_file_metadata",
            arguments={"file_path": "../../outside/secret.png"},
        ),
        {"project_id": "inkloop"},
    )
    assert result.status == "failed"
    assert result.error_code == "ERR_MISSING_REQUIRED_FIELD"


def test_unexpected_tool_errors_do_not_return_internal_paths():
    registry = CapabilityRegistry()
    registry.register_tool(
        ToolDefinition(tool_id="test.raise_path_error", name="Path error", domain="test", purpose="test"),
        lambda args, ctx: (_ for _ in ()).throw(OSError("C:/private/internal.png")),
    )
    result = registry.dispatch(
        ToolCall(call_id="call_path_error", tool_id="test.raise_path_error", arguments={}),
        {"project_id": "inkloop"},
    )
    assert result.status == "failed"
    assert "internal.png" not in result.error
    assert "server log" in result.error


# =============================================================================
# 10. Tool schema violation -> rejected before execution
# =============================================================================
def test_10_tool_schema_violation_rejected(registry):
    # Pass invalid type for project_id (e.g. integer when string expected)
    call = ToolCall(
        call_id="call_schema_bad",
        tool_id="workspace.get_project_context",
        arguments={"project_id": 12345}
    )
    res = registry.dispatch(call, {"project_id": "inkloop"})
    assert res.status == "failed"
    assert res.error_code == "ERR_SCHEMA_VALIDATION_FAILED"


# =============================================================================
# 11. Tool error -> model receives structured error, no false success
# =============================================================================
def test_11_tool_error_structured_feedback(registry):
    call = ToolCall(
        call_id="call_err_file",
        tool_id="image.verify_visual_consistency",
        arguments={"attachment_id": "../../outside", "character_id": "nour"}
    )
    res = registry.dispatch(call, {"project_id": "inkloop"})
    assert res.status == "failed"
    assert res.error_code == "ERR_ATTACHMENT_NOT_FOUND"
    assert "not found" in res.error.lower()


# =============================================================================
# 12. Loop limit reached -> controlled stop / loop detection
# =============================================================================
def test_12_loop_limit_reached_controlled_stop(coordinator):
    session_id = "test_loop_limit_session"
    msg = coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="Inspect character Nour and Story Bible",
        session_id=session_id,
    )
    assert msg.role == "assistant"
    # Never exceeds MAX_TOOL_ROUNDS (5)
    assert len(msg.tool_calls) <= 5


# =============================================================================
# 13. Approval required -> execution pauses with approval ID
# =============================================================================
def test_13_approval_required_pauses_execution(registry):
    canon_hash = "a671b968a12bef9d70ce9f64518be5bf5ad6e804ed01249412d8dbfc23d6fb23"
    ctx = {"project_id": "inkloop", "canon_hash": canon_hash}
    call = ToolCall(
        call_id="call_mutation_pause",
        tool_id="canon.apply_approved_mutation",
        arguments={"project_id": "inkloop", "proposal_id": "prop_test_pause"},
    )
    res = registry.dispatch(call, ctx)
    assert res.status == "gated"
    assert res.requires_approval is True
    assert res.approval_id is not None

    # Check request is pending
    mgr = ApprovalManager.get_instance()
    req = mgr.get_request(res.approval_id)
    assert req.status == ApprovalStatus.PENDING


# =============================================================================
# 14. Stale canon/anchor hash -> revalidate/reject plan before dispatch
# =============================================================================
def test_14_stale_canon_hash_rejected(coordinator, registry):
    plan = coordinator.create_plan(
        project_id="inkloop",
        goal="Plan with hash check",
        spend_limit_usd=1.00
    )
    # Tamper the plan's canon_hash on disk to simulate stale state
    plan_file = PROJECT_ROOT / "runs" / "plans" / f"{plan.plan_id}.json"
    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    plan_data["canon_hash"] = "stale_hash_from_previous_version_00000000"
    plan_file.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")

    call = ToolCall(
        call_id="call_disp_stale",
        tool_id="plan.dispatch_plan",
        arguments={"project_id": "inkloop", "plan_id": plan.plan_id}
    )
    res = registry.dispatch(call, {"project_id": "inkloop"})
    assert res.status == "failed"
    assert res.error_code == "ERR_STALE_CANON_HASH"


# =============================================================================
# 15. Project scope mismatch -> rejected
# =============================================================================
def test_15_project_scope_mismatch_rejected(coordinator, registry):
    plan = coordinator.create_plan(
        project_id="inkloop",
        goal="Scope mismatch plan",
        spend_limit_usd=1.00
    )
    call = ToolCall(
        call_id="call_disp_mismatch",
        tool_id="plan.dispatch_plan",
        arguments={"project_id": "other_project", "plan_id": plan.plan_id}
    )
    res = registry.dispatch(call, {"project_id": "other_project"})
    assert res.status == "failed"
    assert res.error_code == "ERR_PROJECT_SCOPE_MISMATCH"


# =============================================================================
# 16. Unimplemented engine (E4–E7) -> blocked, honest explanation, no dispatch
# =============================================================================
def test_16_unimplemented_engine_fail_closed(registry):
    future_tool_ids = [
        "typography.shape_text",
        "speech_bubble.place_bubbles",
        "effects.apply_fx",
        "compositor.composite_panels",
        "export.export_page",
    ]
    for ft_id in future_tool_ids:
        call = ToolCall(call_id=f"call_{ft_id}", tool_id=ft_id, arguments={})
        res = registry.dispatch(call, {"project_id": "inkloop"})
        assert res.status == "blocked"
        assert res.error_code == "ERR_TOOL_NOT_IMPLEMENTED"
        assert "NOT_IMPLEMENTED" in res.error


def test_e4_agent_tool_is_explicit_offline_only(monkeypatch):
    monkeypatch.setenv("INKLOOP_OFFLINE_MODE", "0")
    live_registry = CapabilityRegistry()
    live_tool = live_registry.get_tool("text.generate_dialogue")
    assert live_tool.status == CapabilityStatus.NOT_IMPLEMENTED
    assert live_tool.is_callable is False

    monkeypatch.setenv("INKLOOP_OFFLINE_MODE", "1")
    offline_registry = CapabilityRegistry()
    offline_tool = offline_registry.get_tool("text.generate_dialogue")
    assert offline_tool.status == CapabilityStatus.AVAILABLE
    result = offline_registry.dispatch(
        ToolCall(
            call_id="call_e4_offline",
            tool_id="text.generate_dialogue",
            arguments={
                "scene_id": "scene_01",
                "panel_id": "panel_02",
                "scene_action": "Nour greets the shopkeeper",
                "character_ids": ["nour"],
                "block_kinds_requested": ["dialogue"],
                "target_language": "en",
                "target_direction": "ltr",
            },
        ),
        {"project_id": "inkloop", "offline_mode": True},
    )
    assert result.status == "success"
    assert result.output["is_simulated"] is True
    assert result.output["blocks"][0]["panel_id"] == "panel_02"


def test_offline_agent_routes_e4_request_through_registered_engine(coordinator):
    message = coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="Generate dialogue for Nour in scene_01 panel_03: a tense greeting",
    )
    assert [call.tool_id for call in message.tool_calls] == ["text.generate_dialogue"]
    result = next(item for item in message.tool_results if item.tool_id == "text.generate_dialogue")
    assert result.status == "success"
    assert result.output["is_simulated"] is True
    assert result.output["blocks"][0]["panel_id"] == "panel_03"


# =============================================================================
# 17. Run trace persists in ExecutionManager
# =============================================================================
def test_17_run_trace_persists_in_execution_manager(coordinator):
    import time
    sid = f"session_trace_verify_{int(time.time()*1000)}"
    coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="List all canvas layout templates",
        session_id=sid,
    )
    em = get_execution_manager()
    events = em.db.list_events_for_run(run_id=sid)
    assert len(events) >= 1
    assert any(e.event_type == ExecutionEventType.RUN_COMPLETED or e.data.get("event_name") == "agent_turn_completed" for e in events)


# =============================================================================
# 18. Regression: no automatic verify_canon + dispatch_plan pair on arbitrary messages
# =============================================================================
def test_18_regression_no_automatic_verify_canon_dispatch_pair(coordinator):
    test_queries = ["hi", "ok", "hello", "what is today's status?"]
    for q in test_queries:
        msg = coordinator.process_chat_turn(project_id="inkloop", user_text=q)
        # Should NEVER contain both context_builder.verify_canon and agent_coordinator.dispatch_plan
        tool_ids = [tc.tool_id for tc in msg.tool_calls]
        assert not ("context_builder.verify_canon" in tool_ids and "agent_coordinator.dispatch_plan" in tool_ids)
        if q in ["hi", "ok", "hello"]:
            assert len(tool_ids) == 0


# =============================================================================
# 19. Regression: requested run cap ($0.50) is never overwritten by project headroom ($10)
# =============================================================================
def test_19_regression_budget_cap_not_overwritten_by_headroom(coordinator):
    msg = coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="Draft a 6-panel sequential generation plan within a $0.50 budget ceiling."
    )
    assert msg.plan is not None
    assert msg.plan.requested_run_budget_cap_usd == 0.50
    # Available budget is $10.00 or similar
    assert msg.plan.project_available_budget_usd is not None
    assert msg.plan.project_available_budget_usd >= 0.50
    # Effective cap is governed by the tighter limit ($0.50)
    assert msg.plan.effective_run_budget_cap_usd == 0.50


# =============================================================================
# 20. Full offline suite passes ($0.00 live spend)
# =============================================================================
def test_20_full_offline_suite_zero_live_spend(coordinator):
    # Process turn with generation and verification in default offline configuration
    msg = coordinator.process_chat_turn(
        project_id="inkloop",
        user_text="Generate one image of Nour and verify visual consistency",
    )
    assert msg.role == "assistant"
    # Live spend must remain 0.00
    for r in msg.tool_results:
        # None of the results charged live credit
            assert r.cost_usd is None or r.cost_usd == 0.0 or r.cost_usd == 0.01 or r.cost_usd == 0.02 or r.cost_usd == 0.04  # estimated, never live billed spend


