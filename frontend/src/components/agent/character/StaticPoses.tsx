import React from 'react';
import { StaticPoseId, CharacterRenderConfig } from './types';
import { CharacterSvgDefs } from './CharacterSvgDefs';
import {
  PlushFurOverlay,
  FaceWindow,
  PearPlushTorso,
  StandingLegs,
} from './CharacterElements';

export interface StaticPoseSvgProps {
  poseId: StaticPoseId;
  config: CharacterRenderConfig;
  svgRef?: React.Ref<SVGSVGElement>;
  className?: string;
  idPrefix?: string;
}

export const StaticPoseSvg: React.FC<StaticPoseSvgProps> = ({
  poseId,
  config,
  svgRef,
  className = 'w-full h-full select-none',
  idPrefix = 'static',
}) => {
  const { palette, showFurTexture, strokeScale, showStudioGrid, showGroundShadow = false, tight = true, viewBox } = config;
  const uid = `${idPrefix}-${poseId}-${palette.id}`;
  const sw = 1.8 * strokeScale;
  const effectiveViewBox = viewBox || (tight ? '20 20 240 255' : '0 0 280 300');

  return (
    <svg
      ref={svgRef}
      xmlns="http://www.w3.org/2000/svg"
      viewBox={effectiveViewBox}
      className={className}
      role="img"
      aria-label={`Agent Character pose ${poseId}`}
    >
      <CharacterSvgDefs uid={uid} palette={palette} />

      {/* Optional Reference Grid */}
      {showStudioGrid && (
        <g stroke={palette.strokeColor} strokeWidth="0.4" opacity="0.14">
          <line x1="140" y1="0" x2="140" y2="300" strokeDasharray="4 4" />
          <line x1="0" y1="268" x2="280" y2="268" strokeDasharray="4 4" />
          <circle cx="140" cy="155" r="110" fill="none" />
        </g>
      )}

      {/* ==================== POSE 01: CLASSIC NEUTRAL STAND ==================== */}
      {poseId === 'pose-neutral' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          {/* Left Hanging Arm */}
          <path
            d="M 80 120
               C 58 134, 46 168, 46 198
               C 46 213, 55 220, 64 218
               C 72 216, 75 206, 75 192
               C 75 176, 79 154, 86 140 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
            strokeLinejoin="round"
          />
          <path
            d="M 67 205 C 64 202, 62 206, 65 212"
            fill="none"
            stroke={palette.strokeColor}
            strokeWidth={1.5 * strokeScale}
            strokeLinecap="round"
          />

          {/* Right Hanging Arm */}
          <path
            d="M 200 120
               C 222 134, 234 168, 234 198
               C 234 213, 225 220, 216 218
               C 208 216, 205 206, 205 192
               C 205 176, 201 154, 194 140 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
            strokeLinejoin="round"
          />
          <path
            d="M 213 205 C 216 202, 218 206, 215 212"
            fill="none"
            stroke={palette.strokeColor}
            strokeWidth={1.5 * strokeScale}
            strokeLinecap="round"
          />

          <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
          <FaceWindow uid={uid} palette={palette} strokeScale={strokeScale} eyeMode="normal" mouthMode="smile" />
          <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
        </g>
      )}

      {/* ==================== POSE 02: CHEERFUL HELLO WAVE ==================== */}
      {poseId === 'pose-wave' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="66" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          {/* Left Relaxed Arm */}
          <path
            d="M 79 122 C 56 138, 45 172, 47 200 C 48 214, 58 219, 66 216 C 74 212, 76 198, 76 184 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          {/* Upper Body & Raised Waving Arm */}
          <g transform="rotate(-3 140 200)">
            <path
              d="M 196 132
                 C 218 118, 238 88, 234 64
                 C 231 50, 217 48, 210 58
                 C 203 68, 198 92, 186 112 Z"
              fill={`url(#${uid}-limb-right)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
              strokeLinejoin="round"
            />
            <path
              d="M 212 65 C 216 69, 219 67, 217 61"
              fill="none"
              stroke={palette.strokeColor}
              strokeWidth={1.5 * strokeScale}
              strokeLinecap="round"
            />
            {/* Motion Arcs */}
            <path
              d="M 243 53 Q 252 63 246 76 M 250 48 Q 261 62 254 79"
              fill="none"
              stroke={palette.strokeColor}
              strokeWidth={1.6 * strokeScale}
              strokeLinecap="round"
              opacity="0.65"
            />

            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="normal"
              mouthMode="open-happy"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
          </g>
        </g>
      )}

      {/* ==================== POSE 03: COZY SEATED REST ==================== */}
      {poseId === 'pose-sitting' && (
        <g transform="translate(0, 14)">
          {showGroundShadow && <ellipse cx="140" cy="252" rx="84" ry="14" fill={`url(#${uid}-ground-shadow)`} />}

          <path
            d="M 140 42
               C 178 42, 198 62, 201 98
               C 204 126, 218 164, 218 202
               C 218 234, 194 248, 140 248
               C 86 248, 62 234, 62 202
               C 62 164, 76 126, 79 98
               C 82 62, 102 42, 140 42 Z"
            fill={`url(#${uid}-body-grad)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <ellipse cx="140" cy="184" rx="52" ry="40" fill={`url(#${uid}-belly-sheen)`} />

          {/* Resting Arms Forward on Lap */}
          <path
            d="M 76 128 C 58 148, 58 184, 80 202 C 92 210, 102 203, 98 191 C 94 179, 84 162, 86 144 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <path
            d="M 204 128 C 222 148, 222 184, 200 202 C 188 210, 178 203, 182 191 C 186 179, 196 162, 194 144 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          {/* Forward Feet with Paw Pads */}
          <ellipse
            cx="96"
            cy="234"
            rx="24"
            ry="19"
            transform="rotate(-10 96 234)"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <ellipse
            cx="95"
            cy="236"
            rx="12"
            ry="9"
            transform="rotate(-10 95 236)"
            fill={palette.suitShadow}
            stroke={palette.strokeColor}
            strokeWidth={1.1 * strokeScale}
          />

          <ellipse
            cx="184"
            cy="234"
            rx="24"
            ry="19"
            transform="rotate(10 184 234)"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <ellipse
            cx="185"
            cy="236"
            rx="12"
            ry="9"
            transform="rotate(10 185 236)"
            fill={palette.suitShadow}
            stroke={palette.strokeColor}
            strokeWidth={1.1 * strokeScale}
          />

          <g transform="translate(0, 4)">
            <FaceWindow uid={uid} palette={palette} strokeScale={strokeScale} eyeMode="normal" mouthMode="smile" />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
          </g>
        </g>
      )}

      {/* ==================== POSE 04: CURIOUS PONDER / THINKING ==================== */}
      {poseId === 'pose-thinking' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          <g transform="rotate(3.5 140 190)">
            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="look-up"
              mouthMode="o-curious"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

            {/* Arm Crossed */}
            <path
              d="M 76 132 C 62 156, 74 182, 118 180 C 130 179, 132 166, 120 163 C 96 160, 88 150, 86 138 Z"
              fill={`url(#${uid}-limb-left)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
              strokeLinejoin="round"
            />

            {/* Arm Touching Chin */}
            <path
              d="M 202 132 C 214 156, 192 172, 162 140 C 153 130, 143 134, 148 145 C 160 168, 198 188, 212 152 Z"
              fill={`url(#${uid}-limb-right)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
              strokeLinejoin="round"
            />
            <circle
              cx="154"
              cy="137"
              r="12"
              fill={`url(#${uid}-limb-right)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />
          </g>

          {/* Thought Bubbles / Idea Spark */}
          <g fill={palette.faceLight} stroke={palette.strokeColor} strokeWidth={1.6 * strokeScale}>
            <circle cx="208" cy="52" r="4" />
            <circle cx="220" cy="40" r="6.5" />
            <path
              d="M 232 22 C 232 14, 245 14, 245 22 C 245 27, 238 28, 238 33"
              fill="none"
              strokeWidth={2.2 * strokeScale}
              strokeLinecap="round"
            />
            <circle cx="238" cy="39" r="1.5" fill={palette.strokeColor} />
          </g>
        </g>
      )}

      {/* ==================== POSE 05: JOYFUL STAR LEAP ==================== */}
      {poseId === 'pose-star-jump' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="274" rx="44" ry="7.5" fill={`url(#${uid}-ground-shadow)`} />}

          <g transform="translate(0, -18)">
            {/* Outstretched Legs */}
            <g transform="rotate(18 108 222)">
              <path
                d="M 92 216 C 92 232, 93 248, 95 256 C 97 263, 129 263, 132 255 C 134 246, 134 230, 134 218 Z"
                fill={`url(#${uid}-leg-grad)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>
            <g transform="rotate(-18 172 222)">
              <path
                d="M 146 218 C 146 230, 146 246, 148 255 C 151 263, 183 263, 185 256 C 187 248, 188 232, 188 216 Z"
                fill={`url(#${uid}-leg-grad)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            {/* Both Arms Raised */}
            <path
              d="M 84 128 C 60 112, 42 84, 48 62 C 51 49, 65 49, 71 60 C 78 72, 84 96, 94 114 Z"
              fill={`url(#${uid}-limb-left)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />
            <path
              d="M 196 128 C 220 112, 238 84, 232 62 C 229 49, 215 49, 209 60 C 202 72, 196 96, 186 114 Z"
              fill={`url(#${uid}-limb-right)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />

            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="happy"
              mouthMode="open-happy"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

            {/* Sparkles */}
            <path
              d="M 42 36 L 45 43 L 52 46 L 45 49 L 42 56 L 39 49 L 32 46 L 39 43 Z"
              fill={palette.faceLight}
              stroke={palette.strokeColor}
              strokeWidth={1.3 * strokeScale}
            />
            <path
              d="M 238 36 L 241 43 L 248 46 L 241 49 L 238 56 L 235 49 L 228 46 L 235 43 Z"
              fill={palette.faceLight}
              stroke={palette.strokeColor}
              strokeWidth={1.3 * strokeScale}
            />
          </g>
        </g>
      )}

      {/* ==================== POSE 06: BASHFUL CHEEK TOUCH ==================== */}
      {poseId === 'pose-shy' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="66" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} pigeonToed />
          <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
          <FaceWindow
            uid={uid}
            palette={palette}
            strokeScale={strokeScale}
            eyeMode="wide"
            mouthMode="shy-wavy"
          />
          <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

          {/* Both Paws Touching Cheeks */}
          <path
            d="M 76 138 C 60 156, 74 176, 102 124 C 107 114, 96 106, 89 114 C 78 128, 72 142, 76 138 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <circle
            cx="98"
            cy="118"
            r="12.5"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          <path
            d="M 204 138 C 220 156, 206 176, 178 124 C 173 114, 184 106, 191 114 C 202 128, 208 142, 204 138 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <circle
            cx="182"
            cy="118"
            r="12.5"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
        </g>
      )}

      {/* ==================== POSE 07: SERENE SLUMBER ==================== */}
      {poseId === 'pose-sleeping' && (
        <g transform="translate(0, 12)">
          {showGroundShadow && <ellipse cx="140" cy="254" rx="86" ry="14" fill={`url(#${uid}-ground-shadow)`} />}

          {/* Cushion */}
          <rect
            x="48"
            y="206"
            width="184"
            height="46"
            rx="23"
            fill={`url(#${uid}-prop-grad)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          <path
            d="M 140 48
               C 178 48, 198 68, 201 104
               C 204 132, 214 166, 214 200
               C 214 230, 190 244, 140 244
               C 90 244, 66 230, 66 200
               C 66 166, 76 132, 79 104
               C 82 68, 102 48, 140 48 Z"
            fill={`url(#${uid}-body-grad)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          <path
            d="M 78 132 C 62 152, 62 186, 82 208 C 90 216, 100 210, 96 198 C 92 184, 84 162, 86 144 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <path
            d="M 202 132 C 218 152, 218 186, 198 208 C 190 216, 180 210, 184 198 C 188 184, 196 162, 194 144 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          <g transform="translate(0, 10) rotate(3 140 100)">
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="sleep"
              mouthMode="sleep-tiny"
            />
          </g>
          <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

          {/* Drifting Zzz */}
          <g
            fill="none"
            stroke={palette.strokeColor}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M 196 48 L 208 48 L 196 60 L 208 60" strokeWidth={2 * strokeScale} />
            <path d="M 214 30 L 229 30 L 214 45 L 229 45" strokeWidth={2.3 * strokeScale} />
            <path d="M 235 10 L 253 10 L 235 28 L 253 28" strokeWidth={2.6 * strokeScale} />
          </g>
        </g>
      )}

      {/* ==================== POSE 08: PROUD AKIMBO STANCE ==================== */}
      {poseId === 'pose-confident' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="70" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          {/* Bent Arms on Hips */}
          <path
            d="M 80 124 C 46 142, 42 168, 74 188 C 84 194, 90 182, 82 174 C 66 162, 68 150, 84 138 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
            strokeLinejoin="round"
          />
          <path
            d="M 200 124 C 234 142, 238 168, 206 188 C 196 194, 190 182, 198 174 C 214 162, 212 150, 196 138 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
            strokeLinejoin="round"
          />

          <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />

          <circle
            cx="78"
            cy="183"
            r="11.5"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <circle
            cx="202"
            cy="183"
            r="11.5"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          <FaceWindow
            uid={uid}
            palette={palette}
            strokeScale={strokeScale}
            eyeMode="normal"
            mouthMode="smirk"
          />
          <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
        </g>
      )}

      {/* ==================== POSE 09: WARM COCOA MUG HUG ==================== */}
      {poseId === 'pose-warm-mug' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />
          <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
          <FaceWindow
            uid={uid}
            palette={palette}
            strokeScale={strokeScale}
            eyeMode="happy"
            mouthMode="smile"
          />
          <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

          {/* Steaming Mug */}
          <g transform="translate(140, 174)">
            <path
              d="M 20 -10 C 31 -10, 31 10, 20 10"
              fill="none"
              stroke={palette.strokeColor}
              strokeWidth={3.5 * strokeScale}
            />
            <path
              d="M 20 -10 C 31 -10, 31 10, 20 10"
              fill="none"
              stroke={palette.faceLight}
              strokeWidth={1.8 * strokeScale}
            />
            <path
              d="M -22 -16 L 22 -16 L 19 16 C 18 24, -18 24, -19 16 Z"
              fill={`url(#${uid}-prop-grad)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
              strokeLinejoin="round"
            />
            <ellipse
              cx="0"
              cy="-16"
              rx="22"
              ry="5.5"
              fill={palette.faceLight}
              stroke={palette.strokeColor}
              strokeWidth={sw * 0.9}
            />
            <ellipse cx="0" cy="-15.5" rx="17" ry="3.2" fill={palette.suitDeepShadow} />
            <path
              d="M -7 -24 Q -12 -32 -5 -39 Q 2 -46 -4 -53"
              fill="none"
              stroke={palette.strokeColor}
              strokeWidth={1.6 * strokeScale}
              strokeLinecap="round"
              opacity="0.6"
            />
            <path
              d="M 7 -22 Q 12 -30 6 -37 Q 0 -44 6 -51"
              fill="none"
              stroke={palette.strokeColor}
              strokeWidth={1.6 * strokeScale}
              strokeLinecap="round"
              opacity="0.6"
            />
          </g>

          {/* Wrapping Arms */}
          <path
            d="M 78 128 C 60 150, 74 182, 118 182 C 127 182, 128 168, 118 166 C 94 164, 86 150, 86 136 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <path
            d="M 202 128 C 220 150, 206 182, 162 182 C 153 182, 152 168, 162 166 C 186 164, 194 150, 194 136 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
        </g>
      )}

      {/* ==================== POSE 10: PLUSH HEART OFFERING ==================== */}
      {poseId === 'pose-heart-gift' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="64" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} rightLegLifted />
          <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
          <FaceWindow
            uid={uid}
            palette={palette}
            strokeScale={strokeScale}
            eyeMode="starry"
            mouthMode="smile"
          />
          <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

          {/* Shaded Monochrome Heart Prop */}
          <path
            d="M 140 194
               C 140 194, 110 174, 110 155
               C 110 143, 122 136, 132 142
               C 137 145, 140 150, 140 150
               C 140 150, 143 145, 148 142
               C 158 136, 170 143, 170 155
               C 170 174, 140 194, 140 194 Z"
            fill={`url(#${uid}-prop-grad)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
            strokeLinejoin="round"
          />
          <ellipse
            cx="123"
            cy="152"
            rx="5"
            ry="3"
            transform="rotate(-25 123 152)"
            fill={palette.eyeHighlight}
            opacity="0.8"
          />

          {/* Supporting Paws */}
          <path
            d="M 78 128 C 60 148, 72 180, 112 178 C 122 177, 122 164, 112 163 C 92 161, 86 148, 86 136 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <path
            d="M 202 128 C 220 148, 208 180, 168 178 C 158 177, 158 164, 168 163 C 188 161, 194 148, 194 136 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
        </g>
      )}
    </svg>
  );
};
