# Comic, Manga, Manhwa, and Picture-Book Visual Storytelling

**Research checked:** 30 October 2026  
**Purpose:** A practical, evidence-linked guide for creators and for InkLoop’s story, image, Canvas, lettering, and verification workflows.

## How to read this guide

This guide combines three kinds of material:

- **Research finding:** a claim from peer-reviewed or scholarly work. It describes evidence or a theory, not a universal recipe.
- **Creator guidance:** advice from working artists, publishers, production software teams, or lettering specialists. Conventions vary by creator, market, language, and audience.
- **InkLoop recommendation:** an implementation proposal derived from the sources and the current product architecture. It is not presented as an industry rule.

No format has one compulsory panel count, page grid, art style, font, bubble shape, or emotional vocabulary. The useful question is what a choice asks the reader to notice, feel, infer, or do next.

## 1. The common storytelling foundation

### 1.1 Build a scene from change

A scene becomes legible when something changes: a character pursues a goal, encounters resistance, learns something, makes a choice, changes position or relationship, or sees a consequence. The page should show the change rather than merely repeat the premise. In comics, images, text, framing, and the gaps between images jointly carry the account; readers infer some of the action between panels. [Cohn, “Visual Narrative Structure”](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12016); [Laubrock & Dunst, “Computational Approaches to Comics Analysis”](https://onlinelibrary.wiley.com/doi/10.1111/tops.12476); [Iyyer et al., “The Amazing Mysteries of the Gutter”](https://arxiv.org/abs/1611.05118).

**Creator workflow:** write a one-sentence scene goal, obstacle, turn, and outcome. Then choose which parts need to be seen, heard, or inferred. Do not turn every sentence of prose into one panel; combine repeated information and give important discoveries room.

### 1.2 Theme is a pattern of choices, not a label

A theme becomes human when the character’s decisions repeatedly put a value under pressure. “Evidence over ambition,” for example, can recur as a visual contrast between a flashy promise and a careful test, then pay off in the final decision. This is a craft recommendation rather than a formula demonstrated by a single study. Scholarly visual-narrative work supports separating event structure, visual sequence, and reader inference; it does not prescribe which themes a creator must use. [Cohn](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12016); [Mills et al., “Multimodal Language of Attitude in Digital Composition”](https://journals.sagepub.com/doi/10.1177/0741088319897978).

### 1.3 Panel transitions and reader inference

An image sequence can show an establishing situation, a continuing action, a change, a reaction, or a result. The transition between panels controls how much the reader must infer. A close pair of related images can read as continuous; a larger break, changed place, or page turn can mark a stronger transition. Research on visual narrative treats panel sequence and layout as interacting structures, and research on gutters describes the reader’s inferences across omitted time and action. [Cohn](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12016); [The Architecture of Visual Narrative Comprehension](https://pmc.ncbi.nlm.nih.gov/articles/PMC4076615/); [The Amazing Mysteries of the Gutter](https://arxiv.org/abs/1611.05118).

**InkLoop recommendation:** each planned panel should state its story function, visible action, important new information, emotional intention, and relationship to the prior/next panel. Layout selection should follow those decisions rather than a fixed default grid.

## 2. Format comparison

| Format | Common reading/production conditions | Useful pacing choices | InkLoop planning implication |
|---|---|---|---|
| Japanese manga | Often right-to-left in Japanese editions; print pages and monochrome screentone traditions are common, but styles and publication formats vary. | Strong shifts between detail and silence, close expressions, inserts, broad establishing views, varied panel shapes, and deliberate page-turn reveals. | Store reading direction explicitly. Do not infer it solely from a style name or user’s language. Keep panel order and dialogue order separate and validate both. |
| Western print comics | Often left-to-right in English editions; page architecture, tiers, splash pages, captions, SFX, and balloon flow can be prominent. | Page-level composition can build a reveal or make a large action image a destination. Lettering is designed with artwork, not added as an afterthought. | Plan page turn and page-level focus before placing art. Reserve real text areas and keep panels variable when narrative weight differs. |
| Manhwa and vertical-scroll webtoons | Korean manhwa appears in print and digital forms; many contemporary webtoons are designed for vertical scrolling and phone reading. | Vertical distance, blank space, gradual reveal, long panels, and scroll-triggered timing can control suspense and emotional rhythm. Long-scroll design differs from a print page; spacing should have a purpose. | Add a vertical-scroll mode with device-width preview, scroll sequence, reveal checkpoints, and pacing gaps. Do not squeeze a vertical episode into a page grid. |
| Graphic novels | Book-length comics can use any regional convention, color system, page design, and narrative structure. | Long-form arcs allow motifs, visual callbacks, chapter breaks, silent passages, and slower scenes. | Maintain continuity across chapters and versions, while allowing intentional changes in viewpoint, tone, and style. |
| Picture/storybooks | Text and illustration share a spread or page; page turns, reader age, read-aloud rhythm, and image-led narrative are central concerns. Some books use few words or no words. | A repeated visual motif, large image, pause, reveal, or turn can carry an emotional beat. Text can complement the image instead of describing it. | Treat spread/page turn as a first-class story boundary. Support narration separately from speech and allow text-free storytelling. |

These are broad production tendencies, not exclusive identities. WEBTOON’s creator resources are a source for platform practice; scholarship examines how vertical scrolling and digital reading affect the reading experience; the 2026 study of scroll panels categorizes spatial expansion, time control, emotional rhythm, and information integration. [WEBTOON Academy](https://www.webtoons.com/en/creators101/webtoon-academy); [Berube et al., “Moving with the Story”: The Haptics of Reader Experience and Response to Digital Comics](https://doi.org/10.1080/13614568.2024.2374291); [Kim, “An Analysis of Continuous Vertical Expansion in Webtoon Scroll Panels”](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART003332306). The latter is a narrow analysis of one panel category, not a complete rulebook for webtoon composition.

### 2.1 Manga and paged comics: compose the page as a whole

Thumbnailing lets a creator test panel sequence, movement, dialogue, and balloon placement before investing in finished drawings. VIZ describes manga “name” thumbnails as a rough draft where story pacing, character movement, dialogue, and sound effects are planned; it also notes that balloon placement affects composition. Clip Studio’s creator guidance discusses how panel size, silhouette, action, expression, scene changes, and gutters affect flow. [VIZ Media, “Manga Creation 101”](https://www.viz.com/blog/posts/manga-creation-101); [Clip Studio, “Pro Artist’s Guide to Comic & Manga Layouts”](https://www.clipstudio.net/how-to-draw/archives/160963).

Use a large panel when the moment needs space or emphasis, smaller panels when subdivisions make timing or reaction readable, and a splash when the page benefits from a single dominant image. A sequence of equal rectangles can be effective for deliberate rhythm, but it should not become an automatic answer to every scene. [Clip Studio layout guide](https://www.clipstudio.net/how-to-draw/archives/160963); [Cohn et al., “The Architecture of Visual Narrative Comprehension”](https://pmc.ncbi.nlm.nih.gov/articles/PMC4076615/).

### 2.2 Manhwa/webtoon: use the scroll as time

Vertical scroll gives the reader control over reveal timing through a physical gesture. Empty space can delay a reveal, isolate a reaction, or slow emotional rhythm; it can also become dead space if it has no narrative purpose. A 2024 reader study discusses scrolling as a tactile part of digital-comic reading and its relation to anticipation; Korean scholarship analyzes expanded vertical panels as spatial, temporal, emotional, and informational strategies. [Berube et al., “Moving with the Story”](https://doi.org/10.1080/13614568.2024.2374291); [Kim 2026](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART003332306).

**Example:** show a hand reaching toward an object, use a short scroll gap, then reveal the character’s face after the result. The gap contributes anticipation; it should not be inserted mechanically between every panel.

### 2.3 Picturebooks and illustrated stories: coordinate image and words

Picturebook page design includes page turns, type placement, frames, characterization, perspective, color, and the relationship between text and image. A World Bank guide for writers and illustrators names these as separate design considerations. Research on picturebook visual language describes pacing as shaped by text division, layout, composition, and image-text interaction. [World Bank, *Read@Home Writers’ and Illustrators’ Guide*](https://thedocs.worldbank.org/en/doc/3c02f6956bbc8428ba6b9cf8909438f9-0140012022/related/Read-Home-Writers-and-Illustrators-Guide-World-Bank.pdf); [“Children’s Book Illustrations: Visual Language of Picture Books”](https://archive.sciendo.com/CRIS/cris.2014.2014.issue-1/cris-2014-0002/cris-2014-0002.pdf).

**Creator workflow:** ask what the illustration adds that the text does not, and what the text adds that the picture does not. Avoid captions that simply restate everything visible unless repetition is deliberate.

## 3. Panel composition, action, and dynamics

### 3.1 Vary the camera for a story reason

An establishing view locates a scene; a medium view can show interaction; a close-up can isolate expression or evidence; an insert can make an object/action legible; a point-of-view image can align the reader with a character; and a reaction image can reveal consequence. These are practical shot descriptions, not a mandatory checklist. Clip Studio’s layout guidance advises varying view and composition rather than relying on repetitive character busts. [Clip Studio layout guide](https://www.clipstudio.net/how-to-draw/archives/160963); [Clip Studio comic creation](https://www.clipstudio.net/en/comics-manga/comic-creation/).

**A six-beat action example:**

1. Wide: show the goal and spatial relationships.
2. Medium: show the character committing to an action.
3. Close insert: show contact or a meaningful object change.
4. Reaction: show the immediate consequence.
5. Wider counter-action: reveal how the world or another character responds.
6. Hold or aftermath: let the consequence land before the next event.

Do not force six panels if one panel communicates the moment better. Change panel count and proportions to serve the beat.

### 3.2 Readability of movement

An action image should make the acting subject, direction, contact point, and consequence understandable. Use pose direction, silhouettes, gesture, overlap, perspective, background cues, and selective motion marks to make the path of action readable. Research into comics flow finds that the directionality of panel content and following layout can align; body posture is a notable cue, though flow is not a universal metric for artistic quality. [Foulsham & Cohn, “Going with the Comics Flow”](https://doi.org/10.1080/21504857.2025.2593920).

**InkLoop recommendation:** vary the action axis and shot scale across a sequence; flag repeated composition as a review hint, not an error. Validate panel order and masks independently from the source artwork and image transform.

### 3.3 Page flow and gutters

Panel arrangements affect scanning and segmentation. The reader needs a plausible order, particularly when panels are nonrectangular, overlapping, inset, or arranged outside a simple grid. Scholarly eye-tracking work reports effects of layout and narrative structure on processing, and notes regressions across panels; it supports treating layout as a meaning-bearing structure. [Foulsham & Cohn, 2026, “On the Interaction Between Layout and Narrative in the Processing of Comic Strips”](https://pubmed.ncbi.nlm.nih.gov/42691285/); [Cohn et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4076615/).

**Creator check:** trace the intended order with a finger at the final reading size. Confirm that speech/caption order follows the same direction. On a scroll canvas, inspect the narrow-phone view, not only the full-resolution editor.

## 4. Image design and reference continuity

### 4.1 Describe an image in layers

A concise panel brief should identify:

- **Story beat:** what changes in this frame.
- **Subject and cast:** exact canonical IDs/versions; which characters are present and which are absent.
- **Acting:** pose, gaze, action, expression, and interaction.
- **Camera:** shot scale, angle, viewpoint, and focal hierarchy.
- **Place and time:** location identity plus scene-specific conditions.
- **Art direction:** selected style/version, medium, line, palette, lighting, texture, and detail density.
- **Composition:** subject position, negative space reserved for text, and relevant panel crop/aspect ratio.
- **Continuity constraints:** identity anchors, props, clothing/state, screen direction, and prior-panel references.
- **Text handling:** exact visible lettering only when the provider can render it reliably; otherwise reserve clean space and apply editable lettering afterward.

This is an InkLoop recommendation informed by professional storyboard and image-reference workflows. Meta’s Muse Image API accepts text and reference images and supports generation, edits, and iterative refinement; Midjourney’s documentation likewise distinguishes content instructions from supplied style-reference images. These capabilities are provider-specific and do not imply perfect style or identity matching. [Meta Model API, “Image Generation with Muse Image”](https://dev.meta.ai/docs/image-generation); [Midjourney, “Style Reference”](https://docs.midjourney.com/hc/en-us/articles/32180011136653-Style-Reference).

### 4.2 Treat style and identity as different controls

Character identity covers stable recognizable traits; pose, emotion, clothing condition, and scene behavior may vary. Style covers medium and rendering choices such as contour, brush, shading, palette, texture, and background treatment. A style reference should not change the character’s identity. A character reference should not silently override the chosen style. This distinction is a product recommendation, not a promise that a generative model will obey every constraint.

**InkLoop recommendation:** compile references as typed roles with source asset ID/version and strength/weight where supported. Keep one profile-version lock per selected style. Attach only relevant references to each panel. Never say “exact,” “guaranteed,” or “100% consistent”; report the actual references sent and any QA outcome.

### 4.3 Continuity across panels

Continuity includes identity, clothing, props, geography, time, lighting, screen direction, and changing state. A character may intentionally become wet, injured, frightened, or more distant without changing canonical identity. A location can remain the same while weather, time, or set dressing changes. Production thumbnails and character profiles are useful because they keep visual decisions available across repeated drawing. [VIZ Media](https://www.viz.com/blog/posts/manga-creation-101); [Clip Studio comic creation](https://www.clipstudio.net/en/comics-manga/comic-creation/).

**Creator check:** before the next panel, compare the character anchors and location reference with the last accepted image; verify only relevant differences. Do not regenerate a whole page because one panel has a scoped continuity defect.

## 5. Effects, visual symbols, and atmosphere

Effects should explain force, sound, speed, impact, focus, mood, or a shift in perception. Speed lines, impact bursts, screentones, halftones, lighting, blur, symbolic marks, and onomatopoeia have different functions; adding all of them at once often obscures the action. Clip Studio documents action lines and screentones as available comic-making techniques and materials. [Clip Studio, “Effects and Tones”](https://www.clipstudio.net/en/comics-manga/tool/effects-tones.html); [Clip Studio, “Tools & Techniques”](https://www.clipstudio.net/en/comics-manga/tools-techniques/).

**Practical use:**

- Use directional lines when the movement path needs emphasis.
- Use an impact shape or distortion at the contact point, not as generic decoration.
- Use halftone or background reduction to manage contrast and focus.
- Use symbolic marks only when the chosen visual language makes their meaning understandable.
- Keep effect layers editable and separate from character identity and source artwork.
- Reserve a quiet panel when contrast or emotional pause is more effective than another effect.

The emotional interpretation of a visual device depends on genre, culture, context, and repetition; effects are not universal emotion labels.

## 6. Dialogue, lettering, fonts, and bubbles

### 6.1 Lettering is part of composition

VIZ’s thumbnail guidance explicitly puts dialogue and balloon placement into early page planning. Clip Studio’s typography guidance discusses dialogue font, sound-effect font, text placement, voice, and balloon margins. Readability comes before decorative lettering, while lettering should still fit the work’s voice and market conventions. [VIZ Media](https://www.viz.com/blog/posts/manga-creation-101); [Clip Studio, “Effective Storytelling and Design Tips”](https://www.clipstudio.net/en/comics-manga/design-tips/).

**Practical hierarchy:**

- Dialogue: highly readable font and stable size/spacing.
- Narration/captions: distinct but compatible treatment.
- SFX: expressive display treatment that does not compete with critical dialogue.
- Emphasis: limited bold, scale, tilt, or shape changes tied to vocal intent.
- Font selection: verify glyph coverage, punctuation, language shaping, and license before bundling.

Blambot’s professional letterer guide presents balloon and lettering traditions while explicitly acknowledging variation among editors and practitioners. Treat uppercase, punctuation, balloon conventions, and character-specific fonts as style decisions rather than global invariants. [Blambot, “Comic Book Grammar & Tradition”](https://blambot.com/pages/comic-book-grammar-tradition).

### 6.2 Balloon shape, tail, speaker, and reading order

A balloon has at least four separate concerns: the body shape, text layout, tail geometry, and semantic speaker link. These should remain editable and linked, not flattened into the generated art. Balloon shape can support delivery (ordinary speech, thought, shout, whisper, machine/radio, or narration), but text and context still carry meaning.

The SIGGRAPH Comic Chat paper describes procedural balloon construction and layout, including variable text layout and tails directed toward speakers. This is one computational design, not proof that one contour is universally natural. [Kurlander, Skelly & Salesin, “Comic Chat”](https://grail.cs.washington.edu/wp-content/uploads/2015/08/comics.pdf). Blambot documents conventional balloon use and the need to make reading order clear. [Blambot](https://blambot.com/pages/comic-book-grammar-tradition).

**InkLoop recommendation:** preserve `speaker_character_id`, panel link, stable bubble ID, text ID, reading order, and tail target. Use a known character anchor when available; if several characters are present and the speaker or target is not known, request a correction or leave the tail unresolved. Do not guess. Allow balloons to cross panel borders where page trim permits; do not apply artwork masks to text/bubble layers. Validate page-bound overflow, collisions, text fit, and tail crossings as warnings or errors with actionable locations.

### 6.3 Distinct contours without sacrificing legibility

Perfectly repeated balloons can feel mechanical; random irregularity can make lettering hard to read. A stable, subtle, ID-seeded contour variation is a deterministic UI/geometry strategy: it creates small differences without another model call, and keeps a bubble stable on reload. This is an InkLoop implementation recommendation supported by the broader computational practice of variable balloon geometry, not a research-established “hand-drawn” standard. [Comic Chat](https://grail.cs.washington.edu/wp-content/uploads/2015/08/comics.pdf).

### 6.4 Arabic, English, and mixed text

Arabic and mixed-direction dialogue require a real bidirectional text engine. Unicode Standard Annex #9 specifies positioning for text containing right-to-left scripts such as Arabic and Hebrew. Direction is paragraph/context sensitive; setting a CSS `direction` value alone does not prove correct shaping, punctuation, line breaking, or glyph support. [Unicode Standard Annex #9, Unicode Bidirectional Algorithm](https://www.unicode.org/reports/tr9/).

**Verification checklist:** test Arabic-only, English-only, mixed Arabic/Latin, numbers, brackets, punctuation, multiline dialogue, and RTL reading order using the actual renderer and installed/licensed fonts. Check glyph shaping, line wrap, alignment, text measurement, and overflow at final display scale. Record the tested browser/platform and fonts. Do not claim Arabic typography is supported from a screenshot alone.

## 7. Emotion, expression, movement, and human feeling

### 7.1 Emotion is multimodal

Human feeling can be communicated through face, gaze, posture, gesture, distance, timing, color, framing, dialogue, balloon treatment, movement, and the surrounding environment. A qualitative study of digital comic creation describes multimodal expression of attitude through linguistic and visual resources; it supports considering more than facial expression alone. [Mills et al. 2020](https://journals.sagepub.com/doi/10.1177/0741088319897978).

**Creator workflow:** define the emotion’s cause, what the character is trying to hide or express, and what changes in the body. Then choose two or three visible cues. A small smile with averted gaze and tense shoulders may convey something more specific than “happy face.” Keep subtext optional: do not invent a trauma or hidden motive not present in the source.

### 7.2 Expressions belong to characters

Expression design should remain recognizable across a character’s range. VIZ recommends character design and expression/body-language exploration before page production; Clip Studio’s character guide likewise ties expression to character personality. [VIZ Media](https://www.viz.com/blog/posts/manga-creation-101); [Clip Studio, Character Art Beginner’s Guide](https://www.clipstudio.net/en/characterart/beginners-guide/).

**Useful acting dimensions:** eye focus; brow tension; mouth and jaw; head tilt; torso openness; shoulder height; hand tension; weight balance; interpersonal distance; stillness versus motion. These are art-direction prompts, not an automatic emotion detector. The actual character design may be a human, creature, object-like being, abstract form, or a face as simple as a circle with a smile; the system should model declared form and identity anchors rather than assume human anatomy.

### 7.3 Dynamic action and emotional rhythm

Variation in body position and scene information can mark changes in a visual narrative; panel content and layout jointly guide attention. [Cohn et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4076615/); [“Running through the Who, Where, and When”](https://www.tandfonline.com/doi/full/10.1080/0163853X.2022.2106402). To avoid a page of repeated static poses, vary action, scale, viewpoint, silhouette, gaze, and pause according to the story—without forcing every panel to be an action shot.

### 7.4 Still-image speaking pose versus lip-sync

A single comic panel can show a speaking mouth pose, an open/closed mouth variation, breath, a shouted expression, or a reaction at a chosen instant. That is expressive still-image acting, not lip-sync. Audio lip-sync is an animation workflow: mouth/viseme shapes are mapped across a timeline against audio. Adobe Animate documents keyframes generated against audio visemes for an animated symbol. [Adobe Animate Help, “Using symbol instances, frame picker, auto Lip sync”](https://helpx.adobe.com/animate/desktop/multimedia-and-video/symbol-instances.html).

The current InkLoop registered tool inventory includes text shaping/generation and speech-bubble placement, but no audio ingestion, viseme analysis, mouth-rig timeline, or lip-sync execution tool. Therefore the report and skills must not claim true audio-driven lip-sync exists. If requested in the future, it needs an explicit audio/animation capability, timing and speaker contracts, editable mouth-shape tracks, and audio-aligned tests.

## 8. Practical production checklists

### Before planning panels

- Identify the source story, scene goal, obstacle, turn, outcome, and intended tone.
- Preserve exact authored dialogue and speaker IDs; distinguish narration, dialogue, thought, and SFX.
- Resolve the requested format, reading direction, page/scroll mode, and any explicit panel count.
- Plan varied beats and shot choices; do not force equal panels or fixed counts.
- Reserve readable space for text and reveal timing before image generation.

### Before generating a panel

- Check stable character IDs/versions, selected style/version, location/prop refs, and source provenance.
- List included cast and excluded cast; selection is not permission to place every chosen character in every panel.
- Specify action, pose, expression, camera, spatial relationships, and style traits that matter here.
- Reuse only compatible assets; attach source references actually needed for this panel.
- Keep generated artwork separate from geometry and editable text.

### Before placing lettering

- Confirm exact text, language, speaker, panel, delivery, and reading order.
- Choose balloon/caption treatment to fit voice and genre; keep the text editable.
- Aim the tail using a known anchor; surface unknowns rather than infer speakers.
- Keep all lettering inside page trim, but allow crossing panel edges; check overlaps and text fit.
- Verify fonts, Arabic shaping, mixed-direction text, and final-size readability.

### Before calling a page complete

- Read it in sequence at intended final size and direction.
- Check shot variety, clear action, legible focal hierarchy, visual continuity, and meaningful pauses.
- Inspect panel order, geometry, art links, text records, bubble IDs/tails, and stable versions.
- Report failed panels or unverified properties accurately; retain successful work and recover from checkpoints.

## 9. InkLoop product recommendations

1. **Typed story beat contract:** represent event, panel function, action, shot, transition, emotional intent, cast IDs/versions, style/location refs, exact text blocks, and page/scroll group. Mark authored wording separately from model-suggested wording.
2. **Flexible format profiles:** manga print, LTR print comic, RTL/LTR webtoon scroll, graphic novel, and picture-book spread should be editable starting points—not locked templates.
3. **Separate semantics from rendering:** story text, speaker, bubble body, tail, typography run, panel mask, image transform, art asset, and effects remain independent, stable, and revisioned.
4. **Honest image controls:** send actual referenced bytes/IDs to the provider; preserve provenance and selected profile versions. Show provider errors and usage only when returned. Never promise exact identity/style reproduction.
5. **Narrative-aware composition checks:** detect repeated shots, missing speakers, cropped text, collisions, ambiguous reading order, and ungrounded cast. Offer scoped fixes and explanations; avoid automatically rewriting the whole page.
6. **Skills are operating guidance, not tools:** workflow markdown may teach selection/order and constraints, but only current registered callable schemas and adapters execute work. Unsupported features remain explicit gaps.

## 10. Research method and source register

### Search log

Searches below were issued to the live web search tool on 30 October 2026. Direct links were opened and their title/content inspected where the source allowed it. Some scholarly publisher sites blocked direct retrieval (403/anti-bot) and one PDF returned a transient 502; for those entries, metadata and the stated abstract-level finding were cross-checked against live indexed search records, and the access limitation is recorded here. The claim scope is kept at the level visible in that record; inaccessible full text is not represented as fully reviewed.

| Query issued | Use |
|---|---|
| `site:webtoons.com/en/creators101 vertical scroll webtoon panel pacing gutters tutorial` | Official creator learning resources and scroll-format references. |
| `comics graphic novel storytelling panel sequence pacing gutters academic visual narrative character emotion research` | Scholarly work on layout, visual sequence, and reader inference. |
| `picture book storytelling page turns visual narrative pacing composition illustrator official guide` | Picturebook page-turn and image/text practice. |
| `site:webtoons.com/en/creators101 webtoon vertical scroll episode panels pacing canvas creators academy` | WEBTOON creator academy source. |
| `Korean webtoon vertical scroll storytelling panel spacing cliffhanger academic study manhwa` | Korean scholarship on vertical expansion and scroll direction. |
| `comic lettering fonts speech balloon text readability comics font official tutorial` | Comic lettering and font guidance. |
| `site:docs.midjourney.com image prompt character reference style reference documentation` | Provider-specific reference controls. |
| `Meta AI image generation API image model muse-image-1.0 prompt documentation` | Configured Muse Image API reference inputs and workflow. |
| `Adobe Animate lip sync visemes chart official help dialogue animation` | Distinguish still illustration from audio-driven animation. |
| `10.1080/13614568.2024.2374291 authors Moving with the story` | Verify article authors and bibliographic metadata using the institutional open-access record. |
| `"Going with the comics flow" authors DOI 10.1080/21504857.2025.2593920` | Verify author list and publication metadata against the university research portal. |
| `"Children’s Book Illustrations: Visual Language of Picture Books" 2014 authors` | Verify author and DOI metadata for the picturebook study. |

Earlier project research already present in [`manga-panel-types.md`](manga-panel-types.md) was retained as a complementary source inventory; it is not represented as a new search in this report.

### Source register

1. **VIZ Media**, “Manga Creation 101,” 9 October 2024. Publisher craft guidance on outline, character design, thumbnails, pacing, dialogue, and balloon placement. [Source](https://www.viz.com/blog/posts/manga-creation-101).
2. **Clip Studio Paint**, “How to Make a Comic: Step-by-step comic creation.” Official product/tutorial guide for comic planning, panel composition, lettering, effects, and export. [Source](https://www.clipstudio.net/en/comics-manga/comic-creation/).
3. **Steve Ellis / Clip Studio Art Rocket**, “Pro Artist’s Guide to Comic & Manga Layouts, Paneling, Flow.” Artist guidance on panel ideas, gutters, pacing, and flow. [Source](https://www.clipstudio.net/how-to-draw/archives/160963).
4. **Clip Studio Paint**, “Effective Storytelling and Design Tips for Comics, Manga, Webtoons.” Creator guidance covering panel layouts, backgrounds, typography, dialogue, and sound effects. [Source](https://www.clipstudio.net/en/comics-manga/design-tips/).
5. **Clip Studio Paint**, “Effects and Tones.” Product/tool reference for action lines and screentone/halftone use. [Source](https://www.clipstudio.net/en/comics-manga/tool/effects-tones.html).
6. **Clip Studio Paint**, “Tools & Techniques.” Comic production tool reference. [Source](https://www.clipstudio.net/en/comics-manga/tools-techniques/).
7. **Clip Studio Paint**, “Character Art: Beginner’s Guide.” Creator guidance on developing character features and expression. [Source](https://www.clipstudio.net/en/characterart/beginners-guide/).
8. **WEBTOON**, “WEBTOON Academy.” Official creator tutorials and resources. This source establishes available training resources, not a universal aesthetic standard. [Source](https://www.webtoons.com/en/creators101/webtoon-academy).
9. **Kim Sunyoung**, “An Analysis of Continuous Vertical Expansion in Webtoon Scroll Panels,” *Manhwa Webtoon Research*, 6(1), 2026, pp. 53–77, DOI 10.23254/coweko.2026.6.1.003. Focused analysis of four vertical expansion strategies. Live search record confirmed title, abstract, venue, and DOI; direct KCI page retrieval was unavailable during this check. [Source](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereSearchBean.artiId=ART003332306).
10. **Berube, Priego, Wisdom, Cooke & Makri**, “Moving with the Story: The Haptics of Reader Experience and Response to Digital Comics,” *New Review of Hypermedia and Multimedia*, 30(1–2), 2024, pp. 94–113, DOI 10.1080/13614568.2024.2374291. Reader research about interaction and digital-comic experience. The DOI page returned 403 in this check; authors and metadata were verified in the City St George’s open repository, which links the paper. [Source](https://openaccess.city.ac.uk/id/eprint/33449/).
11. **Cohn**, “Visual Narrative Structure,” *Cognitive Science*, 2013. Scholarly account of sequential visual narrative structures. [Source](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12016).
12. **Cohn et al.**, “The Architecture of Visual Narrative Comprehension,” *Frontiers in Psychology*, 2014. Research on interactions between narrative structure and page layout. PMC presented a browser check during this run; citation metadata and abstract were checked in indexed records. [Source](https://pmc.ncbi.nlm.nih.gov/articles/PMC4076615/).
13. **Laubrock & Dunst**, “Computational Approaches to Comics Analysis,” *Topics in Cognitive Science*, 2020. Review of computational comics-analysis work and visual narrative structure. [Source](https://onlinelibrary.wiley.com/doi/10.1111/tops.12476).
14. **Iyyer et al.**, “The Amazing Mysteries of the Gutter: Drawing Inferences Between Panels in Comic Book Narratives,” 2016. Research task on comics and inter-panel inference. [Source](https://arxiv.org/abs/1611.05118).
15. **Foulsham & Cohn**, “On the Interaction Between Layout and Narrative in the Processing of Comic Strips,” *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 2026. Eye-tracking/self-paced reading study; access to abstract/record confirmed through PubMed. [Source](https://pubmed.ncbi.nlm.nih.gov/42691285/).
16. **Cohn, van der Vegt, Atilla & Cardoso**, “Going with the Comics Flow: A Theoretical and Empirical Basis for Flow in Comics,” *Journal of Graphic Novels and Comics*, published 16 December 2025, DOI 10.1080/21504857.2025.2593920. Empirical analysis of panel-content direction and layout flow. DOI resolver returned an access error in this check; author list and abstract were verified from the Tilburg University research record. [Source](https://research.tilburguniversity.edu/en/publications/going-with-the-comics-flow-a-theoretical-and-empirical-basis-for-/).
17. **Cohn et al.**, “Running through the Who, Where, and When: A Cross-cultural Analysis of Situational Changes in Comics,” 2022. Scholarly work on situational changes and visual narrative event segmentation. Publisher site returned 403; bibliographic details and abstract were verified from the indexed result. [Source](https://www.tandfonline.com/doi/full/10.1080/0163853X.2022.2106402).
18. **Mills, Stone, Unsworth & Friend**, “Multimodal Language of Attitude in Digital Composition,” *Written Communication*, first published 6 January 2020. Qualitative research on multimodal expression in digital comic making. [Source](https://journals.sagepub.com/doi/10.1177/0741088319897978).
19. **Kurlander, Skelly & Salesin**, “Comic Chat,” SIGGRAPH 1996. Technical paper describing automated comics presentation, gestures, expressions, layout, and balloon construction. It documents a system, not a universal aesthetic prescription. [Source](https://grail.cs.washington.edu/wp-content/uploads/2015/08/comics.pdf).
20. **Blambot**, “Comic Book Grammar & Tradition.” Professional letterer’s synthesis of conventions and personal practice, with explicit acknowledgement that views vary. [Source](https://blambot.com/pages/comic-book-grammar-tradition).
21. **World Bank**, *Read@Home: Writers’ and Illustrators’ Guide*. Professional guide describing picturebook layout, characterization, color, text placement, and image/text relationship. [Source](https://thedocs.worldbank.org/en/doc/3c02f6956bbc8428ba6b9cf8909438f9-0140012022/related/Read-Home-Writers-and-Illustrators-Guide-World-Bank.pdf).
22. **Hana Hladíková**, “Children’s Book Illustrations: Visual Language of Picture Books,” *CRIS—Bulletin of the Centre for Research and Interdisciplinary Study*, 2014(1), pp. 19–31, DOI 10.2478/cris-2014-0002. Scholarly discussion of picturebook narrative flow, pacing, page layout, and image/text interaction. The PDF host returned 502 in this check; author, DOI, and abstract-level summary were verified in live indexed records. [Source metadata and abstract](https://econpapers.repec.org/article/vrsbucris/v_3a2014_3ay_3a2014_3ai_3a1_3ap_3a13_3an_3a2.htm); [DOI](https://doi.org/10.2478/cris-2014-0002).
23. **Unicode Consortium**, “Unicode Standard Annex #9: Unicode Bidirectional Algorithm,” Version 18.0, 1 September 2026. Normative standard for bidirectional text. [Source](https://www.unicode.org/reports/tr9/).
24. **Meta Model API**, “Image Generation with Muse Image.” Current provider documentation on text/image inputs, generation, editing, and iterative refinement. [Source](https://dev.meta.ai/docs/image-generation).
25. **Midjourney**, “Style Reference.” Provider-specific documentation for style-reference images; do not transplant its syntax or guarantees to other APIs. [Source](https://docs.midjourney.com/hc/en-us/articles/32180011136653-Style-Reference).
26. **Adobe**, “Using symbol instances, frame picker, auto Lip sync in Animate.” Product documentation for audio-viseme-driven animation timelines. [Source](https://helpx.adobe.com/animate/desktop/multimedia-and-video/symbol-instances.html).

## 11. Limits and cautions

- Several craft sources are tutorials or practitioner opinion, not controlled experiments. The guide labels them accordingly.
- Research on comics is not equally available for all languages, genres, print and digital platforms, age groups, or visual traditions. The Korean vertical-panel paper is especially narrow in scope.
- “Manga,” “comics,” and “manhwa” are diverse traditions. Do not reduce them to monochrome, left/right reading, or a single vertical template.
- Image-generation prompts and reference controls are provider-specific. A documented reference-input feature does not prove exact style or identity fidelity.
- The research supports informed design and testable reader-facing checks; it cannot guarantee a page is emotionally effective or that a character will be perfectly consistent.
