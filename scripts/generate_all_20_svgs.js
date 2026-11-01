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
  } else if (eye === 'wide') {
    eyesMarkup = `
      <circle cx="116" cy="95" r="7.2" fill="${PALETTE.eyeFill}" />
      <circle cx="113.8" cy="92.4" r="2.6" fill="${PALETTE.eyeHighlight}" />
      <circle cx="164" cy="95" r="7.2" fill="${PALETTE.eyeFill}" />
      <circle cx="161.8" cy="92.4" r="2.6" fill="${PALETTE.eyeHighlight}" />
    `;
  } else if (eye === 'starry') {
    eyesMarkup = `
      <circle cx="116" cy="95" r="6.8" fill="${PALETTE.eyeFill}" />
      <path d="M 115 90.5 L 116 93.2 L 118.7 94.2 L 116 95.2 L 115 97.9 L 114 95.2 L 111.3 94.2 L 114 93.2 Z" fill="${PALETTE.eyeHighlight}" />
      <circle cx="164" cy="95" r="6.8" fill="${PALETTE.eyeFill}" />
      <path d="M 163 90.5 L 164 93.2 L 166.7 94.2 L 164 95.2 L 163 97.9 L 162 95.2 L 159.3 94.2 L 162 93.2 Z" fill="${PALETTE.eyeHighlight}" />
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
  } else if (mouth === 'smirk') {
    mouthMarkup = `<path d="M 133 102.5 Q 141 107 147.5 99.5" fill="none" stroke="${PALETTE.eyeFill}" stroke-width="2.3" stroke-linecap="round" />`;
  } else if (mouth === 'shy-wavy') {
    mouthMarkup = `<path d="M 133 102.5 Q 136.5 105.5 140 102.5 Q 143.5 105.5 147 102.5" fill="none" stroke="${PALETTE.eyeFill}" stroke-width="2.1" stroke-linecap="round" />`;
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

// 10 Static Poses generators
const staticGenerators = {
  'pose-01-neutral.svg': (uid) => `
    ${standingLegs(uid)}
    <path d="M 80 120 C 58 134, 46 168, 46 198 C 46 213, 55 220, 64 218 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <path d="M 200 120 C 222 134, 234 168, 234 198 C 234 213, 225 220, 216 218 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    ${pearTorso(uid)}
    ${faceWindow(uid, 'normal', 'smile')}
    ${furOverlay}
  `,
  'pose-02-wave.svg': (uid) => `
    ${standingLegs(uid)}
    <path d="M 79 122 C 56 138, 45 172, 47 200 C 48 214, 58 219, 66 216 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <g transform="rotate(-3 140 200)">
      <path d="M 196 132 C 218 118, 238 88, 234 64 C 231 50, 217 48, 210 58 C 203 68, 198 92, 186 112 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <path d="M 243 53 Q 252 63 246 76 M 250 48 Q 261 62 254 79" fill="none" stroke="${PALETTE.strokeColor}" stroke-width="1.6" opacity="0.65" stroke-linecap="round" />
      ${pearTorso(uid)}
      ${faceWindow(uid, 'normal', 'open-happy')}
      ${furOverlay}
    </g>
  `,
  'pose-03-sitting.svg': (uid) => `
    <g transform="translate(0, 14)">
      <path d="M 140 42 C 178 42, 198 62, 201 98 C 204 126, 218 164, 218 202 C 218 234, 194 248, 140 248 C 86 248, 62 234, 62 202 C 62 164, 76 126, 79 98 C 82 62, 102 42, 140 42 Z" fill="url(#${uid}-body-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <ellipse cx="140" cy="184" rx="52" ry="40" fill="url(#${uid}-belly-sheen)" />
      <path d="M 76 128 C 58 148, 58 184, 80 202 C 92 210, 102 203, 98 191 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <path d="M 204 128 C 222 148, 222 184, 200 202 C 188 210, 178 203, 182 191 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <ellipse cx="96" cy="234" rx="24" ry="19" transform="rotate(-10 96 234)" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <ellipse cx="184" cy="234" rx="24" ry="19" transform="rotate(10 184 234)" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <g transform="translate(0, 4)">
        ${faceWindow(uid, 'normal', 'smile')}
        ${furOverlay}
      </g>
    </g>
  `,
  'pose-04-thinking.svg': (uid) => `
    ${standingLegs(uid)}
    <g transform="rotate(3.5 140 190)">
      ${pearTorso(uid)}
      ${faceWindow(uid, 'look-up', 'o-curious')}
      ${furOverlay}
      <path d="M 76 132 C 62 156, 74 182, 118 180 C 130 179, 132 166, 120 163 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <path d="M 202 132 C 214 156, 192 172, 162 140 C 153 130, 143 134, 148 145 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <circle cx="154" cy="137" r="12" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    </g>
    <circle cx="208" cy="52" r="4" fill="${PALETTE.faceLight}" stroke="${PALETTE.strokeColor}" stroke-width="1.6" />
    <circle cx="220" cy="40" r="6.5" fill="${PALETTE.faceLight}" stroke="${PALETTE.strokeColor}" stroke-width="1.6" />
  `,
  'pose-05-star-jump.svg': (uid) => `
    <g transform="translate(0, -18)">
      <g transform="rotate(18 108 222)">
        <path d="M 92 216 C 92 232, 93 248, 95 256 C 97 263, 129 263, 132 255 Z" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      </g>
      <g transform="rotate(-18 172 222)">
        <path d="M 146 218 C 146 230, 146 246, 148 255 C 151 263, 183 263, 185 256 Z" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      </g>
      <path d="M 84 128 C 60 112, 42 84, 48 62 C 51 49, 65 49, 71 60 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <path d="M 196 128 C 220 112, 238 84, 232 62 C 229 49, 215 49, 209 60 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      ${pearTorso(uid)}
      ${faceWindow(uid, 'happy', 'open-happy')}
      ${furOverlay}
      <path d="M 42 36 L 45 43 L 52 46 L 45 49 L 42 56 L 39 49 L 32 46 L 39 43 Z" fill="${PALETTE.faceLight}" stroke="${PALETTE.strokeColor}" stroke-width="1.3" />
      <path d="M 238 36 L 241 43 L 248 46 L 241 49 L 238 56 L 235 49 L 228 46 L 235 43 Z" fill="${PALETTE.faceLight}" stroke="${PALETTE.strokeColor}" stroke-width="1.3" />
    </g>
  `,
  'pose-06-shy.svg': (uid) => `
    ${standingLegs(uid, true)}
    ${pearTorso(uid)}
    ${faceWindow(uid, 'wide', 'shy-wavy')}
    ${furOverlay}
    <circle cx="98" cy="118" r="12.5" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <circle cx="182" cy="118" r="12.5" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  `,
  'pose-07-sleeping.svg': (uid) => `
    <g transform="translate(0, 12)">
      <rect x="48" y="206" width="184" height="46" rx="23" fill="url(#${uid}-prop-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      ${pearTorso(uid)}
      <g transform="translate(0, 10) rotate(3 140 100)">
        ${faceWindow(uid, 'sleep', 'smile')}
      </g>
      ${furOverlay}
      <path d="M 196 48 L 208 48 L 196 60 L 208 60 M 214 30 L 229 30 L 214 45 L 229 45" fill="none" stroke="${PALETTE.strokeColor}" stroke-width="2" stroke-linecap="round" />
    </g>
  `,
  'pose-08-confident.svg': (uid) => `
    ${standingLegs(uid)}
    <path d="M 80 124 C 46 142, 42 168, 74 188 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <path d="M 200 124 C 234 142, 238 168, 206 188 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    ${pearTorso(uid)}
    <circle cx="78" cy="183" r="11.5" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <circle cx="202" cy="183" r="11.5" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    ${faceWindow(uid, 'normal', 'smirk')}
    ${furOverlay}
  `,
  'pose-09-warm-mug.svg': (uid) => `
    ${standingLegs(uid)}
    ${pearTorso(uid)}
    ${faceWindow(uid, 'happy', 'smile')}
    ${furOverlay}
    <g transform="translate(140, 174)">
      <path d="M -22 -16 L 22 -16 L 19 16 C 18 24, -18 24, -19 16 Z" fill="url(#${uid}-prop-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <ellipse cx="0" cy="-16" rx="22" ry="5.5" fill="${PALETTE.faceLight}" stroke="${PALETTE.strokeColor}" stroke-width="1.6" />
      <path d="M -7 -24 Q -12 -32 -5 -39 M 7 -22 Q 12 -30 6 -37" fill="none" stroke="${PALETTE.strokeColor}" stroke-width="1.6" stroke-linecap="round" opacity="0.6" />
    </g>
  `,
  'pose-10-heart-gift.svg': (uid) => `
    ${standingLegs(uid, false, true)}
    ${pearTorso(uid)}
    ${faceWindow(uid, 'starry', 'smile')}
    ${furOverlay}
    <path d="M 140 194 C 140 194, 110 174, 110 155 C 110 143, 122 136, 132 142 C 137 145, 140 150, 140 150 C 140 150, 143 145, 148 142 C 158 136, 170 143, 170 155 C 170 174, 140 194, 140 194 Z" fill="url(#${uid}-prop-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  `,
};

// 10 Animations generators
const animGenerators = {
  'anim-01-breathing.svg': (uid) => `
    <style>
      @keyframes ${uid}-breathe { 0%, 100% { transform: translateY(0px) scale(1, 1); } 50% { transform: translateY(-3.5px) scale(1.02, 0.98); } }
      @keyframes ${uid}-blink { 0%, 45%, 49%, 100% { transform: scaleY(1); } 47% { transform: scaleY(0.08); } }
    </style>
    ${standingLegs(uid)}
    <g style="transform-origin: 140px 235px; animation: ${uid}-breathe 3.2s ease-in-out infinite;">
      <path d="M 80 120 C 58 134, 46 168, 46 198 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <path d="M 200 120 C 222 134, 234 168, 234 198 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      ${pearTorso(uid)}
      <g style="transform-origin: 140px 95px; animation: ${uid}-blink 3.8s ease-in-out infinite;">
        ${faceWindow(uid, 'normal', 'smile')}
      </g>
      ${furOverlay}
    </g>
  `,
  'anim-02-wave-loop.svg': (uid) => `
    <style>
      @keyframes ${uid}-wave-arm { 0%, 100% { transform: rotate(-6deg); } 50% { transform: rotate(22deg); } }
      @keyframes ${uid}-wave-body { 0%, 100% { transform: rotate(-1.5deg); } 50% { transform: rotate(2deg); } }
    </style>
    ${standingLegs(uid)}
    <g style="transform-origin: 140px 230px; animation: ${uid}-wave-body 1.1s ease-in-out infinite;">
      <path d="M 79 122 C 56 138, 45 172, 47 200 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <g style="transform-origin: 192px 124px; animation: ${uid}-wave-arm 0.55s ease-in-out infinite;">
        <path d="M 196 132 C 218 118, 238 88, 234 64 C 231 50, 217 48, 210 58 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      </g>
      ${pearTorso(uid)}
      ${faceWindow(uid, 'normal', 'open-happy')}
      ${furOverlay}
    </g>
  `,
  'anim-03-happy-hop.svg': (uid) => `
    <style>
      @keyframes ${uid}-hop { 0%, 100% { transform: translateY(0); } 48% { transform: translateY(-28px); } }
      48% { transform: scale(0.65); opacity: 0.5; } }
    </style>
    <g style="transform-origin: 140px 265px; animation: ${uid}-hop 1.25s ease-in-out infinite;">
      ${standingLegs(uid)}
      ${pearTorso(uid)}
      ${faceWindow(uid, 'happy', 'open-happy')}
      ${furOverlay}
    </g>
  `,
  'anim-04-waddle-walk.svg': (uid) => `
    <style>
      @keyframes ${uid}-waddle { 0%, 100% { transform: rotate(-3.5deg); } 50% { transform: rotate(3.5deg); } }
    </style>
    ${standingLegs(uid)}
    <g style="transform-origin: 140px 210px; animation: ${uid}-waddle 0.95s ease-in-out infinite;">
      <path d="M 80 120 C 58 134, 46 168, 46 198 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <path d="M 200 120 C 222 134, 234 168, 234 198 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      ${pearTorso(uid)}
      ${faceWindow(uid, 'normal', 'smile')}
      ${furOverlay}
    </g>
  `,
  'anim-05-fluff-shiver.svg': (uid) => `
    <style>
      @keyframes ${uid}-shiver { 0%, 100% { transform: translate(0, 0); } 20% { transform: translate(-3px, -1px); } 40% { transform: translate(3px, 0); } 60% { transform: translate(-2px, 1px); } }
    </style>
    <g style="transform-origin: 140px 240px; animation: ${uid}-shiver 1.8s ease-in-out infinite;">
      ${standingLegs(uid, true)}
      ${pearTorso(uid)}
      ${faceWindow(uid, 'wide', 'shy-wavy')}
      ${furOverlay}
    </g>
  `,
  'anim-06-zen-float.svg': (uid) => `
    <style>
      @keyframes ${uid}-float { 0%, 100% { transform: translateY(4px); } 50% { transform: translateY(-16px); } }
    </style>
    <g style="transform-origin: 140px 150px; animation: ${uid}-float 2.8s ease-in-out infinite;">
      ${pearTorso(uid)}
      <ellipse cx="112" cy="232" rx="28" ry="14" transform="rotate(8 112 232)" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <ellipse cx="168" cy="232" rx="28" ry="14" transform="rotate(-8 168 232)" fill="url(#${uid}-leg-grad)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      ${faceWindow(uid, 'sleep', 'smile')}
      ${furOverlay}
    </g>
  `,
  'anim-07-cheek-squish.svg': (uid) => `
    <style>
      @keyframes ${uid}-squish { 0%, 100% { transform: scale(1, 1); } 50% { transform: scale(0.9, 1.05); } }
    </style>
    ${standingLegs(uid)}
    <g style="transform-origin: 140px 220px;">
      ${pearTorso(uid)}
      <g style="transform-origin: 140px 96px; animation: ${uid}-squish 1.6s ease-in-out infinite;">
        ${faceWindow(uid, 'happy', 'shy-wavy')}
      </g>
      <circle cx="92" cy="114" r="13" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <circle cx="188" cy="114" r="13" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      ${furOverlay}
    </g>
  `,
  'anim-08-peekaboo.svg': (uid) => `
    <style>
      @keyframes ${uid}-peek { 0%, 10%, 90%, 100% { transform: translateY(55px); } 30%, 70% { transform: translateY(0); } }
    </style>
    <clipPath id="${uid}-clip"><rect x="0" y="0" width="280" height="225" /></clipPath>
    <g clip-path="url(#${uid}-clip)">
      <g style="animation: ${uid}-peek 3.4s ease-in-out infinite;">
        ${pearTorso(uid)}
        ${faceWindow(uid, 'wide', 'o-curious')}
        ${furOverlay}
      </g>
    </g>
    <line x1="28" y1="225" x2="252" y2="225" stroke="${PALETTE.strokeColor}" stroke-width="3" stroke-linecap="round" />
    <ellipse cx="84" cy="225" rx="16" ry="11" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
    <ellipse cx="196" cy="225" rx="16" ry="11" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
  `,
  'anim-09-sleepy-nod.svg': (uid) => `
    <style>
      @keyframes ${uid}-nod { 0%, 88%, 100% { transform: translateY(0); } 40% { transform: translateY(10px) rotate(5deg); } }
    </style>
    ${standingLegs(uid)}
    ${pearTorso(uid)}
    <g style="transform-origin: 140px 135px; animation: ${uid}-nod 3.6s ease-in-out infinite;">
      ${faceWindow(uid, 'sleep', 'smile')}
    </g>
    ${furOverlay}
  `,
  'anim-10-boogie-dance.svg': (uid) => `
    <style>
      @keyframes ${uid}-boogie { 0%, 100% { transform: translateX(-5px) rotate(-4deg); } 50% { transform: translateX(5px) rotate(4deg); } }
    </style>
    ${standingLegs(uid)}
    <g style="transform-origin: 140px 225px; animation: ${uid}-boogie 1.1s ease-in-out infinite;">
      <path d="M 84 128 C 60 112, 42 84, 48 62 Z" fill="url(#${uid}-limb-left)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      <path d="M 196 128 C 220 112, 238 84, 232 62 Z" fill="url(#${uid}-limb-right)" stroke="${PALETTE.strokeColor}" stroke-width="1.8" />
      ${pearTorso(uid)}
      ${faceWindow(uid, 'starry', 'open-happy')}
      ${furOverlay}
    </g>
  `,
};

// Write out all files
let count = 0;
for (const [filename, gen] of Object.entries(staticGenerators)) {
  const uid = `raw-static-${filename.replace('.svg', '')}`;
  const content = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 300">\n${getDefs(uid)}\n${gen(uid)}\n</svg>`;
  for (const dir of targetDirs) {
    fs.writeFileSync(path.join(dir, filename), content, 'utf-8');
  }
  count++;
}

for (const [filename, gen] of Object.entries(animGenerators)) {
  const uid = `raw-anim-${filename.replace('.svg', '')}`;
  const content = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 300">\n${getDefs(uid)}\n${gen(uid)}\n</svg>`;
  for (const dir of targetDirs) {
    fs.writeFileSync(path.join(dir, filename), content, 'utf-8');
  }
  count++;
}

console.log(`Successfully generated all ${count} standalone black and white SVGs in frontend/public/agent and assets/agent.`);
