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
