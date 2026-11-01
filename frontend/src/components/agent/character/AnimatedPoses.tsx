import React from 'react';
import { AnimatedPoseId, CharacterRenderConfig } from './types';
import { CharacterSvgDefs } from './CharacterSvgDefs';
import { usePageVisibility } from '../../../hooks/usePageVisibility';
import { useReducedMotion } from '../../../hooks/useReducedMotion';
import {
  PlushFurOverlay,
  FaceWindow,
  PearPlushTorso,
  StandingLegs,
} from './CharacterElements';

export interface AnimatedPoseSvgProps {
  animId: AnimatedPoseId;
  config: CharacterRenderConfig;
  svgRef?: React.Ref<SVGSVGElement>;
  className?: string;
  idPrefix?: string;
}

export const AnimatedPoseSvg: React.FC<AnimatedPoseSvgProps> = ({
  animId,
  config,
  svgRef,
  className = 'w-full h-full select-none',
  idPrefix = 'anim',
}) => {
  const { palette, showFurTexture, strokeScale, speedMultiplier, isPaused, showStudioGrid, showGroundShadow = false, tight = true, viewBox } = config;
  const uid = `${idPrefix}-${animId}-${palette.id}`;
  const sw = 1.8 * strokeScale;
  const isVisible = usePageVisibility();
  const { isReduced } = useReducedMotion();
  const playState = isPaused || !isVisible || isReduced ? 'paused' : 'running';
  const dur = (baseSeconds: number) => `${(baseSeconds / speedMultiplier).toFixed(2)}s`;
  const effectiveViewBox = viewBox || (tight ? '20 20 240 255' : '0 0 280 300');

  return (
    <svg
      ref={svgRef}
      xmlns="http://www.w3.org/2000/svg"
      viewBox={effectiveViewBox}
      className={className}
      role="img"
      aria-label={`Agent Character animation ${animId}`}
    >
      <CharacterSvgDefs uid={uid} palette={palette} />

      {/* Embedded Self-Contained Keyframe Animations */}
      <style>{`
        /* 01. Living Breathing & Blink */
        @keyframes ${uid}-breathe {
          0%, 100% { transform: translateY(0px) scale(1, 1); }
          50% { transform: translateY(-3.5px) scale(1.022, 0.985); }
        }
        @keyframes ${uid}-arm-left-idle {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(2.8deg); }
        }
        @keyframes ${uid}-arm-right-idle {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(-2.8deg); }
        }
        @keyframes ${uid}-blink {
          0%, 44%, 48%, 92%, 96%, 100% { transform: scaleY(1); }
          46%, 94% { transform: scaleY(0.08); }
        }

        /* 02. Enthusiastic Wave Loop */
        @keyframes ${uid}-wave-arm {
          0%, 100% { transform: rotate(-6deg); }
          50% { transform: rotate(22deg); }
        }
        @keyframes ${uid}-wave-body {
          0%, 100% { transform: rotate(-1.5deg) translateY(0px); }
          50% { transform: rotate(2deg) translateY(-3px); }
        }

        /* 03. Squash & Stretch Happy Hop */
        @keyframes ${uid}-hop-body {
          0%, 100% { transform: translateY(0px) scale(1.07, 0.93); }
          15% { transform: translateY(6px) scale(1.12, 0.88); }
          48% { transform: translateY(-32px) scale(0.94, 1.06); }
          82% { transform: translateY(4px) scale(1.09, 0.91); }
        }
        @keyframes ${uid}-hop-shadow {
          0%, 100% { transform: scale(1.05, 1); opacity: 0.95; }
          15% { transform: scale(1.14, 1.05); opacity: 1; }
          48% { transform: scale(0.62, 0.62); opacity: 0.48; }
          82% { transform: scale(1.08, 1); opacity: 0.95; }
        }
        @keyframes ${uid}-hop-arm-l {
          0%, 15%, 100% { transform: rotate(-6deg); }
          48% { transform: rotate(36deg); }
        }
        @keyframes ${uid}-hop-arm-r {
          0%, 15%, 100% { transform: rotate(6deg); }
          48% { transform: rotate(-36deg); }
        }

        /* 04. Jaunty Waddle Walk Cycle */
        @keyframes ${uid}-waddle-torso {
          0%, 100% { transform: translateY(0px) rotate(-3.5deg); }
          25% { transform: translateY(-5px) rotate(0deg); }
          50% { transform: translateY(0px) rotate(3.5deg); }
          75% { transform: translateY(-5px) rotate(0deg); }
        }
        @keyframes ${uid}-step-left {
          0%, 100% { transform: translateY(-10px) rotate(-8deg); }
          50% { transform: translateY(2px) rotate(5deg); }
        }
        @keyframes ${uid}-step-right {
          0%, 100% { transform: translateY(2px) rotate(-5deg); }
          50% { transform: translateY(-10px) rotate(8deg); }
        }

        /* 05. Cozy Shiver & Fur Puff */
        @keyframes ${uid}-shiver {
          0%, 55%, 100% { transform: translate(0, 0) scale(1); }
          8% { transform: translate(-3.5px, -1px) scale(1.03, 0.98); }
          16% { transform: translate(3.5px, 0px) scale(1.04, 0.97); }
          24% { transform: translate(-3.5px, -2px) scale(1.05, 0.97); }
          32% { transform: translate(3.5px, 0px) scale(1.04, 0.98); }
          40% { transform: translate(-2px, -1px) scale(1.02, 0.99); }
        }
        @keyframes ${uid}-puff-ring {
          0%, 50%, 100% { transform: scale(0.92); opacity: 0; }
          15% { transform: scale(1.02); opacity: 0.75; }
          42% { transform: scale(1.14); opacity: 0; }
        }

        /* 06. Levitating Zen Meditation */
        @keyframes ${uid}-zen-hover {
          0%, 100% { transform: translateY(4px); }
          50% { transform: translateY(-18px); }
        }
        @keyframes ${uid}-zen-ring {
          0% { transform: scale(0.5); opacity: 0.8; }
          100% { transform: scale(1.35); opacity: 0; }
        }

        /* 07. Happy Cheek Squish & Giggle */
        @keyframes ${uid}-face-squish {
          0%, 100% { transform: scale(1, 1); }
          35%, 65% { transform: scale(0.89, 1.05); }
        }
        @keyframes ${uid}-paw-squish-l {
          0%, 100% { transform: translate(0px, 0px); }
          35%, 65% { transform: translate(8px, -2px); }
        }
        @keyframes ${uid}-paw-squish-r {
          0%, 100% { transform: translate(0px, 0px); }
          35%, 65% { transform: translate(-8px, -2px); }
        }
        @keyframes ${uid}-giggle-bob {
          0%, 100% { transform: translateY(0px); }
          25% { transform: translateY(-3px); }
          45% { transform: translateY(1px); }
          60% { transform: translateY(-4px); }
          75% { transform: translateY(0px); }
        }

        /* 08. Curious Peek-a-Boo */
        @keyframes ${uid}-peek-rise {
          0%, 10%, 92%, 100% { transform: translateY(58px); }
          26%, 76% { transform: translateY(0px); }
        }
        @keyframes ${uid}-peek-scan {
          0%, 28%, 74%, 100% { transform: translateX(0px); }
          42% { transform: translateX(-7px); }
          60% { transform: translateX(7px); }
        }

        /* 09. Sleepy Nod-Off & Startle */
        @keyframes ${uid}-sleepy-head {
          0%, 88%, 100% { transform: translateY(0px) rotate(0deg); }
          30% { transform: translateY(5px) rotate(3deg); }
          62% { transform: translateY(12px) rotate(7deg); }
          76% { transform: translateY(-6px) rotate(-2deg); }
        }
        @keyframes ${uid}-z-float {
          0%, 70%, 100% { opacity: 0; transform: translateY(6px) scale(0.8); }
          25%, 60% { opacity: 0.85; transform: translateY(-8px) scale(1.05); }
        }

        /* 10. Plush Groove Boogie */
        @keyframes ${uid}-boogie-body {
          0%, 100% { transform: translateX(-5px) translateY(0px) rotate(-4deg); }
          25% { transform: translateX(0px) translateY(-6px) rotate(0deg); }
          50% { transform: translateX(5px) translateY(0px) rotate(4deg); }
          75% { transform: translateX(0px) translateY(-6px) rotate(0deg); }
        }
        @keyframes ${uid}-boogie-arm-l {
          0%, 100% { transform: rotate(28deg); }
          50% { transform: rotate(-18deg); }
        }
        @keyframes ${uid}-boogie-arm-r {
          0%, 100% { transform: rotate(18deg); }
          50% { transform: rotate(-28deg); }
        }
        @keyframes ${uid}-star-pulse {
          0%, 100% { transform: scale(0.75) rotate(0deg); opacity: 0.45; }
          50% { transform: scale(1.2) rotate(20deg); opacity: 1; }
        }
      `}</style>

      {showStudioGrid && (
        <g stroke={palette.strokeColor} strokeWidth="0.4" opacity="0.14">
          <line x1="140" y1="0" x2="140" y2="300" strokeDasharray="4 4" />
          <line x1="0" y1="268" x2="280" y2="268" strokeDasharray="4 4" />
        </g>
      )}

      {/* ==================== ANIM 01: LIVING BREATHING & BLINK ==================== */}
      {animId === 'anim-breathing' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          <g
            style={{
              transformOrigin: '140px 235px',
              animation: `${uid}-breathe ${dur(3.2)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            {/* Left Arm Sway */}
            <g
              style={{
                transformOrigin: '80px 128px',
                animation: `${uid}-arm-left-idle ${dur(3.2)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 80 120 C 58 134, 46 168, 46 198 C 46 213, 55 220, 64 218 C 72 216, 75 206, 75 192 C 75 176, 79 154, 86 140 Z"
                fill={`url(#${uid}-limb-left)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            {/* Right Arm Sway */}
            <g
              style={{
                transformOrigin: '200px 128px',
                animation: `${uid}-arm-right-idle ${dur(3.2)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 200 120 C 222 134, 234 168, 234 198 C 234 213, 225 220, 216 218 C 208 216, 205 206, 205 192 C 205 176, 201 154, 194 140 Z"
                fill={`url(#${uid}-limb-right)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />

            {/* Blinking Face Window */}
            <g>
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
              <rect
                x="93.5"
                y="60.5"
                width="93"
                height="71"
                rx="35"
                ry="33"
                fill={`url(#${uid}-face-grad)`}
              />
              <ellipse cx="109" cy="106" rx="12" ry="8.5" fill={`url(#${uid}-cheek-grad)`} />
              <ellipse cx="171" cy="106" rx="12" ry="8.5" fill={`url(#${uid}-cheek-grad)`} />

              <g
                style={{
                  transformOrigin: '140px 95px',
                  animation: `${uid}-blink ${dur(4.0)} ease-in-out infinite`,
                  animationPlayState: playState,
                }}
              >
                <circle cx="116" cy="95" r="6.2" fill={palette.eyeFill} />
                <circle cx="114.2" cy="93" r="2.1" fill={palette.eyeHighlight} />
                <circle cx="164" cy="95" r="6.2" fill={palette.eyeFill} />
                <circle cx="162.2" cy="93" r="2.1" fill={palette.eyeHighlight} />
              </g>

              <path
                d="M 133.5 101.5 Q 140 107.2 146.5 101.5"
                fill="none"
                stroke={palette.eyeFill}
                strokeWidth={2.3 * strokeScale}
                strokeLinecap="round"
              />
            </g>

            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
          </g>
        </g>
      )}

      {/* ==================== ANIM 02: ENTHUSIASTIC GREETING LOOP ==================== */}
      {animId === 'anim-wave-loop' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          <g
            style={{
              transformOrigin: '140px 230px',
              animation: `${uid}-wave-body ${dur(1.1)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <path
              d="M 79 122 C 56 138, 45 172, 47 200 C 48 214, 58 219, 66 216 C 74 212, 76 198, 76 184 Z"
              fill={`url(#${uid}-limb-left)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />

            <g
              style={{
                transformOrigin: '192px 124px',
                animation: `${uid}-wave-arm ${dur(0.55)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 196 132 C 218 118, 238 88, 234 64 C 231 50, 217 48, 210 58 C 203 68, 198 92, 186 112 Z"
                fill={`url(#${uid}-limb-right)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

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

      {/* ==================== ANIM 03: SQUASH & STRETCH HAPPY HOP ==================== */}
      {animId === 'anim-happy-hop' && (
        <g>
          {showGroundShadow && (
            <g
              style={{
                transformOrigin: '140px 269px',
                animation: `${uid}-hop-shadow ${dur(1.25)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />
            </g>
          )}

          <g
            style={{
              transformOrigin: '140px 265px',
              animation: `${uid}-hop-body ${dur(1.25)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

            <g
              style={{
                transformOrigin: '82px 128px',
                animation: `${uid}-hop-arm-l ${dur(1.25)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 80 120 C 58 134, 46 168, 46 198 C 46 213, 55 220, 64 218 C 72 216, 75 206, 75 192 Z"
                fill={`url(#${uid}-limb-left)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <g
              style={{
                transformOrigin: '198px 128px',
                animation: `${uid}-hop-arm-r ${dur(1.25)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 200 120 C 222 134, 234 168, 234 198 C 234 213, 225 220, 216 218 C 208 216, 205 206, 205 192 Z"
                fill={`url(#${uid}-limb-right)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="happy"
              mouthMode="open-happy"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
          </g>
        </g>
      )}

      {/* ==================== ANIM 04: JAUNTY WADDLE WALK CYCLE ==================== */}
      {animId === 'anim-waddle-walk' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}

          {/* Stepping Legs */}
          <g
            style={{
              transformOrigin: '112px 225px',
              animation: `${uid}-step-left ${dur(0.95)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <path
              d="M 90 218 C 90 234, 91 250, 93 259 C 95 266, 104 268, 115 268 C 126 268, 134 265, 135 258 C 136 248, 136 232, 136 224 Z"
              fill={`url(#${uid}-leg-grad)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />
          </g>

          <g
            style={{
              transformOrigin: '168px 225px',
              animation: `${uid}-step-right ${dur(0.95)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <path
              d="M 144 224 C 144 232, 144 248, 145 258 C 146 265, 154 268, 165 268 C 176 268, 185 266, 187 259 C 189 250, 190 234, 190 218 Z"
              fill={`url(#${uid}-leg-grad)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />
          </g>

          {/* Waddling Torso & Arms */}
          <g
            style={{
              transformOrigin: '140px 210px',
              animation: `${uid}-waddle-torso ${dur(0.95)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <g
              style={{
                transformOrigin: '80px 128px',
                animation: `${uid}-step-right ${dur(0.95)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 80 120 C 58 134, 46 168, 46 198 C 46 213, 55 220, 64 218 C 72 216, 75 206, 75 192 Z"
                fill={`url(#${uid}-limb-left)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <g
              style={{
                transformOrigin: '200px 128px',
                animation: `${uid}-step-left ${dur(0.95)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 200 120 C 222 134, 234 168, 234 198 C 234 213, 225 220, 216 218 C 208 216, 205 206, 205 192 Z"
                fill={`url(#${uid}-limb-right)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="normal"
              mouthMode="smile"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
          </g>
        </g>
      )}

      {/* ==================== ANIM 05: COZY FUR PUFF & SHIVER ==================== */}
      {animId === 'anim-fluff-shiver' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}

          <g
            style={{
              transformOrigin: '140px 155px',
              animation: `${uid}-puff-ring ${dur(2.2)} ease-out infinite`,
              animationPlayState: playState,
            }}
            stroke={palette.strokeColor}
            strokeWidth={1.6 * strokeScale}
            strokeDasharray="6 8"
            fill="none"
          >
            <ellipse cx="140" cy="150" rx="88" ry="108" />
          </g>

          <g
            style={{
              transformOrigin: '140px 240px',
              animation: `${uid}-shiver ${dur(2.2)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} pigeonToed />
            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />

            <path
              d="M 78 130 C 60 150, 68 184, 96 184 C 106 184, 108 172, 98 168 C 86 164, 84 150, 86 138 Z"
              fill={`url(#${uid}-limb-left)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />
            <path
              d="M 202 130 C 220 150, 212 184, 184 184 C 174 184, 172 172, 182 168 C 194 164, 196 150, 194 138 Z"
              fill={`url(#${uid}-limb-right)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />

            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="wide"
              mouthMode="shy-wavy"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={true} />
          </g>
        </g>
      )}

      {/* ==================== ANIM 06: LEVITATING ZEN MEDITATION ==================== */}
      {animId === 'anim-zen-float' && (
        <g>
          {/* Concentric Aura Rings */}
          <ellipse
            cx="140"
            cy="266"
            rx="62"
            ry="11"
            fill="none"
            stroke={palette.strokeColor}
            strokeWidth={1.5 * strokeScale}
            style={{
              transformOrigin: '140px 266px',
              animation: `${uid}-zen-ring ${dur(2.8)} linear infinite`,
              animationPlayState: playState,
            }}
          />
          {showGroundShadow && <ellipse cx="140" cy="266" rx="52" ry="9" fill={`url(#${uid}-ground-shadow)`} />}

          {/* Floating Body */}
          <g
            style={{
              transformOrigin: '140px 150px',
              animation: `${uid}-zen-hover ${dur(2.8)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />

            {/* Crossed Lotus Legs */}
            <ellipse
              cx="112"
              cy="232"
              rx="28"
              ry="14"
              transform="rotate(8 112 232)"
              fill={`url(#${uid}-leg-grad)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />
            <ellipse
              cx="168"
              cy="232"
              rx="28"
              ry="14"
              transform="rotate(-8 168 232)"
              fill={`url(#${uid}-leg-grad)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />

            {/* Meditating Paws Together */}
            <path
              d="M 78 130 C 60 152, 74 186, 122 186 C 132 186, 132 172, 122 170 C 94 166, 86 150, 86 138 Z"
              fill={`url(#${uid}-limb-left)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />
            <path
              d="M 202 130 C 220 152, 206 186, 158 186 C 148 186, 148 172, 158 170 C 186 166, 194 150, 194 138 Z"
              fill={`url(#${uid}-limb-right)`}
              stroke={palette.strokeColor}
              strokeWidth={sw}
            />

            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="sleep"
              mouthMode="smile"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

            {/* Orbiting Motes */}
            <circle cx="52" cy="112" r="4" fill={palette.faceLight} stroke={palette.strokeColor} strokeWidth={1.4 * strokeScale} />
            <circle cx="228" cy="112" r="4" fill={palette.faceLight} stroke={palette.strokeColor} strokeWidth={1.4 * strokeScale} />
          </g>
        </g>
      )}

      {/* ==================== ANIM 07: HAPPY CHEEK SQUISH & GIGGLE ==================== */}
      {animId === 'anim-cheek-squish' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          <g
            style={{
              transformOrigin: '140px 220px',
              animation: `${uid}-giggle-bob ${dur(1.6)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />

            <g
              style={{
                transformOrigin: '140px 96px',
                animation: `${uid}-face-squish ${dur(1.6)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <FaceWindow
                uid={uid}
                palette={palette}
                strokeScale={strokeScale}
                eyeMode="happy"
                mouthMode="shy-wavy"
              />
            </g>

            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

            {/* Paws Pressing Cheeks */}
            <g
              style={{
                animation: `${uid}-paw-squish-l ${dur(1.6)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 76 138 C 60 156, 74 176, 96 122 C 102 112, 92 104, 84 112 C 74 126, 70 140, 76 138 Z"
                fill={`url(#${uid}-limb-left)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
              <circle
                cx="92"
                cy="114"
                r="13"
                fill={`url(#${uid}-limb-left)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <g
              style={{
                animation: `${uid}-paw-squish-r ${dur(1.6)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 204 138 C 220 156, 206 176, 184 122 C 178 112, 188 104, 196 112 C 206 126, 210 140, 204 138 Z"
                fill={`url(#${uid}-limb-right)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
              <circle
                cx="188"
                cy="114"
                r="13"
                fill={`url(#${uid}-limb-right)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>
          </g>
        </g>
      )}

      {/* ==================== ANIM 08: CURIOUS PEEK-A-BOO ==================== */}
      {animId === 'anim-peekaboo' && (
        <g>
          <clipPath id={`${uid}-peek-clip`}>
            <rect x="0" y="0" width="280" height="225" />
          </clipPath>

          <g clipPath={`url(#${uid}-peek-clip)`}>
            <g
              style={{
                animation: `${uid}-peek-rise ${dur(3.4)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
              <g
                style={{
                  animation: `${uid}-peek-scan ${dur(3.4)} ease-in-out infinite`,
                  animationPlayState: playState,
                }}
              >
                <FaceWindow
                  uid={uid}
                  palette={palette}
                  strokeScale={strokeScale}
                  eyeMode="wide"
                  mouthMode="o-curious"
                />
              </g>
              <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
            </g>
          </g>

          {/* Ledge */}
          <line
            x1="28"
            y1="225"
            x2="252"
            y2="225"
            stroke={palette.strokeColor}
            strokeWidth={3 * strokeScale}
            strokeLinecap="round"
          />
          <ellipse
            cx="84"
            cy="225"
            rx="16"
            ry="11"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <ellipse
            cx="196"
            cy="225"
            rx="16"
            ry="11"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
        </g>
      )}

      {/* ==================== ANIM 09: SLEEPY NOD-OFF & STARTLE ==================== */}
      {animId === 'anim-sleepy-nod' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          <path
            d="M 80 120 C 58 134, 46 168, 46 198 C 46 213, 55 220, 64 218 C 72 216, 75 206, 75 192 Z"
            fill={`url(#${uid}-limb-left)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />
          <path
            d="M 200 120 C 222 134, 234 168, 234 198 C 234 213, 225 220, 216 218 C 208 216, 205 206, 205 192 Z"
            fill={`url(#${uid}-limb-right)`}
            stroke={palette.strokeColor}
            strokeWidth={sw}
          />

          <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />

          <g
            style={{
              transformOrigin: '140px 135px',
              animation: `${uid}-sleepy-head ${dur(3.6)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="sleep"
              mouthMode="sleep-tiny"
            />
          </g>

          <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />

          {/* Zzz Float */}
          <g
            style={{
              transformOrigin: '215px 45px',
              animation: `${uid}-z-float ${dur(3.6)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
            fill="none"
            stroke={palette.strokeColor}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M 198 54 L 210 54 L 198 66 L 210 66" strokeWidth={2 * strokeScale} />
            <path d="M 218 32 L 234 32 L 218 48 L 234 48" strokeWidth={2.4 * strokeScale} />
          </g>
        </g>
      )}

      {/* ==================== ANIM 10: PLUSH GROOVE BOOGIE ==================== */}
      {animId === 'anim-boogie-dance' && (
        <g>
          {showGroundShadow && <ellipse cx="140" cy="269" rx="68" ry="11" fill={`url(#${uid}-ground-shadow)`} />}
          <StandingLegs uid={uid} palette={palette} strokeScale={strokeScale} />

          <g
            style={{
              transformOrigin: '140px 225px',
              animation: `${uid}-boogie-body ${dur(1.1)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <g
              style={{
                transformOrigin: '80px 128px',
                animation: `${uid}-boogie-arm-l ${dur(0.55)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 84 128 C 60 112, 42 84, 48 62 C 51 49, 65 49, 71 60 C 78 72, 84 96, 94 114 Z"
                fill={`url(#${uid}-limb-left)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <g
              style={{
                transformOrigin: '200px 128px',
                animation: `${uid}-boogie-arm-r ${dur(0.55)} ease-in-out infinite`,
                animationPlayState: playState,
              }}
            >
              <path
                d="M 196 128 C 220 112, 238 84, 232 62 C 229 49, 215 49, 209 60 C 202 72, 196 96, 186 114 Z"
                fill={`url(#${uid}-limb-right)`}
                stroke={palette.strokeColor}
                strokeWidth={sw}
              />
            </g>

            <PearPlushTorso uid={uid} palette={palette} strokeScale={strokeScale} />
            <FaceWindow
              uid={uid}
              palette={palette}
              strokeScale={strokeScale}
              eyeMode="starry"
              mouthMode="open-happy"
            />
            <PlushFurOverlay palette={palette} strokeScale={strokeScale} visible={showFurTexture} />
          </g>

          {/* Pulsing Monochrome Stars */}
          <g
            style={{
              transformOrigin: '44px 48px',
              animation: `${uid}-star-pulse ${dur(0.8)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <path
              d="M 44 36 L 47 45 L 56 48 L 47 51 L 44 60 L 41 51 L 32 48 L 41 45 Z"
              fill={palette.faceLight}
              stroke={palette.strokeColor}
              strokeWidth={1.4 * strokeScale}
            />
          </g>
          <g
            style={{
              transformOrigin: '236px 48px',
              animation: `${uid}-star-pulse ${dur(0.8)} ease-in-out infinite`,
              animationPlayState: playState,
            }}
          >
            <path
              d="M 236 36 L 239 45 L 248 48 L 239 51 L 236 60 L 233 51 L 224 48 L 233 45 Z"
              fill={palette.faceLight}
              stroke={palette.strokeColor}
              strokeWidth={1.4 * strokeScale}
            />
          </g>
        </g>
      )}
    </svg>
  );
};
