# Eye Alignment, Gaze Direction & Ocular Mechanics

Eye direction is the single most critical factor in character performance. When gaze is misdirected, disconnected, or cross-eyed, the viewer instantly perceives the character as lifeless or broken.

---

## 1. The Anatomy of Gaze & Optical Vergence

1. **Shared Optical Axis**:
   - Both human eyes move in tandem (conjugate gaze). The lines of sight from both pupils must converge at a single target point in 3D scene space.
   - For a target at 0.5 meters (holding an object), the eyes converge slightly inward (~3–5 degrees each).
   - For a target at 3+ meters (a character across the room), the optical axes are virtually parallel.
2. **Preventing AI Ocular Defects in Prompting**:
   - **Crossed Eyes (Strabismus)**: Caused by over-emphasizing close-up focus without specifying the exact object location. Solution: anchor gaze explicitly to a physical entity ("both eyes looking down-right toward the lantern nozzle").
   - **Divergent Pupils (Exotropia / Wall-Eyed)**: Caused by diffuse ambient lighting and vague facial descriptions. Solution: explicit prompt directive: "both pupils perfectly aligned and converging on the target; sharp, focused ocular alignment".
   - **Wandering / Unfocused Gaze**: Caused by generic "looking around" prompt text. Solution: replace vague statements with concrete focus ("gaze locked onto the spark at the tip of the tweezers").

---

## 2. Gaze Target Categories & Visual Vectors

| Gaze Target Type | Head & Eye Alignment | Practical Prompt Direction |
| :--- | :--- | :--- |
| **Object in Hands** | Head tilted down 15–30°; eyes cast downward toward hands. | "Head tilted forward looking down at the map on the table; both eyes focused sharply on the paper center." |
| **Scene Partner** | Head turned toward partner; eyes meet partner's eye level. | "Turned three-quarters left making direct, focused eye contact with the companion standing to his left." |
| **Ambient / Environment** | Head aligned with body or scanning horizon; eyes level. | "Looking out past the roof edge toward the distant illuminated city skyline; eyes focused on the far horizon." |
| **Internal Contemplation** | Head slightly tilted or lowered; eyes averted from camera. | "Eyes cast slightly downward-left in deep thought, not making contact with viewer; reflective, pensive gaze." |
| **Direct Address (4th Wall)** | Head frontal or slight tilt; eyes directly on camera lens. | "Direct, intense eye contact with the viewer; pupils centered and locked on camera axis." |

---

## 3. Ocular Directives for Non-Human Entities

For non-human, stylized, or creature companions:
- If canonical anatomy features simple dark bead eyes (e.g. Muse):
  - Do NOT describe white sclera, irises, or human eyelids.
  - Express gaze through head tilt, body turn, and eye highlight position: "Head cocked 20 degrees to the right; black bead eyes oriented directly toward Gomaa's hands."
- If canonical anatomy is robotic/mechanical:
  - Express focus through optical sensor aperture, lens glow, or directional visor orientation.
- If masked or featureless:
  - Express gaze through the visor orientation and head pitch.
