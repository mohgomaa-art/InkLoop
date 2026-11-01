# Character, style, and reference continuity

**Tools this workflow may use:** `canon.inspect_characters`, `canon.inspect_reference_anchor`, `canon.propose_character_mutation`, `canon.apply_approved_mutation`, `assets.list_assets`, `image.verify_visual_consistency`.

Use the current registry schema for each call. If a tool is not advertised or its registry adapter is unavailable, do not claim to have used it.

- A character may be human, animal, creature, object-like, abstract, masked, headless, geometric, or another declared form. Do not infer a human body, face, or anatomy when the profile does not say so.
- Inspect canonical IDs, versions, required identity anchors, exclusions, references, and provenance before a generation or continuity decision.
- Keep stable identity separate from mutable scene state: pose, gaze, emotion, injury, dirt, wetness, outfit condition, and temporary accessories can change without rewriting canon.
- Keep authored attributes, reference observations, model inferences, and unknowns distinct. Never turn an uncertain visual inference into a mandatory canon fact.
- Treat character identity references and style references as separate typed inputs. Preserve source asset IDs and versions. A selected style must not overwrite a character; a character reference must not silently replace the selected style.
- For each panel, pass only the selected/planned cast and relevant references. Do not carry an unselected character into the image just because it appeared in prior context.
- A unique canonical-name correction is allowed only when the target resolves unambiguously; disclose it. Ask one focused question when two identities remain plausible.
- `canon.propose_character_mutation` may create a proposal. `canon.apply_approved_mutation` is approval-gated: never bypass that gate or imply a proposal is canonical before approval succeeds.
- Visual verification is a measured result, not a guarantee. Report which invariants were checked and which were not.

**Research basis:** see the report sections on references, continuity, expression, and non-human character form.
