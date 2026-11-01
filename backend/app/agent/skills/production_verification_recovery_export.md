# Production verification, recovery, and export

**Callable tools:** `canvas.verify_page`, `image.verify_visual_consistency`, `assets.verify_file_integrity`, `verification.inspect_report`, `execution.get_budget_allowance`, `export.generate_comic_book`.

Use only registered callable tools. Verify at the level each tool actually supports; do not imply a visual check from a structural check.

- Before continuing, inspect saved plan/job checkpoints, existing pages/assets, revisions, and budget. Reuse compatible successful work and avoid duplicate calls/spend.
- Resume from the last confirmed checkpoint. Keep completed panels/pages intact; identify missing or failed work separately. Retry only safe transient failures under the run’s retry and budget controls.
- Structural page verification covers only its reported document properties. Image integrity, visual identity, story coherence, typography/rendering, and export each need their corresponding actual check.
- If a verifier is unavailable, errors, or cannot assess a property, report that property as unverified—not passed.
- Before export, validate requested format, page order, dimensions, reading direction, art links, text/bubble records, fonts, and output package. Do not publish externally unless explicitly authorized.
- Return actual output IDs/links, revision, status, warnings, provider usage when returned, and exact blockers. Distinguish completed, partial, failed, and unverified work.
- `execution.run_crash_recovery` and `creative.validate_coherence` are registered but currently lack callable adapters. Do not report them as run; use persisted checkpoints and available page/image verifiers, and disclose any remaining verification gap.

**Research basis:** see the practical page-completion checklist and the report’s limits/cautions.
