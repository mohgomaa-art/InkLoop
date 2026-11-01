# InkLoop Root-Cause Repair Audit

This folder tracks the user-provided repair mandate by issue ID. Statuses mean only what the recorded evidence supports. The M0 baseline is **in progress**, not complete.

## M0 snapshot

- 47 source-register rows created; P1 and P8 are `OPEN / BROKEN`, K3 was `NOT-REPRODUCED` in a mocked-API browser journey, and 44 remain `CLAIMED-UNVERIFIED`. The supplemental chat-hydration issue is also `OPEN / BROKEN`.
- Current isolated backend suite: 713 passed, 1 skipped; frontend TypeScript/Vite build passed; browser fixture journey: 2 passed.
- Registry inventory: 66 tools, 57 available/callable with adapters; six Agent skills and two system prompts fully read.
- No live image calls (0/80); no production images or canonical content were intentionally changed. The P1 GET probe may invoke lazy asset-registry initialization; see its evidence note and do not repeat it against the active store.

The real local Agent UI loaded the referenced project and restored seven nonempty sessions after hydration. During the wait, it falsely showed “No saved chats yet”; a deterministic delayed-session browser regression fails on that state. This is an empty-state/loading UX defect, not evidence that the stored transcripts were deleted.

P8 is separately reproduced in a mocked-API browser test: mouse and keyboard close/open controls work, but reload resets the closed sidebar to visible. P1's isolated endpoint contract test also shows missing and unknown project scopes return 200, while a valid project listing is filtered correctly. The historical P1 500 remains unexplained.

Read [`ledger.md`](ledger.md), [`coverage.json`](coverage.json), [`claims-audit.md`](claims-audit.md), [`tool-inventory.md`](tool-inventory.md), and [`handoff.md`](handoff.md) before continuing. M0 constraints and gaps are in [`open-questions.md`](open-questions.md). Evidence is in `evidence/<ID>/`.

## Executive answer

M0 has not yet established root causes for most reported failures. The local assets endpoint returned 200 for default, missing, and unknown project IDs; the historical 500 did not reproduce, but missing/unknown project scope currently has no route-level validation (`backend/app/api/routers/assets.py:56-83`). The editor image-edit browser test passed with generated landscape/portrait fixtures, but it mocked persistence. No issue is called fixed on that basis.
