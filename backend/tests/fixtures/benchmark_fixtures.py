"""
Canonical M0 benchmark fixtures for Nour and the established six narrative scenes.
Used across orchestration unit, integration, and benchmark tests.
"""
from typing import List
from app.schemas import (
    StoryBible,
    StyleBible,
    CharacterSpec,
    AttributeCheck,
    ReferenceAsset,
    SceneSpec,
    BatchSpec,
)

CANONICAL_NOUR_SPEC = CharacterSpec(
    id="nour",
    attributes=[
        AttributeCheck(id="hair", text="short messy black hair, one white streak on the left", required=True),
        AttributeCheck(id="glasses", text="round glasses", required=True),
        AttributeCheck(id="jacket", text="oversized hooded jacket, lightning-bolt patch on chest", required=True),
        AttributeCheck(id="scar", text="small scar on right cheek", required=False),
    ]
)

CANONICAL_NOUR_REF_ASSET = ReferenceAsset(
    asset_id="nour_reference",
    file_path="runs/m0_visual/reference/nour_reference.png",
    content_hash="b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644",
    mime_type="image/png",
    description="Canonical front portrait of Nour with messy black hair, left white streak, round glasses, and lightning patch jacket."
)

CANONICAL_M0_STYLE = StyleBible(
    id="bw_ink_screentone",
    name="Black and White Ink & Screentone",
    medium="black and white comic ink",
    line_and_tone="black and white ink with screentone shading",
    palette="monochrome",
    negative_rules=[
        "no speech bubbles",
        "no dialogue text",
        "no watermarks",
        "no signatures",
        "no blurry artifacts"
    ],
    version="1.0.0"
)

CANONICAL_M0_STORY_BIBLE = StoryBible(
    bible_id="bible_nour_m0",
    version="1.0.0",
    project_id="inkloop",
    style=CANONICAL_M0_STYLE,
    characters={"nour": CANONICAL_NOUR_SPEC},
    character_assets={"nour": CANONICAL_NOUR_REF_ASSET},
    story_facts=[
        "Nour is an introverted archivist and mechanic in a quiet coastal city.",
        "Nour always wears round wireframe glasses and a hooded jacket with a lightning bolt patch."
    ]
)

CANONICAL_M0_SIX_SCENES: List[SceneSpec] = [
    SceneSpec(
        scene_id="scene_01",
        scene_index=0,
        title="Cafe Portrait",
        shot_type="medium close-up, front view",
        action="sitting at a small wooden cafe table with a warm cup of tea, looking directly towards the viewer",
        character_ids=["nour"],
        scene_state={"time_of_day": "morning", "location": "harbor_cafe"},
        previous_panel_summary=None
    ),
    SceneSpec(
        scene_id="scene_02",
        scene_index=1,
        title="Night Reading",
        shot_type="medium shot, night lighting",
        action="reading a hardcover book under the warm cone of light from an old streetlamp on a quiet stone path",
        character_ids=["nour"],
        scene_state={"time_of_day": "night", "location": "stone_path", "held_object": "hardcover_book"},
        previous_panel_id="panel_01",
        previous_panel_summary="Nour finished tea at the cafe and went for an evening walk."
    ),
    SceneSpec(
        scene_id="scene_03",
        scene_index=2,
        title="Library Corridor",
        shot_type="dynamic medium shot",
        action="standing in a quiet library book corridor holding a small brass key, looking towards the viewer with an alert curious expression",
        character_ids=["nour"],
        scene_state={"time_of_day": "night", "location": "library_hallway", "held_object": "brass_key"},
        previous_panel_id="panel_02",
        previous_panel_summary="Nour discovered an old brass key inside the library archives."
    ),
    SceneSpec(
        scene_id="scene_04",
        scene_index=3,
        title="Rain Walk",
        shot_type="three-quarter side shot",
        action="walking briskly through gentle evening rain holding a transparent umbrella, street reflections visible",
        character_ids=["nour"],
        scene_state={"weather": "rain", "held_object": "umbrella"},
        previous_panel_id="panel_03",
        previous_panel_summary="Nour left the library and stepped into the rainy evening streets."
    ),
    SceneSpec(
        scene_id="scene_05",
        scene_index=4,
        title="Workbench Inspection",
        shot_type="close-up shot",
        action="leaning closely over a wooden workbench, carefully inspecting a small brass mechanical gear with a magnifying lens",
        character_ids=["nour"],
        scene_state={"location": "workshop", "held_object": "magnifying_lens"},
        previous_panel_id="panel_04",
        previous_panel_summary="Nour retreated to the workshop workbench to examine the gear."
    ),
    SceneSpec(
        scene_id="scene_06",
        scene_index=5,
        title="Harbor Sunset",
        shot_type="wide medium shot, sunset backlight",
        action="sitting peacefully on a wooden bench at the edge of a harbor pier, looking out over calm water at dusk",
        character_ids=["nour"],
        scene_state={"time_of_day": "sunset", "location": "harbor_pier"},
        previous_panel_id="panel_05",
        previous_panel_summary="Nour concluded the mechanical repairs and sat by the harbor at dusk."
    ),
]

def create_m0_benchmark_batch_spec(
    batch_id: str = "batch_m0_benchmark",
    max_retries: int = 2,
    spend_cap_usd: float = 25.0,
    output_dir: str = "runs/m1_orchestrations"
) -> BatchSpec:
    """Creates a validated BatchSpec for the full six-panel benchmark."""
    return BatchSpec(
        batch_id=batch_id,
        project_id="inkloop",
        story_id="story_nour_m0",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=CANONICAL_M0_SIX_SCENES,
        model="muse-image-1.0",
        max_retries_per_panel=max_retries,
        spend_cap_usd=spend_cap_usd,
        output_dir=output_dir,
    )
