# M0 Baseline and Reproduction Evidence

Date: 2026-10-31 (local workspace date; test-run timestamps are recorded in the evidence directory names). Branch: `repair/root-cause`.

## Workspace and environment

- Working tree was already extensively modified/untracked before this audit; no cleanup or reset was performed. `git status --short --branch` captured branch `repair/root-cause` and the existing changes. HEAD does not contain multiple runtime directories required by the current application.
- Python 3.12.10; Node v24.21.0; npm 11.19.0; Vite 6.4.5.
- Existing local API process at `127.0.0.1:8000`; no server restart or stop was performed.
- Provider/image calls: 0 of 80. No secrets were read or printed.

## Commands and actual results

| Command | Environment | Result |
|---|---|---|
| `npm run build` | `frontend/` in active workspace | Exit 0; TypeScript and Vite build succeeded. Vite emitted a non-failing >500 kB chunk warning. |
| `python -m pytest frontend/tests/test_editor_image_editing.py -q --tb=short` | Active workspace | Exit 0; 2 passed in 18.80s. Artifacts: `evidence/M0/ui/20261031-063908/{before.png,after.png,trace.zip,video/}`. API is fully intercepted by Playwright. |
| `python -m pytest backend/tests -q --tb=short` | Isolated workspace snapshot, first run with `.git` and built `frontend/dist` intentionally excluded | Exit 1; 711 passed, 1 skipped, 2 failed. Both failures were environment omissions: static SPA test got 404 because `dist` was excluded; gitignore test returned 128 because `.git` was excluded. |
| `git init` + copy built `frontend/dist` | Isolated snapshot only | `git check-ignore .env` returned `.env` with exit 0. No active workspace Git metadata was touched. |
| `python -m pytest backend/tests -q --tb=short` | Same isolated snapshot after supplying the omitted test environment artifacts | Exit 0; 713 passed, 1 skipped, 2 deprecation warnings in 45.60s. |
| Read-only `GET /api/v1/assets` variants | Existing API on port 8000 | `default_project`: 200; missing `project_id`: 200; unknown `project_id`: 200. This did not reproduce the reported default-project 500, and it exposed a separate scope-validation concern (see P1 evidence). |
| Headless Playwright on `#/agent` with the local API | Existing project ID `last_oneee_b36304f4`; all non-GET/HEAD calls blocked | 47–49 API GET responses were HTTP 200, no page errors or mutation requests. Direct API summary: 7 nonempty sessions. Initial capture showed the empty-state message; after waiting for hydration, the session list and selected transcript were present. See `evidence/M0/ui/live-api-smoke/`. |
| `python -m pytest frontend/tests/test_agent_session_hydration.py -q --tb=short` | Deterministic test-only saved session and 1.8s fetch delay | Exit 1, 1 failed in 7.47s: the test reproduced “No saved chats yet” while the saved session list was pending. Screenshot and trace are recorded under `evidence/A7/session-hydration/20261031-065930/`. This is supplemental issue `UX-CHAT-01`; it is a frontend test fixture and no production session is used. |
| `python -m pytest frontend/tests/test_sidebar_persistence.py -q --tb=short` | Deterministic mocked API, mouse close, keyboard reopen/close, then page reload | Exit 1, 1 failed in 9.94s: sidebar reappears after reload. Evidence: `evidence/P8/20261031-070255/`. |
| `python -m pytest backend/tests/test_asset_list_project_scope.py -q --tb=short` | Fresh project Bibles and asset registry under pytest `tmp_path` | Exit 1, 2 failed and 1 passed in 8.21s: missing scope and unknown project both return HTTP 200; valid project filtering passes. Evidence and root cause boundary: `evidence/P1/repro.md`. |
| `python -m pytest frontend/tests/test_editor_missing_page.py -q --tb=short` | Vite browser fixture; all API calls intercepted and missing-page GET returns fixture HTTP 404 | Exit 0, 1 passed in 5.54s. Error text rendered and the reported JavaScript `before` initialization error did not occur. React StrictMode issued two requests, both 404. Evidence: `evidence/P3/20261031-072438/`. This does not reproduce the original user-specific data/navigation sequence. |
| `python -m pytest backend/tests/test_story_bible_crud_api.py backend/tests/test_editable_page_store.py -q --tb=short` | Isolated snapshot only; project CRUD tests delete only projects they create, page-store tests use `tmp_path` | Exit 0, 14 passed in 4.37s. This is baseline coverage for project CRUD/canon and store revision/order behavior, not proof that all reported UI persistence symptoms are fixed. |
| `python -m pytest frontend/tests/test_editor_image_editing.py -q --tb=short` | Deterministic orientation fixtures; API routes intercepted by the test | Exit 0, 2 passed in 21.65s after increasing only the test navigation timeout to tolerate cold Vite module compilation. This does not test real backend persistence or export parity. |
| `python -m pytest frontend/tests/test_agent_session_hydration.py -q --tb=short` | Deterministic delayed saved-session response; API fixture only | Exit 1, 1 failed in 7.21s at the false-empty-state assertion. The 30-second navigation allowance eliminates the prior navigation-timeout noise; reproduced defect is unchanged. |
| `python -m pytest frontend/tests/test_sidebar_persistence.py -q --tb=short` | Deterministic API fixture; mouse and keyboard transitions followed by reload | Exit 1, 1 failed in 9.94s at the post-reload visibility assertion. The 30-second navigation allowance eliminates the prior navigation-timeout noise; reproduced defect is unchanged. |
| `python -m pytest backend/tests/test_p0_reliability_regressions.py -q --tb=short` | Isolated workspace snapshot, provider calls intercepted/injected in tests | Exit 0, 17 passed in 3.35s. Includes truthful provider-unavailable, invalid/empty-response and exact attached-byte boundary checks; does not establish live-provider behavior. |
| Initial aggregate `python -m pytest frontend/tests -q --tb=short` | Browser test harnesses with Vite startup and 5-second default navigation timeout | Exit 1; three browser tests timed out during page navigation before reaching their behavioral assertions. The test-only navigation allowance was raised to 30 seconds; subsequent individual runs are recorded above and reached the actual expected assertions. |
| `python -m pytest frontend/tests/test_sidebar_persistence.py -q --tb=short` | Deterministic mocked API, close by mouse, open/close by keyboard, then reload | Exit 1, 1 failed in 6.70s: sidebar is visible after reload although it was hidden before reload. Evidence: `evidence/P8/20261031-070255/`. |
| `python -m pytest backend/tests/test_asset_list_project_scope.py -q --tb=short` | Fresh project Bibles and asset registry under pytest `tmp_path` | Exit 1, 2 failed and 1 passed in 8.21s: missing scope and unknown project both return HTTP 200; valid project filtering passes. Evidence and root cause boundary: `evidence/P1/repro.md`. |

## Browser evidence scope

The test generated 300×200 and 200×300 RGB fixtures with four colored corner markers, labels, gradients, and an asymmetric arrow. It verified source dimensions/aspect ratios, click selection, double-click edit mode, full source bounds outside the mask, scale, rotation, drag, deselection, saved revision under the mocked API, reload, and the resulting transform. This is a deterministic frontend interaction check. It is not a real storage/API round-trip and does not prove export parity. Historical before-failure evidence was unavailable, so the user-reported defect remains `NOT-REPRODUCED` rather than fixed.

## Current findings

- P1 historical 500: not reproduced. Current missing/unknown project query behavior returns 200; exact response asset counts were not recorded in this pass. `backend/app/api/routers/assets.py:56-83` accepts an optional project ID and passes it directly to the registry filter.
- K3 image edit geometry symptom: not reproduced by the current Playwright UI path; no prior failing screenshot for this run. The source-level application fix, if any, remains unverified against the historical session.
- `UX-CHAT-01`: reproduced. `frontend/src/views/AgentStudioView.tsx:382,443-455,1708-1712` uses an empty array for both “still loading” and “confirmed no saved chats.” The real project restored its seven conversations after hydration; the UI falsely reported none in the interim.
- `P8`: reproduced. `frontend/src/App.tsx:35` initializes the sidebar as open on every mount and does not persist the user's preference; mouse and keyboard toggles work, but reload loses the hidden state.
- P1 route contract: an isolated regression reproduces missing/unknown project scope returning 200 while valid project filtering works. This is separate from the historical default-project 500, whose cause remains unknown.
- P1 caller trace found three unscoped global-library consumers (`AssetLibraryView`, `StyleCopierView`, `CharacterCopierView`) plus four project-scoped callers. A project-only route change must update the unscoped API contract/callers together or it will break asset browsing; see `evidence/P1/repro.md` and `decisions.md`.
- P2 deterministic failure boundaries are covered by 17 passing tests in `test_p0_reliability_regressions.py`. They confirm error mapping and no-fake-success behavior under fixtures; the exact user screenshot's provider response was not captured in this run and live provider analysis was not invoked.
- P4 baseline API CRUD and P5–P7 page-store persistence/revision/list/delete-recovery paths passed their current deterministic tests in the isolated snapshot (14 passed). These tests do not establish the requested real-browser save/reopen flow, multi-step undo integration, or transactional page reorder against the live application; those subclaims remain unverified.
- Other issues remain claims until their exact user-visible path and variants are exercised. The complete 47-item ledger records the current evidence boundary; passing unit/integration tests are not being promoted to real-UI verification.

