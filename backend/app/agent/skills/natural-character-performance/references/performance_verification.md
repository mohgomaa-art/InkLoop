# Character Performance Quality Assessment Protocol

A successful API response code (200 OK) is not proof of character performance quality. Every generated artwork panel must be evaluated against this rigorous 8-dimension rubric.

---

## 1. The 4-State Verdict Contract

Every performance inspection returns one of four definitive states:

| Verdict | Definition | Action Required |
| :--- | :--- | :--- |
| **`PASS`** | All 8 dimensions satisfy quality criteria; eyes aligned, performance emotionally authentic, identity preserved. | Accept panel into Canvas page assembly. |
| **`NEEDS_REVIEW`** | Minor defect (e.g. slight gaze angle discrepancy or marginal hand position) that does not break the panel's reading clarity. | Disclose diagnostic in job checkpoints; creator can proceed or request targeted retouching. |
| **`FAIL`** | Severe defect (e.g. crossed eyes, divergent pupils, blank zombie stare, wrong identity, anatomically distorted face). | Reject candidate. Execute targeted prompt correction with explicit negative bounds. |
| **`NOT_RUN`** | Inspection was omitted or verifier model was offline. | Report property as unverified. Never claim an uninspected image passed verification. |

---

## 2. The 8 Evaluation Dimensions

1. **Canonical Likeness**: Does the subject retain the facial features, skin tone, hair texture, and permanent marks established in the canonical reference asset?
2. **Eye Alignment (Vergence)**: Do both visible pupils share the same optical focal axis without strabismus (crossed eyes) or exotropia (wall eyes)?
3. **Gaze Coherence**: Does the sightline point unambiguously toward the intended scene object, partner, or horizon, rather than staring blankly at the reader?
4. **Emotional Restraint & Authenticity**: Does the expression convey nuanced, scene-appropriate emotion through eyelid and brow tension rather than generic grimacing or vacuous smiling?
5. **Facial Anatomy Integrity**: Are eyes, nose, lips, ears, and jaw anatomically sound and free of double-pupils, melted features, or AI distortion?
6. **Posture-Face Congruence**: Does the character's spine, shoulder tension, head angle, and hand placement reinforce the facial emotional state?
7. **Narrative Relevance**: Does the performance communicate the specific beat function (e.g., discovery, fear, concentration, relief) planned for this panel?
8. **Style Consistency**: Is the rendering linework, crosshatching, and shading congruent with the project's selected style profile?

---

## 3. Targeted Remediation Workflow

When a panel returns `FAIL` or `NEEDS_REVIEW`:
1. **Identify the Exact Discrepancy**: Formulate a localized diagnostic (e.g. "Gomaa's right eye is divergent; looking toward the camera while his left eye looks at the lantern").
2. **Apply Targeted Prompt Invariant**:
   - Add negative constraint: `"avoid mismatched pupil directions or camera stare"`.
   - Reinforce gaze anchor: `"both eyes locked in tight convergence on the tip of the wire held in his right hand"`.
3. **Preserve Surrounding Context**: Do not change the scene environment, lighting, or style profile when adjusting character eye-lines.
