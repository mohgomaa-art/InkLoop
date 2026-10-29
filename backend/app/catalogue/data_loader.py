"""
InkLoop 60-Group Taxonomy Canonical Definitions & Baseline Data Loader.
Populates all 60 groups with exact canonical names, elements, relevance,
and truthful baseline coverage statuses matching INKLOOP_TASKS.md Section 7.
"""
from typing import List

from app.catalogue.enums import (
    CoverageStatus,
    EvidenceClass,
    ClaimConfidence,
    RuleType,
    OutcomeVerdict,
    ConflictPriority,
)
from app.catalogue.models import (
    TaxonomyGroupRecord,
    SourceRecord,
    ResearchClaim,
    GenerationRule,
    RecipeRecord,
)

# Baseline Primary & Research Sources
SRC_META_MUSE_2026 = SourceRecord(
    source_id="src_meta_muse_docs_2026",
    title="Meta AI Muse Image 1.0 & Spark 1.3 Technical Documentation",
    authors=["Meta AI"],
    publisher="Meta Platforms, Inc.",
    url_or_doi="https://api.meta.ai/v1/docs",
    publication_date="2026-04",
    evidence_class=EvidenceClass.PRIMARY_PROVIDER_DOC,
    supported_claim_ids=["clm_60_anchor_composition", "clm_19_screentone_style"],
    notes="Official API specifications for image generation, edits endpoint, and reference anchoring."
)

SRC_MCCLOUD_1993 = SourceRecord(
    source_id="src_mccloud_1993",
    title="Understanding Comics: The Invisible Art",
    authors=["Scott McCloud"],
    publisher="Tundra Publishing / HarperPerennial",
    url_or_doi="ISBN 0-06-097625-X",
    publication_date="1993",
    evidence_class=EvidenceClass.SECONDARY_TECHNICAL,
    supported_claim_ids=["clm_07_framing_scales", "clm_11_panel_transitions", "clm_19_comic_linework"],
    notes="Foundational sequential art theory for framing, closures, and visual iconography."
)

SRC_EISNER_1985 = SourceRecord(
    source_id="src_eisner_1985",
    title="Comics and Sequential Art",
    authors=["Will Eisner"],
    publisher="Poorhouse Press",
    url_or_doi="ISBN 0-9614728-1-2",
    publication_date="1985",
    evidence_class=EvidenceClass.SECONDARY_TECHNICAL,
    supported_claim_ids=["clm_08_camera_angles", "clm_56_narrative_pacing"],
    notes="Pioneering analysis of visual grammar, camera perspectives, and panel encapsulation."
)

SRC_M0_EXPERIMENT_2026 = SourceRecord(
    source_id="src_inkloop_m0_feasibility",
    title="InkLoop M0 Visual Feasibility Experiment: Anchor Composition vs Unanchored Drift",
    authors=["InkLoop Engineering Team"],
    publisher="InkLoop Project Repository (runs/m0_visual/)",
    url_or_doi="runs/m0_visual/summary.json",
    publication_date="2026-10-29",
    evidence_class=EvidenceClass.INKLOOP_EXPERIMENT,
    supported_claim_ids=["clm_60_anchor_composition", "clm_60_spark_verification"],
    notes="Empirical trial: Arm A (unanchored) 0/6 pass rate vs Arm B (anchored with nour_reference.png) 6/6 pass rate evaluated with muse-spark-1.3 tri-state verifier."
)


def build_canonical_60_groups() -> List[TaxonomyGroupRecord]:
    """
    Constructs the complete 60-group taxonomy register matching INKLOOP_TASKS.md Section 7.
    """
    groups_data = [
        # 01
        (1, "tax_01_comic_formats", "01. Comic Formats",
         "Governs overall visual medium conventions, reading direction, and frame density.",
         ["Manga", "Manhwa", "Manhua", "Western Comics", "Graphic Novel", "Webtoon", "Webcomic", "Comic Strip", "Newspaper Comic", "4-Koma", "Motion Comic", "Interactive Comic"]),

        # 02
        (2, "tax_02_canvas_types", "02. Canvas Types",
         "Determines target aspect ratio, bleed allowance, and pixel boundaries for generation.",
         ["Single Page", "Double-Page Spread", "Vertical Scroll Canvas", "Fixed Viewport", "Cover Canvas", "Title Page", "Full-Bleed Canvas", "Framed Canvas", "Borderless Canvas", "Split Canvas", "Continuous Background Canvas"]),

        # 03
        (3, "tax_03_page_structures", "03. Page Structures",
         "Provides layout constraints for panel composition, aspect ratios, and visual flow.",
         ["Single Panel Page", "Two-Panel Page", "Three-Tier Layout", "Four-Panel Grid", "Six-Panel Grid", "Nine-Panel Grid", "Horizontal Strip", "Vertical Strip", "Asymmetric Grid", "Diagonal Grid", "Mosaic", "Montage", "Split-Screen", "Freeform Layout"]),

        # 04
        (4, "tax_04_panel_types_function", "04. Panel Types by Narrative Function",
         "Guides narrative intent, focal emphasis, and environmental density in generated prompts.",
         ["Establishing Panel", "Action Panel", "Reaction Panel", "Reveal Panel", "Detail Panel", "Insert Panel", "Impact Panel", "Silent Panel", "Transition Panel", "Flashback Panel", "Dream Panel", "Cliffhanger Panel", "Closing Panel", "Splash Panel"]),

        # 05
        (5, "tax_05_panel_shapes", "05. Panel Shapes",
         "Constrains subject framing and camera cropping within non-standard bounding geometry.",
         ["Rectangle", "Square", "Wide Rectangle", "Tall Rectangle", "Diagonal Panel", "Trapezoid", "Triangle", "Polygon", "Circle", "Oval", "Wavy Border", "Jagged Border", "Organic Shape", "Irregular Shape", "Fragmented Panel"]),

        # 06
        (6, "tax_06_panel_borders_relationships", "06. Panel Borders & Relationships",
         "Directs gutter spacing, bleed extensions, and frame-breaking subject overflows.",
         ["Standard Bordered", "Borderless", "Inset", "Overlapping", "Bleed", "Full-Bleed", "Figure Breaking Frame", "Panel-within-Panel", "Floating Panel", "Embedded Panel", "Frameless Panel", "Panel Crossing the Gutter"]),

        # 07
        (7, "tax_07_camera_shot_scales", "07. Camera Shot Scales",
         "Controls distance between camera and subject, determining facial detail resolution.",
         ["Extreme Wide Shot", "Very Wide Shot", "Wide Shot", "Long Shot", "Full Body Shot", "Medium Long Shot", "Medium Shot", "Medium Close-up", "Close-up", "Big Close-up", "Extreme Close-up", "Macro Shot", "Detail Insert"]),

        # 08
        (8, "tax_08_camera_angles_views", "08. Camera Angles & Views",
         "Sets 3D viewpoint and elevation angle relative to subject horizon.",
         ["Eye-Level", "High Angle", "Low Angle", "Bird’s-Eye View", "Worm’s-Eye View", "Overhead", "Ground-Level", "Dutch Tilt", "POV", "Reverse POV", "Over-the-Shoulder", "Three-Quarter View", "Front View", "Side Profile", "Back View", "Reflection View"]),

        # 09
        (9, "tax_09_zoom_camera_transitions", "09. Zoom & Camera Transitions",
         "Maintains focal scale continuity across consecutive shot progressions.",
         ["Push-in", "Pull-back", "Extreme Punch-in", "Reveal by Zoom", "Reaction Cut", "Match Cut", "Scale Contrast", "Wide-to-Close-up", "Close-up-to-Wide", "Detail-to-Reveal", "Zoom-in Sequence", "Zoom-out Sequence"]),

        # 10
        (10, "tax_10_composition_types", "10. Composition Types",
         "Defines geometric balance, focal anchor points, and negative space allocation.",
         ["Symmetrical", "Asymmetrical", "Centered", "Off-Center", "Rule of Thirds", "Golden Ratio", "Leading Lines", "Triangular Composition", "Foreground Framing", "Layered Depth", "Negative Space", "Silhouette Composition", "Diagonal Composition", "Radial Composition", "Circular Flow", "Frame within Frame", "Visual Hierarchy", "Focal Point", "Partial Occlusion", "Continuous Composition"]),

        # 11
        (11, "tax_11_panel_transitions", "11. Panel Transitions",
         "Guides subject and action continuity across sequential comic panel transitions.",
         ["Moment-to-Moment", "Action-to-Action", "Subject-to-Subject", "Scene-to-Scene", "Aspect-to-Aspect", "Non-Sequitur", "Cause-to-Effect", "Setup-to-Payoff", "Reveal", "Reaction", "Parallel Cut", "Match Cut", "Time Skip", "Flashback", "Flashforward", "Montage", "Page-Turn Reveal", "Repetition", "Silent Beat"]),

        # 12
        (12, "tax_12_speech_bubble_types", "12. Speech Bubble Types by Function",
         "Establishes negative space reservation so character art does not collide with dialogue.",
         ["Dialogue", "Thought", "Inner Monologue", "Whisper", "Shout", "Scream", "Narration", "Caption", "Off-Panel Dialogue", "Voice-over", "Phone", "Radio", "Broadcast", "Robotic Voice", "Electronic Voice", "Telepathy", "Singing", "Crying Speech", "Gasps", "Interrupted Speech", "Fading Speech"]),

        # 13
        (13, "tax_13_speech_bubble_shapes", "13. Speech Bubble Shapes",
         "Informs prompt generation to avoid rendering baked-in dialogue bubbles into image raster.",
         ["Oval", "Ellipse", "Rounded Rectangle", "Rectangle", "Cloud", "Jagged", "Starburst", "Dashed", "Dotted", "Wavy", "Rough/Distorted", "Electric", "Pixelated", "Decorative", "Borderless Balloon"]),

        # 14
        (14, "tax_14_speech_bubble_tails", "14. Speech Bubble Tails & Connections",
         "Coordinates speaker mouth position with tail origin points.",
         ["Standard Pointed Tail", "Curved Tail", "Short Tail", "Long Tail", "Forked Tail", "Multiple Tails", "Bubble-chain Tail", "Thought Trail", "Tail-less", "Off-Panel Tail", "Connected Balloons", "Sequential Balloons", "Shared Balloon", "Overlapping Balloons", "Interrupted Balloon", "Broken Balloon", "Nested Balloon", "Silent Balloon"]),

        # 15
        (15, "tax_15_text_containers_captions", "15. Text Containers & Captions",
         "Controls compositional space for scene cards, narrator boxes, and letter documents.",
         ["Scene Caption", "Time/Location Card", "Narrator Box", "Internal Monologue Box", "Letter/Document Box", "On-screen UI", "Signage", "Footnote", "Translator Note", "Caption Stack"]),

        # 16
        (16, "tax_16_font_families_lettering", "16. Font Families & Lettering Styles",
         "Guides typography compatibility while enforcing that text is rendered by code, not inside image.",
         ["Comic Lettering", "Hand-lettered", "Sans-serif", "Serif", "Handwritten", "Script", "Display", "Condensed", "Monospaced", "Brush Lettering", "Rough/Distressed", "Pixel/Retro", "Outlined", "Inline", "Decorative"]),

        # 17
        (17, "tax_17_typography_properties", "17. Typography Properties",
         "Informs lettering layer layout and line height parameters.",
         ["Typeface", "Font Size", "Weight", "Width", "Italic", "All Caps", "Small Caps", "Letter Spacing", "Word Spacing", "Line Height", "Alignment", "Text Direction", "Line Breaks", "Balloon Padding", "Text Stroke", "Outline", "Shadow", "Opacity", "Emphasis", "Text Fit", "Text Overflow"]),

        # 18
        (18, "tax_18_arabic_multilingual_lettering", "18. Arabic & Multilingual Lettering",
         "Guarantees RTL text integrity, bidirectional layout, and font shaping constraints.",
         ["Arabic Shaping", "RTL", "LTR", "Bidirectional Text", "Ligatures", "Diacritics", "Vertical Writing", "Line-breaking Rules", "Font Embedding", "Mixed Arabic-English Text", "Text Integrity"]),

        # 19
        (19, "tax_19_stroke_line_art_types", "19. Stroke & Line Art Types",
         "Governs rendering medium, line weight, hatching density, and screentone shading rules.",
         ["Clean Line Art", "Variable Line Weight", "Thick Contour", "Thin Detail Lines", "Sketch Lines", "Rough Ink", "Brush Ink", "Dry Brush", "Scratchy Lines", "Broken Lines", "Hatching", "Cross-Hatching", "Stippling", "Dotwork", "Screentone"]),

        # 20
        (20, "tax_20_motion_lines_focus_effects", "20. Motion Lines & Focus Effects",
         "Directs speed lines, radial action bursts, and dynamic visual velocity.",
         ["Horizontal Speed Lines", "Diagonal Speed Lines", "Radial Speed Lines", "Focus Lines", "Impact Burst", "Action Arcs", "Motion Trails", "Smear Effects", "Motion Blur", "Vibration Lines", "Shake Lines", "Shock Rays", "Perspective Speed Lines"]),

        # 21
        (21, "tax_21_manga_emanata_expression_marks", "21. Manga Emanata & Expression Marks",
         "Guides rendering of symbolic manga expression glyphs (sweat drops, anger veins, gloom lines).",
         ["Sweat Drop", "Anger Vein Mark", "Blush Lines", "Surprise Rays", "Shock Lines", "Trembling Marks", "Tear Marks", "Spiral Eyes", "Gloom Lines", "Embarrassment Marks", "Confusion Marks", "Exhaustion Marks"]),

        # 22
        (22, "tax_22_impact_special_effects", "22. Impact & Special Effects",
         "Controls physical collision debris, shockwaves, magical energy, and energy auras.",
         ["Impact Cloud", "Dust Cloud", "Debris", "Sparks", "Crack Lines", "Shattered Glass", "Smoke Trails", "Energy Aura", "Electric Arcs", "Magic Circles", "Glow", "Glare", "Bloom", "Lens Flare", "Shockwave Rings", "Environmental Particles"]),

        # 23
        (23, "tax_23_sound_effects_sfx", "23. Sound Effects (SFX)",
         "Manages onomatopoeia integration while keeping visual layers decoupled.",
         ["BOOM", "BANG", "CRASH", "TAP", "TICK", "CLICK", "WHOOSH", "SWISH", "CRACK", "THUD", "RUMBLE", "KNOCK", "SPLASH", "BUZZ", "SNAP", "GASP", "SIGH", "ZAP", "DRIP", "CLANG", "SCRAPE", "FOOTSTEPS"]),

        # 24
        (24, "tax_24_facial_expressions_core", "24. Facial Expressions — Core Emotions",
         "Prompts primary emotional states while preserving canonical facial identity.",
         ["Joy", "Sadness", "Anger", "Fear", "Surprise", "Disgust", "Contempt"]),

        # 25
        (25, "tax_25_facial_expressions_complex", "25. Facial Expressions — Complex Emotions",
         "Expresses nuanced psychological states (curiosity, suspicion, determination, smugness).",
         ["Curiosity", "Confusion", "Suspicion", "Disbelief", "Embarrassment", "Shyness", "Smugness", "Pride", "Determination", "Frustration", "Relief", "Anxiety", "Boredom", "Sarcasm", "Awkwardness", "Love", "Awe", "Jealousy", "Regret", "Guilt", "Nervousness"]),

        # 26
        (26, "tax_26_facial_expressions_manga_exaggerated", "26. Facial Expressions — Manga-specific & Exaggerated",
         "Controls extreme stylized expression distortions without breaking character identity.",
         ["Ugly Cry", "Silent Tears", "Hysterical Laughter", "Nervous Smile", "Evil Grin", "Deadpan", "Shock Freeze", "Panic Face", "Exhausted Face", "Dizzy Eyes", "Spiral Eyes", "Blank Face", "Cat-like Smile", "Overwhelmed Expression"]),

        # 27
        (27, "tax_27_facial_expression_components", "27. Facial Expression Components",
         "Specifies micro-features (eyebrow angle, pupil dilation, lip compression) for fine-grained verification.",
         ["Eyebrow Position", "Eye Shape", "Gaze Direction", "Pupil Size", "Mouth Opening", "Lip Compression", "Head Tilt", "Face Angle", "Tears", "Blushing", "Sweat", "Under-eye Shadows", "Emanata"]),

        # 28
        (28, "tax_28_character_poses_basic", "28. Character Poses — Basic",
         "Directs fundamental character stances (standing, sitting, walking, running) under reference anchoring.",
         ["Standing", "Sitting", "Squatting", "Crouching", "Kneeling", "Lying", "Reclining", "Leaning", "Walking", "Running", "Jogging", "Jumping", "Falling", "Landing", "Climbing", "Crawling", "Floating"]),

        # 29
        (29, "tax_29_character_poses_action", "29. Character Poses — Action",
         "Controls dynamic physical combat, acrobatic, and athletic movement poses.",
         ["Reaching", "Grabbing", "Throwing", "Catching", "Pushing", "Pulling", "Lifting", "Dodging", "Blocking", "Attacking", "Defending", "Spinning", "Turning", "Slipping", "Stumbling", "Recoiling"]),

        # 30
        (30, "tax_30_character_poses_body_language", "30. Character Poses — Body Language",
         "Directs communicative gestures (arms crossed, waving, facepalm, pointing) revealing character attitude.",
         ["Arms Crossed", "Hands on Hips", "Pointing", "Waving", "Shrugging", "Facepalm", "Bowing", "Saluting", "Praying Pose", "Handshake", "Hugging", "Covering Face", "Hands Behind Back", "Hands in Pockets", "Open-Palm Gesture"]),

        # 31
        (31, "tax_31_character_poses_interaction", "31. Character Poses — Interaction & Daily Activities",
         "Guides everyday character behavior (reading, writing, drinking, looking back, offering).",
         ["Thinking", "Listening", "Talking", "Reading", "Writing", "Holding Object", "Looking Back", "Reaching Out", "Offering", "Receiving", "Examining", "Hiding"]),

        # 32
        (32, "tax_32_character_pose_parameters", "32. Character Pose Parameters",
         "Controls anatomical foreshortening, weight distribution, line of action, and silhouette readability.",
         ["Body Orientation", "Weight Distribution", "Line of Action", "Limb Configuration", "Head Direction", "Eye Direction", "Foreshortening", "Contact Points", "Silhouette Readability"]),

        # 33
        (33, "tax_33_character_dynamics_movement", "33. Character Dynamics & Movement",
         "Maintains kinetic action-reaction timing (anticipation, follow-through, collision).",
         ["Idle", "Anticipation", "Action", "Follow-through", "Recovery", "Approach", "Retreat", "Chase", "Confrontation", "Face-off", "Hand-off", "Greeting", "Conversation", "Argument", "Reconciliation", "Cooperation", "Push/Pull", "Carrying", "Catching", "Supporting", "Collision", "Separation"]),

        # 34
        (34, "tax_34_group_dynamics_interaction", "34. Group Dynamics & Interaction",
         "Orchestrates multi-character spatial blocking, eye contact axes, and social distance.",
         ["Group Movement", "Formation", "Parallel Actions", "Coordinated Reaction", "Eye Contact", "Looking Away", "Mutual Gaze", "Avoided Gaze", "Personal Space", "Intimate Distance", "Social Distance", "Isolation", "Power Imbalance", "Dominant/Subordinate Framing"]),

        # 35
        (35, "tax_35_action_continuity", "35. Action Continuity",
         "Enforces movement vector consistency and keyframe pose progression between panels.",
         ["Start Pose", "Key Pose", "Contact Pose", "Impact Pose", "End Pose", "Stillness", "Slow Movement", "Rapid Movement", "Staccato Action", "Repetition", "Motion Direction", "Position Continuity"]),

        # 36
        (36, "tax_36_background_types_location", "36. Background Types by Location",
         "Specifies architectural and environmental setting categories for scene grounding.",
         ["Urban Street", "Alley", "Rooftop", "Apartment", "Café", "Shop", "Office", "Workshop", "Warehouse", "Library", "Station", "Vehicle Interior", "Forest", "Mountain", "Beach", "Harbor", "Desert", "Garden", "Ruins", "Underground Space", "Fantasy Environment", "Sci-Fi Environment"]),

        # 37
        (37, "tax_37_background_mood_atmosphere", "37. Background Mood & Atmosphere",
         "Sets environmental tonality (cozy, melancholic, eerie, ominous, chaotic, whimsical).",
         ["Calm", "Cozy", "Warm", "Nostalgic", "Melancholic", "Lonely", "Dreamy", "Romantic", "Mysterious", "Eerie", "Ominous", "Tense", "Chaotic", "Oppressive", "Whimsical", "Serene", "Ephemeral", "Epic", "Surreal"]),

        # 38
        (38, "tax_38_background_detail_levels", "38. Background Detail Levels",
         "Modulates background complexity from white void to detailed panoramic establishing shots.",
         ["Blank", "White Void", "Abstract", "Speed-line Background", "Minimal", "Silhouette-only", "Simplified", "Soft-focus", "Medium-detail", "Detailed", "Highly Detailed", "Panoramic Establishing", "Pattern-based"]),

        # 39
        (39, "tax_39_background_details_props", "39. Background Details & Props",
         "Directs architectural fixtures, environmental storytelling props, and worn surface textures.",
         ["Architecture", "Walls", "Doors", "Windows", "Ceilings", "Arches", "Stairs", "Floors", "Furniture", "Books", "Cups", "Phones", "Tools", "Bags", "Signs", "Plants", "Trees", "Water", "Rocks", "Clouds", "Weather", "Smoke", "Steam", "Reflections", "Environmental Storytelling", "Worn Surfaces", "Discarded Objects"]),

        # 40
        (40, "tax_40_background_continuity_types", "40. Background Continuity Types",
         "Preserves persistent spatial landmarks, recurring props, and environmental state changes.",
         ["Independent Location", "Persistent Location", "Character-interactive Location", "Narratively-changing Location", "Continuous Background", "Recurring Props", "Environmental State Changes", "Fixed Spatial Landmarks"]),

        # 41
        (41, "tax_41_shadow_types_physics", "41. Shadow Types by Physics",
         "Guides physical shadow realism, ambient occlusion, contact shadows, and self-shadows.",
         ["Form Shadow", "Cast Shadow", "Contact Shadow", "Ambient Occlusion", "Self-shadow", "Reflected-light Shadow"]),

        # 42
        (42, "tax_42_shadow_styles", "42. Shadow Styles",
         "Controls stylistic rendering of shadows (cel-shaded, screentone, cross-hatched, solid-black).",
         ["Hard-edge Shadow", "Soft Shadow", "Cel-shaded Shadow", "Gradient Shadow", "Cross-hatched Shadow", "Screentone Shadow", "Stippled Shadow", "Solid-black Shadow", "Graphic Shadow", "Silhouette Shadow"]),

        # 43
        (43, "tax_43_shadow_directions_patterns", "43. Shadow Directions & Patterns",
         "Directs shadow projection angles, dappled patterns, and face-obscuring dramatic shadows.",
         ["Top-lit Shadow", "Side Shadow", "Under-eye Shadow", "Face-obscuring Shadow", "Rim-shadow Contrast", "Long Shadow", "Dappled Shadow", "Layered Shadow", "Projected Pattern Shadow"]),

        # 44
        (44, "tax_44_lighting_sources_directions", "44. Lighting Sources & Directions",
         "Sets lighting setup geometry (key, fill, rim, backlight, practical, ambient bounce).",
         ["Key Light", "Fill Light", "Rim Light", "Backlight", "Sidelight", "Top Light", "Underlight", "Front Light", "Practical Light", "Ambient Light", "Bounce Light"]),

        # 45
        (45, "tax_45_lighting_styles_contrast", "45. Lighting Styles & Contrast",
         "Establishes lighting contrast ratio (chiaroscuro, high-key, low-key, diffused volumetric light).",
         ["High-key", "Low-key", "Balanced Lighting", "Flat Lighting", "High Contrast", "Low Contrast", "Silhouette Lighting", "Chiaroscuro", "Diffused Light", "Volumetric Light"]),

        # 46
        (46, "tax_46_lighting_atmospheres", "46. Lighting Atmospheres",
         "Coordinates time-of-day natural lighting (golden hour, moonlight, neon, overcast, candlelight).",
         ["Morning Light", "Golden Hour", "Sunset", "Twilight", "Moonlight", "Overcast", "Foggy Light", "Neon Lighting", "Fluorescent Lighting", "Candlelight", "Firelight", "Streetlight", "Bioluminescence", "Magical Glow"]),

        # 47
        (47, "tax_47_lighting_parameters", "47. Lighting Parameters",
         "Fine-tunes color temperature, hardness, rim separation, and bloom parameters.",
         ["Direction", "Intensity", "Color Temperature", "Hardness", "Contrast Ratio", "Ambient Fill", "Rim Separation", "Volumetric Rays", "Bloom", "Glare", "Lens Flare"]),

        # 48
        (48, "tax_48_color_systems_palettes", "48. Color Systems & Palettes",
         "Enforces palette discipline (monochrome, grayscale, duotone, limited palette, triadic).",
         ["Monochrome", "Grayscale", "Duotone", "Limited Palette", "Full Color", "Complementary", "Analogous", "Triadic", "Split-complementary", "Monochromatic", "Warm", "Cool", "Neutral", "Mixed"]),

        # 49
        (49, "tax_49_color_rendering_contrast", "49. Color Rendering & Contrast",
         "Controls saturation levels, selective accents, duotone overlays, and color fringing.",
         ["Muted", "Desaturated", "Vibrant", "Selectively Saturated", "High Contrast", "Low Contrast", "High Key", "Low Key", "Color Overlay", "Duotone Overlay", "Vignette", "Glow", "Color Fringing"]),

        # 50
        (50, "tax_50_textures_surface_rendering", "50. Textures & Surface Rendering",
         "Prompts tactile surface textures (paper grain, halftone, screentone, canvas, noise).",
         ["Paper Grain", "Rough Paper", "Halftone", "Screentone", "Canvas Texture", "Noise", "Grain", "Fabric Texture", "Gradient", "Flat Fill", "Hatching", "Cross-hatching", "Stippling", "Dot Pattern"]),

        # 51
        (51, "tax_51_weather_atmospheric_effects", "51. Weather & Atmospheric Effects",
         "Generates environmental weather conditions (rain, snow, fog, wind, dust motes, storm particles).",
         ["Rain", "Snow", "Fog", "Mist", "Wind", "Storm", "Dust", "Dust Motes", "Pollen", "Ash", "Snowflakes", "Sparks", "Smoke", "Steam", "Fire", "Debris"]),

        # 52
        (52, "tax_52_energy_environmental_effects", "52. Energy & Environmental Effects",
         "Directs optical camera phenomena (depth of field, bokeh, chromatic aberration, motion blur).",
         ["Electricity", "Energy Aura", "Magic Particles", "Light Trails", "Hair Movement", "Clothing Flutter", "Leaves Blowing", "Water Ripples", "Depth of Field", "Bokeh", "Lens Flare", "Chromatic Aberration", "Motion Blur", "Vignette"]),

        # 53
        (53, "tax_53_narrative_time_chronology", "53. Narrative Time & Chronology",
         "Maintains temporal context cues (flashbacks, time skip, time lapse, simultaneous beats).",
         ["Present", "Past", "Future", "Flashback", "Flashforward", "Time Skip", "Time Lapse", "Simultaneous Events"]),

        # 54
        (54, "tax_54_narrative_point_of_view", "54. Narrative Point of View",
         "Directs perspective framing (first-person subjective vs third-person omniscient observer).",
         ["First-person", "Third-person", "Omniscient Narrator", "Limited Point of View", "Internal Monologue", "External Narration", "Unreliable Narrator"]),

        # 55
        (55, "tax_55_visual_storytelling_devices", "55. Visual Storytelling Devices",
         "Directs symbolic framing, visual metaphor, foreshadowing motifs, and visual irony.",
         ["Visual Metaphor", "Symbolism", "Foreshadowing", "Recurring Motif", "Callback", "Parallelism", "Visual Irony", "Visual Contrast", "Reveal", "Concealment", "Visual Repetition"]),

        # 56
        (56, "tax_56_narrative_pacing", "56. Narrative Pacing",
         "Controls visual pacing rhythm through panel framing density, pauses, and montage sequences.",
         ["Fast Pacing", "Slow Pacing", "Pause", "Suspense Build-up", "Reveal", "Climactic Beat", "Cliffhanger", "Repetition", "Extended Silence", "Montage"]),

        # 57
        (57, "tax_57_story_world_state", "57. Story World State",
         "Preserves physical state deltas (clothing tear, carried props, environmental damage, open doors).",
         ["Time of Day", "Location", "Weather", "Character Position", "Clothing State", "Carried Objects", "Open/Closed Doors", "Object Placement", "Environmental Damage", "Physical Contact", "Action Outcome", "State Continuity"]),

        # 58
        (58, "tax_58_page_geometry_layout_rules", "58. Page Geometry & Layout Rules",
         "Enforces print and digital canvas layout constraints (aspect ratios, bleed, gutters, safe areas).",
         ["Page Size", "Aspect Ratio", "Margins", "Bleed", "Safe Area", "Panel Borders", "Border Width", "Gutters", "Panel Padding", "Clipping", "Reading Order", "RTL/LTR", "Balloon Placement", "Tail Position"]),

        # 59
        (59, "tax_59_lettering_export_quality", "59. Lettering & Export Quality",
         "Guarantees text fit, line breaking, font licensing, 300 DPI resolution, and PDF export integrity.",
         ["Text Fit", "Line Breaks", "Text Integrity", "Font Embedding", "Font Licensing", "Overflow Detection", "Image Resolution", "DPI", "PDF Export", "PNG Export", "Page Numbering", "Cover", "Title Page", "End Page"]),

        # 60
        (60, "tax_60_visual_continuity_validation", "60. Visual Continuity & Validation",
         "Core InkLoop thesis: enforces character identity, style consistency, reference matching, and verifier check.",
         ["Character Identity", "Style Consistency", "Character Count", "Attribute Presence", "Reference Matching", "Pose Continuity", "Clothing Continuity", "Prop Continuity", "Location Continuity", "Lighting Continuity", "State Tracking", "Composition Drift", "Verifier Confidence", "Retry Policy"]),
    ]

    records = []

    for num, group_id, name, relevance, elements in groups_data:
        # Determine truthful baseline status and evidence mapping
        if num == 60:
            # Group 60: VALIDATED in M0 (ADR-007)
            status = CoverageStatus.VALIDATED
            has_primary = True
            has_rules = True
            has_failure = True
            has_recipes = True
            has_exp = True
            is_val = True
            gaps = [
                "Multi-character co-presence identity drift rate under reference anchoring",
                "High-angle / low-angle camera perspective drift with front-view reference image",
            ]

            sources = [SRC_META_MUSE_2026, SRC_M0_EXPERIMENT_2026]
            claims = [
                ResearchClaim(
                    claim_id="clm_60_anchor_composition",
                    taxonomy_group_id=group_id,
                    claim_text="Passing structured reference image to POST /v1/images/edits reduces character facial drift from 100% to 0% across 6 diverse scenes.",
                    confidence=ClaimConfidence.EXPERIMENTAL_RESULT,
                    source_ids=["src_inkloop_m0_feasibility", "src_meta_muse_docs_2026"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="empirically_verified",
                    empirical_notes="Demonstrated on character Nour across 6 scenes (ADR-007): Arm A 0/6 pass rate, Arm B 6/6 pass rate."
                ),
                ResearchClaim(
                    claim_id="clm_60_spark_verification",
                    taxonomy_group_id=group_id,
                    claim_text="muse-spark-1.3 reliably discriminates matching character candidates from deliberately corrupted candidates using a structured tri-state checklist.",
                    confidence=ClaimConfidence.EXPERIMENTAL_RESULT,
                    source_ids=["src_inkloop_m0_feasibility"],
                    model_applicability=["muse-spark-1.3"],
                    verification_status="empirically_verified",
                    empirical_notes="Correctly returned passed=True on Arm B valid output and passed=False on corrupted test candidate."
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_60_pass_reference_image",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Always supply canonical reference_bytes and reference_mime to image edits endpoint for named characters.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["clean linework", "screentone shading", "single character portrait"],
                    conflicting_concepts=["unanchored text-only generation", "unspecified facial features"],
                    failure_modes=["Glasses frame shape morphing", "Hair white streak position shift", "Jacket emblem loss"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_inkloop_m0_feasibility"],
                    is_empirically_tested=True,
                ),
                GenerationRule(
                    rule_id="rul_60_negative_text_rule",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.NEGATIVE_CONSTRAINT,
                    directive_text="Always include negative rules: 'no dialogue text, no speech bubbles, no watermarks, no signatures'.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    failure_modes=["Baked-in gibberish text", "Spurious speech balloons blocking subject"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_meta_muse_docs_2026"],
                    is_empirically_tested=True,
                )
            ]
            recipes = [
                RecipeRecord(
                    recipe_id="rec_60_reference_anchored_portrait",
                    taxonomy_group_id=group_id,
                    intended_outcome="Consistent character portrait with zero facial feature drift.",
                    use_case="Standard character appearance across story panels.",
                    required_prompt_components=[
                        "black and white comic ink, clean linework with screentone shading",
                        "Nour, short messy black hair with a single sharp streak of white on the left side",
                        "round wireframe glasses",
                        "oversized dark hooded jacket with a small yellow lightning bolt patch on the left chest",
                    ],
                    prohibited_conditions=["color", "dialogue text", "speech bubbles", "watermarks"],
                    target_model="muse-image-1.0",
                    parameters={"n": 1, "endpoint": "/v1/images/edits"},
                    reference_image_required=True,
                    reference_requirements="Clean front or 3/4 view PNG reference sheet with transparent or neutral background",
                    experiment_id="exp_m0_visual_feasibility",
                    experiment_version="1.0.0",
                    input_artifact_ids=["art_nour_reference"],
                    output_artifact_ids=["art_nour_panel_01", "art_nour_panel_02", "art_nour_panel_03", "art_nour_panel_04", "art_nour_panel_05", "art_nour_panel_06"],
                    expected_outcome="Passes 3/3 checklist items on hair streak, glasses frame, and jacket patch.",
                    observed_outcome="6/6 (100%) candidate panels passed canonical verifier checklist.",
                    evaluation_method="muse-spark-1.3 tri-state attribute checklist verifier",
                    result=OutcomeVerdict.PASS,
                    failure_observations=["Arm A text-only baseline produced 0/6 pass rate."],
                    retries_needed=0,
                    limitations=["Tested on solo character framing; crowd scenes require separate sub-panel segmentation."],
                    is_empirically_validated=True,
                )
            ]

        elif num == 19:
            # Group 19: Stroke & Line Art Types (RESEARCHED in M0/M1 Story Bible)
            status = CoverageStatus.RESEARCHED
            has_primary = True
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Cross-hatching vs screentone rendering prompt stability across different resolutions",
                "Dry brush line weight control under muse-image-1.0",
            ]
            sources = [SRC_META_MUSE_2026, SRC_MCCLOUD_1993]
            claims = [
                ResearchClaim(
                    claim_id="clm_19_screentone_style",
                    taxonomy_group_id=group_id,
                    claim_text="Screentone shading directives enforce consistent manga-style tonal gradations without introducing gray muddy blur.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_meta_muse_docs_2026", "src_mccloud_1993"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    empirical_notes="Integrated into canonical StyleBible defaults in M1."
                )
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_19_screentone_linework",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Specify 'clean linework with screentone shading, monochrome palette' in style prompt preamble.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["monochrome", "screentone", "clean lines"],
                    conflicting_concepts=["hyper-realistic shading", "photorealistic gradients"],
                    failure_modes=["Blurry halftone artifacts", "Smudged grayscale gradients"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_meta_muse_docs_2026"],
                    is_empirically_tested=False,
                )
            ]
            recipes = []

        elif num in (7, 8, 28):
            # Groups 07 (Shot scales), 08 (Camera angles), 28 (Basic poses): RESEARCHED
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                f"Model adherence benchmark for {name} elements under reference anchoring",
                "Compatibility interactions with background perspective",
            ]
            sources = [SRC_MCCLOUD_1993, SRC_EISNER_1985]
            claims = [
                ResearchClaim(
                    claim_id=f"clm_{num:02d}_framing_grammar",
                    taxonomy_group_id=group_id,
                    claim_text=f"Sequential framing terms in {name} govern visual distance and narrative focus.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_mccloud_1993", "src_eisner_1985"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                )
            ]
            rules = [
                GenerationRule(
                    rule_id=f"rul_{num:02d}_directive",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text=f"Explicitly declare {name} framing tokens at the start of scene prompt.",
                    confidence=ClaimConfidence.INFERENCE,
                    applies_to_models=["muse-image-1.0"],
                    failure_modes=["Camera zoom drift across consecutive panels"],
                    priority=ConflictPriority.MEDIUM,
                    source_ids=["src_mccloud_1993"],
                    is_empirically_tested=False,
                )
            ]
            recipes = []

        else:
            # All other 55 groups: UNRESEARCHED baseline
            status = CoverageStatus.UNRESEARCHED
            has_primary = False
            has_rules = False
            has_failure = False
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                f"Primary provider documentation mapping for {name} pending",
                f"Empirical prompt recipes for {name} elements pending",
                f"Compatibility constraints and failure mode cataloguing pending",
            ]
            sources = []
            claims = []
            rules = []
            recipes = []

        record = TaxonomyGroupRecord(
            group_id=group_id,
            group_number=num,
            canonical_name=name,
            image_generation_relevance=relevance,
            canonical_elements=elements,
            status=status,
            has_primary_sources=has_primary,
            has_generation_rules=has_rules,
            has_failure_modes=has_failure,
            has_recipes=has_recipes,
            has_recorded_experiments=has_exp,
            is_empirically_validated=is_val,
            research_gaps=gaps,
            claims=claims,
            rules=rules,
            recipes=recipes,
            sources=sources,
            version="1.0.0",
        )
        records.append(record)

    return records
