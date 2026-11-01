"""Browser regression for artwork hit-testing and in-panel edit interactions.

Run from the repository root with:
    python -m pytest frontend/tests/test_editor_image_editing.py -q
"""
from __future__ import annotations

import base64
import io
import json
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
E2E_PROJECT_ID = "repair_e2e_project"


def _fixture_png(width: int, height: int) -> bytes:
    """Make a deterministic orientation/crop fixture with corner IDs and an asymmetric glyph."""
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (int(255 * x / max(1, width - 1)), int(255 * y / max(1, height - 1)), 96)

    draw = ImageDraw.Draw(image)
    marker_w = max(14, width // 10)
    marker_h = max(14, height // 10)
    markers = (
        (0, 0, (255, 0, 0), "TL"),
        (width - marker_w, 0, (0, 190, 0), "TR"),
        (0, height - marker_h, (0, 80, 255), "BL"),
        (width - marker_w, height - marker_h, (255, 220, 0), "BR"),
    )
    font = ImageFont.load_default()
    for x, y, color, label in markers:
        draw.rectangle((x, y, x + marker_w - 1, y + marker_h - 1), fill=color)
        draw.text((x + 2, y + 2), label, fill=(0, 0, 0), font=font)

    # The asymmetric L-arrow makes rotation and reflection observable.
    left, top = width // 3, height // 3
    draw.line((left, top, left, top + height // 5), fill=(0, 0, 0), width=max(2, min(width, height) // 35))
    draw.line((left, top + height // 5, left + width // 4, top + height // 5), fill=(0, 0, 0), width=max(2, min(width, height) // 35))
    draw.polygon(
        (
            (left + width // 4, top + height // 5),
            (left + width // 4 - width // 18, top + height // 5 - height // 14),
            (left + width // 4 - width // 18, top + height // 5 + height // 14),
        ),
        fill=(0, 0, 0),
    )
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _rect(x: float, y: float, width: float, height: float) -> dict:
    return {"x": x, "y": y, "width": width, "height": height}


def _page_document() -> dict:
    panels = [
        {
            "panel_id": "panel_art",
            "reading_order": 1,
            "rect": _rect(40, 40, 320, 360),
            "polygon": None,
            "is_full_bleed": False,
            "bleed_edges": [],
            "is_intentional_overlap": False,
            "intentional_overlap_with": [],
            "overlap_reason": None,
            "z_index": 0,
            "descriptor": None,
        },
        {
            "panel_id": "panel_empty",
            "reading_order": 2,
            "rect": _rect(40, 420, 320, 160),
            "polygon": None,
            "is_full_bleed": False,
            "bleed_edges": [],
            "is_intentional_overlap": False,
            "intentional_overlap_with": [],
            "overlap_reason": None,
            "z_index": 0,
            "descriptor": None,
        },
    ]
    return {
        "schema_version": "1.0.0",
        "page_id": "e2e_image_page",
        "project_id": E2E_PROJECT_ID,
        "revision": 1,
        "layout": {
            "canvas_id": "e2e_canvas",
            "canvas_spec": {"page_format": "custom", "width_px": 400, "height_px": 600, "dpi": 96},
            "page_spec": {"page_id": "e2e_image_page", "page_number": 1, "page_type": "single", "reading_direction": "ltr"},
            "template_id": "six_panel_classic",
            "template_version": "1.0.0",
            "reading_direction": "ltr",
            "panel_slots": panels,
            "trim_box": _rect(0, 0, 400, 600),
            "bleed_box": _rect(0, 0, 400, 600),
            "safe_area_box": _rect(10, 10, 380, 580),
            "usable_box": _rect(10, 10, 380, 580),
            "reading_order_panel_ids": ["panel_art", "panel_empty"],
        },
        "layers": [
            {"layer_id": "panel_layer_art", "kind": "panel", "label": "Panel 1", "visible": True, "locked": False, "z_index": 0, "panel_id": "panel_art", "fit_mode": "cover", "metadata": {}},
            {"layer_id": "panel_layer_empty", "kind": "panel", "label": "Panel 2", "visible": True, "locked": False, "z_index": 0, "panel_id": "panel_empty", "fit_mode": "cover", "metadata": {}},
            {"layer_id": "image_layer_1", "kind": "image", "label": "Artwork", "visible": True, "locked": False, "z_index": 1, "source_asset_id": "asset_image_1", "panel_id": "panel_art", "transform": {"scale_x": 1, "scale_y": 1, "translate_x": 0, "translate_y": 0, "rotation_deg": 0, "anchor_x": 0.5, "anchor_y": 0.5}, "fit_mode": "cover", "metadata": {}},
            {"layer_id": "image_layer_2", "kind": "image", "label": "Portrait Artwork", "visible": True, "locked": False, "z_index": 1, "source_asset_id": "asset_image_2", "panel_id": "panel_empty", "transform": {"scale_x": 1, "scale_y": 1, "translate_x": 0, "translate_y": 0, "rotation_deg": 0, "anchor_x": 0.5, "anchor_y": 0.5}, "fit_mode": "cover", "metadata": {}},
            {"layer_id": "bubble_layer_1", "kind": "text", "label": "Dialogue", "visible": True, "locked": False, "z_index": 2, "panel_id": "panel_art", "fit_mode": "cover", "metadata": {"x": 215, "y": 70, "width": 110, "height": 65, "font_size": 16, "text": "Hello", "bubble_shape": "oval", "tail_type": "none", "bubble_id": "bubble_1"}},
        ],
        "source_artifact_ids": ["asset_image_1", "asset_image_2"],
    }


def test_e2e_fixtures_encode_landscape_portrait_and_orientation_markers():
    landscape = Image.open(io.BytesIO(_fixture_png(300, 200))).convert("RGB")
    portrait = Image.open(io.BytesIO(_fixture_png(200, 300))).convert("RGB")
    assert landscape.size == (300, 200)
    assert portrait.size == (200, 300)
    assert landscape.getpixel((1, 1)) == (255, 0, 0)
    assert landscape.getpixel((298, 1)) == (0, 190, 0)
    assert portrait.getpixel((1, 298)) == (0, 80, 255)
    assert portrait.getpixel((198, 298)) == (255, 220, 0)


def test_editor_image_edit_hit_testing_and_saved_transform():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    node = shutil.which("node") or shutil.which("node.exe")
    vite_entry = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite_entry.exists():
        pytest.skip("Node.js and installed frontend dependencies are required for this browser regression")
    server = subprocess.Popen(
        [node, str(vite_entry), "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=FRONTEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    persisted = _page_document()
    writes: list[dict] = []
    landscape_png = _fixture_png(300, 200)
    portrait_png = _fixture_png(200, 300)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    evidence_dir = ROOT / "docs" / "repair" / "evidence" / "M0" / "ui" / run_id
    video_dir = evidence_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    try:
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if server.poll() is not None:
                    pytest.fail("Vite server exited before becoming ready")
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
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            def mock_api(route):
                nonlocal persisted
                request = route.request
                path = request.url.split("/api/v1", 1)[-1].split("?", 1)[0]
                method = request.method
                if path == "/editor/pages/e2e_image_page" and method == "GET":
                    return route.fulfill(json=persisted)
                if path == "/editor/pages/e2e_image_page" and method == "PUT":
                    body = request.post_data_json
                    persisted = body["document"]
                    persisted["revision"] = int(body["expected_revision"]) + 1
                    writes.append(persisted)
                    return route.fulfill(json=persisted)
                if path == "/editor/pages/e2e_image_page/revisions":
                    return route.fulfill(json=[])
                if path.endswith("/assets/asset_image_1/file"):
                    return route.fulfill(status=200, content_type="image/png", body=landscape_png)
                if path.endswith("/assets/asset_image_2/file"):
                    return route.fulfill(status=200, content_type="image/png", body=portrait_png)
                if path.endswith("/preview"):
                    return route.fulfill(status=200, content_type="image/png", body=landscape_png)
                if path == "/projects":
                    return route.fulfill(json=[{"project_id": E2E_PROJECT_ID, "title": "Repair E2E Fixture", "bible_version": 1, "canon_hash": "", "characters": [], "path": ""}])
                if path == f"/projects/{E2E_PROJECT_ID}/bible":
                    return route.fulfill(json={"characters": {}})
                if path.startswith(f"/projects/{E2E_PROJECT_ID}/creative/styles"):
                    return route.fulfill(json=[])
                if path.startswith("/canvas/panel-layout-presets") or path.startswith("/canvas/bubble-presets"):
                    return route.fulfill(json={"presets": [], "count": 0, "total": 0})
                if path.startswith("/editor/pages/deleted") or path == f"/editor/pages?project_id={E2E_PROJECT_ID}":
                    return route.fulfill(json=[])
                if path == "/assets":
                    return route.fulfill(json=[])
                if path == "/editor/pages/validate":
                    return route.fulfill(json={"valid": True, "diagnostics": []})
                if path == "/health":
                    return route.fulfill(json={"status": "ok", "service": "test", "version": "test", "timestamp": ""})
                if path == "/agent/status":
                    return route.fulfill(json={"mode": "offline"})
                return route.fulfill(json=[])

            context.route("**/api/v1/**", mock_api)
            page = context.new_page()
            page.goto(
                f"http://127.0.0.1:{port}/#/editor?page=e2e_image_page",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.get_by_test_id("panel-artwork-panel_art").wait_for()
            page.screenshot(path=str(evidence_dir / "before.png"), full_page=True)

            root = page.get_by_test_id("manual-editor")
            artwork = page.get_by_test_id("panel-artwork-panel_art")
            bubble = page.get_by_test_id("editor-layer-bubble_layer_1")
            panel_outline = page.get_by_test_id("panel-outline-panel_art")
            visible_panel = panel_outline.bounding_box()
            assert visible_panel is not None
            second_panel = page.get_by_test_id("panel-outline-panel_empty").bounding_box()
            assert second_panel is not None
            art_click_x = visible_panel["x"] + visible_panel["width"] / 2
            art_click_y = visible_panel["y"] + visible_panel["height"] / 2
            first_panel_bottom = visible_panel["y"] + visible_panel["height"]
            panel_gutter = second_panel["y"] - first_panel_bottom
            assert panel_gutter > 0
            clear_point = (art_click_x, first_panel_bottom + panel_gutter / 2)

            # Lettering remains above the artwork and independently selectable.
            bubble.click(position={"x": 55, "y": 30})
            assert root.get_attribute("data-selected-layer") == "bubble_layer_1"
            bubble_layer = page.locator('[data-testid="editor-layer-bubble_layer_1"]')
            bubble_filter = bubble_layer.evaluate("el => getComputedStyle(el).filter")
            assert "drop-shadow" in bubble_filter and "37, 99, 235" in bubble_filter
            page.get_by_text("Properties", exact=True).click()
            assert root.get_attribute("data-selected-layer") == "bubble_layer_1"
            page.get_by_title("Wheel to zoom • Click to reset to 100%").click()
            assert root.get_attribute("data-selected-layer") == "bubble_layer_1"
            page.mouse.click(*clear_point)
            assert root.get_attribute("data-selected-layer") == ""
            bubble.click(position={"x": 55, "y": 30})
            assert root.get_attribute("data-selected-layer") == "bubble_layer_1"

            # Image hit-testing works despite the panel frame being painted above it.
            assert artwork.evaluate("el => getComputedStyle(el).cursor") == "pointer"
            page.mouse.click(art_click_x, art_click_y)
            artwork_highlight = page.get_by_test_id("editor-selection-highlight-panel_art")
            assert artwork_highlight.get_attribute("data-selection-kind") == "image"
            assert artwork.get_attribute("data-image-edit-mode") == "disabled"
            assert page.get_by_title("Scale Up (+10%)").is_disabled()
            page.mouse.dblclick(art_click_x, art_click_y)
            assert artwork.get_attribute("data-image-edit-mode") == "enabled"
            page.wait_for_function("document.querySelector('[data-testid=panel-artwork-panel_art]')?.getAttribute('data-image-bounds-ready') === 'true'")
            assert artwork.get_attribute("data-image-source-width") == "300"
            assert artwork.get_attribute("data-image-source-height") == "200"
            assert page.get_by_test_id("image-overscan-ghost-panel_art").count() == 1
            assert artwork.evaluate("el => getComputedStyle(el).cursor") == "move"
            assert root.get_attribute("data-selected-layer") == "image_layer_1"
            gizmo_body = page.get_by_test_id("transform-gizmo-body")
            assert float(gizmo_body.get_attribute("x")) < 40
            assert float(gizmo_body.get_attribute("width")) > 320
            source_image = page.get_by_test_id("panel-artwork-mask-panel_art").locator("image").first
            source_bounds = source_image.evaluate("el => [Number(el.getAttribute('width')), Number(el.getAttribute('height'))]")
            assert abs(source_bounds[0] / source_bounds[1] - 1.5) < 0.01

            portrait_artwork = page.get_by_test_id("panel-artwork-panel_empty")
            page.wait_for_function("document.querySelector('[data-testid=panel-artwork-panel_empty]')?.getAttribute('data-image-bounds-ready') === 'true'")
            assert portrait_artwork.get_attribute("data-image-source-width") == "200"
            assert portrait_artwork.get_attribute("data-image-source-height") == "300"
            portrait_art_image = page.get_by_test_id("panel-artwork-mask-panel_empty").locator("image").first
            portrait_bounds = portrait_art_image.evaluate("el => [Number(el.getAttribute('width')), Number(el.getAttribute('height'))]")
            assert abs(portrait_bounds[0] / portrait_bounds[1] - (2 / 3)) < 0.01

            page.mouse.click(*clear_point)
            assert root.get_attribute("data-selected-layer") == ""
            assert artwork.get_attribute("data-image-edit-mode") == "disabled"
            page.mouse.dblclick(art_click_x, art_click_y)
            assert artwork.get_attribute("data-image-edit-mode") == "enabled"
            gizmo_body = page.get_by_test_id("transform-gizmo-body")

            page.keyboard.press("Escape")
            assert root.get_attribute("data-selected-layer") == ""
            assert artwork.get_attribute("data-image-edit-mode") == "disabled"
            page.mouse.dblclick(art_click_x, art_click_y)
            assert artwork.get_attribute("data-image-edit-mode") == "enabled"
            gizmo_body = page.get_by_test_id("transform-gizmo-body")

            original_rect = panel_outline.evaluate("el => [el.getAttribute('x'), el.getAttribute('y'), el.getAttribute('width'), el.getAttribute('height')]")
            page.get_by_title("Scale Up (+10%)").click()
            assert artwork.get_attribute("data-image-scale") == "1.1"
            page.get_by_title("Scale Down (-10%)").click()
            assert artwork.get_attribute("data-image-scale") == "1"
            page.get_by_title("Scale Up (+10%)").click()
            assert artwork.get_attribute("data-image-scale") == "1.1"
            page.get_by_title("Rotate +15°").click()
            assert artwork.get_attribute("data-image-rotation") == "15"

            # Dragging the artwork changes image placement, not panel bounds.
            start_x = art_click_x
            start_y = art_click_y
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(start_x + 20, start_y + 20, steps=5)
            page.mouse.up()
            assert artwork.get_attribute("data-image-translate-x") != "0"
            assert panel_outline.evaluate("el => [el.getAttribute('x'), el.getAttribute('y'), el.getAttribute('width'), el.getAttribute('height')]") == original_rect

            page.get_by_title("Finish image editing").click()
            assert artwork.get_attribute("data-image-edit-mode") == "disabled"
            assert page.get_by_test_id("image-overscan-ghost-panel_art").count() == 0

            # Frame selection still works on the panel border; empty panel interior remains selectable.
            page.get_by_test_id("panel-outline-panel_art").click(position={"x": 160, "y": 1})
            assert root.get_attribute("data-selected-layer") == "panel_layer_art"
            panel_highlight = page.get_by_test_id("editor-selection-highlight-panel_art")
            assert panel_highlight.get_attribute("data-selection-kind") == "panel"
            empty_outline = page.get_by_test_id("panel-outline-panel_empty")
            empty_outline.hover(position={"x": 160, "y": 1})
            assert empty_outline.evaluate("el => getComputedStyle(el).stroke") == "rgb(245, 158, 11)"
            empty_outline.click(position={"x": 160, "y": 1})
            assert root.get_attribute("data-selected-layer") == "panel_layer_empty"
            assert page.get_by_test_id("editor-selection-highlight-panel_empty").get_attribute("data-selection-kind") == "panel"

            # Persist and reopen to prove transforms survive the editor document path.
            page.wait_for_function("() => /Saved \\(rev (?:[2-9]|[1-9]\\d+)\\)/.test(document.body.innerText)")
            saved_image = next(layer for layer in writes[-1]["layers"] if layer["layer_id"] == "image_layer_1")
            assert saved_image["transform"]["scale_x"] == 1.1
            assert saved_image["transform"]["scale_y"] == 1.1
            assert saved_image["transform"]["rotation_deg"] == 15
            page.reload()
            page.get_by_test_id("panel-artwork-panel_art").wait_for()
            assert page.get_by_test_id("panel-artwork-panel_art").get_attribute("data-image-scale") == "1.1"
            assert page.get_by_test_id("panel-artwork-panel_art").get_attribute("data-image-rotation") == "15"
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
