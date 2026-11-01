# Canvas page layout and editing

**Tools this workflow may use:** `canvas.list_templates`, `canvas.generate_layout`, `canvas.search_panel_layout_presets`, `canvas.create_page_from_template`, `canvas.create_custom_page`, `canvas.inspect_page_spacing`, `canvas.switch_page_template`, `canvas.reshape_panel`, `canvas.place_panel_artwork`, `canvas.assemble_full_page`, `canvas.verify_page`, `editor.list_pages`, `editor.get_page`, `editor.add_image_to_panel`, `editor.update_image_placement`, `editor.reshape_panel`, `editor.add_line_layer`, `editor.update_vector_layer`.

Read actual page/project/revision context first. Use live schemas; do not invent IDs. Mutate the persisted page document used by the editor, not a parallel representation.

- Match format and reading direction explicitly: paged manga/comic, vertical-scroll episode, graphic-novel page, or storybook spread. A format preset is an editable start, not a locked rule.
- Derive panel count and sizes from the story beats. Avoid fixed four-panel pages or repeated equal grids unless requested or narratively useful.
- When a new page should be drawn freely, call `canvas.create_custom_page` with normalized rectangles or polygon cuts; use story shape preferences to vary panel proportions, and use `canvas.reshape_panel` for later edits. Do not describe a preset grid as hand-scratched geometry.
- When asked about spacing, call `canvas.inspect_page_spacing` on the saved page. It measures the actual rectangle/polygon edge gaps, margins, and configured gutters; never infer the saved measurements from a preview.
- Keep panel geometry/masks separate from art assets and image transforms. Place/replace/fit/scale artwork inside the correct panel without changing unrelated layout.
- Preserve intended reading order and validate it, particularly for RTL pages, diagonal panels, insets, overlaps, and irregular shapes.
- Keep gutters and negative space intentional. In scroll mode, use vertical distance only when it controls pause, reveal, transition, or emotional rhythm.
- Use the current page revision for each edit. Reject stale or out-of-scope operations; do not silently overwrite newer work.
- Before destructive removal, identify exact target IDs and use available approval/undo behavior. Preserve source assets.
- Verify persisted page ID, revision, panel count/order, geometry, placements, and validation warnings after mutation. Return real page links and results.

**Research basis:** see the format comparison and layout/flow sections of the cited practice guide.
