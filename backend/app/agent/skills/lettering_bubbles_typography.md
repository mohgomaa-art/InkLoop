# Lettering, bubbles, tails, and typography

**Callable tools:** `canvas.search_bubble_presets`, `canvas.add_speech_bubble`, `canvas.update_speech_bubble`, `canvas.detect_character_anchor`, `canvas.inspect_page_spacing`, `editor.add_text_layer`, `editor.update_vector_layer`.

Some tools are callable by the deterministic production workflow but may not be advertised to the model on every turn. Call only a tool actually available in the current path; use its registered schema. The repository currently does not expose a supported audio-to-viseme lip-sync tool.

- Do not invent narration, captions, or SFX when exact wording is missing. `text.generate_dialogue` has a deterministic simulated adapter only in explicit offline mode; it is not a live dialogue-generation capability. Never use its offline result as live creative completion or imply a model wrote it. A concise Agent-drafted spoken line is allowed only when explicitly represented in the typed panel plan and a selected character would plausibly say it; otherwise leave the panel without a balloon. Keep proposed wording distinct from exact creator-authored text.
- Keep semantic text/speaker/panel records distinct from typography geometry, bubble body, and tail. Preserve stable layer and speaker IDs.
- Reserve speech bubbles for audible words spoken by a named, selected character. Put narration in a caption/narration box only when it adds information the art does not show; otherwise omit it. Put internal thought in a thought bubble. Never place scene descriptions or action summaries in character speech.
- Keep newly drafted speech short: aim for 8 words or fewer, with 12 words as the maximum. Preserve exact creator-authored dialogue without rewriting or truncation. New Agent speech bubbles use 24px text; measure and report overflow rather than silently shrinking type.
- Select bubble treatment for delivery and voice (ordinary speech, thought, shout, whisper, radio) while keeping it editable and legible. Avoid applying one repeated shape to every line when variation helps the scene.
- Pass the beat's emotional intent, delivery, narrative role, and relevant action context into `canvas.add_speech_bubble`; when those signals are present the server selects the matching treatment. Keep creator-selected bubble presets as intentional overrides.
- Keep body and tail connected with one coherent silhouette where supported. Use a stable speaker ID and a saved anchor, or a clearly labeled single-selected-subject estimate. Never present an estimated subject as identity recognition.
- Agent placement is automatic and collision-checked against the detected subject and existing lettering. If the bounds or safe space cannot be established, report the tool error rather than forcing a fixed location or covering the character. Use `canvas.detect_character_anchor` for a focal-subject estimate and `canvas.inspect_page_spacing` for measured page gaps.
- Font choice must fit the genre and remain readable. Check that the font is installed/licensed and contains required glyphs before use.
- For Arabic/English/mixed text, use the actual Unicode bidirectional/shaping renderer. Verify wrapping, punctuation, baseline, glyph shaping, and final-size readability; do not call RTL support complete based only on CSS direction.
- A still-image speaking mouth pose is not lip-sync. True lip-sync requires audio, viseme/mouth-shape mapping, and a timed animation track. Do not claim or call this capability in InkLoop unless a real registered tool is added.

**Research basis:** see the lettering, bubbles, Arabic/mixed-text, and lip-sync sections of the research report.
