# B2 text limits and measured layout

`backend/app/text/lettering_layout.py` now lays out bubble lettering from the canonical type registry. It measures the selected font with Pillow after Arabic shaping, wraps without removing authored words, keeps Arabic direction RTL, and uses each type's font range and line cap. `font_path` supports a verified project font when a caller supplies its resolved path.

Word-limit violations raise `LetteringValidationError` with stable `code` and `details` (`type_id`, `word_count`, `word_limit`). Agent tool failures return those details in the structured tool result. If the minimum font still cannot fit, layout returns an explicit `ERR_LETTERING_MIN_FONT_OVERFLOW` or `ERR_LETTERING_LINE_LIMIT` diagnostic while preserving the original text; strict Agent bubble creation fails with that diagnostic. The persisted bubble stores the measured lines and layout metadata for editor/export parity work in B7.

The two dialogue-condensing paths are removed from panel-plan recovery and registry normalization. Over-limit planned wording is preserved and flagged for editing/splitting; it is never silently rewritten.

Verification command:

```text
python -m pytest backend/tests/test_bubble_registry.py backend/tests/test_lettering_layout.py backend/tests/test_panel_plan_recovery.py -q --tb=short
```

Result: **39 passed**. Coverage includes every type's word-limit boundary, active-font metrics, Arabic shaping/RTL, minimum-font overflow, explicit line caps, and exact planner-text preservation.
