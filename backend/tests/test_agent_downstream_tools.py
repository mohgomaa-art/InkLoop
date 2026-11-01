"""
Integration tests for Agent Runtime Downstream Engine Tools:
E5 (Typography), E6 (Speech Bubbles), E7 (Effects), S6 (Compositor), S8 (Export), Inspection.
Verifies that when INKLOOP_DOWNSTREAM_ENGINES=1 is enabled, all specialist tools are
dynamically callable, typed, registered, and integrated with the AssetRegistry.
"""
import io
import pytest
from PIL import Image

from app.agent.registry import CapabilityRegistry
from app.agent.schemas import ToolCall, CapabilityStatus
from app.contracts.artifacts import AssetType
from app.storage.registry import AssetRegistry


@pytest.fixture
def downstream_registry(monkeypatch, tmp_path):
    monkeypatch.setenv("INKLOOP_DOWNSTREAM_ENGINES", "1")
    reg = AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")
    from app.agent import registry as reg_module
    monkeypatch.setattr(reg_module, "_get_asset_registry", lambda: reg)
    return CapabilityRegistry(), reg


def test_agent_tool_e5_typography_shape_text(downstream_registry):
    agent_reg, asset_reg = downstream_registry
    tool = agent_reg.get_tool("typography.shape_text")
    assert tool is not None
    assert tool.status == CapabilityStatus.AVAILABLE

    authored_text = "مرحبا بك في InkLoop"
    text_result = agent_reg.dispatch(ToolCall(
        call_id="call_text_for_typography",
        tool_id="text.generate_dialogue",
        arguments={
            "scene_id": "typography_scene",
            "panel_id": "typography_panel",
            "scene_action": authored_text,
            "exact_user_text": authored_text,
            "target_language": "ar",
            "target_direction": "rtl",
        },
    ), {"project_id": "test_proj", "offline_mode": True})
    assert text_result.status == "success", text_result.error
    text_block_id = text_result.output["manifest"]["manifest_id"]
    text_content = text_result.output["blocks"][0]["text_content"]

    call = ToolCall(
        call_id="call_type_01",
        tool_id="typography.shape_text",
        arguments={
            "text_block_artifact_id": text_block_id,
            "text_content": text_content,
            "font_family": "Cairo",
            "font_size_pt": 18.0,
            "max_width_px": 250.0,
            "language": "ar",
            "project_id": "test_proj",
        },
    )
    result = agent_reg.dispatch(call, {"project_id": "test_proj"})
    assert result.status == "success", result.error
    assert result.output["lettering_layer_artifact_id"] is not None
    assert result.output["line_count"] >= 1
    assert result.output["measured_bounds"]["width"] > 0
    resolved = asset_reg.resolve_asset(result.output["lettering_layer_artifact_id"])
    assert resolved.absolute_path.exists()


def test_agent_tool_e6_speech_bubble_placement(downstream_registry):
    agent_reg, asset_reg = downstream_registry
    tool = agent_reg.get_tool("speech_bubble.place_bubbles")
    assert tool is not None
    assert tool.status == CapabilityStatus.AVAILABLE

    text_result = agent_reg.dispatch(ToolCall(
        call_id="call_text_for_bubble",
        tool_id="text.generate_dialogue",
        arguments={
            "scene_id": "bubble_scene",
            "panel_id": "bubble_panel",
            "scene_action": "Exact supplied test line.",
            "exact_user_text": "Exact supplied test line.",
            "target_language": "en",
            "target_direction": "ltr",
        },
    ), {"project_id": "test_proj", "offline_mode": True})
    assert text_result.status == "success", text_result.error
    text_block_id = text_result.output["manifest"]["manifest_id"]
    text_content = text_result.output["blocks"][0]["text_content"]

    shaped = agent_reg.dispatch(ToolCall(
        call_id="call_shape_for_bubble",
        tool_id="typography.shape_text",
        arguments={
            "text_block_artifact_id": text_block_id,
            "text_content": text_content,
            "font_family": "DejaVu Sans",
            "font_size_pt": 18,
            "max_width_px": 220,
            "language": "en",
            "project_id": "test_proj",
        },
    ), {"project_id": "test_proj"})
    assert shaped.status == "success", shaped.error

    call = ToolCall(
        call_id="call_bubble_01",
        tool_id="speech_bubble.place_bubbles",
        arguments={
            "text_block_artifact_id": text_block_id,
            "lettering_layer_artifact_id": shaped.output["lettering_layer_artifact_id"],
            "measured_text_bounds": shaped.output["measured_bounds"],
            "bubble_shape": "oval",
            "panel_slot_rect": {"x": 50, "y": 50, "width": 300, "height": 250},
            "tail_target": {"x": 100, "y": 200},
            "project_id": "test_proj",
        },
    )
    result = agent_reg.dispatch(call, {"project_id": "test_proj"})
    assert result.status == "success", result.error
    assert result.output["bubble_layer_artifact_id"] is not None
    assert result.output["bubble_bounds"]["width"] >= 120
    assert not result.output["collision_detected"]


def test_agent_tool_e7_effects_motion(downstream_registry):
    agent_reg, asset_reg = downstream_registry
    tool = agent_reg.get_tool("effects.apply_fx")
    assert tool is not None
    assert tool.status == CapabilityStatus.AVAILABLE

    call = ToolCall(
        call_id="call_fx_01",
        tool_id="effects.apply_fx",
        arguments={
            "effect_category": "speed_lines",
            "target_panel_rect": {"x": 0, "y": 0, "width": 400, "height": 300},
            "intensity": 1.5,
            "direction_deg": 30.0,
            "project_id": "test_proj",
        },
    )
    result = agent_reg.dispatch(call, {"project_id": "test_proj"})
    assert result.status == "success", result.error
    assert result.output["effect_layer_artifact_id"] is not None
    resolved = asset_reg.resolve_asset(result.output["effect_layer_artifact_id"])
    assert resolved.absolute_path.exists()


def test_agent_tool_s6_compositor(downstream_registry):
    agent_reg, asset_reg = downstream_registry
    # Ingest a mock art layer
    img = Image.new("RGBA", (200, 300), (255, 128, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    asset = asset_reg.ingest_bytes(buf.getvalue(), "panel_art.png", "test_proj", AssetType.GENERIC_ARTIFACT)

    call = ToolCall(
        call_id="call_comp_01",
        tool_id="compositor.composite_panels",
        arguments={
            "canvas_spec_artifact_id": "spec_01",
            "ordered_layer_artifact_ids": [asset.asset_id],
            "dpi": 150.0,
            "width": 200,
            "height": 300,
            "project_id": "test_proj",
        },
    )
    result = agent_reg.dispatch(call, {"project_id": "test_proj"})
    assert result.status == "success", result.error
    assert result.output["composite_page_artifact_id"] is not None
    assert result.output["sha256"] is not None


def test_agent_tool_s8_export_delivery(downstream_registry):
    agent_reg, asset_reg = downstream_registry
    img = Image.new("RGB", (400, 600), (240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page_asset = asset_reg.ingest_bytes(buf.getvalue(), "page_01.png", "test_proj", AssetType.COMPOSITE_PAGE)

    call = ToolCall(
        call_id="call_export_01",
        tool_id="export.export_page",
        arguments={
            "page_composite_artifact_ids": [page_asset.asset_id],
            "target_format": "png",
            "dpi": 150.0,
            "reading_direction": "rtl",
            "project_id": "test_proj",
        },
    )
    result = agent_reg.dispatch(call, {"project_id": "test_proj"})
    assert result.status == "success", result.error
    assert result.output["export_artifact_id"] is not None
    assert result.output["byte_size"] > 0
    assert result.output["sha256"] is not None


def test_semantic_analysis_stays_unavailable_instead_of_returning_file_metadata(downstream_registry):
    agent_reg, _asset_reg = downstream_registry
    tool = agent_reg.get_tool("image.analyze_semantics")
    assert tool is not None
    assert tool.status == CapabilityStatus.NOT_IMPLEMENTED
    assert not tool.is_callable
    assert "metadata inspection is not semantic analysis" in tool.status_reason
    call = ToolCall(
        call_id="call_sem_01",
        tool_id="image.analyze_semantics",
        arguments={"attachment_id": "any_asset_id", "project_id": "test_proj"},
    )
    result = agent_reg.dispatch(call, {"project_id": "test_proj"})
    assert result.status == "blocked"
    assert result.error_code == "ERR_TOOL_NOT_IMPLEMENTED"
