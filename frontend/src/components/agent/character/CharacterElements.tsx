import React from 'react';
import { MonochromePalette } from './types';

export const PlushFurOverlay: React.FC<{
  palette: MonochromePalette;
  strokeScale: number;
  visible: boolean;
}> = ({ palette, strokeScale, visible }) => {
  if (!visible) return null;
  const sw = 1.35 * strokeScale;
  return (
    <g
      stroke={palette.furStroke}
      strokeWidth={sw}
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
      opacity="0.75"
    >
      {/* Crown & Top Hood Fluffy Tufts */}
      <path d="M 134 38 L 131 33 M 140 36 L 140 31 M 147 38 L 150 33" />
      {/* Left Hood & Shoulder Fur Strokes */}
      <path d="M 83 78 L 78 76 M 80 86 L 75 86 M 77 110 L 72 109 M 74 120 L 69 121" />
      {/* Right Hood & Shoulder Fur Strokes */}
      <path d="M 197 78 L 202 76 M 200 86 L 205 86 M 203 110 L 208 109 M 206 120 L 211 121" />
      {/* Lower Hip Fluffy Edges */}
      <path d="M 73 196 L 68 198 M 75 206 L 70 209" />
      <path d="M 207 196 L 212 198 M 205 206 L 210 209" />
      {/* Combed Fleece Marks */}
      <path d="M 118 150 Q 120 155 117 159" opacity="0.5" />
      <path d="M 138 153 Q 140 159 138 163" opacity="0.5" />
      <path d="M 160 150 Q 162 155 159 159" opacity="0.5" />
      <path d="M 106 176 Q 108 182 105 186" opacity="0.45" />
      <path d="M 130 182 Q 132 188 129 192" opacity="0.4" />
      <path d="M 152 182 Q 154 188 151 192" opacity="0.4" />
      <path d="M 174 176 Q 176 182 173 186" opacity="0.45" />
      <path d="M 118 208 Q 120 214 117 218" opacity="0.4" />
      <path d="M 162 208 Q 164 214 161 218" opacity="0.4" />
      {/* Under-Chin Plush Seam */}
      <path d="M 126 135 L 124 140 M 140 137 L 140 142 M 154 135 L 156 140" opacity="0.65" />
    </g>
  );
};

export const FaceWindow: React.FC<{
  uid: string;
  palette: MonochromePalette;
  strokeScale: number;
  eyeMode?: 'normal' | 'happy' | 'sleep' | 'wink' | 'starry' | 'look-up' | 'wide';
  mouthMode?: 'smile' | 'open-happy' | 'o-curious' | 'shy-wavy' | 'sleep-tiny' | 'smirk';
  pupilOffset?: { x: number; y: number };
  squishX?: number;
}> = ({
  uid,
  palette,
  strokeScale,
  eyeMode = 'normal',
  mouthMode = 'smile',
  pupilOffset = { x: 0, y: 0 },
  squishX = 1,
}) => {
  const sw = 1.6 * strokeScale;

  return (
    <g transform={`translate(140, 96) scale(${squishX}, 1) translate(-140, -96)`}>
      {/* Outer Recessed Hood Fur Shadow Bevel */}
      <rect
        x="90"
        y="57"
        width="100"
        height="78"
        rx="38"
        ry="36"
        fill={`url(#${uid}-hood-rim)`}
        stroke={palette.strokeColor}
        strokeWidth={sw * 0.9}
      />

      {/* Smooth Inner Face Plate */}
      <rect
        x="93.5"
        y="60.5"
        width="93"
        height="71"
        rx="35"
        ry="33"
        fill={`url(#${uid}-face-grad)`}
      />

      {/* Top Hood Overhang Inner Shadow */}
      <path
        d="M 98 76 C 108 61, 172 61, 182 76 C 172 66, 108 66, 98 76 Z"
        fill={palette.hoodInnerShadow}
        opacity="0.38"
      />

      {/* Monochrome Soft Diffused Cheek Blushes */}
      <ellipse cx="109" cy="106" rx="12" ry="8.5" fill={`url(#${uid}-cheek-grad)`} />
      <ellipse cx="171" cy="106" rx="12" ry="8.5" fill={`url(#${uid}-cheek-grad)`} />

      {/* EYES */}
      {eyeMode === 'normal' && (
        <g transform={`translate(${pupilOffset.x}, ${pupilOffset.y})`}>
          <circle cx="116" cy="95" r="6.2" fill={palette.eyeFill} />
          <circle cx="114.2" cy="93" r="2.1" fill={palette.eyeHighlight} />
          <circle cx="117.8" cy="97.2" r="0.95" fill={palette.eyeHighlight} opacity="0.85" />

          <circle cx="164" cy="95" r="6.2" fill={palette.eyeFill} />
          <circle cx="162.2" cy="93" r="2.1" fill={palette.eyeHighlight} />
          <circle cx="165.8" cy="97.2" r="0.95" fill={palette.eyeHighlight} opacity="0.85" />
        </g>
      )}

      {eyeMode === 'wink' && (
        <g>
          {/* Left Eye Normal */}
          <circle cx="116" cy="95" r="6.2" fill={palette.eyeFill} />
          <circle cx="114.2" cy="93" r="2.1" fill={palette.eyeHighlight} />
          <circle cx="117.8" cy="97.2" r="0.95" fill={palette.eyeHighlight} opacity="0.85" />

          {/* Right Eye Winking Arch */}
          <path
            d="M 157 95 Q 164 88 171 95"
            stroke={palette.eyeFill}
            strokeWidth={2.7 * strokeScale}
            strokeLinecap="round"
            fill="none"
          />
        </g>
      )}

      {eyeMode === 'look-up' && (
        <g transform="translate(2, -3.5)">
          <circle cx="116" cy="95" r="6.2" fill={palette.eyeFill} />
          <circle cx="117.5" cy="92.5" r="2.2" fill={palette.eyeHighlight} />
          <circle cx="114.5" cy="97" r="1" fill={palette.eyeHighlight} opacity="0.8" />

          <circle cx="164" cy="95" r="6.2" fill={palette.eyeFill} />
          <circle cx="165.5" cy="92.5" r="2.2" fill={palette.eyeHighlight} />
          <circle cx="162.5" cy="97" r="1" fill={palette.eyeHighlight} opacity="0.8" />
        </g>
      )}

      {eyeMode === 'wide' && (
        <g>
          <circle cx="116" cy="95" r="7.2" fill={palette.eyeFill} />
          <circle cx="113.8" cy="92.4" r="2.6" fill={palette.eyeHighlight} />
          <circle cx="118.2" cy="97.6" r="1.3" fill={palette.eyeHighlight} />

          <circle cx="164" cy="95" r="7.2" fill={palette.eyeFill} />
          <circle cx="161.8" cy="92.4" r="2.6" fill={palette.eyeHighlight} />
          <circle cx="166.2" cy="97.6" r="1.3" fill={palette.eyeHighlight} />
        </g>
      )}

      {eyeMode === 'starry' && (
        <g>
          <circle cx="116" cy="95" r="6.8" fill={palette.eyeFill} />
          <path
            d="M 115 90.5 L 116 93.2 L 118.7 94.2 L 116 95.2 L 115 97.9 L 114 95.2 L 111.3 94.2 L 114 93.2 Z"
            fill={palette.eyeHighlight}
          />
          <circle cx="118.2" cy="97.5" r="1.1" fill={palette.eyeHighlight} />

          <circle cx="164" cy="95" r="6.8" fill={palette.eyeFill} />
          <path
            d="M 163 90.5 L 164 93.2 L 166.7 94.2 L 164 95.2 L 163 97.9 L 162 95.2 L 159.3 94.2 L 162 93.2 Z"
            fill={palette.eyeHighlight}
          />
          <circle cx="166.2" cy="97.5" r="1.1" fill={palette.eyeHighlight} />
        </g>
      )}

      {eyeMode === 'happy' && (
        <g
          stroke={palette.eyeFill}
          strokeWidth={2.7 * strokeScale}
          strokeLinecap="round"
          fill="none"
        >
          <path d="M 109 96 Q 116 88 123 96" />
          <path d="M 157 96 Q 164 88 171 96" />
        </g>
      )}

      {eyeMode === 'sleep' && (
        <g
          stroke={palette.eyeFill}
          strokeWidth={2.5 * strokeScale}
          strokeLinecap="round"
          fill="none"
        >
          <path d="M 109 95 Q 116 101 123 95" />
          <path d="M 111 98 L 109 100 M 116 99 L 116 101.5 M 121 98 L 123 100" strokeWidth={1.6 * strokeScale} />
          <path d="M 157 95 Q 164 101 171 95" />
          <path d="M 159 98 L 157 100 M 164 99 L 164 101.5 M 169 98 L 171 100" strokeWidth={1.6 * strokeScale} />
        </g>
      )}

      {/* MOUTH */}
      {mouthMode === 'smile' && (
        <path
          d="M 133.5 101.5 Q 140 107.2 146.5 101.5"
          fill="none"
          stroke={palette.eyeFill}
          strokeWidth={2.3 * strokeScale}
          strokeLinecap="round"
        />
      )}

      {mouthMode === 'open-happy' && (
        <g>
          <path
            d="M 132.5 100.5 Q 140 102 147.5 100.5 C 147.5 108.5, 132.5 108.5, 132.5 100.5 Z"
            fill={palette.eyeFill}
          />
          <path
            d="M 136 105.2 Q 140 103.2 144 105.2 C 142.5 107.2, 137.5 107.2, 136 105.2 Z"
            fill={palette.cheekGlow}
          />
        </g>
      )}

      {mouthMode === 'o-curious' && (
        <ellipse cx="140" cy="103" rx="3.2" ry="3.8" fill={palette.eyeFill} />
      )}

      {mouthMode === 'shy-wavy' && (
        <path
          d="M 133 102.5 Q 136.5 105.5 140 102.5 Q 143.5 105.5 147 102.5"
          fill="none"
          stroke={palette.eyeFill}
          strokeWidth={2.1 * strokeScale}
          strokeLinecap="round"
        />
      )}

      {mouthMode === 'sleep-tiny' && (
        <ellipse
          cx="140"
          cy="103.5"
          rx="2.4"
          ry="1.9"
          fill="none"
          stroke={palette.eyeFill}
          strokeWidth={2 * strokeScale}
        />
      )}

      {mouthMode === 'smirk' && (
        <path
          d="M 133 102.5 Q 141 107 147.5 99.5"
          fill="none"
          stroke={palette.eyeFill}
          strokeWidth={2.3 * strokeScale}
          strokeLinecap="round"
        />
      )}
    </g>
  );
};

export const PearPlushTorso: React.FC<{
  uid: string;
  palette: MonochromePalette;
  strokeScale: number;
}> = ({ uid, palette, strokeScale }) => {
  const sw = 1.8 * strokeScale;
  return (
    <g>
      <path
        d="M 140 37
           C 178 37, 198 58, 201 94
           C 203 118, 211 148, 211 182
           C 211 217, 192 238, 140 238
           C 88 238, 69 217, 69 182
           C 69 148, 77 118, 79 94
           C 82 58, 102 37, 140 37 Z"
        fill={`url(#${uid}-body-grad)`}
        stroke={palette.strokeColor}
        strokeWidth={sw}
        strokeLinejoin="round"
      />
      <ellipse cx="140" cy="178" rx="48" ry="42" fill={`url(#${uid}-belly-sheen)`} />
      <path
        d="M 94 222 Q 140 237 186 222"
        fill="none"
        stroke={palette.suitDeepShadow}
        strokeWidth={2.2 * strokeScale}
        strokeLinecap="round"
        opacity="0.45"
      />
    </g>
  );
};

export const StandingLegs: React.FC<{
  uid: string;
  palette: MonochromePalette;
  strokeScale: number;
  pigeonToed?: boolean;
  rightLegLifted?: boolean;
}> = ({ uid, palette, strokeScale, pigeonToed = false, rightLegLifted = false }) => {
  const sw = 1.8 * strokeScale;
  return (
    <g>
      {/* Left Leg */}
      <g transform={pigeonToed ? 'rotate(-5 112 240)' : undefined}>
        <path
          d="M 90 218
             C 90 234, 91 250, 93 259
             C 95 266, 104 268, 115 268
             C 126 268, 134 265, 135 258
             C 136 248, 136 232, 136 224 Z"
          fill={`url(#${uid}-leg-grad)`}
          stroke={palette.strokeColor}
          strokeWidth={sw}
          strokeLinejoin="round"
        />
        <path
          d="M 96 252 Q 114 256 131 251"
          fill="none"
          stroke={palette.suitDeepShadow}
          strokeWidth={1.5 * strokeScale}
          strokeLinecap="round"
          opacity="0.65"
        />
      </g>

      {/* Right Leg */}
      <g
        transform={
          rightLegLifted
            ? 'translate(4, -10) rotate(-14 165 232)'
            : pigeonToed
            ? 'rotate(5 168 240)'
            : undefined
        }
      >
        <path
          d="M 144 224
             C 144 232, 144 248, 145 258
             C 146 265, 154 268, 165 268
             C 176 268, 185 266, 187 259
             C 189 250, 190 234, 190 218 Z"
          fill={`url(#${uid}-leg-grad)`}
          stroke={palette.strokeColor}
          strokeWidth={sw}
          strokeLinejoin="round"
        />
        <path
          d="M 149 251 Q 166 256 184 252"
          fill="none"
          stroke={palette.suitDeepShadow}
          strokeWidth={1.5 * strokeScale}
          strokeLinecap="round"
          opacity="0.65"
        />
      </g>
    </g>
  );
};
