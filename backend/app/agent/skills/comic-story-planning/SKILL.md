---
name: comic-story-planning
description: Professional narrative architecture, scene dynamics, character agency, and comics adaptation during the story planning stage.
triggers:
  - story planning
  - plan story
  - create comic story
  - develop script
  - plot structure
  - scene beats
  - character motivation
  - dialogue writing
  - comics adaptation
  - narrative outline
non_triggers:
  - canvas panel resizing
  - typography font selection
  - raw image generation without narrative context
---

# Comic Story Planning

**Tools this workflow may use:** `planning.plan_panels`, `canon.inspect_characters`, `canvas.create_page_from_template`, `canvas.create_custom_page`, `canvas.verify_page`.

## Mission

Transform raw creator ideas into structured, compelling, visually adaptable comic story blueprints BEFORE panel geometry or image generation begins.

The planner does not invent arbitrary lore or replace creator intent with generic AI tropes. It deepens narrative drive through causality, character agency, scene turning points, and comics-specific visual pacing.

---

## 1. Grounding in Creative Intent

Before proposing beats or compiling panels:
1. **Read Creator Context**: Extract the core premise, tone, audience, format (paged comic, manga, webtoon, graphic novel), and creator constraints.
2. **Inspect Canon Lore**: Call `canon.inspect_characters` to retrieve verified canonical character profiles, attributes, relationships, and visual invariants.
3. **Preserve Creator Canon**: Never invent unauthorized canon backstories, alter established relationships, or contradict Story Bible rules. If the creator introduces story-local characters, describe them in `story_cast` without writing them into global Canon.
4. **Clarify Genuine Ambiguities**: If the user's premise is underspecified, ask one targeted question rather than assuming a generic genre default.

---

## 2. Narrative Architecture & Pacing

Every compelling comic story progresses through cause-and-effect rather than episodic lists of events ("this happened, therefore X, but Y interrupted, leading to Z", never "and then, and then").

1. **Establish the Core Conflict**:
   - What does the protagonist want immediately? (External objective)
   - What deeper need or flaw complicates this? (Internal stake)
   - What tangible obstacle or opposing force creates resistance?
2. **Select the Structural Model**:
   - *Micro-Story / 1-4 Pages*: Fast hook -> immediate complication -> turning point decision -> punchy resolution or twist.
   - *Kishōtenketsu (4-Koma / Manga)*: Ki (Introduction) -> Shō (Development) -> Ten (Twist / Perspective Shift) -> Ketsu (Conclusion / Realization).
   - *Multi-Page Dramatic Arc*: Setup & inciting incident -> progressive complications & reversals -> crisis & turning point -> climax -> meaningful aftermath.
   - *Mystery / Investigation*: Intriguing clue -> false lead / complication -> deduction through action -> dramatic reveal.
3. **Escalate Stakes Dynamically**:
   - Each page must change the situation: an attempt fails, new information raises the danger, or a relationship is altered. Avoid static scenes where characters repeat established information.

*(See `references/story_structures.md` for detailed structural breakdown and pacing formulas.)*

---

## 3. Character Agency & Dialogue Craft

Characters must drive the story through decisions and actions; they must not simply be passive witnesses to external events.

1. **Active Decisions & Consequences**:
   - Ensure the protagonist makes choices under pressure.
   - Every choice must have consequences that propel the next beat forward.
2. **Differentiated Character Voices**:
   - Characters should have distinct speech cadences, vocabulary, and sentence lengths reflecting their personality, background, and emotional state.
   - Avoid generic, interchangeable, overly formal, or robotic speech.
3. **Dialogue Discipline for Comics**:
   - **Concise Word Limits**: Spoken dialogue should ideally be **8 words or fewer**, with an absolute hard ceiling of **12 words** for newly drafted lines.
   - **Subtext Over Exposition**: Characters rarely state their exact feelings out loud. Let subtext, eye contact, and body language carry emotional depth.
   - **Visual Storytelling Over Speech**: If the artwork can show a character's reaction (e.g. eyes widening, hands clenching, looking away), leave the panel silent. Never write dialogue that explains what is already visible.

*(See `references/character_arcs.md` for character agency frameworks and dialogue contrast techniques.)*

---

## 4. Professional Scene Construction

Every scene must justify its presence by transforming the story's emotional or narrative state.

1. **Scene Dynamics**:
   - **Starting Situation**: Where does the scene open and what is the character's immediate goal?
   - **Obstacle / Conflict**: What unexpected friction blocks their objective?
   - **Tactics**: How does the character adapt and attempt to overcome the obstacle?
   - **Turning Point**: The critical moment of reversal where expectations shift.
   - **Emotional Shift**: How the character's internal state changes from the scene's start to its end.
   - **Consequence / Hook**: What does this outcome force the character to do in the following scene?

*(See `references/scene_craft.md` for the Goal-Conflict-Disaster-Reaction cycle and transition mechanics.)*

---

## 5. Comics Adaptation & Visual Staging

Translating narrative prose into comic art is not simply dividing paragraphs into panels. It requires visual orchestration.

1. **Show vs. Imply**:
   - Choose the peak moment of an action, not the setup or aftermath, unless the reaction carries greater emotional weight.
   - Use panel transitions purposefully: Moment-to-Moment, Action-to-Action, Subject-to-Subject, Scene-to-Scene, Aspect-to-Aspect.
2. **Page Rhythm & Density**:
   - Vary panel density by narrative pacing: High action or fast dialogue uses 5-6 dynamic panels; contemplative, emotional, or establishing beats use 1-3 spacious panels.
   - Avoid monotonous equal square grids unless intentionally evoking strict classic comic strip timing.
3. **Page-Turn Reveals**:
   - In paged formats, place cliffhangers, shocking reveals, or dramatic entrances on the bottom-right panel of an odd-numbered page (or top of the next page) to maximize the physical page-turn surprise.

*(See `references/comics_adaptation.md` for panel density guides, transition strategies, and visual reveal staging.)*

---

## 6. Output Contract: Structured Story Blueprint

When story development is complete, compile the narrative into a reviewable `StoryBlueprintDraft`:

```json
{
  "project_id": "proj_story_01",
  "title": "The Lantern That Remembered",
  "page_count": 2,
  "premise": "On a quiet city rooftop, Gomaa and Muse reconstruct a broken lantern, unaware its hidden starlight map reveals forgotten wishes.",
  "audience_tone": "Poetic, atmospheric, curious wonder",
  "story_arc": "Gomaa repairs the relic with technical care while Muse watches; lighting the flame unexpectedly projects a luminous star chart, prompting them to release it as a beacon for lost dreams.",
  "reading_direction": "rtl",
  "pages": [
    {
      "page_number": 1,
      "summary": "Gomaa finishes assembling the lantern while Muse inspects the brass lens.",
      "beats": [ ... ]
    }
  ]
}
```

This blueprint is passed directly into `compile_story_blueprint` or `planning.plan_panels`.
The skill **never** invents panel geometry directly; page geometry remains the exclusive responsibility of `CanvasEngine` (E2).
