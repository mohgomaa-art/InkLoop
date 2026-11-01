# InkLoop Research Dossier — Manga & Comic Panel Types

**Prepared:** 2026-10-29  
**Purpose:** Establish a source-grounded, implementation-oriented taxonomy of manga/comic panels for InkLoop's Canvas Engine (E2), Image–Canvas Integration (E3), Story/Panel Planning, visual reference analysis, and later Agent tool selection.  
**Evidence policy:** Distinguish established terminology and research findings from a proposed InkLoop classification. This is a synthesis, not a claim that the industry has one universally accepted, exhaustive list of panel types.

---

## Executive finding

There is **no single finite, universally standardized list of “all panel types.”** Comics scholarship distinguishes several systems that are often mistakenly combined: (1) geometry of an individual panel, (2) how panels are arranged in a page or scroll, (3) how the panel is bounded by a frame/page edge, (4) what narrative role it plays, (5) what camera/framing it uses, and (6) how it relates in time or meaning to adjacent panels. These are separate axes, and one panel can have a value on several axes at once.

For example, a panel can simultaneously be **tall + polygonal + bleed + a Peak narrative role + a close-up + part of an action-to-action sequence**. InkLoop should therefore use a **multi-axis panel descriptor**, not a single `panel_type` enum.

This approach follows comics-layout research that separates the spatial relationships between panels (external compositional structure, ECS) from composition inside one panel (internal compositional structure, ICS); research also distinguishes page-layout structure from narrative meaning. [Cohn, *Visual Language Theory and the Scientific Study of Comics* (2018 preprint)](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf) and [Cohn et al., *The Architecture of Visual Narrative Comprehension*](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.00680/full).

## 1. Classification axis A — Page and layout arrangement

These describe **the relationship between panels on a page/canvas**, not what is drawn inside a panel.

| Layout family | Recognizable forms / aliases | What it means | Production considerations for InkLoop |
|---|---|---|---|
| Regular grid | Pure grid, equal grid, modular grid | Panels align into consistent rows and columns; the classic path is usually row-wise then down, adjusted for reading direction. | E2 can derive slots from rows/columns, ratios, gutters and margins. Must encode reading order separately from coordinates. |
| Unequal grid | Asymmetric grid, mixed-size grid | Panels share row/column structure but use different sizes or proportions. | Store explicit ratios or slot rectangles; do not assume uniform cells. |
| Tiered layout | Tiers, horizontal rows, strip rows | A page is organized into horizontal bands, each containing one or more panels. | Represent a row/tier as a parent grouping so rows can contain columns or inset structures. |
| Horizontal stagger | Misaligned vertical edges between panels while a row remains grouped | Vertical boundaries do not line up, but the horizontal tier remains perceptually continuous. | Verify reading order and avoid ambiguous cells; coordinates should not rely on a perfect grid. |
| Vertical stagger | Misaligned horizontal edges while vertical groupings remain | The bottoms/tops of adjacent panels do not align; vertical continuity is retained. | Run a reading-order ambiguity check; visual adjacency can compete with row-based reading. |
| Blockage / blockage layout | Tall panel beside a stack of smaller panels | A large vertical panel spans the height of multiple neighboring panels and can redirect the reading path downward. | Requires explicit sequencing edges; naive row-major sorting can be wrong. |
| Wide-screen stack | Full-width or nearly full-width horizontal panels stacked vertically | Each row may be dominated by one wide panel, increasing vertical rhythm. | Useful for cinematic pauses, landscape reveals and digital adaptation; assess vertical page economy. |
| Vertical-column layout | One or more tall columns, sometimes subdivided | Panels primarily sequence down a column. | Commonly interacts with manga/manhua reading grammar; reading direction must be explicit and tested. |
| Inset / embedded panel | Insert panel inside a larger dominant panel | A smaller panel is enclosed inside a larger panel. It can show a detail, reaction, parallel event, or a second temporal layer. | Requires an explicit parent/child containment relationship and a Z-order; not merely overlapping rectangles. |
| Overlapping panels | Panel shapes physically overlap | One panel intrudes into another panel's region. | Distinguish deliberate overlap from accidental collision. Define clipping, border priority and z-order. |
| Separated / floating panels | Panels detached from the main grid, with visible space around them | Panels are grouped by proximity or composition rather than a continuous shared grid. | Reading order needs explicit sequence IDs; do not infer from X/Y alone. |
| Diagonal / oblique layout | Slanted cuts, diagonal tiers, slanted panel edges | Diagonal boundaries create directional tension and can support action or instability. | Polygon geometry needed; verify non-self-intersection, reading path and text-safe areas. |
| Mixed-diagonal / freeform layout | Several angled directions, irregular cuts, interlocking panels | A more complex composition using mixed angles and shapes. | Treat as constrained polygons, not a rectangular grid. Require robust path ordering and human preview. |
| Radial / converging composition | Panel boundaries or panel placement converge on a focal point | A page directs attention toward a central event or impact. | This is a useful descriptive layout label, not a universally standardized panel class; store focal point and directional constraints. |
| Spiral / circular flow | Panels arranged in a spiral or around a center | A deliberate non-linear route guides the eye around a center. | Experimental; must declare exact reading order and avoid ambiguous navigation. |
| Split / divided view | Two or more simultaneous subviews or divided regions | A scene is divided into concurrent views, locations, participants or a before/after contrast. | Model as distinct panel regions with synchronization/relationship metadata; do not assume each region is sequential. |
| Montage layout | Several images/aspects assembled into a panel or compact group | A montage conveys a compressed set of visual elements, a mental state, conceptual space or multiple moments. | Could be a single compound panel or multiple separate panels; store this distinction explicitly. |
| Compound / grouped panel unit | Multiple panels visually or narratively grouped as one larger constituent | Panels form a perceptual/narrative group within the page. | Use grouping IDs and parent/child structure for plans and readability diagnostics. |
| Full-page splash | One image occupies essentially the full page | A single-page emphasis or introductory/reveal image. It may have borders or bleed to the page edge. | A page-level layout containing one dominant panel; distinguish “splash” from the `bleed` boundary property. |
| Double-page spread / double splash | One composition spans a two-page opening | The spread is designed across both pages; the binding/gutter can divide the central art. Manga scholarship refers to the opening as *mi-hiraki*. | Requires two-page coordinate space, binding/gutter safety, reading order across pages and a print/preview distinction. |
| Four-panel strip | Yonkoma / 4-koma, conventionally four vertical panels | A four-panel comic form often associated with the narrative progression *ki-shō-ten-ketsu* (introduction, development, turn, conclusion). | Implement as a named sequence template, not as a generic rule that all four panels must be equal. Preserve allowed variants. |
| Vertical-scroll composition | Webtoon / long-scroll layout | Panels are arranged along a continuous vertical canvas with variable whitespace between them. | Scroll distance and empty space can control pause and anticipation; page-turn constraints differ from print pages. |

**Research basis:** Cohn explicitly defines pure grids, horizontal/vertical staggering, blockage, inset panels, separation, overlap, variable shapes, and borderless layouts; the article also discusses cultural variation and reading-path constraints. [Cohn 2018, layout sections](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf). The CO-MIX comic creation manual describes splash pages, inserts, slanted panels, borderless panels and size-based pacing. [CO-MIX manual](https://www.mc-celje.si/f/docs/CO-MIX/COMIX_Manual_ENG.pdf). For the four-panel form, see [Cambridge Companion to Manga and Anime, “Newspaper Comic Strips”](https://www.cambridge.org/core/books/abs/cambridge-companion-to-manga-and-anime/newspaper-comic-strips/DA1999C404A16BF8833FE420228FCB28) and the [Embassy of Japan Yonkoma guideline](https://www.uk.emb-japan.go.jp/files/100069624.pdf).

## 2. Classification axis B — Individual panel geometry and shape

These describe the actual **shape of the panel region**. The shape is independent of narrative role, content and page layout.

1. **Square panel** — near-equal width and height.
2. **Horizontal rectangle** — wider than tall; useful for broad spatial views or a horizontal action path.
3. **Vertical rectangle / tall panel** — taller than wide; can emphasize height, descent/ascent, a character's full figure, or vertical pacing.
4. **Panoramic / ultra-wide panel** — unusually wide and shallow; often used for a landscape, establishing view, or long movement.
5. **Narrow strip / sliver panel** — thin horizontal or vertical frame; useful for compressed moments, a glance, pause, or detail (functional effect depends on context, not shape alone).
6. **Triangle / wedge** — triangular panel or tapered wedge.
7. **Trapezoid** — quadrilateral with one pair of parallel sides; common in angled action layouts.
8. **Parallelogram / slanted quadrilateral** — opposing sides remain parallel but edges are tilted.
9. **General polygon** — irregular multi-sided panel with straight edges.
10. **Circular panel** — round boundary.
11. **Oval / elliptical panel** — elongated circular boundary.
12. **Curved / organic boundary** — freeform or curved panel boundary.
13. **Hybrid geometry** — a page combines multiple shape families.
14. **Borderless geometry** — the panel's visual boundary is implicit rather than a complete closed stroke. This is a boundary treatment and may be combined with any underlying region shape.
15. **Custom path** — a vector-defined shape when standard geometry is insufficient.

Comics panels are not restricted to rectangles. The CO-MIX manual notes that panels may be any shape, though square and rectangular panels are common; comics scholarship likewise records circles, triangles, irregular polygons, fluid/organic shapes and borderless panels. [CO-MIX manual](https://www.mc-celje.si/f/docs/CO-MIX/COMIX_Manual_ENG.pdf); [Cohn 2018](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).

### Size is a separate attribute, not a shape

Use measurable size classes (tiny/small/medium/large/dominant) only as derived or author-defined metadata based on area or page ratio. Do not treat “large panel” as a shape. Size affects pacing and emphasis, but its effect is not deterministic. The CO-MIX guide describes large panels as often slowing perceived time and small, closely spaced panels as often accelerating pace. Manga scholar Natsume Fusanosuke's analysis describes panel-size/shape change as a way to create **compression and release**, while emphasizing that panel sequence segments time. [CO-MIX manual](https://www.mc-celje.si/f/docs/CO-MIX/COMIX_Manual_ENG.pdf); [Natsume Fusanosuke, “The Functions of Panels (koma) in Manga”](https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html).

## 3. Classification axis C — Frame, page-edge and boundary treatment

These labels often get confused, but they are not interchangeable.

- **Framed / closed panel:** a visible, substantially complete boundary separates it from neighboring content.
- **Borderless / frameless panel:** no complete visible frame; the reader infers the panel area from composition, whitespace, background, or adjacent frames.
- **Bleed panel / bleeding artwork:** artwork extends to or beyond the printed page edge or trim region. In comics scholarship, “bleeding panels” can also describe panels extending beyond the page edge; use the project's schema to disambiguate art bleed from panel geometry.
- **Full bleed:** artwork extends to the page edge on all relevant sides (exact printer bleed must still be represented separately as production geometry).
- **Splash with bleed:** a page-dominant image also reaches the page edge. Splash and bleed are separate properties; a splash need not bleed, and a smaller panel may bleed.
- **Inset panel:** a smaller panel is enclosed within a larger dominant panel. It may use a border different from the parent image.
- **Frame-breaking figure/object:** a character, hand, weapon, speed line or other artwork intentionally crosses the panel's frame into neighboring space. This is an art-layer/frame relationship, not automatically the same as panel bleed.
- **Shared-edge / shared-border panels:** adjacent panels use a common boundary. The model should avoid double-counting the same physical line as two unrelated borders.
- **Open edge / partial border:** one or more edges are absent or visually interrupted.
- **Broken frame / interrupted border:** a frame is intentionally interrupted by an object, word, impact, or another compositional element.
- **Nested panel:** an inset-like structure with explicit containment depth; distinguish a panel truly inside another panel from a foreground image overlapping an outer frame.
- **Gutter-separated panels:** panels separated by visible blank space.
- **Zero-gutter / tight-edge panels:** little or no space between regions; shared borders or other boundary semantics must remain unambiguous.
- **Non-white gutter:** the gutter itself has a color, pattern, texture, or graphic treatment. The gutter is not necessarily white.

A useful terminology reference defines a gutter as the space between framed panels and bleed as artwork extending to/beyond the page edge; the CO-MIX guide describes inserting a smaller panel inside a larger image and removing selected borders for emphasis. [Comics terminology diagram/definitions](https://hhsenglish.com/wp-content/uploads/2018/08/graphicnoveltermspdf-copy.pdf); [CO-MIX manual](https://www.mc-celje.si/f/docs/CO-MIX/COMIX_Manual_ENG.pdf). Cohn's research explicitly treats panel borders, lack of borders, overlap, proximity/separation, and bleed as distinct layout features. [Cohn 2018](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).

## 4. Classification axis D — Narrative role of a panel

These describe **what a panel contributes to the narrative sequence**, rather than its physical shape. A square and a tall polygonal panel can both perform the same narrative role.

### 4.1 Research-based Visual Narrative Grammar (VNG)

Neil Cohn's research proposes core narrative categories for how panels function in a sequence:

- **Establisher (E):** establishes the entities, situation or relationship without yet advancing the main action.
- **Initial (I):** initiates tension or begins an event; often shows preparation or the start of a path/action.
- **Prolongation (L):** extends a developing action or state between initiation and climax.
- **Peak (P):** the main event/climax where tension or action reaches its critical point.
- **Release (R):** aftermath, resolution, or dissipation of narrative tension.

Cohn's grammar describes a canonical pattern that can include an Establisher, then Initial/Prolongation, then Peak, followed optionally by Release. These are formal narrative roles, not fixed visual templates, and not every panel is a different role. [Cohn, *Visual Narrative Structure*](https://onlinelibrary.wiley.com/doi/10.1111/cogs.12016); [Cohn 2018 review](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).

### 4.2 Other useful planning tags

The following are useful operational tags for an authoring tool. Some are established descriptive terms; others are functional labels that may overlap with VNG roles and should not be treated as a single canonical scholarly taxonomy.

- **Establishing/environment panel:** clarifies where the action takes place; often a wide/long view.
- **Action/preparation panel:** shows the setup for a meaningful action; may map to an Initial.
- **Action continuation panel:** extends an action across time; may map to a Prolongation.
- **Impact/contact panel:** depicts the decisive contact or event; often maps to a Peak.
- **Reaction panel:** shows a character's emotional or physical response to an event.
- **Aftermath/result panel:** shows the consequence of an action; may map to a Release.
- **Close emotional panel:** focuses attention on facial expression, eye, mouth, hand, or posture.
- **Detail / insert panel:** isolates a relevant object, hand, clue, wound, device, token, or environmental detail.
- **POV panel:** depicts what a character sees or an approximation of their viewpoint.
- **Reverse-view / shot-reverse-shot panel:** alternates viewpoints or speakers in a conversation. This is a framing/editing pattern, not a geometry type.
- **Dialogue / two-shot panel:** presents two or more participants together; the panel itself may still use any shot scale.
- **Silent / pause / beat panel:** uses little or no text to create a pause, anticipation, emphasis, discomfort or reflection. Its meaning depends on placement.
- **Reveal panel:** withholds then discloses a person, object, environment, identity, or event.
- **Transition / time-place panel:** marks a move to a new scene, location, time, or state.
- **Cutaway panel:** temporarily shows a related object, off-screen action, another location, or detail that contributes to the scene.
- **Montage panel/sequence:** condenses multiple elements or moments; determine whether they are within one panel or across several panels.
- **Flashback / memory / dream panel:** tags a temporal or subjective layer. It may use a distinct style/border, but no border style universally means “flashback.”
- **Explanatory / diagrammatic panel:** communicates a process, mechanism, map, plan, or visual explanation rather than only a dramatic moment.
- **Atmosphere / aspect panel:** presents setting, weather, objects, light, or mood without a strongly depicted character action.
- **Recap / summary panel:** condenses prior events; use sparingly and keep its temporal reference explicit.
- **Cliffhanger / page-turn setup panel:** positions information and pacing so the next panel or page turn provides a payoff. This is a sequence/page role, not an isolated geometry.
- **Parallel action / cross-cut panel:** alternates concurrent actions or locations; must record temporal relation where ambiguity matters.
- **Symbolic / metaphorical panel:** combines or substitutes imagery to express an idea or mental state. The image may be metaphorical rather than a literal event in the story world.
- **Chibi/comedic reaction cut-in:** a style/function tag for a comedic reaction; it is not a structural shape category.

Andrei Molotiu's comics-studies glossary also identifies montage panels, point-of-view framing, and image/text relationships; the manga scholarship emphasizes that panels can guide attention and psychological participation, not merely divide the page. [Molotiu, *List of Terms for Comics Studies*](https://comicsforum.org/2013/07/26/list-of-terms-for-comics-studies-by-andrei-molotiu/); [Natsume Fusanosuke](https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html).

## 5. Classification axis E — Framing scale, camera angle and point of view

Do **not** confuse shot/framing terms with the geometry or layout of a panel. A panel shape is the container; framing describes how much of the represented scene/subject is shown and from which viewpoint.

### 5.1 Framing scale

- **Extreme long shot / extreme wide shot:** subject is small relative to environment; establishes scale or isolation.
- **Long shot / wide shot:** shows substantial environment and the figure/action in context.
- **Full shot:** frames the whole person/object, where appropriate.
- **Medium-long / three-quarter shot:** an intermediate crop between full and medium; terminology differs across traditions.
- **Medium shot:** commonly a person from approximately waist/knees upward; exact convention varies by source and context.
- **Medium close-up / close shot:** emphasizes head/upper torso or a comparable portion of the subject.
- **Close-up:** tight view of a face, object, or significant region.
- **Extreme close-up / detail close-up:** eye, mouth, fingertip, mechanism, or other tiny region.

### 5.2 Angle / viewpoint

- Eye-level / straight-on.
- High angle / bird's-eye family.
- Low angle / worm's-eye family.
- Overhead / top-down.
- Ground-level / upward view.
- Dutch / canted angle: represented horizon or scene is tilted relative to the page.
- Point-of-view (POV): viewpoint linked to a character's seeing.
- Over-the-shoulder.
- Profile, frontal, rear view, three-quarter view (subject orientation descriptors, not panel geometry).

Terminology and exact boundaries vary across film/comics teaching traditions. A cross-cultural study of Japanese and American comics gives common scale categories (long, full, medium, close and close-up) and explicitly distinguishes “attentional” categories from filmic shot scales. Molotiu's glossary lists distance, angle, canted, depth-of-field and POV framing. [Framing Attention in Japanese and American Comics](https://pmc.ncbi.nlm.nih.gov/articles/PMC3449338/); [Molotiu](https://comicsforum.org/2013/07/26/list-of-terms-for-comics-studies-by-andrei-molotiu/).

## 6. Classification axis F — Relationship between adjacent panels (transitions)

These classify **the transition between panels**, not a standalone panel shape. Scott McCloud's familiar six-part model is widely taught:

1. **Moment-to-moment:** a small time interval or continuing instant; very little changes between panels.
2. **Action-to-action:** the same subject progresses through different actions or stages of an event.
3. **Subject-to-subject:** the sequence shifts between different subjects within a related scene.
4. **Scene-to-scene:** a meaningful jump in time and/or space.
5. **Aspect-to-aspect:** the sequence surveys different aspects of a place, idea, mood or situation, often with no explicit action driving each panel.
6. **Non-sequitur:** panels appear unconnected, leaving a more experimental or associative link to the reader.

Important research caution: scholars note that the boundaries between some categories can be fuzzy and that the six classes do not capture every transition, especially non-narrative or complex sequences. Therefore InkLoop should use them as useful annotations, not rigid rules enforced as universal truth. [McCloud transition summary in *Making Comics*](https://www.sci.utah.edu/~chris/Making-Comics-McCloud.pdf); [Molotiu's critical discussion](https://comicsforum.org/2013/07/26/list-of-terms-for-comics-studies-by-andrei-molotiu/); [University of Winnipeg teaching source](https://www.uwinnipeg.ca/1b19/docs/how-comics-work-web-cc-by-nc-nd.pdf).

Additional useful transition tags in production planning:
- continuity / same time and place;
- elapsed time;
- hard scene cut;
- parallel events / cross-cut;
- flashback entry/exit;
- reveal / withheld information;
- match cut / visual echo;
- repeated image / loop;
- simultaneous action;
- cause → effect;
- anticipation → impact → aftermath;
- emotional reaction;
- abrupt associative jump.

These extra labels are a proposed project vocabulary, not a canonical exhaustive scholarly list.

## 7. Manga-specific panel patterns and page practices

### Yonkoma (4-koma)
A conventional four-panel vertical format, commonly read from top to bottom, often organized through *ki-shō-ten-ketsu*: introduction, development, turn, conclusion. Contemporary examples vary; this is a conventional template rather than a requirement that every four-panel narrative obey the pattern mechanically. Sources: [Cambridge University Press, “Newspaper Comic Strips”](https://www.cambridge.org/core/books/abs/cambridge-companion-to-manga-and-anime/newspaper-comic-strips/DA1999C404A16BF8833FE420228FCB28) and [Embassy of Japan Yonkoma Guidelines](https://www.uk.emb-japan.go.jp/files/100069624.pdf).

### Manga right-to-left reading path
Traditional Japanese manga usually begins at the top-right and proceeds toward the bottom-left, but projects may use different directions due to publication, localization or platform conventions. Reading direction must be project metadata and must be tested against panel-order logic, not inferred from the word “manga” alone. The research article by Natsume and the translators describes the right-to-left movement and also discusses historical variation. [Natsume article](https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html).

### Mi-hiraki (two-page spread)
A two-page opening can be designed as one compositional unit; changes in panel size and direction can compress attention on one page and release it on the next. The physical center fold/inner margin still matters for printed output. [Natsume Fusanosuke](https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html).

### Tachi-kiri / bleed
Manga often uses artwork reaching the page edge. For InkLoop, separate the visual concept “bleed” from print-production bleed dimensions: the first describes the panel/art boundary relationship; the second is extra physical image area beyond trim. Do not let “full bleed” silently override trim or safe-area validation.

### Compression and release
A sequence can move from larger/open imagery to smaller/tighter frames and then return to a large/open frame. Manga research describes this contrast as compression (asshuku) and release (kaihō); it affects attention and subjective pacing. It should be treated as an art-direction/sequence objective, not a fixed geometric template. [Natsume Fusanosuke](https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html).

### Webtoon / vertical scroll
A long-scroll format abandons the fixed printed page as the primary pacing unit. Inter-panel blank space can be variable and can contribute to duration/anticipation; a page-turn reveal becomes a scroll reveal. This is a **canvas/publishing format**, not an individual panel shape. [Cambridge, *Innovations in Digital Comics*](https://www.cambridge.org/core/elements/innovations-in-digital-comics/E7F321812D3D20FC303E4A1783E24928); [Chen 2023, “Flipping Vs. Scrolling in Digital Narratives”](https://asistdl.onlinelibrary.wiley.com/doi/full/10.1002/pra2.896).

## 8. Evidence-based principles for designing panel layouts

These are useful tendencies, not inviolable rules:

- **Reading order is a first-class contract.** Geometric sorting alone is unreliable for staggered, blocked, inset, overlapping and freeform layouts. Store explicit order plus geometry and test the path. [Cohn 2018](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).
- **Keep the path smooth and legible.** Research summarizes reader preferences for grouped regions, smooth paths, avoiding skipped panels, and avoiding gaps in the intended route. A deliberate break can still work, but it should be intentional. [Cohn 2018](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).
- **Layout and story meaning are related but not identical.** Rearranging the same panels may change navigation and pacing without changing the basic semantic content, provided reading order is preserved. [Cohn 2018](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).
- **Size, shape and spacing can shape perceived timing.** Large panels may give a moment weight or duration; tight small panels may accelerate perceived action. This is contextual, not deterministic. [CO-MIX manual](https://www.mc-celje.si/f/docs/CO-MIX/COMIX_Manual_ENG.pdf); [Natsume](https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html).
- **A panel boundary is not merely decoration.** Gutters, frame presence/absence, bleed and overlap help structure the reader's page navigation and infer what belongs together. [Cohn 2018](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).
- **Cultural conventions matter, but avoid stereotypes.** Research reports differences in the frequencies of certain layout arrangements across corpora, not a rule that every manga or every Western comic must use a particular arrangement. [Cohn 2018](https://visuallanguagelab.com/P/2018.ESiC.NC.pdf).
- **Digital scroll spacing is meaningful.** Variable space between vertical panels can influence anticipation and temporal experience; it should be modeled as a deliberate pacing property, not leftover blank height. [Cambridge, *Innovations in Digital Comics*](https://www.cambridge.org/core/elements/innovations-in-digital-comics/E7F321812D3D20FC303E4A1783E24928).

## 9. Recommended InkLoop panel data model

Do not introduce a single `type` property that mixes geometry, narrative role, layout and framing. Use separate typed fields (names are a proposal; reconcile with the existing E2 schemas before implementation):

```json
{
  "panel_id": "panel_03",
  "geometry": {
    "shape": "polygon",
    "rect": {"x": 0, "y": 0, "width": 1000, "height": 1400},
    "vertices": [],
    "coordinate_space": "page_px"
  },
  "layout": {
    "relation": "blockage",
    "group_id": "tier_02",
    "parent_panel_id": null,
    "z_index": 3,
    "intentional_overlap": false
  },
  "boundary": {
    "frame_style": "closed",
    "bleed_to_trim": false,
    "full_bleed": false,
    "frame_break_art": false,
    "gutter_policy": "standard"
  },
  "narrative": {
    "role": "peak",
    "function_tags": ["impact", "action"],
    "transition_from_previous": "action_to_action",
    "time_relation": "continuous"
  },
  "framing": {
    "scale": "close_up",
    "angle": "low",
    "viewpoint": "third_person",
    "focal_point": null
  },
  "reading_order": 3,
  "directionality": "rtl",
  "source_reference_ids": [],
  "notes": ""
}
```

This JSON is **illustrative only**; it is not a claim about the current schemas. This JSON is illustrative only; actual implementation should use the real `Rect`/`Point` contract and Pydantic models already in the repository. The important proposal is the multi-axis separation:

- `geometry.shape`: rectangle, polygon, ellipse, custom path;
- `layout.relation`: grid, tier, stagger, blockage, inset, overlap, floating, splash, spread, vertical-scroll, freeform;
- `boundary`: closed, partial, borderless; bleed; frame-break behavior; gutter treatment;
- `narrative.role`: VNG role or a controlled project role;
- `narrative.transition_from_previous`: relation to prior panel;
- `framing.scale`, `angle`, `viewpoint`;
- `reading_order` independent from geometry;
- `parent/group/z_index` to represent hierarchy and overlap;
- explicit `intentional_overlap`/clipping policy;
- provenance and referenced source assets.

### Validation constraints

- Every panel has stable ID, positive area and a declared coordinate space.
- Every sequence has explicit, unique reading-order indices (or a declared parallel-reading model).
- Parent/inset relationships must be acyclic and spatially valid.
- Polygon boundaries must be valid and non-self-intersecting.
- Overlap must be explicitly allowed and assigned z-order/clipping policy.
- Bleed geometry and print bleed dimensions remain separate fields.
- Splash page, spread, and vertical-scroll are canvas/page layout modes, not primitive polygon kinds.
- Narrative role, transition type, framing scale and geometry must not be collapsed into one enum.
- RTL/LTR is project-level and must be propagated to sequence ordering, not assumed from a visual template name.
- If an image is only a collage/search-results screenshot containing many templates, first identify/crop a selected source panel/layout before reconstructing its exact geometry. Never treat the whole collage as a single layout without the user's intent.

## 10. Relationship to the InkLoop engines

- **E2 Canvas Generation:** owns page/canvas specs, panel slot geometry, page/layout templates, margins, gutters, bleed, safe area, reading order and geometry validation. It should offer templates and constrained custom geometry, not silently generate a “finished comic.”
- **E3 Image–Canvas Integration:** fits/crops artwork into an E2 slot, applies polygon clipping, focal points and transformations. The panel type taxonomy helps determine clipping and fit policy, but E3 should not redraw the layout.
- **E1 Image Generation:** consumes the panel's narrative purpose, framing, style, character state and selected references to generate the art. It should not invent text/lettering inside the art if the product contract reserves text rendering to downstream engines.
- **E4 Text Generation:** creates text artifacts linked to story/panel/speaker, not panel geometry.
- **E5 Typography:** shapes and measures text including Arabic RTL and mixed direction.
- **E6 Speech Bubbles:** places bubble/tail geometry using text metrics, speaker, reading order and collision constraints.
- **E7 Effects:** makes separate effect layers aligned to panel/action/focal regions.
- **Compositor:** assembles all approved layers in order.
- **Quality/Verification:** validates geometry, continuity, image attributes, text integrity, collision and output correctness.
- **Agent:** chooses from the capabilities actually registered as available and combines them through typed tools; it must not dispatch future engines just because this taxonomy describes them.

## 11. Suggested reference-analysis workflow for a panel screenshot

When a user submits an image like a search-results collage of manga panel templates:

1. Classify the input as a collage/reference sheet, not as one panel layout.
2. Detect candidate template thumbnails and crop each candidate region where licensing/terms and input policy allow local inspection.
3. Ask or infer from explicit user selection which candidate template should be analyzed; do not assume the entire collage is the target.
4. For each chosen template, identify the page boundary and whether it is a single page, spread or scroll.
5. Segment panel regions, frames, gutters, bleed areas, insets and overlap relationships.
6. Infer candidate reading order using project direction plus adjacency; represent confidence and mark ambiguous order for user review.
7. Convert detected regions into page-space rectangles/polygons, with a mapping from image coordinates to canvas coordinates.
8. Validate bounds, polygons, gaps, overlap, safe areas and any inferred full-bleed behavior.
9. Present a structural SVG preview with panel IDs and reading order.
10. Allow correction before saving the layout as a user-approved template or running E2 generation.
11. Keep original image provenance and never assert that an externally sourced template has clear commercial reuse rights without checking its license.

Automated extraction from arbitrary template images is a separate vision capability; it should not be claimed as already implemented by E2 merely because E2 can generate deterministic panel geometry.

## 12. Research gaps and cautions

- Industry naming is inconsistent. “Splash,” “full bleed,” “borderless,” “frame-breaking,” and “inset” are sometimes used imprecisely. InkLoop should define them in its own schema and tests.
- “All types” cannot mean a finite closed list: creators combine shapes, border styles, layouts, roles, shot scales and transitions in many ways. The appropriate goal is an extensible taxonomy across independent axes.
- Several functional tags (reaction, reveal, silent beat, cliffhanger, cutaway) are useful for planning but are not all equivalent formal categories in comics scholarship.
- VNG categories describe narrative role in sequences, not spatial panel types.
- McCloud's six transitions describe relationships between adjacent panels, not image shapes.
- A panel's shot scale/angle is not its external page layout.
- The evidence for some perceived effects of size/shape is interpretive or context-dependent; do not encode artistic generalizations as universal quality guarantees.
- The source corpus and cultural findings should not be generalized to all manga genres, readers or individual artists.

## 13. References

1. Neil Cohn, “Visual Language Theory and the Scientific Study of Comics” (2018 chapter preprint, *Empirical Comics Research*). PDF: https://visuallanguagelab.com/P/2018.ESiC.NC.pdf
2. Neil Cohn et al., “The Architecture of Visual Narrative Comprehension: The Interaction of Narrative Structure and Page Layout in Understanding Comics” (2014). https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.00680/full
3. Neil Cohn, “Visual Narrative Structure” (2013, *Cognitive Science*). https://onlinelibrary.wiley.com/doi/10.1111/cogs.12016
4. Neil Cohn, “Framing Attention in Japanese and American Comics: Cross-Cultural Differences in Attentional Structure” (2012). https://pmc.ncbi.nlm.nih.gov/articles/PMC3449338/
5. Natsume Fusanosuke, trans. Jon Holt and Teppei Fukuda, “The Functions of Panels (koma) in Manga” (2021). https://www.japanesestudies.org.uk/ejcjs/vol21/iss2/holt_fukuda.html
6. Andrei Molotiu, “List of Terms for Comics Studies” (2013). https://comicsforum.org/2013/07/26/list-of-terms-for-comics-studies-by-andrei-molotiu/
7. CO-MIX consortium, *Methodology on Inclusive Youth Work Through Comics* (2022). https://www.mc-celje.si/f/docs/CO-MIX/COMIX_Manual_ENG.pdf
8. Ronald Stewart, “Newspaper Comic Strips,” in *The Cambridge Companion to Manga and Anime* (online 2024). https://www.cambridge.org/core/books/abs/cambridge-companion-to-manga-and-anime/newspaper-comic-strips/DA1999C404A16BF8833FE420228FCB28
9. Embassy of Japan in the UK, *Yonkoma Manga Guidelines*. https://www.uk.emb-japan.go.jp/files/100069624.pdf
10. *Innovations in Digital Comics*, Cambridge University Press. https://www.cambridge.org/core/elements/innovations-in-digital-comics/E7F321812D3D20FC303E4A1783E24928
11. Ching-Shiuan Chen, “Flipping Vs. Scrolling in Digital Narratives: Reader Engagement and Reading Patterns in Comic Layouts” (2023). https://asistdl.onlinelibrary.wiley.com/doi/full/10.1002/pra2.896
12. “Comics Terminology” annotated reference (educational handout). https://hhsenglish.com/wp-content/uploads/2018/08/graphicnoveltermspdf-copy.pdf

---

## Recommended next step for InkLoop

Promote this research into a versioned **Panel Taxonomy v1** in the project knowledge catalogue (especially existing taxonomy domains for comic formats, page structures, panel shapes, panel borders/relationships, composition, page geometry/layout, narrative pacing and continuity). Keep every claim tagged as sourced, inferred or a hypothesis. Then define a versioned layout descriptor schema shared by E2/E3 and the Agent. Add tests for all named structural arrangements, and keep research-backed narrative/framing tags separate from deterministic geometric constraints.
