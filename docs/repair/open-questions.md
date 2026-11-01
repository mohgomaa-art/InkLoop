# Open Questions and External Blockers

## M0

- **Clean-checkout baseline unavailable from current Git state.** `repair/root-cause` was created from the existing `main` state, but the active app contains extensive untracked source and data; several runtime modules are absent from HEAD. A worktree at HEAD would not represent the running app. The current isolated test snapshot preserves the dirty workspace source while excluding `.git`, `.env`, installed dependencies and generated build output. Recommendation: keep the snapshot-based baseline and resolve repository ownership/tracking before attempting a clean-checkout build. No user input is needed to continue auditing.
- **Historical P1 500 not reproduced.** The running local instance returned HTTP 200 for the default project, missing `project_id`, and an unknown `project_id`. The route currently accepts an optional project ID and does not validate that a requested project exists (`backend/app/api/routers/assets.py:56-83`). The earlier 500's exact database state/log is unavailable. Keep the historical failure distinct from the currently observed unscoped-success behavior.
- **U1 reference asset not confirmed.** No new visual design will be invented. The supplied images in conversation are not yet located as repository assets in M0. If M6 cannot locate the required reference image in workspace/attachments, follow the mandate's U1 stop rule and request the exact asset.
- **Live provider verification is deferred.** M0 made zero live calls. If provider credentials are absent when controlled visual experiments are reached, document `BLOCKED(reason)` and keep all non-provider work moving; do not substitute a simulation for visual proof.

