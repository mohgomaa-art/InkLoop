"""Reproduce Agent's misleading empty-session state during slow hydration.

Run from the repository root with:
    python -m pytest frontend/tests/test_agent_session_hydration.py -q
"""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PROJECT_ID = "repair_session_hydration_project"
SESSION_ID = "session_repair_hydration"


def test_saved_sessions_are_not_reported_missing_while_hydrating():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    node = shutil.which("node") or shutil.which("node.exe")
    vite_entry = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite_entry.exists():
        pytest.skip("Node.js and installed frontend dependencies are required for this browser regression")

    run_id = time.strftime("%Y%m%d-%H%M%S")
    evidence_dir = ROOT / "docs" / "repair" / "evidence" / "A7" / "session-hydration" / run_id
    video_dir = evidence_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen(
        [node, str(vite_entry), "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=FRONTEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if server.poll() is not None:
                    pytest.fail("Vite exited before becoming ready")
                time.sleep(0.1)
        else:
            pytest.fail("Vite server did not become ready")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                record_video_dir=str(video_dir),
                record_video_size={"width": 1440, "height": 1000},
            )
            context.set_default_timeout(5000)
            context.add_init_script(
                """(() => {
                  const originalFetch = window.fetch.bind(window);
                  window.fetch = async (...args) => {
                    const requestUrl = typeof args[0] === 'string' ? args[0] : args[0].url;
                    const response = await originalFetch(...args);
                    if (requestUrl.includes('/api/v1/agent/sessions') && !requestUrl.includes('/session_repair_hydration')) {
                      await new Promise(resolve => window.setTimeout(resolve, 1800));
                    }
                    return response;
                  };
                })();"""
            )
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            saved_session = {
                "session_id": SESSION_ID,
                "project_id": PROJECT_ID,
                "title": "Saved story chat",
                "created_at": "2026-10-31T00:00:00+00:00",
                "updated_at": "2026-10-31T00:01:00+00:00",
                "messages": [{
                    "message_id": "message_saved_1",
                    "role": "user",
                    "text": "A saved conversation",
                    "timestamp": "2026-10-31T00:00:00+00:00",
                    "attachments": [],
                    "tool_calls": [],
                    "tool_results": [],
                }, {
                    "message_id": "message_saved_2",
                    "role": "assistant",
                    "text": "This transcript was saved.",
                    "timestamp": "2026-10-31T00:01:00+00:00",
                    "attachments": [],
                    "tool_calls": [],
                    "tool_results": [],
                }],
                "metadata": {},
            }

            def mock_api(route):
                path = route.request.url.split("/api/v1", 1)[-1].split("?", 1)[0]
                if path == "/projects":
                    return route.fulfill(json=[{
                        "project_id": PROJECT_ID,
                        "title": "Hydration Fixture",
                        "bible_version": 1,
                        "canon_hash": "",
                        "characters": [],
                        "path": "",
                    }])
                if path == f"/projects/{PROJECT_ID}/bible":
                    return route.fulfill(json={"characters": {}})
                if path == "/health":
                    return route.fulfill(json={"status": "ok", "service": "test", "version": "test", "timestamp": ""})
                if path == "/agent/status":
                    return route.fulfill(json={"mode": "offline_explicit", "runtime_ready": True})
                if path == "/agent/sessions":
                    return route.fulfill(json=[{
                        "session_id": SESSION_ID,
                        "project_id": PROJECT_ID,
                        "title": "Saved story chat",
                        "message_count": 2,
                        "updated_at": "2026-10-31T00:01:00+00:00",
                    }])
                if path == f"/agent/sessions/{SESSION_ID}":
                    return route.fulfill(json=saved_session)
                if path.startswith("/canvas/panel-layout-presets") or path.startswith("/canvas/bubble-presets"):
                    return route.fulfill(json={"presets": [], "count": 0, "total": 0})
                if path.startswith("/editor/pages/deleted") or path == f"/editor/pages?project_id={PROJECT_ID}":
                    return route.fulfill(json=[])
                if path == f"/agent/approvals":
                    return route.fulfill(json=[])
                if path.startswith(f"/projects/{PROJECT_ID}/creative/styles"):
                    return route.fulfill(json=[])
                if path == f"/creative/package/{PROJECT_ID}":
                    return route.fulfill(json={})
                if path == "/evaluation/readiness":
                    return route.fulfill(json={})
                if path == "/execution/budgets":
                    return route.fulfill(json={})
                if path == "/agent/capabilities" or path == "/assets":
                    return route.fulfill(json=[])
                return route.fulfill(json=[])

            context.route("**/api/v1/**", mock_api)
            page = context.new_page()
            page.goto(
                f"http://127.0.0.1:{port}/#/agent",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.get_by_text("Recent Sessions", exact=True).wait_for()
            page.screenshot(path=str(evidence_dir / "before.png"), full_page=True)

            # During the deliberate delay, the API has a saved nonempty session.
            # The UI must present a loading state rather than a false empty state.
            assert page.get_by_text("No saved chats yet", exact=True).count() == 0

            page.get_by_text("Saved story chat", exact=True).wait_for()
            page.get_by_text("This transcript was saved.", exact=True).wait_for()
            page.screenshot(path=str(evidence_dir / "after.png"), full_page=True)
            context.tracing.stop(path=str(evidence_dir / "trace.zip"))
            context.close()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
