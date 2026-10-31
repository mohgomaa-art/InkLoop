# B3 protected-region records and SAM cache

`backend/app/canvas/protected_regions.py` records normalized bounding boxes for one concept per image, keyed by `(sha256(image bytes), normalize(concept))`. The configured adapter uses the existing live SAM 3.1 verifier and rejects its simulated fallback. It persists source (`sam`, `vlm`, or `manual`), stable region IDs, box confidence, mask availability/hash, model, purpose, image dimensions, estimated cost, and query/cache audit events.

Repeated queries return the same cached regions without another provider call and log a zero-cost cache hit. The estimate for a new SAM image/concept request is $0.0025. A query that returns no valid boxes is stored as `regions_unknown`; it contains no guessed center or fallback region and requires manual annotation. Manual annotation is validated in normalized image coordinates and records the annotating actor. An unknown-region override also requires an actor and reason and remains explicitly marked in the saved record.

No live SAM requests were made for B3. Tests use fixture regions and an isolated temporary SQLite database. The focused validation command was:

```text
python -m pytest backend/tests/test_protected_regions.py backend/tests/test_m0_parsers.py backend/tests/test_visual_verification.py backend/tests/test_lettering_layout.py backend/tests/test_bubble_registry.py backend/tests/test_panel_plan_recovery.py -q --tb=short
```

Result: **74 passed**. The tests verify image/concept cache keys, stable IDs, audit cost/model/purpose/cache fields, unknown-region handling, manual annotation, explicit overrides, mask-payload hashing, and no live calls.
