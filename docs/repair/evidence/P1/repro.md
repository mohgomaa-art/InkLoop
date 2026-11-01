# P1 — Asset list project scope and reported 500

Status: **OPEN / BROKEN** for the currently observed missing/unknown-scope behavior. The specifically reported `default_project` HTTP 500 was **not reproduced**.

## Attempts and result

Read-only requests to the already-running local API on port 8000:

- `GET /api/v1/assets?project_id=default_project` → HTTP 200.
- `GET /api/v1/assets` → HTTP 200 (missing project scope).
- `GET /api/v1/assets?project_id=m0_unknown_project` → HTTP 200 (unknown project scope).

These requests did not print or retain asset response bodies. The first GET may initialize the API's lazy registry; this router calls `get_registry()` at `backend/app/api/routers/assets.py:64`, whose initializer can create the registry directory and seed an asset at lines 25–53. Therefore this was not a strictly side-effect-free probe, and no more GET requests are planned for M0. The local server was not stopped or restarted.

## Current root-cause finding

The route declares `project_id: Optional[str] = None` at `backend/app/api/routers/assets.py:56-60`, then passes the optional value directly to `AssetFilter` at lines 75–82 and returns the registry result at line 83. There is no required-scope or project-existence validation in this route. That explains why missing/unknown IDs produce successful responses on this instance; it does **not** establish why another instance returned 500 for `default_project`.

## Evidence boundary

The complete backend suite passes on an isolated workspace snapshot: 713 passed, 1 skipped. Relevant files include `backend/tests/test_assets_upload.py` and `backend/tests/test_api.py`, but no test in the suite was shown to reproduce the historical 500. Exact historical DB state and server traceback are unavailable.

## Next investigation

Before a P1 fix, trace project enumeration/ownership, registry filtering, and app startup against fresh, existing, and unknown IDs in an isolated DB. Add explicit endpoint contract regressions for missing ID, unknown ID, and existing ID. Preserve the active database; do not migrate it during M0.

## Isolated project-scope regression (pre-fix)

Test file: `backend/tests/test_asset_list_project_scope.py`. The test creates two temporary projects with valid Story Bibles and a fresh temporary asset registry; it never accesses `runs/` in the active workspace.

Command: `python -m pytest backend/tests/test_asset_list_project_scope.py -q --tb=short`.

Actual result before any product change: **exit 1**, 2 failed and 1 passed in 8.21s. Missing `project_id` returned HTTP 200 instead of the required 422; an unknown project returned HTTP 200 instead of typed 404 (`ERR_PROJECT_NOT_FOUND`). Listing a valid project returned only its registered asset and passed. This proves the endpoint scope-contract defect independently of the historical 500.

The current defect is caused by `project_id: Optional[str] = None` and the absence of any project-existence lookup before `get_registry().list_assets(...)` in `backend/app/api/routers/assets.py:56-83`. A correction must require the query parameter and verify the corresponding existing Story Bible without using `list_projects()` (which creates `default_project` when no projects exist). It must preserve registry filtering, reject malformed or mismatched project Bibles explicitly, and avoid returning an empty successful list for unknown projects. The reported `default_project` 500 remains unexplained and must not be described as fixed by this contract change.

## Caller and compatibility trace

`frontend/src/api/client.ts:213-220` serializes the project ID only when provided. The current unscoped call is intentional in several asset-picker/library paths: `frontend/src/views/AssetLibraryView.tsx:42`, `StyleCopierView.tsx:131,328`, and `CharacterCopierView.tsx:95,299`. Those views currently consume assets across projects (then apply local trust/project filters where applicable). Project-scoped callers already pass the active ID: `AgentStudioView.tsx:449`, `ManualEditorView.tsx:188`, `ObjectStudioView.tsx:63`, and `VerificationLabView.tsx:54`.

This makes a bare “make `project_id` required” edit incomplete: it would break existing global-library callers. Candidate A is to keep implicit global listing and validate only non-empty supplied IDs; rejected because omission remains ambiguous and cannot satisfy the required missing-parameter contract. Candidate B is an explicit scope contract: require either one validated `project_id` or an explicit global-library scope, reject conflicting/missing scope, and update each unscoped caller after confirming its intended library behavior. This preserves the library while preventing an accidental omission from widening a request. The P1 test currently captures the requested strict project-scope contract and should be extended for the explicit global-library path before the eventual fix.
