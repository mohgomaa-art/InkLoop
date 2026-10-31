# B1 canonical bubble registry

`backend/app/canvas/bubble_registry.py` is the semantic source of truth. It defines exactly eight type IDs and their short descriptions, word limits, line limits, font ranges, default shapes, and tail policy:

| Type ID | Words | Lines | Font px | Default carrier |
|---|---:|---:|---:|---|
| `speech.normal` | 12 | 3 | 16–28 | speech bubble |
| `speech.shout` | 5 | 2 | 18–36 | speech bubble |
| `speech.whisper` | 8 | 3 | 14–24 | speech bubble |
| `thought.cloud` | 10 | 4 | 16–28 | thought bubble |
| `speech.offpanel` | 12 | 3 | 16–28 | speech bubble |
| `narration.box` | 16 | 4 | 14–24 | narration box |
| `caption.timeplace` | 5 | 2 | 12–20 | caption |
| `sfx.text` | 3 | 1 | 28–72 | SFX lettering |

The previous 50 preset IDs remain unchanged. `attach_type_ids()` decorates the existing visual preset records with their semantic `type_id` at the service boundary; old fear, anger, joy, broadcast, and mystery styles map to the nearest semantic type as appearance variants. Caption and SFX semantics do not add extra visual presets or semantic type IDs.

Validation: `python -m pytest backend/tests/test_bubble_registry.py -q --tb=short` — 3 passed.
