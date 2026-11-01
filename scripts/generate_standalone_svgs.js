import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const targetDirs = [
  path.resolve(__dirname, '../frontend/public/agent'),
  path.resolve(__dirname, '../assets/agent'),
];

for (const dir of targetDirs) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// Pure Black & White Palette definitions
const PALETTE = {
  bgCard: '#09090B',
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
};

const getDefs = (uid) => `
  <defs>
    <radialGradient id="${uid}-body-grad" cx="44%" cy="32%" r="65%" fx="38%" fy="25%">
      <stop offset="0%" stop-color="${PALETTE.suitLight}" />
      <stop offset="52%" stop-color="${PALETTE.suitMid}" />
      <stop offset="86%" stop-color="${PALETTE.suitShadow}" />
      <stop offset="100%" stop-color="${PALETTE.suitDeepShadow}" />
    </radialGradient>
    <linearGradient id="${uid}-limb-left" x1="15%" y1="10%" x2="85%" y2="90%">
      <stop offset="0%" stop-color="${PALETTE.suitLight}" />
      <stop offset="55%" stop-color="${PALETTE.suitMid}" />
      <stop offset="100%" stop-color="${PALETTE.suitShadow}" />
    </linearGradient>
    <linearGradient id="${uid}-limb-right" x1="85%" y1="10%" x2="15%" y2="90%">
      <stop offset="0%" stop-color="${PALETTE.suitLight}" />
      <stop offset="55%" stop-color="${PALETTE.suitMid}" />
      <stop offset="100%" stop-color="${PALETTE.suitShadow}" />
    </linearGradient>
    <linearGradient id="${uid}-leg-grad" x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stop-color="${PALETTE.suitDeepShadow}" />
      <stop offset="22%" stop-color="${PALETTE.suitShadow}" />
      <stop offset="68%" stop-color="${PALETTE.suitMid}" />
      <stop offset="100%" stop-color="${PALETTE.suitShadow}" />
    </linearGradient>
    <linearGradient id="${uid}-hood-rim" x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stop-color="${PALETTE.hoodInnerShadow}" />
      <stop offset="35%" stop-color="${PALETTE.suitShadow}" />
      <stop offset="100%" stop-color="${PALETTE.suitLight}" />
    </linearGradient>
    <radialGradient id="${uid}-face-grad" cx="50%" cy="38%" r="60%" fx="46%" fy="30%">
      <stop offset="0%" stop-color="${PALETTE.faceLight}" />
      <stop offset="70%" stop-color="${PALETTE.faceMid}" />
      <stop offset="100%" stop-color="${PALETTE.faceShadow}" />
    </radialGradient>
    <radialGradient id="${uid}-cheek-grad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${PALETTE.cheekGlow}" stop-opacity="0.65" />
      <stop offset="60%" stop-color="${PALETTE.cheekGlow}" stop-opacity="0.25" />
      <stop offset="100%" stop-color="${PALETTE.cheekGlow}" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="${uid}-belly-sheen" cx="50%" cy="42%" r="48%">
      <stop offset="0%" stop-color="${PALETTE.suitRim}" stop-opacity="0.55" />
      <stop offset="100%" stop-color="${PALETTE.suitRim}" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="${uid}-ground-shadow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${PALETTE.suitDeepShadow}" stop-opacity="0.45" />
      <stop offset="65%" stop-color="${PALETTE.suitDeepShadow}" stop-opacity="0.18" />
      <stop offset="100%" stop-color="${PALETTE.suitDeepShadow}" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="${uid}-prop-grad" x1="20%" y1="15%" x2="85%" y2="90%">
      <stop offset="0%" stop-color="${PALETTE.faceLight}" />
      <stop offset="60%" stop-color="${PALETTE.suitMid}" />
      <stop offset="100%" stop-color="${PALETTE.suitDeepShadow}" />
    </linearGradient>
  </defs>
`;

const furOverlay = `
  <g stroke="${PALETTE.furStroke}" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.75">
    <path d="M 134 38 L 131 33 M 140 36 L 140 31 M 147 38 L 150 33" />
    <path d="M 83 78 L 78 76 M 80 86 L 75 86 M 77 110 L 72 109 M 74 120 L 69 121" />
    <path d="M 197 78 L 202 76 M 200 86 L 205 86 M 203 110 L 208 109 M 206 120 L 211 121" />
    <path d="M 73 196 L 68 198 M 75 206 L 70 209" />
    <path d="M 207 196 L 212 198 M 205 206 L 210 209" />
    <path d="M 118 150 Q 120 155 117 159" opacity="0.5" />
    <path d="M 138 153 Q 140 159 138 163" opacity="0.5" />
    <path d="M 160 150 Q 162 155 159 159" opacity="0.5" />
    <path d="M 106 176 Q 108 182 105 186" opacity="0.45" />
    <path d="M 130 182 Q 132 188 129 192" opacity="0.4" />
    <path d="M 152 182 Q 154 188 151 192" opacity="0.4" />
    <path d="M 174 176 Q 176 182 173 186" opacity="0.45" />
    <path d="M 118 208 Q 120 214 117 218" opacity="0.4" />
    <path d="M 162 208 Q 164 214 161 218" opacity="0.4" />
    <path d="M 126 135 L 124 140 M 140 137 L 140 142 M 154 135 L 156 140" opacity="0.65" />
  </g>
`;

const pearTorso = (uid) => `
  <path
    d="M 140 37
       C 178 37, 198 58, 201 94
       C 203 118, 211 148, 211 182
       C 211 217, 192 238, 140 238
       C 88 238, 69 217, 69 182
       C 69 148, 77 118, 79 94
       C 82 58, 102 37, 140 37 Z"
    fill="url(#${uid}-body-grad)"
    stroke="${PALETTE.strokeColor}"
    stroke-width="1.8"
    stroke-linejoin="round"
  />
  <ellipse cx="140" cy="178" rx="48" ry="42" fill="url(#${uid}-belly-sheen)" />
  <path
    d="M 94 222 Q 140 237 186 222"
    fill="none"
    stroke="${PALETTE.suitDeepShadow}"
    stroke-width="2.2"
    stroke-linecap="round"
    opacity="0.45"
  />
`;

const standingLegs = (uid, pigeonToed = false, rightLegLifted = false) => `
  <g ${pigeonToed ? 'transform="rotate(-5 112 240)"' : ''}>
    <path
      d="M 90 218 C 90 234, 91 250, 93 259 C 95 266, 104 268, 115 268 C 126 268, 134 265, 135 258 C 136 248, 136 232, 136 224 Z"
      fill="url(#${uid}-leg-grad)"
      stroke="${PALETTE.strokeColor}"
      stroke-width="1.8"
      stroke-linejoin="round"
    />
    <path d="M 96 252 Q 114 256 131 251" fill="none" stroke="${PALETTE.suitDeepShadow}" stroke-width="1.5" stroke-linecap="round" opacity="0.65" />
  </g>
  <g ${rightLegLifted ? 'transform="translate(4, -10) rotate(-14 165 232)"' : pigeonToed ? 'transform="rotate(5 168 240)"' : ''}>
    <path
      d="M 144 224 C 144 232, 144 248, 145 258 C 146 265, 154 268, 165 268 C 176 268, 185 266, 187 259 C 189 250, 190 234, 190 218 Z"
      fill="url(#${uid}-leg-grad)"
      stroke="${PALETTE.strokeColor}"
      stroke-width="1.8"
      stroke-linejoin="round"
    />
    <path d="M 149 251 Q 166 256 184 252" fill="none" stroke="${PALETTE.suitDeepShadow}" stroke-width="1.5" stroke-linecap="round" opacity="0.65" />
  </g>
`;

const faceWindow = (uid, eye = 'normal', mouth = 'smile') => {
  let eyesMarkup = `
    <circle cx="116" cy="95" r="6.2" fill="${PALETTE.eyeFill}" />
    <circle cx="114.2" cy="93" r="2.1" fill="${PALETTE.eyeHighlight}" />
    <circle cx="117.8" cy="97.2" r="0.95" fill="${PALETTE.eyeHighlight}" opacity="0.85" />
    <circle cx="164" cy="95" r="6.2" fill="${PALETTE.eyeFill}" />
    <circle cx="162.2" cy="93" r="2.1" fill="${PALETTE.eyeHighlight}" />
    <circle cx="165.8" cy="97.2" r="0.95" fill="${PALETTE.eyeHighlight}" opacity="0.85" />
  `;
  if (eye === 'happy') {
    eyesMarkup = `
      <g stroke="${PALETTE.eyeFill}" stroke-width="2.7" stroke-linecap="round" fill="none">
        <path d="M 109 96 Q 116 88 123 96" />
        <path d="M 157 96 Q 164 88 171 96" />
      </g>
    `;
  } else if (eye === 'sleep') {
    eyesMarkup = `
      <g stroke="${PALETTE.eyeFill}" stroke-width="2.5" stroke-linecap="round" fill="none">
        <path d="M 109 95 Q 116 101 123 95" />
        <path d="M 157 95 Q 164 101 171 95" />
      </g>
    `;
  } else if (eye === 'look-up') {
    eyesMarkup = `
      <g transform="translate(2, -3.5)">
        <circle cx="116" cy="95" r="6.2" fill="${PALETTE.eyeFill}" />
        <circle cx="117.5" cy="92.5" r="2.2" fill="${PALETTE.eyeHighlight}" />
        <circle cx="164" cy="95" r="6.2" fill="${PALETTE.eyeFill}" />
        <circle cx="165.5" cy="92.5" r="2.2" fill="${PALETTE.eyeHighlight}" />
      </g>
    `;
  }

  let mouthMarkup = `<path d="M 133.5 101.5 Q 140 107.2 146.5 101.5" fill="none" stroke="${PALETTE.eyeFill}" stroke-width="2.3" stroke-linecap="round" />`;
  if (mouth === 'open-happy') {
    mouthMarkup = `
      <path d="M 132.5 100.5 Q 140 102 147.5 100.5 C 147.5 108.5, 132.5 108.5, 132.5 100.5 Z" fill="${PALETTE.eyeFill}" />
      <path d="M 136 105.2 Q 140 103.2 144 105.2 C 142.5 107.2, 137.5 107.2, 136 105.2 Z" fill="${PALETTE.cheekGlow}" />
    `;
  } else if (mouth === 'o-curious') {
    mouthMarkup = `<ellipse cx="140" cy="103" rx="3.2" ry="3.8" fill="${PALETTE.eyeFill}" />`;
  }

  return `
    <rect x="90" y="57" width="100" height="78" rx="38" ry="36" fill="url(#${uid}-hood-rim)" stroke="${PALETTE.strokeColor}" stroke-width="1.44" />
    <rect x="93.5" y="60.5" width="93" height="71" rx="35" ry="33" fill="url(#${uid}-face-grad)" />
    <path d="M 98 76 C 108 61, 172 61, 182 76 C 172 66, 108 66, 98 76 Z" fill="${PALETTE.hoodInnerShadow}" opacity="0.38" />
    <ellipse cx="109" cy="106" rx="12" ry="8.5" fill="url(#${uid}-cheek-grad)" />
    <ellipse cx="171" cy="106" rx="12" ry="8.5" fill="url(#${uid}-cheek-grad)" />
    ${eyesMarkup}
    ${mouthMarkup}
  `;
};

// Generates Pose 01: Classic Neutral Stand
const getPoseNeutral = () => {
  const uid = 'svg-pose-neutral';
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 300">
  ${getDefs(uid)}
  <ellipse cx="140" cy="269" rx="68" ry="11" fill="url(#${uid}-ground-shadow)" />
  ${standingLegs(uid)}
  <path d="M 80 120 C 58 134, 46 168, 46 198 C 46 213, 55 220, 64 218 C 72 216, 75 206, 75 192 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  <path d="M 200 120 C 222 134, 234 168, 234 198 C 234 213, 225 220, 216 218 C 208 216, 205 206, 205 192 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  ${pearTorso(uid)}
  ${faceWindow(uid, 'normal', 'smile')}
  ${furOverlay}
</svg>`;
};

// Generates Pose 02: Cheerful Hello Wave
const getPoseWave = () => {
  const uid = 'svg-pose-wave';
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 300">
  ${getDefs(uid)}
  <ellipse cx="140" cy="269" rx="66" ry="11" fill="url(#${uid}-ground-shadow)" />
  ${standingLegs(uid)}
  <path d="M 79 122 C 56 138, 45 172, 47 200 C 48 214, 58 219, 66 216 C 74 212, 76 198, 76 184 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  <g transform="rotate(-3 140 200)">
    <path d="M 196 132 C 218 118, 238 88, 234 64 C 231 50, 217 48, 210 58 C 203 68, 198 92, 186 112 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <path d="M 243 53 Q 252 63 246 76 M 250 48 Q 261 62 254 79" fill="none" stroke="${PALETTE.strokeColor}" stroke-width="1.6" opacity="0.65" stroke-linecap="round" />
    ${pearTorso(uid)}
    ${faceWindow(uid, 'normal', 'open-happy')}
    ${furOverlay}
  </g>
</svg>`;
};

// Generates Animated Wave Loop
const getAnimWave = () => {
  const uid = 'svg-anim-wave';
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 300">
  ${getDefs(uid)}
  <style>
    @keyframes ${uid}-wave-arm {
      0%, 100% { transform: rotate(-6deg); }
      50% { transform: rotate(22deg); }
    }
    @keyframes ${uid}-wave-body {
      0%, 100% { transform: rotate(-1.5deg) translateY(0px); }
      50% { transform: rotate(2deg) translateY(-3px); }
    }
  </style>
  <ellipse cx="140" cy="269" rx="68" ry="11" fill="url(#${uid}-ground-shadow)" />
  ${standingLegs(uid)}
  <g style="transform-origin: 140px 230px; animation: ${uid}-wave-body 1.1s ease-in-out infinite;">
    <path d="M 79 122 C 56 138, 45 172, 47 200 C 48 214, 58 219, 66 216 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <g style="transform-origin: 192px 124px; animation: ${uid}-wave-arm 0.55s ease-in-out infinite;">
      <path d="M 196 132 C 218 118, 238 88, 234 64 C 231 50, 217 48, 210 58 C 203 68, 198 92, 186 112 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    </g>
    ${pearTorso(uid)}
    ${faceWindow(uid, 'normal', 'open-happy')}
    ${furOverlay}
  </g>
</svg>`;
};

// Generates Animated Waddle Walk
const getAnimWaddle = () => {
  const uid = 'svg-anim-waddle';
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 300">
  ${getDefs(uid)}
  <style>
    @keyframes ${uid}-waddle-torso {
      0%, 100% { transform: translateY(0px) rotate(-3.5deg); }
      25% { transform: translateY(-5px) rotate(0deg); }
      50% { transform: translateY(0px) rotate(3.5deg); }
      75% { transform: translateY(-5px) rotate(0deg); }
    }
    @keyframes ${uid}-step-l {
      0%, 100% { transform: translateY(-10px) rotate(-8deg); }
      50% { transform: translateY(2px) rotate(5deg); }
    }
    @keyframes ${uid}-step-r {
      0%, 100% { transform: translateY(2px) rotate(-5deg); }
      50% { transform: translateY(-10px) rotate(8deg); }
    }
  </style>
  <ellipse cx="140" cy="269" rx="68" ry="11" fill="url(#${uid}-ground-shadow)" />
  <g style="transform-origin: 112px 225px; animation: ${uid}-step-l 0.95s ease-in-out infinite;">
    <path d="M 90 218 C 90 234, 91 250, 93 259 C 95 266, 104 268, 115 268 C 126 268, 134 265, 135 258 C 136 248, 136 232, 136 224 Z" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  </g>
  <g style="transform-origin: 168px 225px; animation: ${uid}-step-r 0.95s ease-in-out infinite;">
    <path d="M 144 224 C 144 232, 144 248, 145 258 C 146 265, 154 268, 165 268 C 176 268, 185 266, 187 259 C 189 250, 190 234, 190 218 Z" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  </g>
  <g style="transform-origin: 140px 210px; animation: ${uid}-waddle-torso 0.95s ease-in-out infinite;">
    <g style="transform-origin: 80px 128px; animation: ${uid}-step-r 0.95s ease-in-out infinite;">
      <path d="M 80 120 C 58 134, 46 168, 46 198 C 46 213, 55 220, 64 218 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    </g>
    <g style="transform-origin: 200px 128px; animation: ${uid}-step-l 0.95s ease-in-out infinite;">
      <path d="M 200 120 C 222 134, 234 168, 234 198 C 234 213, 225 220, 216 218 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    </g>
    ${pearTorso(uid)}
    ${faceWindow(uid, 'normal', 'smile')}
    ${furOverlay}
  </g>
</svg>`;
};

// Generates Animated Zen Float
const getAnimZen = () => {
  const uid = 'svg-anim-zen';
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 300">
  ${getDefs(uid)}
  <style>
    @keyframes ${uid}-zen-hover {
      0%, 100% { transform: translateY(4px); }
      50% { transform: translateY(-18px); }
    }
    @keyframes ${uid}-zen-ring {
      0% { transform: scale(0.5); opacity: 0.8; }
      100% { transform: scale(1.35); opacity: 0; }
    }
  </style>
  <ellipse cx="140" cy="266" rx="62" ry="11" fill="none" stroke="${PALETTE.strokeColor}" stroke-width="1.5" style="transform-origin: 140px 266px; animation: ${uid}-zen-ring 2.8s linear infinite;" />
  <ellipse cx="140" cy="266" rx="52" ry="9" fill="url(#${uid}-ground-shadow)" />
  <g style="transform-origin: 140px 150px; animation: ${uid}-zen-hover 2.8s ease-in-out infinite;">
    ${pearTorso(uid)}
    <ellipse cx="112" cy="232" rx="28" ry="14" transform="rotate(8 112 232)" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <ellipse cx="168" cy="232" rx="28" ry="14" transform="rotate(-8 168 232)" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <path d="M 78 130 C 60 152, 74 186, 122 186 C 132 186, 132 172, 122 170 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <path d="M 202 130 C 220 152, 206 186, 158 186 C 148 186, 148 172, 158 170 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    ${faceWindow(uid, 'sleep', 'smile')}
    ${furOverlay}
  </g>
</svg>`;
};

// Generates Logo Mark Emblem (Compact)
const getLogoEmblem = () => {
  const uid = 'svg-logo-emblem';
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
  <defs>
    <radialGradient id="${uid}-rim" cx="50%" cy="30%" r="70%">
      <stop offset="0%" stop-color="#FFFFFF" />
      <stop offset="70%" stop-color="#E4E4E7" />
      <stop offset="100%" stop-color="#71717A" />
    </radialGradient>
    <radialGradient id="${uid}-face" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#FFFFFF" />
      <stop offset="80%" stop-color="#F4F4F6" />
      <stop offset="100%" stop-color="#D4D4D8" />
    </radialGradient>
  </defs>
  <rect x="10" y="10" width="100" height="100" rx="36" fill="url(#${uid}-rim)" stroke="#09090B" stroke-width="2.5" />
  <rect x="15" y="15" width="90" height="90" rx="30" fill="url(#${uid}-face)" stroke="#09090B" stroke-width="1.5" />
  <ellipse cx="38" cy="74" rx="9" ry="6" fill="#A1A1AA" opacity="0.4" />
  <ellipse cx="82" cy="74" rx="9" ry="6" fill="#A1A1AA" opacity="0.4" />
  <circle cx="44" cy="62" r="6" fill="#09090B" />
  <circle cx="42" cy="60" r="2.2" fill="#FFFFFF" />
  <circle cx="76" cy="62" r="6" fill="#09090B" />
  <circle cx="74" cy="60" r="2.2" fill="#FFFFFF" />
  <path d="M 54 72 Q 60 77 66 72" fill="none" stroke="#09090B" stroke-width="2.4" stroke-linecap="round" />
</svg>`;
};

const filesToWrite = [
  { name: 'pose-01-neutral.svg', content: getPoseNeutral() },
  { name: 'pose-02-wave.svg', content: getPoseWave() },
  { name: 'anim-02-wave-loop.svg', content: getAnimWave() },
  { name: 'anim-04-waddle-walk.svg', content: getAnimWaddle() },
  { name: 'anim-06-zen-float.svg', content: getAnimZen() },
  { name: 'logo-emblem.svg', content: getLogoEmblem() },
];

for (const dir of targetDirs) {
  for (const item of filesToWrite) {
    const dest = path.join(dir, item.name);
    fs.writeFileSync(dest, item.content, 'utf-8');
    console.log(`Generated: ${dest}`);
  }
}

console.log('SVG generation complete.');
