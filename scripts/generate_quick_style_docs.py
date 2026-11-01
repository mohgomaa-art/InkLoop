"""Generate the ten full Markdown style variants from the locked source schema."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.creative.quick_styles import QUICK_STYLE_TEMPLATES  # noqa: E402


OUT_DIR = ROOT / "templates" / "quick_styles"
MASTER = OUT_DIR / "master_schema.md"


def replace_fenced_block(text: str, after: str, content: str, before: str | None = None) -> str:
    start = text.index(after)
    fence_start = text.index("```", start)
    fence_end = text.index("```", fence_start + 3)
    if before and text.index(before, start) < fence_end:
        raise ValueError(f"Could not locate fenced block before {before!r}")
    return text[: fence_start + 3] + "\n" + content.rstrip() + "\n" + text[fence_end:]


def slot_prompt(template) -> str:
    v = template.variables
    return f"""{v['medium']}. {v['stroke_behavior']}. {v['edge_quality']}. {v['texture']}.

STYLE CORE: {template.style_prompt_core}
MEDIUM: {v['medium']}
LINEWORK: {v['linework']}
STROKE: {v['stroke_behavior']}
SHADING: {v['shading']}
PALETTE: {v['palette']}
LIGHTING: {v['lighting']}
BACKGROUND: {v['background_detail']}
SHAPE LANGUAGE: {v['shape_language']}
EFFECTS: {v['screentones_and_fx']}

WORLD: {{creator-selected environment and world details}}. Render its surfaces and atmosphere using the pinned profile variables; do not invent setting-specific props.
FRAME: {{creator-selected framing}}; {{creator-selected aspect ratio}}; keep focal hierarchy clear and leave text-safe space only when requested.
CAST: exactly {{N}} requested entities, no incidental people, creatures, or implied human anatomy.
SCENE: {{what happens and where exactly; concrete nouns and verbs only}}
SUBJECTS: {{identity, actual form, pose, mutable state, emotion, and gaze for each selected entity; concrete nouns and verbs only; no style instructions}}
PROPS: only these — {{named props and placement, max 3}}. Do not add unnamed objects.

Closing anchor: {template.style_prompt_core}"""


def negative_prompt(template) -> str:
    return ", ".join(template.negative_constraints)


def compact_prompt(template) -> str:
    v = template.variables
    return (
        f"{template.style_prompt_core}; {v['linework']}; {v['shading']}; "
        f"{v['palette']}; {v['lighting']}; {v['texture']}; "
        "exactly {N} requested subjects only; {SCENE}; {SUBJECTS}; {PROPS}; "
        "creator-selected framing {FRAME}; creator-selected aspect ratio {ASPECT_RATIO}. "
        "Send the separate negative constraints only through a provider-supported negative field."
    )


def fidelity_checks(template) -> str:
    return "\n".join(
        f"- **{key.replace('_', ' ').title()} check:** fail if the output contradicts `{value}`; pass when that rule is visible where applicable."
        for key, value in template.variables.items()
    ) + "\n- **Subject and count check:** exactly the requested subjects and named props; no unintended additions."


def preflight(template) -> str:
    return "\n".join([
        "- [ ] All required style variables are present and sourced from this profile version.",
        "- [ ] Keep negative constraints separate in the profile contract; map them only to provider-supported controls.",
        "- [ ] Scene, subject, cast, props, framing, and aspect ratio come from the creator request or explicit defaults.",
        "- [ ] Style vocabulary stays in the style profile, not the scene or subject slots.",
        "- [ ] The negative field does not contain this profile's defining medium or a pinned positive value.",
        "- [ ] Cast and prop counts are explicit and do not include open-world exceptions.",
        "- [ ] Preview image provenance names the provider, prompt, asset ID, and template version.",
        "- [ ] Generated examples are examples; do not promise deterministic or exact style reproduction.",
    ])


def slot_rules() -> str:
    return "\n".join([
        "- Slots contain only concrete scene facts, entities, actions, counts, and named objects. Put all rendering language in the profile variables.",
        "- Entity slots are open-form: humans, animals, monsters, object-like beings, abstract forms, and hybrids are valid. Never infer human anatomy that the creator did not specify.",
        "- State an exact subject count and list only requested props; do not permit vague extras or background-figure exceptions.",
        "- Describe a specific emotion, pose, action, and gaze only when relevant; never let temporary state rewrite canonical identity.",
        "- Framing and aspect ratio come from the creator or active Canvas target, not from this style preset.",
        "- Do not copy reference-image subjects, objects, text, or layout into style rules.",
    ])


def troubleshooting(template) -> str:
    v = template.variables
    return "\n".join([
        "| Symptom | Fix |",
        "|---|---|",
        f"| Style drifts toward another medium | Recheck the positive medium and linework variables: {v['medium']}; {v['linework']}. Remove conflicting positive context. |",
        f"| Surface treatment looks wrong | Adjust only the stroke, edge, shading, and texture variables: {v['stroke_behavior']}; {v['edge_quality']}; {v['shading']}; {v['texture']}. |",
        f"| Palette or lighting drifts | Edit the selected profile palette and lighting fields: {v['palette']}; {v['lighting']}. |",
        "| Subject, framing, or layout changed unexpectedly | Keep those details in the request-specific slots; remove subject or layout details from style references and style prose. |",
        "| Preview differs between reruns | Treat generations as nondeterministic; compare the actual output and record the provider and prompt. Do not claim a fixed seed unless supported. |",
    ])


def validate_style_slots(template, rendered: str) -> None:
    """Keep style vocabulary out of request-owned scene and subject slots."""
    for slot in ("SCENE", "SUBJECTS"):
        match = re.search(rf"^{slot}: \{{([^}}]+)\}}$", rendered, flags=re.MULTILINE)
        if not match:
            raise ValueError(f"Missing or malformed {slot} slot in {template.template_id}")
        slot_text = match.group(1).casefold()
        for style_label in (template.name, template.template_id.replace("_", " ")):
            if style_label.casefold() in slot_text:
                raise ValueError(f"Style label leaked into {slot} slot in {template.template_id}")
    negative = " ".join(template.negative_constraints).casefold()
    if template.name.casefold() in negative:
        raise ValueError(f"Negative constraints ban the selected style in {template.template_id}")


def render(template) -> str:
    text = MASTER.read_text(encoding="utf-8")
    text = text.replace(
        "# Medical Editorial Illustration — AI Generation Schema",
        f"# {template.name} — Quick Style Schema",
        1,
    )
    text = text.replace(
        "*Production tool for AI-generated manga panels (Midjourney / SDXL / DALL-E / GPT-4o)*",
        "*Versioned InkLoop Agent quick style; provider-neutral values are mapped only to controls the configured provider supports.*",
        1,
    )
    metadata = (
        f"\n> **Active quick style:** `{template.template_id}` · **Template version:** `{template.version}`  \n"
        f"> **Purpose:** {template.description}  \n"
        "> This full copy preserves the master schema's section order and slot mechanics. The active style-specific production blocks below supersede the source example values. The medical clinic story, names, and props in the source are historical examples, not default scene content.  \n"
        "> **Style variables:** " + "; ".join(f"`{key}`: {value}" for key, value in template.variables.items()) + "\n"
    )
    title_end = text.index("\n", text.index("# " + template.name))
    subtitle_end = text.index("\n", title_end + 1)
    text = text[:subtitle_end] + metadata + text[subtitle_end:]

    # Keep every original section heading in place while making its active prompt,
    # negative field, example, checks, and repair instructions specific to this style.
    text = replace_fenced_block(text, "Locked blocks are untouchable.", slot_prompt(template), "### Negative Field")
    text = replace_fenced_block(text, "### Negative Field", negative_prompt(template), "**This is now the single source")
    text = text.replace(
        "This goes into the tool's actual negative-prompt input (Midjourney `--no`, SDXL/Flux negative prompt box, DALL-E/GPT-4o as an explicit \"avoid\" instruction appended separately). Keeping it out of the body matters mechanically: the model weighs \"build this\" and \"avoid this\" as separate signals when they're in separate fields, rather than competing for attention inside one token stream the way inline \"NOT anime, NOT 3D\" phrasing does.",
        "Keep this as a separate style-profile field. The current Meta adapter maps it to an `Avoid:` clause in the text prompt because its request has no native negative-prompt parameter; this is not a separate provider-side negative channel.",
        1,
    )
    text = replace_fenced_block(text, "### Compact Variant", compact_prompt(template), "### 10-Second Fidelity Test")
    text = replace_fenced_block(text, "### Filled Example", template.sample_prompt, "### Compact Variant")

    slot_start = text.index("### Slot Rules")
    slot_end = text.index("### Filled Example", slot_start)
    text = text[:slot_start] + "### Slot Rules\n\n" + slot_rules() + "\n\n" + text[slot_end:]

    fidelity_start = text.index("### 10-Second Fidelity Test")
    fidelity_end = text.index("### Pre-Flight Checklist", fidelity_start)
    text = text[:fidelity_start] + "### 10-Second Fidelity Test\n\n" + fidelity_checks(template) + "\n\n" + text[fidelity_end:]
    preflight_start = text.index("### Pre-Flight Checklist")
    preflight_end = text.index("## 4. Troubleshooting Table", preflight_start)
    text = text[:preflight_start] + "### Pre-Flight Checklist\n\n" + preflight(template) + "\n\n" + text[preflight_end:]
    trouble_start = text.index("## 4. Troubleshooting Table")
    trouble_end = text.index("## 5. Optional Second Register", trouble_start)
    text = text[:trouble_start] + "## 4. Troubleshooting Table\n\n" + troubleshooting(template) + "\n\n" + text[trouble_end:]
    appendix = text.index("## Appendix: v6 Full Text")
    text = text[:appendix] + "> **Historical source appendix:** the v6 prose below documents the medical editorial gouache source schema only. It is not an active block for this template and must not be copied into its production prompt.\n\n" + text[appendix:]
    text = text.replace(
        "> This full copy preserves the master schema's section order and slot mechanics. The active style-specific production blocks below supersede the source example values.",
        "> This full copy preserves the master schema's section order and slot mechanics. Historical drift explanations are source notes, not universal model laws. The active style-specific production blocks below supersede the source example values.",
        1,
    )
    return text


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MASTER.is_file():
        raise SystemExit(f"Missing locked master schema: {MASTER}")
    master = MASTER.read_text(encoding="utf-8")
    required_headings = re.findall(r"^#{1,3} .+$", master, flags=re.MULTILINE)
    for template in QUICK_STYLE_TEMPLATES:
        output = OUT_DIR / f"{template.template_id}.md"
        rendered = render(template)
        headings = re.findall(r"^#{1,3} .+$", rendered, flags=re.MULTILINE)
        if headings[1:] != required_headings[1:]:
            raise SystemExit(f"Heading structure drift in {output.name}")
        for slot in ("{N}", "{SCENE}", "{SUBJECTS}", "{PROPS}", "{FRAME}", "{ASPECT_RATIO}"):
            if slot not in rendered:
                raise SystemExit(f"Missing required slot {slot} in {output.name}")
        if template.name.casefold() in ", ".join(template.negative_constraints).casefold():
            raise SystemExit(f"Negative constraints contradict the target style in {output.name}")
        try:
            validate_style_slots(template, rendered)
        except ValueError as error:
            raise SystemExit(str(error)) from error
        output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Generated {len(QUICK_STYLE_TEMPLATES)} full style schema copies in {OUT_DIR}")


if __name__ == "__main__":
    main()
