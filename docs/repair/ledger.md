# Root-Cause Repair Ledger

Source: `docs/repair/evidence/M0/repro.md` and the user-provided mandate. Statuses are preserved conservatively. `OPEN / BROKEN` is a current reproduced defect; `NOT-REPRODUCED` means the stated symptom was exercised in this pass without reproducing it, not that the earlier user report was wrong. All other rows remain claims.

| ID | Title | Status | Root cause (`path:line`) | Evidence | Commit |
|---|---|---|---|---|---|
| P1 | Asset list returned a reported 500 and currently accepts invalid project scope | OPEN / BROKEN | `backend/app/api/routers/assets.py:56-83` currently treats project_id as optional and returns HTTP 200 for missing/unknown project scope; this does not explain historical default-project 500. | [`evidence/P1/repro.md`](evidence/P1/repro.md) | — |
| P2 | Style analysis returned 502 and error feedback was not useful | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/P2/repro.md`](evidence/P2/repro.md) | — |
| P3 | 404 path followed by JavaScript null before-reference error | NOT-REPRODUCED | No cause established; isolated missing-page route displayed its 404 without the reported JavaScript exception. | [`evidence/P3/repro.md`](evidence/P3/repro.md) | — |
| P4 | Project create, rename, edit, and delete lifecycle | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/P4/repro.md`](evidence/P4/repro.md) | — |
| P5 | Editor pages disappear after closing the editor | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/P5/repro.md`](evidence/P5/repro.md) | — |
| P6 | Restorable revisions and multi-step undo/redo | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/P6/repro.md`](evidence/P6/repro.md) | — |
| P7 | Page deletion/reordering and newest-first order | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/P7/repro.md`](evidence/P7/repro.md) | — |
| P8 | Sidebar close, keyboard access, responsive behavior, persistence | OPEN / BROKEN | `frontend/src/App.tsx:35` initializes `sidebarOpen` to `true` on every mount; no persisted state is read or restored. | [`evidence/P8/repro.md`](evidence/P8/repro.md) | — |
| K1 | Canvas selection visibility and clearing rules | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/K1/repro.md`](evidence/K1/repro.md) | — |
| K2 | Canvas cursor states | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/K2/repro.md`](evidence/K2/repro.md) | — |
| K3 | Image edit interaction, proportions, transform persistence | NOT-REPRODUCED | Not established; current interaction passed, and no historical failing trace exists. | [`evidence/K3/repro.md`](evidence/K3/repro.md) | — |
| K4 | Panel geometry, spacing, overlap, and image-placement separation | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/K4/repro.md`](evidence/K4/repro.md) | — |
| K5 | Bubble forms, tails, placement, speaker binding, and stable rendering | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/K5/repro.md`](evidence/K5/repro.md) | — |
| K6 | Font upload, Arabic shaping/RTL, and text behavior | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/K6/repro.md`](evidence/K6/repro.md) | — |
| K7 | Non-destructive vector lines and effects | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/K7/repro.md`](evidence/K7/repro.md) | — |
| K8 | Editor/export render parity | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/K8/repro.md`](evidence/K8/repro.md) | — |
| S1 | Non-human and conditional character identity schema | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S1/repro.md`](evidence/S1/repro.md) | — |
| S2 | One-action character creation and findability | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S2/repro.md`](evidence/S2/repro.md) | — |
| S3 | Character/Style Studio first-time flow simplicity | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S3/repro.md`](evidence/S3/repro.md) | — |
| S4 | Selected character allow-list and reference propagation | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S4/repro.md`](evidence/S4/repro.md) | — |
| S5 | Agent-created character proposal, persistence, and UI visibility | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S5/repro.md`](evidence/S5/repro.md) | — |
| S6 | Structured style comparison against reference | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S6/repro.md`](evidence/S6/repro.md) | — |
| S7 | Editable locked style variables and unified compiler | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S7/repro.md`](evidence/S7/repro.md) | — |
| S8 | Controlled style-fidelity and watercolor-drift experiments | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S8/repro.md`](evidence/S8/repro.md) | — |
| S9 | Documented prompting research applied to tested behavior | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S9/repro.md`](evidence/S9/repro.md) | — |
| S10 | Visual verification availability and truthful NOT_RUN status | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/S10/repro.md`](evidence/S10/repro.md) | — |
| A1 | Agent production-job loop and computed completion | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A1/repro.md`](evidence/A1/repro.md) | — |
| A2 | Planner schema, validation, and recovery contract | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A2/repro.md`](evidence/A2/repro.md) | — |
| A3 | Request routing and ambiguity table | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A3/repro.md`](evidence/A3/repro.md) | — |
| A4 | Revisioned Agent Canvas editing tool coverage | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A4/repro.md`](evidence/A4/repro.md) | — |
| A5 | Live progress events and truthful progress display | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A5/repro.md`](evidence/A5/repro.md) | — |
| A6 | Provider usage/cost instrumentation and truthful UI accounting | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A6/repro.md`](evidence/A6/repro.md) | — |
| A7 | Persisted interruption recovery without duplicate generation | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A7/repro.md`](evidence/A7/repro.md) | — |
| A8 | Weak-point and failure-mode inventory for every registered tool | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A8/repro.md`](evidence/A8/repro.md) | — |
| A9 | Workflow skills and source-backed creative research | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/A9/repro.md`](evidence/A9/repro.md) | — |
| Q1 | Panel as an independently described storytelling unit | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/Q1/repro.md`](evidence/Q1/repro.md) | — |
| Q2 | Panel events, story provenance, and repetition intent | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/Q2/repro.md`](evidence/Q2/repro.md) | — |
| Q3 | Layout variety, pacing metrics, and whitespace | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/Q3/repro.md`](evidence/Q3/repro.md) | — |
| Q4 | Per-panel visual brief and continuity context | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/Q4/repro.md`](evidence/Q4/repro.md) | — |
| Q5 | Typed text-kind decision, creator override, and silence | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/Q5/repro.md`](evidence/Q5/repro.md) | — |
| Q6 | Panel-to-asset mapping and aspect-ratio fit | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/Q6/repro.md`](evidence/Q6/repro.md) | — |
| Q7 | Root cause of unrelated generations and its regression | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/Q7/repro.md`](evidence/Q7/repro.md) | — |
| U1 | Monochrome reference-based design tokens and RTL layout | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/U1/repro.md`](evidence/U1/repro.md) | — |
| U2 | Remove the inappropriate logo from all surfaces | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/U2/repro.md`](evidence/U2/repro.md) | — |
| U3 | Simplify the primary creation flow and advanced controls | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/U3/repro.md`](evidence/U3/repro.md) | — |
| U4 | Re-run full browser suite after UI redesign | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/U4/repro.md`](evidence/U4/repro.md) | — |
| M7 | End-to-end production acceptance suite | CLAIMED-UNVERIFIED | Not established; no causal fix is authorized by this M0 evidence. | [`evidence/M7/repro.md`](evidence/M7/repro.md) | — |

## Supplemental reproduced issue

| ID | Title | Status | Root cause (`path:line`) | Evidence | Commit |
|---|---|---|---|---|---|
| UX-CHAT-01 | Recent Sessions falsely says there are no saved chats while the saved-session list is still loading | OPEN / BROKEN | `frontend/src/views/AgentStudioView.tsx:382,443-455,1708-1712` initializes the list empty and renders the final empty-state copy based only on `sessions.length` while the asynchronous project-state load is pending. | [`evidence/UX-CHAT-01/repro.md`](evidence/UX-CHAT-01/repro.md) | — |
