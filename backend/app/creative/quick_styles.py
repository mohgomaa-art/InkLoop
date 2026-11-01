"""Versioned, built-in visual style templates for the Agent quick-style picker."""
from __future__ import annotations

import json
from typing import Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


QUICK_STYLE_SCHEMA_VERSION = "inkloop.quick-style/1.0.0"
QUICK_STYLE_SAMPLE_PROMPT = (
    "One small chubby cream fluffy hooded creature with smooth pale oval face, "
    "black dot eyes, tiny curved smile and pink blush, standing in a relaxed pose, "
    "full body, on a plain pale background."
)


class QuickStyleTemplate(BaseModel):
    template_id: str
    version: str = QUICK_STYLE_SCHEMA_VERSION
    name: str
    description: str
    style_prompt_core: str
    variables: Dict[str, str]
    negative_constraints: List[str]
    sample_prompt: str = QUICK_STYLE_SAMPLE_PROMPT
    preview_asset_id: Optional[str] = None
    preview_url: Optional[str] = None
    preview_provider: Optional[str] = None
    preview_prompt: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


_STYLE_DATA = [
    {
        "template_id": "medical_editorial_gouache",
        "name": "Gouache",
        "description": "Matte, hand-painted editorial illustration with shaped brushwork.",
        "style_prompt_core": "Hand-painted digital gouache editorial illustration on a flat 2D picture plane; opaque matte strokes build form; broken color and selective lost-and-found edges; zero ink outlines; faces receive the clearest detail while backgrounds resolve into loose painted washes.",
        "variables": {
            "medium": "Hand-painted digital gouache editorial illustration",
            "linework": "No separate ink outlines; edges are paint meeting paint",
            "stroke_behavior": "Opaque shaped strokes, visible scumbling, and restrained dry-brush marks",
            "edge_quality": "Selective crisp and dissolving edges; no uniform contour",
            "shading": "Readable planar light and shaped cool shadows, not smooth airbrush",
            "palette": "Creator-selected palette with controlled warm accents and cool shadow color",
            "lighting": "One readable key light with softly painted separation light",
            "background_detail": "Progressively looser, flatter painted detail behind the subject",
            "texture": "Matte grain and slightly broken color inside large forms",
            "shape_language": "Specific, characterful silhouettes with natural asymmetry",
            "screentones_and_fx": "No screentone by default; restrained painterly effects only when requested",
        },
        "negative_constraints": ["plastic gloss", "beauty-filter symmetry", "uniform airbrush gradients", "unrequested lettering", "extra cast members", "unnamed clutter"],
    },
    {
        "template_id": "manga",
        "name": "Manga",
        "description": "Expressive Japanese comic rendering with intentional ink and screentone control.",
        "style_prompt_core": "Japanese manga page illustration with confident variable-weight ink contours, clear black-white value design, intentional screentone texture, expressive readable faces, and purposeful graphic shadows; use color only when the creator requests color.",
        "variables": {
            "medium": "Japanese manga illustration",
            "linework": "Variable-weight ink contours, clean tapered marks, and purposeful hatching",
            "stroke_behavior": "Confident brush-pen strokes with controlled speed accents",
            "edge_quality": "Crisp focal contours with selective broken marks in atmosphere",
            "shading": "Graphic black-white masses, crosshatch, and controlled screentone values",
            "palette": "Monochrome by default; obey an explicitly selected color palette",
            "lighting": "Dramatic graphic lighting with legible highlight and shadow shapes",
            "background_detail": "Clear environmental cues with detail subordinated to the focal subject",
            "texture": "Printed screentone and restrained paper grain",
            "shape_language": "Readable silhouettes and expressive action staging; adult human figures retain authentic human anatomy without dwarf distortion",
            "screentones_and_fx": "Use screentones, speed lines, or impact marks only when requested or narratively appropriate",
        },
        "negative_constraints": ["painterly gouache bleed", "photographic skin texture", "unrequested full-color gradients", "unrequested text", "extra cast members", "unrequested speed lines"],
    },
    {
        "template_id": "western_comic",
        "name": "Western Comic",
        "description": "Bold comic-book inks, readable spot blacks, and print-aware color.",
        "style_prompt_core": "Western comic-book illustration with decisive contour inking, expressive line weight, deliberate spot blacks, shaped crosshatching, and clear print-aware color separations; preserve readable silhouettes and strong focal contrast.",
        "variables": {
            "medium": "Western comic-book illustration",
            "linework": "Bold expressive contours with varied thickness and clean joins",
            "stroke_behavior": "Brush and nib marks with selective crosshatching",
            "edge_quality": "Firm readable contours; soften only distant atmosphere",
            "shading": "Designed shadow shapes and spot blacks, not photographic gradients",
            "palette": "Intentional limited or full comic palette with crisp color grouping",
            "lighting": "Directional dramatic light with clear highlight separation",
            "background_detail": "Structured setting detail that does not compete with the action",
            "texture": "Printed paper grain or halftone only when it supports the finish",
            "shape_language": "Strong iconic silhouettes and clear anatomy or creature forms",
            "screentones_and_fx": "Halftone, impact bursts, or motion marks only when requested",
        },
        "negative_constraints": ["soft watercolor wash", "uniform hairline contours", "muddy low-contrast color", "unrequested lettering", "extra cast members", "unrequested logos"],
    },
    {
        "template_id": "anime",
        "name": "Anime",
        "description": "Clean animated illustration with shaped cel shadows and expressive color.",
        "style_prompt_core": "Anime-inspired character illustration with clean intentional contours, simplified graphic forms, expressive eyes and gestures, and clearly separated cel-shadow shapes; use atmospheric paint or highlights only as supporting accents.",
        "variables": {
            "medium": "Anime-inspired digital illustration",
            "linework": "Clean tapered outlines with controlled thickness changes",
            "stroke_behavior": "Deliberate smooth digital marks with selective hair and fabric accents",
            "edge_quality": "Crisp subject edges with controlled soft light effects",
            "shading": "Simple cel-shadow planes with a small number of blended accents",
            "palette": "Harmonized expressive palette; maintain creator-specified colors",
            "lighting": "Readable key light with selective rim or glow accents",
            "background_detail": "Atmospheric setting detail balanced against the subject",
            "texture": "Mostly clean finish with subtle texture only when requested",
            "shape_language": "Stylized expressive proportions with stable creator-defined identity; adult human figures retain natural human body anatomy without dwarf caricature",
            "screentones_and_fx": "Glow, sparkles, or motion accents only when requested or scene-appropriate",
        },
        "negative_constraints": ["photorealistic rendering", "gouache dry-brush texture", "muddy blended shadows", "unrequested text", "extra cast members", "generic identity changes"],
    },
    {
        "template_id": "3d_stylized",
        "name": "3D",
        "description": "A designed 3D-rendered look with controlled materials and lighting.",
        "style_prompt_core": "Stylized three-dimensional digital render with coherent modeled forms, tactile material response, intentional key and fill lighting, and a designed color grade; keep geometry and surface treatment legible without adding unrequested realism.",
        "variables": {
            "medium": "Stylized 3D digital render",
            "linework": "No drawn outline unless explicitly requested; rely on silhouette and value separation",
            "stroke_behavior": "Modeled surfaces with controlled material transitions",
            "edge_quality": "Clean modeled contours with intentionally softened secondary edges",
            "shading": "Coherent form shading with readable key, fill, and contact shadows",
            "palette": "Material-aware palette with controlled saturation and color separation",
            "lighting": "Designed key-fill-rim setup appropriate to the scene",
            "background_detail": "Spatially coherent modeled setting; detail density follows creator direction",
            "texture": "Distinct restrained material textures, not a universal glossy finish",
            "shape_language": "Clear volume and silhouette with creator-directed proportions",
            "screentones_and_fx": "Digital light effects only when requested",
        },
        "negative_constraints": ["flat unmodeled vector fills", "ink-only rendering", "unrequested photographic realism", "plastic gloss on every material", "extra cast members", "unrequested text"],
    },
    {
        "template_id": "cartoon",
        "name": "Cartoon",
        "description": "Playful, readable shapes with flexible outlines and expressive posing.",
        "style_prompt_core": "Character-forward cartoon illustration with simplified appealing forms, clear silhouette design, expressive pose and face, and consistent graphic color; choose outline weight and shading to match the creator's request rather than assuming one cartoon subtype.",
        "variables": {
            "medium": "Character-focused cartoon illustration",
            "linework": "Optional clean contours with consistent, intentional weight",
            "stroke_behavior": "Simple confident strokes with selective expressive variation",
            "edge_quality": "Clear silhouette edges and uncluttered internal marks",
            "shading": "Flat color or simple shaped shadows as requested",
            "palette": "Clear coordinated palette with readable color blocks",
            "lighting": "Simple legible lighting that supports expression and form",
            "background_detail": "Reduced background detail unless the creator asks for a rich setting",
            "texture": "Clean base finish with optional subtle grain",
            "shape_language": "Exaggerated but coherent forms for creatures and expressive staging; retain specified creature anatomy; adult human figures retain natural authentic human proportions without caricature distortion",
            "screentones_and_fx": "Graphic accents used selectively and only as requested",
        },
        "negative_constraints": ["unrequested photorealism", "unrequested painterly texture", "overly complex surface detail", "extra cast members", "unrequested text", "anatomy not present in the character brief"],
    },
    {
        "template_id": "fantasy_illustration",
        "name": "Fantasy Illustration",
        "description": "Atmospheric fantasy art with material-aware detail and authored light.",
        "style_prompt_core": "Fantasy illustration with an authored sense of wonder, material-specific surface detail, deliberate focal hierarchy, and atmospheric light; keep magical motifs, creatures, costume, and world elements limited to what the creator describes.",
        "variables": {
            "medium": "Fantasy illustration in the requested paint or ink medium",
            "linework": "Medium-appropriate contours; emphasize silhouette over decorative noise",
            "stroke_behavior": "Layered marks shaped to the material and focal point",
            "edge_quality": "Focal edges clear, atmosphere edges selectively softened",
            "shading": "Volumetric or graphic shadow design matching the chosen medium",
            "palette": "World-specific palette with controlled luminous accents",
            "lighting": "Atmospheric key light; magical glow only when explicitly described",
            "background_detail": "World-building detail concentrated at story-relevant landmarks",
            "texture": "Material-specific stone, cloth, foliage, or magic effects as requested",
            "shape_language": "Distinct silhouettes; preserve nonhuman forms and stated anatomy",
            "screentones_and_fx": "Runes, particles, or spell effects only when present in the brief",
        },
        "negative_constraints": ["generic medieval clutter", "unrequested magic symbols", "unrequested glow", "photographic material mismatch", "extra cast members", "unrequested lettering"],
    },
    {
        "template_id": "stylized_illustration",
        "name": "Stylized Illustration",
        "description": "Flexible authored illustration with specific shape and color decisions.",
        "style_prompt_core": "Authored stylized illustration defined by deliberate shape simplification, controlled color relationships, readable focal hierarchy, and a consistent surface treatment; do not infer a genre, medium, or subject from the style name alone.",
        "variables": {
            "medium": "Creator-selected illustration medium, preserved literally",
            "linework": "Creator-defined presence, absence, and weight of contour lines",
            "stroke_behavior": "Consistent chosen mark-making with selective variation",
            "edge_quality": "Intentional balance of crisp, soft, and broken edges",
            "shading": "Consistent value grouping selected for the profile",
            "palette": "Creator-defined palette hierarchy and accent behavior",
            "lighting": "Scene-compatible light without adding unrequested mood",
            "background_detail": "Creator-selected detail level and focal separation",
            "texture": "Selected surface texture applied consistently and selectively",
            "shape_language": "Specific simplification and silhouette rules, not generic style labels",
            "screentones_and_fx": "No assumed effects; apply only defined profile effects",
        },
        "negative_constraints": ["generic style substitution", "contradictory media", "unrequested text", "unrequested effects", "extra cast members", "subject or layout copied from a style reference"],
    },
    {
        "template_id": "dark_gothic",
        "name": "Dark Gothic",
        "description": "Gothic atmosphere with intentional value control and ornate detail only where needed.",
        "style_prompt_core": "Dark gothic illustration with deliberate chiaroscuro, rich but controlled dark values, architectural or organic forms only when specified, and selective ornament; preserve readable subjects and do not add horror motifs merely because the style is gothic.",
        "variables": {
            "medium": "Gothic illustration in the creator-selected medium",
            "linework": "Expressive contours with selective engraving or hatch detail",
            "stroke_behavior": "Controlled marks supporting silhouette, fabric, and atmosphere",
            "edge_quality": "Strong focal edges against selective atmospheric loss",
            "shading": "Deep shaped shadows with legible subject separation",
            "palette": "Muted or saturated dark palette as directed, with restrained accents",
            "lighting": "Chiaroscuro or low-key lighting with a readable focal light source",
            "background_detail": "Ornament concentrated in story-relevant regions, not everywhere",
            "texture": "Subtle aged, etched, or painterly texture matching the chosen medium",
            "shape_language": "Distinct silhouettes with controlled verticality or angularity",
            "screentones_and_fx": "Mist, grain, or supernatural effects only when described",
        },
        "negative_constraints": ["unreadable crushed blacks", "unrequested gore", "unrequested occult symbols", "uniform ornament overload", "extra cast members", "unrequested text"],
    },
    {
        "template_id": "cute_pink_pop",
        "name": "Cute Pink Pop",
        "description": "Sweet playful pop illustration with lively pink accents, not a fixed character type.",
        "style_prompt_core": "Cute pop illustration with appealing readable shapes, bright coordinated color, expressive friendly details, and selective decorative accents; pink is an optional palette emphasis, not a requirement to alter the subject or add stereotyped props.",
        "variables": {
            "medium": "Cute pop illustration in a clean digital or print-inspired finish",
            "linework": "Smooth confident outlines with gentle weight changes",
            "stroke_behavior": "Clean graphic marks with small expressive accents",
            "edge_quality": "Crisp subject edges with a few soft decorative elements",
            "shading": "Simple bright cel shading with gentle highlights",
            "palette": "Pastel or vivid pink accents balanced with creator-selected colors",
            "lighting": "Soft upbeat light with tidy highlights and no forced glow",
            "background_detail": "Simple decorative background with clear subject separation",
            "texture": "Clean finish or light print grain when appropriate",
            "shape_language": "Rounded, friendly forms while preserving the actual subject silhouette",
            "screentones_and_fx": "Small sparkles or hearts only when wanted; never add them by default",
        },
        "negative_constraints": ["unrequested hearts, bows, or makeup", "overly sugary color cast", "photorealistic texture", "busy background clutter", "extra cast members", "unrequested text"],
    },
]


_PREVIEW_MANIFEST = Path(__file__).resolve().parents[3] / "frontend" / "public" / "quick-style-previews" / "manifest.json"
try:
    _preview_data = json.loads(_PREVIEW_MANIFEST.read_text(encoding="utf-8")).get("previews", {})
except (OSError, ValueError):
    _preview_data = {}

QUICK_STYLE_TEMPLATES: List[QuickStyleTemplate] = []
for _item in _STYLE_DATA:
    _preview = _preview_data.get(_item["template_id"], {})
    if _preview.get("status") == "generated":
        _item = {
            **_item,
            "preview_asset_id": _preview.get("asset_id"),
            "preview_url": _preview.get("preview_url"),
            "preview_provider": _preview.get("provider"),
            "preview_prompt": _preview.get("prompt"),
        }
    QUICK_STYLE_TEMPLATES.append(QuickStyleTemplate(**_item))
QUICK_STYLE_BY_ID: Dict[str, QuickStyleTemplate] = {
    item.template_id: item for item in QUICK_STYLE_TEMPLATES
}
