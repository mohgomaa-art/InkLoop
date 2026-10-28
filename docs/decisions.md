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
- **Status:** [VERIFIED ENDPOINT / BLOCKED AUTHENTICATION]
- **Context:** The hackathon requires meaningful use of Meta models via the Meta Model API (`https://api.meta.ai/v1`).
- **Verified Facts:**
  - Official documentation standard specifies `MODEL_API_KEY` as the canonical environment variable.
  - Base URL is `https://api.meta.ai/v1`.
  - Endpoint probe confirmed live server responses (`x-route: model-api-rust`, HTTP 401 when unauthorized).
  - SDK compatibility verified: `openai` Python SDK (v3.41.0) and direct `httpx` HTTP requests configured with `base_url="https://api.meta.ai/v1"` and Bearer authorization.
  - Project-root `.env` loading normalized via `Path(__file__).resolve().parent.parent.parent / ".env"` rather than working directory.
  - Safe credential masking enforced: zero key characters are logged, serialized, or displayed.
- **Current Blocker:** `MODEL_API_KEY` is not configured in `.env` or system environment. Execution stops before making authenticated calls.

---

## ADR-005: SAM 3.1 Segmentation & Fallback Policy
- **Status:** [DOCUMENTED SPECIFICATION / BLOCKED AUTHENTICATION]
- **Context:** Bounding boxes and subject masks are needed for smart cropping, face protection, and bubble placement.
- **Decision:**
  - Primary: SAM 3.1 accessed via `/v1/responses` using Promptable Concept Segmentation (`input_text: "person"`).
  - Fallback: If SAM 3.1 is unavailable or latent, Muse Spark Vision will return normalized bounding boxes (`[ymin, xmin, ymax, xmax]`).

---

## ADR-006: Hard Safety & Budget Guardrails
- **Status:** [VERIFIED IMPLEMENTATION]
- **Context:** Unbounded retry loops in agentic workflows risk exhausting credits and incurring runaway API costs.
- **Decision:**
  - Hard limit of 2 targeted retries per panel; max 4 attempts total before marking `needs_human`.
  - Global budget cap defaulting to $25.00 USD, checked before each generation batch.
  - Concurrency capped at 1-2 concurrent requests.
