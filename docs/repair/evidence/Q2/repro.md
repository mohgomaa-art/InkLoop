# Q2 — Panel events, story provenance, and repetition intent

Status: **CLAIMED-UNVERIFIED**.

## M0 baseline attempt

The isolated full backend baseline command `python -m pytest backend/tests -q --tb=short` completed with exit 0: 713 passed, 1 skipped, 2 deprecation warnings. The browser fixture suite completed with exit 0: 2 passed. Both outputs are recorded in [`../M0/repro.md`](../M0/repro.md).

Relevant baseline test/source inventory: backend/tests/test_panel_planner.py; backend/tests/test_panel_plan_recovery.py

## Finding

The user-reported symptom was not reproduced as a distinct failure in this M0 run. A passing test suite is not evidence that a previous failure is fixed; this status remains `CLAIMED-UNVERIFIED` until the exact path, user data state, and required UI variants are reproduced. No root cause or implementation change is claimed.

## Required next evidence

Reproduce the actual reported route in the running UI or a deterministic regression that fails before the repair; preserve the request, state, screenshot/trace/log, and data scope. Then trace the complete caller-to-storage/provider path and test neighboring behaviors before editing.
