import shutil
from pathlib import Path

from app.agent.registry import CapabilityRegistry, IMAGE_CHAT_TOOL_IDS
from app.agent.schemas import CapabilityStatus, ToolDefinition


def _tool(tool_id, *, status=CapabilityStatus.AVAILABLE, is_callable=True):
    return ToolDefinition(
        tool_id=tool_id,
        name=tool_id.split(".")[-1].replace("_", " ").title(),
        domain=tool_id.split(".")[0],
        purpose=f"Run {tool_id}.",
        status=status,
        is_callable=is_callable,
    )


def test_image_chat_catalog_contains_only_scoped_available_tools_with_adapters():
    registry = CapabilityRegistry.__new__(CapabilityRegistry)
    registry._tools = {
        "generation.generate_image": _tool("generation.generate_image"),
        "canon.inspect_characters": _tool("canon.inspect_characters"),
        "canon.apply_approved_mutation": _tool("canon.apply_approved_mutation"),
        "canvas.add_speech_bubble": _tool("canvas.add_speech_bubble"),
        "workspace.get_project_context": _tool("workspace.get_project_context"),
        "image.analyze_semantics": _tool(
            "image.analyze_semantics",
            status=CapabilityStatus.NOT_IMPLEMENTED,
            is_callable=False,
        ),
        "assets.list_assets": _tool("assets.list_assets"),
    }
    registry._adapters = {
        tool_id: (lambda _args, _ctx: {})
        for tool_id in (
            "generation.generate_image",
            "canon.inspect_characters",
            "canon.apply_approved_mutation",
            "canvas.add_speech_bubble",
            "workspace.get_project_context",
            "assets.list_assets",
        )
    }

    tool_ids = {tool.tool_id for tool in registry.list_image_chat_tools()}

    assert tool_ids == {
        "generation.generate_image",
        "canon.inspect_characters",
        "canon.apply_approved_mutation",
        "canvas.add_speech_bubble",
        "assets.list_assets",
    }
    assert tool_ids <= IMAGE_CHAT_TOOL_IDS
    assert "workspace.get_project_context" not in tool_ids
    assert "image.analyze_semantics" not in tool_ids


def test_callable_filter_excludes_available_definitions_without_adapters():
    registry = CapabilityRegistry.__new__(CapabilityRegistry)
    registry._tools = {
        "generation.generate_image": _tool("generation.generate_image"),
        "assets.list_assets": _tool("assets.list_assets"),
    }
    registry._adapters = {
        "generation.generate_image": lambda _args, _ctx: {},
    }

    assert [tool.tool_id for tool in registry.list_tools(callable_only=True)] == [
        "generation.generate_image",
    ]


def test_capabilities_endpoint_exposes_the_same_scoped_chat_catalog(monkeypatch):
    from app.api.routers import agent as agent_router

    registry = CapabilityRegistry.__new__(CapabilityRegistry)
    registry._tools = {
        "generation.generate_image": _tool("generation.generate_image"),
        "workspace.get_project_context": _tool("workspace.get_project_context"),
    }
    registry._adapters = {
        tool_id: (lambda _args, _ctx: {})
        for tool_id in registry._tools
    }
    monkeypatch.setattr(CapabilityRegistry, "get_instance", classmethod(lambda _cls: registry))

    response = agent_router.list_capabilities(chat_only=True)

    assert [tool["tool_id"] for tool in response] == ["generation.generate_image"]


def test_character_proposal_resolves_project_from_absolute_store_path(monkeypatch, tmp_path):
    from app.agent import registry as registry_module

    source_bible = Path(__file__).resolve().parents[2] / "runs" / "inkloop" / "bible.json"
    assert source_bible.is_file(), "The repository's default test fixture Bible is required."

    project_dir = tmp_path / "runs" / "inkloop"
    project_dir.mkdir(parents=True)
    shutil.copy2(source_bible, project_dir / "bible.json")
    monkeypatch.setattr(registry_module, "PROJECT_ROOT", tmp_path)
    registry = CapabilityRegistry.__new__(CapabilityRegistry)

    result = registry._propose_mutation_adapter(
        {
            "project_id": "inkloop",
            "target_id": "test_creature",
            "target_type": "character",
            "change_description": "Add a test character proposal.",
            "proposed_changes": {
                "action": "add",
                "name": "Test Creature",
                "attributes": [{"id": "shape", "text": "round with a smile", "required": True}],
            },
        },
        {"project_id": "inkloop"},
    )

    assert result["status"] == "pending"
    assert result["requires_approval"] is True
    assert (project_dir / "canon_proposals.jsonl").is_file()
