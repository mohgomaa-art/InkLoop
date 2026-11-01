import { MonochromePalette, MonochromeThemeId, CharacterAssetMeta } from './types';

export const BW_PALETTES: Record<MonochromeThemeId, MonochromePalette> = {
  'ink-light': {
    id: 'ink-light',
    name: 'Fine Ink & Chalk',
    subtitle: 'High-contrast black linework & crisp achromatic studio shading',
    bgCard: '#FFFFFF',
    suitLight: '#FFFFFF',
    suitMid: '#F4F4F6',
    suitShadow: '#D4D4D8',
    suitDeepShadow: '#71717A',
    suitRim: '#FFFFFF',
    faceLight: '#FFFFFF',
    faceMid: '#F8F8FA',
    faceShadow: '#E4E4E7',
    hoodInnerShadow: '#52525B',
    eyeFill: '#09090B',
    eyeHighlight: '#FFFFFF',
    cheekGlow: '#A1A1AA',
    strokeColor: '#09090B',
    furStroke: '#52525B',
    groundShadow: 'rgba(9, 9, 11, 0.18)',
    accentTone: '#18181B',
  },
  'ink-dark': {
    id: 'ink-dark',
    name: 'Obsidian Velvet',
    subtitle: 'Dark-mode carbon plush with pure silver highlights & rim light',
    bgCard: '#09090B',
    suitLight: '#52525B',
    suitMid: '#3F3F46',
    suitShadow: '#27272A',
    suitDeepShadow: '#121215',
    suitRim: '#D4D4D8',
    faceLight: '#FAFAFA',
    faceMid: '#E4E4E7',
    faceShadow: '#A1A1AA',
    hoodInnerShadow: '#09090B',
    eyeFill: '#09090B',
    eyeHighlight: '#FFFFFF',
    cheekGlow: '#71717A',
    strokeColor: '#D4D4D8',
    furStroke: '#71717A',
    groundShadow: 'rgba(0, 0, 0, 0.65)',
    accentTone: '#F4F4F5',
  },
  'pure-contrast': {
    id: 'pure-contrast',
    name: 'Pure Two-Tone Vector',
    subtitle: 'Minimalist stark silhouette for ultra-crisp micro marks',
    bgCard: '#FFFFFF',
    suitLight: '#FFFFFF',
    suitMid: '#FFFFFF',
    suitShadow: '#E4E4E7',
    suitDeepShadow: '#000000',
    suitRim: '#FFFFFF',
    faceLight: '#FFFFFF',
    faceMid: '#FFFFFF',
    faceShadow: '#E4E4E7',
    hoodInnerShadow: '#000000',
    eyeFill: '#000000',
    eyeHighlight: '#FFFFFF',
    cheekGlow: '#A1A1AA',
    strokeColor: '#000000',
    furStroke: '#000000',
    groundShadow: 'rgba(0, 0, 0, 0.25)',
    accentTone: '#000000',
  },
};

export const STATIC_POSES_META: CharacterAssetMeta[] = [
  {
    id: 'pose-neutral',
    index: 1,
    title: 'Classic Balanced Stand',
    category: 'static',
    badge: 'Pose 01',
    description: 'Faithful monochrome pear-shaped plush silhouette, recessed hood window, and gentle calm smile.',
    technicalNotes: 'Symmetric baseline with dual-stop radial plush shading and recessed face aperture.'
  },
  {
    id: 'pose-wave',
    index: 2,
    title: 'Cheerful Hello Wave',
    category: 'static',
    badge: 'Pose 02',
    description: 'Right fuzzy mitten raised high in greeting with subtle head tilt and joyful open smile.',
    technicalNotes: 'Asymmetric shoulder articulation, tilted hood aperture, and dynamic weight shift.'
  },
  {
    id: 'pose-sitting',
    index: 3,
    title: 'Cozy Seated Rest',
    category: 'static',
    badge: 'Pose 03',
    description: 'Seated comfortably on the floor with chubby legs extended forward showing soft oval paw pads.',
    technicalNotes: 'Foreshortened lower limbs, widened lower belly contour, and resting lap arms.'
  },
  {
    id: 'pose-thinking',
    index: 4,
    title: 'Curious Ponder',
    category: 'static',
    badge: 'Pose 04',
    description: 'One paw resting thoughtfully under the chin gazing upward with inquisitive idea spark.',
    technicalNotes: 'Upward pupil offset, inquisitive "o" mouth geometry, and overlapping forearm shadow.'
  },
  {
    id: 'pose-star-jump',
    index: 5,
    title: 'Joyful Star Leap',
    category: 'static',
    badge: 'Pose 05',
    description: 'Captured mid-air in an exuberant star jump with happy crescent eyes and monochrome sparkles.',
    technicalNotes: 'Elevated Y-axis body group, outstretched limbs, and arched happy eye paths.'
  },
  {
    id: 'pose-shy',
    index: 6,
    title: 'Bashful Cheek Touch',
    category: 'static',
    badge: 'Pose 06',
    description: 'Both fluffy paws gently pressing against rosy monochrome cheeks with inward-turned toes.',
    technicalNotes: 'Dual inward arm vectors, enlarged twin specular eye highlights, and wavy shy smile.'
  },
  {
    id: 'pose-sleeping',
    index: 7,
    title: 'Serene Slumber',
    category: 'static',
    badge: 'Pose 07',
    description: 'Peacefully snoozing on cushion with relaxed eyelids, drooped head, and floating monochrome Zzz.',
    technicalNotes: 'Downward shifted face mask, curved sleeping eyelid arcs, and layered Zzz glyphs.'
  },
  {
    id: 'pose-confident',
    index: 8,
    title: 'Proud Akimbo Stance',
    category: 'static',
    badge: 'Pose 08',
    description: 'Paws planted confidently on plush hips with puffed chest, resolute expression, and heroic presence.',
    technicalNotes: 'Bent elbow silhouette cutouts, broadened chest gradient, and smirk mouth path.'
  },
  {
    id: 'pose-warm-mug',
    index: 9,
    title: 'Warm Cocoa Hug',
    category: 'static',
    badge: 'Pose 09',
    description: 'Cradling a steaming monochrome ceramic cup with both mittens and contentedly closed happy eyes.',
    technicalNotes: 'Foreground prop layering with rising bezier steam trails and soft ambient occlusion.'
  },
  {
    id: 'pose-heart-gift',
    index: 10,
    title: 'Plush Heart Offering',
    category: 'static',
    badge: 'Pose 10',
    description: 'Presenting a dimensional monochrome heart between both paws with one foot playfully kicked up.',
    technicalNotes: '3D shaded monochrome heart emblem, starry eye highlights, and single-leg balance.'
  },
];

export const ANIMATED_POSES_META: CharacterAssetMeta[] = [
  {
    id: 'anim-breathing',
    index: 1,
    title: 'Living Plush Idle & Blink',
    category: 'animated',
    badge: 'Anim 01',
    description: 'Organic diaphragm breathing expansion paired with natural double-blinks and subtle arm pendulum sway.',
    technicalNotes: 'Multi-phase scaleY/scaleX torso respiration + stepped eyelid clipping keyframe.'
  },
  {
    id: 'anim-wave-loop',
    index: 2,
    title: 'Enthusiastic Greeting Loop',
    category: 'animated',
    badge: 'Anim 02',
    description: 'Continuous energetic arm wave from the shoulder with synchronized head bobbing and joyful expression.',
    technicalNotes: 'Pivot-anchored arm rotation (transform-origin) synced with harmonic head tilt.'
  },
  {
    id: 'anim-happy-hop',
    index: 3,
    title: 'Squash & Stretch Bounce',
    category: 'animated',
    badge: 'Anim 03',
    description: 'Full classical animation bounce cycle with pre-jump anticipation squash, mid-air stretch, and plush landing.',
    technicalNotes: 'Synchronized body translation, volume-preserving squash/stretch, and reactive shadow scale.'
  },
  {
    id: 'anim-waddle-walk',
    index: 4,
    title: 'Jaunty Waddle Walk Cycle',
    category: 'animated',
    badge: 'Anim 04',
    description: 'Rhythmic alternating chubby leg steps, counter-balanced arm swings, and endearing side-to-side waddle.',
    technicalNotes: '180-degree phase-shifted limb cycles with lateral torso oscillation.'
  },
  {
    id: 'anim-fluff-shiver',
    index: 5,
    title: 'Cozy Fur Puff & Shiver',
    category: 'animated',
    badge: 'Anim 05',
    description: 'Playful high-frequency plush vibration that puffs out the furry silhouette before settling into a warm sigh.',
    technicalNotes: 'High-frequency horizontal jitter keyframes burst + expanding fur aura rings.'
  },
  {
    id: 'anim-zen-float',
    index: 6,
    title: 'Levitating Zen Meditation',
    category: 'animated',
    badge: 'Anim 06',
    description: 'Weightless sinusoidal hover in lotus posture with expanding monochrome ripple rings and orbiting motes.',
    technicalNotes: 'Continuous sine-wave vertical float with staggered opacity ring emitters.'
  },
  {
    id: 'anim-cheek-squish',
    index: 7,
    title: 'Happy Cheek Squish & Giggle',
    category: 'animated',
    badge: 'Anim 07',
    description: 'Both paws press inward to squish the soft face window while the shoulders bounce in a rapid giggle.',
    technicalNotes: 'Elastic horizontal compression on face aperture synced with inward paw translation.'
  },
  {
    id: 'anim-peekaboo',
    index: 8,
    title: 'Curious Peek-a-Boo',
    category: 'animated',
    badge: 'Anim 08',
    description: 'Ducks low, pops up curiously to scan left and right with wide blinking eyes, beams a smile, and repeats.',
    technicalNotes: 'Multi-stage vertical translation with horizontal pupil/face tracking keyframes.'
  },
  {
    id: 'anim-sleepy-nod',
    index: 9,
    title: 'Sleepy Nod-Off & Startle',
    category: 'animated',
    badge: 'Anim 09',
    description: 'Eyelids droop heavy as the plush head nods down in stages with floating Zs, then startles wide awake.',
    technicalNotes: 'Asymmetric easing curve for gradual head droop followed by snappy wake recovery.'
  },
  {
    id: 'anim-boogie-dance',
    index: 10,
    title: 'Plush Groove Boogie',
    category: 'animated',
    badge: 'Anim 10',
    description: 'Upbeat side-to-side hip groove, alternating pumping mittens, tapping feet, and pulsing monochrome stars.',
    technicalNotes: 'Coordinated multi-part dance choreography with rhythmic sparkle scale pulses.'
  },
];
