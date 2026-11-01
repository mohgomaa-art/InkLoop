# Image generation and reference verification

**Tools this workflow may use:** `generation.check_readiness`, `generation.generate_image`, `image.inspect_file_metadata`, `image.verify_visual_consistency`, `assets.list_assets`, `assets.verify_file_integrity`, `execution.get_budget_allowance`.

Use these only when available through the registered callable runtime. Runtime schemas and provider contracts are authoritative.

## Prepare the panel brief

Include the narrative change, exact planned cast and stable profile versions, action/pose/expression, camera and focal hierarchy, location/time, selected style/version, relevant reference IDs, composition/crop, and any text-safe area. State who is absent when cast leakage would change the scene. Keep style constraints separate from identity constraints.

Send actual reference asset bytes/IDs through the provider-supported reference path. Do not claim that naming an asset in prose supplied its image bytes. Preserve provider/run IDs and source provenance. Use source-specific parameters only when the selected provider documents them.

## Before and after generation

- Check readiness and budget before paid calls. If credentials, references, or a usable cost estimate are missing, state the blocker without fabricating an image or cost.
- Generate one planned panel at a time unless a real supported batch call is available. Use idempotency and saved checkpoints; avoid duplicate spend on retry.
- Retry at most one failure when the provider error is actually transient and retry is safe. Do not retry validation, authentication, scope, or budget failures as if they were transient.
- Record returned asset ID, model/provider, request/run ID, reference IDs/versions, and usage when supplied. Unknown usage remains unknown.
- Run consistency checks only when requested/supported. Report detected mismatches and the exact checks; never promise exact identity/style matching.
- Check file integrity and metadata before placing the asset. MIME, dimensions, decode failure, timeout, permission, and storage errors remain explicit.

**Research basis:** Meta Muse Image supports text plus reference-image inputs and edits; those documented capabilities do not guarantee fidelity. See the provider-specific discussion and citations in the research report.
