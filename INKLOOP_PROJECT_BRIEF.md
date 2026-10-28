# InkLoop — Project Brief & Engineering Plan

**Working name.** Meta Global AI Developer Hackathon · Track: **Indie Developer** · Theme: **Build for Your World** · Solo
**Written:** Thu Oct 29, 2026 · **Deadline:** Wed Nov 4, 9:00 PM ET (≈ 4:00 AM Cairo on Nov 5 — verify the offset, DST changed this week)

> **Audience:** Mohamed + coding agents (Claude Code, Antigravity). Agents: read sections 1, 3, 5, 9, 10 before writing any code.
>
> **Status tags used below:** `[VERIFIED]` confirmed from docs/rules text · `[TO VERIFY]` assumption, test on Day 0 · `[DECISION]` a choice made · `[RISK]` something that can sink us.

---

## 0. TL;DR

**EN.** InkLoop turns a story into a finished illustrated book where characters and art style never drift. The user does 4 simple steps; behind the scenes a deterministic pipeline keeps the "canon" (characters, style, places, story state) in **external files**, not in the model's memory, builds a fresh context for every panel, **verifies** every image against the canon, regenerates failures, and lays everything out with **code** (templates, real fonts, RTL). The proof is a **benchmark**: drift rate and cost per accepted panel with and without the verification loop.

**AR.** InkLoop بياخد قصة ويطلعها كتاب مصور كامل الشخصيات والستايل فيه ثابتين. المستخدم بيعمل 4 خطوات بس. من ورا الكواليس: الذاكرة (الشخصيات، الستايل، الأماكن، حالة القصة) **ملفات خارجية** مش في دماغ الموديل، وكل بانيل بيتبني له context جديد من الصفر، وكل صورة **بتتفحص** قصاد الـ canon والفاشل بيتعاد، والتخطيط والنص والخطوط **بالكود**. الإثبات: **أرقام** (نسبة الانحراف وتكلفة البانيل المقبول) مع وبدون حلقة الفحص.

---

## 1. Hard constraints (breaking these can disqualify the project)

| Rule | What it means for us |
|---|---|
| **New work only** `[VERIFIED]` | Everything shown must be built during the event. **New public repo, first commit on day 1.** Commit history is our proof. |
| **Demo shows only hackathon-built work** `[VERIFIED]` | No old assets in the demo. **Do NOT import or show anything from: Interactive Cases, Dr. Fouad story images, ArtForge, Dual Draw, Still Human, NotebookMG.** No copied code from them. Write a fresh canvas/layout engine on open-source libraries. |
| **Public repo** `[VERIFIED]` | GitHub public, accessible without login. No API keys, ever (`.env` is gitignored; add a pre-commit secret scan). |
| **3-minute demo video** `[VERIFIED]` | One of the main scoring artifacts. Plan it early (section 12). |
| **Banned / avoid list** `[VERIFIED]` | AI medical advice, basic RAG, simple image analyzers, simple "AI for education" chatbots, job screeners, nutrition coaches, personality analyzers, sports analyzers, anything political or about war. **Demo story must be neutral: no medical, education, politics, war, religion.** |
| **Must use Meta models** `[VERIFIED]` | Stage 1 is pass/fail on "fits theme + reasonably used Meta Model API / open weights". |
| **Rights to code/data/assets** `[VERIFIED]` | Fonts: OFL / open license only, record license per font. Libraries: record license. **No "in the style of <named artist/franchise>" in prompts.** Demo story/characters must be original. |
| **Submission** `[VERIFIED]` | Organizers confirmed we can **edit the existing submission** until the deadline; credits unaffected. One submitter, all members listed (solo = just Mohamed). |

**Scoring weights** `[VERIFIED]`: Impact 30% · Use of Meta tooling 25% · Technical depth 20% · Demo 25%.
**Bonus prizes we can target:** Best Build on Open Weights ($10K, needs Glimmer / Spark Open) · Best Agentic Use-Case ($5K) · Best Creative Build ($5K, Muse Image/Wonder) · Most Viral ($20K, post demo on X) · Community Vote ($10K).

---

## 2. Product

### 2.1 Problem (first-hand)
Amateurs generate comic panels with general tools; the **character and style change from image to image**. Mohamed's own experience on an earlier comic: roughly **1000 generations to get ~200 usable, consistent images** (≈20% yield; an anecdote — we must re-measure it in the benchmark, with new assets, during the hackathon).

### 2.2 User-facing flow (4 steps — keep the UI this simple)
1. **Characters & style.** System generates 3–4 candidate designs → user picks one → system builds and **locks** a Style Bible (multi-view sheet, expressions, palette notes).
2. **Cast.** Name the main characters, short traits, outfits. (Everything the story is allowed to contain is declared here.)
3. **Story.** Write/paste the story and key events (user's own text).
4. **Language & lettering.** Choose language (Arabic/English, RTL/LTR). **Text is the user's original text rendered by code with real fonts — never generated inside images.**
→ Output: a complete book (PDF + page PNGs), same style and same characters throughout.

### 2.3 Non-goals (cut hard)
Free-form canvas editor · 10 styles · video · social features · accounts/payments · mobile app · medical/educational content. **Ship 3 polished styles max** (art-directed by Mohamed, an illustrator — this is a differentiator).

### 2.4 Why this can win (honest reasoning)
- Pain is real and **measured**; most Discord ideas are not.
- Meta's own Muse Image docs recommend exactly our pattern (anchored composition: build reference images once, pass them on every render) `[VERIFIED]`.
- Demo = a finished book flipping on screen + a live "drift caught and fixed" moment. Easy to understand in 3 minutes.
- **Crowded space** (video editors, asset generators, PixiTween). We separate by **numbers + engineering of consistency**, not by "AI comics".

---

## 3. Core thesis — consistency is an engineering problem

Three rules (everything else follows):

1. **Memory is external and structured.** The model never "remembers" the character. A versioned **Story Bible** on disk is the single source of truth.
2. **Every call gets a fresh, minimal context assembled by code** (the *continuity packet*). No growing chat history → no context drift, no forgetting.
3. **Nothing is accepted without verification** against the Bible, and **the checker can only remove, never add** (code enforces; the model only returns pass/fail/unsure per attribute).

**Metrics (the proof):**
- **Drift rate** = % of accepted panels failing a *human* blind check on the character checklist.
- **First-pass yield** = % of generated candidates accepted without retry.
- **Attempts per accepted panel**, **$ per accepted panel**, **seconds per page**.
- **Verifier quality** = agreement with human labels (precision/recall on ~60 labeled panels). Without this, "zero deviation" is just the judge grading itself.

> **Wording discipline:** never claim "zero errors" in the video. Claim: *"every accepted panel passes a checklist; here is the measured drift rate with and without the loop."* If the final demo story really has zero failures, show the log and say so.

---

## 4. Meta models & roles

| Model | Role in InkLoop | Status |
|---|---|---|
| **Muse Image** (`muse-image-1.0`) | Character sheets (anchors) + every panel via `/v1/images/edits` with references | `[VERIFIED]` OpenAI-compatible: `POST /v1/images/generations`, `POST /v1/images/edits` (also multi-image composition); base URL `https://api.meta.ai/v1` |
| **Muse Spark** | (a) **Director**: story → structured panel plan (schema-validated). (b) **Judge**: vision comparison anchor vs panel → strict JSON. (c) **Bible-mutation proposals** (new props/locations). | model id `[TO VERIFY]` via `client.models.list()`; vision input `[TO VERIFY]` |
| **SAM 3.1** | Subject bbox/mask (smart crop that never cuts the face), character count check, **free-space map for bubbles**, speaker position for bubble tails | endpoint & output format `[TO VERIFY]` — put behind a `Segmenter` interface; fallback = Spark returns boxes |
| **Muse Glimmer 30B / Spark Open** | Optional **second judge** on open weights (Modal/Baseten) → eligible for Open-Weights prize | `[TO VERIFY]` partner credits; Baseten note: use `meta-models/muse-spark-open-1026` |
| **Muse Voice Transcribe** | *Stretch only*: tell the story by voice (Arabic) | cut by default |
| **Muse Wonder** | Unknown to us | `[TO VERIFY]` what it is before planning around it |

**Pricing** `[TO VERIFY on the Billing page]`: Mohamed reports ≈ **$2.5 per 1000 images**; a third-party page reports a flat $0.01/image and that failed/filtered images aren't billed. Either way **images are cheap; Spark judge calls are the real cost.** Rate limits are unpublished → build in backoff + a global concurrency cap.

**Architecture rule:** `ImageGen`, `Judge`, `Segmenter` are interfaces. Mocks exist **only in unit tests**, never in the demo path.

---

## 5. Architecture

```
 User (4-step wizard, React)
        │  story text + choices
        ▼
 ┌────────────────────────── FastAPI backend ──────────────────────────┐
 │  Orchestrator (deterministic state machine; LLM only at decisions)  │
 │                                                                     │
 │  Story Bible (files)  ──►  Continuity Packet builder (pure code)    │
 │   canon (read-only)             │                                   │
 │   state timeline                ▼                                   │
 │                         Panel Generator (stateless)                 │
 │                          Muse Image /images/edits + refs            │
 │                                │  N candidates                      │
 │                                ▼                                    │
 │            Verifier:  L0 code → L1 SAM → L2 Spark judge (→ L3 2nd)  │
 │                                │ pass            │ fail             │
 │                                ▼                 ▼                  │
 │                         accepted panel     targeted retry / simplify│
 │                                │                                    │
 │                                ▼                                    │
 │   Layout engine: template JSON + SAM fit + bubbles (code) + fonts   │
 │                                │                                    │
 │                                ▼                                    │
 │               HTML/SVG pages ──► Chromium (Playwright) ──► PDF/PNG  │
 │                                                                     │
 │  Run log (SQLite): every attempt, score, cost, latency → benchmark  │
 └─────────────────────────────────────────────────────────────────────┘
```

**[DECISION] Pipeline, not a free-roaming agent.** A deterministic state machine with LLM calls at decision points (plan, choose template, judge, decide retry strategy). It is more reliable, debuggable, and still "agentic" in the ways judges look for (autonomy, multi-step decisions, self-correction). Be honest about this in the README.

### 5.1 Story Bible = the memory

Three layers:

| Layer | Contents | Mutability |
|---|---|---|
| **Canon** | style lock, character sheets + specs, location refs | immutable per run; versioned by content hash |
| **State timeline** | per-panel facts: outfit changes, injuries, props held, time of day, weather | append-only; each entry cites the panel that created it |
| **Run log** | attempts, scores, costs | analytics only; never fed back to the model |

```
bible/
  style.json                  # name, medium, line/tone rules, palette or "B&W + screentone", negative rules
  characters/<id>/
    sheet.png                 # anchor (front/side/expressions)  — generated once, user-approved
    spec.json                 # checklist attributes (see below)
  locations/<id>/ref.png + spec.json
  state.jsonl                 # {panel_id, entity, field, old, new}
```

`spec.json` for a character — the **checklist the judge uses** (this is where "what counts as the same character" is defined; Mohamed's illustrator judgment goes here):
```json
{
  "id": "nour",
  "attributes": [
    {"id":"hair",   "text":"short messy black hair, one white streak on the left", "required":true},
    {"id":"glasses","text":"round glasses",                                         "required":true},
    {"id":"jacket", "text":"oversized hooded jacket, lightning-bolt patch on chest","required":true},
    {"id":"scar",   "text":"small scar on right cheek",                             "required":false}
  ],
  "tolerances": {"min_face_px_for_check": 80}
}
```

**Anti-hallucination rule:** the planner may only use entities declared in the Bible. A new character/prop/location **cannot appear silently** — it must go through an explicit *Bible mutation* (auto-generate its ref + user approval, or reject). Plans are validated with pydantic; invalid plans are rejected and retried.

### 5.2 Continuity Packet (assembled by code, per panel)
- style lock text + style ref image(s)
- refs for **only the characters in this panel** (and the location ref, if recurring)
- **current state** of those entities (from `state.jsonl` up to this panel)
- the panel's own beat (shot type, action, camera, light) + one-line summary of the previous panel
- negative rules ("no text, no speech bubbles, no watermark, exactly N characters")

**Always anchor to the original sheet, never to the previous panel** (copying copies → drift accumulates).

### 5.3 Panel Generator
- Stateless function: `generate(packet, n=2..3) -> candidates[]`. Fresh context every call.
- Generate **at the panel's aspect ratio** (see 5.6) — don't crop later.
- Best-of-N in parallel is cheap; judge calls are the cost → keep N small (2–3) and gate with L0/L1 first.

### 5.4 Verifier (cheap → expensive; reject early)
| Layer | Checks | Cost |
|---|---|---|
| **L0 code** | valid image, not blank, correct aspect, **sheet-bleed** (output too similar to the anchor sheet / white sheet margins), no big uniform area, optional OCR for **baked-in text** | free |
| **L1 SAM 3.1** | expected character count (no extra/missing people), subject bbox size within the shot-type range, subject not cut off, face size ≥ threshold for identity check | cheap |
| **L2 Spark judge** | input: anchor sheet + candidate (+ location ref) + checklist from `spec.json` + state facts. **Output strict JSON:** `{attr_id: "pass"|"fail"|"unsure", "evidence": "..."}`. Code accepts only if **all required = pass** (`unsure` = fail). | main cost |
| **L3 optional** | second judge on Glimmer/Spark Open; or pairwise pick between survivors | optional |

**Remove-only principle:** the judge never edits the plan or adds content; code decides from its yes/no flags. Calibrate the judge: label ~60 panels by hand, report agreement. If agreement is poor, the benchmark claim is void — fix the judge first.

### 5.5 Retry policy
1. Failed attribute(s) → add a **targeted instruction** ("hair must have the white streak on the LEFT") and regenerate.
2. After 2 failures → **simplify** the shot (wider/closer, fewer characters, simpler background).
3. After K attempts (default 4) → mark `needs_human`. **In the benchmark this counts as a failure** — don't hide it.
4. Global **budget cap** per book and per day (credits are finite; a loop bug must not drain $150).

### 5.6 Layout engine (templates) — the "book" part
- Template = JSON; code renders it. **Start with 5 templates**: splash (1), 2 stacked, 1 wide + 2, 2×2 grid, wide-strip + 3. No slanted panels in v1.
```json
{
  "id": "wide_plus_two", "page": {"w":1600,"h":2400,"margin":80,"gutter":24},
  "reading_order": "rtl",
  "panels": [
    {"id":"p1","x":80,"y":80,"w":1440,"h":900},
    {"id":"p2","x":80,"y":1004,"w":708,"h":1316},
    {"id":"p3","x":812,"y":1004,"w":708,"h":1316}
  ]
}
```
- **Template chosen before generation** (Spark picks per scene: action → wide, dialogue → grid, emotional beat → splash). Each image is generated for its panel's aspect ratio. `[TO VERIFY]` whether `size`/aspect is configurable; if not → restrict templates to 3 ratios (square, wide, tall) and use `images.edit` outpainting only if needed.
- **Fit:** `cover` with a **focal point from the SAM bbox**; the crop must contain the subject bbox. If impossible → mark and regenerate at a better ratio.
- **Bubbles (code):** types speech/thought/shout/caption. Candidate positions from the SAM **free-space map**; choose the position nearest the speaker, away from faces; tail points to the speaker bbox. Autosize text (binary search); minimum readable font size; if it doesn't fit → flag (never rewrite the user's text).
- **Text integrity check:** assert rendered strings **==** source script strings.
- **Arabic/RTL:** render text in the **browser (HTML/SVG)**, not Pillow. Pillow without libraqm does **not** shape Arabic. Use OFL fonts bundled locally (no CDN). RTL page order and panel order for Arabic/manga; LTR for western.
- **Export:** Playwright/Chromium → PDF (+ PNG per page). Embed fonts.

### 5.7 State tracker
Per panel, Spark proposes **state deltas** (e.g., "jacket torn at sleeve", "holding lantern", "night, rain"); code validates them against the schema and appends to `state.jsonl`. The judge's checklist for later panels includes the **current state** — this is how a torn sleeve stays torn.

### 5.8 Stack `[DECISION]`
Python 3.11+ · FastAPI · pydantic · SQLite · `openai` SDK (base URL `https://api.meta.ai/v1`) · Pillow/numpy (L0 checks only) · Playwright (export) · React + Vite + TS (wizard UI) · SSE for progress. `.env` for keys (gitignored). No external infra.

**Deployment** `[TO DECIDE]`: judges look at code + video + "live product". Option: deploy with a **budget-capped server key + rate limit**, or "bring your own Meta key" (Vee Vee-style), or both. A public endpoint with an uncapped key will burn credits.

---

## 6. Benchmark (the proof) — design before building

- **Material:** 3 styles × 3 stories (12–16 panels each) → ~100+ panels. All **new**, original, neutral content.
- **Arms** (same stories, same planner output, prompts **frozen before the run**):
  - **A** — text description only (`/generations`), no references.
  - **B** — anchored with references (`/edits`), single shot, no verification.
  - **C** — anchored + verification loop + retry policy (the full system).
- **Metrics per arm:** drift rate (human blind check), first-pass yield, attempts per accepted panel, $/accepted panel, seconds/page.
- **Human check:** ≥ 10 raters if possible (friends/community), blind and shuffled, same checklist as `spec.json`.
- **Judge validation:** agreement between Spark judge and human labels on ~60 panels (precision/recall of "fail" detection).
- **Report:** one table in the README + one chart in the video. Include failures and `needs_human` counts. Publish raw logs (`runs/*.jsonl`).
- **Success target (not a promise):** C clearly beats B and A — e.g., drift in the tens of % for A and low single digits for C. If numbers are mediocre, say so; honest numbers beat inflated ones.

---

## 7. Roadmap (Thu Oct 29 → Wed Nov 4) — each milestone has an exit gate

> Egypt/ET time difference means "Nov 4, 9 PM ET" is ~4 AM Cairo Nov 5. **Plan to submit Tue Nov 3 night.** Wed is buffer only. Office hours are weekdays 10–11 AM ET in Discord (not weekends).

| # | When | Deliverable | Exit gate |
|---|---|---|---|
| **M0** | Thu Oct 29 (2–3 h) | New public repo + secret scan. API smoke test. `consistency_test.py` (A vs B on 6 scenes). Judge smoke test (does Spark vision tell a wrong panel from a right one?). SAM access test. | **GO** if anchored (B) is clearly the same character in ≥ 4/6 panels (after at most one prompt iteration) **and** Spark can flag obvious drift. **NO-GO → pivot to PatchProof** (see section 13). Decide within the day, not in 3 days. |
| **M1** | Thu–Fri | Bible schema + loader; step-1 flow (3–4 candidates → pick → lock sheet); continuity packet builder; stateless panel generator; run log (SQLite). | Generate a 6-panel sequence for one character from code only, with all attempts logged. |
| **M2** | Fri–Sat | Verifier L0 + L1 + L2; retry/simplify policy; budget cap; hand-label ~60 panels for judge calibration. | Judge agreement with human labels measured and written down. A deliberately corrupted panel (wrong hair) is caught. |
| **M3** | Sat–Sun | Layout engine: 5 templates, SAM fit, bubbles, RTL, fonts, PDF/PNG export; text-integrity check. | A 4-page book with real Arabic text renders correctly (shaping, RTL, no overflow). |
| **M4** | Sun–Mon | Planner (story → validated panel plan), state tracker, 4-step wizard UI, progress streaming. | End-to-end: story in → 12–16 page book out, no manual file edits. |
| **M5** | Mon–Tue | Benchmark runs (arms A/B/C), human blind rating, README with the table + raw logs. **Feature freeze Mon Nov 2 evening.** | Numbers exist, are reproducible from `runs/`, and failures are included. |
| **M6** | Tue Nov 3 | Record + edit the 3-min video; final README, `CONTRIBUTIONS.md`; **submit (edit existing submission)**; post on X. | Public repo opens logged-out; video link works logged-out; submission lists you. |
| Buffer | Wed Nov 4 | Fixes only. Last chance for organizer questions was Tue. | — |

**Stretch (only after M4 works):** one poster/thumbnail/character-sheet template each to show the engine generalizes (same pipeline, different template) · Glimmer as second judge (Open-Weights prize) · 3rd style · color · voice input.
**Cut order if late:** voice → Glimmer judge → 3rd style → extra templates → UI polish. **Never cut:** Bible, verifier, layout/lettering, benchmark.

---

## 8. Where it can go wrong (risk register)

| # | Failure mode | Why it happens | Early signal | Mitigation |
|---|---|---|---|---|
| 1 | **Anchor doesn't hold** across scenes | model weak at style/identity | M0 test < 4/6 | one prompt iteration; try other style (B&W first); else pivot |
| 2 | **Sheet bleed** | model pastes the reference sheet layout/white background into the panel | white margins, multi-view panels | L0 check; prompt "single scene, not a sheet"; use cropped single-view anchor in addition |
| 3 | **Baked-in text / fake letters** | image models like writing text | tiny glyphs in bubbles/signs | prompt negatives + L0 OCR/judge flag + reject; text only by code |
| 4 | **Two-character identity bleed** | features swap/merge when 2+ characters share a panel | hair/jacket on the wrong person | per-character refs; test 2-char scenes in M0/M1; judge checks each character separately; simplify shot on failure |
| 5 | **Wrong character count** | extra bystanders appear | SAM count ≠ expected | L1 count check + "exactly N characters" in prompt |
| 6 | **Face at distance loses identity** | small subjects in wide shots | judge fails wide shots | `min_face_px_for_check`: don't judge identity below threshold; compensate with outfit/silhouette attributes |
| 7 | **Style creep over a long book** | repeated sampling drifts | later pages look different | always anchor to canon, never previous panel; periodic canon re-check; benchmark with 16-panel stories |
| 8 | **State continuity breaks** (torn sleeve repaired) | model forgets | judge flags state attributes | state timeline injected into packet + checklist |
| 9 | **Aspect ratio unsupported** | API may fix sizes | `size` rejected | restrict to 3 ratios; design templates around them |
| 10 | **SAM endpoint unclear/unavailable** | new model, docs unknown | Day 0 test fails | `Segmenter` interface; Spark-boxes fallback; layout still works with lower precision |
| 11 | **Judge is unreliable** | LLM judge hallucinated passes | agreement < ~85% on labels | calibrate on human labels; stricter rubric; L3 second judge; never claim results without agreement number |
| 12 | **Retry loop burns credits** | bug or hard scene | spend graph | hard budget caps, max attempts, kill switch, cost shown in UI |
| 13 | **Rate limits / latency** | unpublished limits | 429s | exponential backoff, concurrency cap, pre-generate & cache for demo |
| 14 | **Safety filter rejects an image** | content policy | empty/failed responses | handle as retry-with-rephrase; keep content neutral |
| 15 | **Arabic text breaks** (disconnected letters, wrong direction) | Pillow/Canvas shaping, bad fonts | M3 render test | HTML/SVG in Chromium; bundled OFL fonts; test with long and diacritic text |
| 16 | **Template engine eats days** | layout is a deep rabbit hole | M3 slipping | 5 templates, no free-form editor, no slanted panels |
| 17 | **Scope creep** (warned about in the Discord) | "one more feature" | new features before M4 done | cut order in section 7; feature freeze Nov 2 |
| 18 | **Rules violation** | old assets/code leak in | any import from old repos | fresh repo; `CONTRIBUTIONS.md`; reviewer checklist (section 11) |
| 19 | **Demo fragility** | live API fails on camera | latency spikes | record from cached real runs; show the log; keep one live segment short |
| 20 | **Banned-list ambiguity** | "creative" ≠ banned, but judges may be strict | — | keep story neutral; optionally ask in #questions: "Is an illustrated-story generator with consistency verification in scope for Build for Your World?" |
| 21 | **Overclaiming** ("zero errors") | marketing instinct | — | claim only measured numbers (section 3) |
| 22 | **Coding agents generate unverified bulk code** | speed over checking | no tests, placeholders | agent rules (section 10); tests per milestone |

---

## 9. Testing strategy

- **Unit:** layout geometry (no panel overlap, bubbles inside panel, safe margins) · schema validation (plans, Bible, state deltas) · continuity-packet assembly (golden files) · text-integrity (rendered == source) · budget cap.
- **Verifier tests:** a labeled set of good/bad panels (including a deliberately corrupted one per attribute) → expected pass/fail. Track judge precision/recall.
- **Integration:** one cached real run per style (fixtures recorded from real API calls; never fabricated). A smoke test that builds a 4-page book end to end.
- **Visual snapshots:** PDF page → PNG, compared to approved baselines (Arabic RTL page, 2×2 grid page, splash page).
- **Chaos:** two-character scenes, night/day of the same location, back view, close-up, 30+ panel story.
- **Rule:** mocks only in tests. The demo path uses real calls or recorded real outputs, labeled as such.

---

## 10. Repo layout & agent operating rules (for Claude Code / Antigravity)

```
inkloop/
  README.md               # what it is, results table, how to run, honest limitations
  CONTRIBUTIONS.md        # everything built during the hackathon, with dates (judges need this)
  docs/                   # this brief, decisions log, benchmark protocol
  backend/
    app/ (api, orchestrator, bible, packet, generate, verify, layout, export, models, runlog)
    tests/
  frontend/               # React + Vite + TS wizard
  assets/fonts/           # OFL only + LICENSES.md
  templates/              # layout JSON
  runs/                   # raw benchmark logs (jsonl)
  scripts/                # consistency_test.py, benchmark runner, label tool
  .env.example            # no real keys
```

**Agent rules (paste into `CLAUDE.md` / `AGENTS.md`):**
1. Read this brief first. Work **one milestone at a time**; do not start the next before the exit gate passes.
2. **No placeholders, no fake data, no temporary workarounds in product code.** Mocks only inside `tests/`.
3. **Never read, print, or commit secrets.** Keys come from `.env` only; never log them.
4. **Do not copy code or assets from Mohamed's older projects** (Interactive Cases, ArtForge, Dual Draw, Still Human, NotebookMG). Fresh code only; record library licenses.
5. Small commits with messages that say **what is new** (the commit history is evidence for "new work only").
6. Every external assumption marked `[TO VERIFY]` must be tested and the result written to `docs/decisions.md` before building on it.
7. Validate all model outputs with schemas; reject and retry invalid ones. The model never writes the final text of the book — **code renders the user's text**.
8. Cost safety: every loop has max attempts and a budget cap; log tokens/images/$ per call.
9. When something fails, report the real error and the evidence — do not hide it behind retries or silent fallbacks.

---

## 11. Day-0 verification checklist (do before building on any of it)

- [ ] API key works; **credits visible** on the Billing page; card accepted (Egypt).
- [ ] `client.models.list()` → real model ids (Spark, Image, SAM, Glimmer?).
- [ ] `images.generate` response shape: `b64_json` or `url`? image size/aspect options? `n` limit? seed supported?
- [ ] `images.edit` with **one** reference, then with **multiple** references (character + location). Does it keep identity?
- [ ] Is text-in-image reliably suppressed by the prompt? How often do letters appear?
- [ ] Spark vision input accepts 2 images + checklist and returns strict JSON? How often does it hallucinate a pass?
- [ ] SAM 3.1: endpoint, input (text prompt vs points), output (mask/box), latency, cost.
- [ ] Rate limits observed (429 behavior) with 3–5 parallel calls.
- [ ] Actual price per image and per Spark call (measure, don't assume).
- [ ] Fonts shortlisted (Arabic + Latin comic-friendly, OFL) and licenses recorded.
- [ ] Optional: Modal / Baseten credits requested (needed for Open-Weights prize path).
- [ ] Optional: question posted to organizers about scope (item 20 above).

---

## 12. Demo video (3:00) — outline

1. **0:00–0:20 Problem.** Fresh baseline generated during the hackathon: same prompt, five panels, the character changes every time. (No old assets.)
2. **0:20–1:00 The 4 steps.** Pick character → lock → cast → story → language.
3. **1:00–1:50 Under the hood.** Story Bible on screen; continuity packet; **a live moment where the verifier rejects a drifted panel (red, with the reason) and the retry fixes it.** Show the attempt log.
4. **1:50–2:30 The book.** Page flip through a finished 12–16 page book; Arabic RTL page; templates; bubbles placed by SAM free-space.
5. **2:30–2:50 Numbers.** Table: A vs B vs C (drift, yield, $/panel). Judge agreement number.
6. **2:50–3:00 Close.** Open-source repo, what's next.

Pre-record from cached real runs; keep any live segment short and rehearsed.

---

## 13. Fallback plan

If M0 says NO-GO (identity doesn't hold even with anchors and one prompt iteration): **PatchProof** — an agent that takes an open-source repo with a known historical CVE, finds the vulnerability, writes a patch, and proves it (exploit test red → green + regression tests pass, rollback on failure), benchmarked on ~30 CVEs, Spark vs Spark Open/Glimmer. Defensive only. First step there: test whether Muse can find/patch a simple known vulnerability.

---

## 14. Submission checklist

- [ ] Repo **public**, opens logged-out; README has results table, limitations, run instructions.
- [ ] `CONTRIBUTIONS.md` lists what was built when; no old code/assets.
- [ ] No secrets in history (scan before the final push).
- [ ] 3-min video link works logged-out; shows only hackathon-built features.
- [ ] Track: **Indie Developer**; theme: **Build for Your World**.
- [ ] **Edit the existing submission** (organizers confirmed) — remove all traces of the old project.
- [ ] Post the demo on X and submit the link (Most Viral); share in the community gallery (Community Vote).
- [ ] Submit by **Tue Nov 3 night**.

---

## 15. Thinking out loud — decisions & reasoning

- **Why external memory?** The failure in Mohamed's 1000→200 experience is the agent's context: it forgets, drifts, and improvises. Moving memory to files and rebuilding context per call removes the failure at the source instead of prompting around it.
- **Why verify + remove-only?** Judges and users trust numbers. A checker that can only reject (never rewrite) is simple to reason about, and its quality can be measured against human labels.
- **Why templates + code lettering?** It makes the output a *book*, makes Arabic correct, and uses SAM for something real (fit, bubbles, tails) rather than decoration.
- **Why generate at panel aspect?** Cropping after generation breaks composition and faces; the template should drive generation.
- **Which style first?** Black-and-white ink with screentone removes color drift, so identity problems show up cleanly. Then a flat-color style; the painterly style is the hardest — try it last, drop it if it fails. Style references must be Mohamed's own artwork or generated assets (no scraped art, no named-artist prompts).
- **Why not a "do everything" design tool (posters, thumbnails, covers, 10 styles)?** Judges have seen it; 6 days isn't enough to polish 10 styles. One engine with one flagship output (the book) and, at most, one template each for other formats as proof of generality.
- **Be honest about autonomy.** It's a pipeline with agentic decisions — say so. Overclaiming is a bigger risk than underclaiming.
- **Be careful about what the benchmark proves.** It proves "C beats A/B on *our* stories and *our* checklist, as judged by humans blind". It does not prove general consistency.

### Open questions for Mohamed
1. Demo story: Arabic, English, or both pages side by side? (Arabic RTL is a differentiator; English helps non-Arabic judges.)
2. Starting style: confirm B&W ink first?
3. Deployment: budget-capped server key, bring-your-own-key, or both?
4. Who can do blind human rating (target ≥ 10 people)?
5. Do you want Glimmer as a second judge (Open-Weights prize) or skip to protect the schedule?

---

## 16. Appendix — what's already known

- `consistency_test.py` (provided in chat): 6 scenes, arm A (text only) vs arm B (anchored `/images/edits`), ~13 images. Scoring rule: B ≥ 4/6 → continue.
- Meta Muse Image docs (via search): OpenAI-compatible images endpoints, anchored composition recommended, multi-image composition via edits; price reports vary by source → verify on Billing.
- Hackathon facts: Indie prizes $150K/$100K/$75K/$50K/$25K; bonuses listed in section 1; judging is Nov 5–8; closing ceremony Nov 9; community vote winner Nov 16.
