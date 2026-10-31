# Bubble system repair: B0 root-cause trace

Date: 2026-10-31
Branch: `repair/bubbles`, created from `82e408e2072b2633c63892262aee56ca8b968cad` with the pre-existing dirty worktree preserved.

## Reproduction evidence

- Saved trace: `runs/agent_sessions/session_last_oneee_b36304f4_1793422296925_zrtxxn.json`.
- Project: `last_oneee_b36304f4` (`last oneee · v3`). Page: `page_story_429f2386aa74`.
- The trace records the exact caption, `Some lights stay on.`, as a narration caption in beat 4 (source JSON lines 127–131 and repeated planning snapshots).
- At the text operation (source JSON lines 1424–1439), the Agent called `editor.add_text_layer` for panel `page_01_panel_04`, layer `text_7e0e1aaf8c0edc77`, font `Comic Neue` at 18 px. The successful result (lines 2613–2635) saved revision 6 with `kind: text`, x=61, y=930.793, width=778, and no `height`, `bubble_shape`, `tail_target`, or semantic text carrier in layer metadata.
- That panel is 810 px wide (source JSON lines 1313–1316); the operation therefore filled 96.0% of the panel width with an ordinary caption.
- The same run records `canvas.add_speech_bubble` failing for panels 2 and 3 with `ERR_BUBBLE_TAIL_ANCHOR_REQUIRED` (lines 2587–2610). Those failures do not establish the appearance of a successful dialogue bubble.
- The pre-fix editor screenshot is [`evidence/b0-before-last-light.jpg`](evidence/b0-before-last-light.jpg). It shows the saved page at revision 21, where all 8 layers are four panel layers and four image layers; the old caption is absent. This later revision is retained as the current-state baseline and is not misrepresented as a screenshot of revision 6.

## Verified cause

1. `backend/app/agent/registry.py:2480-2502` creates `editor.add_text_layer` as `LayerKind.TEXT` and defaults its width to `panel.rect.width - 32`. At the traced 810 px panel, that is 778 px. It stores no semantic carrier or bubble type.
2. `frontend/src/views/ManualEditorView.tsx:2947-2968` routes every visible text layer through `SpeechBubbleSvg`, without checking whether the layer is a caption/plain text or a balloon.
3. `frontend/src/components/editor/SpeechBubbleSvg.tsx:77-118` defaults missing shape/tail metadata to `oval` and `smooth_pointer`; a missing tail target points below the bubble. A plain caption is consequently painted as a wide oval with a pointer.
4. `backend/app/canvas/compositor.py:232-263` also treats every text layer as a bubble, but independently defaults to `rounded_rectangle` and a different height/layout path. Editor and export can disagree.
5. `frontend/src/views/ManualEditorView.tsx:1127-1129` creates a new manual speech bubble with its target below the body, which cannot aim at the speaker.

## Rejected and unresolved hypotheses

- **Panel-derived Agent balloon sizing caused this caption:** rejected. The failing trace operation is `editor.add_text_layer`, whose width is set directly from the panel. The separate successful Agent bubble sizing path in `backend/app/agent/registry.py:3021-3045` measures shaped text with Pillow metrics; that is not the source of this caption width.
- **The screenshot proves revision 6 rendered the defect:** rejected. The screenshot shows revision 21, and the UI reports 8 layers with no text layer. It is useful for current saved state only. A historical version is immutable in the revision store; restoring it would mutate the user's page, so this baseline capture did not do that.
- **A successful Agent dialogue bubble already has verified speaker-tail placement:** unresolved. Both relevant bubble calls in this saved trace failed before producing an artifact.

## B0 conclusion

The root cause is a type/renderer mismatch: plain text and narration are represented as generic `TEXT` layers, while the editor and export interpret every `TEXT` layer as a speech balloon and use different rendering defaults. The 778 px panel-derived width makes that mismatch visually extreme. Agent balloon sizing is a separate path and is not implicated in this caption failure.

No application files were edited before saving the screenshot and recording this trace. The historical page was not restored or otherwise changed.
