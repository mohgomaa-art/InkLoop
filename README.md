# InkLoop 🎨📖

> **Turn original stories into illustrated books where characters and art style never drift.**
> Built for the Meta Global AI Developer Hackathon 2026 · Track: Indie Developer · Theme: Build for Your World.

---

## The Core Thesis: Consistency is an Engineering Problem

Generating a single compelling comic panel is easy. Generating an entire illustrated book where characters, clothing, props, and art styles remain consistent across 16 panels has historically resulted in high drift and low yield (~20% usable panels in standard workflows).

InkLoop solves this not with prompt tricks or model memory, but with a **deterministic engineering pipeline**:
1. **External Structured Memory (Story Bible):** Character sheets, style locks, and state timelines live in versioned files on disk—never in model context windows.
2. **Fresh Per-Panel Continuity Packet:** Pure code builds a minimal, isolated context for each panel anchored to the canonical Bible.
3. **Multi-Tiered Verification Loop:**
   - **L0 Code:** Aspect ratio, blank panel detection, sheet bleed check, text leakage check.
   - **L1 SAM 3.1:** Character count, subject framing, face bounding box dimensions.
   - **L2 Muse Spark Judge:** Multimodal visual comparison of anchor vs panel against declared attribute checklists. Remove/reject only—the judge never mutates the plan.
4. **Targeted, Bounded Retries:** Retries add specific corrections (e.g. "restore white hair streak on the left") or simplify shots, subject to a hard budget cap.
5. **Deterministic Code Layout & Lettering:** Real text layout in HTML/SVG rendered to PDF via Chromium, with native Arabic RTL shaping and OFL typography.
6. **Empirical Benchmarks:** Rigorous measurement of Drift Rate, First-Pass Yield, Cost/Panel, and Verifier Agreement.

---

## Repository Structure

```
inkloop/
├── INKLOOP_PROJECT_BRIEF.md   # Complete project specification and hackathon rules
├── CONTRIBUTIONS.md           # Work completed during hackathon with timestamps
├── README.md                  # Project overview, setup, and results
├── docs/                      # Architectural decisions and milestone audit reports
│   ├── decisions.md           # Architecture Decision Records (ADRs)
│   └── m0-report.md           # M0 Day-0 verification audit report
├── backend/                   # FastAPI backend & orchestration engine
│   ├── app/                   # Core pipeline modules
│   └── tests/                 # Unit and verification tests
├── frontend/                  # 4-step wizard UI (React + Vite + TypeScript)
├── assets/fonts/              # Bundled OFL comic fonts (Arabic & Latin)
├── templates/                 # Deterministic layout definitions (JSON)
├── runs/                      # Auditable benchmark runs (JSONL)
└── scripts/                   # M0 test harnesses and benchmark runners
```

---

## Setup & Running M0 Smoke Tests

### Prerequisites
- Python 3.11+
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/inkloop.git
cd inkloop

# Copy environment template and add your Meta Model API credentials
cp .env.example .env
# Edit .env with your META_API_KEY

# Run unit tests
pytest backend/tests/
```
