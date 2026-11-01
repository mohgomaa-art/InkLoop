# Repair Handoff — M0 in progress

Last updated: 2026-10-31. Work branch: `repair/root-cause`.

## Read this first after a context reset

1. `docs/repair/handoff.md`
2. `docs/repair/ledger.md`
3. `docs/repair/open-questions.md`
4. `docs/repair/evidence/M0/repro.md`

## Current position

M0 baseline artifacts now exist: issue ledger and evidence directories, tool inventory, read ledger, claims audit, test/browser evidence, and decision/open-question notes. No feature code has been changed in the M0 pass. Active workspace user changes and databases remain intact.

Backend full suite passed only in an isolated snapshot after supplying `.git` and the previously built `frontend/dist`: 713 passed, 1 skipped, exit 0. Browser test passed 2 cases but intercepts API requests. Frontend build passed with a non-fatal chunk-size warning. Existing app server was not restarted.

P1's historical 500 is not reproduced. The current GET endpoint accepts missing and unknown project IDs and returns 200; route validation root cause is visible at `backend/app/api/routers/assets.py:56-84`. Do not conflate these findings. K3 editor transform report was not reproduced in the current frontend test; persistence/export remain untested.

The real local Agent UI loaded seven nonempty sessions for `last_oneee_b36304f4` and restored its selected transcript, but initially displayed “No saved chats yet.” The cause is verified at `frontend/src/views/AgentStudioView.tsx:382,443-455,1708-1712`: empty list state is presented as a final empty result before the async load resolves. A deterministic test-only delay reproduces it and fails as expected; screenshot and trace are in `evidence/A7/session-hydration/20261031-065930/`. Track this as supplemental issue `UX-CHAT-01`; no feature fix has been made in M0.

P8 is reproduced independently: sidebar close works by mouse, reopening/closing works by keyboard activation, but reload resets the hidden sidebar to visible. `frontend/src/App.tsx:35` initializes `sidebarOpen` to `true` on mount and never persists it. The failing browser regression and screenshots are in `evidence/P8/20261031-070255/`.

P1 now has a deterministic isolated regression at `backend/tests/test_asset_list_project_scope.py`: two cases fail before product changes (missing scope and unknown project return 200); valid-project asset filtering passes. Its temporary Story Bibles, registry, and assets are all under pytest `tmp_path`. The historical 500 is still unverified.

## Next authorized work

Continue the M0 issue-by-issue reproduction pass, preserving a screenshot/trace/log for UI-visible defects and using isolated data for DB-writing tests. Inspect each test's side effects before running it against any workspace. M0 has not met its gate: the majority of issue rows still lack direct symptom reproduction and historical fixes remain unverified. Do not change product code until the remaining M0 reproduction/evidence work is reconciled. No provider image calls without an issue-specific reason and cost entry.

## Workspace caveat

A clean checkout at HEAD does not include all current app modules. Do not clean/reset, stage unrelated untracked files, or use the active production databases to create an artificial clean test. No commit was created in M0; preserve this caveat when deciding what can safely be committed.
