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
    source_location="Meta AI Developer Documentation: Muse API v1.0 Reference, Image Edits Specification",
    what_it_establishes="Establishes API contracts for /v1/images/edits endpoint, reference multipart attachment, and spark-1.3 checklist parameters.",
    what_it_does_not_establish="Does not establish comic storytelling conventions, panel layout mechanics, or multi-panel pacing.",
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
    source_location="Chapters 2-4: Visual Iconography, Blood in the Gutter, and Panel Transitions",
    what_it_establishes="Establishes sequential art grammar, transition classifications, framing scale taxonomy, and reader closure theory.",
    what_it_does_not_establish="Does not establish generative model prompt weights, diffusion noise schedules, or digital inking algorithms.",
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
    supported_claim_ids=["clm_08_camera_angles", "clm_56_narrative_pacing", "clm_56_suspense_beat"],
    source_location="Chapters 1, 3, and 5: Framing, Perspective, and Encapsulation",
    what_it_establishes="Establishes visual narrative mechanics, dramatic camera angles, expressive posture, and panel encapsulation.",
    what_it_does_not_establish="Does not establish AI image synthesis behavior, automated rendering pipelines, or software interfaces.",
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
    source_location="runs/m0_visual/summary.json and benchmark candidate artifacts",
    what_it_establishes="Establishes that passing nour_reference.png to muse-image-1.0 /v1/images/edits reduces single-character facial drift from 100% to 0% across 6 diverse scenes.",
    what_it_does_not_establish="Does not establish multi-character co-presence consistency, full 14-element validation of Group 60, or arbitrary character references beyond Nour.",
    notes="Empirical trial: Arm A (unanchored) 0/6 pass rate vs Arm B (anchored with nour_reference.png) 6/6 pass rate evaluated with muse-spark-1.3 tri-state verifier."
)

SRC_COHN_2018 = SourceRecord(
    source_id="src_cohn_2018",
    title="Visual Language Theory and the Scientific Study of Comics",
    authors=["Neil Cohn"],
    publisher="Empirical Comics Research / Routledge",
    url_or_doi="https://visuallanguagelab.com/P/2018.ESiC.NC.pdf",
    publication_date="2018",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=[
        "clm_03_ecs_vs_ics_independence",
        "clm_03_blockage_navigation",
        "clm_04_role_geometry_independence",
        "clm_05_shape_container_vs_size",
        "clm_06_bleed_vs_splash",
        "clm_58_trim_vs_bleed_separation",
    ],
    source_location="Sections on External Compositional Structure (ECS), Internal Compositional Structure (ICS), Grids, and Boundary Treatments",
    what_it_establishes="Establishes structural independence between page layout (ECS) and internal panel composition (ICS), blockage path navigation, and multi-axis separation.",
    what_it_does_not_establish="Does not establish generative diffusion model prompt engineering or automated rendering pipelines.",
    notes="Foundational scientific analysis of comic visual language and page architecture."
)

SRC_COHN_2014 = SourceRecord(
    source_id="src_cohn_2014",
    title="The Architecture of Visual Narrative Comprehension: The Interaction of Narrative Structure and Page Layout",
    authors=["Neil Cohn", "Ryan Taylor", "Tom Holcomb"],
    publisher="Frontiers in Psychology",
    url_or_doi="https://doi.org/10.3389/fpsyg.2014.00680",
    publication_date="2014",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=["clm_03_blockage_navigation"],
    source_location="Eye-tracking and ERP empirical studies on comic page navigation",
    what_it_establishes="Establishes empirical reading path navigation under pure grids vs blockage and staggered tiered layouts.",
    what_it_does_not_establish="Does not establish digital comic scrolling physics or automated layout generators.",
    notes="Empirical cognitive science evidence on comic reading order preferences."
)

SRC_COHN_2013 = SourceRecord(
    source_id="src_cohn_2013",
    title="Visual Narrative Structure",
    authors=["Neil Cohn"],
    publisher="Cognitive Science",
    url_or_doi="https://doi.org/10.1111/cogs.12016",
    publication_date="2013",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=["clm_04_vng_grammar", "clm_53_asshuku_kaiho_pacing"],
    source_location="Visual Narrative Grammar (VNG) Formal Model",
    what_it_establishes="Establishes formal grammatical constituent structure of visual narrative: Establisher (E), Initial (I), Prolongation (L), Peak (P), and Release (R).",
    what_it_does_not_establish="Does not establish physical printing tolerances or font kerning metrics.",
    notes="Authoritative paper introducing Visual Narrative Grammar (VNG)."
)

SRC_COHN_2012 = SourceRecord(
    source_id="src_cohn_2012",
    title="Framing Attention in Japanese and American Comics: Cross-Cultural Differences in Attentional Structure",
    authors=["Neil Cohn"],
    publisher="Visual Cognition",
    url_or_doi="https://doi.org/10.1080/13506285.2012.701831",
    publication_date="2012",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=["clm_54_pov_immersion"],
    source_location="Corpus study of attentional framing across Japanese and Western comic panels",
    what_it_establishes="Establishes cross-cultural shot scale frequencies and attentional framing differences (subject vs scene vs POV framing).",
    what_it_does_not_establish="Does not establish individual artist drawing styles or uniform genre constraints.",
    notes="Empirical corpus study of manga vs American comic framing conventions."
)

SRC_NATSUME_2021 = SourceRecord(
    source_id="src_natsume_2021",
    title="The Functions of Panels (koma) in Manga",
    authors=["Natsume Fusanosuke", "Jon Holt (trans.)", "Teppei Fukuda (trans.)"],
    publisher="Electronic Journal of Contemporary Japanese Studies",
    url_or_doi="https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html",
    publication_date="2021",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=[
        "clm_01_manga_rtl_flow",
        "clm_05_shape_container_vs_size",
        "clm_53_asshuku_kaiho_pacing",
        "clm_56_panel_density_velocity",
        "clm_58_mihiraki_binding_fold",
    ],
    source_location="Sections on Koma Function, Asshuku (Compression) and Kaiho (Release), and Mi-hiraki (Two-Page Spreads)",
    what_it_establishes="Establishes manga panel grammar, compression and release pacing mechanics, two-page spread (mi-hiraki) dynamics, and top-right to bottom-left flow.",
    what_it_does_not_establish="Does not establish software data structures or SVG rasterization specifications.",
    notes="Classic manga scholarship on the functional semiotics of comic panels."
)

SRC_MOLOTIU_2013 = SourceRecord(
    source_id="src_molotiu_2013",
    title="List of Terms for Comics Studies",
    authors=["Andrei Molotiu"],
    publisher="Comics Forum",
    url_or_doi="https://comicsforum.org/2013/07/26/list-of-terms-for-comics-studies-by-andrei-molotiu/",
    publication_date="2013",
    evidence_class=EvidenceClass.SECONDARY_TECHNICAL,
    supported_claim_ids=[
        "clm_04_vng_grammar",
        "clm_04_silent_panel_pause",
        "clm_11_aspect_mood_transitions",
        "clm_53_flashback_visual_separation",
        "clm_54_shot_reverse_shot",
    ],
    source_location="Glossary of panel types, transitions, subjective perspectives, and montage",
    what_it_establishes="Establishes standardized terminology for montage panels, shot-reverse-shot dialogue editing, and narrative points of view in comics.",
    what_it_does_not_establish="Does not establish formal mathematical graph representations of panel layouts.",
    notes="Comprehensive academic glossary of comics analysis terminology."
)

SRC_COMIX_2022 = SourceRecord(
    source_id="src_comix_2022",
    title="Methodology on Inclusive Youth Work Through Comics",
    authors=["CO-MIX Consortium"],
    publisher="CO-MIX Erasmus+ Strategic Partnership",
    url_or_doi="https://www.mc-celje.si/f/docs/CO-MIX/COMIX_Manual_ENG.pdf",
    publication_date="2022",
    evidence_class=EvidenceClass.SECONDARY_TECHNICAL,
    supported_claim_ids=[
        "clm_03_diagonal_tension",
        "clm_05_shape_container_vs_size",
        "clm_05_panoramic_vista",
        "clm_05_tall_vertical_stature",
        "clm_06_bleed_vs_splash",
        "clm_06_figure_breaking_frame",
        "clm_56_panel_density_velocity",
    ],
    source_location="Chapter 3: The Architecture of Comic Pages, Panel Shapes, and Inset Storytelling",
    what_it_establishes="Establishes practical comic creation principles: irregular polygons, slanted cuts, pacing acceleration via small frames, and inset panels.",
    what_it_does_not_establish="Does not establish quantitative eye-tracking metrics or neural network architectures.",
    notes="Practical European pedagogical manual for sequential comic construction."
)

SRC_STEWART_2024 = SourceRecord(
    source_id="src_stewart_2024",
    title="Newspaper Comic Strips",
    authors=["Ronald Stewart"],
    publisher="The Cambridge Companion to Manga and Anime (Cambridge University Press)",
    url_or_doi="https://doi.org/10.1017/9781009118552.003",
    publication_date="2024",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=["clm_01_yonkoma_structure"],
    source_location="Historical evolution of 4-koma manga and structural conventions",
    what_it_establishes="Establishes the structural history, evolution, and narrative constraints of Japanese four-panel comic strips (yonkoma).",
    what_it_does_not_establish="Does not establish vertical webtoon infinite-scroll formats.",
    notes="Scholarly overview of 4-koma serial narrative conventions."
)

SRC_EMBASSY_JAPAN_YONKOMA = SourceRecord(
    source_id="src_embassy_japan_yonkoma",
    title="Yonkoma Manga Guidelines",
    authors=["Embassy of Japan in the UK"],
    publisher="Ministry of Foreign Affairs of Japan",
    url_or_doi="https://www.uk.emb-japan.go.jp/files/100069624.pdf",
    publication_date="2020",
    evidence_class=EvidenceClass.PRIMARY_PROVIDER_DOC,
    supported_claim_ids=["clm_01_yonkoma_structure"],
    source_location="Official competition guidelines on Yonkoma panel proportions and ki-shō-ten-ketsu progression",
    what_it_establishes="Establishes official specifications for 4-panel vertical manga format and classical ki-shō-ten-ketsu narrative structure.",
    what_it_does_not_establish="Does not establish Western multi-tier comic book formats.",
    notes="Official Japanese cultural agency specification for Yonkoma manga structure."
)

SRC_CAMBRIDGE_DIGITAL_COMICS = SourceRecord(
    source_id="src_cambridge_digital_comics",
    title="Innovations in Digital Comics",
    authors=["Cambridge University Press"],
    publisher="Cambridge University Press",
    url_or_doi="https://doi.org/10.1017/9781009366472",
    publication_date="2023",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=["clm_01_webtoon_scroll_timing"],
    source_location="Chapter on Webtoons and Continuous Long-Scroll Reading Ergonomics",
    what_it_establishes="Establishes digital canvas transformations: how vertical scroll distance and inter-panel blank intervals replace page turns.",
    what_it_does_not_establish="Does not establish physical print margin and bleed tolerances.",
    notes="Academic monograph analyzing long-scroll digital comic reading dynamics."
)

SRC_CHEN_2023 = SourceRecord(
    source_id="src_chen_2023",
    title="Flipping Vs. Scrolling in Digital Narratives: Reader Engagement and Reading Patterns in Comic Layouts",
    authors=["Ching-Shiuan Chen"],
    publisher="Proceedings of the Association for Information Science and Technology",
    url_or_doi="https://doi.org/10.1002/pra2.896",
    publication_date="2023",
    evidence_class=EvidenceClass.PEER_REVIEWED_RESEARCH,
    supported_claim_ids=["clm_01_webtoon_scroll_timing"],
    source_location="Comparative user study of page-turning vs vertical scrolling",
    what_it_establishes="Establishes empirical reader engagement differences between paginated page-turning and continuous vertical scrolling.",
    what_it_does_not_establish="Does not establish raster inking algorithms or text rendering engines.",
    notes="User study evaluating narrative comprehension across print vs webtoon scrolling."
)

SRC_COMICS_TERMINOLOGY_2018 = SourceRecord(
    source_id="src_comics_terminology_2018",
    title="Comics Terminology Reference Guide",
    authors=["HHS English Language Arts"],
    publisher="HHS Academic Curriculum",
    url_or_doi="https://hhsenglish.com/wp-content/uploads/2018/08/graphicnoveltermspdf-copy.pdf",
    publication_date="2018",
    evidence_class=EvidenceClass.SECONDARY_TECHNICAL,
    supported_claim_ids=["clm_06_bleed_vs_splash"],
    source_location="Visual diagrams and definitions for bleed, gutter, splash, and inset panels",
    what_it_establishes="Establishes pedagogical definitions distinguishing bleed, gutter, splash page, and inset panel frames.",
    what_it_does_not_establish="Does not establish experimental cognitive science hypotheses.",
    notes="Standard secondary technical curriculum guide for graphic novel terminology."
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
            # Group 60: EXPERIMENTALLY TESTED in M0 (ADR-007)
            # Downgraded from VALIDATED: M0 tested 1 recipe (solo portrait reference anchoring for Nour),
            # but Group 60 contains 14 canonical elements. Broad groups (>3 elements) require comprehensive
            # multi-element validation (>=2 passing recipes) before attaining group-level VALIDATED status.
            status = CoverageStatus.EXPERIMENTALLY_TESTED
            has_primary = True
            has_rules = True
            has_failure = True
            has_recipes = True
            has_exp = True
            is_val = False
            gaps = [
                "Multi-character co-presence identity drift rate under reference anchoring",
                "High-angle / low-angle camera perspective drift with front-view reference image",
                "Pose and lighting continuity validation across dynamic panel transitions",
                "Clothing and prop continuity validation across story timeline state deltas",
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
                    artistic_theory_vs_empirical="empirical_observation",
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
                    artistic_theory_vs_empirical="empirical_observation",
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
                    applies_to_character_ids=["nour"],
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
                    artistic_theory_vs_empirical="artistic_theory",
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
                    artistic_theory_vs_empirical="artistic_theory",
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

        elif num == 1:
            # Group 01: Comic Formats (RESEARCHED - Manga, 4-Koma, Webtoon)
            status = CoverageStatus.RESEARCHED
            has_primary = True  # SRC_EMBASSY_JAPAN_YONKOMA is PRIMARY_PROVIDER_DOC
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Empirical measurement of optimal webtoon vertical gutter height in pixels under varying screen DPIs",
                "Model prompt fidelity when generating sequential 4-koma panels in a single raster vs segmented tiles",
            ]
            sources = [
                SRC_STEWART_2024,
                SRC_EMBASSY_JAPAN_YONKOMA,
                SRC_CAMBRIDGE_DIGITAL_COMICS,
                SRC_CHEN_2023,
                SRC_NATSUME_2021,
            ]
            claims = [
                ResearchClaim(
                    claim_id="clm_01_yonkoma_structure",
                    taxonomy_group_id=group_id,
                    claim_text="Conventional 4-koma structure follows ki-shō-ten-ketsu: setup (ki), development (shō), twist/turn (ten), and conclusion (ketsu) across equal vertical panels.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_stewart_2024", "src_embassy_japan_yonkoma"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_01_manga_rtl_flow",
                    taxonomy_group_id=group_id,
                    claim_text="Traditional manga sequences from top-right to bottom-left, redirecting eye navigation and panel reading priority.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_natsume_2021"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_01_webtoon_scroll_timing",
                    taxonomy_group_id=group_id,
                    claim_text="Long-scroll vertical layouts replace page-turns with inter-panel whitespace intervals to govern reading cadence and dramatic reveals.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cambridge_digital_comics", "src_chen_2023"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_01_4koma_quad_beats",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For 4-koma format, compose scene beats in four sequential vertical segments following ki-shō-ten-ketsu progression.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["4-koma", "vertical strip", "yonkoma", "equal panels"],
                    conflicting_concepts=["irregular splash page", "horizontal western comic strip"],
                    failure_modes=["Unequal panel sizing disrupting 4-koma cadence", "Twist beat missing dramatic shift"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_embassy_japan_yonkoma", "src_stewart_2024"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_01_webtoon_whitespace_pacing",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For vertical-scroll formats, modulate vertical gutters with extended blank space to induce tension before reveals.",
                    confidence=ClaimConfidence.INFERENCE,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["webtoon", "vertical scroll", "infinite scroll"],
                    conflicting_concepts=["tight print gutters", "horizontal tiered grid"],
                    failure_modes=["Cluttered vertical gutter crowding dramatic reveals"],
                    priority=ConflictPriority.MEDIUM,
                    source_ids=["src_cambridge_digital_comics", "src_chen_2023"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 3:
            # Group 03: Page Structures (RESEARCHED - ECS vs ICS, Blockage, Diagonal Grid)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Reading eye-tracking verification on mixed diagonal-orthogonal hybrid pages",
                "Automated CSS/SVG gutter alignment precision when rendering non-rectangular blockage panels",
            ]
            sources = [SRC_COHN_2018, SRC_COHN_2014, SRC_COMIX_2022]
            claims = [
                ResearchClaim(
                    claim_id="clm_03_ecs_vs_ics_independence",
                    taxonomy_group_id=group_id,
                    claim_text="External Compositional Structure (page grid/layout) is structurally distinct and independent from Internal Compositional Structure (panel content).",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2018"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_03_blockage_navigation",
                    taxonomy_group_id=group_id,
                    claim_text="A tall panel beside a stack of smaller panels creates blockage, redirecting the reader's path downward before advancing horizontally.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2018", "src_cohn_2014"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="empirical_observation",
                ),
                ResearchClaim(
                    claim_id="clm_03_diagonal_tension",
                    taxonomy_group_id=group_id,
                    claim_text="Slanted boundaries and oblique cuts induce visual velocity and psychological instability in high-tempo action scenes.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_comix_2022"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_03_blockage_reading_order",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For blockage layouts, sequence internal panel action strictly along the vertical column before crossing tiers.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["blockage layout", "staggered tiers", "vertical strip"],
                    conflicting_concepts=["horizontal Z-path reading assumption"],
                    failure_modes=["Reader confusion from ambiguous Z-path vs vertical column priority"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_cohn_2014", "src_cohn_2018"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_03_action_diagonal_cuts",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Use slanted/oblique panel boundaries during high-tempo action sequences to convey velocity and instability.",
                    confidence=ClaimConfidence.INFERENCE,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["diagonal grid", "action scene", "dynamic combat"],
                    conflicting_concepts=["calm dialogue", "rigid nine-panel grid"],
                    failure_modes=["Awkwardly clipped character anatomy along extreme oblique angles"],
                    priority=ConflictPriority.MEDIUM,
                    source_ids=["src_comix_2022"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 4:
            # Group 04: Panel Types by Narrative Function (RESEARCHED - VNG Grammar, Peak, Silent)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Model prompt weighting for Prolongation (L) vs Initial (I) phase transitions",
                "Empirical reader comprehension test on inverted VNG structures (e.g. Peak preceding Establisher)",
            ]
            sources = [SRC_COHN_2013, SRC_COHN_2018, SRC_MOLOTIU_2013]
            claims = [
                ResearchClaim(
                    claim_id="clm_04_vng_grammar",
                    taxonomy_group_id=group_id,
                    claim_text="Panels fulfill formal Visual Narrative Grammar roles: Establisher (E), Initial (I), Prolongation (L), Peak (P), and Release (R).",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2013"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_04_role_geometry_independence",
                    taxonomy_group_id=group_id,
                    claim_text="Narrative function is independent of physical panel geometry; any shape or aspect ratio can fulfill an Establisher or Peak role.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2018"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_04_silent_panel_pause",
                    taxonomy_group_id=group_id,
                    claim_text="Panels devoid of text create a contemplative pause, compressing attention and decelerating subjective narrative time.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_molotiu_2013"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_04_vng_canonical_progression",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Sequence scene generation prompts according to Visual Narrative Grammar (E -> I -> L -> P -> R).",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["visual narrative grammar", "canonical pacing", "scene progression"],
                    conflicting_concepts=["unstructured random panel sequencing"],
                    failure_modes=["Premature climax without prior Establisher/Initial narrative setup"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_cohn_2013"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_04_peak_focal_emphasis",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For Peak / Impact panels, maximize contrast, dynamic pose, and clear focal anchoring on the decisive action.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["impact panel", "peak beat", "action climax", "high contrast"],
                    conflicting_concepts=["static eye-level medium shot", "low-contrast background blend"],
                    failure_modes=["Decisive impact obscured by cluttered ambient details"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_cohn_2013", "src_molotiu_2013"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_04_silent_panel_cleanliness",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.NEGATIVE_CONSTRAINT,
                    directive_text="For Silent / Pause beat panels, enforce strict negative prompts excluding text, speech balloons, and sound effects.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["silent panel", "ambient beat", "contemplative pause"],
                    conflicting_concepts=["onomatopoeia", "dialogue balloon", "shout caption"],
                    failure_modes=["Spurious text artifacts breaking contemplative silence"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_molotiu_2013"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 5:
            # Group 05: Panel Shapes (RESEARCHED - Panoramic, Tall Vertical, Container vs Size)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Model stability when generating for non-standard polygonal panel aspect ratios (>3:1 or <1:3)",
                "Subject repositioning during dynamic SVG polygon cropping",
            ]
            sources = [SRC_COMIX_2022, SRC_COHN_2018, SRC_NATSUME_2021]
            claims = [
                ResearchClaim(
                    claim_id="clm_05_shape_container_vs_size",
                    taxonomy_group_id=group_id,
                    claim_text="Panel shape serves as the spatial view container, while panel size modulates narrative pacing via compression and release.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2018", "src_natsume_2021", "src_comix_2022"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_05_panoramic_vista",
                    taxonomy_group_id=group_id,
                    claim_text="Panoramic ultra-wide panels emphasize vast spatial context, environmental scale, and horizontal movement.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_comix_2022"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_05_tall_vertical_stature",
                    taxonomy_group_id=group_id,
                    claim_text="Tall vertical rectangles emphasize physical height, falling/rising motion, and character full-figure stature.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_comix_2022", "src_natsume_2021"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_05_panoramic_horizon_rule",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For panoramic panels, anchor broad horizontal horizons along the lower third and expand environmental breadth.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["panoramic", "wide rectangle", "environmental vista", "horizontal expanse"],
                    conflicting_concepts=["tight vertical portrait crop", "extreme close-up"],
                    failure_modes=["Subject distorted by horizontal stretching", "Compressed vertical field of view"],
                    priority=ConflictPriority.MEDIUM,
                    source_ids=["src_comix_2022"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_05_tall_vertical_composition",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For tall vertical panels, compose subjects along the vertical axis (full-figure standing, upward glance, or descending action).",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["tall rectangle", "vertical panel", "full body shot", "towering scale"],
                    conflicting_concepts=["wide landscape vista", "horizontal panoramic composition"],
                    failure_modes=["Empty upper/lower dead space", "Head or feet clipped by vertical framing"],
                    priority=ConflictPriority.MEDIUM,
                    source_ids=["src_comix_2022", "src_natsume_2021"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 6:
            # Group 06: Panel Borders & Relationships (RESEARCHED - Bleed vs Splash, Frame Breaking, Inset)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Multi-layer alpha compositor support for frame-breaking elements",
                "Automated z-index resolution for overlapping inset panels",
            ]
            sources = [SRC_COHN_2018, SRC_COMIX_2022, SRC_COMICS_TERMINOLOGY_2018]
            claims = [
                ResearchClaim(
                    claim_id="clm_06_bleed_vs_splash",
                    taxonomy_group_id=group_id,
                    claim_text="Bleed describes artwork extending to or beyond page trim; splash describes page dominance. Smaller panels can also bleed.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2018", "src_comics_terminology_2018", "src_comix_2022"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_06_figure_breaking_frame",
                    taxonomy_group_id=group_id,
                    claim_text="Characters or objects extending beyond the panel border increase visual pop, perceived 3D depth, and narrative urgency.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_comix_2022"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_06_inset_hierarchy",
                    taxonomy_group_id=group_id,
                    claim_text="Inset panels require explicit parent containment, z-ordering, and contrast with parent artwork to prevent spatial ambiguity.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_comics_terminology_2018"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_06_figure_breaking_frame",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Allow character limbs, weapon tips, or motion streaks to extend beyond panel boundary stroke during dramatic impact beats.",
                    confidence=ClaimConfidence.INFERENCE,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["figure breaking frame", "dynamic combat", "impact panel", "3d depth pop"],
                    conflicting_concepts=["strict bordered grid", "contained boxed panel"],
                    failure_modes=["Severed limb artifact when rendered without layer alpha transparency"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_comix_2022"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_06_inset_contrast_rule",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="When nesting detail insert panels, ensure high tonal contrast and distinct border stroke between inset frame and underlying parent art.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["inset panel", "detail insert", "panel-within-panel"],
                    conflicting_concepts=["identical tonal background", "borderless inset over detailed background"],
                    failure_modes=["Inset panel bleeding into parent panel background, confusing reading order"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_comics_terminology_2018"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 11:
            # Group 11: Panel Transitions (RESEARCHED - Aspect-to-Aspect, Moment-to-Moment, Action Continuity)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Vector continuity validation across multi-panel prompt generation without shared seed",
                "Aspect-to-aspect semantic coherence benchmarking",
            ]
            sources = [SRC_MCCLOUD_1993, SRC_COHN_2018, SRC_MOLOTIU_2013]
            claims = [
                ResearchClaim(
                    claim_id="clm_11_aspect_mood_transitions",
                    taxonomy_group_id=group_id,
                    claim_text="Manga prominently uses aspect-to-aspect transitions to establish mood, atmosphere, and subjective place rather than continuous action.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_mccloud_1993", "src_molotiu_2013"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_11_moment_to_moment_pacing",
                    taxonomy_group_id=group_id,
                    claim_text="Moment-to-moment transitions decelerate subjective time during high-tension anticipation or emotional realization.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_mccloud_1993"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_11_aspect_mood_transitions",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="In atmospheric or contemplative manga scenes, employ aspect-to-aspect cuts across environment, lighting, and ambient objects.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["aspect-to-aspect", "atmospheric pacing", "environmental detail", "manga transition"],
                    conflicting_concepts=["rapid action-to-action combat", "talking head dialogue"],
                    failure_modes=["Disjointed random objects lacking atmospheric coherence with scene emotional tone"],
                    priority=ConflictPriority.MEDIUM,
                    source_ids=["src_mccloud_1993", "src_molotiu_2013"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_11_action_to_action_continuity",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For action sequences, maintain clear screen direction and vector continuity between consecutive action-to-action panels.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["action-to-action", "vector continuity", "screen direction", "dynamic combat"],
                    conflicting_concepts=["disorienting 180-degree camera flip", "disconnected scene-to-scene jump"],
                    failure_modes=["Inverted movement trajectory disorienting reader across consecutive action panels"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_mccloud_1993", "src_cohn_2018"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 53:
            # Group 53: Narrative Time & Chronology (RESEARCHED - Asshuku & Kaiho, Flashback)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Empirical measurement of perceived elapsed time per panel area",
                "Model prompt consistency when rendering flashback soft edges",
            ]
            sources = [SRC_NATSUME_2021, SRC_COHN_2013, SRC_MOLOTIU_2013]
            claims = [
                ResearchClaim(
                    claim_id="clm_53_asshuku_kaiho_pacing",
                    taxonomy_group_id=group_id,
                    claim_text="Manga modulates subjective time through panel size and density: compression (asshuku) accelerates pace, while large panels release tension (kaihō).",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_natsume_2021", "src_cohn_2013"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_53_flashback_visual_separation",
                    taxonomy_group_id=group_id,
                    claim_text="Flashbacks and memories require distinctive frame treatments (darkened gutters, dashed borders, desaturated tones) to demarcate non-linear time.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_molotiu_2013"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_53_compression_release_pacing",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Structure chapter sequences by alternating between tight multi-panel compression (asshuku) and large-panel release (kaihō).",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["asshuku", "kaiho", "compression and release", "manga temporal rhythm"],
                    conflicting_concepts=["monotonous uniform grid", "unvarying panel sizing"],
                    failure_modes=["Monotonous reading rhythm caused by unvarying panel dimensions across dramatic beats"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_natsume_2021"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_53_flashback_styling",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For memory/flashback sequences, inject soft vignette borders and desaturated monochrome styling directives.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["flashback", "memory", "past timeline", "desaturated tone", "vignette"],
                    conflicting_concepts=["high-saturation present timeline", "sharp modern screentone"],
                    failure_modes=["Reader confusing past memory with present real-time sequence"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_molotiu_2013"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 54:
            # Group 54: Narrative Point of View (RESEARCHED - POV Immersion, Shot-Reverse-Shot)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Model tendency to render observer head in POV prompts without explicit negative exclusion",
                "Consistency of gaze vector alignment in shot-reverse-shot pairs",
            ]
            sources = [SRC_COHN_2012, SRC_MOLOTIU_2013]
            claims = [
                ResearchClaim(
                    claim_id="clm_54_pov_immersion",
                    taxonomy_group_id=group_id,
                    claim_text="POV framing approximates character direct perception, creating psychological immersion and heightened reader empathy.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2012"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_54_shot_reverse_shot",
                    taxonomy_group_id=group_id,
                    claim_text="Conversational comic dialogue alternates speaker viewpoints without crossing the 180-degree axis to preserve spatial orientation.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_molotiu_2013"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_54_pov_framing_cues",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="For POV panels, exclude observing character's face; include partial foreground visual cues (hand, weapon, shoulder edge).",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["first-person pov", "subjective view", "foreground hand cue", "immersive camera"],
                    conflicting_concepts=["third-person wide shot showing observer face"],
                    failure_modes=["Model rendering the observing character in third-person despite POV directive"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_cohn_2012"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_54_dialogue_reverse_shot",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="In conversational dialogue, maintain consistent screen orientation when alternating over-the-shoulder reverse shots.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["shot-reverse-shot", "over-the-shoulder", "180-degree rule", "conversational dialogue"],
                    conflicting_concepts=["crossing the 180-degree axis", "inconsistent character facing direction"],
                    failure_modes=["Characters appearing to look in the same direction rather than at each other"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_molotiu_2013"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 56:
            # Group 56: Narrative Pacing (RESEARCHED - Panel Density Velocity, Suspense Beat)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Reading speed variance across high-density digital screens vs physical print",
                "Maximum panel density threshold before micro-panel comprehension deteriorates",
            ]
            sources = [SRC_NATSUME_2021, SRC_EISNER_1985, SRC_COMIX_2022]
            claims = [
                ResearchClaim(
                    claim_id="clm_56_panel_density_velocity",
                    taxonomy_group_id=group_id,
                    claim_text="Panel count per page inversely correlates with reading time: higher panel density accelerates perceived action velocity.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_natsume_2021", "src_comix_2022"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_56_suspense_beat",
                    taxonomy_group_id=group_id,
                    claim_text="A small, silent beat panel immediately preceding a Peak panel amplifies reader suspense and dramatic payoff.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_eisner_1985"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_56_suspense_silent_beat",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Place a small, silent beat panel immediately before an impact or reveal panel to build suspense.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["silent beat", "suspense pause", "pre-climax beat", "anticipation"],
                    conflicting_concepts=["simultaneous loud impact", "unbroken dense action dialogue"],
                    failure_modes=["Premature climax without suspense pause degrading dramatic impact"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_eisner_1985"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_56_action_panel_density",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Increase panel density with smaller, tightly cropped frames during high-intensity combat or rapid sequences.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["high panel density", "fast pacing", "rapid combat cuts", "tight cropping"],
                    conflicting_concepts=["single panoramic splash during fast exchanges", "sluggish wide framing"],
                    failure_modes=["High panel density resulting in cramped, unreadable micro-illustrations"],
                    priority=ConflictPriority.MEDIUM,
                    source_ids=["src_natsume_2021", "src_comix_2022"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        elif num == 58:
            # Group 58: Page Geometry & Layout Rules (RESEARCHED - Mi-hiraki Binding Fold, Bleed Separation)
            status = CoverageStatus.RESEARCHED
            has_primary = False
            has_rules = True
            has_failure = True
            has_recipes = False
            has_exp = False
            is_val = False
            gaps = [
                "Canvas pixel conversion accuracy across 300 DPI vs 600 DPI print standards",
                "Binding pinch variance for perfect bound vs saddle-stitch comic physical bindings",
            ]
            sources = [SRC_COHN_2018, SRC_NATSUME_2021, SRC_COMIX_2022]
            claims = [
                ResearchClaim(
                    claim_id="clm_58_mihiraki_binding_fold",
                    taxonomy_group_id=group_id,
                    claim_text="Double-page spreads (mi-hiraki) must account for physical binding gutter so critical art and faces are not swallowed by the fold.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_natsume_2021"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
                ResearchClaim(
                    claim_id="clm_58_trim_vs_bleed_separation",
                    taxonomy_group_id=group_id,
                    claim_text="Production bleed (physical 3mm canvas expansion) must be decoupled from artistic panel bleed.",
                    confidence=ClaimConfidence.FACT,
                    source_ids=["src_cohn_2018"],
                    model_applicability=["muse-image-1.0"],
                    verification_status="hypothesized",
                    artistic_theory_vs_empirical="artistic_theory",
                ),
            ]
            rules = [
                GenerationRule(
                    rule_id="rul_58_mihiraki_binding_safety",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="In double-page spreads (mi-hiraki), keep character faces, focal points, and dialogue outside the central 40px binding fold.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["double-page spread", "mi-hiraki", "binding fold safety", "two-page layout"],
                    conflicting_concepts=["centering vital facial features exactly across center spine"],
                    failure_modes=["Character face bisected or distorted by book binding gutter"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_natsume_2021"],
                    is_empirically_tested=False,
                ),
                GenerationRule(
                    rule_id="rul_58_trim_bleed_separation",
                    taxonomy_group_id=group_id,
                    rule_type=RuleType.POSITIVE_GUIDANCE,
                    directive_text="Ensure artwork flagged for bleed extends 3mm/36px beyond the trim line while keeping vital text inside the safe zone.",
                    confidence=ClaimConfidence.FACT,
                    applies_to_models=["muse-image-1.0"],
                    compatible_concepts=["bleed extension", "3mm print margin", "safe zone boundary"],
                    conflicting_concepts=["placing dialogue or focal art right against the raw canvas edge"],
                    failure_modes=["Essential art or text sliced off by physical trimming blades"],
                    priority=ConflictPriority.HIGH,
                    source_ids=["src_cohn_2018"],
                    is_empirically_tested=False,
                ),
            ]
            recipes = []

        else:
            # All other 44 groups: UNRESEARCHED baseline
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
