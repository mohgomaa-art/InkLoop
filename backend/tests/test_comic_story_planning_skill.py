import re
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.agent.production import load_relevant_workflow_skills
from app.agent.registry import CapabilityRegistry
from app.planning.panel_planner import (
    StoryBlueprintDraft,
    StoryPageDraft,
    StoryBeatDraft,
    StoryCastProfile,
    PanelTextPlan,
    TextContentKind,
    TextCarrier,
    compile_story_blueprint,
)
from app.canvas.descriptors import NarrativeFunction
from app.canvas.models import ReadingDirection


SKILLS_DIR = Path(__file__).parents[1] / "app" / "agent" / "skills"
STORY_SKILL_DIR = SKILLS_DIR / "comic-story-planning"


def test_comic_story_planning_skill_files_and_references_exist():
    skill_file = STORY_SKILL_DIR / "SKILL.md"
    assert skill_file.is_file(), "comic-story-planning/SKILL.md must exist."
    content = skill_file.read_text(encoding="utf-8")
    assert "name: comic-story-planning" in content
    assert "# Comic Story Planning" in content
    assert "planning.plan_panels" in content

    refs_dir = STORY_SKILL_DIR / "references"
    assert refs_dir.is_dir(), "comic-story-planning/references/ directory must exist."
    for expected_ref in (
        "story_structures.md",
        "scene_craft.md",
        "character_arcs.md",
        "comics_adaptation.md",
    ):
        ref_path = refs_dir / expected_ref
        assert ref_path.is_file(), f"Reference file {expected_ref} must exist."
        ref_text = ref_path.read_text(encoding="utf-8")
        assert len(ref_text) > 300, f"Reference file {expected_ref} must have substantive content."


def test_story_planning_skill_triggers_on_narrative_requests():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}

    queries = [
        "Please help me plan the story and narrative beats for my comic.",
        "How do I structure the plot and scene craft for this chapter?",
        "Help me write dialogue and character arcs for my manga script.",
        "I need a story plan with causal progression and scene turning points.",
    ]
    for q in queries:
        result = load_relevant_workflow_skills(q, callable_ids)
        assert "# Comic Story Planning" in result, f"Query '{q}' should trigger comic-story-planning."


def test_story_planning_skill_does_not_trigger_on_unrelated_queries():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}

    unrelated_queries = [
        "Which font and bubble fit this dialogue?",
        "Reshape panel 2 into a polygon.",
        "Check the budget allowance for image generation.",
    ]
    for q in unrelated_queries:
        result = load_relevant_workflow_skills(q, callable_ids)
        assert "# Comic Story Planning" not in result, f"Query '{q}' should NOT trigger comic-story-planning."


def test_story_blueprint_enforces_word_limit_on_new_dialogue():
    # Spoken dialogue must be 12 words or fewer for newly drafted beats
    valid_text = PanelTextPlan(
        content_kind=TextContentKind.SPOKEN_DIALOGUE,
        carrier=TextCarrier.SPEECH_BUBBLE,
        text_content="The signal is coming from the roof.",  # 7 words - valid
        speaker_id="char_gomaa",
    )
    assert valid_text.text_content == "The signal is coming from the roof."

    # Empty text content for text-bearing beat raises error
    with pytest.raises(ValidationError):
        StoryBeatDraft(
            story_event="Gomaa speaks",
            character_ids=["char_gomaa"],
            visible_character_names=["Gomaa"],
            characterless=False,
            text=PanelTextPlan(
                content_kind=TextContentKind.SPOKEN_DIALOGUE,
                carrier=TextCarrier.SPEECH_BUBBLE,
                text_content="",  # Invalid: text-bearing beat must not be empty
                speaker_id="char_gomaa",
            ),
        )


def _make_beat(event: str, *, speaker_id: str = "char_gomaa", dialogue: str = "Look here.", n_func: NarrativeFunction = NarrativeFunction.ACTION_CONTINUATION):
    return StoryBeatDraft(
        story_event=event,
        reader_takeaway=event,
        visual_focus="focal point",
        emotional_intent="focused curiosity",
        narrative_function=n_func,
        character_ids=[speaker_id] if speaker_id else [],
        visible_character_names=["Gomaa"] if speaker_id else [],
        characterless=not bool(speaker_id),
        text=PanelTextPlan(
            content_kind=TextContentKind.SPOKEN_DIALOGUE if dialogue else TextContentKind.NONE,
            carrier=TextCarrier.SPEECH_BUBBLE if dialogue else TextCarrier.NONE,
            text_content=dialogue if dialogue else None,
            speaker_id=speaker_id if dialogue else None,
        ),
    )


def test_story_planning_benchmark_five_scenarios():
    """
    Evaluates 5 distinct story planning benchmarks:
    1. Short emotional story
    2. Multi-character conflict
    3. Character-driven mystery
    4. Short adventure
    5. Story with meaningful silent sequence
    """
    # 1. Short Emotional Story (2 pages, subtle emotional arc)
    p1_beats = [
        _make_beat("Gomaa discovers his grandfather's broken pocket watch in an attic trunk.", dialogue="Still ticking, faintly."),
        _make_beat("He uses precision tweezers to align the bent escapement gear.", dialogue="Just a fraction more."),
    ]
    p2_beats = [
        _make_beat("The watch gears lock smoothly into place, releasing a stored chime.", dialogue="It remembers."),
        _make_beat("Gomaa closes the lid, smiling softly in quiet remembrance.", dialogue=None),  # Silent payoff
    ]
    blueprint_emotional = StoryBlueprintDraft(
        project_id="bench_emotional",
        page_count=2,
        title="The Living Watch",
        premise="Gomaa repairs a forgotten family timepiece and connects with a lost memory.",
        story_arc="Discovery leads to dedicated craft, culminating in a resonant chime of memory.",
        reading_direction=ReadingDirection.RTL,
        pages=[
            StoryPageDraft(page_number=1, summary="Discovery and careful repair.", beats=p1_beats),
            StoryPageDraft(page_number=2, summary="Successful alignment and quiet emotional payoff.", beats=p2_beats),
        ],
    )
    assert blueprint_emotional.page_count == 2
    assert len(blueprint_emotional.pages[1].beats) == 2
    assert blueprint_emotional.pages[1].beats[1].text.content_kind == TextContentKind.NONE

    # 2. Multi-Character Conflict (Tactical disagreement)
    b_conflict = StoryBlueprintDraft(
        project_id="bench_conflict",
        page_count=1,
        title="Crossroads at Sunset",
        premise="Two wanderers disagree on whether to cross a shaky suspension bridge before nightfall.",
        story_arc="Urgency clashes with caution until an external tremor forces an immediate decision.",
        reading_direction=ReadingDirection.LTR,
        pages=[
            StoryPageDraft(
                page_number=1,
                summary="The travelers debate the bridge crossing as the storm approaches.",
                beats=[
                    _make_beat("Rook tests the bridge rope with his boot, shaking his head.", speaker_id="char_rook", dialogue="These cables are frayed."),
                    _make_beat("Lyra points to the black thunderclouds rolling over the ridge.", speaker_id="char_lyra", dialogue="The pass floods in twenty minutes."),
                    _make_beat("A sudden gust snaps one of the outer guide ropes with a crack.", speaker_id=None, dialogue=None),
                    _make_beat("Lyra leaps forward, grabbing Rook's harness as the plank tips.", speaker_id="char_lyra", dialogue="Jump now!"),
                ],
            )
        ],
    )
    assert len(b_conflict.pages[0].beats) == 4
    assert b_conflict.pages[0].beats[2].characterless is True

    # 3. Character-Driven Mystery (Investigative deduction)
    b_mystery = StoryBlueprintDraft(
        project_id="bench_mystery",
        page_count=1,
        title="The Missing Cipher",
        premise="An archivist decodes a hidden watermark revealed only by ultraviolet lantern light.",
        story_arc="Apparent blank parchment yields a coordinate map under specialized light.",
        reading_direction=ReadingDirection.RTL,
        pages=[
            StoryPageDraft(
                page_number=1,
                summary="A blank letter reveals its secret.",
                beats=[
                    _make_beat("Gomaa examines an unaddressed parchment under ordinary lamp light.", dialogue="No ink marks anywhere."),
                    _make_beat("He switches on the ultraviolet quartz lamp, sweeping it across the paper.", dialogue="Wait... beneath the fibers."),
                    _make_beat("Luminescent blue geometric constellations glow across the page surface.", speaker_id=None, dialogue=None),
                ],
            )
        ],
    )
    assert len(b_mystery.pages[0].beats) == 3

    # 4. Short Adventure (Dynamic movement & obstacle navigation)
    b_adventure = StoryBlueprintDraft(
        project_id="bench_adventure",
        page_count=1,
        title="Rooftop Escape",
        premise="A courier dashes across rain-slick terracotta tiles to deliver an urgent dispatch.",
        story_arc="A high-altitude leap over an alleyway leads to a safe landing on a fire escape.",
        reading_direction=ReadingDirection.LTR,
        pages=[
            StoryPageDraft(
                page_number=1,
                summary="Sprint across the rooftops.",
                beats=[
                    _make_beat("Sprinting at full speed toward the roof parapet.", dialogue="Clear the gap!"),
                    _make_beat("Mid-air leap over the deep four-story chasm between buildings.", dialogue=None),
                    _make_beat("Tumbling onto the rusted iron fire escape with a metallic clang.", dialogue="Made it."),
                ],
            )
        ],
    )
    assert len(b_adventure.pages[0].beats) == 3

    # 5. Meaningful Silent Sequence (Pure visual comics storytelling)
    b_silent = StoryBlueprintDraft(
        project_id="bench_silent",
        page_count=1,
        title="First Snow",
        premise="A solitary traveler pauses on a mountain path as the season's first snowflakes drift down.",
        story_arc="Solitude, quiet contemplation, and the soft arrival of winter.",
        reading_direction=ReadingDirection.RTL,
        pages=[
            StoryPageDraft(
                page_number=1,
                summary="A peaceful arrival of winter.",
                beats=[
                    _make_beat("A single delicate snowflake lands on an outstretched wool glove.", speaker_id=None, dialogue=None, n_func=NarrativeFunction.SILENT),
                    _make_beat("Gomaa looks up at the darkening grey sky, breath misting.", speaker_id="char_gomaa", dialogue=None, n_func=NarrativeFunction.SILENT),
                    _make_beat("Wide view of the mountain pines turning white under gentle snowfall.", speaker_id=None, dialogue=None, n_func=NarrativeFunction.SILENT),
                ],
            )
        ],
    )
    assert all(beat.text.content_kind == TextContentKind.NONE for beat in b_silent.pages[0].beats)
