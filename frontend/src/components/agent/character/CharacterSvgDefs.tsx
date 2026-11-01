import React from 'react';
import { MonochromePalette } from './types';

export interface CharacterSvgDefsProps {
  uid: string;
  palette: MonochromePalette;
}

export const CharacterSvgDefs: React.FC<CharacterSvgDefsProps> = ({ uid, palette }) => (
  <defs>
    {/* Main Pear Plush Body 3D Radial Gradient */}
    <radialGradient id={`${uid}-body-grad`} cx="44%" cy="32%" r="65%" fx="38%" fy="25%">
      <stop offset="0%" stopColor={palette.suitLight} />
      <stop offset="52%" stopColor={palette.suitMid} />
      <stop offset="86%" stopColor={palette.suitShadow} />
      <stop offset="100%" stopColor={palette.suitDeepShadow} />
    </radialGradient>

    {/* Limb Left Shading Gradient */}
    <linearGradient id={`${uid}-limb-left`} x1="15%" y1="10%" x2="85%" y2="90%">
      <stop offset="0%" stopColor={palette.suitLight} />
      <stop offset="55%" stopColor={palette.suitMid} />
      <stop offset="100%" stopColor={palette.suitShadow} />
    </linearGradient>

    {/* Limb Right Shading Gradient */}
    <linearGradient id={`${uid}-limb-right`} x1="85%" y1="10%" x2="15%" y2="90%">
      <stop offset="0%" stopColor={palette.suitLight} />
      <stop offset="55%" stopColor={palette.suitMid} />
      <stop offset="100%" stopColor={palette.suitShadow} />
    </linearGradient>

    {/* Leg Gradient with Crease Shadow */}
    <linearGradient id={`${uid}-leg-grad`} x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stopColor={palette.suitDeepShadow} />
      <stop offset="22%" stopColor={palette.suitShadow} />
      <stop offset="68%" stopColor={palette.suitMid} />
      <stop offset="100%" stopColor={palette.suitShadow} />
    </linearGradient>

    {/* Recessed Hood Rim Bevel Gradient */}
    <linearGradient id={`${uid}-hood-rim`} x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stopColor={palette.hoodInnerShadow} />
      <stop offset="35%" stopColor={palette.suitShadow} />
      <stop offset="100%" stopColor={palette.suitLight} />
    </linearGradient>

    {/* Smooth Matte Face Surface Gradient */}
    <radialGradient id={`${uid}-face-grad`} cx="50%" cy="38%" r="60%" fx="46%" fy="30%">
      <stop offset="0%" stopColor={palette.faceLight} />
      <stop offset="70%" stopColor={palette.faceMid} />
      <stop offset="100%" stopColor={palette.faceShadow} />
    </radialGradient>

    {/* Soft Monochrome Cheek Blush Radial Gradient */}
    <radialGradient id={`${uid}-cheek-grad`} cx="50%" cy="50%" r="50%">
      <stop offset="0%" stopColor={palette.cheekGlow} stopOpacity="0.65" />
      <stop offset="60%" stopColor={palette.cheekGlow} stopOpacity="0.25" />
      <stop offset="100%" stopColor={palette.cheekGlow} stopOpacity="0" />
    </radialGradient>

    {/* Belly Plush Highlight */}
    <radialGradient id={`${uid}-belly-sheen`} cx="50%" cy="42%" r="48%">
      <stop offset="0%" stopColor={palette.suitRim} stopOpacity="0.55" />
      <stop offset="100%" stopColor={palette.suitRim} stopOpacity="0" />
    </radialGradient>

    {/* Soft Ground Contact Shadow */}
    <radialGradient id={`${uid}-ground-shadow`} cx="50%" cy="50%" r="50%">
      <stop offset="0%" stopColor={palette.suitDeepShadow} stopOpacity="0.45" />
      <stop offset="65%" stopColor={palette.suitDeepShadow} stopOpacity="0.18" />
      <stop offset="100%" stopColor={palette.suitDeepShadow} stopOpacity="0" />
    </radialGradient>

    {/* Prop / Mug / Heart Gradient */}
    <linearGradient id={`${uid}-prop-grad`} x1="20%" y1="15%" x2="85%" y2="90%">
      <stop offset="0%" stopColor={palette.faceLight} />
      <stop offset="60%" stopColor={palette.suitMid} />
      <stop offset="100%" stopColor={palette.suitDeepShadow} />
    </linearGradient>
  </defs>
);
