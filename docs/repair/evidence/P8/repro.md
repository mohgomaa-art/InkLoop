# P8 — Sidebar state resets after reload

Status: **OPEN / BROKEN**.

## Root cause

`frontend/src/App.tsx:35` initializes `sidebarOpen` with `useState(true)` on each mount; the application does not read or persist the creator's prior sidebar state. Header and Sidebar buttons both mutate this state in memory at lines 151–157, so the close/open interaction works until reload.

## Reproduction

Test: `frontend/tests/test_sidebar_persistence.py::test_sidebar_mouse_and_keyboard_state_survives_reload`.

Command: `python -m pytest frontend/tests/test_sidebar_persistence.py -q --tb=short`.

Actual result: **exit 1**, 1 failed in 6.70s. The test closed the sidebar with its mouse close control, reopened it with keyboard Enter on “Open sidebar,” closed it with keyboard Enter on “Close sidebar,” confirmed it hidden, then reloaded. After reload the sidebar was visible; expected hidden. This reproduces the persistence defect while confirming the direct mouse/keyboard toggles work in this fixture.

Evidence: [`closed-before-reload.png`](20261031-070255/closed-before-reload.png), [`after-reload.png`](20261031-070255/after-reload.png), [`trace.zip`](20261031-070255/trace.zip), and browser video in the same directory. API is intercepted by a deterministic test fixture; no project writes occur.

Isolated re-run after increasing only the test's navigation timeout to tolerate cold Vite compilation: `python -m pytest frontend/tests/test_sidebar_persistence.py -q --tb=short` → **exit 1**, 1 failed in 9.94s. It reached the post-reload assertion and reproduced the same visible sidebar reset. New evidence is under [`20261031-071537/`](20261031-071537/). This removes the navigation-timeout ambiguity from the earlier aggregate test run.

## Alternatives and blast radius

- Rejected: leave the state in memory and restore it only when the Agent child mounts; the sidebar is owned by the top-level `App`, so this would not survive application reload.
- Candidate repair: persist the sidebar preference in a namespaced local UI preference and hydrate it in `App` before rendering. Keep mouse, keyboard, narrow-width layout, and project switching behavior unchanged.
- Blast radius: top-level application shell and all routes. The preference must not be coupled to project IDs or conversation state.

## Acceptance

This test passes after the repair; default first-run behavior remains open when there is no saved preference; close via mouse and keyboard remains operable; saved hidden/open state survives full reload; narrow viewport and editor layout remain valid.
