# Repair Decisions

## M0

1. Work branch is `repair/root-cause`; existing dirty and untracked work is preserved.
2. The active workspace is not a clean checkout. The current application includes substantial untracked source, including Agent, API, Canvas, and frontend modules. HEAD does not contain all files required to run this exact application. M0 therefore uses an isolated snapshot of the workspace and clearly labels it as a snapshot, not a clean checkout.
3. Backend tests run against the isolated copy because current tests write beneath `PROJECT_ROOT/runs/`; the active workspace contains user project assets and databases. No backend test suite was run against the active project store.
4. The browser test uses deterministic programmatically generated fixtures and intercepts API requests. It verifies the current frontend editor interactions, not server-authoritative persistence or a full live Agent journey.
5. No paid provider/image-generation calls are made during M0. The live image-call counter is 0/80.
6. No source image, Canon, Story Bible, generated artwork, or existing chat was changed by the M0 audit. Browser artifacts were written only under `docs/repair/evidence/`. The read-only P1 GET may call lazy registry initialization; its DB file already existed, and no later probe was made.
7. Do not commit application or test files from the pre-existing dirty/untracked tree until their ownership and dependency boundary is understood. M0 documentation is being prepared separately; no commit has yet been created.

## Prompt findings recorded without changing behavior

`model_client.py` composes the Agent's system instructions inline. The block repeats directive numbering (`2`, `12`) and combines a general material-ambiguity question rule with a later production rule saying not to stall for story requests. The rules also rely on downstream deterministic validation for page counts and speaker scope. These are investigation leads, not a root-cause finding for any reported issue.
# P1 asset-list scope decision

- Keep the reported historical `default_project` 500 unassigned: the active server returned 200 and no historical traceback is available.
- Treat missing and unknown scope as a demonstrated contract defect, but preserve explicit global asset-library use. Before implementation, introduce an explicit global-library scope or a dedicated global route and migrate the three unscoped frontend callers (`AssetLibraryView`, `StyleCopierView`, and `CharacterCopierView`). Do not silently let an omitted scope enumerate every project.
- Project validation must use non-mutating Story Bible lookup; do not call `GET /projects` or `list_projects()` from this route because the latter creates `default_project` when the project set is empty.
- P1 pre-fix regression uses `pytest tmp_path`; the active artifact database is not touched.
