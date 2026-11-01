# Quick Style Templates: Research and Variable Map

## Locked schema and scope

`master_schema.md` is the attached source schema copied without edits. The ten generated style files preserve its complete section-heading order and required prompt slots. Each file changes only the active visual-style blocks and the style-specific examples, checks, negative constraints, and troubleshooting entries. Medical clinic content and the v6 gouache appendix remain labeled as historical source material, not production defaults for other styles.

## Variable inventory

| Field | Owner | Pin behavior | Meaning |
|---|---|---|---|
| `medium` | Style profile | Pinned by default | The intended material or rendering medium. |
| `linework` | Style profile | Pinned by default | Presence, absence, weight, and behavior of contours. |
| `stroke_behavior` | Style profile | Pinned by default | Brush, pen, or digital mark-making. |
| `edge_quality` | Style profile | Pinned by default | Crisp, soft, broken, or selectively lost edges. |
| `shading` | Style profile | Pinned by default | Value grouping and shadow treatment. |
| `palette` | Style profile | Pinned by default | Color hierarchy and accent behavior. |
| `lighting` | Style profile | Pinned by default | Key, fill, shadow, and atmosphere rules. |
| `background_detail` | Style profile | Pinned by default | Environmental detail and focal separation. |
| `texture` | Style profile | Pinned by default | Surface grain, print treatment, or material texture. |
| `shape_language` | Style profile | Pinned by default | Shape simplification and silhouette conventions. |
| `screentones_and_fx` | Style profile | Pinned by default | Optional graphic effects; never assumed scene content. |
| `negative_constraints` | Style profile | Separate contract field | Style-specific exclusions; must not conflict with the selected style. |
| `SCENE`, `SUBJECTS`, `N`, `PROPS` | Request/context | Never inherited from a style | Scene facts, actual entity forms, exact count, and explicitly named objects. |
| `FRAME`, `ASPECT_RATIO` | Request/context | Never pinned by a style | Creator/editor-selected framing and output ratio. |

The Agent applies the profile's pinned variables to generation context. The preset's example prompt is only a preview test; it is not injected into normal creator requests.

## Research findings applied

1. **Separate what is depicted from how it is rendered.** Liu and Chilton evaluated thousands of generations and analyzed subject/style prompt structure and style-specific failure modes. The templates keep scene and subject slots separate from medium, linework, lighting, palette, and texture. [Design Guidelines for Prompt Engineering Text-to-Image Generative Models](https://arxiv.org/abs/2109.06977)
2. **Do not assume a style keyword guarantees a visual result.** A 2024 human-centered study found that iterations often did not meaningfully change styles and that negative terms were sometimes misused. The templates define observable rendering traits and require output-level review rather than relying on labels such as “anime” or “gothic.” [Prompting AI Art: An Investigation into the Creative Skill of Prompt Engineering](https://doi.org/10.1080/10447318.2024.2431761)
3. **Counts and relations deserve explicit tests.** GenAI-Bench reports persistent weaknesses on compositional prompts involving attributes and relationships. The schema therefore keeps exact subject count, named props, and scene/action in explicit slots. [Evaluating and Improving Compositional Text-to-Visual Generation](https://openaccess.thecvf.com/content/CVPR2024W/EvGenFM/html/Li_Evaluating_and_Improving_Compositional_Text-to-Visual_Generation_CVPRW_2024_paper.html)
4. **Preview and iteration reduce prompt guesswork.** PromptNavi studies interactive visual prompt exploration as a way to reduce cognitive load and help users refine image intent. InkLoop presents examples next to the one-click style action and records each generated preview's provenance. [PromptNavi](https://www.sciencedirect.com/science/article/pii/S0097849325002584)
5. **Reference controls are provider-specific and nondeterministic.** Meta's guide says model output can differ between runs and reference images can influence style, subject, pose, and layout. InkLoop labels examples as examples and does not claim that a style preview is a guarantee. [Meta image-generation guide](https://dev.meta.ai/docs/cookbook/image-generation-basics?project_id=29035399122726954&team_id=1741581793652561). Midjourney's `--sref` and weights are proprietary controls; InkLoop does not forward them to Meta. [Midjourney Style Reference documentation](https://docs.midjourney.com/hc/en-us/articles/32180011136653-Style-Reference)

## Preview brief and provenance

All ten previews use exactly this scene brief so the visual treatment is easier to compare:

> One fox-like creature with large pointed ears, a long bushy tail and round eyes, wearing a hooded cloak, standing on a cobblestone path and holding one lit lantern in a raised paw, in front of a stone archway with a tall window above it, three-quarter view, full body. One subject only.

Why this brief: the earlier one (a blank creature on a plain pale background) gave most style variables nothing to act on. It had no light source, material, depth, architecture, or mood, and its dot-eyes-and-smile face pulled every style toward the same cute blob. This one adds a light source (lantern), fabric (cloak), fur, ground contact, architecture, and depth. Previews made with the earlier brief or with template 1.0.0 are not comparable with 1.0.1.

Each successful example records the registered `asset_id`, model/provider name, sample prompt, and quick-style template version. The provider does not promise identical framing or deterministic results. Missing previews remain visibly unavailable; the UI must not replace them with fabricated artwork.

## Important provider limitation

The style `negative_constraints` live in a separate profile field. The configured Meta image request does not currently expose a dedicated negative-prompt parameter in InkLoop's adapter; the generation compiler therefore maps it to an “Avoid” clause in the prompt text. This is not a native negative channel. Vendor parameters may be added only when InkLoop's provider contract actually supports them.

## Compiler and template contract (template 1.0.1)

- Send the generator only the style block (opening line, STYLE CORE, the labeled variables), the request slots, the Avoid clause, and the closing anchor, in that order. Do not send the full schema file: about 70% of every style file is inherited gouache-era history.
- Strip all template placeholder hints before sending (for example `concrete nouns and verbs only`, `no style instructions`, `creator-selected`). If one reaches the provider it is read as picture content.
- The Avoid clause is a flat list of concrete visual nouns, placed before the closing anchor, never as the last words of the prompt. The adapter must not add meta-words such as `unrequested`.
- The locked style block contains no negations and no conditionals. Defaults are concrete; a creator-selected medium or palette replaces only the matching default.
- Acceptance gate for a preview: every Observable check in the style file passes, and the swap test (labels hidden) can tell the ten previews apart. A preview that fails either is recorded as failed, not shipped as the example.
