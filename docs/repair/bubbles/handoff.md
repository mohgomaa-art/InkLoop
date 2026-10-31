# Bubble repair handoff

## Current state

- Work is on `repair/bubbles`, branched at current HEAD without cleaning or resetting the pre-existing dirty worktree.
- B0 baseline is recorded in [`root-cause.md`](root-cause.md); screenshot: [`evidence/b0-before-last-light.jpg`](evidence/b0-before-last-light.jpg).
- The inspected browser session was isolated from the user's open Edge tab. The latter had unsaved changes and was not interacted with.
- The exact saved run shows a 778 px ordinary caption text layer in an 810 px panel at revision 6. The current page is revision 21 and has no text layer; the historical page was not restored.
- Root cause: plain text/narration layers are sent through the bubble renderer; export also treats them as bubbles with different geometry defaults.
- The proposed panel-sizing cause for Agent bubbles is rejected for this caption path; Agent bubble measurement already uses Pillow metrics. Two traced speech-bubble attempts failed because they lacked a tail anchor.

## Next actions

1. B1–B3 are complete. The semantic registry retains all 50 appearance IDs; lettering now enforces type limits with shaped-font metrics; protected regions are cached by image SHA-256 and normalized concept, with explicit unknown/manual/override states. The current focused validation set passes 74 tests and made no live SAM calls.
2. Implement B4 deterministic multi-bubble placement using known protected regions, reading direction, gutters, and safe margins; reject unknown regions unless manually annotated or explicitly overridden.
3. Preserve the existing page and DB. Use a copy or dedicated test project for visual reproduction and post-fix UI/export checks.
4. Update this handoff and the ledger at each milestone; stage only bubble repair paths and make one scoped commit per completed B0–B7 milestone.
