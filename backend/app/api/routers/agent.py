"""
InkLoop Agent Coordinator (S9) REST API Router.
Exposes endpoints for multimodal chat turns, tool capabilities, plan generation,
approvals, durable sessions, and image attachment inspection.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse

from app.config import PROJECT_ROOT
from app.agent.schemas import (
    ToolDefinition,
    AgentMessage,
    AgentSession,
    AgentAttachment,
    AgentPlan,
    ApprovalRequest,
)
from app.agent.registry import CapabilityRegistry
from app.agent.coordinator import AgentCoordinator
from app.agent.live_activity import begin_activity, finish_activity, get_activity, record_tool_activity
from app.agent.session_store import SessionStore
from app.agent.approvals import ApprovalManager
from app.agent.image_inspector import inspect_image_bytes, resolve_attachment_path, ImageInspectionError, MAX_FILE_BYTES
from app.agent.file_inspector import inspect_document_bytes, resolve_document_path

router = APIRouter(prefix="/agent", tags=["Agent Coordinator (S9)"])

# Singletons
_coordinator_instance: Optional[AgentCoordinator] = None

def get_coordinator() -> AgentCoordinator:
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = AgentCoordinator()
    return _coordinator_instance

# Request Payloads
class ChatRequest(BaseModel):
    project_id: str = "default_project"
    message: str = ""
    attachments: List[AgentAttachment] = Field(default_factory=list)
    session_id: Optional[str] = None
    approval_id: Optional[str] = None
    spend_limit_usd: Optional[float] = None
    selected_character_ids: List[str] = Field(default_factory=list)
    selected_style_profile_id: Optional[str] = None
    selected_style_version: Optional[int] = None
    selected_location_id: Optional[str] = None
    selected_location_version: Optional[int] = None
    activity_id: Optional[str] = None
    canvas_page_id: Optional[str] = None
    canvas_panel_id: Optional[str] = None
    canvas_expected_revision: Optional[int] = None
    model: Optional[str] = None

class PlanRequest(BaseModel):
    project_id: str = "default_project"
    goal: str
    spend_limit_usd: Optional[float] = None

class ApprovalDecisionRequest(BaseModel):
    decision: str  # "APPROVE" | "REJECT"
    rationale: Optional[str] = None

class CreateSessionRequest(BaseModel):
    project_id: str = "default_project"
    title: str = "New Conversation"

class RetryLastTurnRequest(BaseModel):
    project_id: str = "default_project"
    activity_id: Optional[str] = None

@router.get("/status")
def get_agent_status() -> Dict[str, Any]:
    """Retrieve Agent Coordinator runtime readiness and operational status."""
    import os
    from app.config import InkLoopConfig
    offline_mode = os.getenv("INKLOOP_OFFLINE_MODE", "0").lower() in ("1", "true")
    cfg = InkLoopConfig.load()
    credentials_configured = cfg.has_credentials
    mode = "offline_explicit" if offline_mode else ("live_configured" if credentials_configured else "provider_unavailable")
    return {
        "status": "operational" if offline_mode or credentials_configured else "provider_unavailable",
        "phase": "S9_v1",
        "spec": "INKLOOP_AGENT_DESIGN_V1.md",
        "runtime_ready": offline_mode or credentials_configured,
        "mode": mode,
        "model_name": cfg.muse_spark_model,
        "image_model": cfg.muse_image_model,
        "sam_model": cfg.sam_model,
        "provider": "Meta AI",
        "model_credentials_configured": credentials_configured,
        "tools_registered": len(CapabilityRegistry.get_instance().list_tools()),
    }

@router.get("/capabilities")
def list_capabilities(
    domain: Optional[str] = None,
    chat_only: bool = False,
) -> List[Dict[str, Any]]:
    """List registered tools, optionally limited to callable image-chat tools."""
    reg = CapabilityRegistry.get_instance()
    tools = (
        reg.list_image_chat_tools()
        if chat_only
        else reg.list_tools(domain=domain)
    )
    if chat_only and domain:
        tools = [tool for tool in tools if tool.domain == domain]
    return [t.model_dump() for t in tools]

@router.post("/chat")
def send_chat_message(payload: ChatRequest) -> Dict[str, Any]:
    """
    Executes a model-driven multimodal chat turn:
    Invokes registered specialist tools dynamically, grounds response in real evidence,
    and records durable turn trace.
    """
    coord = get_coordinator()
    if payload.activity_id:
        begin_activity(payload.activity_id)
    try:
        assistant_msg = coord.process_chat_turn(
            project_id=payload.project_id,
            user_text=payload.message,
            attachments=payload.attachments,
            session_id=payload.session_id,
            approval_id=payload.approval_id,
            spend_limit_usd=payload.spend_limit_usd,
            selected_character_ids=payload.selected_character_ids,
            selected_style_profile_id=payload.selected_style_profile_id,
            selected_style_version=payload.selected_style_version,
            selected_location_id=payload.selected_location_id,
            selected_location_version=payload.selected_location_version,
            activity_callback=(
                (lambda event: record_tool_activity(payload.activity_id, event))
                if payload.activity_id else None
            ),
            canvas_page_id=payload.canvas_page_id,
            canvas_panel_id=payload.canvas_panel_id,
            canvas_expected_revision=payload.canvas_expected_revision,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)})
    finally:
        if payload.activity_id:
            finish_activity(payload.activity_id)
    return assistant_msg.model_dump()


@router.get("/activity/{activity_id}")
def get_chat_activity(activity_id: str) -> Dict[str, Any]:
    """Return real tool dispatches observed during an active chat turn."""
    if len(activity_id) > 100:
        raise HTTPException(status_code=422, detail="Invalid activity ID")
    return get_activity(activity_id)

@router.post("/plans")
def create_plan(payload: PlanRequest) -> Dict[str, Any]:
    """
    Synthesizes and validates a typed execution plan DAG for a user goal.
    Directly compatible with frontend apiClient.createAgentPlan.
    """
    coord = get_coordinator()
    plan = coord.create_plan(
        project_id=payload.project_id,
        goal=payload.goal,
        spend_limit_usd=payload.spend_limit_usd,
    )
    return plan.model_dump()

@router.get("/plans/{plan_id}")
def get_plan(plan_id: str) -> Dict[str, Any]:
    """Retrieve an existing plan DAG by ID."""
    plans_dir = PROJECT_ROOT / "runs" / "plans"
    plan_file = plans_dir / f"{plan_id}.json"
    if not plan_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_PLAN_NOT_FOUND", "message": f"Plan {plan_id} not found."}
        )
    import json
    data = json.loads(plan_file.read_text(encoding="utf-8"))
    return data

@router.post("/approvals/{approval_id}")
def submit_approval(approval_id: str, payload: ApprovalDecisionRequest) -> Dict[str, Any]:
    """Record an operator approval or rejection decision for a gated action."""
    mgr = ApprovalManager.get_instance()
    try:
        req = mgr.submit_decision(
            approval_id=approval_id,
            decision=payload.decision,
            rationale=payload.rationale,
        )
        return req.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_APPROVAL_ERROR", "message": str(e)}
        )

@router.get("/approvals/{approval_id}")
def get_approval(approval_id: str) -> Dict[str, Any]:
    """Retrieve approval request details."""
    mgr = ApprovalManager.get_instance()
    req = mgr.get_request(approval_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_APPROVAL_NOT_FOUND", "message": f"Approval {approval_id} not found."}
        )
    return req.model_dump()

@router.get("/approvals")
def list_approvals(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List pending and decided approvals."""
    mgr = ApprovalManager.get_instance()
    return [r.model_dump() for r in mgr.list_requests(project_id=project_id)]

@router.get("/traces/{run_id}")
def get_run_trace(run_id: str) -> Dict[str, Any]:
    """Retrieve append-only execution events and diagnostics for a run or session."""
    from app.api.routers.execution import get_execution_manager
    em = get_execution_manager()
    events = em.db.list_events_for_run(run_id=run_id)
    return {
        "run_id": run_id,
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }

@router.get("/sessions")
def list_sessions(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List durable Agent sessions, across projects when no project is supplied."""
    store = SessionStore.get_instance()
    sessions = store.list_sessions(project_id=project_id)
    return [
        {
            "session_id": s.session_id,
            "project_id": s.project_id,
            "title": _session_display_title(s),
            "message_count": len(s.messages),
            "updated_at": s.updated_at,
        }
        for s in sessions
    ]


def _session_display_title(session) -> str:
    """Use the first user prompt as a readable title for legacy untitled chats."""
    title = (session.title or "").strip()
    if title.casefold() not in {"", "new session", "new conversation"}:
        return title
    first_user_message = next((message.text for message in session.messages if message.role == "user" and message.text.strip()), "")
    if not first_user_message:
        return "New conversation"
    first_line = " ".join(first_user_message.strip().splitlines()).strip()
    return first_line[:64] + ("…" if len(first_line) > 64 else "")

@router.post("/sessions")
def create_session(payload: CreateSessionRequest) -> Dict[str, Any]:
    """Create a new conversational session."""
    store = SessionStore.get_instance()
    sess = store.create_session(project_id=payload.project_id, title=payload.title)
    return sess.model_dump()

@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    """Retrieve full conversation transcript and tool events for a session."""
    store = SessionStore.get_instance()
    sess = store.get_session(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_SESSION_NOT_FOUND", "message": f"Session {session_id} not found."}
        )
    return sess.model_dump()


def _turn_has_pending_approval(messages) -> bool:
    return any(
        message.pending_approval is not None
        or any(result.status == "gated" for result in message.tool_results)
        for message in messages
    )


@router.delete("/sessions/{session_id}/last-turn")
def delete_last_turn(session_id: str, project_id: str = Query(...)) -> Dict[str, Any]:
    """Delete the newest prompt and its reply from this project's transcript."""
    store = SessionStore.get_instance()
    try:
        session, removed = store.remove_last_turn(session_id, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error_code": "ERR_SESSION_NOT_FOUND", "message": str(exc)})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"error_code": "ERR_SESSION_PROJECT_MISMATCH", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error_code": "ERR_NO_LAST_TURN", "message": str(exc)})
    if _turn_has_pending_approval(removed):
        store.restore_turn(session_id, project_id, len(session.messages), removed)
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ERR_TURN_HAS_PENDING_APPROVAL", "message": "Resolve the pending approval before deleting this turn."},
        )
    return {
        "session_id": session_id,
        "removed_message_ids": [message.message_id for message in removed],
        "message_count": len(session.messages),
    }


@router.post("/sessions/{session_id}/retry-last")
def retry_last_turn(session_id: str, payload: RetryLastTurnRequest) -> Dict[str, Any]:
    """Replace the newest attempt by rerunning its exact saved prompt and context."""
    store = SessionStore.get_instance()
    try:
        session, removed = store.remove_last_turn(session_id, payload.project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error_code": "ERR_SESSION_NOT_FOUND", "message": str(exc)})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"error_code": "ERR_SESSION_PROJECT_MISMATCH", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error_code": "ERR_NO_LAST_TURN", "message": str(exc)})

    keep_count = len(session.messages)
    if _turn_has_pending_approval(removed):
        store.restore_turn(session_id, payload.project_id, keep_count, removed)
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ERR_TURN_HAS_PENDING_APPROVAL", "message": "Resolve the pending approval before retrying this turn."},
        )

    prompt = removed[0]
    context = prompt.request_context or {}
    if payload.activity_id:
        begin_activity(payload.activity_id)
    try:
        assistant_msg = get_coordinator().process_chat_turn(
            project_id=payload.project_id,
            user_text=prompt.text,
            attachments=prompt.attachments,
            session_id=session_id,
            spend_limit_usd=context.get("spend_limit_usd"),
            selected_character_ids=context.get("selected_character_ids") or [],
            selected_style_profile_id=context.get("selected_style_profile_id"),
            selected_style_version=context.get("selected_style_version"),
            selected_location_id=context.get("selected_location_id"),
            selected_location_version=context.get("selected_location_version"),
            activity_callback=(
                (lambda event: record_tool_activity(payload.activity_id, event))
                if payload.activity_id else None
            ),
            canvas_page_id=context.get("canvas_page_id"),
            canvas_panel_id=context.get("canvas_panel_id"),
            canvas_expected_revision=context.get("canvas_expected_revision"),
        )
    except ValueError as exc:
        store.restore_turn(session_id, payload.project_id, keep_count, removed)
        raise HTTPException(status_code=422, detail={"message": str(exc)})
    except Exception:
        store.restore_turn(session_id, payload.project_id, keep_count, removed)
        raise HTTPException(status_code=500, detail={"error_code": "ERR_AGENT_RETRY_FAILED", "message": "The retry could not be completed; the previous attempt was restored."})
    finally:
        if payload.activity_id:
            finish_activity(payload.activity_id)
    return assistant_msg.model_dump()

@router.post("/attachments/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    project_id: str = Form("default_project"),
) -> Dict[str, Any]:
    """
    Safely inspects and stores an uploaded image or text document attachment.
    Enforces bounded reads, content validation, project isolation, and SHA-256 integrity.
    """
    try:
        content = await file.read(MAX_FILE_BYTES + 1)
        filename = file.filename or "attachment"
        if content.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")) or (content.startswith(b"RIFF") and content[8:12] == b"WEBP"):
            att = inspect_image_bytes(data=content, filename=filename, project_id=project_id)
        else:
            att = inspect_document_bytes(data=content, filename=filename, project_id=project_id)
        return att.model_dump()
    except ImageInspectionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": e.code, "message": e.message}
        )
    except Exception:
        raise HTTPException(status_code=500, detail={"error_code": "ERR_ATTACHMENT_UPLOAD_FAILED", "message": "Attachment upload could not be completed."})

@router.get("/attachments/{attachment_id}/file")
def get_attachment_file(attachment_id: str, project_id: str = Query(...)) -> FileResponse:
    """Serve a previously validated attachment from its owning project."""
    try:
        try:
            path = resolve_document_path(attachment_id, project_id)
        except ImageInspectionError:
            path = resolve_attachment_path(attachment_id, project_id)
        from mimetypes import guess_type
        return FileResponse(path, media_type=guess_type(path.name)[0] or "application/octet-stream", filename=path.name)
    except ImageInspectionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": exc.code, "message": exc.message})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "ERR_ATTACHMENT_READ_FAILED", "message": "Attachment could not be served."}
        )
