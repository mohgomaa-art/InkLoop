# InkLoop — End-to-End Project Tasks & Scope-Control Plan

**Document type:** Master task register, architecture baseline, implementation sequence, and scope-control contract  
**Product:** InkLoop — research-driven manga, manhwa, and comics production system  
**Project owner / final decision maker:** Mohamed Gomaa  
**Technical direction:** ChatGPT acts as project lead in this conversation; coding agents execute one approved task prompt at a time.  
**Primary workspace reported by the implementation agent:** `C:\Users\mnile\Desktop\InkLoob`  
**Primary brief:** `INKLOOP_PROJECT_BRIEF.md`  
**Status at creation:** M0 feasibility is reported complete; the user states the Image Generation Engine is finished; the remaining system must be built without silently reducing scope.

---

## 0. Purpose of This File

This file is the project's execution source of truth. It exists to prevent scope drift, omitted engines, accidental simplification, and coding agents making unilateral architecture decisions.

Every task is tracked from the initial repository and research foundation through all production engines, integration, verification, export, user-facing workflow, release, and maintenance.

### Mandatory rule: NO SILENT REDUCTION

- Do not delete, merge away, or quietly omit a required engine, feature family, taxonomy group, language requirement, verification layer, output format, or deliverable listed here.
- Do not interpret milestone sequencing as permission to reduce the final product scope. Work is staged because components have dependencies, not because later components are optional.
- A temporary implementation may be narrower than the final specification only when the difference is explicitly recorded as `NOT IMPLEMENTED YET`, with a task, dependency, and acceptance criteria retained here.
- If a requested feature is technically blocked, document the evidence, preserve its contract and task, and propose alternatives for the project owner. Do not remove it.
- Never mark a task complete because files exist. Completion requires evidence against its acceptance criteria.
- Do not replace real functionality with placeholders, mocks in the product path, hand-waved claims, or fake benchmark results.
- Do not start a later milestone while the current milestone's exit gate remains unmet unless the project owner explicitly authorizes a documented exception.
- Any scope change must be recorded in `docs/decisions.md` and approved by the project owner.

### Status legend

- `[x]` Completed and supported by actual evidence or explicitly confirmed by the project owner.
- `[ ]` Not complete.
- `[~]` In progress; evidence and remaining work must be stated.
- `[!]` Blocked; preserve the task and record the external dependency or failure.
- `[?]` Needs a project-owner decision or an evidence-based technical decision.

A claimed result and an independently reproduced result are not the same. Reports must distinguish them.

---

## 1. Product North Star — Immutable Scope

InkLoop is a specialist production system for generating polished manga, manhwa, and comic artwork and assembling that artwork into finished comic pages/books. Image generation is only one specialist engine in the full system.

The system must use a research-driven knowledge catalogue, explicit data contracts, deterministic geometry, independent engines, reproducible execution logs, and evidence-based quality checks.

### Final product capabilities

1. Research-backed image generation with style and character consistency.
2. A knowledge catalogue covering all 60 previously agreed taxonomy groups.
3. External, structured Story Bible / Canon and versioned story state.
4. Canvas generation with strict dimensions, page geometry, margins, gutters, panel geometry, and output profiles.
5. Separate image-to-canvas integration with exact fitting, cropping, alignment, transforms, and coordinate handling.
6. Separate speech-bubble generation and placement with shape, tail, speaker, reading-order, collision, and text-fit rules.
7. Separate story/text generation for dialogue, narration, captions, inner monologue, sound-effect words, and related text blocks.
8. Separate typography and font engine, including typeface/style management, font generation where supported, glyph coverage, shaping, text measurement, lettering, Arabic RTL and mixed-language support.
9. Separate effects and motion engine including speed lines, impacts, blur families, glare, glow, bloom, lighting effects, particles, smoke, rain, energy and other enumerated effects.
10. Final compositor that renders and orders all layers without taking ownership of the engines' logic.
11. Quality and verification system for both visual correctness and deterministic engineering correctness.
12. Export and delivery system for final PDFs, page PNGs, supported web/vertical formats, and editable/recomposable project artifacts.
13. Shared project state, asset provenance, run logs, budget controls, resume/retry behavior, and reproducibility.
14. A coordinating Agent that can invoke the complete set of approved tools and specialist engines. Its detailed tool design will be discussed separately with the project owner; it must not be invented prematurely.
15. A user-facing project workflow consistent with the original brief: character/style setup, cast, story, language/lettering, preview, generation, approval, and export.
16. Complete tests, benchmarks, documentation, original demo assets, license tracking, release process, and evidence for all claims.

### Product boundaries

- This is not a generic chatbot, general-purpose desktop assistant, or generic image-generation wrapper.
- Do not delegate all artistic composition to one giant prompt or a single image-generation call. The specialist engines own their own outputs.
- Do not render dialogue or final lettering inside generated artwork. Preserve clean artwork and render source text through the text/typography/bubble pipeline.
- Do not confuse a catalogue entry with a verified capability. Every supported claim needs evidence or must be marked experimental.
- Do not let the Agent replace deterministic engineering where code can enforce geometry, file integrity, text integrity, budgets, schemas, or state transitions.

---

## 2. Sources of Truth and Decision Rules

Use the following precedence if sources conflict:

1. Explicit, latest instruction from the project owner in the current conversation.
2. This `INKLOOP_TASKS.md` after it is reviewed/accepted by the owner.
3. `INKLOOP_PROJECT_BRIEF.md` for original project constraints and baseline architecture.
4. Approved records in `docs/decisions.md`.
5. Versioned engine contracts and schemas.
6. Research records, official documentation, experiments, and benchmark results.
7. Agent assumptions, which have no authority until verified or approved.

If an inconsistency is found, stop the affected work, document it, and ask the project lead for a decision when material. Never silently reconcile differences by removing a requirement.

### External sources and research

- Use official API/library documentation for request format, supported capabilities, and licensing terms.
- Use academic papers, established technical references, and documented professional sources for relevant artistic, perceptual, typography, graphics, and layout principles.
- Separate `FACT`, `INFERENCE`, `HYPOTHESIS`, `EXPERIMENTAL RESULT`, and `UNKNOWN` in research notes.
- Save source details, access date, exact claim supported, relevant quotation/snippet or page/section, and applicability/limits.
- Never assert that a model reliably follows a visual instruction without testing it on controlled cases.
- Never present an LLM judge's decision as objective ground truth without independent validation.

---

## 3. Current Status Baseline

This baseline reflects reports supplied in the conversation. Confirm actual repository status before relying on any local file paths or commit references.

- [x] M0 API authentication and model catalogue request reported successful.
- [x] One minimal Muse Spark text-generation request reported successful.
- [x] M0 visual experiment reported completed: Muse Image text-only and reference-anchored arms; six scenes reported as 0/6 versus 6/6; two verifier examples; one SAM segmentation test.
- [x] M0 test suite reported as 16 passing tests at the end of that milestone.
- [x] Project owner states the Image Generation Engine is finished. Treat its current implementation as an existing engine; do not rewrite it merely to fit a new folder layout. Audit it, preserve it, and change it only when an explicit integration requirement or proven defect requires a change.
- [ ] Research-backed knowledge catalogue: the 60 taxonomy groups have been identified, but each group must still have research records, rules, evidence levels, experiments as appropriate, and a controlled retrieval/integration design unless that work is separately verified as complete.
- [ ] Master engine contracts and final coordinate/color/rendering conventions approved.
- [ ] Canvas Generation Engine.
- [ ] Image–Canvas Integration Engine.
- [ ] Text Generation Engine.
- [ ] Typography & Font Generation Engine.
- [ ] Speech Bubble Engine.
- [ ] Effects & Motion Engine.
- [ ] Final Compositor.
- [ ] Full Quality & Verification Engine.
- [ ] Export & Delivery Engine.
- [ ] Full project coordinator/Agent tool integration; detailed design is deferred to a separate owner-led discussion.
- [ ] User-facing end-to-end workflow and preview/approval experience.
- [ ] End-to-end tests, measured quality benchmark, release readiness, and final demo/submission artifacts.

**M0 interpretation limit:** The reported six-scene result is a promising feasibility result, not proof of universal consistency. The verifier evidence covers two cases, and the SAM evidence covers one request. Future reports must preserve those sample-size limitations.

---

## 4. Target Architecture

### 4.1 Main layers

1. **Project Workspace / User Workflow** — project setup, character/style approval, cast, story, language, generation settings, preview, approval, and export.
2. **Coordinator / Agent Layer** — eventually invokes tools and engines according to approved contracts. Design its detailed tool catalogue only after the owner-led discussion.
3. **Shared Core** — project configuration, Story Bible, canon snapshots, state timeline, schemas/contracts, coordinates, budgets, events, errors, and run execution.
4. **Research & Knowledge Layer** — the 60-group image-generation knowledge catalogue, research evidence registry, recipes, compatibility rules, experiment registry, source traceability, and versioning.
5. **Seven Specialist Production Engines** — Image Generation, Canvas Generation, Image–Canvas Integration, Speech Bubbles, Text Generation, Typography/Fonts, Effects/Motion.
6. **Final Compositor** — layer graph and final rendering.
7. **Quality & Verification** — visual, typography, geometry, continuity, policy, and output validation.
8. **Export & Delivery** — PDF, page PNGs, supported long-scroll/web formats, and project artifacts.
9. **Storage & Observability** — asset registry, local artifact store, SQLite run log, provenance, costs, timings, diagnostics, and reproducibility.

### 4.2 Specialist production engines — strict ownership

#### Engine E1 — Image Generation Engine [BASELINE COMPLETED PER OWNER]
Owns image-generation decisions and provider calls, research-driven prompt compilation, reference conditioning, style/character anchoring, generated image artifacts, and generation metadata. Its knowledge catalogue is for choosing and composing visual instructions with evidence and rules. It does not own final panel placement, bubbles, text, fonts, or post-generation effect layers.

#### Engine E2 — Canvas Generation Engine
Owns the creation of canvas/page/panel geometry and the canvas artifact itself: dimensions, aspect ratios, resolution, page format, margins, bleed, safe zones, gutters, panel slots, grid/freeform arrangements, reading direction, and geometry validation.

#### Engine E3 — Image–Canvas Integration Engine
Owns precise placement of generated images inside canvas/panel slots: coordinate transforms, scale, fit/crop policy, anchor/focal preservation, clipping, positioning, output size, resampling, and transformation audit. It must preserve aspect ratio unless an explicit user-approved distortion operation is requested.

#### Engine E4 — Speech Bubble Engine
Owns balloon geometry and rendering, bubble category and shape, tail routing, speaker association, candidate regions, collision checks, reading order, multiple/connected/overlapping bubbles, safe margins, and final bubble-shape layers. It consumes real text metrics; it does not generate dialogue or own glyph rendering.

#### Engine E5 — Text Generation Engine
Owns narrative text artifacts: dialogue, narration, captions, internal monologue, off-panel dialogue, interruption/fading rules, SFX words, tone, character voice, and consistency with the story's canon/state. It records text provenance and must respect user-supplied text as immutable when exact preservation is required.

#### Engine E6 — Typography & Font Generation Engine
Owns font discovery/catalogue and licenses, creation of new typeface/font assets when technically achievable, lettering styles, glyph coverage, Arabic shaping and mixed-direction text, text shaping, metrics, kerning, line breaks, text fit, style application, and rendering text into independent layers. Creating a visual lettering specimen is not automatically equivalent to producing a valid font file; the system must distinguish those outputs.

#### Engine E7 — Effects & Motion Engine
Owns independently controllable effects and their parameters/masks/layers: motion and speed lines, action arcs, impact effects, motion smears, blur families, glow, bloom, glare, lens flare, lighting rays, particles, smoke/steam, rain/snow/fog, sparks/debris, electricity/energy aura, environmental effects, and other approved catalogue elements. It must not silently modify the source art, text, character identity, or bubble content.

### 4.3 Supporting production services — required, not replacements

#### S1 — Story Bible / Canon / State Service
Stores versioned character definitions, approved visual sheets, style Bible, location references, allowed cast/props/locations, state timeline, and immutable run snapshots. Canon changes require an explicit versioned change; state changes are logged as events.

#### S2 — Research & Knowledge System
Stores the image-generation catalogue and its 60 taxonomy groups, research sources, evidence level, visual effects, selection rules, compatibility rules, prompt recipes, negative constraints, limits, controlled experiment results, and version history. No unsupported catalogue item may be represented as empirically verified.

#### S3 — Asset Registry & Artifact Store
Registers every image, canvas, panel, mask, font, text layer, effect layer, composite, QA report, and export with stable IDs, file path, content hash, size/dimensions, origin, parent assets, engine/version, configuration hash, license/source, and creation time.

#### S4 — Run Log, Execution & Budget Manager
Records every actual attempt including started, succeeded, failed, cancelled, and interrupted states; enforces per-operation/global budget, concurrency, bounded retries, timeouts, idempotency where possible, resume behavior, and event traceability.

#### S5 — Scene/Story Planning Service
Converts a story and current Story Bible into structured scene/panel requirements and state deltas. It may use an LLM for bounded planning decisions, but schemas and deterministic validation own the final accepted state. Only declared entities may be used unless a versioned canon-mutation flow is approved.

#### S6 — Final Compositor
Owns the ordered layer graph and final raster/vector render. It does not replace the Image–Canvas Integration, Bubble, Text, Typography, or Effects engines; it composes their outputs by ID and coordinates.

#### S7 — Quality & Verification System
Runs deterministic geometry/text/file tests and calibrated visual checks. It emits structured PASS/FAIL/UNSURE results with evidence. Required `UNSURE`, invalid data, missing attributes, or contradictory checks must fail closed where the relevant contract requires it.

#### S8 — Export & Delivery System
Creates final PDF, page PNGs, long-scroll outputs and editable/recomposable artifacts; validates outputs and records the exact source composite/run/version.

#### S9 — Coordinator / Agent
Final scope includes an Agent that can orchestrate approved engines/tools. Detailed tool names, schemas, confirmation policies, planning logic, and memory behavior are deliberately deferred until the owner-led discussion. No coding agent may independently invent or freeze that design.

---

## 5. Shared Contracts and Data Standards — Prerequisites for Engine Work

### T5.1 — Define global coordinate and measurement conventions
- [x] Choose canonical internal coordinate units and document pixel, physical print, viewport, and normalized coordinate conversions (verified in `app.contracts.geometry`).
- [x] Define page coordinates, panel-local coordinates, source-image coordinates, text-layer coordinates, bubble coordinates, and effect-mask coordinates (`CoordinateSpace` enum).
- [x] Define origin (top-left) and axis direction (+X right, +Y down) for each coordinate space.
- [x] Define rounding, clipping, resampling, DPI (300 print / 96 preview), physical dimensions, and exact pixel constraints.
- [x] Define coordinate transform data structures (`Transform2D`, `FitMode`) and reversible transform tests (verified in `test_contracts_geometry.py`).
- [x] Define color space (sRGB), alpha convention (straight alpha), transparency, and compositing behavior.
- [x] Define raster/vector asset conventions and supported formats (PNG, WebP, SVG, PDF).
- [x] Add deterministic unit tests for coordinate conversions and boundary handling (32 unit tests passing).
- **Acceptance:** every engine contract uses the same documented convention; conversions have tests and no ambiguous coordinate fields remain. (SATISFIED: `docs/shared-contracts.md`, `backend/app/contracts/geometry.py`).

### T5.2 — Define versioned engine contracts
- [x] Define shared IDs for projects, runs, scenes, panels, characters, assets, fonts, text blocks, bubbles, effects, pages, and QA reports (`IdPrefix` and `identity.py`).
- [x] Define typed input/output contracts for every engine using Pydantic validated schemas (`EngineRunRequest`, `EngineRunResponse`).
- [x] Define `engine_id`, `engine_version`, `schema_version`, `config_hash`, provenance, and source-asset links (`ProvenanceRecord`).
- [x] Define structured failure responses including stable error code, stage, retriable flag, safe message, and evidence links (`ErrorCode`, `EngineFailure`, `ValidationErrorDetail`).
- [x] Define `NOT_IMPLEMENTED_YET`, `EXPERIMENTAL`, `BLOCKED`, `FAILED`, `SUCCESS`, and `NEEDS_REVIEW` states rather than silently substituting behavior (`EngineStatus`).
- [x] Define API compatibility and migration rules for contract revisions.
- **Acceptance:** contract fixtures and tests validate a good result, reject malformed results, and preserve backward compatibility rules. (SATISFIED: `backend/app/contracts/engine.py`, `backend/app/contracts/errors.py`, `backend/tests/test_contracts_engine.py`).

### T5.3 — Story Bible and canonical state
- [x] Define versioned `ProjectSpec`, `StyleBible`, `CharacterSpec`, `LocationSpec`, `PropSpec`, and `StoryStateEvent` schemas.
- [x] Separate immutable canonical attributes from mutable per-story state.
- [x] Store approved reference image IDs and hashes for characters, style, locations, and key props.
- [x] Define explicit canon mutation proposal, approval, version, and audit flow.
- [x] Define allowed cast, props, and locations so generators cannot silently introduce undeclared entities.
- [x] Define deterministic state snapshot per scene/panel.
- [x] Define file-based JSON source of truth; keep binary asset bytes in the artifact store, not inline in JSON.
- **Acceptance:** a project can be loaded, validated, snapshotted, and reconstructed; canonical definitions are not mutated by generation runs. (SATISFIED: `backend/app/project/` (`asset_refs.py`, `canon.py`, `story_state.py`, `bible.py`), `backend/tests/test_story_bible.py`, `backend/tests/test_story_bible_advanced.py`).

### T5.4 — Asset registry, content hashes, and reproducibility
- [ ] Define an asset manifest schema for all image, canvas, font, text, mask, effect, composite, and export artifacts.
- [ ] Compute SHA-256 for every produced/stored artifact where applicable.
- [ ] Record parent artifact IDs and transformations so the artifact lineage can be traversed.
- [ ] Record original source, license, and permitted use where applicable.
- [ ] Prevent overwriting an approved source or prior generation result without creating a new version.
- **Acceptance:** a final page can be traced back to the exact project state, engine configurations, inputs, and source assets.

### T5.5 — Run execution and budgets
- [ ] Standardize run IDs and attempt IDs.
- [ ] Record every attempt's start time, end time, latency, status, request ID, usage, estimated/confirmed cost, and sanitized error.
- [ ] Distinguish provider-reported costs from estimates.
- [ ] Enforce retry ceilings, concurrency caps, timeouts, cancellation, and global/project/per-run budget ceilings.
- [ ] Add kill switches for repeated or runaway generation.
- [ ] Record interrupted operations as incomplete rather than deleting them.
- [ ] Add a dry-run/validation mode for workflows that can be validated without provider calls.
- **Acceptance:** successful, failed, cancelled, and interrupted operations remain traceable without secrets in the log.

---

## 6. Research Program — Required Across the Full Project

Research is not a decorative bibliography. It must influence engine behavior and be verified through experiments.

### T6.1 — Research governance
- [ ] Define a consistent research record with claim, source, date accessed, source type, evidence classification, limits, relevance, and engine/taxonomy IDs.
- [ ] Maintain `FACT`, `INFERENCE`, `HYPOTHESIS`, `EXPERIMENTAL RESULT`, and `UNKNOWN` separately.
- [ ] Record why a source supports each rule; do not attach citations without a claim mapping.
- [ ] Track licenses for fonts, libraries, model-generated assets, reference assets, and any external datasets.
- [ ] Create a review process to promote a rule from hypothesis to experimentally supported.
- **Acceptance:** every production-critical research rule has a traceable basis and a clear confidence/evidence status.

### T6.2 — Experimental design and visual evaluation
- [ ] Define controlled prompt/model experiments with frozen inputs and parameter records.
- [ ] Define blind human evaluation protocol for artistic quality and consistency where appropriate.
- [ ] Define repeatability, sample size, failure capture, and uncertainty reporting.
- [ ] Define visual regression sets for composition, edge cases, text render, bubble placement, and effects.
- [ ] Maintain canonical test artifacts that are original and created for InkLoop.
- [ ] Do not make universal quality claims from the small M0 sample.
- **Acceptance:** research claims can be reproduced or clearly marked exploratory; failures are preserved and included.

### T6.3 — Research-backed image-generation knowledge catalogue
- [ ] Preserve all 60 taxonomy groups listed in Section 7.
- [ ] Research each group, its intended visual effect, when it is suitable, failure modes, interacting variables, and compatible/incompatible combinations.
- [ ] Produce controlled prompt recipes only when supported by actual runs or label them as hypotheses.
- [ ] Define how the Image Generation Engine retrieves only relevant knowledge for a scene.
- [ ] Define ranking/selection logic with explicit constraints and evidence; do not place all 60 groups into every prompt.
- [ ] Keep artistic selection separate from provider-call mechanics.
- [ ] Store catalogue version and selected taxonomy records with each image-generation run.
- [ ] Test whether selected rules improve a measurable outcome rather than assuming they do.
- **Acceptance:** all 60 groups exist in versioned source data with no omitted agreed elements; each record exposes evidence status and limitations; generation runs record which knowledge was used.

---

## 7. The 60-Group Taxonomy — Required Coverage Checklist

This is the catalogue coverage register. Preserve every element in the previously agreed full element lists. The headings below are not permission to replace their contents with shorter lists. Every group must be represented in the knowledge source, have a stable identifier, and have a research/evidence status.

- [ ] **01. Comic Formats** — Manga, Manhwa, Manhua, Western Comics, Graphic Novel, Webtoon, Webcomic, Comic Strip, Newspaper Comic, 4-Koma, Motion Comic, Interactive Comic.
- [ ] **02. Canvas Types** — Single Page, Double-Page Spread, Vertical Scroll Canvas, Fixed Viewport, Cover Canvas, Title Page, Full-Bleed Canvas, Framed Canvas, Borderless Canvas, Split Canvas, Continuous Background Canvas.
- [ ] **03. Page Structures** — Single Panel Page, Two-Panel Page, Three-Tier Layout, Four-Panel Grid, Six-Panel Grid, Nine-Panel Grid, Horizontal Strip, Vertical Strip, Asymmetric Grid, Diagonal Grid, Mosaic, Montage, Split-Screen, Freeform Layout.
- [ ] **04. Panel Types by Narrative Function** — Establishing Panel, Action Panel, Reaction Panel, Reveal Panel, Detail Panel, Insert Panel, Impact Panel, Silent Panel, Transition Panel, Flashback Panel, Dream Panel, Cliffhanger Panel, Closing Panel, Splash Panel.
- [ ] **05. Panel Shapes** — Rectangle, Square, Wide Rectangle, Tall Rectangle, Diagonal Panel, Trapezoid, Triangle, Polygon, Circle, Oval, Wavy Border, Jagged Border, Organic Shape, Irregular Shape, Fragmented Panel.
- [ ] **06. Panel Borders & Relationships** — Standard Bordered, Borderless, Inset, Overlapping, Bleed, Full-Bleed, Figure Breaking Frame, Panel-within-Panel, Floating Panel, Embedded Panel, Frameless Panel, Panel Crossing the Gutter.
- [ ] **07. Camera Shot Scales** — Extreme Wide Shot, Very Wide Shot, Wide Shot, Long Shot, Full Body Shot, Medium Long Shot, Medium Shot, Medium Close-up, Close-up, Big Close-up, Extreme Close-up, Macro Shot, Detail Insert.
- [ ] **08. Camera Angles & Views** — Eye-Level, High Angle, Low Angle, Bird’s-Eye View, Worm’s-Eye View, Overhead, Ground-Level, Dutch Tilt, POV, Reverse POV, Over-the-Shoulder, Three-Quarter View, Front View, Side Profile, Back View, Reflection View.
- [ ] **09. Zoom & Camera Transitions** — Push-in, Pull-back, Extreme Punch-in, Reveal by Zoom, Reaction Cut, Match Cut, Scale Contrast, Wide-to-Close-up, Close-up-to-Wide, Detail-to-Reveal, Zoom-in Sequence, Zoom-out Sequence.
- [ ] **10. Composition Types** — Symmetrical, Asymmetrical, Centered, Off-Center, Rule of Thirds, Golden Ratio, Leading Lines, Triangular Composition, Foreground Framing, Layered Depth, Negative Space, Silhouette Composition, Diagonal Composition, Radial Composition, Circular Flow, Frame within Frame, Visual Hierarchy, Focal Point, Partial Occlusion, Continuous Composition.
- [ ] **11. Panel Transitions** — Moment-to-Moment, Action-to-Action, Subject-to-Subject, Scene-to-Scene, Aspect-to-Aspect, Non-Sequitur, Cause-to-Effect, Setup-to-Payoff, Reveal, Reaction, Parallel Cut, Match Cut, Time Skip, Flashback, Flashforward, Montage, Page-Turn Reveal, Repetition, Silent Beat.
- [ ] **12. Speech Bubble Types by Function** — Dialogue, Thought, Inner Monologue, Whisper, Shout, Scream, Narration, Caption, Off-Panel Dialogue, Voice-over, Phone, Radio, Broadcast, Robotic Voice, Electronic Voice, Telepathy, Singing, Crying Speech, Gasps, Interrupted Speech, Fading Speech.
- [ ] **13. Speech Bubble Shapes** — Oval, Ellipse, Rounded Rectangle, Rectangle, Cloud, Jagged, Starburst, Dashed, Dotted, Wavy, Rough/Distorted, Electric, Pixelated, Decorative, Borderless Balloon.
- [ ] **14. Speech Bubble Tails & Connections** — Standard Pointed Tail, Curved Tail, Short Tail, Long Tail, Forked Tail, Multiple Tails, Bubble-chain Tail, Thought Trail, Tail-less, Off-Panel Tail, Connected Balloons, Sequential Balloons, Shared Balloon, Overlapping Balloons, Interrupted Balloon, Broken Balloon, Nested Balloon, Silent Balloon.
- [ ] **15. Text Containers & Captions** — Scene Caption, Time/Location Card, Narrator Box, Internal Monologue Box, Letter/Document Box, On-screen UI, Signage, Footnote, Translator Note, Caption Stack.
- [ ] **16. Font Families & Lettering Styles** — Comic Lettering, Hand-lettered, Sans-serif, Serif, Handwritten, Script, Display, Condensed, Monospaced, Brush Lettering, Rough/Distressed, Pixel/Retro, Outlined, Inline, Decorative.
- [ ] **17. Typography Properties** — Typeface, Font Size, Weight, Width, Italic, All Caps, Small Caps, Letter Spacing, Word Spacing, Line Height, Alignment, Text Direction, Line Breaks, Balloon Padding, Text Stroke, Outline, Shadow, Opacity, Emphasis, Text Fit, Text Overflow.
- [ ] **18. Arabic & Multilingual Lettering** — Arabic Shaping, RTL, LTR, Bidirectional Text, Ligatures, Diacritics, Vertical Writing, Line-breaking Rules, Font Embedding, Mixed Arabic-English Text, Text Integrity.
- [ ] **19. Stroke & Line Art Types** — Clean Line Art, Variable Line Weight, Thick Contour, Thin Detail Lines, Sketch Lines, Rough Ink, Brush Ink, Dry Brush, Scratchy Lines, Broken Lines, Hatching, Cross-Hatching, Stippling, Dotwork, Screentone.
- [ ] **20. Motion Lines & Focus Effects** — Horizontal Speed Lines, Diagonal Speed Lines, Radial Speed Lines, Focus Lines, Impact Burst, Action Arcs, Motion Trails, Smear Effects, Motion Blur, Vibration Lines, Shake Lines, Shock Rays, Perspective Speed Lines.
- [ ] **21. Manga Emanata & Expression Marks** — Sweat Drop, Anger Vein Mark, Blush Lines, Surprise Rays, Shock Lines, Trembling Marks, Tear Marks, Spiral Eyes, Gloom Lines, Embarrassment Marks, Confusion Marks, Exhaustion Marks.
- [ ] **22. Impact & Special Effects** — Impact Cloud, Dust Cloud, Debris, Sparks, Crack Lines, Shattered Glass, Smoke Trails, Energy Aura, Electric Arcs, Magic Circles, Glow, Glare, Bloom, Lens Flare, Shockwave Rings, Environmental Particles.
- [ ] **23. Sound Effects (SFX)** — BOOM, BANG, CRASH, TAP, TICK, CLICK, WHOOSH, SWISH, CRACK, THUD, RUMBLE, KNOCK, SPLASH, BUZZ, SNAP, GASP, SIGH, ZAP, DRIP, CLANG, SCRAPE, FOOTSTEPS.
- [ ] **24. Facial Expressions — Core Emotions** — Joy, Sadness, Anger, Fear, Surprise, Disgust, Contempt.
- [ ] **25. Facial Expressions — Complex Emotions** — Curiosity, Confusion, Suspicion, Disbelief, Embarrassment, Shyness, Smugness, Pride, Determination, Frustration, Relief, Anxiety, Boredom, Sarcasm, Awkwardness, Love, Awe, Jealousy, Regret, Guilt, Nervousness.
- [ ] **26. Facial Expressions — Manga-specific & Exaggerated** — Ugly Cry, Silent Tears, Hysterical Laughter, Nervous Smile, Evil Grin, Deadpan, Shock Freeze, Panic Face, Exhausted Face, Dizzy Eyes, Spiral Eyes, Blank Face, Cat-like Smile, Overwhelmed Expression.
- [ ] **27. Facial Expression Components** — Eyebrow Position, Eye Shape, Gaze Direction, Pupil Size, Mouth Opening, Lip Compression, Head Tilt, Face Angle, Tears, Blushing, Sweat, Under-eye Shadows, Emanata.
- [ ] **28. Character Poses — Basic** — Standing, Sitting, Squatting, Crouching, Kneeling, Lying, Reclining, Leaning, Walking, Running, Jogging, Jumping, Falling, Landing, Climbing, Crawling, Floating.
- [ ] **29. Character Poses — Action** — Reaching, Grabbing, Throwing, Catching, Pushing, Pulling, Lifting, Dodging, Blocking, Attacking, Defending, Spinning, Turning, Slipping, Stumbling, Recoiling.
- [ ] **30. Character Poses — Body Language** — Arms Crossed, Hands on Hips, Pointing, Waving, Shrugging, Facepalm, Bowing, Saluting, Praying Pose, Handshake, Hugging, Covering Face, Hands Behind Back, Hands in Pockets, Open-Palm Gesture.
- [ ] **31. Character Poses — Interaction & Daily Activities** — Thinking, Listening, Talking, Reading, Writing, Holding Object, Looking Back, Reaching Out, Offering, Receiving, Examining, Hiding.
- [ ] **32. Character Pose Parameters** — Body Orientation, Weight Distribution, Line of Action, Limb Configuration, Head Direction, Eye Direction, Foreshortening, Contact Points, Silhouette Readability.
- [ ] **33. Character Dynamics & Movement** — Idle, Anticipation, Action, Follow-through, Recovery, Approach, Retreat, Chase, Confrontation, Face-off, Hand-off, Greeting, Conversation, Argument, Reconciliation, Cooperation, Push/Pull, Carrying, Catching, Supporting, Collision, Separation.
- [ ] **34. Group Dynamics & Interaction** — Group Movement, Formation, Parallel Actions, Coordinated Reaction, Eye Contact, Looking Away, Mutual Gaze, Avoided Gaze, Personal Space, Intimate Distance, Social Distance, Isolation, Power Imbalance, Dominant/Subordinate Framing.
- [ ] **35. Action Continuity** — Start Pose, Key Pose, Contact Pose, Impact Pose, End Pose, Stillness, Slow Movement, Rapid Movement, Staccato Action, Repetition, Motion Direction, Position Continuity.
- [ ] **36. Background Types by Location** — Urban Street, Alley, Rooftop, Apartment, Café, Shop, Office, Workshop, Warehouse, Library, Station, Vehicle Interior, Forest, Mountain, Beach, Harbor, Desert, Garden, Ruins, Underground Space, Fantasy Environment, Sci-Fi Environment.
- [ ] **37. Background Mood & Atmosphere** — Calm, Cozy, Warm, Nostalgic, Melancholic, Lonely, Dreamy, Romantic, Mysterious, Eerie, Ominous, Tense, Chaotic, Oppressive, Whimsical, Serene, Ephemeral, Epic, Surreal.
- [ ] **38. Background Detail Levels** — Blank, White Void, Abstract, Speed-line Background, Minimal, Silhouette-only, Simplified, Soft-focus, Medium-detail, Detailed, Highly Detailed, Panoramic Establishing, Pattern-based.
- [ ] **39. Background Details & Props** — Architecture, Walls, Doors, Windows, Ceilings, Arches, Stairs, Floors, Furniture, Books, Cups, Phones, Tools, Bags, Signs, Plants, Trees, Water, Rocks, Clouds, Weather, Smoke, Steam, Reflections, Environmental Storytelling, Worn Surfaces, Discarded Objects.
- [ ] **40. Background Continuity Types** — Independent Location, Persistent Location, Character-interactive Location, Narratively-changing Location, Continuous Background, Recurring Props, Environmental State Changes, Fixed Spatial Landmarks.
- [ ] **41. Shadow Types by Physics** — Form Shadow, Cast Shadow, Contact Shadow, Ambient Occlusion, Self-shadow, Reflected-light Shadow.
- [ ] **42. Shadow Styles** — Hard-edge Shadow, Soft Shadow, Cel-shaded Shadow, Gradient Shadow, Cross-hatched Shadow, Screentone Shadow, Stippled Shadow, Solid-black Shadow, Graphic Shadow, Silhouette Shadow.
- [ ] **43. Shadow Directions & Patterns** — Top-lit Shadow, Side Shadow, Under-eye Shadow, Face-obscuring Shadow, Rim-shadow Contrast, Long Shadow, Dappled Shadow, Layered Shadow, Projected Pattern Shadow.
- [ ] **44. Lighting Sources & Directions** — Key Light, Fill Light, Rim Light, Backlight, Sidelight, Top Light, Underlight, Front Light, Practical Light, Ambient Light, Bounce Light.
- [ ] **45. Lighting Styles & Contrast** — High-key, Low-key, Balanced Lighting, Flat Lighting, High Contrast, Low Contrast, Silhouette Lighting, Chiaroscuro, Diffused Light, Volumetric Light.
- [ ] **46. Lighting Atmospheres** — Morning Light, Golden Hour, Sunset, Twilight, Moonlight, Overcast, Foggy Light, Neon Lighting, Fluorescent Lighting, Candlelight, Firelight, Streetlight, Bioluminescence, Magical Glow.
- [ ] **47. Lighting Parameters** — Direction, Intensity, Color Temperature, Hardness, Contrast Ratio, Ambient Fill, Rim Separation, Volumetric Rays, Bloom, Glare, Lens Flare.
- [ ] **48. Color Systems & Palettes** — Monochrome, Grayscale, Duotone, Limited Palette, Full Color, Complementary, Analogous, Triadic, Split-complementary, Monochromatic, Warm, Cool, Neutral, Mixed.
- [ ] **49. Color Rendering & Contrast** — Muted, Desaturated, Vibrant, Selectively Saturated, High Contrast, Low Contrast, High Key, Low Key, Color Overlay, Duotone Overlay, Vignette, Glow, Color Fringing.
- [ ] **50. Textures & Surface Rendering** — Paper Grain, Rough Paper, Halftone, Screentone, Canvas Texture, Noise, Grain, Fabric Texture, Gradient, Flat Fill, Hatching, Cross-hatching, Stippling, Dot Pattern.
- [ ] **51. Weather & Atmospheric Effects** — Rain, Snow, Fog, Mist, Wind, Storm, Dust, Dust Motes, Pollen, Ash, Snowflakes, Sparks, Smoke, Steam, Fire, Debris.
- [ ] **52. Energy & Environmental Effects** — Electricity, Energy Aura, Magic Particles, Light Trails, Hair Movement, Clothing Flutter, Leaves Blowing, Water Ripples, Depth of Field, Bokeh, Lens Flare, Chromatic Aberration, Motion Blur, Vignette.
- [ ] **53. Narrative Time & Chronology** — Present, Past, Future, Flashback, Flashforward, Time Skip, Time Lapse, Simultaneous Events.
- [ ] **54. Narrative Point of View** — First-person, Third-person, Omniscient Narrator, Limited Point of View, Internal Monologue, External Narration, Unreliable Narrator.
- [ ] **55. Visual Storytelling Devices** — Visual Metaphor, Symbolism, Foreshadowing, Recurring Motif, Callback, Parallelism, Visual Irony, Visual Contrast, Reveal, Concealment, Visual Repetition.
- [ ] **56. Narrative Pacing** — Fast Pacing, Slow Pacing, Pause, Suspense Build-up, Reveal, Climactic Beat, Cliffhanger, Repetition, Extended Silence, Montage.
- [ ] **57. Story World State** — Time of Day, Location, Weather, Character Position, Clothing State, Carried Objects, Open/Closed Doors, Object Placement, Environmental Damage, Physical Contact, Action Outcome, State Continuity.
- [ ] **58. Page Geometry & Layout Rules** — Page Size, Aspect Ratio, Margins, Bleed, Safe Area, Panel Borders, Border Width, Gutters, Panel Padding, Clipping, Reading Order, RTL/LTR, Balloon Placement, Tail Position.
- [ ] **59. Lettering & Export Quality** — Text Fit, Line Breaks, Text Integrity, Font Embedding, Font Licensing, Overflow Detection, Image Resolution, DPI, PDF Export, PNG Export, Page Numbering, Cover, Title Page, End Page.
- [ ] **60. Visual Continuity & Validation** — Character Identity, Style Consistency, Character Count, Attribute Presence, Reference Matching, Pose Continuity, Clothing Continuity, Prop Continuity, Location Continuity, Lighting Continuity, State Tracking, Composition Drift, Verifier Confidence, Retry Policy.

---

## 8. Engine Workstreams and Full Task Lists

## Workstream E1 — Image Generation Engine (Existing; preserve and integrate)

### E1.1 — Baseline preservation and audit
- [x] Image-generation API feasibility and reference-anchored M0 experiment reported complete.
- [x] Project owner says Image Generation Engine is finished.
- [ ] Audit current source files, public interfaces, configuration, and real request flow before integration. Do not rewrite merely for style.
- [ ] Identify the exact supported model/provider operations from live-tested implementation and official docs.
- [ ] Verify key safety, timeouts, budget enforcement, error handling, and result hashes remain correct.
- [ ] Preserve the original M0 evidence and clearly label its sample size and limitations.
- **Acceptance:** existing engine works through a stable contract and does not own other engine responsibilities.

### E1.2 — Knowledge catalogue integration
- [ ] Complete the 60-group research catalogue tasks in Section 6 and Section 7.
- [ ] Define retrieval based on scene intent, cast, camera, mood, visual style, and explicit constraints.
- [ ] Define rule precedence: user constraints, canonical design, scene requirements, research-supported defaults, optional stylistic suggestions.
- [ ] Compile selected knowledge into a structured `VisualSceneSpec` and then into provider instructions.
- [ ] Record exactly which taxonomy/rule versions were retrieved for each run.
- [ ] Keep negative constraints, canonical references, and scene state explicit.
- [ ] Add experiment harnesses to compare unresearched prompts with research-compiled prompts.
- **Acceptance:** visual decisions are traceable to catalogue entries and experiments; no unsupported claim is treated as a guarantee.

## Workstream E2 — Canvas Generation Engine

### E2.1 — Canvas model and geometry
- [ ] Define `CanvasSpec`, `PageSpec`, `PanelSlot`, `GutterSpec`, `MarginSpec`, `BleedSpec`, `SafeAreaSpec`, and layout-template schemas.
- [ ] Support explicit width/height, aspect ratio, resolution, pixel density, physical output size, orientation, page format, and color/background settings.
- [ ] Support single page, spread, vertical-scroll/long canvas, fixed viewport, cover/title page, full bleed, framed, borderless, split canvas, and continuous-background canvas.
- [ ] Support page structures and the full agreed layout family, including regular grids, strips, asymmetric, diagonal, mosaic/montage, split-screen, and freeform arrangements where specified.
- [ ] Define reading order and panel traversal independently of language assumptions.
- [ ] Define geometry constraints and allowed/forbidden overlaps.
- [ ] Implement deterministic canvas generation from validated specs.
- [ ] Render or serialize the canvas as a stable SVG/raster/geometry artifact.
- [ ] Add previews and debug overlays for panel boundaries, safe zones, gutters, and bleed.

### E2.2 — Geometry validation
- [ ] Check every panel is within the intended canvas bounds unless an explicit bleed/overlap rule allows otherwise.
- [ ] Check required gutters, margins, and safe areas.
- [ ] Detect unintended panel overlap and zero/negative dimensions.
- [ ] Validate pixel/physical dimension conversions and rounding.
- [ ] Add property-based or parameterized tests across common and edge-case canvas dimensions.
- **Acceptance:** identical input specs produce identical geometry and a verifiable canvas artifact; invalid geometry fails explicitly.

## Workstream E3 — Image–Canvas Integration Engine

### E3.1 — Placement and fitting
- [ ] Define `PlacementSpec`, image transforms, focal/anchor points, crop region, fit policy, clipping policy, and resampling settings.
- [ ] Implement `contain`, `cover`, crop-to-frame, anchor-preserving fit, focal-point-aware fit, and explicitly approved custom transforms.
- [ ] Preserve aspect ratio by default.
- [ ] Support source-resolution checks and avoid unnecessary upscaling where quality policy disallows it.
- [ ] Map image-local, panel-local, and page-global coordinates correctly.
- [ ] Preserve crop provenance and all transform parameters.
- [ ] Support transparent and opaque inputs with specified alpha compositing.
- [ ] Return structured `PlacedPanelLayer` artifacts with exact target dimensions.

### E3.2 — Placement quality gates
- [ ] Verify final placed dimensions match the target slot exactly.
- [ ] Verify no unintended clipping of required subjects/anchors.
- [ ] Verify selected crop policy was applied rather than silently substituted.
- [ ] Report impossible fits rather than distorting the image.
- [ ] Add tests for aspect ratios, extreme portrait/landscape sources, focal points near edges, transparency, and bounds.
- **Acceptance:** placement is deterministic and reversible/auditable from saved transform metadata; no silent crop, stretch, or offset.

## Workstream E4 — Text Generation Engine

### E4.1 — Structured text generation
- [ ] Define `ScriptBlock`, `DialogueBlock`, `NarrationBlock`, `CaptionBlock`, `MonologueBlock`, `SFXTextBlock`, `SpeakerRef`, `TextProvenance`, and reading-order fields.
- [ ] Generate dialogue, narration, inner monologue, scene/time captions, off-panel speech, radio/phone/robotic speech, interrupted speech, fading speech, and relevant SFX words.
- [ ] Maintain character-specific voice, vocabulary, tone, and style bible constraints.
- [ ] Maintain chronology, causes/effects, scene intent, and continuity with story state.
- [ ] Keep the user's original text immutable when exact preservation is requested.
- [ ] Validate that referenced speakers, entities, props, and locations are declared in the Story Bible or pass through approved canon mutation.
- [ ] Track each text block to story passage, panel, speaker, and generation provenance.
- [ ] Add length/fit guidance without allowing the text engine to silently rewrite content to satisfy layout.
- [ ] Separate semantic text generation from visual text effects.

### E4.2 — Text quality and continuity
- [ ] Validate every text block against required schema and language.
- [ ] Check chronology and state consistency against scene plans.
- [ ] Add human-review hooks for content that cannot be reliably validated deterministically.
- [ ] Ensure unsupported or malformed output fails clearly and is not silently accepted.
- **Acceptance:** the engine returns structured, attributable text and respects exact-user-text requirements.

## Workstream E5 — Typography & Font Generation Engine

### E5.1 — Font and style inventory
- [ ] Create an inventory of typeface families, styles, language coverage, glyph coverage, licenses, and permitted embedding/use.
- [ ] Preserve separate categories for dialogue, narration, captions, SFX, display headings, handwritten, brush, distressed, pixel/retro, serif, sans-serif, script, and other agreed families.
- [ ] Record font licenses and source files; never use assets with unclear rights.
- [ ] Define whether each typeface output is a font file, a generated glyph/lettering asset, a style preset, or only a visual sample. Do not conflate these outputs.

### E5.2 — Typeface/font generation
- [ ] Research technically viable approaches for generating coherent font families rather than isolated attractive letters.
- [ ] Define glyph repertoire and required characters for supported languages.
- [ ] Define glyph metrics, baseline, ascenders/descenders, side bearings, kerning, spacing, weight consistency, and fallback behavior.
- [ ] Build the selected supported generation/authoring path with explicit output formats and licensing review.
- [ ] Validate that all required glyphs are present and no missing characters are silently substituted.
- [ ] Maintain versioned font assets and deterministic build metadata.

### E5.3 — Shaping, measuring, and lettering
- [ ] Implement reliable text shaping using a renderer that supports Arabic correctly.
- [ ] Support RTL, LTR, mixed Arabic/English, punctuation, numerals, ligatures, diacritics, and line-break behavior.
- [ ] Compute actual text bounds after shaping.
- [ ] Implement size, weight, style, width, tracking, leading, alignment, outline/stroke, shadow, fill, opacity, emphasis, and fit options.
- [ ] Produce independent, editable `TextLayer` artifacts.
- [ ] Add text-integrity assertions: rendered content must equal the approved source text.
- [ ] Test long lines, punctuation, diacritics, mixed direction, and constrained balloon interiors.
- **Acceptance:** text measurements match rendered output within defined tolerances; Arabic shaping/RTL and user-text integrity pass regression tests.

## Workstream E6 — Speech Bubble Engine

### E6.1 — Bubble schema and shapes
- [ ] Define `BubbleSpec`, `BubbleLayout`, `BubbleShapeLayer`, `BubbleTail`, `SpeakerAttachment`, and `ReadingOrderNode`.
- [ ] Implement all agreed functional bubble types: dialogue, thought, whisper, shout, scream, narration/caption, inner monologue, off-panel, phone/radio/broadcast/robotic/electronic/telepathic speech, singing, crying, gasps, interruptions, fading/trailing speech.
- [ ] Implement all agreed bubble shapes: oval/ellipse, rounded rectangle, rectangle, cloud, jagged/starburst, dashed/dotted, wavy, distorted, electric, pixelated, decorative, and borderless variants.
- [ ] Implement tail types and relations: standard, curved, short/long, forked, multiple, thought trails, tail-less, off-panel, connected/sequential/shared/overlapping/interrupted/broken/nested/silent balloons.
- [ ] Implement captions and text containers separately from dialogue balloons.

### E6.2 — Spatial placement
- [ ] Consume final panel geometry and text metrics; do not estimate text size from character counts alone.
- [ ] Analyze safe regions, faces, important props, speaker boxes, and composition focal areas.
- [ ] Generate candidate positions according to scene, reading order, and user/layout constraints.
- [ ] Route tails to the correct speaker with no ambiguity.
- [ ] Avoid face occlusion and unapproved overlap with important art.
- [ ] Resolve collisions between balloons, canvas boundaries, panel borders, and other overlays.
- [ ] Support RTL and LTR reading order explicitly.
- [ ] Recompute placements when text/font metrics change.
- [ ] Return structured `needs_human` or layout failure when no valid placement is possible.

### E6.3 — Bubble rendering and tests
- [ ] Render editable bubble shapes as vector/raster layers independent from the glyph layer.
- [ ] Validate bubble interior padding and tail geometry.
- [ ] Add geometry/collision tests and visual regression snapshots for single and multi-speaker scenes.
- **Acceptance:** every bubble has a valid shape, correct speaker relation, readable text area, and defined reading order; conflicts are detected rather than hidden.

## Workstream E7 — Effects & Motion Engine

### E7.1 — Effects system and effect registry
- [ ] Define an `EffectSpec` schema containing effect ID/category, target layer, target region/mask, parameters, ordering/depth, intensity, blend mode, provenance, and reproducibility settings.
- [ ] Preserve all agreed effect families: speed/focus lines, motion trails, action arcs, smears, motion blur, shake/vibration marks, impacts, shockwaves, debris, sparks, smoke, steam, rain, snow, fog, dust, particles, electricity, energy/magic aura, glow, bloom, glare, lens flare, light rays, depth of field, bokeh, chromatic aberration, vignette, and environmental motion.
- [ ] Separate vector/geometry effects from pixel filters, generated overlay assets, and time-based/animated effects if supported later.
- [ ] Define effect compatibility/precedence rules and how style constraints affect rendering.
- [ ] Preserve source art; apply effects as independent non-destructive layers by default.

### E7.2 — Motion and spatial behavior
- [ ] Define direction vectors, focal points, motion paths, strength, length, density, blur radius, threshold, and region masks.
- [ ] Support effect placement behind/in front of characters and relative to text/bubbles.
- [ ] Keep effects within the target panel or apply explicit bleed permission.
- [ ] Avoid obscuring required identity attributes or making text unreadable unless explicitly intended.
- [ ] Ensure effect parameters can be serialized and replayed.

### E7.3 — Quality and validation
- [ ] Add deterministic tests for effect bounds, alpha, blend order, parameter limits, and mask application.
- [ ] Add visual comparisons for major effect families and negative cases.
- [ ] Measure performance for complex layers and large canvases.
- **Acceptance:** effects remain independently editable/removable, reproduce from configuration, and do not mutate unrelated layers.

---

## 9. Final Compositor, Quality, Export, Workspace, and Agent

## Workstream S6 — Final Compositor

- [ ] Define a versioned `LayerGraph` with explicit z-order and source IDs.
- [ ] Support page background, panel backgrounds/art, integration transforms, art-overlap rules, effects under/over art, bubble shapes, text layers, foreground effects, and page-level overlays.
- [ ] Use a deterministic renderer and explicit alpha/color-space handling.
- [ ] Support partial recomposition: changing text or a bubble must not re-run image generation.
- [ ] Preserve all editable layer/artifact references in the composite manifest.
- [ ] Support raster and vector layers where relevant.
- [ ] Produce full-resolution composites and preview-resolution images as separate artifacts.
- [ ] Add pixel-determinism or bounded-render-difference tests appropriate to the rendering backend.
- **Acceptance:** the final page reproduces from the layer graph and underlying assets; independent layers remain traceable.

## Workstream S7 — Quality & Verification

### Deterministic checks
- [ ] Image/file validity and decoded dimensions.
- [ ] Canvas/panel geometry, bounds, margins, gutters, bleed, and overlap rules.
- [ ] Image fit/crop/anchor and coordinate mapping.
- [ ] Required character/prop count and schema constraints when supported by evidence.
- [ ] Bubble bounds, tail association, collision, safe region, and reading order.
- [ ] Text content integrity, font availability, shaping, overflow, and metrics.
- [ ] Effect bounds, alpha, layer ordering, and permitted region.
- [ ] Export file integrity, page count, physical/pixel size, font embedding where applicable.
- [ ] Asset provenance and hash verification.

### Visual checks
- [ ] Character identity and required attributes versus approved references.
- [ ] Style consistency and unwanted visual drift.
- [ ] Scene-state continuity: clothing, props, pose/action outcome, location and environmental state.
- [ ] Composition and focal-point preservation.
- [ ] Lighting/shadow consistency when specified.
- [ ] Text/bubble readability and absence of accidental obscuration.
- [ ] Calibrate model-based judgments against independent human labels.
- [ ] Record precision, recall, false acceptance, false rejection, and uncertainty when a labelled evaluation set is available.
- [ ] Fail closed for required `unsure`, malformed output, missing evidence, or contradictory verdicts.
- [ ] Make quality policies configurable by project/engine without weakening hard constraints.

### Repair routing
- [ ] Every QA failure identifies the responsible artifact/engine and failed rule.
- [ ] Route repair to the owning engine rather than regenerating the whole project by default.
- [ ] Use bounded retries and preserve every failed attempt.
- [ ] Mark unresolved issues `NEEDS_REVIEW`; do not erase them from reports.
- **Acceptance:** QA reports are structured, reproducible, evidence-linked, and have coverage tests.

## Workstream S8 — Export & Delivery

- [ ] Define export profiles for page PDF, per-page PNG, full-page raster, long-scroll/webtoon, and a recomposable project package.
- [ ] Define output dimensions, aspect ratio, pixel density/DPI, color profile, transparency, and compression settings.
- [ ] Embed fonts only when license/format allows; record font licenses in project metadata.
- [ ] Export PDF with correct page boxes, page order, margins, bleed, and reading direction.
- [ ] Export PNG pages with predictable filenames and exact dimensions.
- [ ] Export full-length vertical canvas if selected.
- [ ] Bundle manifest, assets, hashes, engine versions, settings, QA reports, and source lineage as appropriate.
- [ ] Validate the exported files by reopening/parsing them and checking metadata/dimensions.
- [ ] Produce an export summary with success/failure for each output artifact.
- **Acceptance:** every declared output format can be generated and independently validated from an approved composite.

## Workstream UI — User-Facing Project Workspace

- [ ] Preserve the four-step conceptual workflow from the brief: characters/style; cast; story; language/lettering.
- [ ] Add project settings for output type, dimensions, reading direction, language, style, and quality profile.
- [ ] Allow the user to inspect/approve canonical character/style sheets.
- [ ] Allow editing story and scene requirements while preserving immutable source text where requested.
- [ ] Show generation/processing status and progress events from the job manager.
- [ ] Show previews for art, canvas, composed pages, bubbles, lettering, effects, QA, and export artifacts.
- [ ] Provide re-run/repair actions for the responsible stage, with explicit cost/impact where applicable.
- [ ] Provide artifact/version history and differences between attempts.
- [ ] Provide manual review/approval for canon mutations, ambiguous verification, and unresolved QA conflicts.
- [ ] Keep the interface aligned with engine capability; never fake functionality with a disabled-looking control that does nothing.
- **Acceptance:** the core end-to-end workflow works without hand-editing internal files and gives the user control at the points that require approval.

## Workstream S9 — Agent / Coordinator (Design deferred by owner)

The final system must have an Agent capable of calling the agreed tools and engines, but detailed tool design is deferred until the project owner discusses it.

Until the owner approves the design:
- [ ] Do not freeze agent tool names or schemas.
- [ ] Do not create an independent agent per taxonomy group.
- [ ] Do not put specialist engine logic inside the Agent.
- [ ] Keep engine calls accessible through stable contracts so future Agent tools can wrap them.

After the owner-led design session:
- [ ] Record approved user goals, tool boundaries, tool schemas, prerequisites, confirmation rules, and error behavior.
- [ ] Implement tool wrappers that call the specialist engine interfaces.
- [ ] Enforce permissions, project scoping, budget, cancellation, idempotency where possible, and confirmations for expensive/destructive/irreversible operations.
- [ ] Keep durable state in project files/database, not implicit model conversation memory.
- [ ] Give the Agent access to research/knowledge retrieval with evidence provenance.
- [ ] Make plan, action, tool result, validation, and repair steps inspectable in a run trace.
- [ ] Add end-to-end tests proving the Agent chooses valid tools and cannot bypass schema/QA/budget enforcement.
- [ ] Ensure the Agent can request each intended engine output without duplicating the engine's internal business logic.
- **Acceptance:** an approved natural-language project request can be turned into a traceable engine plan and executed while respecting all safety, budget, and data constraints.

---

## 10. End-to-End Pipeline Contracts

- [ ] Define a complete pipeline manifest with project/run IDs, canon snapshot, scene IDs, required outputs, engine versions, configuration hashes, budget cap, and QA policy.
- [ ] Convert the story into structured `ScenePlan` and `PanelPlan` records.
- [ ] Resolve story-state and canon references before dispatching engine work.
- [ ] Generate or validate canvas geometry before final placement; record when art generation precedes geometry and why.
- [ ] Execute image generation using the knowledge selection and canonical reference images.
- [ ] Verify generated artwork before integration when the relevant visual gate is enabled.
- [ ] Place images into canvas slots with deterministic transformations.
- [ ] Generate text blocks and validate story/speaker references.
- [ ] Generate/render fonts and compute actual text metrics.
- [ ] Lay out bubbles and tails using image regions and measured text bounds.
- [ ] Generate effects as independent layers based on panel specifications.
- [ ] Assemble layer graph and render composite.
- [ ] Run final QA and route failures to the relevant engine.
- [ ] Export all requested deliverables and validate them.
- [ ] Record full provenance and provide a human-readable run summary.
- [ ] Support selective recomputation from the earliest affected stage when an input changes.
- **Acceptance:** one project can run from approved brief/story to validated final deliverables with complete traceability and no manual internal file edits.

### Dependency invalidation rules

- A Story Bible canon change invalidates only outputs that depend on the changed canon/version, not unrelated assets.
- A scene action/camera change invalidates that scene's relevant generation and downstream layers.
- A canvas dimension/layout change invalidates affected placement and downstream composites; it may require art regeneration only if the selected image-generation constraints demand it.
- A text change invalidates text metrics, affected bubble placements, composites, QA, and exports; it must not automatically invalidate source art.
- A font change invalidates shaping/metrics, bubble fit, lettering render, composites, QA, and exports; it must not automatically invalidate source art.
- A bubble shape/placement change invalidates bubble render and downstream composite/QA/export only.
- An effect parameter change invalidates that effect layer and downstream composite/QA/export only.
- An export-profile change invalidates export output, not the canonical art or layout unless the profile changes their constraints.

---

## 11. Testing, Benchmarks, and Acceptance Standards

### T11.1 — Unit testing
- [ ] Validate all schemas and error states.
- [ ] Test deterministic geometry and transformation math.
- [ ] Test taxonomy loading/retrieval/compatibility rules.
- [ ] Test Story Bible immutability and state timeline application.
- [ ] Test text shaping/metrics and source-text integrity.
- [ ] Test bubble geometry and collision handling.
- [ ] Test effect parameter validation and layer isolation.
- [ ] Test asset hashes and provenance lineage.
- [ ] Test budget ceilings, timeouts, cancellation, retry count, and failed-attempt logging.

### T11.2 — Integration testing
- [ ] Test each pair of connected engines with real contracts and deterministic test fixtures.
- [ ] Test image-to-canvas placement at portrait, landscape, square, and edge dimensions.
- [ ] Test long and short texts in each supported bubble family.
- [ ] Test Arabic RTL, English LTR, and mixed-language lettering.
- [ ] Test effects behind/in front of art, bubbles, and text.
- [ ] Test compositor ordering and selective recomputation.
- [ ] Test PDF/PNG exports by reopening the actual files and verifying dimensions/content.

### T11.3 — Visual regression and human review
- [ ] Build original controlled test cases covering all major visual categories.
- [ ] Keep approved reference output and expected constraints versioned.
- [ ] Compare outputs using appropriate pixel/structural metrics where suitable; do not rely on pixel similarity alone for semantically variable generated images.
- [ ] Conduct blind human review for character/visual consistency, typography, bubble placement, and artistic readability when making quality claims.
- [ ] Record test set size, sampling, known limitations, disagreement and uncertainty.
- [ ] Keep negative examples and failed runs rather than selecting only successes.

### T11.4 — End-to-end benchmark
- [ ] Preserve M0's A/B result as a historical feasibility experiment with its sample-size limitations.
- [ ] Design a larger controlled benchmark with frozen scene prompts, canonical references, consistent evaluation rules, repeat runs, and logged model/config versions.
- [ ] Compare text-only, reference-anchored, and reference-anchored-plus-verification/retry modes where available.
- [ ] Measure character/style drift, attribute-level errors, first-pass yield, attempts per accepted panel, cost per accepted panel, latency, and verifier precision/recall.
- [ ] Publish the benchmark method and machine-readable raw results with no secrets.
- [ ] Include failures, filtered requests, `needs_human`, and unfinished scenes in denominators as specified by the protocol.
- **Acceptance:** claims in README/demo match measured results and disclose sample size and limitations.

---

## 12. Milestones and Exit Gates

Milestones order work and dependencies. They do not reduce the final scope.

### M0 — Feasibility & API Foundation [REPORTED COMPLETE]
- [x] API key/configuration and model catalogue verification reported successful.
- [x] Image generation / reference-anchored feasibility tests reported successful.
- [x] Two-case visual verifier smoke test reported successful.
- [x] One SAM segmentation test reported successful.
- [x] Unit tests and reports committed locally per prior agent report.
- [ ] Reconfirm current local Git state and local evidence before relying on it for future release documentation.
- **Exit gate:** historical M0 report retained; claims remain appropriately qualified.

### M1 — Contracts, Story Bible, State, Asset/Run Infrastructure
- [ ] Complete Sections 5.1–5.5.
- [ ] Audit and adapt existing image engine to the approved contract without unnecessary rewrite.
- [ ] Define test fixtures and dry-run support.
- [ ] Validate all schemas and provenance.
- **Exit gate:** Story Bible and shared data contracts are stable; no engine has ambiguous ownership; automated tests pass.

### M2 — Research & Image Knowledge Catalogue
- [ ] Complete Section 6 and every group in Section 7.
- [ ] Implement source/evidence registry, taxonomy versioning, retrieval, and compatibility logic.
- [ ] Bind image engine generation requests to selected knowledge records and log the selection.
- [ ] Run controlled prompt tests and document results.
- **Exit gate:** all 60 groups preserved and represented; research/evidence status and limitations are explicit; catalogue selection is testable.

### M3 — Canvas Generation Engine
- [ ] Complete E2 tasks and geometry tests.
- **Exit gate:** deterministic, validated canvas/page/panel geometry for all agreed page structures.

### M4 — Image–Canvas Integration Engine
- [ ] Complete E3 tasks and transformation tests.
- **Exit gate:** real generated image can be integrated into a defined canvas slot with exact dimensions and audited transformations.

### M5 — Text Generation Engine
- [ ] Complete E4 tasks and provenance/continuity tests.
- **Exit gate:** a structured scene can produce validated text blocks with the correct speaker, function, language, and source handling.

### M6 — Typography & Font Generation Engine
- [ ] Complete E5 research, valid font/style outputs, shaping, metrics, and rendering.
- **Exit gate:** approved source text renders accurately in supported languages; actual metrics are available to the Bubble Engine; claims about generated font files are evidence-backed.

### M7 — Speech Bubble Engine
- [ ] Complete E6 shapes, tails, placement, reading order, collision checks, and renderer.
- **Exit gate:** dialogue and captions are laid out using real text metrics and correct speaker links, with explicit unresolved failures.

### M8 — Effects & Motion Engine
- [ ] Complete E7 effect registry, required effects, non-destructive layers, and tests.
- **Exit gate:** configured effects can be rendered reproducibly as independent layers in correct spatial/order relationships.

### M9 — Final Compositor
- [ ] Complete layer graph, rendering, provenance, and selective recomposition.
- **Exit gate:** a full page is reproducibly assembled from all available engine artifacts with correct layer order.

### M10 — Quality & Verification
- [ ] Complete deterministic checks, visual checks, calibration, and repair routing.
- **Exit gate:** a page cannot be approved while required checks fail or remain unresolved; each failure points to an owning stage.

### M11 — Export & Delivery
- [ ] Complete PDF, per-page PNG, long-scroll/web formats, source package, and validators.
- **Exit gate:** approved outputs can be exported and independently reopened/validated with full manifest and provenance.

### M12 — Full Agent/Coordinator Integration
- [ ] Conduct the separate owner-led discussion and record the approved Agent tool architecture.
- [ ] Implement the Agent only after its tools/contracts are approved.
- [ ] Test engine orchestration, error routing, budgets, approvals, cancellation, run trace, and selective recomputation.
- **Exit gate:** an approved project request can drive all required engines through auditable tool calls without bypassing the deterministic gates.

### M13 — User Workflow Integration
- [ ] Build the complete project workflow described in the original brief.
- [ ] Integrate project state, engines, live progress, previews, approvals, repair, version history, and exports.
- **Exit gate:** a user can create and deliver an illustrated project through the interface without editing internal files manually.

### M14 — End-to-End Quality, Release, and Delivery
- [ ] Complete automated tests and benchmark protocol.
- [ ] Verify licensing and asset rights.
- [ ] Perform clean-install and logged-out/public-repository checks where release requires them.
- [ ] Add setup instructions, limitations, troubleshooting, architecture guide, and reproducibility instructions.
- [ ] Scan Git history and release artifacts for secrets.
- [ ] Produce a three-minute demo using only permitted original/new work if still targeting the hackathon.
- [ ] Confirm current hackathon rules, dates, submission state, and required deliverables before any public submission action.
- [ ] Prepare final release package and record its hashes and version.
- **Exit gate:** every promised product path works, known limitations are disclosed, and the release is reproducible.

---

## 13. Global Definition of Done

No engine, integration, or milestone is complete until all applicable criteria below are satisfied.

- [ ] Its responsibility and non-responsibilities are documented.
- [ ] Its input/output contracts are versioned and validated.
- [ ] It has real implementation code, not only a plan or placeholder.
- [ ] It has unit tests for valid, invalid, boundary, and failure cases.
- [ ] It has integration tests with the neighboring engine contracts.
- [ ] It records actual operations, outputs, errors, and provenance.
- [ ] It has a reproducible path to inspect and verify its outputs.
- [ ] It does not leak credentials or unsafe payloads.
- [ ] Its supported features and limitations are accurately described.
- [ ] Its acceptance criteria are satisfied by evidence.
- [ ] Any unsupported item remains tracked as incomplete rather than removed.

---

## 14. Global Non-Functional Requirements

### Reliability
- [ ] Every external request has a timeout and bounded retry policy.
- [ ] Transient failures are distinguished from deterministic errors such as invalid payload, authentication failure, or policy rejection.
- [ ] Every failed attempt remains visible in logs.
- [ ] Operations that can be resumed have explicit resumability/idempotency rules.

### Security and privacy
- [ ] API credentials remain in environment configuration and never appear in Git or logs.
- [ ] Public endpoints, if introduced, have authentication/authorization, rate limits, and spend limits appropriate to their exposure.
- [ ] Uploaded/user story text and user assets have clear storage and retention behavior.
- [ ] Any external API transmission is documented.
- [ ] No external asset is used without rights and license tracking.

### Performance and cost
- [ ] Concurrency is controlled and provider limits are respected.
- [ ] Image generation and verifier cost are attributed per run/panel/accepted result where billing evidence supports it.
- [ ] Large-image processing has measured memory/time bounds.
- [ ] Unnecessary generation is avoided through dependency invalidation and selective recomputation.
- [ ] Long-running jobs provide progress and cancellation behavior.

### Accessibility and usability
- [ ] The UI presents actionable errors and progress.
- [ ] Preview and approval steps make uncertain AI outputs visible.
- [ ] RTL/LTR behavior is correct across the complete pipeline, not only in a text widget.
- [ ] Exported text remains legible at its intended viewing/printing size.

### Maintainability
- [ ] Engine responsibilities remain isolated.
- [ ] Research and engine rules are versioned.
- [ ] Schema changes have migration/compatibility notes.
- [ ] Dependencies and licenses are recorded.
- [ ] Logs and output manifests are documented.

---

## 15. Repository and Documentation Deliverables

- [ ] `README.md` — product purpose, setup, architecture, supported functionality, evidence-backed results, limitations, and run instructions.
- [ ] `INKLOOP_PROJECT_BRIEF.md` — original brief retained as a historical specification.
- [ ] `INKLOOP_TASKS.md` — this file, updated after every approved milestone.
- [ ] `docs/architecture.md` — final component/dependency diagrams and ownership boundaries.
- [ ] `docs/engine-contracts.md` — schemas, units, coordinates, errors, and versioning.
- [ ] `docs/decisions.md` — approved decisions with evidence and rationale.
- [ ] `docs/research-methodology.md` — research classifications and experiment method.
- [ ] `docs/quality-standards.md` — measurable acceptance and validation rules.
- [ ] `docs/m0-report.md` and `docs/m0-visual-report.md` — preserve historical feasibility evidence and limits.
- [ ] `docs/milestones/` — one report per milestone, including outcomes, failures, costs/usage, tests, and commit.
- [ ] `CONTRIBUTIONS.md` — accurately describes work built during the relevant time period; no fabricated or misattributed contributions.
- [ ] `LICENSE` — chosen repository license compatible with all included assets/code.
- [ ] `THIRD_PARTY_NOTICES.md` or equivalent — libraries, fonts, licenses, model/provider terms, and notices.
- [ ] `.env.example` — variable names and safe placeholders only.
- [ ] Secret scanning and repository hygiene checks.

---

## 16. Required Final Artifact Manifest

A completed project/run must be capable of producing a manifest including, as applicable:

- Project ID and version.
- Story Bible/canon snapshot hash.
- Story and scene/panel IDs.
- All used taxonomy record IDs and versions.
- Image-generation model/configuration/reference hashes.
- Canvas specifications and geometry version.
- Image placement/crop/transformation settings.
- Text source, block IDs, speaker IDs, and provenance.
- Typeface/font IDs, versions, licenses, shaping settings, and metrics.
- Bubble geometry, speaker tails, order and collision decisions.
- Effect IDs, configurations, masks, ordering, and source assets.
- Layer graph and compositor version.
- QA results and unresolved issues.
- Export profile, dimensions, format, hashes, and validation outcome.
- Every relevant generation attempt, status, request ID, latency, usage, and cost classification.

The manifest must never contain API keys or unnecessary raw credential-bearing payloads.

---

## 17. Change Control and Anti-Drift Protocol

Before executing any new coding prompt, the agent must:

1. Read this task file and the relevant source brief sections.
2. Check the current Git status and last commit.
3. Identify the active milestone and its exit criteria.
4. State which exact tasks it will execute and which files it expects to modify.
5. Keep changes limited to the active milestone, unless a dependency is demonstrably necessary and recorded.
6. Execute the requested implementation and tests.
7. Review the diff and inspect generated artifacts.
8. Update the status of this task file only where evidence warrants it.
9. Record decisions, test outcomes, failures, limitations, and commit hash in the milestone report.
10. Stop at the exit gate and wait for the project lead's next prompt.

### Prohibited behavior

- No “cleanup” that removes listed requirements.
- No changing the product from comic-production engines into a general AI tool.
- No collapsing the seven specialist production engines into one generic engine.
- No replacing the research catalogue with a flat prompt list.
- No treating “the API returned 200” as proof that the visual result is correct.
- No claiming a font file was generated when only a sample image or preset exists.
- No claiming exact geometry without numerical tests.
- No treating a visually plausible bubble as correct without tail/speaker/reading-order checks.
- No deleting failed generations, failed tests, or negative benchmark examples.
- No assuming future Agent design decisions; wait for the owner-led discussion.
- No publishing, submitting, pushing, deleting, or spending significant credits without the relevant authorized action and checks.

---

## 18. Immediate Next Actions

- [ ] Place this file at the repository root as `INKLOOP_TASKS.md` and review it with the project owner.
- [ ] Verify all current M0 artifacts and Git history in the actual project workspace.
- [ ] Keep the Image Generation Engine as completed work; audit its boundaries rather than rewrite it.
- [ ] Start M1: shared contracts, coordinate conventions, Story Bible/state, asset registry, and run execution infrastructure.
- [ ] Begin the research-backed image-generation knowledge catalogue work in parallel only where it does not destabilize M1 contracts; preserve all 60 taxonomy groups.
- [ ] Do not build the full UI or Agent tool design before the engine contracts and dependencies are agreed.
- [ ] Do not begin M2/M3/etc. until the active exit gate has a report and the project lead reviews it.

**Project-wide success definition:** InkLoop is complete when the seven independent production engines, shared services, final compositor, quality verification, export pipeline, research-backed knowledge catalogue, approved Agent orchestration, and end-to-end user workflow operate together to produce traceable, high-quality illustrated comic deliverables with reproducible evidence and no silently omitted scope.
