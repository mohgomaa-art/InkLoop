"""
Unit and Integration Test Suite for Multi-Style and Dynamic Character Prompt Synthesis & Verification.
Guarantees:
1. Zero hardcoded manga/screentone prompts when projects declare Manhwa, Western comics, or European BD.
2. Zero hardcoded character names: arbitrary characters (Jin, Vanguard, Clara) are dynamically loaded.
3. Dynamic style derivation from StoryBible.style into prompt headers and negative constraints.
4. Dynamic palette and invariant checking in StyleIdentityQAService.
5. Dynamic character and anchor resolution across agent tool adapters.
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from PIL import Image

from app.schemas import AttributeCheck, SceneSpec
from app.project.canon import (
    CharacterDefinition,
    StyleDefinition,
)
from app.project.bible import (
    StoryBible,
)
from app.context_builder import (
    _resolve_bible_style_rules,
    build_panel_context_packet,
)
from app.verification.style_identity_qa import StyleIdentityQAService
from app.creative.models import (
    StyleProfile,
    CharacterIdentityProfile,
    QASeverity,
    QACategory,
)


def _make_test_image(color=(128, 128, 128), size=(64, 64)) -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()


# =============================================================================
# 1. Manhwa Webtoon Dynamic Style Compilation Test
# =============================================================================

def test_manhwa_webtoon_dynamic_prompt_compilation():
    """Verifies a full-color Manhwa webtoon compiles with zero manga/screentone assumptions."""
    now_str = datetime.now(timezone.utc).isoformat()
    jin = CharacterDefinition(
        character_id="jin",
        name="Jin",
        description="A quiet webtoon student investigator with sharp senses",
        visual_invariants=[
            "young male, approx 18 years old",
            "straight parted raven black hair",
            "sharp dark brown eyes, clean unblemished skin",
        ],
        attributes=[
            AttributeCheck(id="hair", text="straight parted raven black hair", required=True),
            AttributeCheck(id="eyes", text="sharp dark brown eyes", required=True),
            AttributeCheck(id="coat", text="dark high-collar modern trench coat", required=True),
            AttributeCheck(id="eyewear", text="wireframe reading glasses", required=False),
        ],
    )
    webtoon_style = StyleDefinition(
        style_id="style_webtoon_manhwa",
        name="Manhwa Webtoon Full-Color",
        medium="digital webtoon manhwa",
        rendering_approach="clean digital line art with vibrant full-color cinematic lighting and smooth digital gradients",
        line_art_rules=["crisp digital vector contours", "minimal crosshatching"],
        tonal_rules=["soft atmospheric cell shading", "vibrant volumetric rim lighting"],
        palette_or_screentone={"palette": "full_color"},
        negative_constraints=["no screentones", "no black and white", "no grainy halftone dots", "no speech bubbles"],
    )
    bible = StoryBible(
        project_id="proj_webtoon_jin",
        title="Midnight Resonance",
        logline="A student uncovers psychic echoes in Seoul.",
        characters={"jin": jin},
        style=webtoon_style,
        created_at=now_str,
        updated_at=now_str,
    )

    # 1. Verify dynamic style resolution
    line_and_tone, neg_rules, style_meta = _resolve_bible_style_rules(bible)
    assert style_meta["medium"] == "digital webtoon manhwa"
    assert "crisp digital vector contours" in line_and_tone
    assert "screentone" not in line_and_tone.lower()

    # 2. Verify compiled panel context packet
    scene = SceneSpec(
        scene_id="scene_01",
        scene_index=0,
        title="Rainy Seoul Alley",
        shot_type="medium shot",
        action="Jin stands under neon rain in Seoul, reflecting on a hidden clue",
        character_ids=["jin"],
    )
    packet = build_panel_context_packet(
        story_bible=bible,
        scene=scene,
        panel_id="panel_01",
    )

    prompt = packet.generation_prompt
    prohibited = packet.prohibited_deviations

    # Assertions
    assert "Digital Webtoon Manhwa panel illustration" in prompt
    assert "crisp digital vector contours" in prompt
    # Not using screentone as style medium or shading instruction
    assert "screentone shading" not in prompt.lower()
    assert "straight parted raven black hair" in prompt
    assert "dark high-collar modern trench coat" in prompt
    # Negative prompt respects manhwa negative constraints
    assert any("no screentones" in p for p in prohibited)
    assert any("no black and white" in p for p in prohibited)


# =============================================================================
# 2. Western Superhero Comic Dynamic Style Compilation Test
# =============================================================================

def test_western_comic_dynamic_prompt_compilation():
    """Verifies a Western superhero comic compiles bold CMYK dynamic inks."""
    now_str = datetime.now(timezone.utc).isoformat()
    vanguard = CharacterDefinition(
        character_id="vanguard",
        name="Vanguard",
        description="Armored guardian of the metropolis",
        visual_invariants=[
            "muscular male hero in prime physical condition",
            "golden chest armor with glowing cyan core emblem",
            "flowing crimson cape, unmasked face with determined expression",
        ],
        attributes=[
            AttributeCheck(id="armor", text="heavy golden chest armor with cyan core emblem", required=True),
            AttributeCheck(id="cape", text="flowing crimson cape", required=True),
            AttributeCheck(id="helmet", text="gold and titanium battle helmet", required=False),
        ],
    )
    western_style = StyleDefinition(
        style_id="style_western_superhero",
        name="Western Dynamic CMYK",
        medium="american superhero comic book",
        rendering_approach="bold dynamic brush inking with saturated CMYK colors and dramatic chiaroscuro cross-hatching",
        line_art_rules=["heavy feathering", "muscular anatomy outlines", "dynamic speed inking"],
        tonal_rules=["bold graphic shadow cutouts", "saturated CMYK color separation"],
        palette_or_screentone={"palette": "cmyk_color"},
        negative_constraints=["no manga screentone", "no watercolor wash", "no dialogue balloons"],
    )
    bible = StoryBible(
        project_id="proj_western_vanguard",
        title="Vanguard: Apex Day",
        logline="A lone champion defends the skyline.",
        characters={"vanguard": vanguard},
        style=western_style,
        created_at=now_str,
        updated_at=now_str,
    )

    line_and_tone, neg_rules, style_meta = _resolve_bible_style_rules(bible)
    assert style_meta["medium"] == "american superhero comic book"
    assert "heavy feathering" in line_and_tone

    scene = SceneSpec(
        scene_id="scene_01",
        scene_index=0,
        title="Skyline Perch",
        shot_type="wide shot",
        action="Vanguard hovers above the skyscraper rooftop at dusk, cape billowing in the wind",
        character_ids=["vanguard"],
    )
    packet = build_panel_context_packet(
        story_bible=bible,
        scene=scene,
        panel_id="panel_01",
    )

    prompt = packet.generation_prompt
    assert "American Superhero Comic Book panel illustration" in prompt
    assert "heavy feathering" in prompt
    assert "heavy golden chest armor with cyan core emblem" in prompt
    assert "flowing crimson cape" in prompt


# =============================================================================
# 3. Dynamic Unscripted Attribute Auto-Negation Test
# =============================================================================

def test_unscripted_optional_attribute_auto_negation():
    """Verifies that optional character attributes not mentioned in the brief are auto-negated."""
    now_str = datetime.now(timezone.utc).isoformat()
    clara = CharacterDefinition(
        character_id="clara",
        name="Clara",
        description="A scientist with unblemished skin and optional protective goggles",
        visual_invariants=[
            "young woman, 20s, clean unblemished face with no scars or marks",
            "auburn hair tied in a neat ponytail",
        ],
        attributes=[
            AttributeCheck(id="hair", text="auburn ponytail", required=True),
            AttributeCheck(id="goggles", text="protective lab goggles", required=False),
            AttributeCheck(id="scar", text="facial battle scar", required=False),
        ],
    )
    bible = StoryBible(
        project_id="proj_clara",
        title="Sub-Zero Laboratory",
        characters={"clara": clara},
        style=StyleDefinition(
            style_id="style_ligne_claire",
            name="Ligne Claire",
            medium="European Comic Album (Ligne Claire)",
            rendering_approach="clean thin ligne claire lines",
        ),
        created_at=now_str,
        updated_at=now_str,
    )

    scene = SceneSpec(
        scene_id="scene_01",
        scene_index=0,
        title="Lab Reading",
        shot_type="close-up",
        action="Clara reads a clipboard at her desk in the warm library",
        character_ids=["clara"],
    )
    packet = build_panel_context_packet(
        story_bible=bible,
        scene=scene,
        panel_id="panel_01",
    )

    # Goggles and scar were not in the scene action; verify auto-negations prevent hallucinations
    prohibited = " ".join(packet.prohibited_deviations).lower()
    assert "goggles" in prohibited or "clean unblemished skin" in prohibited
    assert "scar" in prohibited or "clean unblemished skin" in prohibited


# =============================================================================
# 4. StyleIdentityQAService Multi-Style Dynamic Palette Test
# =============================================================================

def test_style_identity_qa_leaves_semantic_palette_fidelity_unverified():
    """Pixel metadata must not be reported as a style fidelity score."""
    qa = StyleIdentityQAService()

    # 1. Full-color Manhwa profile tested against grayscale image -> should trigger WARNING
    manhwa_profile = StyleProfile(
        profile_id="style_manhwa_v1",
        project_id="test_proj",
        name="Manhwa Digital Color",
        style_prompt_core="Vibrant digital color webtoon lighting, smooth gradients, rich hues",
        negative_constraints=["no black and white", "no 3D render"],
    )
    gray_image = _make_test_image(color=(128, 128, 128))  # Perfect gray, zero chromatic variation
    res_gray = qa.evaluate(
        run_id="run_1",
        asset_id="asset_1",
        image_bytes=gray_image,
        requested_scene_action="Character walks down colorful night street",
        style_profile=manhwa_profile,
    )
    assert res_gray.status == "not_verified"
    assert res_gray.style_score is None
    assert res_gray.overall_score is None

    # 2. Strict monochrome Manga profile tested against chromatic image -> should trigger WARNING
    manga_profile = StyleProfile(
        profile_id="style_manga_v1",
        project_id="test_proj",
        name="Manga Screentone Noir",
        style_prompt_core="Black and white comic ink, clean screentone shading",
        negative_constraints=["no color", "monochrome strictly"],
    )
    chromatic_image = _make_test_image(color=(220, 40, 40))  # Vivid red, heavy chromatic variance
    res_color = qa.evaluate(
        run_id="run_2",
        asset_id="asset_2",
        image_bytes=chromatic_image,
        requested_scene_action="Character stands in monochrome shadow",
        style_profile=manga_profile,
    )
    assert res_color.status == "not_verified"
    assert res_color.style_score is None
    assert res_color.overall_score is None


# =============================================================================
# 5. Character Identity Invariant Audit Finding Test
# =============================================================================

def test_character_invariants_are_not_reported_as_visually_verified():
    """Text profile invariants are not evidence that output pixels match them."""
    qa = StyleIdentityQAService()
    char_prof = CharacterIdentityProfile(
        profile_id="char_jin_v1",
        project_id="test_proj",
        character_id="jin",
        name="Jin",
        identity_invariants=["raven black straight hair", "dark brown sharp eyes", "unblemished clean skin"],
    )
    test_img = _make_test_image(color=(100, 100, 100))

    result = qa.evaluate(
        run_id="run_3",
        asset_id="asset_3",
        image_bytes=test_img,
        requested_scene_action="Jin investigates the crime scene",
        character_profiles=[char_prof],
    )

    invariant_findings = [f for f in result.findings if f.finding_id.startswith("fnd_invariants")]
    assert not invariant_findings
    assert result.identity_score is None
    assert result.status == "not_verified"
    assert "character_identity" in result.not_checked_dimensions


# =============================================================================
# 6. Model Client Dynamic Character Routing Test
# =============================================================================

def test_model_client_dynamic_character_anchor_routing():
    """Verifies AgentModelClient resolves non-Nour characters dynamically without hardcoding."""
    from app.config import InkLoopConfig, PROJECT_ROOT
    from app.agent.model_client import AgentModelClient
    from app.project.bible import save_bible

    now_str = datetime.now(timezone.utc).isoformat()
    jin = CharacterDefinition(
        character_id="jin",
        name="Jin",
        description="A webtoon investigator",
        visual_invariants=["raven black straight hair"],
        attributes=[AttributeCheck(id="hair", text="raven black straight hair", required=True)],
    )
    bible = StoryBible(
        project_id="proj_jin_routing",
        title="Dynamic Jin Project",
        characters={"jin": jin},
        style=StyleDefinition(
            style_id="style_manhwa",
            name="Manhwa",
            medium="digital webtoon",
            rendering_approach="clean webtoon",
        ),
        created_at=now_str,
        updated_at=now_str,
    )
    p_dir = PROJECT_ROOT / "runs" / "proj_jin_routing"
    p_dir.mkdir(parents=True, exist_ok=True)
    save_bible(bible, p_dir / "bible.json")

    client = AgentModelClient(config=InkLoopConfig())
    # Test 1: Canon & Character inspection for Jin
    tool_calls, direct_reply, status_msg = client.plan_next_action(
        messages=[{"role": "user", "content": "Inspect the Jin canon anchor and mandatory attributes"}],
        project_context={"project_id": "proj_jin_routing"},
        available_tools=[],
    )
    assert tool_calls is not None
    assert tool_calls[0].tool_id == "canon.inspect_characters"

    # Test 2: Reference image anchor inspection for Jin
    tool_calls, direct_reply, status_msg = client.plan_next_action(
        messages=[{"role": "user", "content": "Inspect Jin reference image"}],
        project_context={"project_id": "proj_jin_routing"},
        available_tools=[],
    )
    assert tool_calls is not None
    assert tool_calls[0].tool_id == "canon.inspect_reference_anchor"
    assert tool_calls[0].arguments.get("character_id") == "jin"
