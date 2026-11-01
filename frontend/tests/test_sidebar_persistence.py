"""Reproduce sidebar state being reset when the app reloads.

Run from the repository root with:
    python -m pytest frontend/tests/test_sidebar_persistence.py -q
"""
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
PROJECT_ID = "repair_sidebar_project"


def test_sidebar_mouse_and_keyboard_state_survives_reload():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    node = shutil.which("node") or shutil.which("node.exe")
    vite_entry = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite_entry.exists():
        pytest.skip("Node.js and installed frontend dependencies are required for this browser regression")

    run_id = time.strftime("%Y%m%d-%H%M%S")
    evidence_dir = ROOT / "docs" / "repair" / "evidence" / "P8" / run_id
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
                f"localStorage.setItem('inkloop_current_project', '{PROJECT_ID}')"
            )
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            def mock_api(route):
                path = route.request.url.split("/api/v1", 1)[-1].split("?", 1)[0]
                if path == "/projects":
                    return route.fulfill(json=[{
                        "project_id": PROJECT_ID,
                        "title": "Sidebar Fixture",
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
                if path.startswith("/canvas/panel-layout-presets") or path.startswith("/canvas/bubble-presets"):
                    return route.fulfill(json={"presets": [], "count": 0, "total": 0})
                return route.fulfill(json=[])

            context.route("**/api/v1/**", mock_api)
            page = context.new_page()
            try:
                page.goto(
                    f"http://127.0.0.1:{port}/#/agent",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                page.locator(".app-sidebar").wait_for(state="visible")
                page.locator(".sidebar-close").click()
                assert page.locator(".app-sidebar").count() == 0

                open_button = page.get_by_role("button", name="Open sidebar")
                open_button.focus()
                page.keyboard.press("Enter")
                page.locator(".app-sidebar").wait_for(state="visible")

                close_button = page.get_by_role("button", name="Close sidebar").first
                close_button.focus()
                page.keyboard.press("Enter")
                assert page.locator(".app-sidebar").count() == 0
                page.screenshot(path=str(evidence_dir / "closed-before-reload.png"), full_page=True)

                page.reload(wait_until="domcontentloaded")
                page.get_by_role("button", name="Close sidebar").first.wait_for()
                page.screenshot(path=str(evidence_dir / "after-reload.png"), full_page=True)
                assert page.locator(".app-sidebar").count() == 0
            finally:
                context.tracing.stop(path=str(evidence_dir / "trace.zip"))
                context.close()
                browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
