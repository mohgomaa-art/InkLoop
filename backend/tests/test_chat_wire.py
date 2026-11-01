"""
Acceptance Test Suite for S9 Agent Studio Live Chat Wire (Option A).
Verifies:
- Scenario 1: 'hi' returns conversational greeting with 0 tool calls.
- Scenario 2: Arabic greetings ('اه', 'مرحبا') return conversational greeting with 0 tool calls.
- Scenario 3: Real Canon inspection returns real tool call and Story Bible output.
- Scenario 4: Plan draft creates DAG in DRAFT/PLANNED state without premature execution or fake approvals.
- Scenario 5: Backend validation errors return clean structured HTTP error responses.
- Scenario 6: Attachment upload rejects files > 15MB with HTTP 422 ERR_ATTACHMENT_TOO_LARGE.
- Scenario 7: Valid image upload returns server-issued reference with SHA-256 and dimensions, usable in chat.
"""
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.api.server import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _make_test_image_bytes(width: int = 200, height: int = 200, fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# =============================================================================
# Scenario 1: 'hi' produces conversational response with ZERO tool calls
# =============================================================================
def test_scenario_1_greeting_hi_zero_tool_calls(client):
    """Greeting 'hi' produces conversational response with ZERO tool calls."""
    resp = client.post("/api/v1/agent/chat", json={"project_id": "inkloop", "message": "hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert "hello" in data["text"].lower() or "studio" in data["text"].lower() or "inkloop" in data["text"].lower()
    assert len(data.get("tool_calls", [])) == 0
    assert len(data.get("tool_results", [])) == 0


# =============================================================================
# Scenario 2: Arabic greetings produce conversational response with ZERO tool calls
# =============================================================================
def test_scenario_2_arabic_greeting_ah_zero_tool_calls(client):
    """Arabic greeting 'اه' or 'مرحبا' produces conversational response with ZERO tool calls."""
    resp = client.post("/api/v1/agent/chat", json={"project_id": "inkloop", "message": "اه"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert len(data.get("tool_calls", [])) == 0
    assert len(data.get("tool_results", [])) == 0

    resp_marhaba = client.post("/api/v1/agent/chat", json={"project_id": "inkloop", "message": "مرحبا"})
    assert resp_marhaba.status_code == 200
    data_marhaba = resp_marhaba.json()
    assert len(data_marhaba.get("tool_calls", [])) == 0


# =============================================================================
# Scenario 3: Real Canon inspection returns real tool call and Story Bible output
# =============================================================================
def test_scenario_3_canon_inspection_request_returns_real_tool_call(client):
    """Canon inspection query returns real tool call and Story Bible output."""
    resp = client.post(
        "/api/v1/agent/chat",
        json={"project_id": "inkloop", "message": "Inspect Nour's canonical invariants"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tool_calls"]) >= 1
    tool_ids = [tc["tool_id"] for tc in data["tool_calls"]]
    assert "canon.inspect_characters" in tool_ids or "canon.inspect_reference_anchor" in tool_ids
    assert len(data["tool_results"]) >= 1
    res = next(r for r in data["tool_results"] if r["tool_id"] in tool_ids)
    assert res["status"] == "success"
    assert "output" in res and res["output"] is not None


# =============================================================================
# Scenario 4: Plan request creates draft DAG without premature approval or execution
# =============================================================================
def test_scenario_4_plan_request_no_premature_approval_or_execution(client):
    """Plan draft request creates a draft plan DAG without false claim of execution or approval."""
    resp = client.post(
        "/api/v1/agent/chat",
        json={"project_id": "inkloop", "message": "Draft a 6-panel plan for Scene 1"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tool_calls"]) >= 1
    tool_ids = [tc["tool_id"] for tc in data["tool_calls"]]
    assert "plan.draft_plan" in tool_ids
    # Plan is in DRAFT/PLANNED status, NOT executed
    if data.get("plan"):
        assert data["plan"]["status"] in ("DRAFT", "PLANNED")
        assert data["plan"]["dispatched"] is False


# =============================================================================
# Scenario 5: Backend validation errors fail cleanly with structured HTTP status
# =============================================================================
def test_scenario_5_backend_validation_error_fails_cleanly(client):
    """Invalid requests fail with clear HTTP status rather than fake success answers."""
    # Invalid session endpoint query
    resp = client.get("/api/v1/agent/sessions/non_existent_session_999999")
    assert resp.status_code == 404
    data = resp.json()
    assert "error_code" in data.get("detail", {}) or "message" in data.get("detail", {})


# =============================================================================
# Scenario 6: Attachment upload size limit rejection (> 15MB)
# =============================================================================
def test_scenario_6_attachment_upload_size_limit_rejection(client):
    """Files exceeding 15MB are rejected with HTTP 422."""
    huge_data = b"0" * (16 * 1024 * 1024)  # 16 MB
    resp = client.post(
        "/api/v1/agent/attachments/upload",
        files={"file": ("huge.png", io.BytesIO(huge_data), "image/png")},
        data={"project_id": "inkloop"},
    )
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"]["error_code"] == "ERR_ATTACHMENT_TOO_LARGE"


# =============================================================================
# Scenario 7: Valid image upload passes reference with SHA-256 and dimensions
# =============================================================================
def test_scenario_7_attachment_upload_valid_passes_reference(client):
    """Valid image upload returns server-issued reference with SHA-256 and dimensions."""
    img_bytes = _make_test_image_bytes(250, 180, "PNG")
    resp = client.post(
        "/api/v1/agent/attachments/upload",
        files={"file": ("valid_panel.png", io.BytesIO(img_bytes), "image/png")},
        data={"project_id": "inkloop"},
    )
    assert resp.status_code == 200
    att = resp.json()
    assert "attachment_id" in att
    assert "storage_path" not in att
    assert att["width"] == 250
    assert att["height"] == 180
    assert len(att["content_sha256"]) == 64

    # Now pass server-issued attachment into chat request
    chat_resp = client.post(
        "/api/v1/agent/chat",
        json={
            "project_id": "inkloop",
            "message": "Inspect this image attachment metadata",
            "attachments": [att]
        }
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert len(chat_data["tool_calls"]) >= 1
    assert "image.inspect_file_metadata" in [tc["tool_id"] for tc in chat_data["tool_calls"]]
