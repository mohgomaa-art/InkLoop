"""
Tests for InkLoop S9 Autonomous Agent Execution Loop.
Verifies that the Agent Coordinator behaves as an autonomous agent that plans,
executes, composites, and delivers comics end-to-end rather than stalling as a chatbot.
"""
import json
import os
import uuid
from unittest.mock import MagicMock
import pytest

from app.config import PROJECT_ROOT
from app.agent.coordinator import (
    AgentCoordinator,
    _needs_model_follow_up,
    _find_matching_saved_plan_for_story,
    _extract_story_title_and_hash,
    MAX_TOOL_ROUNDS,
)
from app.agent.production import production_action_requested
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import ToolResult
from app.agent.session_store import SessionStore


def _use_simulated_e1_boundary(monkeypatch):
    """Keep production-loop tests deterministic and prevent live image spend."""
    registry = CapabilityRegistry.get_instance()
    real_adapter = registry._adapters["generation.generate_image"]
    monkeypatch.setitem(
        registry._adapters,
        "generation.generate_image",
        lambda args, ctx: real_adapter(args, {**ctx, "offline_mode": True}),
    )


def test_max_tool_rounds_is_expanded_for_agentic_loop():
    assert MAX_TOOL_ROUNDS >= 8


def test_affirmative_action_words_recognized_by_needs_model_follow_up():
    inspection_result = ToolResult(
        call_id="call_inspect",
        tool_id="canon.inspect_characters",
        status="success",
        output={"characters": ["char_nour"]},
    )
    # These confirmation/execution words must NOT cause premature loop termination
    assert _needs_model_follow_up("start", [inspection_result], None)
    assert _needs_model_follow_up("yes pls", [inspection_result], None)
    assert _needs_model_follow_up("proceed", [inspection_result], None)
    assert _needs_model_follow_up("go ahead", [inspection_result], None)
    assert _needs_model_follow_up("do it", [inspection_result], None)
    assert _needs_model_follow_up("continue", [inspection_result], None)
    assert _needs_model_follow_up("ابدأ", [inspection_result], None)


def test_production_action_requested_matches_execution_commands():
    # Direct execution commands
    assert production_action_requested("start")
    assert production_action_requested("proceed")
    assert production_action_requested("go ahead")
    assert production_action_requested("do it")
    assert production_action_requested("continue")
    assert production_action_requested("add to canvas")
    assert production_action_requested("ابدأ")
    assert production_action_requested("تابع")

    # Pure affirmations accept an offer but are NOT direct execution commands
    assert not production_action_requested("yes pls")
    assert not production_action_requested("yes please")

    # Long narrative story text containing prose words like 'continue' or 'finish'
    # must NOT falsely trigger immediate production
    story_prose = (
        "Part One: The Challenge. I needed something I could finish and defend. "
        "Could an agent investigate rather than continue executing blindly? "
        "We decided to build the smallest version that proves the capability."
    )
    assert not production_action_requested(story_prose)


def test_history_compacting_reduces_story_tokens():
    """Verifies that previous user story turns > 300 chars are compacted in model history."""
    story_text = "# The $150 Mistake\n" + ("A" * 800)
    title, digest = _extract_story_title_and_hash(story_text)
    assert "150" in title or "Mistake" in title
    assert len(digest) == 64


def test_exact_plan_matching_reuses_8_panel_plan_for_real_one():
    """Verifies that 'The $150 Mistake' in project 'real_one_6675e532' reuses the saved 8-panel plan."""
    saved_session_file = PROJECT_ROOT / "runs" / "agent_sessions" / "session_1793338404482_0mp80.json"
    if not saved_session_file.exists():
        pytest.skip("Saved session file not present in repository")

    with open(saved_session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    story_text = data["messages"][0]["text"]

    matched_plan, plan_cid = _find_matching_saved_plan_for_story("real_one_6675e532", story_text)
    assert matched_plan is not None
    assert plan_cid == "call_ac5b836c-8791-4102-b651-fbe9edfe1215"
    assert len(matched_plan.get("plans", [])) == 8


def test_changed_story_hash_rejects_old_plan_and_creates_fresh_plan():
    """Verifies that an unrelated story text does not reuse an existing plan with a different hash."""
    unrelated_story = (
        "In deep space, Captain Zephyr navigated the asteroid field toward the forgotten derelict station. "
        "Scanners detected an anomalous quantum signature emanating from the primary reactor core. "
        "Preparing the docking clamps, the crew readied their atmospheric suits for the zero-gravity EVA."
    )
    matched_plan, plan_cid = _find_matching_saved_plan_for_story("real_one_6675e532", unrelated_story)
    assert matched_plan is None
    assert plan_cid is None


def test_exact_sequence_paste_story_yes_pls_then_start_reuses_8_panel_plan(monkeypatch):
    """
    Reproduces the exact sequence from the user audit:
    Turn 1: Paste full story 'The $150 Mistake' into project 'real_one_6675e532'.
            -> Verifies pending story action is recorded with status='plan_ready'.
    Turn 2: User responds 'yes pls'.
            -> Verifies it reuses the matching 8-panel plan (call_ac5b836c-8791-4102-b651-fbe9edfe1215).
            -> Verifies status='plan_ready', panel_count=8, 0 tool calls executed (no random diagnostics).
            -> Verifies 'Comic Adaptation Plan Ready' review message.
    Turn 3: User responds 'start'.
            -> Verifies coordinator resumes the saved plan directly without re-asking the model.
            -> Verifies Canvas assembly, composite page, and comic export are executed.
            -> Verifies job status='completed' and Canvas links are returned.
    """
    if os.getenv("INKLOOP_RUN_REPO_DATA_MUTATION_TESTS") != "1":
        pytest.skip("This legacy scenario reads and mutates the persistent real_one project; run only against an isolated project-data clone.")
    saved_session_file = PROJECT_ROOT / "runs" / "agent_sessions" / "session_1793338404482_0mp80.json"
    if not saved_session_file.exists():
        pytest.skip("Saved session file not present in repository")

    with open(saved_session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    story_text = data["messages"][0]["text"]

    project_id = "real_one_6675e532"
    session_id = f"test_session_exact_seq_{uuid.uuid4().hex[:6]}"
    _use_simulated_e1_boundary(monkeypatch)

    mock_client = MagicMock()
    mock_client.plan_next_action.return_value = (
        None,
        "Love the setup — accidental win turning into a real build constraint is a great hook. Do you want me to turn this Part One into a comic page, and if so with how many panels?",
        None,
    )
    mock_client.last_usage = None
    mock_client._synthesize_grounded_response.return_value = "Comic production completed successfully."

    coord = AgentCoordinator(model_client=mock_client)

    # --- Turn 1: Post Story ---
    msg_1 = coord.process_chat_turn(
        project_id=project_id,
        user_text=story_text,
        session_id=session_id,
        offline_mode=False,
    )
    assert msg_1.pending_story_action is not None
    assert msg_1.pending_story_action.panel_count == 8

    # --- Turn 2: 'yes pls' (Affirmation & Plan Ready Review) ---
    msg_2 = coord.process_chat_turn(
        project_id=project_id,
        user_text="yes pls",
        session_id=session_id,
        offline_mode=False,
    )
    assert msg_2.pending_story_action is not None
    assert msg_2.pending_story_action.status == "plan_ready"
    assert msg_2.pending_story_action.panel_count == 8
    assert msg_2.pending_story_action.plan_call_id == "call_ac5b836c-8791-4102-b651-fbe9edfe1215"
    assert len(msg_2.tool_calls or []) == 0  # No premature or diagnostic tool calls!
    assert "Comic Adaptation Plan Ready" in msg_2.text

    # --- Turn 3: 'start' (Direct Execution of Saved Plan) ---
    msg_3 = coord.process_chat_turn(
        project_id=project_id,
        user_text="start",
        session_id=session_id,
        offline_mode=False,
    )
    assert msg_3.pending_story_action is not None
    assert msg_3.pending_story_action.status == "completed"

    executed_tools = [call.tool_id for call in (msg_3.tool_calls or [])]
    assert "canvas.create_page_from_template" in executed_tools
    assert "canvas.composite_page" in executed_tools
    assert "export.generate_comic_book" in executed_tools
    generated_results = [result for result in msg_3.tool_results if result.tool_id == "generation.generate_image"]
    assert len(generated_results) == 8
    assert all(result.output and result.output.get("is_simulated") is True for result in generated_results)

    assert msg_3.production_job is not None
    assert msg_3.production_job.get("status") == "completed"
    assert len(msg_3.production_job.get("panels", {})) == 8
    assert all(panel["status"] == "placed" for panel in msg_3.production_job["panels"].values())
    from app.api.routers.editor import get_page_store
    from app.editor.models import LayerKind
    for page in msg_3.production_job["pages"]:
        document = get_page_store().get(page["page_id"])
        for panel_id in page["panel_ids"]:
            assert any(layer.kind == LayerKind.IMAGE and layer.panel_id == panel_id for layer in document.layers)

    # Canvas page and PDF download links present in message text
    assert "Download Print-Ready PDF" in msg_3.text
    assert "api/v1/assets" in msg_3.text


def test_new_unmatched_story_starts_without_replanning_and_reports_simulated_art_truthfully(monkeypatch):
    """
    Verifies that a new unmatched story:
    1. Creates one outline with sensible default panel count on 'yes pls'.
    2. 'start' executes that outline without replanning.
    """
    project_id = f"test_proj_unmatched_{uuid.uuid4().hex[:6]}"
    session_id = f"session_{project_id}"
    _use_simulated_e1_boundary(monkeypatch)

    new_story = (
        "# The Crystal Caverns\n"
        "### Chapter 1: The Descent\n"
        "Nour stepped through the luminescent archway into the subterranean cave system. "
        "Bioluminescent fungi cast an ethereal azure glow across the jagged stalactites hanging above. "
        "A distant resonant chime echoed through the chambers as the crystalline pillars harmonized. "
        "She consulted her holographic datapad to calibrate the resonance frequencies. "
        "Deep within the central vault, the dormant planetary core began to awaken with pulsing radiance."
    )

    mock_client = MagicMock()
    mock_client.plan_next_action.return_value = (
        None,
        "Would you like me to adapt this story into a comic page?",
        None,
    )
    mock_client.last_usage = None
    mock_client._synthesize_grounded_response.return_value = "Production finished."

    coord = AgentCoordinator(model_client=mock_client)

    # Turn 1: Post story
    msg_1 = coord.process_chat_turn(
        project_id=project_id,
        user_text=new_story,
        session_id=session_id,
        offline_mode=False,
    )
    assert msg_1.pending_story_action is not None

    # Turn 2: 'yes pls' -> prepares source-grounded outline
    msg_2 = coord.process_chat_turn(
        project_id=project_id,
        user_text="yes pls",
        session_id=session_id,
        offline_mode=False,
    )
    assert msg_2.pending_story_action is not None
    assert msg_2.pending_story_action.status == "plan_ready"
    assert msg_2.pending_story_action.panel_count >= 1

    # Turn 3: 'start' -> executes production directly
    msg_3 = coord.process_chat_turn(
        project_id=project_id,
        user_text="start",
        session_id=session_id,
        offline_mode=False,
    )
    assert msg_3.pending_story_action is not None
    # This test deliberately routes E1 through its offline simulated boundary.
    # Simulated art must not be reported as a finished production job or
    # handed off for composite/export.
    assert msg_3.pending_story_action.status == "needs_attention"

    executed_tools = [c.tool_id for c in (msg_3.tool_calls or [])]
    assert "canvas.create_custom_page" in executed_tools
    assert "canvas.inspect_page_spacing" in executed_tools
    assert "generation.generate_image" in executed_tools
    assert "canvas.composite_page" not in executed_tools
    assert "export.generate_comic_book" not in executed_tools
    assert "0/5 panels placed" in msg_3.text
