import pytest

from app.agent.schemas import AgentAttachment, AgentMessage
from app.agent.session_store import SessionStore


def _message(message_id, role, text, **kwargs):
    return AgentMessage(message_id=message_id, role=role, text=text, **kwargs)


def test_remove_last_turn_only_removes_latest_prompt_and_reply(tmp_path):
    store = SessionStore(sessions_dir=tmp_path)
    session = store.create_session(project_id="project_a", session_id="session_controls")
    store.append_message(session.session_id, _message("u1", "user", "keep this"))
    store.append_message(session.session_id, _message("a1", "assistant", "kept reply"))
    store.append_message(session.session_id, _message("u2", "user", "delete this"))
    store.append_message(session.session_id, _message("a2", "assistant", "delete reply"))

    updated, removed = store.remove_last_turn(session.session_id, "project_a")

    assert [message.message_id for message in removed] == ["u2", "a2"]
    assert [message.message_id for message in updated.messages] == ["u1", "a1"]
    assert SessionStore(sessions_dir=tmp_path).get_session(session.session_id).messages[-1].text == "kept reply"


def test_session_list_refreshes_changed_transcript_from_another_store_instance(tmp_path):
    writer = SessionStore(sessions_dir=tmp_path)
    reader = SessionStore(sessions_dir=tmp_path)
    session = writer.create_session(project_id="project_a", session_id="live_history")
    assert reader.list_sessions(project_id="project_a")[0].messages == []

    writer.append_message(session.session_id, _message("live_user", "user", "A newly saved creator request"))

    refreshed = reader.list_sessions(project_id="project_a")
    assert len(refreshed) == 1
    assert refreshed[0].messages[0].text == "A newly saved creator request"


def test_session_list_can_return_all_projects_and_uses_prompt_for_untitled_chat(monkeypatch, tmp_path):
    from app.api.routers import agent as agent_router

    store = SessionStore(sessions_dir=tmp_path)
    session_a = store.create_session(project_id="project_a", session_id="history_a")
    session_b = store.create_session(project_id="project_b", session_id="history_b")
    store.append_message(session_a.session_id, _message("u1", "user", "Create a hopeful six-panel story"))
    monkeypatch.setattr(agent_router.SessionStore, "get_instance", lambda: store)

    all_sessions = agent_router.list_sessions()
    project_a_sessions = agent_router.list_sessions(project_id="project_a")

    assert {item["project_id"] for item in all_sessions} == {"project_a", "project_b"}
    assert project_a_sessions[0]["title"] == "Create a hopeful six-panel story"
    assert [item["session_id"] for item in project_a_sessions] == ["history_a"]


def test_remove_last_turn_enforces_project_scope_and_existing_prompt(tmp_path):
    store = SessionStore(sessions_dir=tmp_path)
    session = store.create_session(project_id="project_a", session_id="session_scope")
    with pytest.raises(PermissionError):
        store.remove_last_turn(session.session_id, "project_b")
    with pytest.raises(ValueError, match="no prompt"):
        store.remove_last_turn(session.session_id, "project_a")


def test_delete_last_turn_endpoint_returns_removed_ids(monkeypatch, tmp_path):
    from app.api.routers import agent as agent_router

    store = SessionStore(sessions_dir=tmp_path)
    session = store.create_session(project_id="project_a", session_id="session_delete_endpoint")
    store.append_message(session.session_id, _message("u1", "user", "remove this prompt"))
    store.append_message(session.session_id, _message("a1", "assistant", "remove this answer"))
    monkeypatch.setattr(agent_router.SessionStore, "get_instance", lambda: store)

    result = agent_router.delete_last_turn(session.session_id, project_id="project_a")

    assert result["removed_message_ids"] == ["u1", "a1"]
    assert result["message_count"] == 0


def test_retry_last_turn_replays_saved_prompt_attachments_and_context(monkeypatch, tmp_path):
    from app.api.routers import agent as agent_router
    from app.api.routers.agent import RetryLastTurnRequest

    store = SessionStore(sessions_dir=tmp_path)
    session = store.create_session(project_id="project_a", session_id="session_retry")
    attachment = AgentAttachment(
        attachment_id="attachment_ref_1",
        filename="ref.png",
        mime_type="image/png",
        byte_size=123,
        content_sha256="abc",
        asset_id="asset_ref_1",
    )
    original_user = _message(
        "u1", "user", "draw this exact scene", attachments=[attachment],
        request_context={
            "selected_character_ids": ["muse_id"],
            "selected_style_profile_id": "style_1",
            "selected_style_version": 3,
            "selected_location_id": "place_1",
            "selected_location_version": 2,
            "spend_limit_usd": 0.25,
            "canvas_page_id": "page_1",
            "canvas_panel_id": "panel_02",
            "canvas_expected_revision": 7,
        },
    )
    store.append_message(session.session_id, original_user)
    store.append_message(session.session_id, _message("a1", "assistant", "first failed attempt"))
    calls = {}

    class _Coordinator:
        def process_chat_turn(self, **kwargs):
            calls.update(kwargs)
            retried_user = _message("u2", "user", kwargs["user_text"], attachments=kwargs["attachments"])
            retried_assistant = _message("a2", "assistant", "second attempt")
            store.append_message(session.session_id, retried_user)
            store.append_message(session.session_id, retried_assistant)
            return retried_assistant

    monkeypatch.setattr(agent_router.SessionStore, "get_instance", lambda: store)
    monkeypatch.setattr(agent_router, "get_coordinator", lambda: _Coordinator())

    result = agent_router.retry_last_turn(session.session_id, RetryLastTurnRequest(project_id="project_a"))

    assert result["text"] == "second attempt"
    assert calls["user_text"] == "draw this exact scene"
    assert calls["attachments"][0].asset_id == "asset_ref_1"
    assert calls["selected_character_ids"] == ["muse_id"]
    assert calls["selected_style_profile_id"] == "style_1"
    assert calls["selected_style_version"] == 3
    assert calls["selected_location_id"] == "place_1"
    assert calls["selected_location_version"] == 2
    assert calls["spend_limit_usd"] == 0.25
    assert calls["canvas_page_id"] == "page_1"
    assert calls["canvas_panel_id"] == "panel_02"
    assert calls["canvas_expected_revision"] == 7
    saved = store.get_session(session.session_id)
    assert [message.text for message in saved.messages] == ["draw this exact scene", "second attempt"]
