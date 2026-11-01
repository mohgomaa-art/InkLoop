import re
from pathlib import Path

from app.agent.production import load_relevant_workflow_skills
from app.agent.registry import CapabilityRegistry


SKILLS_DIR = Path(__file__).parents[1] / "app" / "agent" / "skills"


def test_full_comic_pipeline_loads_only_skills_with_real_callable_tools():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}
    context = "Please create a manga page with panels, character references, dialogue and bubbles."

    result = load_relevant_workflow_skills(context, callable_ids)

    for title in (
        "# Story planning and production to Canvas",
        "# Character, style, and reference continuity",
        "# Image generation and reference verification",
        "# Canvas page layout and editing",
        "# Lettering, bubbles, tails, and typography",
        "# Production verification, recovery, and export",
    ):
        assert title in result
    assert "lip-sync" in result.lower()


def test_targeted_lettering_question_does_not_load_production_skills():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}

    result = load_relevant_workflow_skills("Which font and bubble fit this dialogue?", callable_ids)

    assert "# Lettering, bubbles, tails, and typography" in result
    assert "# Story planning and production to Canvas" not in result
    assert "# Image generation and reference verification" not in result


def test_short_confirmation_inherits_prior_comic_offer_and_tools_are_callable():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}
    result = load_relevant_workflow_skills(
        "The creator pasted a story. Assistant: Should I turn this into a comic page? User: yes pls",
        callable_ids,
    )

    assert "# Story planning and production to Canvas" in result
    assert "# Image generation and reference verification" in result
    assert "# Canvas page layout and editing" in result


def test_active_tool_ids_listed_by_skills_exist_and_have_callable_adapters():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}
    chat_ids = {tool.tool_id for tool in registry.list_image_chat_tools()}
    unknown = set()
    hidden = set()
    for path in SKILLS_DIR.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith(("**Tools:**", "**Callable tools:**", "**Tools this workflow may use:**")):
                ids = set(re.findall(r"`([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)`", line))
                unknown.update(ids - callable_ids)
                hidden.update(ids - chat_ids)
    assert not unknown, f"Skills reference tools without callable adapters: {sorted(unknown)}"
    assert not hidden, f"Skills advertise tools that are not exposed to Agent chat: {sorted(hidden)}"


def test_live_mode_does_not_expose_offline_dialogue_or_lipsync_as_live_tools(monkeypatch):
    monkeypatch.delenv("INKLOOP_OFFLINE_MODE", raising=False)
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}
    assert "text.generate_dialogue" not in callable_ids
    assert "typography.shape_text" not in callable_ids
    lettering_skill = (SKILLS_DIR / "lettering_bubbles_typography.md").read_text(encoding="utf-8")
    assert "deterministic simulated adapter only in explicit offline mode" in lettering_skill
    assert "audio-to-viseme lip-sync tool" in (SKILLS_DIR / "lettering_bubbles_typography.md").read_text(encoding="utf-8")


def test_research_report_covers_requested_topics_and_documents_live_searches():
    report = (SKILLS_DIR.parents[3] / "docs" / "research" / "comic-visual-storytelling-practice-guide.md").read_text(encoding="utf-8")
    for topic in (
        "Format comparison",
        "Panel composition, action, and dynamics",
        "Image design and reference continuity",
        "Effects, visual symbols, and atmosphere",
        "Dialogue, lettering, fonts, and bubbles",
        "Emotion, expression, movement, and human feeling",
        "Still-image speaking pose versus lip-sync",
        "Search log",
        "Source register",
    ):
        assert topic in report
    assert report.count("](") >= 25
    assert "Searches below were issued to the live web search tool" in report
    assert "blocked direct retrieval" in report
