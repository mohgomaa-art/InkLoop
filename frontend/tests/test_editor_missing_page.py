"""Exercise the editor's 404/deep-link path without touching page storage."""
from __future__ import annotations

import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PROJECT_ID = "repair_missing_page_project"
PAGE_ID = "repair_missing_page"


def test_missing_editor_deep_link_surfaces_404_without_null_before_error():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    node = shutil.which("node") or shutil.which("node.exe")
    vite_entry = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite_entry.exists():
        pytest.skip("Node.js and installed frontend dependencies are required for this browser regression")

    run_id = time.strftime("%Y%m%d-%H%M%S")
    evidence_dir = ROOT / "docs" / "repair" / "evidence" / "P3" / run_id
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
                f"localStorage.setItem('inkloop_current_project', '{PROJECT_ID}');"
                f"localStorage.removeItem('inkloop_active_page_{PROJECT_ID}');"
            )
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            missing_page_responses: list[int] = []
            page_errors: list[str] = []

            def mock_api(route):
                request = route.request
                path = request.url.split("/api/v1", 1)[-1].split("?", 1)[0]
                if path == "/projects":
                    return route.fulfill(json=[{
                        "project_id": PROJECT_ID, "title": "Missing Page Fixture",
                        "bible_version": 1, "canon_hash": "", "characters": [], "path": "",
                    }])
                if path == f"/projects/{PROJECT_ID}/bible":
                    return route.fulfill(json={"characters": {}})
                if path == "/health":
                    return route.fulfill(json={"status": "ok", "service": "test", "version": "test", "timestamp": ""})
                if path == "/agent/status":
                    return route.fulfill(json={"mode": "offline_explicit", "runtime_ready": True})
                if path == f"/editor/pages/{PAGE_ID}" and request.method == "GET":
                    missing_page_responses.append(404)
                    return route.fulfill(status=404, json={"detail": {"error_code": "ERR_PAGE_NOT_FOUND", "message": f"Page {PAGE_ID} not found"}})
                if path.startswith("/canvas/panel-layout-presets") or path.startswith("/canvas/bubble-presets"):
                    return route.fulfill(json={"presets": [], "count": 0, "total": 0})
                if path.startswith("/editor/pages/deleted") or path == f"/editor/pages?project_id={PROJECT_ID}":
                    return route.fulfill(json=[])
                if path == "/assets" or path.startswith("/assets?"):
                    return route.fulfill(json=[])
                if path.startswith(f"/projects/{PROJECT_ID}/creative/styles"):
                    return route.fulfill(json=[])
                return route.fulfill(json=[])

            context.route("**/api/v1/**", mock_api)
            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(
                f"http://127.0.0.1:{port}/#/editor?page={PAGE_ID}",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.locator(".editor-error").filter(has_text=f"Page {PAGE_ID} not found").wait_for()
            page.screenshot(path=str(evidence_dir / "missing-page-error.png"), full_page=True)
            # React.StrictMode can intentionally issue the page-load effect twice
            # in development. Every request must still receive the same truthful
            # not-found response; request count is not part of the product contract.
            assert missing_page_responses
            assert set(missing_page_responses) == {404}
            assert not any("before" in message.lower() for message in page_errors)
            context.tracing.stop(path=str(evidence_dir / "trace.zip"))
            context.close()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
