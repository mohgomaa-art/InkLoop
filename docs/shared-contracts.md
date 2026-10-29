# InkLoop Shared Contracts, Geometry Specification & Core Infrastructure

**Document Type:** Master Contract Specification & Developer Guide  
**Status:** Canonical & Active  
**Version:** `1.0.0`  
**Governing Authority:** `INKLOOP_TASKS.md`  
**Target Audience:** Parallel Engine Agents (Sessions 1 through 4), Compositor, and Frontend Teams  

---

## 1. Executive Summary

This document establishes the canonical data contracts, coordinate systems, and core infrastructure for the **InkLoop** manga, manhwa, and comic production platform.

All seven specialist production engines, supporting services, final compositor, and verification gates operate against these explicit, testable, backward-compatible contracts.

```mermaid
graph TD
    subgraph Shared Core Contracts
        ID[Identity & Entity Refs]
        GEO[Canonical Geometry & Transforms]
        ART[Artifact & Asset Manifests]
        ENG[Engine Run Request/Response]
        ERR[Error Taxonomy & Validation]
    end

    subgraph Specialist Production Engines
        E1[E1: Image Generation]
        E2[E2: Canvas Generation]
        E3[E3: Image-Canvas Integration]
        E4[E4: Text Generation]
        E5[E5: Typography & Fonts]
        E6[E6: Speech Bubbles]
        E7[E7: Effects & Motion]
    end

    subgraph Assembly & Delivery
        S6[S6: Final Compositor]
        S7[S7: QA & Verification Gate]
        S8[S8: Export & Delivery]
    end

    Shared Core Contracts --> E1
    Shared Core Contracts --> E2
    Shared Core Contracts --> E3
    Shared Core Contracts --> E4
    Shared Core Contracts --> E5
    Shared Core Contracts --> E6
    Shared Core Contracts --> E7
    E1 & E2 & E3 & E4 & E5 & E6 & E7 --> S6
    S6 --> S7
    S7 --> S8
```

---

## 2. Project and Entity Identity Contract

To guarantee cross-engine interoperability and avoid duplicate or ambiguous references, all entities in InkLoop use lowercase, typed, prefix-based identifiers conforming to the regex `^[a-z][a-z0-9]*(_[a-z0-9]+)+$`.

### 2.1 Standard Prefixes (`IdPrefix`)

| Prefix | Entity Description | Example |
| :--- | :--- | :--- |
| `proj_` | Project root identifier | `proj_inkloop_demo` |
| `story_` | Story narrative unit | `story_autumn_fog` |
| `ch_` | Chapter or episode sequence | `ch_01_awakening` |
| `scene_` | Scene beat within a story | `scene_01_cafe_portrait` |
| `page_` | Physical or digital canvas page | `page_01` |
| `panel_` | Specific panel slot on a page | `panel_01_01` |
| `char_` | Character in the Story Bible | `char_nour` |
| `char_ver_` | Specific character canon revision | `char_ver_nour_v2` |
| `asset_` | Registered immutable source asset | `asset_nour_ref_01` |
| `art_` | Generated or intermediate artifact | `art_panel_01_raw` |
| `run_` | Pipeline or engine execution run | `run_20261029_001` |
| `att_` | Attempt number within a run | `att_01` |
| `qa_` | Quality / verification audit report | `qa_verdict_p01` |
| `font_` | Bundled or generated typeface | `font_cairo_regular` |
| `txt_` | Attributed script/dialogue text block | `txt_dialogue_01_01` |
| `bbl_` | Vector/raster balloon layer | `bbl_layer_01_01` |
| `fx_` | Independent motion/visual effect layer | `fx_speed_lines_01` |
| `canvas_` | Base canvas layout spec | `canvas_a4_4koma` |
| `tax_` | 60-group taxonomy rule identifier | `tax_01_manga_format` |

### 2.2 Validation and Helper Functions
- `is_valid_id(entity_id: str, expected_prefix: Optional[IdPrefix] = None) -> bool`: Validates naming format.
- `generate_id(prefix: IdPrefix, slug: Optional[str] = None) -> str`: Produces collision-resistant IDs using 8-character hex entropy (e.g. `panel_cafe_a3f89b12`).

---

## 3. Canonical Coordinate System and Geometry Conventions

### 3.1 Non-Negotiable Spatial Invariants
1. **Origin:** Top-Left corner `(0.0, 0.0)`. Matches DOM, SVG, Canvas 2D, Chromium Playwright compositor, and raw bitmap buffer indexing.
2. **Axis Directions:**
   - **+X** points **horizontally to the right**.
   - **+Y** points **vertically downwards**.
3. **Primary Units:**
   - **Screen/Render Pixels (`px`):** The primary internal working unit across all engines at a declared Canvas DPI.
   - **Physical Print Units:** Millimeters (`mm`) or typographic Points (`pt`, $1\text{ pt} = \frac{1}{72}\text{ inch}$).
   - **Normalized Units:** Dimensionless $[0.0, 1.0] \times [0.0, 1.0]$ unit space relative to container width and height.

### 3.2 Conversion Formulas
$$\text{px} = \frac{\text{mm} \times \text{DPI}}{25.4}, \quad \text{mm} = \frac{\text{px} \times 25.4}{\text{DPI}}$$
$$\text{px} = \frac{\text{pt} \times \text{DPI}}{72.0}, \quad \text{pt} = \frac{\text{px} \times 72.0}{\text{DPI}}$$

Default DPI for print is **300.0 DPI** ($1\text{ mm} \approx 11.811\text{ px}$); default for screen preview is **96.0 DPI** or **72.0 DPI**.

### 3.3 Rectangle Representation & Half-Open Rasterization
- **Canonical Schema:** `Rect(x: float, y: float, width: float, height: float)` where:
  - `x`, `y` are finite numbers.
  - `width > 0.0` and `height > 0.0` are strictly positive spatial extents.
  - Derived boundaries: $x_{\min} = x$, $y_{\min} = y$, $x_{\max} = x + \text{width}$, $y_{\max} = y + \text{height}$.
- **Half-Open Interval:** Discrete rasterization adheres strictly to $[x_{\min}, x_{\max}) \times [y_{\min}, y_{\max})$.
  > [!IMPORTANT]
  > Adjacent panels sharing a common border (e.g. Panel A ends at $x=500$, Panel B begins at $x=500$) do **NOT** intersect or double-render the pixel column at $x=500$.

### 3.4 Rotation Convention
- **Units:** Degrees ($^\circ$), clockwise positive.
- **Radians Conversion:** $\text{radians} = \text{degrees} \times \frac{\pi}{180.0}$.
- **Anchor:** Rotation is performed around a normalized anchor point $(u, v) \in [0.0, 1.0]^2$ (default: $(0.5, 0.5)$ center).

### 3.5 Explicit Coordinate Spaces (`CoordinateSpace`)

| Coordinate Space | Description & Origin | Example Dimensions |
| :--- | :--- | :--- |
| `PAGE` | Full canvas space including margins, gutters, and bleed. Origin at page top-left. | $2480 \times 3508\text{ px}$ (A4 @ 300 DPI) |
| `PANEL_SLOT` | Local coordinate space inside a specific panel frame. Origin `(0, 0)` at panel slot top-left. | $1000 \times 800\text{ px}$ |
| `SOURCE_IMAGE` | Intrinsic raw pixel buffer of generated artwork. Origin `(0, 0)` at image top-left. | $1280 \times 1920\text{ px}$ |
| `TEXT_LAYER` | Coordinate space local to text box / glyph layout. Origin `(0, 0)` at text bounding box. | Variable |
| `BUBBLE` | Coordinate space local to speech bubble envelope. Origin `(0, 0)` at bubble bounds top-left. | Variable |
| `EFFECT_MASK` | Coordinate space for motion/effect procedural layers. Origin `(0, 0)` at effect layer top-left. | Variable |
| `VIEWPORT` | Frontend/client display coordinates scaled for viewing. | $800 \times 1131\text{ px}$ |
| `NORMALIZED` | Unit square $[0.0, 1.0] \times [0.0, 1.0]$ for relative bounding boxes and anchors. | $1.0 \times 1.0$ |

### 3.6 Color, Alpha, Blend, and Asset Formats

To ensure deterministic color reproduction and cross-layer rendering fidelity:
- **Color Spaces (`ColorSpace`):**
  - `SRGB`: Standard display color space (default for web and previews).
  - `DISPLAY_P3`: Wide gamut color space.
  - `CMYK_FOGRA39`: European standard offset print CMYK.
  - `CMYK_SWOP`: US standard commercial web offset print CMYK.
  - `GRAYSCALE`: Monochrome / 1-channel halftone or manga ink space.
- **Alpha Modes (`AlphaMode`):**
  - `STRAIGHT`: RGB channels are unmultiplied by alpha. Standard for PNG/SVG source assets.
  - `PREMULTIPLIED`: RGB channels are multiplied by alpha $A \cdot [R, G, B]$. Required by high-performance compositors to prevent edge fringing.
  - `OPAQUE`: Alpha channel ignored ($A = 1.0$).
- **Blend Modes (`BlendMode`):**
  - `NORMAL`, `MULTIPLY` (screentones, shading), `SCREEN` (highlights, blasts), `OVERLAY` (contrast blend), `DARKEN`, `LIGHTEN`, `COLOR_DODGE`, `COLOR_BURN`, `HARD_LIGHT`, `SOFT_LIGHT`.
- **Asset Formats (`AssetFormat`):**
  - Raster: `PNG`, `WEBP`, `JPEG`, `TIFF`.
  - Vector / Document: `SVG`, `PDF`.
- **Clipping Modes (`ClipMode`):**
  - `CLIP_TO_PANEL`: Strict clipping to panel slot rectangle.
  - `BLEED_TO_PAGE_EDGE`: Artwork extends past trim into bleed margin.
  - `BREAK_FRAME`: Deliberate frame-breaking artwork (e.g. character limb or weapon extending over gutter).

### 3.7 Coordinate Space Transformations
- `panel_to_page(point: Point, panel_rect: Rect) -> Point`: $x_{\text{page}} = x_{\text{panel\_rect}} + x_{\text{local}}$, $y_{\text{page}} = y_{\text{panel\_rect}} + y_{\text{local}}$
- `page_to_panel(point: Point, panel_rect: Rect) -> Point`: $x_{\text{local}} = x_{\text{page}} - x_{\text{panel\_rect}}$, $y_{\text{local}} = y_{\text{page}} - y_{\text{panel\_rect}}$
- `bubble_to_page(point: Point, bubble_rect: Rect) -> Point` / `page_to_bubble(point: Point, bubble_rect: Rect) -> Point`
- `text_to_bubble(point: Point, text_rect: Rect) -> Point` / `bubble_to_text(point: Point, text_rect: Rect) -> Point`
- `effect_to_page(point: Point, effect_rect: Rect) -> Point` / `page_to_effect(point: Point, effect_rect: Rect) -> Point`
- `normalize_point(point: Point, container: Rect) -> Point` / `denormalize_point(norm_point: Point, container: Rect) -> Point`
- `normalize_rect(rect: Rect, container: Rect) -> Rect` / `denormalize_rect(norm_rect: Rect, container: Rect) -> Rect`
- `snap_to_pixel_grid(rect: Rect) -> Rect`: Integer snapping: $x = \lfloor x + 0.5 \rfloor$, $w = \max(1.0, \lfloor w + 0.5 \rfloor)$.
- `clip_rect(rect: Rect, bounds: Rect) -> Optional[Rect]`: Clips rectangle to bounds, returning `None` if completely outside.

### 3.8 Fit Modes (`FitMode`)
When Engine E3 (Image–Canvas Integration) places a source image into a panel slot:
- `CONTAIN`: Scale uniformly by $\min(s_x, s_y)$. Entire image is visible; letterboxing may occur.
- `COVER`: Scale uniformly by $\max(s_x, s_y)$. Slot is completely filled; cropping occurs along excess edges.
- `CROP_TO_FRAME`: Specific source crop rect mapped to target slot.
- `STRETCH`: Non-uniform scaling (aspect ratio is altered). Disallowed by default; requires explicit user approval.
- `MANUAL`: User-specified arbitrary affine transform matrix.

---

## 4. Shared Specialist Engine Execution Contract

All seven production engines implement a uniform execution protocol:

```python
EngineRunRequest[TParams] -> EngineRunResponse[TOutput]
```

### 4.1 Specialist Engine Identifiers (`EngineId`)
- `e1_image_generation`: Muse Image prompt compilation, reference anchoring, generation.
- `e2_canvas_generation`: Page geometry, panel slots, margins, gutters, bleed.
- `e3_image_canvas_integration`: Placement, fitting (`contain`/`cover`), transforms, cropping.
- `e4_text_generation`: Script blocks, dialogue, narration, captions, SFX words, tone.
- `e5_typography_font`: Typeface discovery, font generation/selection, text shaping, metrics.
- `e6_speech_bubble`: Balloon geometry, tail routing, reading order, collision avoidance.
- `e7_effects_motion`: Independent speed lines, blur, glow, impact bursts, weather overlays.
- `s6_compositor`: Multi-layer ordering and final raster/vector compositing.
- `s7_quality_verification`: Deterministic geometry/text tests and visual checking gates.
- `s8_export_delivery`: PDF generation, page PNG export, packaging, and delivery.

### 4.2 Standard Request & Response Protocol
- **`EngineRunRequest[TParams]`**: Contains `run_id`, `attempt_id`, `engine_id`, `project_id`, `input_artifact_ids`, `parameters: TParams`, `schema_version = "1.0.0"`, `config_hash`, `budget_limit_usd`, and `dry_run: bool`.
- **`EngineRunResponse[TOutput]`**: Contains `status: EngineStatus`, `quality_verdict: QualityVerdict`, `output_artifact_ids`, `output: TOutput`, `schema_version = "1.0.0"`, `usage: UsageMetrics`, `provenance: ProvenanceRecord`, `validation_errors: List[ValidationErrorDetail]`, and `error: Optional[EngineFailure]`.

### 4.3 Execution Status vs Quality Verdict Separation
To avoid conflating execution health with creative/quality assessment, InkLoop maintains a strict invariant separating pipeline status from quality verdicts:
- **`EngineStatus` (Pipeline Execution State):**
  - `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`, `NEEDS_REVIEW`, `NOT_IMPLEMENTED_YET`, `EXPERIMENTAL`, `BLOCKED`, `NOT_IMPLEMENTED`.
  - Reflects whether the software executed without unhandled crashes, provider errors, or contract violations.
- **`QualityVerdict` (Content & Gate Evaluation State):**
  - `PENDING`: Evaluation not yet performed.
  - `PASSED`: Meets all visual, typographic, or layout criteria.
  - `FAILED`: Violated quality heuristics or consistency thresholds.
  - `UNSURE`: Confidence score fell within indeterminate threshold interval.
  - `NEEDS_REVIEW`: Requires human approval / manual editorial signoff.
  - `BLOCKED`: Upstream quality gate failure prevents evaluation.

> [!IMPORTANT]
> An engine run can execute to technical completion (`status == EngineStatus.SUCCESS`), but fail quality verification (`quality_verdict == QualityVerdict.FAILED`). Downstream pipelines must inspect both.

### 4.4 Typed Engine Parameter & Output Schemas

Every engine and supporting subsystem defines strictly typed Pydantic models for its parameters and outputs:

| Engine / Subsystem | Parameter Schema | Output Schema | Key Fields |
| :--- | :--- | :--- | :--- |
| **E1: Image Generation** | `ImageGenerationParams` | `ImageGenerationOutput` | `prompt`, `negative_prompt`, `reference_asset_ids`, `aspect_ratio`, `guidance_scale`, `seed`, `primary_artifact_id`, `detections` |
| **E2: Canvas Generation** | `CanvasGenerationParams` | `CanvasGenerationOutput` | `page_dimensions`, `margins`, `bleed`, `reading_direction`, `panel_slots`, `gutter_horizontal`, `gutter_vertical` |
| **E3: Image-Canvas Integration** | `ImageCanvasIntegrationParams` | `ImageCanvasIntegrationOutput` | `source_artifact_id`, `target_panel_rect`, `fit_mode`, `anchor`, `clip_mode`, `transform`, `clipped_rect`, `break_frame_overflow` |
| **E4: Text Generation** | `TextGenerationParams` | `TextGenerationOutput` | `script_prompt`, `characters_present`, `scene_context`, `blocks`, `dialogue_count`, `sfx_count` |
| **E5: Typography & Fonts** | `TypographyParams` | `TypographyOutput` | `blocks`, `font_family`, `reading_direction`, `target_dpi`, `shaped_blocks`, `metrics` |
| **E6: Speech Bubbles** | `SpeechBubbleParams` | `SpeechBubbleOutput` | `shaped_blocks`, `panel_rect`, `avoidance_regions`, `bubble_slots`, `tail_points`, `reading_order` |
| **E7: Effects & Motion** | `EffectsMotionParams` | `EffectsMotionOutput` | `effect_type`, `target_rect`, `blend_mode`, `intensity`, `direction_degrees`, `effect_artifact_id` |
| **S6: Final Compositor** | `CompositorParams` | `CompositorOutput` | `page_dimensions`, `layers`, `color_space`, `alpha_mode`, `composite_artifact_id`, `dpi` |
| **S7: Verification Gate** | `VerificationParams` | `VerificationOutput` | `verdict`, `confidence`, `discrepancies`, `reference_comparison_id`, `metrics` |
| **S8: Export & Delivery** | `ExportParams` | `ExportOutput` | `target_format`, `dpi`, `color_profile`, `bleed_included`, `export_artifact_id`, `checksum` |

### 4.5 Provenance and Reproducibility
Every `EngineRunResponse` embeds a `ProvenanceRecord`:
- `engine_id`, `engine_version`, `schema_version = "1.0.0"`.
- `config_hash`: SHA-256 of execution parameters and model settings.
- `source_asset_ids`: Explicit parent asset lineage.
- `seed`: Random seed for deterministic reproducibility.
- `timestamp`: ISO-8601 execution timestamp.

---

## 5. Artifact and Asset Manifest Contract

Large binary files (PNGs, WebPs, PDFs, TTFs) are **never** embedded directly in database tables or serialized JSON state. They are managed through lightweight, immutable `ArtifactManifest` records referencing files on disk.

### 5.1 Artifact Fields
- `artifact_id`: Stable ID (`art_...`).
- `asset_type`: `AssetType` enum (`image_generated`, `panel_layer`, `font_file`, `bubble_layer`, etc.).
- `content_sha256`: Hexadecimal SHA-256 digest computed from file bytes.
- `byte_size`: Size in bytes on disk.
- `file_path`: Relative filesystem path from project root (e.g. `runs/m0_visual/arm_b/scene_01_anchored.png`).
- `dimensions`: Optional `Size(width, height)`.
- `parent_artifact_ids`: Immediate parent IDs for lineage tracing.
- `lifecycle_status`: `DRAFT`, `APPROVED`, `REJECTED`, `ARCHIVED`, `DELETED`.

---

## 6. Standardized Error and Failure Taxonomy

Machine-readable error codes eliminate ambiguous error handling:

| Code Range | Category | Key Error Codes |
| :--- | :--- | :--- |
| `ERR_1000s` | **Schema & Contract** | `INVALID_SCHEMA`, `MISSING_REQUIRED_FIELD`, `INVALID_IDENTIFIER_FORMAT`, `UNKNOWN_ENTITY_REFERENCE` |
| `ERR_2000s` | **Geometry & Spatial** | `ZERO_OR_NEGATIVE_DIMENSION`, `NON_FINITE_COORDINATE`, `OUT_OF_BOUNDS`, `PANEL_UNINTENDED_OVERLAP`, `ASPECT_RATIO_DISTORTION` |
| `ERR_3000s` | **Canon & Narrative** | `UNDECLARED_CHARACTER`, `UNDECLARED_PROP`, `UNDECLARED_LOCATION`, `CHRONOLOGY_VIOLATION`, `SPEAKER_MISMATCH` |
| `ERR_4000s` | **Provider & Network** | `PROVIDER_AUTH_FAILED`, `PROVIDER_RATE_LIMITED`, `PROVIDER_TIMEOUT`, `CONTENT_POLICY_VIOLATION`, `BUDGET_EXCEEDED` |
| `ERR_5000s` | **Verification & QA** | `VERIFICATION_FAILED`, `VERIFICATION_UNSURE`, `TEXT_INTEGRITY_MISMATCH`, `FACE_TOO_SMALL_FOR_VERIFICATION` |
| `ERR_6000s` | **Engine Lifecycle** | `ENGINE_NOT_IMPLEMENTED_YET`, `ENGINE_EXPERIMENTAL_FEATURE`, `MAX_RETRIES_EXCEEDED`, `RUN_CANCELLED` |

---

## 7. Protected Image Generation Engine Adapter

The completed M0 Image Generation Engine is integrated via [`ImageGenerationEngineAdapter`](file:///C:/Users/mnile/Desktop/InkLoob/backend/app/contracts/adapters/image_generation.py).

### Verified Integration Capabilities:
1. **Pre-flight Validation:** Verifies non-empty prompt and existence of reference image before any network dispatch.
2. **Dry-Run Mode Guard:** Returns complete, valid `EngineRunResponse[ImageGenerationOutput]` with strictly `image_ops: 0`, `compute_seconds: 0.001`, `cost: 0.0`, and mock SHA hashes, preventing dry-run outputs from ever being mistaken for billable productions.
3. **Payload Builder Compatibility:** Reuses `build_image_edit_payload` from `backend/app/parsers.py` without modifying working M0 behavior.
4. **SAM Bounding Box Bridge:** `BoundingBox.to_rect()` converts segmentation detections into canonical `Rect` models.
5. **Offline Mock Response Harness & Error Mapping:**
   - Evaluated without live API calls using `handle_mock_response`.
   - `HTTP 200`: `EngineStatus.SUCCESS`, `output_artifact_ids` populated, `image_ops: 1`.
   - `HTTP 400` (Content Policy): `EngineStatus.FAILED`, `ErrorCode.CONTENT_POLICY_VIOLATION`, `retryable: True` (can retry with modified prompt).
   - `HTTP 401` (Auth Failure): `EngineStatus.FAILED`, `ErrorCode.PROVIDER_AUTH_FAILED`, `retryable: False` (hard fail, immediate halt).
   - `HTTP 429` (Rate Limit): `EngineStatus.FAILED`, `ErrorCode.PROVIDER_RATE_LIMITED`, `retryable: True` (retryable with backoff).
   - `HTTP 500` (Internal Server Error): `EngineStatus.FAILED`, `ErrorCode.PROVIDER_TIMEOUT`, `retryable: True` (transient provider failure).

---

## 8. Downstream Engine Implementation Directives

Parallel agents executing subsequent tasks must strictly follow these rules:

1. **Canvas Generation Engine (E2 / Session 2):**
   - Emit panel geometries strictly as `Rect(x, y, width, height)` in `CoordinateSpace.PAGE`.
   - Never allow negative or zero widths/heights.
   - Enforce gutter spacing so adjacent panels adhere to disjoint half-open boundaries ($x_2 \le x_1$ or $x_1 + w_1 \le x_2$).
2. **Image–Canvas Integration Engine (E3 / Session 3):**
   - Consume raw image dimensions (`Size`) and target slot (`Rect`).
   - Use `calculate_fit_transform(source_size, target_rect, mode=FitMode.COVER, anchor=Point(0.5, 0.5))`.
   - Preserve aspect ratio; do not stretch images unless `mode=FitMode.STRETCH` is explicitly approved.
3. **Speech Bubble Engine (E6 / Session 4):**
   - Bubble placement bounds must be evaluated in `CoordinateSpace.PAGE` or `CoordinateSpace.PANEL_SLOT`.
   - Use `rect_intersects` for bubble-to-bubble and bubble-to-face collision checking.
   - Tail coordinates must connect from bubble perimeter to speaker anchor point.
4. **Final Compositor (S6):**
   - Order layers deterministically: Background $\to$ Panel Artwork $\to$ Inset Panels $\to$ Background Effects $\to$ Foreground Artwork $\to$ Speech Bubbles $\to$ Lettering $\to$ Foreground Effects $\to$ Borders.
   - Pixel snapping must use `snap_to_pixel_grid` to avoid subpixel blur on borders.
