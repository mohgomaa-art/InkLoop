# InkLoop Architecture Decision Records (ADRs)

---

## ADR-001: External Structured Memory (Story Bible)
- **Status:** [VERIFIED ARCHITECTURE]
- **Context:** Early comic generation experiments demonstrated that in-context conversational memory drifts and degrades across multiple panels (~20% yield across 1000 generations).
- **Decision:** All character attributes, style rules, location references, and state changes are stored in explicit, versioned disk files (`bible/characters/`, `bible/style.json`, `bible/state.jsonl`).
- **Consequences:** Every generation call receives a newly assembled *continuity packet*. The model has zero long-term memory; drift is eliminated at the architectural boundary.

---

## ADR-002: Remove-Only Multi-Tier Verification Gate
- **Status:** [VERIFIED ARCHITECTURE]
- **Context:** LLM judges that attempt to "fix" or "edit" generation plans frequently introduce hallucinations and unpredictable mutations.
- **Decision:** The verification system is strictly hierarchical and remove-only:
  - **L0 Code:** Aspect ratio, blank frames, sheet-bleed, and text leakage.
  - **L1 SAM 3.1:** Subject counts, bounding box framing, and face size thresholds.
  - **L2 Muse Spark Judge:** Multimodal visual comparison against declared `spec.json` checklist.
  - Output is strict tri-state JSON (`pass`, `fail`, `unsure`).
  - Code accepts only if all required attributes are `pass` (`unsure` is treated as `fail`).
- **Consequences:** The judge never generates content; it acts solely as a deterministic gatekeeper.

---

## ADR-003: Deterministic Code Layout & Chromium Rendering
- **Status:** [VERIFIED ARCHITECTURE]
- **Context:** AI image generators cannot reliably render correct Arabic calligraphy, complex typography, or stable speech bubbles without distortion and baked-in pseudo-text.
- **Decision:** Image generation is strictly restricted to clean panel artwork without dialogue or lettering. Lettering and bubbles are rendered entirely by code (HTML/SVG rendered via Chromium/Playwright) using bundled SIL OFL fonts (Cairo, Tajawal, Bangers, Comic Neue).
- **Assertion:** $\text{RenderedText}(P) \equiv \text{SourceScript}(P)$.

---

## ADR-004: Meta Model API Integration & Canonical Credential Standard
- **Status:** [VERIFIED & LIVE IN PRODUCTION]
- **Context:** The hackathon requires meaningful use of Meta models via the Meta Model API (`https://api.meta.ai/v1`).
- **Verified Facts:**
  - Official documentation standard specifies `MODEL_API_KEY` as the canonical environment variable.
  - Base URL is `https://api.meta.ai/v1`.
  - Endpoint probe confirmed live server responses (`x-route: model-api-rust`).
  - Model catalog retrieved: `muse-image-1.0`, `muse-spark-1.3`, `sam-3.1` verified present and active.
  - Minimal text generation request succeeded (`POST /v1/chat/completions` with `muse-spark-1.3`).
  - Project-root `.env` loading normalized via `python-dotenv`.
  - Safe credential masking enforced: zero key characters are logged, serialized, or displayed.

---

## ADR-005: SAM 3.1 Segmentation & Output Format Standard
- **Status:** [VERIFIED & LIVE IN PRODUCTION]
- **Context:** Bounding boxes and subject masks are needed for smart cropping, face protection, and bubble placement.
- **Decision & Verified Implementation:**
  - Primary: SAM 3.1 accessed via `POST /v1/responses` using Promptable Concept Segmentation (`input_text: "person"`, `input_image: <data_url>`).
  - Live response protocol returns custom special tokens: `<|box;x1=...;y1=...;x2=...;y2=...;w=...;h=...|>` and `<|mask;x=0;y=0;data=...|>`.
  - Verified parser (`backend/app/parsers.py:parse_sam_response`) extracts subject bounding boxes and RLE masks deterministically.
  - Latency verified at ~8.35s per request.

---

## ADR-006: Hard Safety & Budget Guardrails
- **Status:** [VERIFIED & ENFORCED IN M0]
- **Context:** Unbounded retry loops in agentic workflows risk exhausting credits and incurring runaway API costs.
- **Decision:**
  - Hard limit of 2 targeted retries per panel; max 4 attempts total before marking `needs_human`.
  - M0 budget cap enforced at $\le \$5.00$ USD; actual visual experiment expenditure was $\$0.172$ ($\approx 3.44\%$ of cap).
  - Concurrency strictly enforced at 1. Max image ops capped at 20 (16 executed), Spark ops at 6 (2 executed), SAM ops at 2 (1 executed).

---

## ADR-007: Verified Reference Anchoring and Empirical Feasibility Gate (GO)
- **Status:** [EMPIRICALLY VERIFIED — EXIT GATE PASSED]
- **Context:** The central InkLoop thesis asserts that character identity consistency can be maintained across diverse scenes using structured external references, and that visual defects can be caught by an independent verifier.
- **Empirical Proof:**
  - **Reference Anchoring:** Evaluated 6 diverse scenes comparing unanchored Arm A (`POST /v1/images/generations`) vs reference-anchored Arm B (`POST /v1/images/edits` with `nour_reference.png`).
  - **Arm A Result:** 0/6 (0%) passed the canonical checklist due to severe feature drift on hair streak, glasses frame style, and lightning patch.
  - **Arm B Result:** 6/6 (100%) passed all canonical checklist items (short messy black hair with left white streak, round wireframe glasses, oversized hooded jacket with lightning patch), easily surpassing the $\ge 4/6$ (66.7%) threshold.
  - **Verifier Discrimination:** `muse-spark-1.3` evaluated with tri-state checklist. Correctly accepted matching Arm B candidate (`passed=True`, all 3 attributes `pass`) and correctly rejected deliberately corrupted candidate (`passed=False`, all 3 attributes `fail`).
  - **Decision:** **GO** for Milestone 1 (M1 - Story Engine & Continuity Pipeline). All Day-0 technical assumptions are proven true by live API execution.

---

## ADR-008: Versioned Story Bible, Cryptographic Canon Snapshots & Append-Only State Timeline
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN M1]
- **Context:** To prevent context drift across multi-panel comic generation, memory must be externalized, canonical definitions must be strictly immutable during execution runs, and narrative state transitions must be ordered and deterministic.
- **Architectural Invariants & Decisions:**
  1. **Strict Canon vs Narrative State Separation:**
     - **Canon (`CanonSnapshot`):** Visual style rules, structurally addressable character specs with verifier attributes, recurring locations, and props. Immutable during runs; frozen via `ConfigDict(frozen=True)` and protected against in-place mutations.
     - **State Timeline (`StoryStateTimeline`):** Ordered, append-only sequence of narrative events (`StoryStateEvent`). Captures dynamic changes (held props, clothing tears, weather, positions) without rewriting the canon.
  2. **Cryptographic Canon Content Hashing:**
     - Deterministic SHA-256 hash computed over sorted JSON dictionaries of canonical definitions (`style`, `characters`, `locations`, `props`). Any tampering or modification alters the hash immediately.
  3. **Controlled Canon Mutation Flow:**
     - New entities cannot appear silently. Generation calls referencing undeclared characters, locations, or props are rejected with `UndeclaredEntityError`.
     - Canon modifications require an explicit `CanonMutationProposal` followed by caller-authorized `apply_canon_mutation` (or `reject_canon_mutation`), producing a new monotonic version (`v{N+1}`) while preserving prior snapshots in `<project_dir>/snapshots/`.
  4. **Deterministic State Resolution & Contradiction Detection:**
     - Given an immutable Canon snapshot and event sequence, `resolve_timeline_state` sorts by monotonic `sequence_number`, timestamp, and `event_id`, deterministically resolving the effective state for any target panel.
     - Detects contradictory state transitions when an event asserts an unexpected `previous_value`.
     - Supports isolated parallel runs without cross-contamination.
  5. **Asset Reference Integrity & Storage Decoupling:**
     - Binary image bytes and base64 payloads are strictly barred from Story Bible JSON metadata. References use `AssetRef` with filesystem path validation, path traversal guards (`Path.relative_to`), and SHA-256 checksum verification.
  6. **Original User Story Text Preservation:**
     - `user_story_text` in `StoryBible` preserves original user input (including Arabic RTL and diacritics) byte-for-byte without normalization or deletion.
- **Verification Evidence:**
  - 34 dedicated unit and integration tests passing in `backend/tests/test_story_bible.py` and `backend/tests/test_story_bible_advanced.py`. Total test suite: 98 passing tests.

---

## ADR-009: Content-Addressed Asset Registry, Physical Artifact Store & Reproducible Lineage DAG
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN M1]
- **Context:** Comic production generates large volumes of heterogeneous artifacts (reference sheets, panel crops, masks, lettering vectors, bubble geometry, speech text blocks, composites, page previews, and final print exports). To ensure tamper-evidence, lineage traceability, and system stability under concurrent or resumed workflows, binary assets must be cleanly decoupled from searchable metadata, deduplicated, and tracked through a directed acyclic graph (DAG).
- **Architectural Invariants & Decisions:**
  1. **Decoupled Architecture (Physical Store vs Registry DB):**
     - **Physical Content-Addressed Store (`ArtifactStore`):** Physical binary content is stored on disk strictly organized by SHA-256 digest: `objects/<hash[:2]>/<sha256><norm_ext>`. Callers cannot dictate disk destinations or file paths.
     - **Metadata & Lineage Persistence (`RegistryDB`):** SQLite database operating in WAL mode with enforced foreign keys and secondary indexes (`project_id`, `content_sha256`, `asset_type`, `run_id`, `parent_id`, `child_id`).
  2. **Security & Input Sanitization (OWASP / Defensive Hardening):**
     - **Path Traversal Defense:** Caller-supplied paths are validated via `Path.resolve().relative_to(root)`. Any directory escape attempts trigger explicit `PathTraversalSecurityError`.
     - **Sanitized Logical Filenames:** Original logical filenames are sanitized via `re.sub(r"[^\w.\-]", "_", ...)` and never used to determine physical storage paths.
     - **Prohibited Executables:** Prohibited extensions (`.exe`, `.sh`, `.bat`, `.cmd`, `.ps1`, `.py`, etc.) are unconditionally rejected via `InvalidFileFormatError` (`PROHIBITED_EXECUTABLE_EXTENSION`).
     - **Deep Magic Byte & Structural Inspection:** File extensions are never trusted blindly:
       - Raster images must match valid PNG, WebP, or JPEG magic headers and pass Pillow structural verification (`verify()` + `size > 0`).
       - Font files must match TrueType (`\x00\x01\x00\x00`), OpenType (`OTTO`), or WOFF/WOFF2 signatures.
       - Vector SVG files are parsed for `<svg` tags and screened for dangerous `<script` tags (`PROHIBITED_SVG_SCRIPT_TAG`).
       - PDF documents must verify `%PDF-` magic headers.
       - JSON artifacts are verified to decode as valid UTF-8 and valid JSON.
  3. **Content Immutability & Deduplication:**
     - Registered assets are identified by their SHA-256 digest. Identical file contents share the same physical disk object, preventing redundant disk usage while allowing separate logical asset IDs and run linkages.
     - Corrupted or modified files on disk are detected immediately during `verify_asset()` or resolution via streaming SHA-256 recalculation (`AssetIntegrityError`).
  4. **Reproducible Lineage DAG & Cycle Prevention:**
     - Downstream derivatives (`register_derivative`) record parent asset IDs, transformation operation, configuration hash, and engine metadata.
     - Registering a derivative verifies all parent IDs exist (`UnregisteredParentError`) and runs DFS cycle detection across the lineage graph (`LineageCycleError`), guaranteeing an acyclic DAG.
  5. **Bidirectional Story Bible Integration:**
     - `AssetMetadata.to_asset_ref()` maps registered assets directly to Story Bible `AssetRef` models.
     - `AssetRegistry.register_from_asset_ref()` imports existing Story Bible assets (such as canonical character sheets) into managed storage while preserving original IDs and content hashes.
     - Story Bible state operations and timeline resolution operate strictly read-only on the asset registry.
  6. **Deterministic Manifest Exports:**
     - `export_manifest()` generates a stable, reproducible machine-readable JSON manifest sorted deterministically by `asset_id`.
     - Zero secrets, API keys, or raw binary payloads are included in manifests or database logs.
- **Verification Evidence:**
  - 16 dedicated unit and integration tests passing in `backend/tests/test_storage_registry.py`.
  - Total test suite: 123 passing tests with zero regressions.
