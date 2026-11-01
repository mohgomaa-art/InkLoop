---
name: natural-character-performance
description: Believable, emotionally authentic, focused character acting during image generation, eliminating crossed eyes, vacant stares, and stiff expressions.
triggers:
  - character performance
  - eye gaze
  - eye alignment
  - facial expression
  - character acting
  - body language
  - character emotion
  - character pose
  - believable characters
  - prevent crossed eyes
  - natural performance
non_triggers:
  - bubble lettering placement
  - story plot outlining
  - canvas page layout geometry
---

# Natural Character Performance

**Tools this workflow may use:** `generation.generate_image`, `canon.inspect_characters`, `canon.inspect_reference_anchor`, `generation.check_readiness`, `image.verify_visual_consistency`.

## Mission

Eliminate artificial stiffness, crossed/misaligned eyes, vacant stares, and unmotivated emotional exaggeration during character image generation. Ensure every generated character acts with psychological intention, focused ocular alignment, and posture-face congruence grounded in canonical references.

---

## 1. Eliminate the Primary Image Quality Defects

The performance engine specifically targets and eradicates the following common AI image failures:

| Quality Failure | Root Cause in AI Models | Natural Performance Mandate |
| :--- | :--- | :--- |
| **Crossed or Misaligned Eyes** | Independent eye rendering without optical vergence constraints. | Specify unambiguous, unified gaze target coordinates and shared optical focal axis. |
| **Divergent Pupils (Wall-Eyed)** | Asymmetric pupil placement across disparate eye sockets. | Explicit instruction: both pupils converge accurately on the target object/character. |
| **Vacant / Dead Stares** | Lack of micro-eyelid tension or attentional focus. | Engage upper and lower eyelid tension (orbicularis oculi) matching active cognition. |
| **Unmotivated Camera Staring** | Model default to passport portrait framing. | Head and eyes must orient toward diegetic scene focal points unless breaking the 4th wall. |
| **Exaggerated Facial Grimacing** | Overfitting to extreme theatrical stock emotion tags. | Restrained, grounded emotion: subtle brow furrow, closed mouth with slight corner tension. |
| **Mismatched Posture & Face** | Decoupled face and body prompt tags. | Whole-body somatic congruence: slumped shoulders with sadness, forward lean with curiosity. |
| **Frozen Identical Expression** | Identity prompts over-constraining emotional range. | Separate stable anatomical invariants from mutable emotional performance. |

---

## 2. Grounding Every Generation in Canonical References

Never rely on text prompts alone to preserve identity. Text without reference anchoring causes identity drift and generic faces.

1. **Resolve Explicit Canonical IDs**: Retrieve canonical character profiles using `canon.inspect_characters`.
2. **Anchor to Real Image References**: Identify the verified reference asset ID and supply it as a `character_reference` in `ReferenceImagePayload`.
3. **Strict Reference Separation**:
   - `character_reference`: Informs facial identity, facial structure, skin tone, hair texture, and physical invariants ONLY.
   - `style_reference`: Informs rendering linework, crosshatching, color palette, and textures ONLY.
   - Never let a style reference replace a character's face or body.
4. **Non-Human Character Forms**:
   - For non-human beings (e.g. creature companions, robots, masked or headless entities), do not force human facial features or ocular anatomy.
   - Use their canonical visual language: posture, ear tilt, eye glow, tentacle stance, or body orientation.

*(See `references/meta_muse_prompting.md` for payload construction and multi-image reference ordering.)*

---

## 3. Optical Alignment & Gaze Mechanics

For characters with visible eyes, define optical direction as a physical vector:

1. **Head Orientation**: Specify head rotation (frontal, three-quarter view, profile, tilted up, lowered chin).
2. **Eye-Line Vector**:
   - Define exact gaze target (e.g. "looking down at the brass lantern on the table", "making direct eye contact with Muse on her right").
   - Define gaze quality: Direct, peripheral, lowered in thought, or distant horizon focus.
3. **Ocular Vergence & Pupil Alignment**:
   - Both eyes must converge toward the shared target point in 3D scene space.
   - For close-up objects, slight convergence is natural; for distant objects, eye axes are parallel.
   - Never allow one eye to look at the camera while the other looks at a scene partner.

*(See `references/eye_gaze_direction.md` for geometry rules, vergence vectors, and ocular prompt patterns.)*

---

## 4. Emotional Subtlety & Facial Action Mechanics

Believable acting is understated. In animation and film, powerful emotion is communicated through micro-tensions rather than screaming or wide-eyed shock.

1. **The Three Facial Zones (Ekman FACS Principles)**:
   - **Upper Face (Forehead & Eyebrows)**: Corrugator (furrow between brows in concentration/concern); frontalis (brow raise in curiosity); inner brow raise in sorrow.
   - **Middle Face (Eyelids & Eyes)**: Attentive eyelid tension (slight squint in sharp focus); relaxed lids in calm; widened lids ONLY in genuine brief alarm.
   - **Lower Face (Mouth & Jaw)**: Softly closed lips for quiet focus; pressed lips for stubborn resolve; slight unilateral corner smirk for wry amusement. Avoid default toothy grins.
2. **Subtle Asymmetry**: Natural faces are rarely mirror-symmetrical. A slight head tilt, one raised brow, or an asymmetrical smirk injects immediate human vitality.

*(See `references/facial_expression_mechanics.md` for Action Unit breakdowns across core comic emotional states.)*

---

## 5. Staging: Body Language Reinforces the Face

A character acts with their entire skeleton. The face is only the focal tip of a somatic performance.

1. **Disney Staging Principles**:
   - **Silhouette & Clarity**: The character's emotional stance should be readable in pure silhouette.
   - **Spine & Weight Distribution**: Forward weight transfer indicates engagement, aggression, or eagerness; backward weight transfer signals caution, disgust, or surprise.
   - **Shoulder & Neck Tension**: Dropped shoulders indicate relief or exhaustion; raised, bunched shoulders signal defensive stress or sudden chill.
   - **Hands & Interaction**: Hands must be doing something purposeful (holding tools, bracing against a surface, gesturing, curled in pockets), never dangling in generic T-pose or claw shapes.

*(See `references/body_language_staging.md` for posture congruence matrices and hand acting blueprints.)*

---

## 6. Visual Quality Assessment Protocol

After generation, assess the character performance using an explicit four-value verdict:

```text
VERDICT: PASS | NEEDS_REVIEW | FAIL | NOT_RUN
```

Evaluate across 8 dimensions:
1. **Canonical Likeness**: Matches the character reference asset features and invariants.
2. **Eye Alignment**: Both eyes align along the correct sightlines without strabismus or divergent pupils.
3. **Gaze Coherence**: Gaze connects unambiguously with the intended scene subject or object.
4. **Emotional Restraint**: Expression is appropriate to the story beat without unmotivated exaggeration.
5. **Facial Anatomy Integrity**: Features are clean, undistorted, and free of double-pupil or artifacting errors.
6. **Posture-Face Congruence**: Body language, shoulders, and head angle reinforce the facial emotion.
7. **Narrative Relevance**: The performance clearly communicates the planned beat's emotional intent.
8. **Style Preservation**: The rendering technique preserves the project's selected style profile.

*(See `references/performance_verification.md` for diagnostic scoring checklists and targeted correction protocols.)*
