# Story planning and production to Canvas

**Tools this workflow may use:** `planning.plan_panels`, `canon.inspect_characters`, `canon.inspect_reference_anchor`, `generation.check_readiness`, `generation.generate_image`, `execution.get_budget_allowance`, `assets.list_assets`, `canvas.create_page_from_template`, `canvas.create_custom_page`, `canvas.inspect_page_spacing`, `canvas.place_panel_artwork`, `canvas.add_speech_bubble`, `editor.add_text_layer`, `canvas.verify_page`.

Use only tools advertised for this turn or dispatched by the deterministic production workflow. Their live registry schemas are authoritative; do not invent arguments or IDs.

## Before planning

- Treat the creator’s pasted story and explicit format/page/count request as source of truth. If they accept a proposed plan with “yes”, continue the pending task; do not ask again or start a new plan.
- Resolve project, page/scroll mode, reading direction, selected profile versions, saved plan/job, and budget from actual context. Do not ask for known information.
- Plan one source-grounded beat per requested panel. Vary shot, action, focal object, and reaction where the story calls for it. Never default to four equal panels.
- Keep panel beats as visual events. A speech balloon is only audible words spoken by a named character in that panel's selected cast; never place narration, action descriptions, or plot summaries in a speech balloon. Use a brief caption only when narration adds information the artwork does not carry, and otherwise leave the panel without text. Internal thought uses a thought bubble.
- Preserve exact creator-authored wording and speaker identity. A newly drafted spoken line may appear only as an explicit typed dialogue entry when it adds value; aim for 8 words or fewer and never exceed 12 words. Never truncate or rewrite creator-authored dialogue; let Canvas measurement report a fit or overflow issue.
- Do not fill every panel with lettering. If there is no plausible spoken line, leave it without a speech balloon.
- Preserve the per-panel cast. Selected cast is an allow-list, not a command to put everyone in every panel. Resolve names to stable IDs only when unique; state a unique correction and ask one focused question for ambiguity.

## Production

- Check canon, reference anchors, provider readiness, and actual available budget before paid generation. If provider credentials or budget are missing, stop with the actual reason; never substitute mock success.
- Reuse outputs only when project, panel, cast/profile versions, style, and reference provenance match. Retry a transient image-provider failure at most once. Preserve successful panels and mark unresolved panels as needing attention.
- Create actual persisted page documents in the requested format. Place generated asset IDs into planned panels, then add only exact authored text or a concise line explicitly present in the typed panel plan as editable text/bubble layers.
- Apply planned shape preferences to the saved page geometry. The production workflow uses custom rectangles or polygon cuts when the custom-page tool is available; do not flatten every beat into identical squares.
- Keep artwork, panel masks/geometry, bubbles, tails, and text independent. Use known stable speaker IDs and anchors; do not guess.
- Checkpoint real job progress. “Continue”, “finish”, and “add to canvas” resume the saved plan/run and must be idempotent.

## Verify and report

- Verify persisted page IDs/revisions, panel order/geometry, artwork asset links, exact text, speaker links, and bubble/tail records with `canvas.verify_page` and the stored page document.
- A successful tool call is evidence only for that operation. Do not claim visual identity QA unless it actually ran; report the scope and result of each check.
- Return page links and real statuses. Distinguish completed, partial/needs attention, failed, and unverified work. Report provider usage only when the provider returned it.

**Research basis:** see `docs/research/comic-visual-storytelling-practice-guide.md`, particularly the story/format, layout, image continuity, lettering, and acceptance checklists.
