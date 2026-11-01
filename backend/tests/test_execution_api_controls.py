from fastapi.testclient import TestClient

from app.api.server import create_app
from app.api.routers import execution as execution_router
from app.execution.manager import ExecutionManager
from app.execution.states import RunStatus


def test_run_detail_cancel_resume_and_sse_use_persisted_ledger(tmp_path, monkeypatch):
    manager = ExecutionManager(db_path=tmp_path / "exec.sqlite")
    monkeypatch.setattr(execution_router, "get_execution_manager", lambda: manager)
    monkeypatch.setattr(execution_router, "get_registry", lambda: None)
    client = TestClient(create_app())

    run = manager.create_run(project_id="project_editor_test", run_id="run_cancel_test")
    manager.start_run(run.run_id)
    detail = client.get(f"/api/v1/execution/runs/{run.run_id}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "running"
    assert any(event["event_type"] == "run_started" for event in detail.json()["events"])

    cancelled = client.post(f"/api/v1/execution/runs/{run.run_id}/cancel", json={"reason": "creator_stop"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    interrupted = manager.create_run(project_id="project_editor_test", run_id="run_resume_test")
    manager.start_run(interrupted.run_id)
    manager.db.update_run_status(interrupted.run_id, RunStatus.INTERRUPTED)
    resumed = client.post(f"/api/v1/execution/runs/{interrupted.run_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "running"

    completed = manager.create_run(project_id="project_editor_test", run_id="run_sse_test")
    manager.start_run(completed.run_id)
    manager.complete_run(completed.run_id)
    stream = client.get(f"/api/v1/execution/runs/{completed.run_id}/events/stream")
    assert stream.status_code == 200
    assert "run_created" in stream.text and "stream_complete" in stream.text
