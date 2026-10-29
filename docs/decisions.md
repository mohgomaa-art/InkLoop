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

---

## ADR-010: Run Execution Lifecycle, Multi-Scope Decimal Budget Manager & Crash Recovery Engine
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN M1]
- **Context:** Automated comic production dispatches paid provider API requests, runs complex multi-step pipelines (canvas layout, panel generation, segmentation, bubble placement, lettering, and quality verification), and must guard against unbounded runaway loops, double billing, lost responses, and unobservable crashes. Financial accounting must be exact, and execution history must remain auditable without leaking credentials.
- **Architectural Invariants & Decisions:**
  1. **Strict State Machine Envelopes:**
     - **Run Lifecycle (`RunStatus`):** `created` -> `queued` -> `running` -> `[succeeded, failed, cancelled, interrupted, needs_review]`. Terminal states (`succeeded`, `failed`, `cancelled`) are immutable and strictly reject re-execution or status mutations (`RunTerminalError`).
     - **Attempt Lifecycle (`AttemptStatus`):** `started` -> `[succeeded, failed, cancelled, interrupted]`. Every retry or re-attempt generates a distinct, non-overwriting attempt record.
     - **Operation Lifecycle (`OperationStatus`):** `pending` -> `running` -> `[succeeded, failed, blocked, interrupted, reconciliation_required, needs_review]`. Partial runs with uncompleted operations cannot be marked `SUCCEEDED`.
  2. **Atomic Multi-Scope Budget Reservation & Exact Decimal Accounting:**
     - Pre-dispatch reservation: operations cannot run unless estimated spend is atomically reserved in `BudgetManager` before provider dispatch (`BudgetExceededError`).
     - Hierarchical scopes: Global, Project, Run, Operation. Effective allowance is `min(global, project, run, operation)`. Child scopes cannot exceed stricter parent caps (`BudgetScopeViolationError`).
     - Exactly-once settlement: duplicate settlements are rejected (`DuplicateSettlementError`). Unused funds on cancelled/unbilled operations are released back to available allowance.
     - All financial calculations use Python `Decimal` (minor units / 4 decimal places) to completely eliminate binary floating-point drift.
     - Cost classifications are strictly distinguished: `estimated`, `reserved`, `provider_reported`, `billing_confirmed`, `unknown`. Estimates are never conflated with confirmed billing.
     - When pricing is unknown (`unknown`), hard operation-count ceilings are enforced without fabricating fictitious prices.
  3. **Bounded Retries & Permanent Failure Circuit Breakers:**
     - Deterministic errors (`AUTHENTICATION_ERROR`, `BAD_REQUEST`, `BUDGET_EXCEEDED`, `DEPENDENCY_FAILED`) are classified as permanent and immediately halt without entering retry loops (`PermanentErrorNotRetryableError`).
     - Transient errors (`RATE_LIMIT_EXCEEDED`, `NETWORK_TIMEOUT`, `SERVER_ERROR`, `CONTENT_POLICY_VIOLATION`) permit bounded retries up to configured ceilings (`max_retries_per_panel`).
     - Downstream dependent operations are blocked if a prerequisite fails (`DependencyFailedError`).
  4. **Crash Recovery & Uncertain Outcome Reconciliation:**
     - Process restarts run `recover_on_startup()` to detect runs and operations left in `running` or `queued` status, transitioning them safely to `interrupted`.
     - Lost responses or remote timeouts mark attempts as `interrupted` with `reconciliation_required=True`. Reserved funds are held (never assumed free or refunded) until external reconciliation.
     - Safe resumption (`resume_run`) preserves already `succeeded` operations without redundant re-generation, revalidates input asset hashes, and resets only interrupted operations to `pending`.
  5. **Append-Only Event Ledger & Secret Hygiene:**
     - All state transitions, budget reservations, settlements, releases, and recovery discoveries append typed events to `events` table in SQLite (`WAL` mode).
     - Run summaries (`RunSummary`) serialize deterministically with zero API keys, headers, or raw binary payloads.
- **Verification Evidence:**
  - 21 dedicated unit and integration tests passing in `backend/tests/test_execution_manager.py`.
  - Total test suite: 166 passing tests across all subsystems with zero regressions.

---

## ADR-011: Image Generation Knowledge Catalogue Schema, Research Governance & 60-Group Coverage Register
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN T6.1]
- **Context:** To ensure controlled, reproducible comic art generation without prompt bloat or hallucinated rules, the Image Generation Engine requires a structured technical knowledge catalogue. The catalogue must maintain strict research governance, separate evidence classes from claim confidences, enforce anti-gaming validation, and maintain a truthful coverage register across all 60 taxonomy groups.
- **Architectural Invariants & Decisions:**
  1. **Exclusivity to Image Generation Engine (E1):**
     - The catalogue is a dedicated technical knowledge base for image prompt conditions, model capabilities, negative constraints, and recipes. It does not replace the other engines (Canvas, Bubble, Lettering, Effects, Compositor).
  2. **Strict Separation of Evidence Class vs Claim Confidence:**
     - **Evidence Class (`EvidenceClass`):** `PRIMARY_PROVIDER_DOC` (official Meta Muse docs), `PEER_REVIEWED_RESEARCH`, `INKLOOP_EXPERIMENT` (reproducible runs), `SECONDARY_TECHNICAL` (comic theory literature: McCloud, Eisner), `ANECDOTAL_UNVERIFIED`.
     - **Claim Confidence (`ClaimConfidence`):** `FACT`, `INFERENCE`, `HYPOTHESIS`, `EXPERIMENTAL_RESULT`, `UNKNOWN`.
  3. **Anti-Gaming Model Invariants:**
     - An `UNRESEARCHED` group cannot be marked validated or claim recorded experiments (`validate_group_coverage_integrity`).
     - A recipe cannot claim `is_empirically_validated=True` without an explicit `experiment_id` and a non-untested result (`validate_recipe_integrity`).
     - A `VALIDATED` group requires at least one empirically passing recipe and primary provider / experimental source backing.
  4. **Truthful 60-Group Baseline Coverage:**
     - All 60 taxonomy groups from `INKLOOP_TASKS.md` Section 7 are represented with stable IDs (`tax_01_comic_formats` ... `tax_60_visual_continuity_validation`) and 840 canonical elements.
     - Truthful baseline status: 1 VALIDATED (Group 60, backed by M0 visual feasibility experiment ADR-007), 4 RESEARCHED (Groups 07, 08, 19, 28, backed by primary style guidelines and comic theory), and 55 UNRESEARCHED with explicit open research gaps visible.
  5. **Deterministic Serialization & Provenance Linking:**
     - Serialized to `backend/app/catalogue/data/taxonomy_60_groups.json` sorted by sequential group number.
     - Integrates with shared contracts (`IdPrefix.TAXONOMY`, `ProvenanceRecord.taxonomy_rule_ids`).
- **Verification Evidence:**
  - 12 dedicated unit and integration tests passing in `backend/tests/test_image_knowledge_catalogue.py`.
  - Total test suite: 179 passing tests with zero regressions.

---

## ADR-012: Research Governance Hardening, Structured Licensing Tracking, Promotion Workflow & Group 60 Status Reconciliation
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN T6.1]
- **Context:** Following the establishment of the catalogue foundation, research governance (Task T6.1) required full hardening: task boundaries needed explicit reconciliation against T6.2/T6.3, source claims required verifiable boundaries (what they establish vs what they do not establish), licensing rights across all asset families required strict tracking without assuming commercial clearance for unknown assets, formal peer/lead promotion workflows needed audit trails, and Group 60's coverage classification required truthful adjustment to avoid premature group-level validation claims from a narrow single-character trial.
- **Architectural Invariants & Decisions:**
  1. **Reconciliation of Research Tasks:**
     - `T6.1 — Research governance`: data models, confidence/evidence separation, claim mapping, licensing tracking (`LicenseRecord`, `LicenseRegistry`), promotion workflow (`PromotionReviewRecord`, `PromotionWorkflow`), and catalogue foundation register.
     - `T6.2 — Experimental design and visual evaluation`: controlled prompt experiments, blind human evaluation, visual regression sets, and failure analysis protocols.
     - `T6.3 — Research-backed image-generation knowledge catalogue`: comprehensive research across all 60 groups, prompt recipes, runtime scene-relevance retrieval, and generation integration.
  2. **Truthful Group 60 Coverage Downgrade & Broad Group Anti-Gaming Rule:**
     - Group 60 contains 14 canonical elements (`Character Identity`, `Style Consistency`, `Character Count`, `Attribute Presence`, `Reference Matching`, `Pose Continuity`, `Clothing Continuity`, `Prop Continuity`, `Location Continuity`, `Lighting Continuity`, `State Tracking`, `Composition Drift`, `Verifier Confidence`, `Retry Policy`).
     - The M0 trial evaluated a single recipe (`rec_60_reference_anchored_portrait`) on single-character Nour portraits. Labeling the entire group `VALIDATED` was premature.
     - Group 60 is now classified truthfully as `EXPERIMENTALLY_TESTED` (`is_empirically_validated=False` at the group level, `has_recorded_experiments=True`). The passing recipe and claim remain verified and tested.
     - **Anti-Gaming Invariant (`TaxonomyGroupRecord`):** Any broad group (>3 canonical elements) cannot attain `CoverageStatus.VALIDATED` with fewer than 2 passing, empirically validated recipes across diverse elements.
  3. **Granular Source & Claim Provenance:**
     - `SourceRecord` enforces explicit documentation of `source_location` (chapter, section, doc URL, experiment artifact path), `what_it_establishes`, and `what_it_does_not_establish`.
     - `ResearchClaim` explicitly distinguishes `artistic_theory` (sequential art theory literature) from `empirical_observation` (model API runs and metric benchmarks).
  4. **Structured Licensing & Commercial Safety Governance:**
     - `LicenseRecord` and `LicenseRegistry` manage formal rights tracking across fonts (`LicenseTargetType.FONT`), software libraries (`SOFTWARE_LIBRARY`), model outputs (`MODEL_GENERATED`), reference images (`REFERENCE_IMAGE`), and external datasets (`EXTERNAL_DATASET`).
     - **Fail-Closed Commercial Rule:** `LicenseRecord` validator rejects any configuration where `license_type == LicenseType.UNKNOWN` and `is_commercial_use_permitted == True`. Unknown rights cannot be silently assumed.
     - Default baseline assets registered and cleared: Amiri font (SIL-OFL-1.1), Pillow (HPND), Pydantic (MIT), HTTPX (BSD), Meta Muse/Spark terms (provider commercial terms), and Nour reference image (proprietary original created for InkLoop by Mohamed Gomaa).
  5. **Formal Promotion & Review Workflow:**
     - `PromotionWorkflow` audits status upgrades for claims and groups, generating immutable `PromotionReviewRecord` entries with reviewer identity, reviewer role, decision, rationale, verified evidence IDs, and timestamps.
     - Baseless promotion requests without evidence or violating integrity invariants fail closed with `ReviewDecision.REJECTED` and clear error diagnostics.
  6. **Self-Contained CLI Scripting:**
     - `scripts/generate_taxonomy.py` provides supported CLI operations (`--check`, `--audit`, `--rebuild`, `--export`) with automatic backend `sys.path` bootstrapping to prevent import errors regardless of invocation working directory.
- **Verification Evidence:**
  - 20 dedicated unit and integration tests passing in `backend/tests/test_image_knowledge_catalogue.py`.
  - Full backend test suite: 209 passing tests with zero regressions.
  - Zero paid API spend incurred.

---

## ADR-013: Experimental Design, Blind Human Evaluation Protocol, Repeatability Accounting & Visual Regression Corpus
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN T6.2]
- **Context:** To ensure controlled, scientifically rigorous, and reproducible comic visual evaluation without unbacked quality claims, InkLoop requires a standardized experimental design and visual-evaluation subsystem. The framework must enforce pre-declared hypotheses, immutable frozen configurations, complete sample denominator accounting, file-based blind human evaluation, honest statistical uncertainty intervals, and a 7-domain visual regression corpus that prevents unimplemented engines from falsely reporting test passes.
- **Architectural Invariants & Decisions:**
  1. **Separation of Plans from Executions & Frozen Configurations:**
     - Pre-declared specifications (`ExperimentPlan`) remain strictly distinct from executed summaries (`ExperimentExecutionSummary`). A plan retains `is_executed=False` and cannot be mistaken for an empirical result.
     - Configurations are frozen (`FrozenConfig`, `ConfigDict(frozen=True)`). Any change to prompt, parameters, seed, or input artifact hashes produces a distinct `config_hash` via deterministic SHA-256.
     - Secret hygiene is strictly enforced: nested dictionary/list auditing rejects raw credentials, bearer tokens, or API keys in configurations.
     - Bitwise determinism is never falsely promised for hosted diffusion models; reproducibility is explicitly classified (`REPRODUCIBLE`, `PARTIALLY_REPRODUCIBLE`, `CANNOT_BE_REPRODUCED`).
  2. **Strict Denominator Reconciliation & Failure Accounting:**
     - Denominator integrity: `planned == completed + failed + filtered + unresolved + unfinished` (`reconcile_sample_denominator`). Every started attempt must be preserved in reporting denominators; selective deletion of failed or inconvenient runs is structurally forbidden.
     - Samples marked `SUCCESS` must provide output hashes; samples marked `FAILED` or `FILTERED` must record explicit reason codes.
     - Statistical uncertainty for binomial pass rates is calculated via Wilson score confidence intervals, accurately reflecting small-sample variance without inflating exploratory trials.
  3. **File-Based Blind Human Evaluation Protocol:**
     - `BlindEvaluationSheet` presents opaque sample IDs (`bld_...`) and sanitized relative image paths free of arm keywords, prompt clauses, or condition tokens (`arm_a`, `arm_b`, `baseline`, `anchored`).
     - Presentation order is reproducibly randomized via recorded integer seed (`random_seed`).
     - Confidential unblinding keys (`BlindingKeyMap`) are maintained separately until ratings are locked.
     - Preserves individual rater judgments (`HumanJudgmentRecord`), computing consensus verdicts, disagreement logs, and inter-rater reliability via Cohen's Kappa ($\kappa$). Documents what $\kappa$ proves (agreement above chance) and what it does not prove (ground truth).
     - Provides clean machine-readable CSV and JSON exports for downstream analysis.
  4. **Seven-Domain Visual Regression Corpus & Engine Readiness Invariant:**
     - `VisualRegressionCorpus` establishes versioned test specifications (`VisualRegressionCase`) across all 7 comic production domains:
       1. Composition & Framing (E1 Image Gen - READY)
       2. Character / Reference Consistency (E1 Image Gen - READY)
       3. Generation Defects & Artifacts (E1 Image Gen - READY)
       4. Text Rendering & Arabic Shaping (E5 Typography - BLOCKED_BY_ENGINE)
       5. Speech Bubble Geometry & Placement (E6 Speech Bubble - BLOCKED_BY_ENGINE)
       6. Effects & Motion Lines (E7 Effects - BLOCKED_BY_ENGINE)
       7. Export & Delivery Reconstruction (S8 Export - BLOCKED_BY_ENGINE)
     - **Fail-Closed Engine Readiness Guard:** Unimplemented engines (E2, E4, E5, E6, E7, S8) cannot be instantiated with `readiness="ready"`, cannot register baseline hashes, and strictly evaluate as `NOT_EVALUABLE` / `is_blocked=True`. They are structurally barred from reporting passing regression results.
  5. **Truthful M0 Historical Experiment Ingestion:**
     - Ingests historical feasibility trials (`runs/m0_visual/benchmark_results.json`) into canonical schemas (`m0_adapter.py`) preserving exact sample-level request IDs, latencies, token counts, and artifact hashes (`nour_reference.png` hash `b2c2c4dc...`).
     - Documents exact outcomes: Arm A 0/6 (0.0%, 95% CI [0.0, 0.4096]), Arm B 6/6 (100.0%, 95% CI [0.5904, 1.0]).
     - Retains explicit scientific limits: N=6 per arm constitutes exploratory visual feasibility, not a universal guarantee. Confirmed billing invoices are recorded as `UNAVAILABLE`.
  6. **Zero Duplicate Infrastructure:**
     - Reuses shared `ExecutionManager` (`CostRecord`, `run_id`, `attempt_id`), `AssetRegistry` (`art_...`, content hashes), `TaxonomyRegister`, and `IdPrefix`. Zero parallel databases created.
- **Verification Evidence:**
  - 14 dedicated unit and integration tests passing in `backend/tests/test_visual_evaluation_framework.py`.
  - 20 catalogue tests passing in `backend/tests/test_image_knowledge_catalogue.py`.
  - Full backend test suite: 225 passing tests with zero regressions.
  - Zero live model API spend incurred.
