"""
Execution Management, Decimal Budgets & Event Ledger API Router.
Enforces multi-scope decimal budget ceilings, atomic reservations, append-only event auditing,
and crash recovery reconciliation.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncIterator
import asyncio
import json
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from app.config import PROJECT_ROOT
from app.execution.manager import ExecutionManager
from app.execution.budget_manager import BudgetScope
from app.execution.errors import ExecutionError
from app.execution.states import RunStatus
from app.storage.registry import AssetNotFoundError, AssetIntegrityError
from app.api.routers.assets import get_registry

router = APIRouter(prefix="/execution", tags=["Execution & Budgets"])

class CancelRunRequest(BaseModel):
    reason: str = Field(default="user_cancelled", max_length=300)

_execution_manager_instance: Optional[ExecutionManager] = None

def get_execution_manager() -> ExecutionManager:
    global _execution_manager_instance
    if _execution_manager_instance is None:
        db_path = PROJECT_ROOT / "runs" / "execution.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _execution_manager_instance = ExecutionManager(db_path=db_path)
    return _execution_manager_instance

@router.get("/budgets")
def get_budgets(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve multi-scope decimal budget allowances, reservations, and spends."""
    em = get_execution_manager()
    bm = em.budget_manager
    
    global_avail = bm.get_available_budget(BudgetScope.GLOBAL)
    project_avail = bm.get_available_budget(BudgetScope.PROJECT, project_id) if project_id else None

    return {
        "global_cap_usd": float(bm.global_cap_usd),
        "available_global_usd": float(global_avail),
        "project_caps": {k: float(v) for k, v in bm.project_caps.items()},
        "run_caps": {k: float(v) for k, v in bm.run_caps.items()},
        "project_available_usd": float(project_avail) if project_avail is not None else None,
        "precision": "4_decimal_places",
        "accounting_mode": "strict_decimal_minor_units",
    }

@router.get("/runs")
def list_execution_runs() -> List[Dict[str, Any]]:
    """List execution run records with statuses, attempt counts, and durations."""
    em = get_execution_manager()
    runs = em.db.list_runs()
    return [r.model_dump() for r in runs]

@router.get("/runs/{run_id}")
def get_execution_run(run_id: str) -> Dict[str, Any]:
    """Return one run with its real operations, attempts, and ledger events."""
    em = get_execution_manager()
    run = em.db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"message": f"Run '{run_id}' was not found."})
    return {
        "run": run.model_dump(mode="json"),
        "operations": [op.model_dump(mode="json") for op in em.db.list_operations_for_run(run_id)],
        "events": [event.model_dump(mode="json") for event in em.db.list_events_for_run(run_id)],
    }

@router.post("/runs/{run_id}/cancel")
def cancel_execution_run(run_id: str, request: CancelRunRequest = CancelRunRequest()) -> Dict[str, Any]:
    try:
        result = get_execution_manager().cancel_run(run_id, reason=request.reason)
        return result.model_dump(mode="json")
    except ExecutionError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc)})

@router.post("/runs/{run_id}/resume")
def resume_execution_run(run_id: str) -> Dict[str, Any]:
    registry = get_registry()
    def check_asset(asset_id: str, expected_hash: str) -> bool:
        try:
            resolved = registry.resolve_asset(asset_id, verify_integrity=True)
            return resolved.metadata.content_sha256 == expected_hash
        except (AssetNotFoundError, AssetIntegrityError):
            return False
    try:
        result = get_execution_manager().resume_run(run_id, asset_checker=check_asset)
        return result.model_dump(mode="json")
    except ExecutionError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc)})

@router.get("/runs/{run_id}/events/stream")
async def stream_execution_events(run_id: str, request: Request, after: int = 0, poll_ms: int = 900):
    """Stream append-only run events from SQLite as SSE; cursor is event list position."""
    em = get_execution_manager()
    if em.db.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail={"message": f"Run '{run_id}' was not found."})
    poll_seconds = min(max(poll_ms, 250), 5000) / 1000
    async def event_stream() -> AsyncIterator[str]:
        cursor = max(after, 0)
        last_heartbeat = asyncio.get_running_loop().time()
        while not await request.is_disconnected():
            events = em.db.list_events_for_run(run_id)
            while cursor < len(events):
                event = events[cursor]
                payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
                yield f"id: {cursor + 1}\ndata: {payload}\n\n"
                cursor += 1
            current = em.db.get_run(run_id)
            if current and current.status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
                yield "event: stream_complete\ndata: {}\n\n"
                return
            now = asyncio.get_running_loop().time()
            if now - last_heartbeat >= 15:
                yield ": keep-alive\n\n"
                last_heartbeat = now
            await asyncio.sleep(poll_seconds)
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.get("/events")
def list_execution_events(run_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve append-only execution events from SQLite ledger."""
    em = get_execution_manager()
    if run_id:
        events = em.db.list_events_for_run(run_id=run_id)
        if limit:
            events = events[-limit:]
        return [e.model_dump() for e in events]

    import json
    with em.db._lock:
        with em.db._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            events = []
            for row in cur.fetchall():
                try:
                    events.append({
                        "event_id": row["event_id"],
                        "run_id": row["run_id"],
                        "operation_id": row["operation_id"],
                        "attempt_id": row["attempt_id"],
                        "event_type": row["event_type"],
                        "timestamp": row["timestamp"],
                        "schema_version": row["schema_version"],
                        "data": json.loads(row["data_json"]),
                    })
                except Exception:
                    continue
            return events

@router.post("/recover")
def run_crash_recovery() -> Dict[str, Any]:
    """
    Execute crash recovery audit on uncompleted runs left in RUNNING or QUEUED states.
    Transitions interrupted states safely with reconciliation flags.
    """
    em = get_execution_manager()
    summary = em.recover_on_startup()
    return {
        "status": "completed",
        "recovered_runs": summary.get("interrupted_run_ids", []),
        "recovered_operations": summary.get("interrupted_operation_ids", []),
        "total_recovered_runs": summary.get("interrupted_runs_count", 0),
        "total_recovered_operations": summary.get("interrupted_operations_count", 0),
        "uncertain_reservations_count": summary.get("uncertain_reservations_count", 0),
    }
