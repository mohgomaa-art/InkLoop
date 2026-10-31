# Bubble repair handoff

## Current state

- Work is on `repair/bubbles`, branched at current HEAD without cleaning or resetting the pre-existing dirty worktree.
- B0 baseline is recorded in [`root-cause.md`](root-cause.md); screenshot: [`evidence/b0-before-last-light.jpg`](evidence/b0-before-last-light.jpg).
- The inspected browser session was isolated from the user's open Edge tab. The latter had unsaved changes and was not interacted with.
- The exact saved run shows a 778 px ordinary caption text layer in an 810 px panel at revision 6. The current page is revision 21 and has no text layer; the historical page was not restored.
- Root cause: plain text/narration layers are sent through the bubble renderer; export also treats them as bubbles with different geometry defaults.
- The proposed panel-sizing cause for Agent bubbles is rejected for this caption path; Agent bubble measurement already uses Pillow metrics. Two traced speech-bubble attempts failed because they lacked a tail anchor.

## Next actions

1. B1–B7 are fully implemented and verified. All 39 bubble-specific tests and 58 workflow/planner regression tests pass with zero failures.
2. Milestone artifacts and evidence:
   - B0: Root cause traced and documented in `root-cause.md`, baseline in `evidence/b0-before-last-light.jpg`.
   - B1: Canonical 8-type registry in `bubble_registry.py`.
   - B2: Font measurement, word/line limits, Arabic RTL shaping in `lettering_layout.py`.
   - B3: Region caching by SHA-256 and fail-closed unknown behavior in `protected_regions.py`.
   - B4: Deterministic placement engine with panoramic caps (<=35% width, <=38% height), face avoidance, and gutter bleed in `placement_engine.py`.
   - B5: Unified vector builder (`BubbleVectorBuilder`) with single closed M...Z path, no interior seams, and deterministic hash-seeded noise in `bubble_vector.py`.
   - B6: Shared command service (`BubbleService`) in `bubble_service.py`, 5 new CapabilityRegistry tools (`bubble.add`, `bubble.update`, `bubble.remove`, `bubble.list`, `bubble.place_all`), and line-level script planning with `PanelScriptLine` in `panel_planner.py` & `story_to_canvas.py`.
   - B7: Unified rendering in `SpeechBubbleSvg.tsx` and `compositor.py`, multi-bubble reading order, Arabic RTL letter joining, and visual proof in `evidence/b7-after-last-light.jpg`.
3. Ledger updated in `ledger.md`. All milestones B0–B7 are complete with rigorous evidence.
