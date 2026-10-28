# InkLoop — Hackathon Contributions Log

This document records all software engineering work, architectural artifacts, tests, benchmarks, and assets produced during the **Meta Global AI Developer Hackathon (Oct 26 – Nov 4, 2026)**.

In strict compliance with hackathon regulations:
- All code, documentation, schemas, and configurations listed below are built completely from scratch during the hackathon period.
- No code, datasets, characters, or graphic assets are imported or reused from previous projects.
- All dependencies and third-party libraries use open-source licenses (MIT, Apache 2.0, OFL).

---

## Timeline & Milestones

### Milestone 0: Day-0 Technical Feasibility & Foundation (Thu Oct 29, 2026)
- **Repo & Hygiene:**
  - Initialized clean public repository structure.
  - Implemented `.gitignore` with strict security exclusions (keys, `.env`, tokens, binary caches).
  - Created `.env.example` defining required Meta API configurations, model identifiers, and spend bounds.
- **Architectural & Specification Documents:**
  - `docs/decisions.md`: Architecture decision records (ADRs) tracking verified assumptions, model endpoint shapes, and fallback strategies.
  - `docs/m0-report.md`: Complete audit and empirical verification report for Milestone 0.
- **Feasibility & Benchmark Test Harnesses:**
  - `scripts/api_smoke_test.py`: Probe Meta Model API (`https://api.meta.ai/v1`) connectivity, authentication invariants, and model catalog.
  - `scripts/consistency_test.py`: Controlled 6-scene character consistency benchmark comparing Arm A (text-only) vs Arm B (anchored `/v1/images/edits`) with hard budget caps.
  - `scripts/verifier_smoke_test.py`: L2 Muse Spark multimodal verification harness validating character attribute checklists against structured JSON schemas.
  - `scripts/sam_smoke_test.py`: SAM 3.1 promptable segmentation and bounding box verification harness with fallback support.
- **Defensive Backend Unit Tests:**
  - `backend/tests/test_m0_foundation.py`: Automated tests verifying environment configuration, pydantic schema validation for Character Story Bible and Verifier reports, and spend cap safety guards.
