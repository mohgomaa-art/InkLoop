# UX-CHAT-01 — False empty state while saved sessions load

Status: **OPEN / BROKEN**.

## Root cause

The Recent Sessions list initializes as `[]` at `frontend/src/views/AgentStudioView.tsx:382`, and the UI renders “No saved chats yet” solely when that array is empty at lines 1708–1712. The session list is not assigned until the project-state `Promise.all` finishes at lines 443–455 and `setSessions` runs around line 537. There is no loading state distinguishing an unresolved request from a confirmed empty list.

## Reproduction — failing deterministic browser regression

Test: `frontend/tests/test_agent_session_hydration.py::test_saved_sessions_are_not_reported_missing_while_hydrating`.

Command: `python -m pytest frontend/tests/test_agent_session_hydration.py -q --tb=short`.

Actual result: **exit 1**, 1 failed in 7.47s. The test delays the project session-list response by 1.8 seconds; the response contains one saved session with a nonempty transcript. Before it arrives, the UI renders the false empty-state message, failing the assertion that the list must not claim no chats exist while loading.

Failure evidence: [`before.png`](../A7/session-hydration/20261031-065930/before.png), [`trace.zip`](../A7/session-hydration/20261031-065930/trace.zip), and test video in the same run folder. No production image, project, or session is used by this deterministic test.

Isolated re-run after increasing only the test navigation timeout: `python -m pytest frontend/tests/test_agent_session_hydration.py -q --tb=short` → **exit 1**, 1 failed in 7.21s at the same false-empty assertion. The delayed saved-session fixture is still returned and the bug is independently reproduced. Latest screenshot/video evidence is under [`20261031-071528/`](20261031-071528/); the failure occurs before the test's trace-finalization line, so this run has no `trace.zip`.

## Real project variant

Headless Chromium opened the live UI with read-only API requests for the project ID supplied in the conversation (`last_oneee_b36304f4`). The API reported **7 nonempty sessions** (message counts: 25, 12, 8, 4, 4, 4, 4). A screenshot taken before hydration showed “No saved chats yet”; after waiting for hydration, the saved session list and selected transcript appeared. The hydrated state is captured in [`agent-last-oneee-hydrated.png`](../M0/ui/live-api-smoke/agent-last-oneee-hydrated.png); the earlier empty state is [`agent-last-oneee.png`](../M0/ui/live-api-smoke/agent-last-oneee.png). There were no page errors and no mutation requests. The project records were not altered.

This establishes a temporary false-empty UI state and delayed restoration on that browser/API path. It does not establish transcript deletion or explain a case where the list remains empty after the session API returns.

## Alternatives and blast radius

- Rejected: leave the empty message in place and rely on the data eventually arriving. This is the reproduced misleading state.
- Candidate repair: keep per-project loading/error/empty states distinct; show a neutral loading message or skeleton until the matching project session query resolves, preserve existing visible sessions during a project switch until the new project result is ready, and show an explicit error on request failure. No REST or persistence schema change is needed.
- Blast radius: Agent Studio project switching and session hydration only; ensure current selected session, transcript cache, and pending activity recovery remain intact.

## Acceptance

The failing test passes with delayed session-list responses; a truly empty successful response shows the empty message only after completion; a failed response shows an error/retry state, not empty success. Real-project reload restores sessions and transcript without a false empty state or losing a pending activity. Retest fast and slow responses and rapid project switching.
