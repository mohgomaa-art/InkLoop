from app.agent.coordinator import _tools_for_turn
from app.agent.registry import CapabilityRegistry, IMAGE_CHAT_TOOL_IDS
from app.agent.model_client import AgentModelClient
from app.agent.schemas import ToolCall


def test_chat_catalog_exposes_revisioned_canvas_edit_and_delivery_operations():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}
    available = {tool.tool_id for tool in registry.list_image_chat_tools()}
    required = {
        "editor.list_pages",
        "editor.get_page",
        "editor.add_image_to_panel",
        "editor.update_image_placement",
        "editor.reshape_panel",
        "editor.add_text_layer",
        "editor.add_line_layer",
        "editor.update_vector_layer",
        "editor.remove_layer",
        "canvas.composite_page",
        "export.generate_comic_book",
    }

    assert required <= IMAGE_CHAT_TOOL_IDS
    assert required <= callable_ids
    assert required <= available


def test_tool_catalog_is_filtered_to_callable_adapters():
    registry = CapabilityRegistry()
    chat_tools = registry.list_image_chat_tools()
    assert chat_tools
    assert all(tool.tool_id in registry._adapters for tool in chat_tools)
    assert all(tool.is_callable for tool in chat_tools)


def test_skill_is_not_loaded_when_its_required_tool_is_absent_from_this_turn():
    from app.agent.production import load_relevant_workflow_skills

    selected = load_relevant_workflow_skills(
        "Please create a comic story with panels and dialogue.",
        {"planning.plan_panels", "canvas.create_page_from_template"},
    )
    assert selected == ""


def test_export_intent_receives_export_and_page_context_tools_only():
    registry = CapabilityRegistry()
    selected = _tools_for_turn(registry.list_image_chat_tools(), "Export this page as PDF")
    selected_ids = {tool.tool_id for tool in selected}

    assert "export.generate_comic_book" in selected_ids
    assert "editor.list_pages" in selected_ids
    assert "planning.plan_panels" not in selected_ids


def test_read_only_story_bible_inspection_does_not_get_routed_to_story_planning():
    registry = CapabilityRegistry()
    selected = _tools_for_turn(
        registry.list_image_chat_tools(),
        "Inspect Nour's character details and canon anchor in the Story Bible.",
    )
    selected_ids = {tool.tool_id for tool in selected}
    assert "canon.inspect_characters" in selected_ids
    assert "canon.inspect_reference_anchor" in selected_ids
    assert "planning.plan_panels" not in selected_ids


def test_sequential_generation_plan_uses_budget_plan_tool():
    registry = CapabilityRegistry()
    selected = _tools_for_turn(
        registry.list_image_chat_tools(),
        "Draft a 6-panel sequential generation plan for Chapter 1 Scene 2 within a $0.50 budget ceiling.",
    )
    assert [tool.tool_id for tool in selected] == ["plan.draft_plan"]


def test_single_image_generation_is_not_routed_to_story_planning_by_scene_word():
    registry = CapabilityRegistry()
    selected = _tools_for_turn(
        registry.list_image_chat_tools(),
        "Generate one image of the approved Nour character using the current scene brief.",
    )
    selected_ids = {tool.tool_id for tool in selected}
    assert "generation.generate_image" in selected_ids
    assert "planning.plan_panels" not in selected_ids


def test_story_preview_uses_typed_lettering_plan_before_canvas_mutations():
    registry = CapabilityRegistry()
    selected = _tools_for_turn(
        registry.list_image_chat_tools(),
        "Create a comic story with panels and exact dialogue; add its text to the Canvas page.",
    )
    selected_ids = {tool.tool_id for tool in selected}

    assert selected_ids == {"planning.plan_panels"}
    schema = selected[0].parameters_schema
    beat_text = schema["$defs"]["StoryBeatDraft"]["properties"]["text"]
    assert beat_text["description"]
    assert "text" in schema["$defs"]["StoryBeatDraft"]["required"]


def test_offline_canvas_fallback_uses_current_page_revision_and_real_panel():
    registry = CapabilityRegistry()
    project_id = "tool_discovery_revision_test"
    create = registry.dispatch(ToolCall(
        call_id="create_revision_test_page",
        tool_id="canvas.create_page_from_template",
        arguments={"project_id": project_id, "layout_template": "four_panel_cinematic"},
    ), {"project_id": project_id})
    assert create.status == "success", create.error
    page_id = create.output["page_id"]

    from app.api.routers.editor import get_page_store
    initial = get_page_store().get(page_id)
    first_panel = sorted(initial.layout.panel_slots, key=lambda panel: panel.reading_order)[0].panel_id
    changed = registry.dispatch(ToolCall(
        call_id="make_page_revision_two",
        tool_id="editor.add_text_layer",
        arguments={
            "page_id": page_id,
            "expected_revision": initial.revision,
            "panel_id": first_panel,
            "text": "Existing note",
        },
    ), {"project_id": project_id})
    assert changed.status == "success", changed.error

    client = AgentModelClient()
    calls, response, _label = client.plan_next_action(
        messages=[{"role": "user", "content": "add text layer 'New lettering' to the canvas editor"}],
        available_tools=registry.list_image_chat_tools(),
        project_context={"project_id": project_id, "offline_mode": True},
    )
    assert response is None
    assert calls and calls[0].tool_id == "editor.add_text_layer"
    assert calls[0].arguments["page_id"] == page_id
    assert calls[0].arguments["expected_revision"] == changed.output["revision"]
    assert calls[0].arguments["panel_id"] == first_panel

    result = registry.dispatch(calls[0], {"project_id": project_id})
    assert result.status == "success", result.error
    saved = get_page_store().get(page_id)
    assert saved.revision == changed.output["revision"] + 1
    assert any(layer.metadata.get("text") == "New lettering" for layer in saved.layers)


def test_offline_editor_fallback_never_invents_page_or_placeholder_text():
    project_id = "tool_discovery_empty_project"
    client = AgentModelClient()
    calls, response, _label = client.plan_next_action(
        messages=[{"role": "user", "content": "add text layer to canvas editor"}],
        available_tools=CapabilityRegistry().list_image_chat_tools(),
        project_context={"project_id": project_id, "offline_mode": True},
    )
    assert calls is None
    assert "no edit was made" in response
    assert "placeholder" not in response


def test_agent_lettering_composite_and_export_use_same_persisted_page(monkeypatch, tmp_path):
    from app.api.routers import assets as assets_router, editor as editor_router
    from app.agent import registry as registry_module
    from app.editor.store import PageDocumentStore
    from app.storage.registry import AssetRegistry

    assets = AssetRegistry(tmp_path / "assets", db_path=tmp_path / "assets.sqlite")
    pages = PageDocumentStore(tmp_path / "pages.sqlite", assets)
    monkeypatch.setattr(assets_router, "get_registry", lambda: assets)
    monkeypatch.setattr(editor_router, "get_page_store", lambda: pages)
    monkeypatch.setattr(registry_module, "_get_asset_registry", lambda: assets)
    registry = CapabilityRegistry()
    project_id = "same_page_production_test"
    ctx = {"project_id": project_id, "offline_mode": True}

    created = registry.dispatch(ToolCall(
        call_id="same_doc_create",
        tool_id="canvas.create_page_from_template",
        arguments={"project_id": project_id, "layout_template": "four_panel_cinematic"},
    ), ctx)
    assert created.status == "success", created.error
    page_id, panel_id = created.output["page_id"], created.output["panel_ids"][0]

    lettering = registry.dispatch(ToolCall(
        call_id="same_doc_text",
        tool_id="editor.add_text_layer",
        arguments={
            "page_id": page_id,
            "expected_revision": created.output["revision"],
            "panel_id": panel_id,
            "text": "The evidence wins.",
            "layer_id": "text_evidence_wins",
            "direction": "ltr",
        },
    ), ctx)
    assert lettering.status == "success", lettering.error

    bubble = registry.dispatch(ToolCall(
        call_id="same_doc_bubble",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": page_id,
            "expected_revision": lettering.output["revision"],
            "panel_id": panel_id,
            "text": "We can try.",
            "speaker": "Muse",
            "bubble_shape": "oval",
            "tail_type": "smooth_pointer",
        },
    ), ctx)
    assert bubble.status == "success", bubble.error
    saved = pages.get(page_id)
    assert saved.revision == bubble.output["revision"]
    assert any(layer.layer_id == "text_evidence_wins" for layer in saved.layers)
    assert any(layer.layer_id == bubble.output["bubble_id"] for layer in saved.layers)

    composite = registry.dispatch(ToolCall(
        call_id="same_doc_composite",
        tool_id="canvas.composite_page",
        arguments={"page_id": page_id, "project_id": project_id},
    ), ctx)
    assert composite.status == "success", composite.error
    composite_asset = assets.resolve_asset(composite.output["composite_page_artifact_id"], verify_integrity=True)
    assert composite_asset.metadata.project_id == project_id
    assert composite.output["revision"] == saved.revision

    exported = registry.dispatch(ToolCall(
        call_id="same_doc_export",
        tool_id="export.generate_comic_book",
        arguments={"page_id": page_id, "project_id": project_id, "target_format": "pdf"},
    ), ctx)
    assert exported.status == "success", exported.error
    export_asset = assets.resolve_asset(exported.output["export_artifact_id"], verify_integrity=True)
    assert export_asset.metadata.project_id == project_id
    assert exported.output["page_count"] == 1
    assert exported.output["byte_size"] > 0
    assert exported.output["sha256"]
