# Meta Muse Image Prompting & Reference Conditioning

This reference provides exact prompt engineering patterns for Meta Muse Image `/v1/images/edits` and `/v1/images/generations` to achieve consistent identity, natural performance, and clean rendering.

---

## 1. Prompt Hierarchy & Structural Layering

To prevent prompt competition and instruction drift, compile prompts in a strict sequential order:

```text
[1. MEDIUM & RENDERING HEADER]
Graphic novel comic panel illustration, clean ink linework, subtle screen tones.

[2. CANONICAL IDENTITY ANCHORING]
Preserve the exact character likeness from the canonical reference image.

[3. SUBJECT PERFORMANCE, ACTION & GAZE]
Gomaa is leaning forward over a wooden rooftop workbench, holding a thin copper wire with tweezers.
His head is angled three-quarters left; both eyes look directly down at the open lantern housing.
His expression is quiet, intense concentration: slight furrow between eyebrows, lips closed firmly without strain.
His shoulders are hunched forward in focused craftsmanship, left hand steadying the lantern base.

[4. COMPANION / SECOND SUBJECT PERFORMANCE]
Beside him, Muse (tiny round white furry creature) sits upright on the table edge.
Its head is tilted 20 degrees in curious observation, dark bead eyes watching the tool movement.

[5. ENVIRONMENT & LIGHTING]
Night sky background with distant city rooflines and cold blue starlight contrasting with the warm amber glow from the lantern's test filament.

[6. CANONICAL IDENTITY INVARIANTS]
Gomaa [char_gomaa] — preserve: black curly hair, dark tortoiseshell glasses, freckles across nose bridge, dark ribbed turtleneck sweater.
Rules only for Gomaa: do not depict formal suits or lab coats.

[7. NEGATIVE CONSTRAINTS & QUALITY GUARDS]
Do not draw speech bubbles, lettering, or captions into the image.
Avoid crossed eyes, divergent pupils, wandering gaze, vacant stares, extra fingers, or distorted facial anatomy.
```

---

## 2. Multi-Image Reference Payload Construction

Meta Muse Image accepts an ordered array of images in `ReferenceImagePayload`:

```python
ReferenceImagePayload(
    asset_id="art_gomaa_canon_ref_01",
    image_bytes=b"...",
    mime_type="image/png",
    role="character_reference",  # Role instructs prompt compiler
    character_id="char_gomaa",
    weight=1.0,
    notes="Primary face and hair reference for Gomaa"
)
```

### Ordering Rules
1. **Character References First**: In multi-character scenes, attach verified portraits in declared cast order (up to 3 characters max).
2. **Composition / Previous Panel Reference Second**: If doing a direct continuation or pose variation, attach the composition reference.
3. **Style Reference Third**: Attach the creator-selected style profile reference.
4. **Hard Limit**: Maximum 5 reference images per request.

---

## 3. Scoping Style vs Identity in Prompt Directives

To prevent the style reference from erasing the character's facial likeness:

- Include explicit negative boundary:
  `"Do not copy any style reference's subject, characters, objects, scene, text, framing, panel layout, or number of panels."`
- Explicit character likeness directive:
  `"Keep each selected character's identity separate. Use style images only for rendering technique, palette, line, and texture."`
