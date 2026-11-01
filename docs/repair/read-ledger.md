# M0 Read Ledger

Scope: files required to understand the current Agent, Canvas, image, and verification pathways. `Fully read` means the entire named file was read in this M0 pass; `Partially read` means only named sections were inspected. No claims are made about unread code.

| File | Status | Notes |
|---|---|---|
| `backend/app/agent/skills/canvas_layout_and_editing.md` | Fully read | Tool scope, edit rules, revision handling, layout and spacing verification. |
| `backend/app/agent/skills/character_style_continuity.md` | Fully read | Canon identity, selected cast, reference provenance and limits. |
| `backend/app/agent/skills/image_generation_and_verification.md` | Fully read | Provider, reference, budget, retry and truthfulness rules. |
| `backend/app/agent/skills/lettering_bubbles_typography.md` | Fully read | Text kinds, speaker scope, placement, font and Arabic limitations. |
| `backend/app/agent/skills/production_verification_recovery_export.md` | Fully read | Persisted checkpoints, recovery and verification scope. |
| `backend/app/agent/skills/story_to_canvas.md` | Fully read | Planning-to-Canvas sequence and production constraints. |
| `backend/app/agent/model_client.py` | Partially read | Entire dynamically composed system-instruction block at lines 297–355 and adjacent message construction through image/document attachment handling were read. Rest of client not audited. |
| `backend/app/verification/l2_judge.py` | Partially read | Full `JUDGE_SYSTEM_PROMPT` and `build_judge_prompt` read; judge transport and response parsing not audited. |
| `backend/app/agent/registry.py` | Partially read | Registry initialization/list/dispatch (lines 377–475), registered adapter inventory, and selected adapter code read. Full adapters not read. |
| `backend/app/agent/schemas.py` | Partially read | Tool contract definitions and Agent plan/attachment/usage schemas read. Rest of schemas not audited. |
| `backend/app/api/routers/assets.py` | Partially read | `get_registry` and asset-list route (lines 17–87) read for P1; remaining routes not audited. |
| `backend/app/api/routers/creative.py` | Partially read | Style-analysis endpoint and provider-error mapping (lines 264–283) read for P2; other endpoints not audited. |
| `backend/app/creative/analyzer.py` | Partially read | Vision transport, JSON parsing, StyleAnalyzer validation and reference resolution (lines 1–310) read for P2; remaining character/object analyzers not fully audited. |
| `backend/app/storage/models.py` | Partially read | Asset registry models and filter contract inspected for P1; remaining model fields not fully audited. |
| `frontend/src/views/ManualEditorView.tsx` | Partially read | Page-load/error path and `drag.before` access sites inspected for P3; full editor behavior not audited. |
| `frontend/src/App.tsx` | Partially read | Sidebar state initialization, shell toggles and project initialization inspected for P8; remaining routing behavior not audited. |
| `backend/app/config.py` | Fully read | Project-root resolution, provider credential presence property and safe key masking. No secret value was read or printed. |
| `frontend/tests/test_editor_image_editing.py` | Fully read | Current programmatic image fixtures and Playwright journey. Backend calls are intercepted by the test route. |
| `frontend/tests/test_agent_session_hydration.py` | Fully read | Deterministic slow-session browser regression. API responses are fixture-only. Navigation timeout increased to 30 seconds for cold Vite compilation. |
| `frontend/tests/test_sidebar_persistence.py` | Fully read | Deterministic mouse/keyboard/reload browser regression. API responses are fixture-only. Navigation timeout increased to 30 seconds for cold Vite compilation. |
| `backend/tests/test_asset_list_project_scope.py` | Fully read | New pre-fix isolated API regression; creates test projects/asset registry under pytest `tmp_path`. |
| `frontend/tests/test_editor_missing_page.py` | Fully read | Test-only deep-link 404 regression; Vite browser fixture intercepts all API requests and records screenshot, trace, and video. |
| `frontend/src/main.tsx` | Fully read | Confirmed React.StrictMode wrapper, which replays effects in development and explains duplicate GETs in the missing-page fixture. |
| `backend/app/api/routers/projects.py` | Partially read | Project-list fallback and read/write helpers inspected for P1; remaining routes not audited. |
| `backend/app/project/bible.py` | Partially read | StoryBible model, path resolver, load/save functions, and canonical-bible factory inspected for P1. |
| `backend/app/storage/registry.py` | Partially read | Registry initialization, ingestion and list/filter call path inspected for P1. |
| `backend/app/storage/registry_db.py` | Partially read | SQLite table initialization and list filtering inspected for P1. |
| `frontend/src/api/client.ts` | Partially read | `listAssets` query serialization inspected for P1; remaining API methods not audited. |
| `frontend/src/views/AssetLibraryView.tsx` | Partially read | Asset list call and current project usage inspected for P1. |
| `frontend/src/views/StyleCopierView.tsx` | Partially read | Initial and post-upload asset listing call sites inspected for P1. |
| `frontend/src/views/CharacterCopierView.tsx` | Partially read | Initial and post-upload asset listing call sites inspected for P1. |
| `frontend/package.json` | Fully read | Build/lint scripts and dependencies. |
| `backend/tests/conftest.py` | Fully read | Tests force offline mode and blank provider keys; full tests run only on an isolated snapshot. |
| `.agents/**` | Not inventoried as skills | Collaboration metadata, not a `SKILL.md` package. |

No `fullstack-deep-read` skill was available in the environment. No `AGENTS.md` or additional repository `SKILL.md` was found by the M0 scoped discovery command.
