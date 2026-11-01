# Medical Editorial Illustration — AI Generation Schema
*Production tool for AI-generated manga panels (Midjourney / SDXL / DALL-E / GPT-4o)*

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
Hand-painted digital gouache editorial illustration. Matte visible
brushwork on a flat 2D canvas. Volume built from shaped painterly strokes
and soft planar shadows — never computed lighting. Zero outlines: every
edge is paint meeting paint. Matte grainy finish, slightly broken color
inside every shape.

STYLE CORE: stylized semi-realistic characters with characterful specific
faces — particular nose, brow weight, natural slight asymmetry, never
generic beauties. Chunky directional hair with a few flyaway strands and
one lighter streak. Mottled dabbed blush on cheeks and nose. Soft planar
face shading: lit forehead and cheekbone, shaded eye sockets and jaw.
Shadows are shaped painterly forms tinted teal-blue, never black, never
uniform gradient fades. Hands simple and relaxed.

WORLD: bright spotless modern clinic, walls desaturated pastel teal-cyan
(#A8D8DC) in loose painterly washes, light wood and cream furniture, one
floor-to-ceiling window blown out to pure white, plants as loose dabbed
foliage. Background grows looser, flatter and hazier with distance —
painted blur, not lens blur. One warm honey-gold key light (#F5C87A)
lays readable lit planes on faces and hands; a soft painted rim light
lifts figures off the background. High-key, airy, optimistic, low
contrast, exactly one warm zone.

FRAME: wide 16:9 banner, eye-level, waist-up framing, subject slightly
off-center, upper third kept simple for a headline, sharpest paint
handling on the faces.

CAST: exactly {N} people, no one else in frame, no background crowds —
distant staff at most as soft blurred shapes.
PEOPLE: {role, age, hair, clothing, asymmetric pose, one specific emotion,
gaze direction — nouns and verbs only}
PROPS: only these — {named props with placement, max 3}. Every other
surface empty. No medical equipment, no monitors, no signage, no wall
text, no logos.

Closing anchor: hand-painted gouache editorial illustration, visible
brushwork, teal-blue shaped shadows, one warm golden glow, pastel teal
world.
```

### Negative Field (separate parameter — never merged into the body prompt)

This goes into the tool's actual negative-prompt input (Midjourney `--no`, SDXL/Flux negative prompt box, DALL-E/GPT-4o as an explicit "avoid" instruction appended separately). Keeping it out of the body matters mechanically: the model weighs "build this" and "avoid this" as separate signals when they're in separate fields, rather than competing for attention inside one token stream the way inline "NOT anime, NOT 3D" phrasing does.

```
line art, outlines, ink, sketch, pen strokes, 3D, render, CGI, Blender,
Pixar, clay, figurine, plastic skin, porcelain, airbrush smoothness,
beauty filter, photo, photorealism, anime, manga, cel shading, vector,
flat design, poster, dark shadows, black shadows, heavy contrast, crowd,
extra people, text, letters, watermark, signature, logo, deformed hands,
extra fingers
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

- Slots accept **nouns, verbs, and concrete adjectives only** — no style words inside slots (no "cartoon," "flat," "cel," "vector," "comic," "anime," "3D," "render," "smooth," "flawless" — they break the lock)
- Emotion must be **specific**: "skeptical half-smile," "weary warmth" — never "happy"
- Poses must be **asymmetric**; every hand occupied or in a named gesture
- Mentorship scenes = young + elderly pairing; peer scenes = same age, contrasting emotions
- **Cast/prop counts are hard limits, not suggestions** — state {N} explicitly (e.g., "exactly 2 people") and list props by name; don't leave either open-ended

### Filled Example — Image 3 Fidelity Test

```
CAST: exactly 1 person, no one else in frame, no background crowds.

PEOPLE: one elderly male doctor with thick swept-back white hair, full
white beard, and bold dark rectangular glasses, wearing a white coat over
a light blue shirt and striped navy tie, stethoscope around neck, seated
leaning forward with hands clasped on the desk, brow furrowed in skeptical
judgment, looking directly at the viewer.

PROPS: only these — papers spread on the desk, a potted green plant at the
left wall. Every other surface empty.
```
*(Note: the desktop monitor from earlier versions' example is dropped here — it would violate v7's explicit "no monitors" prop ban.)*

### Compact Variant (Midjourney / token-limited tools)

```
hand-painted digital gouache editorial illustration, matte visible
brushwork, painterly volume, no outlines, characterful asymmetric faces,
mottled dabbed blush, chunky directional hair, stylized proportions,
pastel teal-cyan clinic #A8D8DC, blown-out white window, warm golden key
light #F5C87A, shaped teal shadows #7FB3BD, painted rim light, loose
hazy background, waist-up, negative space upper third, exactly {N}
people only, no crowds, only named props, empty surfaces, no equipment,
no signage {SCENE} --ar 16:9 --style raw --no 3D, CGI, render, smooth
airbrush, plastic, symmetry, outlines, text, photorealism, anime, vector,
extra people, clutter
```

### 10-Second Fidelity Test

Check these independently — a render can pass one and fail the others:

- **Texture check — Failed**: perfectly smooth gradients, buttery airbrush, plastic/porcelain sheen, no visible stroke anywhere. **Passed**: visible brush marks in hair/shadows/background, matte grain, some crisp edges and some dissolving ones.
- **Character check — Failed**: symmetrical stock-beautiful face, generic features, airbrushed perfection. **Passed**: a specific, slightly asymmetrical, individual face you could describe distinctly from another generation.
- **Dimensionality check — Failed**: every object equally modeled, uniform detail front-to-back. **Passed**: face most detailed → background loosest and flattest.
- **Cast/prop-lockdown check (new in v7) — Failed**: extra background staff visible as distinct figures (not just blurred shapes), or unnamed objects filling empty surfaces (a wall clock, a second monitor, signage). **Passed**: exactly the stated headcount, only the named props, everything else genuinely empty.

**Rule of thumb**: if you could believably 3D-print it, it failed the medium. If every generated face could pass for a stock photo model, it failed the character check — even if the texture check passed. If you can count more people or objects than you asked for, it failed the lockdown check — even if the style is perfect.

### Pre-Flight Checklist

- [ ] All 4 locked blocks present, unshortened, in order (STYLE CORE, WORLD, FRAME, plus the opening medium paragraph)
- [ ] Negative field submitted as a **separate parameter**, not merged into the body prompt
- [ ] No banned words anywhere in the body: *cartoon, flat, vector, cel, anime, comic, 3D, render, ambient occlusion, sculpted, depth of field, smooth airbrush, flawless, idealized, symmetry*
- [ ] Closing anchor line present
- [ ] Slots contain zero style vocabulary
- [ ] One warm light only, hex-anchored palette intact
- [ ] 16:9 + upper-third negative space stated
- [ ] **CAST states an exact number, not "a few" or left open**
- [ ] **PROPS lists specific named items only, with the empty-surface and no-equipment/signage bans intact**
- [ ] **Run the 10-Second Fidelity Test above on the actual output — check texture, character, AND cast/prop-lockdown independently**
- [ ] **Check background-flattening specifically (Open Question #4) — don't assume it worked because the prompt asked for it**
- [ ] **Check hands specifically — the negative field bans "deformed hands, extra fingers," but verify on the actual render, don't assume the ban alone fixes it**
- [ ] **If texture or character-specificity looks weak, consider re-adding v6's dropped detail (Appendix below) before inventing new language**

---

## 4. Troubleshooting Table

| Symptom in output | Fix |
|---|---|
| Looks like a 3D render / CGI figurine | Check for leaked 3D-pipeline vocabulary — see Purge Table. Don't add more "flat" language on top; remove the offending word instead. |
| Smooth, plastic, or "AI gloss" look returns | Check for leaked airbrush/smooth/flawless language — see Purge Table. |
| Faces still look generic/symmetrical despite texture instructions | This is the risk in Open Question #3. Strengthen PEOPLE with more specific, named asymmetries ("nose slightly off-center," "one eyebrow higher") rather than general "asymmetric" instructions. If it persists, pull back in v6's fuller CHARACTERS block (Appendix) — v7's compression may have cut too much. |
| Extra background people appear despite the cast lockdown | This is the risk in Open Question #2. Remove the "distant staff at most" exception clause entirely and re-test with a hard "no other people, empty background" instead. |
| Unnamed clutter appears (wall clock, second monitor, signage) despite the prop lockdown | Reinforce with "completely bare walls" or "nothing else in the room" alongside the existing bans. |
| Looks photographic | Strengthen opening: "flat 2D digital painting, illustration only, zero photorealism" |
| Faces too anime | Add: "Western editorial illustration proportions, realistic face structure" |
| Too dark / moody | Add: "overexposed windows, high-key, white-dominant frame" |
| Background too detailed / doesn't flatten | Try "soft focus background" or "background dissolves into hazy paint" rather than "depth of field" |
| Style drifts mid-set | Put style block first AND repeat the closing anchor; for MJ use `--sref {ref image URL} --sw 100` |
| Wrong palette | Use hex targets directly: walls #A8D8DC, shadows #7FB3BD, warm light #F5C87A |
| Same character, different face across panels | Text prompting alone won't fix this — see "Open Questions" section on IP-Adapter/LoRA/reference-image locking |

---

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
