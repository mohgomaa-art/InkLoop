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
     - Current register status: 0 VALIDATED, 14 RESEARCHED (Groups 01, 03-08, 11, 19, 28, 53, 54, 56, 58), 1 EXPERIMENTALLY_TESTED (Group 60, backed by the limited M0 visual feasibility experiment ADR-007), and 45 UNRESEARCHED with explicit open research gaps visible.
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

---

## ADR-014: Four-Session Unification, Canonical Nour Specification, Multi-Layer Authority Separation & End-to-End Visual Verification Integration
- **Status:** [VERIFIED ARCHITECTURE & RECONCILED IN M1 INTEGRATION]
- **Context:** Four independent agent sessions and recent concurrent feature branches developed distinct subsystems: Story Bible & Canon (T5.3), Asset Registry (T5.4), Execution Manager & Budgets (T5.5), 60-Group Knowledge Catalogue (T6.1), Visual Evaluation (T6.2), Batch Orchestration & Resumability (T4/M1), Multi-Tier Visual Verification (S7), and FastAPI REST endpoints. This ADR records the authoritative architectural reconciliation, invariant resolution, authority separation, and verification gate semantics unified across all subsystems.
- **Architectural Invariants & Decisions:**
  1. **Canonical Nour Specification & Invariant Ground Truth:**
     - Ground-truth reference anchor verified at `runs/m0_visual/reference/nour_reference.png` (SHA-256: `b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644`, size 2,513,756 bytes).
     - Specification reconciliation:
       - 3 Required Invariants (`required=True`): `hair` (short messy black hair, white streak on left), `glasses` (round glasses), `jacket` (oversized hooded jacket, lightning-bolt patch on chest).
       - 1 Optional Checklist Attribute (`required=False`): `scar` (`id="scar"`, `text="small scar on right cheek"`).
     - Unified across `backend/tests/fixtures/benchmark_fixtures.py`, `backend/app/project/bible.py`, `docs/story_bible_example.json`, and `scripts/consistency_test.py`.
     - In accordance with the Rule of Closed Failure, an optional attribute failure does not reject the candidate, while any required attribute failure strictly rejects candidate acceptance.
  2. **Multi-Layer Authority Separation & Zero Conflicting Databases:**
     - **Execution & Budget Authority:** `ExecutionManager` (`backend/app/execution/manager.py`) is the single authority for run, operation, attempt, and event lifecycles, and atomic multi-scope Decimal budget accounting.
     - **Orchestrator adapter reconciliation:** `BatchOrchestrator` reserves through `start_attempt()` before provider dispatch, stores the manager's generated attempt ID, and settles through `complete_attempt()` using the actual supported signature. Manager errors are no longer silently ignored; absent provider cost remains `UNKNOWN` and null on the attempt record, while simulation costs remain `ESTIMATED`.
     - **Artifact & Lineage Authority:** `AssetRegistry` (`backend/app/storage/registry.py`) is the single authority for content-addressed artifact deduplication, SHA-256 validation, and parent-child lineage DAGs.
     - **Narrative & Canon Authority:** `StoryBible` (`backend/app/project/bible.py`) is the single authority for project definitions, immutable canon snapshots, and monotonic append-only state timelines.
     - **Checkpoint Reporting:** `BatchSummary` (JSON) serves as a serialized checkpoint report that derives from and never contradicts the append-only event ledger.
  3. **Lossless Canon & Schema Bridging:**
     - Full round-trip preservation between `backend/app/project/canon.py` and `backend/app/schemas.py`:
       - `StyleBible`: Preserves `line_art_rules`, `tonal_rules`, `positive_constraints`, `negative_constraints`, `lighting_constraints`, `background_detail_rules`, `color_palette`.
       - `CharacterDefinition.to_character_spec`: Preserves `name`, `visual_invariants`, `restrictions`, and `clothing_attributes`.
       - `StoryBible.to_orchestrator_bible`: Bridges `canon_hash` losslessly into orchestrator execution context.
       - Backward compatibility: `Tolerances` maps legacy `min_face_resolution_px` alias to `min_face_px_for_check`. `StoryBible` provides `create_canon_snapshot()` alias mapping to `get_canon_snapshot()`.
  4. **Deterministic Generation Fingerprints & Resumability Invariants:**
     - Fingerprints (`compute_context_fingerprint`) deterministically hash all generation-affecting inputs (Bible version, canon_hash, scene instructions, character invariants, state events, negative constraints, model ID, sampling parameters, aspect ratio, camera, lighting, and reference asset hashes).
     - Generated output files/hashes are strictly excluded from the generation input fingerprint.
     - Resume validation: previous outputs are reused if and only if the context fingerprint matches AND the output file exists on disk, has non-zero size, and matches its recorded SHA-256 content hash. Missing, truncated, or tampered output files trigger automatic panel regeneration.
  5. **Strict Tri-Tier Visual Verification Semantics (L0, L1, L2):**
     - **L0 Code Checker:** Validates decodability, dimension bounds, aspect ratios, and non-blankness. Adds explicit `asset_profile` parameter: `"panel"` allows clean solid/screentone backgrounds, whereas `"sheet"` enforces bleed margin limits.
     - **L1 Subject Checker:** Evaluates SAM 3.1 subject count, framing, and face scale thresholds. Live SAM API errors or network failures fail closed (`passed=False, is_simulated=False`) without silent fallback to simulated heuristic passes.
     - **L2 Multimodal Judge:** Dispatches candidate vs reference comparison to Meta Muse Spark. Enforces Rule of Closed Failure: all required attributes must pass; any failure or malformed output rejects the panel. `UNSURE` escalates to `NEEDS_HUMAN` and halts blind retries.
     - **Truthful Status Coherence:** `generated_panels` $\ne$ `verified_panels`. Unverified panels are labeled `UNVERIFIED`; visual verification is decoupled from generation completion.
  6. **Catalogue Governance & License Cleared Baseline:**
     - 60 groups and 840 canonical elements verified structurally and under anti-gaming rules.
     - Baseline asset licensing cleared: Nour reference image verified as proprietary original created for InkLoop by Mohamed Gomaa.
- **Verification Evidence:**
  - Orchestrator-to-ExecutionManager lifecycle, reservation, simulated estimate classification, and unknown provider cost: `backend/tests/test_m1_orchestration.py` (2 offline integration regressions).
  - 238 dedicated unit and integration tests passing in `backend/tests/` with zero regressions and zero failures.
  - Full suite execution time: ~10 seconds.
  - Zero live paid API spend incurred during automated test runs.

---

## ADR-015: Canvas Generation Engine Architecture, Deterministic Layout Templates, Polygon Geometry, and Spatial Previews
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN E2 / M3]
- **Context:** As part of Milestone M3 (Specialist Engine E2), InkLoop requires a dedicated backend Canvas Generation Engine to compute deterministic manga/manhwa page layouts, enforce physical print bounds (A4, B5, US Comic) and webtoon scrolls, calculate non-cumulative margins/gutters/bleeds, support polygonal diagonal panel cuts, and produce reproducible structural previews without coupling to image generation or frontend UI.
- **Architectural Invariants & Decisions:**
  1. **Canonical Spatial Coordinate System:**
     - Adheres strictly to `backend/app/contracts/geometry.py`: Origin at Top-Left (0.0, 0.0), +X axis pointing rightward, +Y axis pointing downward.
     - Discrete raster boundaries adhere to half-open intervals $[x, x + width) \times [y, y + height)$.
     - Derived coordinates are computed non-cumulatively from canonical usable width/height to eliminate floating-point drift.
     - Integer-pixel snapping (`snap_to_pixel_grid`) ensures exact grid alignment with bounded quantization error $\le 0.5$ px.
  2. **Core Domain Contracts (`backend/app/canvas/models.py`):**
     - `CanvasSpec`: Declares physical dimensions, DPI (default 300.0), color space, background, `MarginSpec`, `GutterSpec`, `BleedSpec`, and `SafeAreaSpec`. Includes standard presets (`create_a4`, `create_b5`, `create_us_comic`, `create_webtoon`).
     - `PageSpec`: Identifies page number, structural type (`PageType.SINGLE`, `SPREAD_LEFT`, `SPREAD_RIGHT`, `WEBTOON_SCROLL`), and `ReadingDirection` (`RTL` for Manga/Arabic vs `LTR` for Western/Webtoon).
     - `PanelSlot`: Stores canonical panel identifier, reading order, bounding `Rect`, optional polygon vertices (`List[Point]`), full-bleed flags, intentional overlap declaration, and stacking z-index.
     - `CanvasLayoutResult`: Single source of truth for both SVG and raster preview representations, containing exact envelopes for `trim_box`, `bleed_box`, `safe_area_box`, and `usable_box`.
  3. **Deterministic Layout Template Family (`backend/app/canvas/templates/`):**
     - **Manga Grid (`manga_grid`):** Configurable rows and columns with uniform or custom proportional ratios. Traverses columns right-to-left for RTL manga and left-to-right for LTR.
     - **Six-Panel Classic (`six_panel_classic`):** 3 rows of 2 panels with dramatic storytelling proportions (establishing row ~30%, action row ~38%, reaction row ~32%).
     - **Four-Koma (`four_koma`):** 4-panel vertical strip layout adhering to the traditional Ki-Shō-Ten-Ketsu narrative structure with uniform or rhythmic spacing.
     - **Dynamic Shonen (`dynamic_shonen`):** High-energy action layout with diagonal polygonal slash cuts. Computes exact trapezoidal vertices, validates positive area via shoelace formula, enforces non-self-intersection, and supports deterministic variation via explicit seed.
     - **Vertical Webtoon (`webtoon_vertical`):** Continuous vertical scroll layout with configurable panel heights, cinematic pacing gaps, and automatic canvas height derivation.
  4. **Strict Boundary Envelopes & Fail-Closed Spatial Validation:**
     - `trim_box` ($[0, 0, W, H)$), `bleed_box` ($[-B_l, -B_t, W+B_l+B_r, H+B_t+B_b)$), `safe_area_box` ($[S_l, S_t, W-S_l-S_r, H-S_t-S_b)$), `usable_box` ($[M_l, M_t, W-M_l-M_r, H-M_t-M_b)$).
     - Containment invariants: Ordinary panels must lie within `trim_box`; full-bleed panels must lie within `bleed_box`. Out-of-bounds panels fail with `OutOfBoundsLayoutError` (`ERR_2003_OUT_OF_BOUNDS`).
     - Pairwise overlap: Unintended intersections fail with `UnintendedOverlapError` (`ERR_2004_PANEL_UNINTENDED_OVERLAP`).
     - Insufficient space: Margins or gutters exceeding canvas size fail with `ImpossibleLayoutError` (`ERR_2007_IMPOSSIBLE_FIT`).
     - Resource limits: Width $\le 20,000$ px, height $\le 100,000$ px, and total pixels $\le 100,000,000$ px prevent allocation exhaustion (`AllocationLimitExceededError`).
  5. **Structural Preview Representations (`backend/app/canvas/previews/`):**
     - **SVG Structural Preview (`SVGPreviewGenerator`):** Generates valid, self-contained, byte-stable SVG with stable element IDs, grouped guide layers (bleed, trim, safe area, usable area), reading badges, and reading flow lines. Enforces XML entity escaping and strips script/event injection.
     - **Raster Structural Preview (`RasterPreviewGenerator`):** Renders clean structural outlines and badges via Pillow matching canonical geometry. Enforces maximum buffer allocation ceilings before memory allocation.
  6. **Clean Engine & API Boundaries:**
     - Adapts to shared engine contracts: `CanvasEngine.generate_from_params` losslessly produces `CanvasGenerationOutput`.
     - Exposes minimal REST endpoints under `/api/v1/canvas/` (`/templates`, `/generate`, `/preview/svg`).
     - Maintains clean separation: does not place images (E3), text (E4), bubbles (E6), or effects (E7), and touches zero frontend files.
- **Verification Evidence:**
  - 23 dedicated unit and integration tests passing in `backend/tests/test_canvas_engine.py`.
  - Full backend test suite: 262 passing tests with zero regressions and zero failures.
  - Zero live API spend incurred ($0.00).

---

## ADR-016: Image–Canvas Integration Engine Architecture, Mathematical Fitting, Polygonal Alpha Masking, and Lineage Tracking
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTED IN E3 / M4]
- **Context:** Following the completion and audit of the Canvas Generation Engine (E2), InkLoop requires the specialist Image–Canvas Integration Engine (E3) to map generated panel artwork into layout panel slots with strict aspect-ratio preservation, anchor-directed cropping, anti-aliased polygonal clipping, full-bleed boundary handling, and complete transformation provenance without modifying canvas geometry or rendering dialogue/bubbles/effects.
- **Architectural Invariants & Decisions:**
  1. **Strict Upstream Consumption & Decoupling:**
     - Consumes `CanvasLayoutResult` and its ordered `PanelSlot` instances produced by E2.
     - E3 operates strictly on image placement. It does not generate story text (E4), shape fonts (E5), place speech bubbles (E6), apply motion lines (E7), or compose finished books (S8).
  2. **Mathematical Transform Contract & Aspect-Ratio Preservation:**
     - Adheres to `calculate_fit_transform()` from `backend/app/contracts/geometry.py`.
     - `FitMode.COVER`: Scales uniformly to completely fill the target slot ($scale = \max(tw/sw, th/sh)$). Excess native resolution is cropped using normalized anchor points $[0.0, 1.0]$ without aspect-ratio distortion ($scale_x \equiv scale_y$).
     - `FitMode.CONTAIN`: Scales uniformly so the entire artwork fits inside the target slot ($scale = \min(tw/sw, th/sh)$) with transparent (or optional background color) letterbox padding.
     - `FitMode.STRETCH`: Non-uniform scaling permitted only under explicit override.
     - Any unintended aspect-ratio distortion under `CONTAIN` or `COVER` raises `AspectRatioDistortionError`.
  3. **Anchor & Focal-Point Directed Cropping:**
     - In `COVER` mode, `compute_source_crop_rect()` calculates the exact native source bounding box using normalized anchor coordinates `Point(x=anchor_x, y=anchor_y)`:
       - `(0.5, 0.5)`: Centered crop.
       - `(0.5, 0.0)` / `(0.5, 1.0)`: Top-aligned / bottom-aligned crop.
       - `(0.0, 0.5)` / `(1.0, 0.5)`: Left-aligned / right-aligned crop.
  4. **Anti-Aliased Polygonal Alpha Masking:**
     - For non-rectangular action panels (e.g. dynamic shonen diagonal cuts with `panel.has_polygon == True`), polygon vertices are mapped from PAGE coordinate space to local slot coordinate space: $(p.x - target.x, p.y - target.y)$.
     - An 8-bit alpha mask (`L` mode) is drawn via Pillow (`ImageDraw.polygon`), preserving anti-aliased edges and compositing with the source image's existing alpha channel (`Image.composite`).
     - Pixels outside the polygon are masked to 100% transparency ($\alpha = 0$), while pixels inside remain fully visible ($\alpha = 255$).
  5. **Full-Bleed Envelope Handling:**
     - When `panel.is_full_bleed == True` and `allow_bleed == True`, the target slot rectangle is expanded to the outer `bleed_box` or declared bleed edges before transform calculation.
  6. **Lineage Tracking, Determinism & Provenance:**
     - Produces structured `PlacedPanelLayer` artifacts recording `layer_id`, `panel_id`, `source_content_hash`, `output_content_hash`, native `source_dimensions`, `placed_rect`, `local_rect`, `transform_applied` (`Transform2D`), and clipping flags.
     - Deterministic PNG encoding guarantees byte-stable outputs for identical inputs.
     - Adapts losslessly to `ImageCanvasIntegrationOutput` from shared engine contracts.
  7. **Defensive Allocation & Memory Safeguards:**
     - Source images exceeding $20,000 \times 20,000$ px or $100,000,000$ total pixels raise `AllocationLimitExceededError`.
     - Corrupted or unparsable image bytes raise `UnsupportedImageFormatError`.
- **Verification Evidence:**
  - 14 dedicated unit and integration tests passing in `backend/tests/test_image_canvas_integration.py`.
  - 49 geometry and canvas tests passing across `contracts/geometry.py` and `canvas/`.
  - Full backend test suite: 276 passing tests with zero regressions and zero failures (10.02s execution).
  - Zero live API spend incurred ($0.00).

### ADR-017: Knowledge Catalogue Deterministic Retrieval & Image-Generation Context Integration (Task T6.3)
- **Status:** Approved / Implemented
- **Date:** 2026-10-29
- **Context:**
  InkLoop requires connecting its authoritative 60-group / 840-element image knowledge catalogue to the real image-generation context compilation path (E1) without flat prompt concatenation, prompt-stuffing, external vector databases, unapproved LLM dependencies, or live paid API spend. Knowledge records must be selected based on active scene signals, governed by research confidence, filtered for compatibility, bounded by explicit budgets, and traced with immutable provenance.
- **Decisions:**
  1. **Typed Retrieval Domain Contracts (`backend/app/catalogue/retrieval_models.py`):**
     - `KnowledgeRetrievalRequest`: Typed query contract capturing scene framing, shot scale, action, camera angle, lighting, panel instructions, character IDs, canonical reference presence, visual invariants, style linework/tonal rules, palette, and positive/negative constraints.
     - `KnowledgeBudget`: Enforces strict capacity limits on injected rules (`max_rules=3`), recipes (`max_recipes=1`), claims (`max_claims=2`), and approximate prompt tokens (`max_prompt_tokens_approx=150`).
     - `KnowledgeRetrievalPolicy`: Controls status threshold (`min_coverage_status=RESEARCHED`), hypothesis inclusion (`allow_hypotheses=False`), provenance requirements (`require_provenance=True`), and empty-selection behavior.
     - `CandidateEvaluation` & `KnowledgeRetrievalResult`: Transparent audit trail recording scores, signal matches, exclusion reasons, budget consumption, and positive/negative prompt clauses.
  2. **Deterministic Relevance Scoring & Explainable Tie-Breaking:**
     - Signals are extracted purely from scene and style context without hidden state.
     - Scoring weights combine signal match strength (+10 to +25 for canonical element/anchor matches), group research status (`VALIDATED`: +15, `EXPERIMENTALLY_TESTED`: +10, `RESEARCHED`: +5), and rule priority (`HIGH`: +3, `MEDIUM`: +1.5, `LOW`: +0).
     - Deterministic tie-breaking sorts candidates by `(-relevance_score, -priority_weight, group_number, record_id)`. Identical inputs yield identical selections.
  3. **Strict Compatibility & Negative Constraint Precedence:**
     - Rules declaring `conflicting_concepts` are checked against active scene/style tokens; detected clashes are excluded with reason `CONFLICTING_CONCEPT`.
     - Hard negative constraints and character restrictions take absolute precedence over catalogue rules. Any positive directive contradicting a negative rule is excluded as `CONTRADICTS_NEGATIVE_CONSTRAINT`.
  4. **E1 Context Builder & Fingerprint Invalidation:**
     - Hooked directly into `build_panel_context_packet()` in `backend/app/context_builder.py`.
     - Injected positive clauses form a clean prompt section: `Catalogue guidance: ...`.
     - Negative clauses merge cleanly into `prohibited_deviations`.
     - Context fingerprint computation includes `catalogue_version`, `knowledge_selection_hash`, and `selected_knowledge_ids`. Any change to catalogue records or retrieved recipes invalidates downstream panel fingerprints, preventing stale cache reuse during `BatchOrchestrator.resume_batch()`.
  5. **Provenance & Execution Manager Logging:**
     - Every selected item is backed by indexed `SourceRecord` instances declaring `what_it_establishes` vs `what_it_does_not_establish`.
     - `GenerationAttemptRecord.sanitized_request_metadata` records `catalogue_version`, `knowledge_selection_hash`, `selected_knowledge_ids`, and `knowledge_provenance_ids`.
  6. **Dry-Run & Explain Operation:**
     - `KnowledgeRetriever.explain()` and REST endpoint `POST /api/v1/catalogue/explain` generate comprehensive Markdown evaluation reports showing candidates, scores, rationale, exclusions, and budget consumption without invoking generative models.
  7. **Research Maturity & Status Integrity:**
     - Current register status: 45 groups are `UNRESEARCHED`, 14 are `RESEARCHED`, 1 is `EXPERIMENTALLY_TESTED` (Group 60), and 0 are `VALIDATED`. Structural completeness is never conflated with empirical validation.
- **Verification Evidence:**
  - 16 dedicated unit and integration tests passing in `backend/tests/test_catalogue_retrieval.py`.
  - 20 catalogue and governance tests passing in `backend/tests/test_image_knowledge_catalogue.py`.
  - Full backend test suite: 295 passing tests with zero regressions and zero failures (10.67s execution).
  - Zero live API spend incurred ($0.00).

---

## ADR-018: Structured Text Generation Engine & Semantic Continuity Architecture (Workstream E4)
- **Status:** [VERIFIED ARCHITECTURE & IMPLEMENTATION]
- **Date:** 2026-10-29
- **Context:**
  InkLoop requires a dedicated, typed, and deterministic Text Generation Engine (Engine E4) to create, ingest, structure, and validate all narrative text blocks—dialogue, narration, captions, inner monologue, off-panel speech, interrupted/fading speech, and sound-effect words.
  The engine must guarantee character voice, narrative timeline continuity, Story Bible / Canon adherence, and exact code-point immutability for user-authored text without conflating semantic text generation with downstream typography shaping (E5) or speech bubble geometry (E6).
- **Decisions:**
  1. **Strict Separation of Semantic Text from Visual Layout:**
     - E4 is restricted to generating semantic text artifacts, delivery traits, reading order, and length guidance.
     - Glyph shaping, kerning, line-breaking metrics, and font generation are deferred to E5. Bubble bounds, tails, and spatial placement are deferred to E6.
  2. **Domain Models & Script Block Primitives (`backend/app/text/models.py`):**
     - `ScriptBlock`: Atomic narrative unit defining `block_id`, `scene_id`, `panel_id`, `block_kind`, `reading_order_index`, `text_content`, `language`, `direction`, `is_exact_user_text`, `provenance`, `speaker`, `delivery`, `caption_kind`, `sfx_category`, and `length_guidance`.
     - `TextScriptManifest`: Verifiable container bundling accepted blocks, canon hash, bible version, reading order, and diagnostic logs.
     - `SpeakerRef` & `TextProvenance`: Traceability primitives recording speaker declaration, voice traits, source passage ID, source text hash, and model metadata.
  3. **Exact User Text Immutability Invariant:**
     - When `SourceMode.USER_EXACT` is requested, the text engine guarantees byte-for-byte and code-point-by-code-point preservation.
     - Any modification (translation, paraphrasing, punctuation alteration, diacritic stripping) triggers `DiagnosticCode.EXACT_TEXT_ALTERATION` and rejects the block.
  4. **Story Bible & Canon State Invariants:**
     - All character speakers must be declared in the active `StoryBible` or `CanonSnapshot`. Undeclared entities fail closed with `DiagnosticCode.UNDECLARED_SPEAKER` (ERROR severity).
     - Timeline state is resolved via `resolve_timeline_state()`. If a character is marked `unconscious`, `asleep`, `knocked_out`, or `gagged`, dialogue speech fails closed with `DiagnosticCode.CANON_STATE_CONTRADICTION`. Internal monologue remains permitted.
     - `CanonSnapshot` immutability is preserved; passing canon objects to E4 cannot mutate state or mappings.
  5. **Multilingual Script & Directionality Semantics:**
     - Full native support for Arabic (with tashkeel/diacritics), English, and mixed-script text.
     - Logical character order is strictly preserved in memory. Text direction is stored as semantic metadata (`TextDirection.RTL` / `LTR`) without visual string inversion.
  6. **Provider-Neutral Adapter Architecture & Zero Live Spend:**
     - `SimulatedTextGenerationAdapter`: Fast, deterministic offline generation for unit and integration testing ($0.00 spend).
     - `MetaTextGenerationAdapter`: Live Meta Model API stub that fails closed when unconfigured without generating hallucinatory mock data.
  7. **Adaptation to Shared Engine Contracts (`backend/app/contracts/engine.py`):**
     - Adapts `TextGenerationParams` to `EngineRunResponse[TextGenerationOutput]` featuring `TextScriptManifest`, metrics, and execution metadata.
  8. **REST Router Integration (`backend/app/api/routers/text.py`):**
     - Endpoints mounted under `/api/v1/text`: `POST /validate`, `POST /ingest`, `POST /generate`.
- **Verification Evidence:**
  - 17 dedicated unit and integration tests passing in `backend/tests/test_text_generation.py`.
  - Full backend test suite: 312 passing tests with zero regressions and zero failures (11.83s execution).
  - Zero live API spend incurred ($0.00).


## ADR-019: AI Creative Director, Character Maker & Universe Builder Architecture

- **Date:** 2026-10-29
- **Status:** Accepted & Verified
- **Context:**
  InkLoop requires an end-to-end, production-oriented AI Creative Director and Universe Builder capable of transforming natural-language briefs into coherent, editable, versioned creative-production packages. The system must not act as a mere prompt generator or chat form; it must connect directly to InkLoop's Story Bible, Character Copier, Style Copier, down-stream prompt compilers, and cross-document validation engines.
- **Decisions & Implementation Architecture:**
  1. **16-Stage Deterministic Pipeline (`backend/app/creative/service.py`):**
     - Executes sequential stages: `UNDERSTAND_BRIEF`, `EXPAND_CORE_PREMISE`, `GENERATE_STORY_BIBLE`, `DEVELOP_MAIN_CHARACTERS`, `BUILD_ENSEMBLE_RELATIONSHIPS`, `DESIGN_WORLD_AND_LOCATIONS`, `FORMULATE_NARRATIVE_STRUCTURE`, `DEFINE_VISUAL_STYLE`, `MAP_STYLE_TO_CHARACTERS`, `CREATE_CHARACTER_SHEET_PLANS`, `VALIDATE_COHERENCE`, `PRESENT_REVIEW_PACKAGE`, `WAIT_FOR_APPROVAL_WHERE_REQUIRED`, `SAVE_APPROVED_VERSIONS`, `OPTIONALLY_QUEUE_REFERENCE_SHEETS`, `COMPLETE_WITH_RECEIPT`.
     - Operates in offline mode with deterministic synthesis ($0.00 spend).
  2. **Fact Classification & Evidence Tracking (`backend/app/creative/schemas.py`):**
     - Classifies brief statements into `EXPLICIT_USER_FACT`, `AGENT_PROPOSAL`, and `OPEN_QUESTION`.
     - Preserves user creative ownership without hallucinating unconfirmed canon.
  3. **Supernatural Rule Constraints & Anti-God-Mode Stakes:**
     - In `MagicOrTechAbilityRule`, every supernatural or technological ability strictly requires defined `cost_or_strain` and `absolute_limit`. Omission fails closed as a coherence violation.
  4. **Cross-Document Coherence Validator (`backend/app/creative/validator.py`):**
     - Deterministically verifies invariant retention, relationship referential integrity, narrative act progression, and flags active `StoryBible` canon conflicts.
  5. **Human Canon Mutation Approval & Reversibility:**
     - Prohibits silent mutation of approved Story Bible canon.
     - Commits proposals only upon explicit human approval, monotonically incrementing `bible_version` and recalculating cryptographic `canon_hash`.
  6. **Downstream Production Prompt Compilation (`backend/app/creative/prompt_compiler.py`):**
     - Directly consumes `CreativeContractsPackage` and `CharacterIdentityProfile` to compile prompt tokens with strict instruction precedence (action intent -> mandatory invariants & wardrobe -> visual style -> environment -> negative constraints).
  7. **Fullstack Integration:**
     - Backend REST endpoints mounted under `/api/v1/creative`: `POST /develop`, `GET /package/{project_id}`, `POST /validate/{project_id}`, `POST /approve`, `GET /contracts/{project_id}`, `POST /compile-prompt`.
     - Agent runtime tools registered in `backend/app/agent/registry.py`: `creative.develop_universe`, `creative.get_package`, `creative.validate_coherence`, `creative.approve_canon`.
     - Frontend UI view in `frontend/src/views/CreativeDirectorView.tsx` with mode switcher, 8 deliverable tabs, interactive prompt compiler sandbox, and human approval banner.
- **Verification Evidence:**
  - 7 dedicated unit and integration tests passing in `backend/tests/test_creative_director.py`.
  - Frontend production build (`npm run build`) passing with zero TypeScript errors.
  - Acceptance scenario executed and verified across all 12 criteria (`scripts/verify_creative_acceptance.py`).
  - Zero live API spend incurred ($0.00).
