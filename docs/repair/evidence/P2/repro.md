# P2 — Style analysis returned 502 and error feedback was not useful

Status: **CLAIMED-UNVERIFIED**.

## M0 baseline attempt

The isolated full backend baseline command `python -m pytest backend/tests -q --tb=short` completed with exit 0: 713 passed, 1 skipped, 2 deprecation warnings. The browser fixture suite completed with exit 0: 2 passed. Both outputs are recorded in [`../M0/repro.md`](../M0/repro.md).

Relevant baseline test/source inventory: backend/tests/test_p0_reliability_regressions.py; backend/tests/test_creative_director.py

Isolated focused run: `python -m pytest backend/tests/test_p0_reliability_regressions.py -q --tb=short` → **exit 0**, 17 passed in 3.35s. The tests force provider-unavailable and malformed/no-output boundaries; they do not call the live provider or reproduce the creator's exact provider payload.

## Current code trace

`backend/app/creative/analyzer.py:40-118` sends the verified image bytes to the configured vision endpoint, retries only HTTP 429/5xx and transport timeout/network failures, rejects empty/malformed structured output, and returns `AnalysisProviderError`. `backend/app/api/routers/creative.py:264-283` maps missing provider credentials to 503, provider/structure failures to 502, and invalid references to 422. `frontend/src/views/StyleCopierView.tsx:365-435` validates references, submits selected asset IDs, and displays the API error text in an “Analysis failed” toast. The saved style profile is written only after analysis returns successfully (`StyleCopierView.tsx:414-431`).

The screenshot's visible “invalid structured analysis” failure is consistent with the API's 502 mapping; it is not a successful fake analysis. The original provider response and exact payload are unavailable, so it is not established whether the provider response was malformed, incomplete for the response contract, truncated, or affected by some other transient response issue. The UI path offers no explicit retry action from this error state.

## Finding

The user-reported provider error was not reproduced against the live provider in this M0 run. The user's screenshot and request log are source evidence of a prior 502; the focused tests confirm current failure mapping for deterministic error fixtures. A passing test suite is not evidence that the provider response path is repaired. The status remains `CLAIMED-UNVERIFIED`; no live provider result or root cause is claimed.

## Required next evidence

Reproduce the actual reported route in the running UI or a deterministic regression that fails before the repair; preserve the request, state, screenshot/trace/log, and data scope. Then trace the complete caller-to-storage/provider path and test neighboring behaviors before editing.
