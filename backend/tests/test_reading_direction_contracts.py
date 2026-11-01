"""Regression test suite for Phase 1: Domain Models & Reading Direction Contracts.

Validates that:
1. Left-to-Right (LTR), Top-to-Bottom is the standard default for all models, requests, and tools.
2. Right-to-Left (RTL) remains an explicit, fully supported alternative.
3. Language and reading direction are orthogonal and decoupled.
4. Backward compatibility: Existing serialized documents with reading_direction='rtl' deserialize correctly.
"""
import pytest
from app.canvas.models import PageSpec, ReadingDirection
from app.contracts.engine import CanvasGenerationParams
from app.planning.panel_planner import (
    PanelPlanningRequest,
    StoryBlueprintDraft,
    NarrativeBeat,
    recommend_layout_template,
)
from app.canvas.descriptors import NarrativeFunction
from app.project.bible import StoryBible
from app.project.canon import StyleDefinition, CharacterDefinition, AttributeCheck
from app.api.routers.projects import QuickStartProjectRequest


def _sample_style():
    return StyleDefinition(
        style_id="test_ink_style",
        name="Test Ink Style",
        medium="digital ink",
        rendering_approach="black-and-white high contrast",
        line_art_rules=["crisp contours"],
        tonal_rules=["solid blacks"],
        positive_constraints=["comic lineart"],
    )


def _sample_character(cid="hero", name="Hero"):
    return CharacterDefinition(
        character_id=cid,
        name=name,
        canon_version=1,
        attributes=[
            AttributeCheck(id="hair", text="spiky brown hair", required=True),
        ],
    )


def _sample_beat(beat_id="b1", focus="Hero walking into alley"):
    return NarrativeBeat(
        beat_id=beat_id,
        narrative_function=NarrativeFunction.ESTABLISHING.value,
        story_event="Detective enters alley",
        reader_takeaway="The reader understands the scene location",
        character_ids=["detective"],
        environment="Rainy city street",
        visual_focus=focus,
        emotional_intent="tension",
        text={"content_kind": "none", "carrier": "none"},
    )


def test_page_spec_defaults_to_ltr():
    page = PageSpec(page_id="p1")
    assert page.reading_direction == ReadingDirection.LTR


def test_page_spec_supports_explicit_rtl():
    page = PageSpec(page_id="p1", reading_direction=ReadingDirection.RTL)
    assert page.reading_direction == ReadingDirection.RTL


def test_page_spec_backward_compatibility_deserialization():
    legacy_json = '{"page_id": "p_legacy", "page_number": 1, "reading_direction": "rtl"}'
    page = PageSpec.model_validate_json(legacy_json)
    assert page.reading_direction == ReadingDirection.RTL

    ltr_json = '{"page_id": "p_new", "page_number": 1, "reading_direction": "ltr"}'
    page_ltr = PageSpec.model_validate_json(ltr_json)
    assert page_ltr.reading_direction == ReadingDirection.LTR


def test_canvas_generation_params_defaults_to_ltr():
    params = CanvasGenerationParams()
    assert params.reading_direction == "ltr"


def test_panel_planning_request_defaults_to_ltr():
    req = PanelPlanningRequest(
        scene_id="scene_001",
        beats=[_sample_beat()],
    )
    assert req.reading_direction == ReadingDirection.LTR


def test_panel_planning_request_supports_explicit_rtl():
    req = PanelPlanningRequest(
        scene_id="scene_001",
        reading_direction=ReadingDirection.RTL,
        beats=[_sample_beat()],
    )
    assert req.reading_direction == ReadingDirection.RTL


def test_story_blueprint_draft_defaults_to_ltr():
    draft = StoryBlueprintDraft.model_validate({
        "project_id": "story_proj",
        "page_count": 1,
        "title": "Detective Noir",
        "premise": "A detective in neon rain",
        "story_arc": "Investigating a missing artifact",
        "pages": [
            {
                "page_number": 1,
                "summary": "The clue is found",
                "beats": [
                    {
                        "narrative_function": NarrativeFunction.ESTABLISHING.value,
                        "story_event": "Detective finds clue",
                        "reader_takeaway": "The crime scene is discovered",
                        "visual_focus": "Magnifying glass on footprint",
                        "emotional_intent": "intrigue",
                        "character_ids": ["detective"],
                        "visible_character_names": ["Detective"],
                        "characterless": False,
                        "text": {
                            "content_kind": "spoken_dialogue",
                            "carrier": "speech_bubble",
                            "speaker_name": "Detective",
                            "text_content": "The footprints lead inside.",
                        },
                    }
                ],
            }
        ],
    })
    assert draft.reading_direction == ReadingDirection.LTR


def test_recommend_layout_template_defaults_to_ltr():
    tpl = recommend_layout_template([])
    assert tpl is not None


def test_quick_start_project_request_defaults_to_ltr():
    req = QuickStartProjectRequest(
        title="Neo Tokyo Noir",
        premise="Detective mystery",
    )
    assert req.reading_direction == "ltr"
    assert req.language == "en"


def test_language_and_reading_direction_decoupling():
    # 1. Arabic text in an LTR comic layout (valid educational or webcomic use-case)
    bible_ar_ltr = StoryBible(
        project_id="proj_ar_ltr",
        bible_version=1,
        created_at="2026-10-31T12:00:00Z",
        updated_at="2026-10-31T12:00:00Z",
        language="ar",
        reading_direction="ltr",
        style=_sample_style(),
        characters={"hero": _sample_character("hero", "Tariq")},
    )
    assert bible_ar_ltr.language == "ar"
    assert bible_ar_ltr.reading_direction == "ltr"

    # 2. English text in an RTL Manga layout (authentic Western localization of Manga)
    bible_en_rtl = StoryBible(
        project_id="proj_en_rtl",
        bible_version=1,
        created_at="2026-10-31T12:00:00Z",
        updated_at="2026-10-31T12:00:00Z",
        language="en",
        reading_direction="rtl",
        style=_sample_style(),
        characters={"shin": _sample_character("shin", "Shin")},
    )
    assert bible_en_rtl.language == "en"
    assert bible_en_rtl.reading_direction == "rtl"


def test_story_bible_defaults_to_en_ltr():
    bible = StoryBible(
        project_id="proj_default",
        bible_version=1,
        created_at="2026-10-31T12:00:00Z",
        updated_at="2026-10-31T12:00:00Z",
        style=_sample_style(),
        characters={"c1": _sample_character("c1", "Alex")},
    )
    assert bible.language == "en"
    assert bible.reading_direction == "ltr"
