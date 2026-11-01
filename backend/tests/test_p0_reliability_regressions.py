"""Regression coverage for previously fabricated success and attachment handling."""
import base64
import hashlib
import json
from io import BytesIO

import pytest
from PIL import Image

from app.config import InkLoopConfig
from app.contracts.artifacts import AssetType
from app.creative.analyzer import AnalysisUnavailableError, StyleAnalyzer, _call_vision_json, _parse_json_object
from app.creative.orchestration import CreativeOrchestrator, GenerationProviderUnavailableError
from app.storage.registry import AssetRegistry
from app.verification.style_identity_qa import StyleIdentityQAService
from app.agent.file_inspector import inspect_document_bytes, resolve_document_path, extract_stored_document
from app.agent.model_client import AgentModelClient


def _png() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (16, 16), (10, 20, 30)).save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def registry(tmp_path):
    return AssetRegistry(store_root=tmp_path / "assets", db_path=tmp_path / "assets" / "registry.db", project_root=tmp_path)


def test_reference_analysis_fails_closed_without_credentials(registry):
    asset = registry.ingest_bytes(_png(), "ref.png", "p0_project", AssetType.IMAGE_REFERENCE)
    analyzer = StyleAnalyzer(registry, config=InkLoopConfig(model_api_key=None))
    with pytest.raises(AnalysisUnavailableError, match="requires configured"):
        analyzer.analyze_references("p0_project", [asset.asset_id])


def test_style_analysis_endpoint_reports_provider_unavailable_as_503(monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    import app.api.routers.creative as creative_router

    class UnavailableAnalyzer:
        def __init__(self, registry): pass
        def analyze_references(self, **kwargs):
            raise AnalysisUnavailableError("Reference analysis requires configured vision-provider credentials.")

    monkeypatch.setattr(creative_router, "StyleAnalyzer", UnavailableAnalyzer)
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/projects/p0_project/creative/styles/analyze",
        json={"asset_ids": ["unused"]},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ERR_VISION_PROVIDER_UNAVAILABLE"


def test_vision_request_contains_exact_registered_image_bytes_and_mime(monkeypatch):
    raw = _png()
    captured = {}

    class Response:
        status_code = 200
        def json(self):
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": '{"ok":true}'}]}]}

    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            captured.update(kwargs["json"])
            return Response()

    monkeypatch.setattr("app.creative.analyzer.httpx.Client", Client)
    cfg = InkLoopConfig(model_api_key="unit-test-key")
    assert _call_vision_json(cfg, [(raw, "image/png")], "inspect", "test") == {"ok": True}
    image = next(item for item in captured["input"][0]["content"] if item["type"] == "input_image")
    assert image["image_url"] == "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def test_vision_json_parser_ignores_prose_and_parses_first_complete_object():
    assert _parse_json_object(
        'Here is the result:\n```json\n{"linework": "clean {and} varied"}\n```\nDone.'
    ) == {"linework": "clean {and} varied"}


def test_live_empty_model_response_does_not_report_success(monkeypatch):
    class Response:
        status_code = 200
        def json(self): return {"output": []}

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: Response())
    client = AgentModelClient(config=InkLoopConfig(model_api_key="unit-test-key"))
    calls, text, _ = client._plan_live_action([{"role": "user", "content": "do something"}], [], {"project_id": "p"})
    assert calls is None
    assert "no usable response" in text
    assert "processed your request" not in text


def test_explicit_offline_mode_does_not_fabricate_document_analysis():
    client = AgentModelClient(config=InkLoopConfig(model_api_key=None))
    calls, text, _ = client._plan_offline_action(
        [{"role": "user", "content": "Summarize this", "attachments": [{"mime_type": "text/plain"}]}],
        [], {"project_id": "p", "offline_mode": True},
    )
    assert calls is None
    assert "cannot interpret document contents" in text
    assert "No summary" in text


def test_generation_requires_credentials_unless_offline_mode_is_explicit(monkeypatch, registry):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.setenv("INKLOOP_OFFLINE_MODE", "0")
    with pytest.raises(GenerationProviderUnavailableError):
        CreativeOrchestrator(registry=registry)


def test_qa_does_not_assign_fake_identity_or_variation_scores():
    result = StyleIdentityQAService().evaluate(
        run_id="run-test", asset_id="asset-test", image_bytes=_png(), requested_scene_action="walk",
    )
    assert result.status == "not_verified"
    assert result.passed is False
    assert result.identity_score is None
    assert result.variation_score is None
    assert result.leakage_detected is None


def test_document_upload_storage_roundtrip_preserves_bytes_and_extracted_text(tmp_path, monkeypatch):
    import app.agent.file_inspector as inspector
    monkeypatch.setattr(inspector, "_attachment_project_dir", lambda project_id: tmp_path / project_id)
    raw = "An actual creator brief.\nKeep this exact sentence.".encode("utf-8")
    attachment = inspect_document_bytes(raw, "brief.txt", "p0_project")
    path = resolve_document_path(attachment.attachment_id, "p0_project")
    assert path.read_bytes() == raw
    assert extract_stored_document(path) == raw.decode("utf-8")
    assert attachment.content_sha256 == hashlib.sha256(raw).hexdigest()

    captured = {}
    class Response:
        status_code = 200
        def json(self): return {"output": []}
    def fake_post(*args, **kwargs):
        captured.update(kwargs["json"])
        return Response()
    monkeypatch.setattr("httpx.post", fake_post)
    client = AgentModelClient(config=InkLoopConfig(model_api_key="unit-test-key"))
    client._plan_live_action(
        [{"role": "user", "content": "Summarize the attached brief.", "attachments": [attachment.model_dump()]}],
        [], {"project_id": "p0_project"},
    )
    sent_text = "\n".join(
        item.get("text", "")
        for message in captured["input"] if isinstance(message, dict)
        for item in message.get("content", []) if isinstance(item, dict)
    )
    assert raw.decode("utf-8") in sent_text


def test_agent_followup_omits_repeated_attachment_and_records_only_provider_usage(monkeypatch):
    from types import SimpleNamespace

    import httpx

    captured = {}

    class Response:
        status_code = 200
        def json(self):
            return {
                "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Done."}]}],
                "usage": {"input_tokens": 120, "output_tokens": 18, "total_tokens": 138},
            }

    def fake_post(*_args, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr(httpx, "post", fake_post)
    client = AgentModelClient(config=SimpleNamespace(
        model_api_key="unit-test-key", muse_spark_model="test-model", meta_base_url="https://provider.invalid",
    ))
    client._plan_live_action(
        messages=[{"role": "user", "content": "Continue the analysis.", "attachments": [{
            "attachment_id": "already-inspected-image", "mime_type": "image/png", "filename": "reference.png",
        }]}],
        available_tools=[],
        project_context={"project_id": "p0_project"},
        iteration=2,
    )

    assert not any(
        item.get("type") == "input_image"
        for message in captured["input"] if isinstance(message, dict)
        for item in message.get("content", []) if isinstance(item, dict)
    )
    assert client.last_usage == {"input_tokens": 120, "output_tokens": 18, "total_tokens": 138}


def test_document_upload_endpoint_stores_and_serves_validated_content(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    import app.agent.file_inspector as inspector
    monkeypatch.setattr(inspector, "_attachment_project_dir", lambda project_id: tmp_path / project_id)
    content = b"Creator-owned note reaches the live model as document text."
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/agent/attachments/upload",
        files={"file": ("brief.txt", content, "text/plain")},
        data={"project_id": "p0_upload"},
    )
    assert response.status_code == 200
    attachment = response.json()
    assert attachment["mime_type"] == "text/plain"
    assert attachment["content_sha256"] == hashlib.sha256(content).hexdigest()
    downloaded = client.get(f"/api/v1/agent/attachments/{attachment['attachment_id']}/file?project_id=p0_upload")
    assert downloaded.status_code == 200
    assert downloaded.content == content


def test_batch_generation_without_credentials_returns_503_instead_of_simulation(monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    import app.api.routers.generation as generation

    monkeypatch.setattr(generation.InkLoopConfig, "load", lambda: InkLoopConfig(model_api_key=None))
    monkeypatch.setattr(generation, "_get_project_bible", lambda project_id: type("Bible", (), {"bible_version": "1.0.0"})())
    response = TestClient(create_app()).post("/api/v1/generation/batches", json={
        "project_id": "p0_no_provider",
        "scenes": [{"scene_id": "scene-1", "scene_index": 0, "title": "A scene", "shot_type": "wide", "action": "A quiet moment", "character_ids": []}],
    })
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ERR_IMAGE_PROVIDER_UNAVAILABLE"


def test_creative_provider_failure_does_not_fall_back_to_procedural(monkeypatch, tmp_path):
    from app.creative.service import CreativeDirectorService, CreativeProviderError
    from app.creative.schemas import CreativeMode
    import app.creative.service as service_module

    monkeypatch.delenv("INKLOOP_OFFLINE_MODE", raising=False)
    monkeypatch.setattr(service_module.InkLoopConfig, "load", lambda: InkLoopConfig(model_api_key="configured"))
    monkeypatch.setattr(service_module, "synthesize_with_live_ai", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("provider timeout")))
    monkeypatch.setattr(service_module, "build_dynamic_universe", lambda **kwargs: (_ for _ in ()).throw(AssertionError("procedural fallback must not run")))
    service = CreativeDirectorService(packages_dir=tmp_path / "packages")
    with pytest.raises(CreativeProviderError, match="provider timeout"):
        service.develop_universe("provider_error_project", "A new story", CreativeMode.QUICK_CONCEPT)


def test_creative_develop_without_credentials_returns_503(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    from app.creative.service import CreativeDirectorService
    import app.api.routers.creative as creative_router
    import app.creative.service as service_module

    monkeypatch.delenv("INKLOOP_OFFLINE_MODE", raising=False)
    monkeypatch.setattr(service_module.InkLoopConfig, "load", lambda: InkLoopConfig(model_api_key=None))
    service = CreativeDirectorService(packages_dir=tmp_path / "packages")
    monkeypatch.setattr(CreativeDirectorService, "_instance", service)
    response = TestClient(create_app()).post("/api/v1/creative/develop", json={
        "project_id": "provider_missing_project",
        "user_prompt": "A creator's new story",
        "offline_mode": False,
    })
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ERR_CREATIVE_PROVIDER_UNAVAILABLE"


def test_in_panel_generation_without_credentials_does_not_substitute_simulation(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    import app.api.routers.editor as editor

    doc = SimpleNamespace(project_id="p0_panel", layout=SimpleNamespace(get_panel=lambda panel_id: object()))
    monkeypatch.setattr(editor, "get_page_store", lambda: SimpleNamespace(get=lambda page_id: doc))
    monkeypatch.setattr(editor.InkLoopConfig, "load", lambda: InkLoopConfig(model_api_key=None))
    response = TestClient(create_app()).post(
        "/api/v1/editor/pages/page-1/panels/panel-1/generate",
        json={"prompt": "A creator's scene", "character_ids": []},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ERR_IMAGE_PROVIDER_UNAVAILABLE"


def test_batch_submission_is_idempotent_and_rejects_reused_id_with_new_inputs(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    from app.schemas import BatchStatus, BatchSummary
    import app.api.routers.generation as generation

    monkeypatch.setattr(generation, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(generation.InkLoopConfig, "load", lambda: InkLoopConfig(model_api_key=None))
    monkeypatch.setattr(generation, "_get_project_bible", lambda project_id: type("Bible", (), {"bible_version": "1.0.0"})())
    calls = []

    class SavingOrchestrator:
        def __init__(self, **kwargs): pass
        def orchestrate_batch(self, spec):
            calls.append(spec)
            summary = BatchSummary(
                batch_id=spec.batch_id, status=BatchStatus.RUNNING, project_id=spec.project_id,
                story_id=spec.story_id, bible_version="1.0.0", total_panels=1,
                successful_panels=0, failed_panels=0, unresolved_panels=1,
                total_attempts=0, attempts_per_panel={}, total_duration_seconds=0,
                started_at="2026-10-30T00:00:00Z", is_simulated=True,
                source_scenes=spec.scenes, request_fingerprint=spec.request_fingerprint,
            )
            path = tmp_path / "runs" / "batches" / f"{spec.batch_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(summary.model_dump_json(), encoding="utf-8")
            return summary

    monkeypatch.setattr(generation, "BatchOrchestrator", SavingOrchestrator)
    client = TestClient(create_app())
    payload = {
        "batch_id": "idem-p0-batch", "project_id": "p0_idem", "is_simulated": True,
        "scenes": [{"scene_id": "scene-1", "scene_index": 0, "title": "Scene", "shot_type": "wide", "action": "A beat"}],
    }
    first = client.post("/api/v1/generation/batches", json=payload)
    second = client.post("/api/v1/generation/batches", json=payload)
    changed = {**payload, "scenes": [{**payload["scenes"][0], "action": "A different beat"}]}
    conflict = client.post("/api/v1/generation/batches", json=changed)
    assert first.status_code == second.status_code == 200
    assert len(calls) == 1
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error_code"] == "ERR_BATCH_IDEMPOTENCY_CONFLICT"


def test_missing_project_bible_is_not_replaced_with_demo_canon(monkeypatch, tmp_path):
    from fastapi import HTTPException
    import app.api.routers.generation as generation

    monkeypatch.setattr(generation, "PROJECT_ROOT", tmp_path)
    with pytest.raises(HTTPException) as missing:
        generation._get_project_bible("new_creator_project")
    assert missing.value.status_code == 404
    assert not (tmp_path / "runs" / "new_creator_project" / "bible.json").exists()
    with pytest.raises(HTTPException) as unsafe:
        generation._get_project_bible(".._.._outside")
    assert unsafe.value.status_code == 422

