#!/usr/bin/env python3
"""Read-only InkLoop visual-asset forensic inventory and inspection ledger.

The only writes are new audit outputs under docs/visual_forensics. Source assets,
databases, application code, and generation history are opened read-only.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import mimetypes
import os
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import fitz
import numpy as np
from PIL import Image, ImageFile, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "visual_forensics"
SCHEMA = "1.0.0"
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff",
    ".avif", ".heic", ".heif", ".svg", ".ico", ".icns", ".apng", ".jp2",
    ".j2k", ".jpf", ".jpx", ".jpm", ".mj2", ".jxl", ".psd", ".eps",
}
VISUAL_DOC_EXTS = {".pdf"}
EXCLUDED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache"}
ASSET_DB = ROOT / "runs" / "artifact_store" / "registry.db"
DB_CANDIDATES = [
    ASSET_DB,
    ROOT / "runs" / "creative_profiles.db",
    ROOT / "runs" / "page_documents.db",
    ROOT / "runs" / "execution.db",
    ROOT / "backend" / "runs" / "execution.db",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception as exc:
                    raise ValueError(f"Invalid JSONL at {path}:{n}: {exc}") from exc
    return out


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def phash(data: bytes) -> str:
    """64-bit DCT perceptual hash; candidate grouping only, never lineage proof."""
    with Image.open(io.BytesIO(data)) as source:
        img = source.convert("RGB")
        img.thumbnail((4096, 4096))
        gray = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2GRAY)
    small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(small)[:8, :8]
    ac = dct.flatten()[1:]
    median = float(np.median(ac))
    bits = (dct.flatten() > median).astype(np.uint8)
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def phash_rgb(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return phash(buf.getvalue())


def mime_for(path: Path, detected: str | None = None) -> str | None:
    if detected == "SVG":
        return "image/svg+xml"
    if detected == "PDF":
        return "application/pdf"
    return mimetypes.guess_type(path.name)[0]


def safe_walk() -> list[Path]:
    files: list[Path] = []
    output_root = OUT.resolve()
    for base, dirs, names in os.walk(ROOT, topdown=True, followlinks=False):
        bp = Path(base)
        kept = []
        for dirname in dirs:
            candidate = bp / dirname
            if dirname in EXCLUDED_DIRS or candidate.is_symlink():
                continue
            try:
                if candidate.resolve().is_relative_to(output_root):
                    continue
            except OSError:
                continue
            kept.append(dirname)
        dirs[:] = sorted(kept)
        for name in names:
            p = bp / name
            if p.suffix.lower() in IMAGE_EXTS | VISUAL_DOC_EXTS:
                files.append(p)
    return sorted(files, key=lambda p: rel(p).casefold())


def render_svg(raw: bytes, browser: Any) -> bytes:
    encoded = base64.b64encode(raw).decode("ascii")
    page = browser.new_page(viewport={"width": 640, "height": 640}, device_scale_factor=1)
    page.route("**/*", lambda route: route.abort())
    html = (
        "<html><body style='margin:0;width:640px;height:640px;display:grid;place-items:center;background:#fff'>"
        f"<img src='data:image/svg+xml;base64,{encoded}' style='max-width:620px;max-height:620px;object-fit:contain'>"
        "</body></html>"
    )
    try:
        page.set_content(html, wait_until="load", timeout=10000)
        page.locator("img").evaluate("img => img.decode()")
        return page.screenshot(type="png", omit_background=False)
    finally:
        page.close()


def decode_image(raw: bytes) -> tuple[Image.Image, str, int, int, int]:
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    with Image.open(io.BytesIO(raw)) as image:
        detected = image.format or "unknown"
        frames = int(getattr(image, "n_frames", 1))
        width, height = image.size
        image.verify()
    with Image.open(io.BytesIO(raw)) as image:
        image.seek(0)
        return image.convert("RGBA"), detected, width, height, frames


def image_record(path: Path, browser: Any) -> tuple[dict[str, Any], bytes | None]:
    start = time.time()
    record: dict[str, Any] = {
        "audit_schema_version": SCHEMA,
        "file_id": "file:" + rel(path),
        "source_kind": "workspace_file",
        "relative_path": rel(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "source_mtime_utc": None,
        "source_mtime_ns": None,
        "byte_size": None,
        "sha256": None,
        "detected_format": None,
        "mime_type": None,
        "width": None,
        "height": None,
        "aspect_ratio": None,
        "frame_count": None,
        "page_count": None,
        "phash64": None,
        "phash_algorithm": "opencv-dct-32-to-8-v1",
        "decode_status": "pending",
        "decode_error": None,
        "visual_item_ids": [],
        "registry_asset_ids": [],
        "scan_duration_seconds": None,
    }
    try:
        st = path.stat()
        record["byte_size"] = st.st_size
        record["source_mtime_utc"] = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()
        record["source_mtime_ns"] = st.st_mtime_ns
        raw = path.read_bytes()
        record["sha256"] = sha256_bytes(raw)
        if path.suffix.lower() == ".pdf":
            document = fitz.open(stream=raw, filetype="pdf")
            record["detected_format"] = "PDF"
            record["mime_type"] = "application/pdf"
            record["page_count"] = len(document)
            record["decode_status"] = "decoded"
            return record, raw
        if path.suffix.lower() == ".svg":
            rendered = render_svg(raw, browser)
            img, _, width, height, _ = decode_image(rendered)
            record.update({"detected_format": "SVG", "mime_type": "image/svg+xml", "width": width, "height": height,
                           "aspect_ratio": width / height if height else None, "frame_count": 1,
                           "phash64": phash_rgb(img), "decode_status": "decoded"})
            return record, raw
        img, detected, width, height, frames = decode_image(raw)
        record.update({"detected_format": detected, "mime_type": mime_for(path, detected), "width": width,
                       "height": height, "aspect_ratio": width / height if height else None,
                       "frame_count": frames, "phash64": phash(raw), "decode_status": "decoded"})
        return record, raw
    except Exception as exc:
        record["decode_status"] = "unreadable"
        record["decode_error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        return record, None
    finally:
        record["scan_duration_seconds"] = round(time.time() - start, 4)


def render_pdf_page(raw: bytes, page_number: int) -> tuple[bytes, int, int]:
    doc = fitz.open(stream=raw, filetype="pdf")
    page = doc.load_page(page_number)
    rect = page.rect
    scale = min(2.0, 1800 / max(rect.width, rect.height))
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return pix.tobytes("png"), pix.width, pix.height


def open_readonly_db(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN")
    return con


def read_registry() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    assets: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not ASSET_DB.exists():
        return assets, edges, [{"source": rel(ASSET_DB), "error": "registry database missing"}]
    try:
        con = open_readonly_db(ASSET_DB)
        cols = {r[1] for r in con.execute("PRAGMA table_info(assets)")}
        if not cols:
            raise RuntimeError("assets table missing")
        for row in con.execute("SELECT * FROM assets ORDER BY asset_id"):
            d = dict(row)
            for field in ("extra_metadata", "lineage_params", "validation_errors", "font_metadata"):
                if field in d and isinstance(d[field], str):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        d[field + "_parse_error"] = True
            assets.append(d)
        try:
            for row in con.execute("SELECT parent_id, child_id FROM asset_lineage ORDER BY parent_id, child_id"):
                edges.append({"parent_id": row[0], "child_id": row[1], "evidence": "asset_lineage table"})
        except sqlite3.Error as exc:
            errors.append({"source": rel(ASSET_DB), "error": f"asset_lineage: {exc}"})
        con.rollback()
        con.close()
    except Exception as exc:
        errors.append({"source": rel(ASSET_DB), "error": f"{type(exc).__name__}: {exc}"})
    return assets, edges, errors


def iter_json_files() -> Iterable[Path]:
    for base, dirs, files in os.walk(ROOT, topdown=True):
        bp = Path(base)
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and d != "visual_forensics")
        for name in files:
            if Path(name).suffix.lower() in {".json", ".jsonl"}:
                yield bp / name


def extract_asset_ids(obj: Any) -> set[str]:
    ids: set[str] = set()
    pattern = re.compile(r"^(art_[A-Za-z0-9_-]+|asset_[A-Za-z0-9_-]+|att_[a-fA-F0-9]{8,})$")
    def walk(x: Any, key: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, str(k))
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, str) and ("asset" in key.lower() or "artifact" in key.lower() or "attachment" in key.lower()):
            if pattern.match(x):
                ids.add(x)
    walk(obj)
    return ids


def scan_structured_references(asset_ids: set[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for path in iter_json_files():
        if path.resolve().is_relative_to(OUT.resolve()):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".jsonl":
                parsed = [json.loads(line) for line in text.splitlines() if line.strip()]
            else:
                parsed = json.loads(text)
            ids = extract_asset_ids(parsed)
            for aid in sorted(ids):
                if aid in asset_ids:
                    refs.append({"source_path": rel(path), "asset_id": aid, "reference_status": "registered_asset_id_found"})
                else:
                    refs.append({"source_path": rel(path), "asset_id": aid, "reference_status": "unresolved_asset_id"})
        except Exception:
            continue
    return refs


def collect_sessions() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    roots = [ROOT / "runs" / "agent_sessions", ROOT / "runs" / "batches", ROOT / "runs" / "quick_story_jobs",
             ROOT / "runs" / "creative_packages", ROOT / "runs" / "plans", ROOT / "runs" / "phase1_reproduction_traces.json"]
    seen: set[Path] = set()
    for base in roots:
        paths = [base] if base.is_file() else list(base.rglob("*.json")) if base.exists() else []
        for path in paths:
            try:
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for index, message in enumerate(data.get("messages", []) if isinstance(data, dict) else []):
                if not isinstance(message, dict):
                    continue
                calls = {c.get("call_id"): c for c in message.get("tool_calls", []) if isinstance(c, dict)}
                results = {r.get("call_id"): r for r in message.get("tool_results", []) if isinstance(r, dict)}
                for call_id, call in calls.items():
                    tool_id = str(call.get("tool_id", ""))
                    # Preserve planning and Canvas handoff calls that explain how
                    # an image entered (or failed to enter) the page document.
                    if not any(part in tool_id.lower() for part in (
                        "generate", "analy", "inspect", "verif", "panel", "canvas", "image", "asset"
                    )):
                        continue
                    result = results.get(call_id, {})
                    args = call.get("arguments") or {}
                    output = result.get("output") or {}
                    inputs = sorted(extract_asset_ids(args))
                    outputs = sorted(extract_asset_ids(output))
                    prompt = args.get("prompt") if isinstance(args, dict) else None
                    events.append({
                        "audit_schema_version": SCHEMA,
                        "event_id": f"tool:{call_id}", "source_path": rel(path),
                        "session_id": data.get("session_id") if isinstance(data, dict) else None,
                        "project_id": data.get("project_id") if isinstance(data, dict) else None,
                        "message_index": index, "message_id": message.get("message_id"),
                        "timestamp": message.get("timestamp"), "timestamp_source": "assistant_message_timestamp_not_assumed_provider_start",
                        "tool_id": tool_id, "call_id": call_id, "status": result.get("status", "result_missing"),
                        "arguments": args, "prompt_as_recorded": prompt,
                        "effective_prompt": args.get("effective_prompt") if isinstance(args, dict) else None,
                        "input_asset_ids": inputs, "output_asset_ids": outputs,
                        "provider": output.get("provider"), "model": output.get("model"),
                        "is_simulated": output.get("is_simulated", args.get("is_simulated") if isinstance(args, dict) else None),
                        "duration_seconds": result.get("duration_seconds"),
                        "error": result.get("error"), "error_code": result.get("error_code"),
                        "result_output": output,
                    })
                production_job = message.get("production_job")
                if isinstance(production_job, dict) and production_job.get("job_id"):
                    events.append({
                        "audit_schema_version": SCHEMA,
                        "event_id": "job_snapshot:" + str(production_job.get("job_id")) + ":" + str(production_job.get("updated_at") or index),
                        "source_path": rel(path), "session_id": data.get("session_id"),
                        "project_id": production_job.get("project_id") or data.get("project_id"),
                        "message_index": index, "timestamp": production_job.get("updated_at"),
                        "timestamp_source": "saved_job_updated_at_not_provider_generation_time",
                        "summary_type": "saved_production_job_snapshot", "status": production_job.get("status"),
                        "input_asset_ids": sorted(extract_asset_ids(production_job)), "output_asset_ids": [],
                        "job_snapshot": production_job,
                    })
            # Batch and job summaries are indexed as lifecycle events, not misreported as individual provider calls.
            if isinstance(data, dict) and ("batch_id" in data or "job_id" in data):
                events.append({
                    "audit_schema_version": SCHEMA,
                    "event_id": f"summary:{data.get('batch_id') or data.get('job_id')}",
                    "source_path": rel(path), "project_id": data.get("project_id"),
                    "timestamp": data.get("started_at") or data.get("created_at"),
                    "timestamp_source": "summary_record_timestamp", "status": data.get("status"),
                    "summary_type": "batch_or_job", "summary": data,
                })
    return events


def collect_execution_events() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for path in DB_CANDIDATES:
        if not path.exists():
            sources.append({"path": rel(path), "status": "missing"})
            continue
        try:
            con = open_readonly_db(path)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            source = {"path": rel(path), "status": "readable", "tables": {}}
            for table in sorted(tables):
                if table.startswith("sqlite_"):
                    continue
                count = con.execute(f'SELECT COUNT(*) FROM "{table.replace(chr(34), chr(34)*2)}"').fetchone()[0]
                source["tables"][table] = count
            source["read_transaction_started_at_utc"] = utc_now()
            source["read_transaction_note"] = "Recorded after the first schema query opened the SQLite read snapshot."
            source["database_file_mtime_utc"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            sources.append(source)
            if "events" in tables:
                for row in con.execute("SELECT * FROM events ORDER BY timestamp, event_id"):
                    d = dict(row)
                    try:
                        d["data"] = json.loads(d.pop("data_json", "{}"))
                    except Exception:
                        d["data"] = None
                    events.append({"audit_schema_version": SCHEMA, "source_path": rel(path), "event_id": d.get("event_id"),
                                   "timestamp": d.get("timestamp"), "timestamp_source": "execution_event_timestamp",
                                   "run_id": d.get("run_id"), "operation_id": d.get("operation_id"),
                                   "attempt_id": d.get("attempt_id"), "event_type": d.get("event_type"), "data": d.get("data")})
            con.rollback(); con.close()
        except Exception as exc:
            sources.append({"path": rel(path), "status": "read_error", "error": f"{type(exc).__name__}: {exc}"})
    return events, sources


def read_profile_references() -> list[dict[str, Any]]:
    path = ROOT / "runs" / "creative_profiles.db"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        con = open_readonly_db(path)
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, kind in (("character_profile_versions", "character"), ("style_profile_versions", "style")):
            if table not in tables:
                continue
            for row in con.execute(f'SELECT * FROM "{table}" ORDER BY profile_id, version'):
                d = dict(row)
                try:
                    payload = json.loads(d.get("payload_json") or "{}")
                except Exception:
                    payload = {}
                project_id = d.get("project_id")
                if not project_id:
                    lookup = "character_profiles" if kind == "character" else "style_profiles"
                    if lookup in tables:
                        match = con.execute(f'SELECT project_id,name FROM "{lookup}" WHERE profile_id=?', (d.get("profile_id"),)).fetchone()
                        if match:
                            project_id = match["project_id"]
                out.append({
                    "entity_type": kind, "profile_id": d.get("profile_id"), "version": d.get("version"),
                    "project_id": project_id, "created_at": d.get("created_at"),
                    "reference_asset_ids": sorted(extract_asset_ids(payload)),
                    "payload": payload,
                })
        con.rollback(); con.close()
    except Exception as exc:
        out.append({"entity_type": "read_error", "profile_id": None, "error": f"{type(exc).__name__}: {exc}"})
    return out


def asset_registration_events(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for asset in assets:
        if asset.get("asset_type") not in {"image_generated", "image_reference"} and not str(asset.get("mime_type") or "").startswith("image/"):
            continue
        extra = asset.get("extra_metadata") if isinstance(asset.get("extra_metadata"), dict) else {}
        refs = set()
        for key, value in extra.items():
            if "asset" in key.lower() or "reference" in key.lower() or "artifact" in key.lower():
                refs |= extract_asset_ids({key: value})
        events.append({
            "audit_schema_version": SCHEMA,
            "event_id": "asset_record:" + str(asset.get("asset_id")),
            "source_path": rel(ASSET_DB), "project_id": asset.get("project_id"), "run_id": asset.get("run_id"),
            "timestamp": asset.get("created_at"), "timestamp_source": "asset_registry_created_at_is_registration_not_generation_time",
            "generation_timestamp": None,
            "generation_timestamp_explanation": "Registry created_at records asset registration only; generation time requires a provider/tool event.",
            "event_kind": "asset_registration_record", "tool_id": None, "status": asset.get("lifecycle_status"),
            "call_id": None, "input_asset_ids": sorted(refs), "output_asset_ids": [asset.get("asset_id")],
            "prompt_as_recorded": extra.get("prompt"), "effective_prompt": extra.get("effective_prompt"),
            "provider": extra.get("provider"), "model": extra.get("model"),
            "is_simulated": extra.get("is_simulated"), "asset_metadata": asset,
        })
    return events


def make_graph(asset_rows: list[dict[str, Any]], lineage: list[dict[str, Any]], files: list[dict[str, Any]],
               timeline: list[dict[str, Any]], page_data: list[dict[str, Any]],
               profile_refs: list[dict[str, Any]], references: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for a in asset_rows:
        aid = a["asset_id"]
        nodes["asset:" + aid] = {"id": "asset:" + aid, "kind": "asset", "asset_id": aid, "project_id": a.get("project_id"),
                                  "asset_type": a.get("asset_type"), "sha256": a.get("content_sha256")}
        if a.get("managed_path"):
            fid = a.get("linked_file_id") or ("store-path:runs/artifact_store/" + str(a.get("managed_path")))
            nodes.setdefault(fid, {"id": fid, "kind": "workspace_file_or_store_path", "path": a.get("managed_path")})
            edges.append({"from": fid, "to": "asset:" + aid, "type": "registry_maps_path_to_asset",
                          "verification": "explicit_registry_record", "evidence": "asset registry managed_path"})
    for f in files:
        fid = f["file_id"]
        nodes.setdefault(fid, {"id": fid, "kind": "workspace_file", "path": f.get("relative_path"), "sha256": f.get("sha256")})
    image_assets_by_hash: dict[str, list[str]] = defaultdict(list)
    for a in asset_rows:
        if a.get("asset_type") in {"image_generated", "image_reference"} or str(a.get("mime_type") or "").startswith("image/"):
            if a.get("content_sha256"):
                image_assets_by_hash[a["content_sha256"]].append(a["asset_id"])
    for f in files:
        for aid in image_assets_by_hash.get(f.get("sha256"), []):
            edges.append({"from": f["file_id"], "to": "asset:" + aid,
                          "type": "same_exact_bytes_as_registered_asset", "verification": "sha256_equality",
                          "evidence": f.get("sha256"),
                          "warning": "Exact byte identity does not prove temporal derivation or causality."})
    for e in lineage:
        src, dst = "asset:" + e["parent_id"], "asset:" + e["child_id"]
        nodes.setdefault(src, {"id": src, "kind": "unresolved_asset_reference", "asset_id": e["parent_id"]})
        nodes.setdefault(dst, {"id": dst, "kind": "unresolved_asset_reference", "asset_id": e["child_id"]})
        edges.append({"from": src, "to": dst, "type": "registry_parent_child", "verification": "explicit_registry_edge",
                      "evidence": e.get("evidence")})
    for event in timeline:
        eid = "generation:" + str(event["event_id"])
        nodes[eid] = {"id": eid, "kind": "generation_or_analysis_event", "event_id": event.get("event_id"),
                      "tool_id": event.get("tool_id"), "status": event.get("status"), "source_path": event.get("source_path")}
        for aid in event.get("input_asset_ids", []):
            n = "asset:" + aid
            nodes.setdefault(n, {"id": n, "kind": "unresolved_asset_reference", "asset_id": aid})
            edges.append({"from": n, "to": eid, "type": "explicit_generation_input", "verification": "tool_call_arguments"})
        for aid in event.get("output_asset_ids", []):
            n = "asset:" + aid
            nodes.setdefault(n, {"id": n, "kind": "unresolved_asset_reference", "asset_id": aid})
            edges.append({"from": eid, "to": n, "type": "explicit_generation_output", "verification": "tool_result"})
    for p in page_data:
        pid = f"page:{p['page_id']}:rev:{p['revision']}"
        nodes[pid] = {"id": pid, "kind": "canvas_page_revision", **p}
        for aid in p.get("asset_ids", []):
            n = "asset:" + aid
            nodes.setdefault(n, {"id": n, "kind": "unresolved_asset_reference", "asset_id": aid})
            edges.append({"from": n, "to": pid, "type": "placed_or_referenced_on_page_revision", "verification": "page_document_content"})
    for profile in profile_refs:
        profile_node = f"profile:{profile['entity_type']}:{profile['profile_id']}:v{profile.get('version', 'unknown')}"
        nodes[profile_node] = {"id": profile_node, "kind": "creative_profile_version", **profile}
        for aid in profile.get("reference_asset_ids", []):
            n = "asset:" + aid
            nodes.setdefault(n, {"id": n, "kind": "unresolved_asset_reference", "asset_id": aid})
            edges.append({"from": n, "to": profile_node, "type": "profile_reference_asset",
                          "verification": "creative_profile_version_payload"})
    for ref in references:
        if ref.get("reference_status") in {"page_revision_asset_reference", "creative_profile_version_reference"}:
            continue
        source = "record:" + str(ref.get("source_path", "unknown"))
        nodes.setdefault(source, {"id": source, "kind": "structured_record", "path": ref.get("source_path")})
        aid = ref.get("asset_id")
        if not aid:
            continue
        target = "asset:" + str(aid)
        nodes.setdefault(target, {"id": target, "kind": "unresolved_asset_reference", "asset_id": aid})
        edges.append({"from": source, "to": target, "type": "structured_record_references_asset",
                      "verification": ref.get("reference_status"), "evidence": ref.get("source_path")})
    return {"audit_schema_version": SCHEMA, "nodes": list(nodes.values()), "edges": edges,
            "edge_policy": "Explicit source records only; similarity does not create lineage."}


def create_preview_items(files: list[dict[str, Any]], raw_by_path: dict[str, bytes]) -> list[dict[str, Any]]:
    visual: dict[str, dict[str, Any]] = {}
    for f in files:
        if f.get("decode_status") != "decoded" or not f.get("sha256"):
            continue
        ext = f.get("extension") or Path(f.get("relative_path", "")).suffix.lower()
        raw_key = f.get("raw_source_key") or f.get("relative_path")
        if ext == ".pdf":
            raw = raw_by_path.get(raw_key)
            if not raw:
                continue
            try:
                doc = fitz.open(stream=raw, filetype="pdf")
                page_count = len(doc)
                for pno in range(page_count):
                    png, width, height = render_pdf_page(raw, pno)
                    digest = sha256_bytes(png)
                    vid = "pdfpage:" + hashlib.sha256((f["file_id"] + f"#{pno+1}").encode()).hexdigest()[:16]
                    visual[vid] = {"audit_schema_version": SCHEMA, "visual_item_id": vid,
                                   "kind": "pdf_page_render", "source_file_id": f["file_id"],
                                   "source_path": f.get("relative_path"), "page_number": pno + 1,
                                   "render_sha256": digest, "width": width, "height": height,
                                   "aspect_ratio": width / height if height else None,
                                   "phash64": phash(png), "source_hash": f["sha256"],
                                   "source_kind": f.get("source_kind"),
                                   "registry_asset_ids": [], "inspection_status": "PENDING",
                                   "preview_bytes": png}
            except Exception as exc:
                f["pdf_render_error"] = f"{type(exc).__name__}: {exc}"
            continue
        vid = "visual:" + f["sha256"]
        item = visual.setdefault(vid, {"audit_schema_version": SCHEMA, "visual_item_id": vid,
                                         "kind": "image_file_content", "sha256": f["sha256"],
                                         "width": f.get("width"), "height": f.get("height"),
                                         "aspect_ratio": f.get("aspect_ratio"), "phash64": f.get("phash64"),
                                         "source_file_ids": [], "source_paths": [], "source_raw_keys": [], "source_extensions": [], "git_blob_ids": [], "registry_asset_ids": [],
                                         "inspection_status": "PENDING"})
        item["source_file_ids"].append(f["file_id"])
        item["source_paths"].append(f.get("relative_path", "[Git blob without path]"))
        item["source_raw_keys"].append(raw_key)
        item["source_extensions"].append(ext)
    # Create a compact image preview per exact content item, preserving the original untouched.
    preview_root = OUT / "visual" / "previews"
    preview_root.mkdir(parents=True, exist_ok=True)
    for vid, item in visual.items():
        if "preview_bytes" in item:
            png = item.pop("preview_bytes")
            im = Image.open(io.BytesIO(png)).convert("RGBA")
        else:
            source_keys = item.get("source_raw_keys", [])
            raw_key = next((key for key in source_keys if key in raw_by_path or key + ":render" in raw_by_path), None)
            if raw_key is None:
                continue
            raw = raw_by_path[raw_key]
            path_hint = next((p for p in item.get("source_paths", []) if p), "")
            if Path(path_hint).suffix.lower() == ".svg" or ".svg" in item.get("source_extensions", []):
                raw = raw_by_path.get(raw_key + ":render", raw)
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
        im.thumbnail((720, 720), Image.Resampling.LANCZOS)
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        dest = preview_root / (hashlib.sha256(vid.encode()).hexdigest()[:20] + ".jpg")
        bg.convert("RGB").save(dest, format="JPEG", quality=82, optimize=True)
        item["preview_path"] = rel(dest)
        item["inspection_status"] = "PENDING"
    return sorted(visual.values(), key=lambda x: x["visual_item_id"])


def create_contact_sheets(items: list[dict[str, Any]], per_sheet: int = 24) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sheet_root = OUT / "visual" / "comparisons"
    sheet_root.mkdir(parents=True, exist_ok=True)
    sheets: list[dict[str, Any]] = []
    index: dict[str, Any] = {"audit_schema_version": SCHEMA, "items_per_sheet": per_sheet, "sheets": []}
    ready = [i for i in items if i.get("preview_path")]
    cell_w, cell_h, cols = 300, 310, 4
    for start in range(0, len(ready), per_sheet):
        group = ready[start:start + per_sheet]
        sheet_no = len(sheets) + 1
        rows = (len(group) + cols - 1) // cols
        canvas = Image.new("RGB", (cols * cell_w, rows * cell_h + 42), (238, 238, 238))
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 10), f"Visual audit batch {sheet_no:03d} — {len(group)} content items", fill=(20, 20, 20))
        for j, item in enumerate(group):
            x, y = (j % cols) * cell_w, 42 + (j // cols) * cell_h
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), fill=(250, 250, 250), outline=(150, 150, 150), width=1)
            preview = Image.open(ROOT / item["preview_path"]).convert("RGB")
            preview.thumbnail((cell_w - 16, 235), Image.Resampling.LANCZOS)
            canvas.paste(preview, (x + (cell_w - preview.width) // 2, y + 5))
            short_id = item["visual_item_id"].replace("visual:", "sha:")[:30]
            path_text = (item.get("source_paths") or [item.get("source_path", "")])[0] or "[Git blob without path]"
            path_text = path_text[-38:]
            aliases = len(item.get("source_paths", [])) + len(item.get("registry_asset_ids", []))
            draw.text((x + 6, y + 246), short_id, fill=(10, 10, 10))
            draw.text((x + 6, y + 264), path_text, fill=(45, 45, 45))
            draw.text((x + 6, y + 282), f"{item.get('width','?')}×{item.get('height','?')} · {aliases} mapped records", fill=(45, 45, 45))
        dest = sheet_root / f"batch-{sheet_no:03d}.jpg"
        canvas.save(dest, format="JPEG", quality=88, optimize=True)
        rec = {"batch_id": f"BATCH-{sheet_no:03d}", "sheet_path": rel(dest),
               "visual_item_ids": [i["visual_item_id"] for i in group], "item_count": len(group),
               "inspection_status": "PENDING"}
        sheets.append(rec); index["sheets"].append(rec)
    return sheets, index


def build_ledger(files: list[dict[str, Any]], assets: list[dict[str, Any]], items: list[dict[str, Any]], sheets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    item_by_sha = {i.get("sha256"): i for i in items if i.get("sha256")}
    sheet_by_item = {vid: s["batch_id"] for s in sheets for vid in s["visual_item_ids"]}
    ledger: list[dict[str, Any]] = []
    for f in files:
        if f.get("extension") == ".pdf":
            associated = [i for i in items if i.get("source_file_id") == f["file_id"]]
            if associated:
                for i in associated:
                    ledger.append({"entity_type": "pdf_page", "entity_id": i["visual_item_id"], "file_id": f["file_id"],
                                   "asset_id": "", "content_sha256": i.get("render_sha256"),
                                   "visual_item_id": i["visual_item_id"], "batch_id": sheet_by_item.get(i["visual_item_id"], ""),
                                   "status": "PENDING", "evidence": "", "note": ""})
            else:
                ledger.append({"entity_type": "visual_document", "entity_id": f["file_id"], "file_id": f["file_id"],
                               "asset_id": "", "content_sha256": f.get("sha256"), "visual_item_id": "", "batch_id": "",
                               "status": "UNREADABLE" if f.get("pdf_render_error") else "PENDING", "evidence": "", "note": f.get("pdf_render_error", "")})
            continue
        visual_id = "visual:" + str(f.get("sha256")) if f.get("sha256") else ""
        ledger.append({"entity_type": "workspace_file", "entity_id": f["file_id"], "file_id": f["file_id"],
                       "asset_id": "", "content_sha256": f.get("sha256"), "visual_item_id": visual_id,
                       "batch_id": sheet_by_item.get(visual_id, ""),
                       "status": "PENDING" if f.get("decode_status") == "decoded" else "UNREADABLE",
                       "evidence": "", "note": "" if f.get("decode_status") == "decoded" else f.get("decode_error", "")})
    for a in assets:
        sha = a.get("content_sha256")
        visual_id = "visual:" + str(sha) if sha in item_by_sha else ""
        ledger.append({"entity_type": "registry_asset", "entity_id": "asset:" + str(a.get("asset_id")),
                       "file_id": "file:" + str(a.get("managed_path", "")), "asset_id": a.get("asset_id", ""),
                       "content_sha256": sha, "visual_item_id": visual_id,
                       "batch_id": sheet_by_item.get(visual_id, ""),
                       "status": "PENDING" if visual_id else "INACCESSIBLE",
                       "evidence": "", "note": "" if visual_id else "No matching readable workspace image content found"})
    return ledger


def write_ledger(ledger: list[dict[str, Any]]) -> None:
    path = OUT / "inspection_ledger.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["entity_type", "entity_id", "file_id", "asset_id", "content_sha256", "visual_item_id", "batch_id", "status", "evidence", "note"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(ledger)


def read_ledger() -> list[dict[str, str]]:
    with (OUT / "inspection_ledger.csv").open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cmd_collect(_: argparse.Namespace) -> None:
    started = utc_now()
    OUT.mkdir(parents=True, exist_ok=True)
    source_db_state_before = {}
    for source_db in DB_CANDIDATES:
        if source_db.exists():
            st = source_db.stat()
            source_db_state_before[rel(source_db)] = {"size_bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
    raw_by_path: dict[str, bytes] = {}
    files: list[dict[str, Any]] = []
    browser = None
    pw = None
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
    except Exception:
        browser = None
    paths_to_scan = safe_walk()
    print(f"Scanning {len(paths_to_scan)} workspace visual files...", flush=True)
    for scan_index, path in enumerate(paths_to_scan, 1):
        row, raw = image_record(path, browser)
        if raw is not None:
            raw_by_path[row["relative_path"]] = raw
            if row["extension"] == ".svg":
                try:
                    if browser:
                        raw_by_path[row["relative_path"] + ":render"] = render_svg(raw, browser)
                    else:
                        row["decode_status"] = "unreadable"
                        row["decode_error"] = "Local Chromium unavailable for SVG rendering"
                except Exception as exc:
                    row["decode_status"] = "unreadable"
                    row["decode_error"] = f"SVG render failed: {type(exc).__name__}: {exc}"
        files.append(row)
        if scan_index % 100 == 0 or scan_index == len(paths_to_scan):
            print(f"Scanned {scan_index}/{len(paths_to_scan)} workspace visual files", flush=True)

    all_assets, lineage, db_errors = read_registry()
    image_assets = [a for a in all_assets if a.get("asset_type") in {"image_generated", "image_reference"}
                    or str(a.get("mime_type") or "").startswith("image/")
                    or str(a.get("extension") or "").lower() in IMAGE_EXTS]
    all_asset_ids = {a.get("asset_id") for a in all_assets}
    file_by_rel = {f["relative_path"]: f for f in files}
    image_asset_ids = {a.get("asset_id") for a in image_assets}
    for a in all_assets:
        managed = a.get("managed_path")
        if not managed:
            continue
        full = (ROOT / "runs" / "artifact_store" / managed).resolve()
        try:
            path_rel = full.relative_to(ROOT.resolve()).as_posix()
        except Exception:
            path_rel = ""
        f = file_by_rel.get(path_rel)
        if f:
            if a.get("asset_id") in image_asset_ids:
                f["registry_asset_ids"].append(a.get("asset_id"))
                a["registry_hash_matches_bytes"] = f.get("sha256") == a.get("content_sha256")
            else:
                a["registry_hash_matches_bytes"] = None
            a["linked_file_id"] = f["file_id"]
            a["physical_file_sha256"] = f.get("sha256")
        else:
            a["linked_file_id"] = None
            a["physical_file_sha256"] = None
            a["registry_hash_matches_bytes"] = None
            a["file_resolution_status"] = "missing_or_path_outside_scanned_root"

    git_rows: list[dict[str, Any]] = []
    git_commit_times: dict[str, dict[str, Any]] = {}
    git_errors: list[dict[str, Any]] = []
    try:
        output = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=ROOT, text=True, errors="replace")
        seen: set[tuple[str, str]] = set()
        for line in output.splitlines():
            parts = line.split(" ", 1)
            if len(parts) != 2 or Path(parts[1]).suffix.lower() not in IMAGE_EXTS | VISUAL_DOC_EXTS:
                continue
            oid, git_path = parts
            if (oid, git_path) in seen:
                continue
            seen.add((oid, git_path))
            raw_key = "git:" + oid
            try:
                raw = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=ROOT)
                ext = Path(git_path).suffix.lower()
                row = {"audit_schema_version": SCHEMA, "file_id": f"git:{oid}:{git_path}",
                       "source_kind": "reachable_git_blob", "git_blob_oid": oid, "relative_path": git_path,
                       "extension": ext, "raw_source_key": raw_key, "byte_size": len(raw),
                       "sha256": sha256_bytes(raw), "source_mtime_utc": None, "source_mtime_ns": None,
                       "timestamp_source": "git_object_has_no_filesystem_mtime"}
                git_rows.append(row)
                if ext == ".pdf":
                    doc = fitz.open(stream=raw, filetype="pdf")
                    row.update({"detected_format": "PDF", "mime_type": "application/pdf", "page_count": len(doc), "decode_status": "decoded"})
                elif ext == ".svg":
                    if not browser:
                        row.update({"decode_status": "unreadable", "decode_error": "Local Chromium unavailable for SVG rendering"})
                    else:
                        rendered = render_svg(raw, browser)
                        _, _, width, height, frames = decode_image(rendered)
                        row.update({"detected_format": "SVG", "mime_type": "image/svg+xml", "width": width, "height": height,
                                    "aspect_ratio": width / height if height else None, "frame_count": frames,
                                    "phash64": phash_rgb(Image.open(io.BytesIO(rendered))), "decode_status": "decoded"})
                        raw_by_path[raw_key + ":render"] = rendered
                else:
                    _, fmt, width, height, frames = decode_image(raw)
                    row.update({"detected_format": fmt, "mime_type": mime_for(Path(git_path), fmt), "width": width,
                                "height": height, "aspect_ratio": width / height if height else None,
                                "frame_count": frames, "phash64": phash(raw), "decode_status": "decoded"})
                raw_by_path[raw_key] = raw
                if ext != ".pdf":
                    commit = subprocess.run(["git", "log", "--all", f"--find-object={oid}", "--format=%H%x09%cI", "-n", "1"],
                                            cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip()
                    if commit:
                        commit_id, _, commit_time = commit.partition("\t")
                        row["git_introducing_commit"] = commit_id
                        row["git_commit_time"] = commit_time or None
                        row["git_timestamp_source"] = "git_commit_time_not_generation_time"
            except Exception as exc:
                row = {"audit_schema_version": SCHEMA, "file_id": f"git:{oid}:{git_path}",
                       "source_kind": "reachable_git_blob", "git_blob_oid": oid, "relative_path": git_path,
                       "extension": Path(git_path).suffix.lower(), "decode_status": "inaccessible",
                       "decode_error": f"{type(exc).__name__}: {str(exc)[:300]}"}
                git_rows.append(row)
                git_errors.append({"git_blob_oid": oid, "path": git_path, "error": row["decode_error"]})
    except Exception as exc:
        db_errors.append({"source": "git rev-list", "error": f"{type(exc).__name__}: {exc}"})

    unreachable_rows: list[dict[str, Any]] = []
    try:
        fsck = subprocess.run(["git", "fsck", "--full", "--no-reflogs", "--unreachable", "--no-progress"],
                              cwd=ROOT, text=True, capture_output=True, check=False)
        unreachable_oids = sorted(set(re.findall(r"(?:unreachable|dangling) blob ([0-9a-f]+)", fsck.stdout + "\n" + fsck.stderr)))
        reachable_oids = {r.get("git_blob_oid") for r in git_rows}
        for oid in unreachable_oids:
            if oid in reachable_oids:
                continue
            try:
                raw = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=ROOT)
                row = {"audit_schema_version": SCHEMA, "file_id": "git-unreachable:" + oid,
                       "source_kind": "unreachable_git_blob", "git_blob_oid": oid, "relative_path": None,
                       "extension": None, "raw_source_key": "git-unreachable:" + oid,
                       "byte_size": len(raw), "sha256": sha256_bytes(raw), "source_mtime_utc": None,
                       "timestamp_source": "unreachable_git_object_without_path_or_commit"}
                if raw.startswith(b"%PDF-"):
                    doc = fitz.open(stream=raw, filetype="pdf")
                    row.update({"extension": ".pdf", "detected_format": "PDF", "mime_type": "application/pdf", "page_count": len(doc), "decode_status": "decoded"})
                elif b"<svg" in raw[:8192].lower():
                    row["extension"] = ".svg"
                    if browser:
                        rendered = render_svg(raw, browser); _, _, width, height, frames = decode_image(rendered)
                        row.update({"detected_format": "SVG", "mime_type": "image/svg+xml", "width": width, "height": height,
                                    "aspect_ratio": width / height if height else None, "frame_count": frames,
                                    "phash64": phash_rgb(Image.open(io.BytesIO(rendered))), "decode_status": "decoded"})
                        raw_by_path[row["raw_source_key"] + ":render"] = rendered
                    else:
                        row.update({"decode_status": "unreadable", "decode_error": "Local Chromium unavailable for SVG rendering"})
                else:
                    _, fmt, width, height, frames = decode_image(raw)
                    row.update({"extension": "." + fmt.lower(), "detected_format": fmt, "mime_type": Image.MIME.get(fmt),
                                "width": width, "height": height, "aspect_ratio": width / height if height else None,
                                "frame_count": frames, "phash64": phash(raw), "decode_status": "decoded"})
                raw_by_path[row["raw_source_key"]] = raw
                unreachable_rows.append(row)
            except Exception as exc:
                # Most unreachable blobs are source and build data; an ordinary
                # non-image object is not a visual audit read error.
                if raw.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"%PDF-")) or (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP") or b"<svg" in raw[:8192].lower():
                    git_errors.append({"git_blob_oid": oid, "path": None, "error": f"Recognized visual blob could not be decoded: {type(exc).__name__}: {str(exc)[:200]}"})
    except Exception as exc:
        git_errors.append({"git_blob_oid": None, "path": None, "error": f"git fsck failed: {type(exc).__name__}: {exc}"})
    if browser:
        browser.close()
    if pw:
        pw.stop()

    all_files = files + git_rows + unreachable_rows
    items = create_preview_items(all_files, raw_by_path)
    item_by_sha = {i.get("sha256"): i for i in items if i.get("sha256")}
    for asset in image_assets:
        asset.setdefault("audit_schema_version", SCHEMA)
        visual_item = item_by_sha.get(asset.get("content_sha256"))
        asset["visual_item_id"] = visual_item.get("visual_item_id") if visual_item else None
        if visual_item and asset.get("asset_id") not in visual_item["registry_asset_ids"]:
            visual_item["registry_asset_ids"].append(asset.get("asset_id"))
    for git_row in git_rows + unreachable_rows:
        if git_row.get("decode_status") == "decoded" and git_row.get("sha256"):
            visual_item = item_by_sha.get(git_row["sha256"])
            if visual_item:
                visual_item.setdefault("git_blob_ids", []).append(git_row["file_id"])

    exec_events, db_sources = collect_execution_events()
    timeline = collect_sessions() + exec_events + asset_registration_events(image_assets)
    timeline.sort(key=lambda x: (str(x.get("timestamp") or ""), str(x.get("event_id") or "")))
    references = scan_structured_references(all_asset_ids)
    profile_refs = read_profile_references()
    for profile in profile_refs:
        for aid in profile.get("reference_asset_ids", []):
            references.append({"source_path": rel(ROOT / "runs" / "creative_profiles.db"), "asset_id": aid,
                               "reference_status": "creative_profile_version_reference", "profile_id": profile.get("profile_id"),
                               "profile_version": profile.get("version"), "project_id": profile.get("project_id")})

    page_data: list[dict[str, Any]] = []
    page_db = ROOT / "runs" / "page_documents.db"
    page_db_error = None
    assets_by_id = {a.get("asset_id"): a for a in all_assets}
    if page_db.exists():
        try:
            con = open_readonly_db(page_db)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            page_heads = {}
            if "pages" in tables:
                page_heads = {r["page_id"]: dict(r) for r in con.execute(
                    "SELECT page_id,project_id,revision,artifact_id,created_at,updated_at,deleted_at FROM pages")}
            if "page_revisions" in tables:
                for row in con.execute("SELECT page_id,revision,artifact_id,created_at FROM page_revisions ORDER BY page_id,revision"):
                    d = dict(row); head = page_heads.get(d["page_id"], {})
                    artifact = assets_by_id.get(d.get("artifact_id"))
                    referenced = []
                    if artifact and artifact.get("managed_path"):
                        stored = (ROOT / "runs" / "artifact_store" / artifact["managed_path"]).resolve()
                        try:
                            referenced = sorted(extract_asset_ids(json.loads(stored.read_text(encoding="utf-8"))))
                        except Exception:
                            pass
                    page_data.append({"page_id": d["page_id"], "project_id": head.get("project_id"),
                                      "revision": d["revision"], "artifact_id": d.get("artifact_id"),
                                      "created_at": d.get("created_at"), "updated_at": head.get("updated_at"),
                                      "deleted_at": head.get("deleted_at"), "asset_ids": referenced})
            con.rollback(); con.close()
        except Exception as exc:
            page_db_error = f"{type(exc).__name__}: {exc}"
    if page_db_error:
        db_errors.append({"source": rel(page_db), "error": page_db_error})
    references.extend({"source_path": rel(page_db), "asset_id": aid, "reference_status": "page_revision_asset_reference",
                       "page_id": page["page_id"], "revision": page["revision"]}
                      for page in page_data for aid in page.get("asset_ids", []))

    graph = make_graph(all_assets, lineage, all_files, timeline, page_data, profile_refs, references)
    sheets, sheet_index = create_contact_sheets(items)
    ledger = build_ledger(all_files, image_assets, items, sheets)
    for f in all_files:
        if f.get("extension") != ".pdf" and f.get("sha256"):
            f["visual_item_id"] = "visual:" + f["sha256"]
        else:
            f["visual_item_id"] = None
        f["inspection_status"] = "PENDING" if f.get("decode_status") == "decoded" else f.get("decode_status", "UNREADABLE").upper()
    for asset in image_assets:
        asset["inspection_status"] = "PENDING" if asset.get("visual_item_id") else "INACCESSIBLE"

    write_jsonl(OUT / "inventory" / "files.jsonl", all_files)
    write_jsonl(OUT / "inventory" / "registry_assets.jsonl", image_assets)
    write_jsonl(OUT / "inventory" / "references.jsonl", references)
    write_jsonl(OUT / "generation" / "timeline.jsonl", timeline)
    write_json(OUT / "lineage" / "graph.json", graph)
    write_jsonl(OUT / "visual" / "items.jsonl", items)
    write_json(OUT / "visual" / "sheet_index.json", sheet_index)
    source_stat_after = {}
    for path in DB_CANDIDATES:
        if path.exists():
            st = path.stat()
            source_stat_after[rel(path)] = {"size_bytes": st.st_size,
                "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                "mtime_ns": st.st_mtime_ns}
    changed_db_sources = [path for path, state in source_db_state_before.items()
                          if path not in source_stat_after
                          or state.get("size_bytes") != source_stat_after[path].get("size_bytes")
                          or state.get("mtime_ns") != source_stat_after[path].get("mtime_ns")]
    initial_workspace = {f.get("file_id"): f for f in files if f.get("source_kind") == "workspace_file"}
    current_workspace = {"file:" + rel(p): p for p in safe_walk()}
    new_workspace_paths = sorted(set(current_workspace) - set(initial_workspace))
    missing_workspace_paths = sorted(set(initial_workspace) - set(current_workspace))
    changed_workspace_hashes = []
    recheck_errors = []
    for file_id, path in current_workspace.items():
        if file_id not in initial_workspace:
            continue
        try:
            current_hash = sha256_file(path)
            if current_hash != initial_workspace[file_id].get("sha256"):
                changed_workspace_hashes.append(file_id)
        except Exception as exc:
            recheck_errors.append({"file_id": file_id, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
    stability_checked_at = utc_now()
    write_json(OUT / "source_manifest.json", {
        "audit_schema_version": SCHEMA, "audit_started_at": started, "inventory_written_at": utc_now(),
        "repository_root": str(ROOT), "excluded_directory_names": sorted(EXCLUDED_DIRS),
        "workspace_visual_file_count": len(files), "reachable_git_blob_path_pairs": len(git_rows),
        "unreachable_git_image_blob_count": len(unreachable_rows), "all_registered_asset_records": len(all_assets),
        "registered_image_asset_record_count": len(image_assets), "registry_lineage_edge_count": len(lineage),
        "database_sources": db_sources, "database_read_errors": db_errors, "git_read_errors": git_errors,
        "database_file_state_after_read": source_stat_after,
        "database_file_state_before_read": source_db_state_before,
        "database_sources_changed_during_audit": changed_db_sources,
        "database_file_stability_note": "Read-only SQLite transactions were used; file size/mtime snapshots are included to reveal concurrent source changes.",
        "workspace_file_stability": {"checked_at": stability_checked_at,
            "new_workspace_paths": new_workspace_paths, "missing_workspace_paths": missing_workspace_paths,
            "content_changed_file_ids": changed_workspace_hashes, "recheck_errors": recheck_errors,
            "stable": not (new_workspace_paths or missing_workspace_paths or changed_workspace_hashes or recheck_errors)},
        "registry_asset_type_counts": dict(Counter(str(a.get("asset_type")) for a in all_assets)),
        "registry_image_asset_type_counts": dict(Counter(str(a.get("asset_type")) for a in image_assets)),
        "registry_image_records_missing_managed_path": sum(1 for a in image_assets if not a.get("managed_path")),
        "registry_image_records_missing_content_hash": sum(1 for a in image_assets if not a.get("content_sha256")),
        "registry_image_records_with_unresolved_file": sum(1 for a in image_assets if not a.get("linked_file_id")),
        "page_revision_count": len(page_data),
        "page_revision_asset_reference_count": sum(len(p.get("asset_ids", [])) for p in page_data),
        "structured_asset_reference_count": len(references),
        "filesystem_scan_note": "Filesystem mtime and registry created_at are not treated as generation timestamps.",
    })
    write_ledger(ledger)
    print(json.dumps({"workspace_visual_files": len(files), "reachable_git_blobs": len(git_rows),
                      "unreachable_git_image_blobs": len(unreachable_rows), "all_registry_assets": len(all_assets),
                      "registry_image_assets": len(image_assets), "lineage_edges": len(lineage),
                      "visual_items": len(items), "sheets": len(sheets), "ledger_rows": len(ledger),
                      "db_errors": len(db_errors), "git_errors": len(git_errors)}, indent=2))


def cmd_mark_reviewed(args: argparse.Namespace) -> None:
    batch_id = args.batch.upper()
    index_path=OUT/"visual"/"sheet_index.json"
    index=json.loads(index_path.read_text(encoding="utf-8"))
    sheet=next((s for s in index.get("sheets",[]) if s["batch_id"].upper()==batch_id),None)
    if not sheet: raise SystemExit(f"Unknown batch {batch_id}")
    reviewed_at=utc_now()
    items_path=OUT/"visual"/"items.jsonl";items=read_jsonl(items_path)
    reviewed=set(sheet["visual_item_ids"])
    for item in items:
        if item["visual_item_id"] in reviewed:
            item["inspection_status"]="INSPECTED"
            item["inspection_evidence"]=sheet["sheet_path"]
            item["inspection_note"]=args.note
            item["inspected_at"]=reviewed_at
    write_jsonl(items_path,items)
    reviewed_item_map={item["visual_item_id"]:item for item in items if item.get("inspection_status")=="INSPECTED"}
    files_path=OUT/"inventory"/"files.jsonl"; file_rows=read_jsonl(files_path)
    reviewed_pages=defaultdict(set); all_pages=defaultdict(set)
    for item in items:
        if item.get("kind")=="pdf_page_render":
            all_pages[item.get("source_file_id")].add(item.get("visual_item_id"))
            if item.get("inspection_status")=="INSPECTED":
                reviewed_pages[item.get("source_file_id")].add(item.get("visual_item_id"))
    for row in file_rows:
        if row.get("extension")==".pdf":
            fid=row.get("file_id")
            if all_pages.get(fid) and all_pages[fid] <= reviewed_pages.get(fid,set()):
                row["inspection_status"]="INSPECTED"; row["inspection_evidence"]="multiple reviewed PDF page sheets"
            continue
        visual_id="visual:"+str(row.get("sha256")) if row.get("sha256") else None
        if visual_id in reviewed_item_map:
            row["inspection_status"]="INSPECTED"
            row["inspection_evidence"]=reviewed_item_map[visual_id].get("inspection_evidence")
            row["inspection_note"]=reviewed_item_map[visual_id].get("inspection_note")
    write_jsonl(files_path,file_rows)
    assets_path=OUT/"inventory"/"registry_assets.jsonl"; asset_rows=read_jsonl(assets_path)
    for row in asset_rows:
        item=reviewed_item_map.get(row.get("visual_item_id"))
        if item:
            row["inspection_status"]="INSPECTED"
            row["inspection_evidence"]=item.get("inspection_evidence")
            row["inspection_note"]=item.get("inspection_note")
    write_jsonl(assets_path,asset_rows)
    sheet["inspection_status"]="INSPECTED";sheet["inspected_at"]=reviewed_at;sheet["inspection_note"]=args.note
    write_json(index_path,index)
    ledger=read_ledger()
    for row in ledger:
        if row.get("visual_item_id") in reviewed:
            row["status"]="INSPECTED";row["evidence"]=sheet["sheet_path"];row["note"]=args.note
    write_ledger(ledger)
    write_jsonl(OUT/"visual"/"reviews.jsonl",[
        {"audit_schema_version":SCHEMA,"batch_id":batch_id,"visual_item_ids":sorted(reviewed),
         "evidence":sheet["sheet_path"],"inspection_note":args.note,"inspected_at":reviewed_at}
        for _ in [0]
    ] if not (OUT/"visual"/"reviews.jsonl").exists() else read_jsonl(OUT/"visual"/"reviews.jsonl") + [
        {"audit_schema_version":SCHEMA,"batch_id":batch_id,"visual_item_ids":sorted(reviewed),
         "evidence":sheet["sheet_path"],"inspection_note":args.note,"inspected_at":reviewed_at}])
    print(f"Marked {len(reviewed)} visual items and {sum(1 for r in ledger if r.get('visual_item_id') in reviewed)} mapped records in {batch_id} as inspected.")


def hamming(a: str, b: str) -> int:
    try: return (int(a,16)^int(b,16)).bit_count()
    except Exception: return 65


def cmd_validate(_: argparse.Namespace) -> None:
    files=read_jsonl(OUT/"inventory"/"files.jsonl")
    assets=read_jsonl(OUT/"inventory"/"registry_assets.jsonl")
    items=read_jsonl(OUT/"visual"/"items.jsonl")
    ledger=read_ledger()
    graph=json.loads((OUT/"lineage"/"graph.json").read_text(encoding="utf-8"))
    manifest=json.loads((OUT/"source_manifest.json").read_text(encoding="utf-8"))
    node_ids={n["id"] for n in graph.get("nodes",[])}
    dangling=[e for e in graph.get("edges",[]) if e.get("from") not in node_ids or e.get("to") not in node_ids]
    status_counts=Counter(r.get("status") for r in ledger)
    content_status=Counter(i.get("inspection_status") for i in items)
    asset_mismatch=[a["asset_id"] for a in assets if a.get("linked_file_id") and a.get("registry_hash_matches_bytes") is False]
    inaccessible_assets=[a.get("asset_id") for a in assets if not a.get("visual_item_id")]
    unreadable_files=[f.get("file_id") for f in files if f.get("decode_status") != "decoded"]
    unresolved_asset_edges=[e for e in graph.get("edges",[]) if e.get("verification")=="explicit_generation_input" and e.get("to") not in node_ids]
    exact_groups=Counter(f.get("sha256") for f in files if f.get("sha256"))
    registry_hash_groups=defaultdict(list)
    for asset in assets:
        if asset.get("content_sha256"):
            registry_hash_groups[asset["content_sha256"]].append(asset.get("asset_id"))
    phash_items=[i for i in items if i.get("phash64")]
    near_pairs=[]
    for i,a in enumerate(phash_items):
        for b in phash_items[i+1:]:
            d=hamming(a["phash64"],b["phash64"])
            if 0<d<=8: near_pairs.append({"a":a["visual_item_id"],"b":b["visual_item_id"],"hamming_distance":d,"review_required":True})
    tool_events=[e for e in read_jsonl(OUT/"generation"/"timeline.jsonl") if e.get("tool_id")]
    tool_status_counts=Counter(str(e.get("status") or "unknown") for e in tool_events)
    generation_tool_events=[e for e in tool_events if "generat" in str(e.get("tool_id", "")).lower()]
    unregistered_visuals=[i["visual_item_id"] for i in items if i.get("kind")=="image_file_content" and not i.get("registry_asset_ids")]
    late_delta=read_jsonl(OUT/"inventory"/"late_snapshot_delta.jsonl")
    late_status_counts=Counter(r.get("status", "unknown") for r in late_delta)
    unresolved_reference_edges=[e for e in graph.get("edges",[]) if e.get("verification")=="unresolved_asset_id"]
    review_rows=read_jsonl(OUT/"visual"/"reviews.jsonl")
    sheet_index=json.loads((OUT/"visual"/"sheet_index.json").read_text(encoding="utf-8"))
    source_stable=manifest.get("workspace_file_stability",{}).get("stable",False)
    database_stable=not manifest.get("database_sources_changed_during_audit",[])
    coverage={
        "audit_schema_version":SCHEMA,"generated_at":utc_now(),
        "workspace_image_and_visual_document_file_count":sum(1 for f in files if f.get("source_kind")=="workspace_file"),
        "reachable_git_visual_blob_path_count":sum(1 for f in files if f.get("source_kind")=="reachable_git_blob"),
        "unreachable_git_visual_blob_count":sum(1 for f in files if f.get("source_kind")=="unreachable_git_blob"),
        "total_workspace_and_git_visual_file_or_blob_records":len(files),
        "source_extension_counts":dict(Counter(str(f.get("extension") or "unknown") for f in files)),
        "registered_image_asset_record_count":len(assets),
        "registered_image_unique_sha256_count":len(registry_hash_groups),
        "registered_image_duplicate_sha256_group_count":sum(1 for group in registry_hash_groups.values() if len(group)>1),
        "registered_image_duplicate_alias_record_count":sum(len(group)-1 for group in registry_hash_groups.values() if len(group)>1),
        "largest_registered_hash_alias_groups":[{"sha256":sha,"asset_ids":ids,"count":len(ids)} for sha,ids in sorted(registry_hash_groups.items(),key=lambda x:(-len(x[1]),x[0]))[:20]],
        "unregistered_image_content_item_count":len(unregistered_visuals),
        "unregistered_image_visual_item_ids":unregistered_visuals[:500],
        "unique_readable_visual_item_count":len(items),
        "unique_image_content_item_count":sum(1 for i in items if i.get("kind")=="image_file_content"),
        "rendered_pdf_page_count":sum(1 for i in items if i.get("kind")=="pdf_page_render"),
        "physical_or_blob_file_status_counts":dict(Counter(f.get("decode_status") for f in files)),
        "inspection_ledger_entity_counts":dict(Counter(r.get("entity_type") for r in ledger)),
        "inspection_ledger_status_counts":dict(status_counts),
        "visual_item_inspection_status_counts":dict(content_status),
        "registered_sha_mismatch_count":len(asset_mismatch),"registered_sha_mismatch_asset_ids":asset_mismatch,
        "registered_assets_without_visual_content_count":len(inaccessible_assets),
        "registered_assets_without_visual_content_ids":inaccessible_assets[:500],
        "unreadable_or_inaccessible_file_count":len(unreadable_files),
        "unreadable_or_inaccessible_file_ids":unreadable_files[:500],
        "exact_duplicate_sha256_groups":len([n for n in exact_groups.values() if n>1]),
        "exact_duplicate_file_or_blob_aliases":sum(n-1 for n in exact_groups.values() if n>1),
        "perceptual_candidate_pairs_hamming_le_8":near_pairs,
        "timeline_tool_call_count":len(tool_events),"timeline_tool_status_counts":dict(tool_status_counts),
        "timeline_generation_tool_call_count":len(generation_tool_events),
        "late_snapshot_delta_file_count":len(late_delta),
        "late_snapshot_delta_status_counts":dict(late_status_counts),
        "late_snapshot_delta_pdf_page_count":sum(int(r.get("page_count") or 0) for r in late_delta),
        "late_snapshot_delta_pdf_pages_rendered":0,
        "captured_registry_all_asset_rows":manifest.get("all_registered_asset_records"),
        "registry_table_observation_count":manifest.get("registry_snapshot_discrepancy",{}).get("later_table_count_observed"),
        "later_registry_row_difference_unreconciled":manifest.get("registry_snapshot_discrepancy",{}).get("difference_not_reconciled"),
        "unreachable_nonvisual_git_blob_count":manifest.get("unreachable_nonvisual_git_blob_count",0),
        "contact_sheets_reviewed":len(review_rows),
        "contact_sheets_total":len(sheet_index.get("sheets",[])),
        "audit_stop_reason":manifest.get("visual_review_stop_reason"),
        "unresolved_asset_reference_edge_count":len(unresolved_reference_edges),
        "evidence_supported_relationship_edge_count":len(graph.get("edges",[]))-len(unresolved_reference_edges),
        "workspace_snapshot_stable":source_stable,"database_files_stable":database_stable,
        "lineage_graph_node_count":len(node_ids),"lineage_graph_edge_count":len(graph.get("edges",[])),
        "lineage_graph_dangling_edge_count":len(dangling),"lineage_graph_dangling_edges":dangling[:100],
        "full_visual_coverage":(
            all(i.get("inspection_status")=="INSPECTED" for i in items)
            and all(r.get("status")=="INSPECTED" for r in ledger)
            and not asset_mismatch and not dangling and not inaccessible_assets and not unreadable_files
            and source_stable and database_stable
        ),
        "coverage_rule":"No full-coverage claim while any relevant image is pending, unreadable, inaccessible, hash-mismatched, or has unresolved graph references. Similarity candidates require visual review.",
    }
    write_json(OUT/"coverage.json",coverage)
    print(json.dumps({k:v for k,v in coverage.items() if k not in {"perceptual_candidate_pairs_hamming_le_8","lineage_graph_dangling_edges"}},indent=2))


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("collect");p.set_defaults(func=cmd_collect)
    p=sub.add_parser("mark-reviewed");p.add_argument("--batch",required=True);p.add_argument("--note",required=True);p.set_defaults(func=cmd_mark_reviewed)
    p=sub.add_parser("validate");p.set_defaults(func=cmd_validate)
    args=parser.parse_args();args.func(args)


if __name__=="__main__":
    main()
