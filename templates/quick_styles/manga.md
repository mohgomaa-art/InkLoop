# Manga — Quick Style Schema
*Versioned InkLoop Agent quick style; provider-neutral values are mapped only to controls the configured provider supports.*
> **Active quick style:** `manga` · **Template version:** `inkloop.quick-style/1.0.0`  
> **Purpose:** Expressive Japanese comic rendering with intentional ink and screentone control.  
> This full copy preserves the master schema's section order and slot mechanics. Historical drift explanations are source notes, not universal model laws. The active style-specific production blocks below supersede the source example values. The medical clinic story, names, and props in the source are historical examples, not default scene content.  
> **Style variables:** `medium`: Japanese manga illustration; `linework`: Variable-weight ink contours, clean tapered marks, and purposeful hatching; `stroke_behavior`: Confident brush-pen strokes with controlled speed accents; `edge_quality`: Crisp focal contours with selective broken marks in atmosphere; `shading`: Graphic black-white masses, crosshatch, and controlled screentone values; `palette`: Monochrome by default; obey an explicitly selected color palette; `lighting`: Dramatic graphic lighting with legible highlight and shadow shapes; `background_detail`: Clear environmental cues with detail subordinated to the focal subject; `texture`: Printed screentone and restrained paper grain; `shape_language`: Readable silhouettes and expressive, deliberate exaggeration; `screentones_and_fx`: Use screentones, speed lines, or impact marks only when requested or narratively appropriate


> **What this file is**: a prompt-engineering schema for generating consistent AI-illustrated manga panels, not a style guide for a human artist. It evolved through several versions as real weaknesses got found — the version history below is kept intact so you don't re-discover the same problems later.

---

## ⚠️ Open Questions — Read Before Using v7.2

**1. v7 compresses v6's texture language — this is untested, and now two changes are stacked at once.** v7 drops several things that were doing specific work in v6: "scumbled and dry-brushed," "lost-and-found edges," the honest-aging detail ("elders get individual crease-strokes, softer jowls, textured gray hair"), and the explicit no-beauty-filter/no-airbrush bans. If v6 itself was never test-rendered, you're now stacking two unverified changes (v6's texture/character shift *and* v7's compression) into one prompt. **Recommendation: render a test batch before trimming further, and if texture or character-specificity looks weak, the first thing to try is re-adding v6's dropped detail (Appendix) — not inventing new language.**

**2. "Distant staff at most as soft blurred shapes" partially contradicts the hard cast-lock right above it.** The `CAST: exactly {N} people, no one else in frame` constraint is genuinely useful, but the exception clause right after it could give the model license to add people back in. Watch this specifically on the fidelity test.

**3. Watch for "magazine quality" pulling against "characterful/asymmetric."** STYLE CORE asks for honest, individual, non-symmetrical faces, while "editorial illustration" as a trained visual category leans toward idealized, symmetrical faces. Check texture and character-specificity independently on the fidelity test.

**4. Verify background-flattening actually happens.** The prompt asks the model to vary its own rendering fidelity *within one image*. Check specifically whether the background actually loosens and flattens, or stays as detailed as the face.

**5. Seed-based repair (Section 3's Repair Loop) is tool-dependent — don't assume it works everywhere.** Midjourney exposes and respects `--seed`, so patching one line while holding the seed fixed is a reliable way to isolate what changed. **DALL-E 3 does not reliably expose a usable seed to the user, and its internal prompt-paraphrasing (see Mechanism #3 below) further weakens seed-based reproducibility even where a seed exists.** On DALL-E 3, treat each generation as independent — the repair loop's *patch lines* are still useful, but don't expect "same seed + one new line = one isolated change" to hold.

**6. Still unresolved — character identity across panels.** No version of this schema locks a character's *face identity* across multiple generations. For a manga with recurring characters, this needs IP-Adapter/LoRA (SDXL/Flux), `--sref` (Midjourney, style only — not identity), or an attached reference image per generation (DALL-E/GPT-4o). Until one of these is wired in, this schema solves *stylistic* consistency only.

---

## 1. Version History (why each version changed)

| Version | Core idea | Failure that led to the next version |
|---|---|---|
| v1 (slot-grammar) | Locked template + fixed slot menus (scene/pose/prop pick-lists) | Abstract terms ("semi-realistic stylized cartoon") let the model pick its own generic interpretation. No skin/light physics described → drift toward anime or photoreal. Palette *named* (cerulean-teal) but not *described* as light behavior. |
| v2 (dense description) | Replaced category labels with physical/sensory description — skin, eyes, hair, light behavior described in prose, not named | Better fidelity, but no explicit ban on "flat/vector/cartoon" vocabulary, and no formal way to branch into the metaphor/symbolic mode from v1 — that branching logic got dropped. |
| v3 → v4 | Same dense-description approach + explicit banned-word list + hex-anchored colors + volumetric/dimensional form language | Overcorrected into CGI-adjacent territory. Words like "three-dimensional solid," "ambient occlusion," "sculpted clay," and "render directive" are literal 3D-pipeline vocabulary — the model reads them as Blender/Pixar instructions, not painting instructions. Produced a uniform, evenly-lit "figurine" look. |
| v5 | Explicit medium lock ("this is a PAINTING, not CGI") + full purge of 3D-pipeline vocabulary + selective, art-directed dimensionality (face fullest detail → background flattens into haze) + smooth airbrush finish | Fixed the CGI problem, but the smooth-airbrush finish combined with "idealized" character language reproduced the original "AI gloss" problem — flawless symmetrical faces, plastic sheen, no individuality. **Also: used inline "NOT a photograph, NOT anime, NOT vector, NOT 3D/CGI" phrasing in the positive body — see Mechanism #2 (pink elephant) below. This likely undermined its own fix.** |
| v6 | Replaces smooth airbrush with **visible, controlled digital-gouache brushwork** — opaque strokes, matte grainy finish, lost-and-found edges — and replaces "idealized" characters with **specific, characterful, honestly-aged, asymmetric faces**. Explicitly bans plastic/beauty-filter/airbrush language. | Never test-rendered before being compressed into v7. **Also carried forward the same inline "NOT..." phrasing as v5 — same pink-elephant risk.** |
| v7 | Compresses v6 into a tighter prompt, and adds a genuinely new constraint: an explicit **cast lockdown** and **prop lockdown**. Drops the inline "NOT..." phrasing in favor of purely positive description (though not explicitly for this reason at the time). | Not yet tested. Compression may have cut load-bearing texture/character detail from v6; the cast-lock has a self-contradicting escape clause. |
| v7.1 | Splits bans into a dedicated **negative field**, separate from the body prompt. Adds `deformed hands, extra fingers` — a failure mode nothing in prior versions explicitly banned. | Not yet tested against v7's other open questions. |
| **v7.2 (current)** | No change to the production prompt text itself (it was already clean of inline "NOT..." phrasing). Adds an explicit **drift-mechanisms framework** (5 named causes, not just symptoms) and a **repair loop** for patching failed renders without full rewrites. Retroactively explains *why* several past versions' fixes may have partly worked despite self-sabotaging language, and flags that seed-based repair is tool-dependent. | See Open Questions above — none of the structural risks from v7/v7.1 are resolved by this addition; it's diagnostic and workflow tooling, not a new style. |

**The pink-elephant risk, stated plainly**: v5 and v6 both wrote "NOT a photograph, NOT anime, NOT vector, NOT 3D/CGI" directly into the body prompt the model reads as instruction. If naming a concept to exclude it can partially activate that concept (a real, documented phenomenon in language-conditioned generation, not speculation), then those versions' apparent fixes for CGI-drift may have worked *despite* this phrasing, not because of it. v7 happens to have already dropped this pattern in its rewrite — worth confirming that was deliberate going forward, not an accident of compression.

**Carried-over and still unresolved from v1**: the Mode A/B/C/D branching (storybook / cel / cinematic / metaphor) existed in v1 but has no equivalent in v7.x. If your manga needs the symbolic/metaphor register (giant wave, floating brain, halo — see Section 5 below), you currently have to construct that prompt by hand rather than swapping a locked mode block.

---

## 2. Diagnosis: The 5 Drift Mechanisms

Earlier diagnosis (below) named *symptoms*. This is the mechanism-level explanation for *why* each one happens — useful because it tells you which fix actually addresses the cause versus which just treats the symptom.

| Mechanism | What happens | Which past failure this explains |
|---|---|---|
| **Dilution** | Models weight the first ~40 and last ~20 tokens hardest. A long prose block buries the style core by the time scene slots arrive — attention to the style instructions decays across a long prompt. | v6's ~600-word block; explains *why* "style stated once, prompt runs long → model forgets it" happens, not just that it does |
| **Pink elephant** | Every "NOT 3D / NOT anime" phrase *mentions* the banned concept — naming it can partially activate it. Negatives belong in a dedicated negative-prompt field, never the positive body. | v5 and v6's inline "NOT..." phrasing — see note above |
| **Paraphrase** | Some tools (notably DALL-E 3) rewrite your prompt internally before generating. Long conditional prose gets rephrased and constraints can be silently dropped; short imperative sentences survive rewriting better. | Explains inconsistent results on DALL-E 3 specifically, even with an otherwise-correct prompt |
| **Slot smuggling** | Scene/role words like "surgeon" or "lab" carry their own learned visual priors (sterile photorealism, equipment clutter) independent of your style instructions, and can override them. | The reason the Slot Rules restrict slots to "nouns and verbs only, no style words" — this names *why* even neutral-sounding nouns can betray the style |
| **Open-world slots** | Leaving counts/quantities unstated invites the model to fill gaps with hallucinated crowds, invented equipment, or random background text. | Exactly what the v7 cast/prop lockdown was built to close |

**The original failure-mode table (kept for reference — same underlying issues, listed by symptom rather than mechanism):**

| Failure | Effect on output |
|---|---|
| Abstract terms ("semi-realistic stylized cartoon") | Model picks its own generic cartoon interpretation |
| No skin/eye/hair rendering physically described | Faces drift toward anime or photoreal |
| Palette *named* but not *described* as light behavior | Wrong color temperature in output |
| No light physics narrative | Flat lighting, hard black shadows |
| 3D-pipeline words used to mean "dimensional" | Model outputs CGI/figurine look instead of painting |
| Smooth/idealized language with no texture or individuality specified | "AI gloss" — plastic sheen, symmetrical stock faces |

**The fix, updated**: dense positive-only style core, anchored at both the front and back of the prompt (fighting dilution); closed-world scene wrappers with explicit counts (fighting open-world slots); negatives exiled entirely to their own field (fighting pink-elephant); short imperative phrasing where the target tool is known to paraphrase (fighting paraphrase-drift); and neutral, style-free scene nouns only (fighting slot smuggling).

---

## 3. MASTER PROMPT v7 (current production version) — Compressed + Cast/Prop Lockdown

**What changed from v6**: compressed the prose (see Open Question #1 for what got cut) and added two new hard constraints that no earlier version had — a **cast lockdown** (exact headcount, no incidental background people) and a **prop lockdown** (only named props, every other surface empty, explicit bans on medical equipment/monitors/signage/wall text). These directly target the clutter and incidental-figure drift the original wider-batch audit flagged.

Locked blocks are untouchable. Fill only the `{SLOTS}`. Copy everything including the closing anchor line.

```
Japanese manga illustration. Confident brush-pen strokes with controlled speed accents. Crisp focal contours with selective broken marks in atmosphere. Printed screentone and restrained paper grain.

STYLE CORE: Japanese manga page illustration with confident variable-weight ink contours, clear black-white value design, intentional screentone texture, expressive readable faces, and purposeful graphic shadows; use color only when the creator requests color.
MEDIUM: Japanese manga illustration
LINEWORK: Variable-weight ink contours, clean tapered marks, and purposeful hatching
STROKE: Confident brush-pen strokes with controlled speed accents
SHADING: Graphic black-white masses, crosshatch, and controlled screentone values
PALETTE: Monochrome by default; obey an explicitly selected color palette
LIGHTING: Dramatic graphic lighting with legible highlight and shadow shapes
BACKGROUND: Clear environmental cues with detail subordinated to the focal subject
SHAPE LANGUAGE: Readable silhouettes and expressive, deliberate exaggeration
EFFECTS: Use screentones, speed lines, or impact marks only when requested or narratively appropriate

WORLD: {creator-selected environment and world details}. Render its surfaces and atmosphere using the pinned profile variables; do not invent setting-specific props.
FRAME: {creator-selected framing}; {creator-selected aspect ratio}; keep focal hierarchy clear and leave text-safe space only when requested.
CAST: exactly {N} requested entities, no incidental people, creatures, or implied human anatomy.
SCENE: {what happens and where exactly; concrete nouns and verbs only}
SUBJECTS: {identity, actual form, pose, mutable state, emotion, and gaze for each selected entity; concrete nouns and verbs only; no style instructions}
PROPS: only these — {named props and placement, max 3}. Do not add unnamed objects.

Closing anchor: Japanese manga page illustration with confident variable-weight ink contours, clear black-white value design, intentional screentone texture, expressive readable faces, and purposeful graphic shadows; use color only when the creator requests color.
```

### Negative Field (separate parameter — never merged into the body prompt)

Keep this as a separate style-profile field. The current Meta adapter maps it to an `Avoid:` clause in the text prompt because its request has no native negative-prompt parameter; this is not a separate provider-side negative channel.

```
painterly gouache bleed, photographic skin texture, unrequested full-color gradients, unrequested text, extra cast members, unrequested speed lines
```

**This is now the single source of truth for "avoid" words.** The body prompt's closing anchor above has had its redundant "no text anywhere" trimmed since the negative field already covers text/letters/watermark/signature/logo — don't duplicate bans across both places, or updates will drift out of sync. If a new failure mode shows up later (see Purge Table below for the historical ones), add it here once, not to both the body and the negative field.

**What this specifically adds that nothing else in the schema covered**: `deformed hands, extra fingers` — the classic AI-hands failure mode. Every prior version only gave a *positive* hand instruction ("hands simple and relaxed," "hands simplified, a few stroke-folds only"); nothing explicitly banned the failure case until now. Worth keeping even if you revise the rest of this field later.

Keep this table next to the prompt. Each row below was a real drift a past version fell into. When troubleshooting an "off" render later, the instinct will be to reach back into one of these — that's exactly how each drift happened the first time.

| ❌ Never write | ✅ Write instead | Drift it causes if reintroduced |
|---|---|---|
| 3D world / dimensional scene / sculpted / solid | flat picture plane / painted canvas | CGI/figurine look (v4's failure) |
| ambient occlusion | soft painted shadow pooling in creases | 3D-render vocabulary leak |
| render / render directive | painting | Same |
| depth of field | hazy painted background blur | CGI-camera vocabulary leak |
| shading wraps around curvature | gradient laid onto the form | 3D-modeling vocabulary leak |
| smooth airbrush / buttery gradient | visible brushwork, scumbled, dry-brushed | Reintroduces plastic "AI gloss" (v5's failure) |
| idealized / flawless / beauty-filter symmetry | specific, characterful, honestly asymmetric | Reintroduces generic stock-face sameness |
| highlights follow the light source (physically) | highlights placed where composition wants them | Loses art-directed, painterly logic |

### Slot Rules

- Slots contain only concrete scene facts, entities, actions, counts, and named objects. Put all rendering language in the profile variables.
- Entity slots are open-form: humans, animals, monsters, object-like beings, abstract forms, and hybrids are valid. Never infer human anatomy that the creator did not specify.
- State an exact subject count and list only requested props; do not permit vague extras or background-figure exceptions.
- Describe a specific emotion, pose, action, and gaze only when relevant; never let temporary state rewrite canonical identity.
- Framing and aspect ratio come from the creator or active Canvas target, not from this style preset.
- Do not copy reference-image subjects, objects, text, or layout into style rules.

### Filled Example — Image 3 Fidelity Test

```
One small round nonhuman creature with two dot eyes and a curved smile, standing in a relaxed pose, full body, on a plain pale background.
```
*(Note: the desktop monitor from earlier versions' example is dropped here — it would violate v7's explicit "no monitors" prop ban.)*

### Compact Variant (Midjourney / token-limited tools)

```
Japanese manga page illustration with confident variable-weight ink contours, clear black-white value design, intentional screentone texture, expressive readable faces, and purposeful graphic shadows; use color only when the creator requests color.; Variable-weight ink contours, clean tapered marks, and purposeful hatching; Graphic black-white masses, crosshatch, and controlled screentone values; Monochrome by default; obey an explicitly selected color palette; Dramatic graphic lighting with legible highlight and shadow shapes; Printed screentone and restrained paper grain; exactly {N} requested subjects only; {SCENE}; {SUBJECTS}; {PROPS}; creator-selected framing {FRAME}; creator-selected aspect ratio {ASPECT_RATIO}. Send the separate negative constraints only through a provider-supported negative field.
```

### 10-Second Fidelity Test

- **Medium check:** fail if the output contradicts `Japanese manga illustration`; pass when that rule is visible where applicable.
- **Linework check:** fail if the output contradicts `Variable-weight ink contours, clean tapered marks, and purposeful hatching`; pass when that rule is visible where applicable.
- **Stroke Behavior check:** fail if the output contradicts `Confident brush-pen strokes with controlled speed accents`; pass when that rule is visible where applicable.
- **Edge Quality check:** fail if the output contradicts `Crisp focal contours with selective broken marks in atmosphere`; pass when that rule is visible where applicable.
- **Shading check:** fail if the output contradicts `Graphic black-white masses, crosshatch, and controlled screentone values`; pass when that rule is visible where applicable.
- **Palette check:** fail if the output contradicts `Monochrome by default; obey an explicitly selected color palette`; pass when that rule is visible where applicable.
- **Lighting check:** fail if the output contradicts `Dramatic graphic lighting with legible highlight and shadow shapes`; pass when that rule is visible where applicable.
- **Background Detail check:** fail if the output contradicts `Clear environmental cues with detail subordinated to the focal subject`; pass when that rule is visible where applicable.
- **Texture check:** fail if the output contradicts `Printed screentone and restrained paper grain`; pass when that rule is visible where applicable.
- **Shape Language check:** fail if the output contradicts `Readable silhouettes and expressive, deliberate exaggeration`; pass when that rule is visible where applicable.
- **Screentones And Fx check:** fail if the output contradicts `Use screentones, speed lines, or impact marks only when requested or narratively appropriate`; pass when that rule is visible where applicable.
- **Subject and count check:** exactly the requested subjects and named props; no unintended additions.

### Pre-Flight Checklist

- [ ] All required style variables are present and sourced from this profile version.
- [ ] Keep negative constraints separate in the profile contract; map them only to provider-supported controls.
- [ ] Scene, subject, cast, props, framing, and aspect ratio come from the creator request or explicit defaults.
- [ ] Style vocabulary stays in the style profile, not the scene or subject slots.
- [ ] The negative field does not contain this profile's defining medium or a pinned positive value.
- [ ] Cast and prop counts are explicit and do not include open-world exceptions.
- [ ] Preview image provenance names the provider, prompt, asset ID, and template version.
- [ ] Generated examples are examples; do not promise deterministic or exact style reproduction.

## 4. Troubleshooting Table

| Symptom | Fix |
|---|---|
| Style drifts toward another medium | Recheck the positive medium and linework variables: Japanese manga illustration; Variable-weight ink contours, clean tapered marks, and purposeful hatching. Remove conflicting positive context. |
| Surface treatment looks wrong | Adjust only the stroke, edge, shading, and texture variables: Confident brush-pen strokes with controlled speed accents; Crisp focal contours with selective broken marks in atmosphere; Graphic black-white masses, crosshatch, and controlled screentone values; Printed screentone and restrained paper grain. |
| Palette or lighting drifts | Edit the selected profile palette and lighting fields: Monochrome by default; obey an explicitly selected color palette; Dramatic graphic lighting with legible highlight and shadow shapes. |
| Subject, framing, or layout changed unexpectedly | Keep those details in the request-specific slots; remove subject or layout details from style references and style prose. |
| Preview differs between reruns | Treat generations as nondeterministic; compare the actual output and record the provider and prompt. Do not claim a fixed seed unless supported. |

## 5. Optional Second Register: Symbolic / Metaphor Mode

Not covered by v7's single locked template. From the wider source batch's conceptual images (giant wave + bucket labeled "Clinical Judgment," floating brain, crystal ball, caped doctor with halo) — useful for internal/psychological beats (stress, ambition, dream sequences) if your manga wants a tonal shift for those scenes.

**This is a creative addition, not something extracted from a coherent source** — the wider batch that inspired it was itself inconsistent (different AI sessions, no shared characters). Treat adopting it as your deliberate choice to unify a technique, not preservation of an original style.

Example scene construction:
```
SCENE: a serene minimal interior with shoji screen walls and pale tile
floor; a giant Hokusai-style ocean wave in flat ukiyo-e teal and white
crashes into a single oversized brass bucket standing center-frame, water
spilling and pooling around it; two tiny human figures stand far left,
dwarfed, observing in silence.
```

If you use this mode regularly, it's worth formally re-adding as a fourth locked block option (parallel to how v1 had Mode A/B/C/D) rather than constructing it ad hoc each time, and re-writing it in v7's textured vocabulary and cast/prop-lockdown style rather than v2's smoother, unconstrained language.

---

## 6. Still Open / Not Yet Solved by Any Version

1. **Character identity lock across panels** — the biggest gap. See "Open Questions" section at the top.
2. **v7's compression vs. v6's untested texture/character detail** — two unverified changes are currently stacked. See Open Question #1. Test before trimming further.
3. **Cast lockdown's self-contradicting exception clause** — "distant staff at most" may undermine "exactly {N} people." See Open Question #2.
4. **Characterful faces vs. "magazine quality" pulling back toward idealized** — untested. See Open Question #3.
5. **Selective-fidelity rendering (background flattening)** — untested. See Open Question #4. If it doesn't hold up on real generations, the schema needs a different lever (composition-based soft focus) rather than more painterly adjectives.
6. **Sequential/panel logic** — this schema generates single hero-banner-style images. Manga needs multi-panel pages, varying shot sizes (close-up/medium/wide) within one scene, and speech-bubble space planning. None of that exists yet in any version.
7. **Emotion/expression range** — the emotion slot values are still a short fixed list (skeptical half-smile, weary warmth, etc.). A recurring character will need a much larger and more specific expression vocabulary to avoid repeating the same 3-4 emotional beats for hundreds of panels.

---

> **Historical source appendix:** the v6 prose below documents the medical editorial gouache source schema only. It is not an active block for this template and must not be copied into its production prompt.

## Appendix: v6 Full Text (fallback reference)

Kept in full because v7 compressed it without testing v6 first (Open Question #1). If v7 renders come back weaker on texture or character-specificity than expected, this is the first place to pull detail back from — not a prompt to invent new language from scratch.

```
A hand-painted editorial illustration in a textured digital gouache style —
opaque painterly strokes on a flat 2D picture plane. NOT a photograph, NOT
anime, NOT vector, NOT 3D/CGI, NOT smooth airbrush, NOT plastic, NOT
beauty-filter. Premium healthcare magazine quality, but visibly PAINTED.

MEDIUM & TEXTURE (locked): This is a painting with visible, controlled
brushwork — like opaque gouache or matte acrylic applied digitally. Strokes
are most visible in hair, shadows, and background washes; transitions are
scumbled and dry-brushed in places, never one continuous perfect gradient.
Edges are lost-and-found: some crisp against the background, some
dissolving into loose paint. Matte finish with a faint grain. No plastic
sheen, no porcelain smoothness, no buttery airbrush, no dead-flat fills —
color is slightly broken, with subtle tone variation inside every shape.

FORM & SHADOW (locked): Zero line art — every edge is paint meeting paint.
Volume is suggested by painterly gradients plus readable light and shadow
planes on the face: lit forehead and cheekbone, softly shaded eye sockets
and jaw — planar like a gouache portrait study, then softened. Shadows are
SHAPED painterly forms with slightly irregular, stroke-quiet edges — part
soft, part crisp — never uniform gradient fades. Blush is dabbed in mottled
patches on cheeks and nose. Hair is built from chunky directional locks
with visible stroke texture and a few flyaway strands, one lighter sheen
streak. Hands simplified, a few stroke-folds only.

CHARACTERS (locked): specific, characterful individuals — never generic
beauties. Each face has a distinct structure: particular nose shape, brow
weight, jawline, cheekbones; natural slight facial asymmetry. Age is
painted honestly: elders get individual crease-strokes, softer jowls,
textured gray hair; the young get soft fullness and smooth-but-matte skin.
Eyes expressive with painted catchlights. Proportions charmingly
illustrative, slightly elongated. No beauty-filter symmetry, no stock-face,
no airbrushed perfection.

ENVIRONMENT (locked): spotless modern medical interior — walls in
desaturated pastel teal-cyan (#A8D8DC) with loose painterly washes, white
ceiling with slim recessed light panels, light wood and cream furniture,
one floor-to-ceiling window blown out to pure white, thin glass partition,
plants as loose dabbed foliage. Background progressively looser and flatter
toward the back — painted blur, not lens blur.

LIGHTING (locked): high-key and airy. One warm honey-gold key light
(#F5C87A) lays readable lit planes across faces and hands. All shadows
tinted cool teal-blue (#7FB3BD), shaped as painterly forms, never black.
A soft painted rim light separates figures from the background. The back
of the room dissolves into loose bright washes.

COLOR GRADE (locked): cool pastel teal-and-white base, cream accents,
exactly ONE warm golden zone. Low contrast, optimistic, calm — but with
painterly color variation everywhere, never sterile-smooth.

CAMERA (locked): eye-level, wide 16:9 banner, waist-up or knee-up framing,
subject slightly off-center, upper third kept simple for a headline,
sharpest paint handling on faces.

SCENE: {what is happening, where exactly in the room}

CHARACTERS IN SCENE: {1–2 people — role, age, hair, clothing, asymmetric
pose, one specific emotion, gaze direction}

PROPS (max 3): {named objects and placement}

Final directive: hand-painted gouache-style editorial illustration,
visible controlled brushwork, mottled dabbed blush, shaped teal shadows,
characterful specific faces, matte grainy finish, zero line art, pastel
teal palette, one warm golden glow, no text, no letters, no logos, no
watermarks.
```

**If pulling detail back from here**: consider merging v6's texture/character depth with v7's cast/prop lockdown, rather than choosing one wholesale — they solve different problems and aren't mutually exclusive.
