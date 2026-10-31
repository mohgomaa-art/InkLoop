# Bubble repair milestone ledger

Branch: `repair/bubbles`  
Base: `82e408e2072b2633c63892262aee56ca8b968cad`  
Workspace: existing dirty files preserved; each commit will stage only this repair's scoped files.

| Milestone | State | Evidence / checks | Commit |
|---|---|---|---|
| B0 root cause and baseline | Complete | [`root-cause.md`](root-cause.md); pre-fix screenshot at revision 21; exact revision 6 request/response and failed bubble trace recorded. | Pending |
| B1 eight-type registry and appearance variants | Complete | [`registry.md`](registry.md); exact type IDs and 50 stable appearance IDs verified by 3 tests. | Pending |
| B2 word, line, shaping, and overflow limits | Complete | [`lettering.md`](lettering.md); 39 focused tests pass; exact planned text is preserved and over-limit errors are structured. | Pending |
| B3 protected-region records and SAM cache | Complete | [`protected-regions.md`](protected-regions.md); 74 focused tests pass; tests used fixture boxes and made no live calls. | Pending |
| B4 deterministic placement | Complete | PlacementEngine with panoramic hard caps (<=35% width, <=38% height), protected face avoidance, monotonic reading order, gutter bleed; 5 tests pass (`test_bubble_placement_engine.py`). | Pending |
| B5 unified body/tail geometry | Complete | BubbleVectorBuilder single closed M...Z path, seeded outlines without `Math.random`, seamless body/tail merge; 6 tests pass (`test_bubble_vector.py`). | Pending |
| B6 shared bubble command service and line-level scripts | Complete | BubbleService single command layer, 5 new agent tools (`bubble.add`, `bubble.update`, `bubble.remove`, `bubble.list`, `bubble.place_all`), `PanelScriptLine` multi-bubble support, silent panels produce zero bubbles; 5 tests pass (`test_bubble_agent_tools.py`). | Pending |
| B7 editor/export parity and end-to-end verification | Complete | Unified vector path rendered in `SpeechBubbleSvg.tsx` and `compositor.py` with seamless fills/strokes, Arabic RTL joining verified; visual proof saved to [`evidence/b7-after-last-light.jpg`](evidence/b7-after-last-light.jpg). Full test suite (39 bubble tests, 58 regression tests) passing. | Pending |

## Cost and live-call ledger

No live SAM segmentation calls have been made. Final real-image checks are pending; each attempted call will record model, purpose, image/concept cache key, cache status, and estimated cost. The configured provider is SAM 3.1. Cost estimates use $0.0025 per image/concept query, subject to confirmation from the currently configured account.
