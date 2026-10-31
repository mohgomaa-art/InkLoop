import React, { useMemo } from 'react';
import type { EditorLayerDto } from '../../api/client';

export type BubbleShape =
  | 'oval'
  | 'rounded_rectangle'
  | 'thought_cloud'
  | 'shout_burst'
  | 'explosive_blast'
  | 'fear_tremble'
  | 'affection_heart'
  | 'splat_surprise'
  | 'electric_robotic'
  | 'tilted_banner'
  | 'speedline_aura'
  | 'connected_lobes'
  | 'radio_broadcast_zigzag'
  | 'folded_ribbon_3d'
  | 'dark_aura_ghost'
  | 'icicle_frost'
  | 'whisper_cloud_soft'
  | 'double_border_impact'
  | 'droplet_tear_sad'
  | 'glitch_digital_crt'
  | 'scalloped_flower'
  | 'spiky_ring_scream'
  | 'heavy_weight_emphasis'
  | 'none';

export type TailType =
  | 'smooth_pointer'
  | 'lightning_bolt'
  | 'bubble_chain'
  | 'whisper_dashed'
  | 'smoke_puff'
  | 'dual_pointer'
  | 'off_screen_pointer'
  | 'curved_hook_tail'
  | 'zigzag_antenna'
  | 'none';

export type BubbleAccent =
  | 'none'
  | 'speedline_needles'
  | 'sparkles'
  | 'sweat_drop'
  | 'shock_marks'
  | 'anger_vein_cross'
  | 'heart_flutter'
  | 'dizziness_swirl'
  | 'electric_sparks';

const bubbleNoise = (seed: string, index: number): number => {
  let hash = 2166136261;
  const value = `${seed}:${index}`;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 0xffffffff;
};

interface SpeechBubbleSvgProps {
  layer: EditorLayerDto;
  isSelected: boolean;
  zoom: number;
  onPointerDownTailHandle?: (e: React.PointerEvent, layerId: string) => void;
}

export const SpeechBubbleSvg: React.FC<SpeechBubbleSvgProps> = ({
  layer,
  isSelected,
  zoom,
  onPointerDownTailHandle,
}) => {
  const m = layer.metadata as Record<string, any>;
  const shape = (m.bubble_shape as BubbleShape) || 'oval';
  const tailType = (m.tail_type as TailType) || 'smooth_pointer';
  const accent = (m.accent as BubbleAccent) || (m.accents as BubbleAccent) || 'none';
  const halftoneShadow = Boolean(m.halftone_shadow || m.has_halftone_shadow);
  const isInverted = Boolean(m.inverted_dark_mode) || shape === 'dark_aura_ghost';

  const x = Number(m.x || 0);
  const y = Number(m.y || 0);
  const width = Math.max(40, Number(m.width || 240));
  const height = Math.max(30, Number(m.height || 140));
  const fontSize = Number(m.font_size || 24);
  const strokeWidth = Number(m.stroke_width || m.border_width || 2.5);
  const geometryIsCurrent = Number(m.bubble_geometry_version || 0) >= 2;
  const organicSeed = String(m.bubble_id || layer.layer_id);
  const unifiedPath = (typeof m.unified_path === 'string' && m.unified_path.startsWith('M')) ? m.unified_path : null;

  const defaultFill = isInverted ? '#111111' : '#FFFFFF';
  const defaultStroke = isInverted ? '#FFFFFF' : '#111111';
  const defaultText = isInverted ? '#FFFFFF' : '#111111';

  const strokeColor = String(m.border_color || m.bubble_stroke || defaultStroke);
  const fillColor = String(m.bg_color || m.bubble_fill || defaultFill);
  const textColor = String(m.color || defaultText);
  const textValue = String(m.text || '');
  const textDirection = m.direction === 'rtl' || m.direction === 'ltr'
    ? m.direction
    : /[\u0590-\u08ff\ufb1d-\ufefc]/u.test(textValue) ? 'rtl' : 'ltr';
  const strokeDash = String(m.stroke_dash || (shape === 'whisper_cloud_soft' || tailType === 'whisper_dashed' ? '5 4' : ''));

  const padX = Number(m.padding_x || 24);
  const padY = Number(m.padding_y || 18);

  const cx = x + width / 2;
  const cy = y + height / 2;
  const rx = width / 2;
  const ry = height / 2;
  const organicTurn = (bubbleNoise(organicSeed, 97) - 0.5) * 1.2;
  const organicScale = 0.994 + bubbleNoise(organicSeed, 98) * 0.012;
  const organicPathTransform = `translate(${cx} ${cy}) rotate(${organicTurn.toFixed(2)}) scale(${organicScale.toFixed(4)}) translate(${-cx} ${-cy})`;

  // Tail tip position
  const tipX = Number(m.tail_target?.x ?? m.tail_tip_x ?? (cx - rx * 0.3));
  const tipY = Number(m.tail_target?.y ?? m.tail_tip_y ?? (y + height + 50));

  // Compute or reuse bubble path
  const bubblePath = useMemo(() => {
    if (shape === 'none') return '';
    if (geometryIsCurrent && m.svg_path && typeof m.svg_path === 'string' && m.svg_path.startsWith('M')) {
      const bakedW = m._baked_width ?? (m.scale_factor && m.scale_factor !== 1 ? -1 : width);
      const bakedH = m._baked_height ?? (m.scale_factor && m.scale_factor !== 1 ? -1 : height);
      if (bakedW === width && bakedH === height) {
        return m.svg_path;
      }
    }

    if (shape === 'oval') {
      const points = Array.from({ length: 16 }, (_, i) => {
        const angle = (2 * Math.PI * i) / 16;
        const radius = 1 + (bubbleNoise(organicSeed, i) - 0.5) * 0.035;
        return [cx + rx * radius * Math.cos(angle), cy + ry * radius * Math.sin(angle)] as [number, number];
      });
      let d = `M ${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
      for (let i = 0; i < points.length; i++) {
        const p = points[i];
        const prev = points[(i - 1 + points.length) % points.length];
        const next = points[(i + 1) % points.length];
        const after = points[(i + 2) % points.length];
        d += ` C ${(p[0] + (next[0] - prev[0]) / 6).toFixed(1)} ${(p[1] + (next[1] - prev[1]) / 6).toFixed(1)} ${(next[0] - (after[0] - p[0]) / 6).toFixed(1)} ${(next[1] - (after[1] - p[1]) / 6).toFixed(1)} ${next[0].toFixed(1)} ${next[1].toFixed(1)}`;
      }
      return d + ' Z';
    }

    if (shape === 'rounded_rectangle') {
      const rad = Math.min(22, width / 4, height / 4);
      return `M ${x + rad} ${y} H ${x + width - rad} A ${rad} ${rad} 0 0 1 ${x + width} ${y + rad} V ${y + height - rad} A ${rad} ${rad} 0 0 1 ${x + width - rad} ${y + height} H ${x + rad} A ${rad} ${rad} 0 0 1 ${x} ${y + height - rad} V ${y + rad} A ${rad} ${rad} 0 0 1 ${x + rad} ${y} Z`;
    }

    if (shape === 'thought_cloud' || shape === 'whisper_cloud_soft') {
      const numLobes = shape === 'whisper_cloud_soft' ? 14 : 10;
      const pts: [number, number][] = [];
      for (let i = 0; i < numLobes; i++) {
        const ang = (2 * Math.PI * i) / numLobes;
        const organic = 1 + (bubbleNoise(organicSeed, i) - 0.5) * 0.10;
        pts.push([cx + rx * organic * Math.cos(ang), cy + ry * organic * Math.sin(ang)]);
      }
      const lobeR = Math.min(rx, ry) * (shape === 'whisper_cloud_soft' ? 0.32 : 0.42);
      let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
      for (let i = 0; i < numLobes; i++) {
        const next = pts[(i + 1) % numLobes];
        d += ` A ${lobeR.toFixed(1)} ${lobeR.toFixed(1)} 0 0 1 ${next[0].toFixed(1)} ${next[1].toFixed(1)}`;
      }
      return d + ' Z';
    }

    if (shape === 'shout_burst') {
      const numPeaks = 16;
      let d = '';
      for (let i = 0; i < numPeaks * 2; i++) {
        const ang = (Math.PI * i) / numPeaks;
        const isPeak = i % 2 === 1;
        const sc = isPeak ? 1.18 : 0.84;
        const px = cx + rx * Math.cos(ang) * sc;
        const py = cy + ry * Math.sin(ang) * sc;
        d += `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)} `;
      }
      return d + 'Z';
    }

    if (shape === 'explosive_blast' || shape === 'spiky_ring_scream') {
      const numSpikes = shape === 'spiky_ring_scream' ? 22 : 14;
      let d = '';
      for (let i = 0; i < numSpikes * 2; i++) {
        const ang = (Math.PI * i) / numSpikes;
        const isPeak = i % 2 === 1;
        const factor = isPeak ? (shape === 'spiky_ring_scream' ? 1.38 : 1.28 + 0.15 * Math.sin(i * 1.7)) : 0.72;
        const px = cx + rx * Math.cos(ang) * factor;
        const py = cy + ry * Math.sin(ang) * factor;
        d += `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)} `;
      }
      return d + 'Z';
    }

    if (shape === 'fear_tremble') {
      const numSteps = 36;
      let d = '';
      for (let i = 0; i < numSteps; i++) {
        const ang = (2 * Math.PI * i) / numSteps;
        const jitter = 1 + 0.06 * Math.sin(ang * 12) + 0.04 * Math.cos(ang * 7);
        const px = cx + rx * Math.cos(ang) * jitter;
        const py = cy + ry * Math.sin(ang) * jitter;
        d += `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)} `;
      }
      return d + 'Z';
    }

    if (shape === 'affection_heart') {
      const topY = y + height * 0.2;
      const botY = y + height;
      return `M ${cx} ${botY} C ${x - rx * 0.1} ${cy + ry * 0.4} ${x} ${y + ry * 0.2} ${x + rx * 0.5} ${y} C ${cx - rx * 0.1} ${y} ${cx} ${topY - 8} ${cx} ${topY} C ${cx} ${topY - 8} ${cx + rx * 0.1} ${y} ${x + width - rx * 0.5} ${y} C ${x + width} ${y + ry * 0.2} ${x + width + rx * 0.1} ${cy + ry * 0.4} ${cx} ${botY} Z`;
    }

    if (shape === 'splat_surprise') {
      const numLobes = 12;
      let d = '';
      for (let i = 0; i < numLobes; i++) {
        const ang = (2 * Math.PI * i) / numLobes;
        const drip = 1 + 0.22 * Math.sin(ang * 4) + (i === 3 || i === 6 || i === 9 ? 0.18 : 0);
        const px = cx + rx * Math.cos(ang) * drip;
        const py = cy + ry * Math.sin(ang) * drip;
        d += `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)} `;
      }
      return d + 'Z';
    }

    if (shape === 'electric_robotic') {
      const cut = Math.min(18, width / 5, height / 5);
      return `M ${x + cut} ${y} L ${x + width - cut} ${y} L ${x + width} ${y + cut} L ${x + width} ${y + height - cut} L ${x + width - cut} ${y + height} L ${x + cut} ${y + height} L ${x} ${y + height - cut} L ${x} ${y + cut} Z`;
    }

    if (shape === 'tilted_banner' || shape === 'folded_ribbon_3d') {
      const skew = Math.min(20, width * 0.08);
      return `M ${x + skew} ${y} L ${x + width} ${y} L ${x + width - skew} ${y + height} L ${x} ${y + height} Z`;
    }

    if (shape === 'radio_broadcast_zigzag') {
      const steps = 18;
      let d = `M ${x} ${y + 12}`;
      for (let i = 0; i <= steps; i++) {
        const segX = x + (width * i) / steps;
        const segY = y + (i % 2 === 0 ? 0 : 7);
        d += ` L ${segX.toFixed(1)} ${segY.toFixed(1)}`;
      }
      d += ` L ${x + width} ${y + height - 12}`;
      for (let i = steps; i >= 0; i--) {
        const segX = x + (width * i) / steps;
        const segY = y + height - (i % 2 === 0 ? 0 : 7);
        d += ` L ${segX.toFixed(1)} ${segY.toFixed(1)}`;
      }
      return d + ' Z';
    }

    if (shape === 'dark_aura_ghost') {
      const steps = 28;
      let d = '';
      for (let i = 0; i < steps; i++) {
        const ang = (2 * Math.PI * i) / steps;
        const flame = 1 + 0.16 * Math.sin(ang * 6) + (Math.sin(ang) < 0 ? 0.22 * Math.abs(Math.sin(ang * 3)) : -0.05);
        const px = cx + rx * Math.cos(ang) * flame;
        const py = cy + ry * Math.sin(ang) * flame;
        d += `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)} `;
      }
      return d + 'Z';
    }

    if (shape === 'icicle_frost') {
      const rad = 14;
      let d = `M ${x + rad} ${y} H ${x + width - rad} A ${rad} ${rad} 0 0 1 ${x + width} ${y + rad} V ${y + height * 0.7}`;
      const numIcicles = 7;
      for (let i = numIcicles; i >= 0; i--) {
        const icX = x + (width * i) / numIcicles;
        const tipLen = (i % 2 === 1 ? 26 : 14);
        d += ` L ${(icX + 6).toFixed(1)} ${(y + height * 0.7).toFixed(1)} L ${icX.toFixed(1)} ${(y + height + tipLen).toFixed(1)} L ${(icX - 6).toFixed(1)} ${(y + height * 0.7).toFixed(1)}`;
      }
      d += ` V ${y + rad} A ${rad} ${rad} 0 0 1 ${x + rad} ${y} Z`;
      return d;
    }

    if (shape === 'glitch_digital_crt') {
      return `M ${x + 6} ${y} H ${x + width * 0.4} V ${y + 4} H ${x + width * 0.46} V ${y} H ${x + width - 14} L ${x + width} ${y + 14} V ${y + height * 0.6} H ${x + width - 6} V ${y + height * 0.68} H ${x + width} V ${y + height - 10} L ${x + width - 10} ${y + height} H ${x + width * 0.55} V ${y + height - 4} H ${x + width * 0.48} V ${y + height} H ${x + 14} L ${x} ${y + height - 14} V ${y + height * 0.3} H ${x + 5} V ${y + height * 0.22} H ${x} V ${y + 10} Z`;
    }

    if (shape === 'droplet_tear_sad') {
      return `M ${cx} ${y + 6} C ${cx + rx * 0.8} ${y + ry * 0.5} ${x + width} ${cy + ry * 0.4} ${x + width - 12} ${y + height - 14} C ${cx + rx * 0.7} ${y + height + 8} ${cx - rx * 0.7} ${y + height + 8} ${x + 12} ${y + height - 14} C ${x} ${cy + ry * 0.4} ${cx - rx * 0.8} ${y + ry * 0.5} ${cx} ${y + 6} Z`;
    }

    if (shape === 'scalloped_flower') {
      const petals = 12;
      let d = '';
      for (let i = 0; i < petals; i++) {
        const a1 = (2 * Math.PI * i) / petals;
        const a2 = (2 * Math.PI * (i + 1)) / petals;
        const amid = (a1 + a2) / 2;
        const p1x = cx + rx * Math.cos(a1);
        const p1y = cy + ry * Math.sin(a1);
        const p2x = cx + rx * Math.cos(a2);
        const p2y = cy + ry * Math.sin(a2);
        const cpx = cx + rx * 1.25 * Math.cos(amid);
        const cpy = cy + ry * 1.25 * Math.sin(amid);
        if (i === 0) d += `M ${p1x.toFixed(1)} ${p1y.toFixed(1)}`;
        d += ` Q ${cpx.toFixed(1)} ${cpy.toFixed(1)} ${p2x.toFixed(1)} ${p2y.toFixed(1)}`;
      }
      return d + ' Z';
    }

    if (shape === 'heavy_weight_emphasis') {
      const rad = Math.min(26, height / 2);
      return `M ${x + rad} ${y} H ${x + width - rad} A ${rad} ${rad} 0 0 1 ${x + width} ${y + rad} V ${y + height - rad} A ${rad} ${rad} 0 0 1 ${x + width - rad} ${y + height} H ${x + rad} A ${rad} ${rad} 0 0 1 ${x} ${y + height - rad} V ${y + rad} A ${rad} ${rad} 0 0 1 ${x + rad} ${y} Z`;
    }

    return `M ${x} ${y} H ${x + width} V ${y + height} H ${x} Z`;
  }, [shape, m.svg_path, geometryIsCurrent, organicSeed, x, y, width, height, cx, cy, rx, ry]);

  // Secondary tail for dual pointer / chorus
  const secondaryTailPath = m.secondary_tail_path || '';
  const doubleStrokePath = m.double_stroke_path || '';
  const ribbonFoldPaths = Array.isArray(m.ribbon_fold_paths) ? m.ribbon_fold_paths : [];

  // Compute primary tail path or chain circles
  const { tailPath, chainCircles } = useMemo(() => {
    if (shape === 'none' || tailType === 'none') {
      return { tailPath: '', chainCircles: [] };
    }

    if (geometryIsCurrent && m.tail_path && typeof m.tail_path === 'string') {
      const bakedW = m._baked_width ?? (m.scale_factor && m.scale_factor !== 1 ? -1 : width);
      const bakedH = m._baked_height ?? (m.scale_factor && m.scale_factor !== 1 ? -1 : height);
      if (bakedW === width && bakedH === height) {
        return { tailPath: m.tail_path, chainCircles: m.tail_chain_circles || [] };
      }
    }

    let dx = tipX - cx;
    let dy = tipY - cy;
    let dist = Math.hypot(dx, dy);
    if (dist < 1e-4) {
      dx = 0;
      dy = 1;
      dist = 1;
    }
    const ux = dx / dist;
    const uy = dy / dist;

    const boundaryScale = 1 / Math.sqrt((ux / Math.max(rx, 1e-6)) ** 2 + (uy / Math.max(ry, 1e-6)) ** 2);
    const bx = cx + ux * boundaryScale * 0.82;
    const by = cy + uy * boundaryScale * 0.82;

    const tx = -uy;
    const ty = ux;
    const baseW = 14;

    const p1x = bx + tx * baseW;
    const p1y = by + ty * baseW;
    const p2x = bx - tx * baseW;
    const p2y = by - ty * baseW;

    if (tailType === 'bubble_chain') {
      const circles: [number, number, number][] = [
        [bx + (tipX - bx) * 0.25, by + (tipY - by) * 0.25, 11],
        [bx + (tipX - bx) * 0.55, by + (tipY - by) * 0.55, 7.5],
        [bx + (tipX - bx) * 0.85, by + (tipY - by) * 0.85, 4.5],
      ];
      return { tailPath: '', chainCircles: circles };
    }

    if (tailType === 'lightning_bolt') {
      const k1x = bx + (tipX - bx) * 0.35 + tx * 16;
      const k1y = by + (tipY - by) * 0.35 + ty * 16;
      const k2x = bx + (tipX - bx) * 0.7 - tx * 12;
      const k2y = by + (tipY - by) * 0.7 - ty * 12;
      const p = `M ${p1x.toFixed(1)} ${p1y.toFixed(1)} L ${k1x.toFixed(1)} ${k1y.toFixed(1)} L ${k2x.toFixed(1)} ${k2y.toFixed(1)} L ${tipX.toFixed(1)} ${tipY.toFixed(1)} L ${(k2x + tx * 4).toFixed(1)} ${(k2y + ty * 4).toFixed(1)} L ${p2x.toFixed(1)} ${p2y.toFixed(1)} Z`;
      return { tailPath: p, chainCircles: [] };
    }

    if (tailType === 'zigzag_antenna') {
      const k1x = bx + (tipX - bx) * 0.25 + tx * 14;
      const k1y = by + (tipY - by) * 0.25 + ty * 14;
      const k2x = bx + (tipX - bx) * 0.55 - tx * 14;
      const k2y = by + (tipY - by) * 0.55 - ty * 14;
      const k3x = bx + (tipX - bx) * 0.8 + tx * 10;
      const k3y = by + (tipY - by) * 0.8 + ty * 10;
      const p = `M ${p1x.toFixed(1)} ${p1y.toFixed(1)} L ${k1x.toFixed(1)} ${k1y.toFixed(1)} L ${k2x.toFixed(1)} ${k2y.toFixed(1)} L ${k3x.toFixed(1)} ${k3y.toFixed(1)} L ${tipX.toFixed(1)} ${tipY.toFixed(1)} L ${(k3x - tx * 3).toFixed(1)} ${(k3y - ty * 3).toFixed(1)} L ${(k2x + tx * 3).toFixed(1)} ${(k2y + ty * 3).toFixed(1)} L ${(k1x - tx * 3).toFixed(1)} ${(k1y - ty * 3).toFixed(1)} L ${p2x.toFixed(1)} ${p2y.toFixed(1)} Z`;
      return { tailPath: p, chainCircles: [] };
    }

    if (tailType === 'curved_hook_tail') {
      const hookCtrlX = bx + (tipX - bx) * 0.3 + tx * 32;
      const hookCtrlY = by + (tipY - by) * 0.3 + ty * 32;
      const p = `M ${p1x.toFixed(1)} ${p1y.toFixed(1)} Q ${hookCtrlX.toFixed(1)} ${hookCtrlY.toFixed(1)} ${tipX.toFixed(1)} ${tipY.toFixed(1)} Q ${(hookCtrlX - tx * 8).toFixed(1)} ${(hookCtrlY - ty * 8).toFixed(1)} ${p2x.toFixed(1)} ${p2y.toFixed(1)} Z`;
      return { tailPath: p, chainCircles: [] };
    }

    if (tailType === 'off_screen_pointer') {
      const farTipX = bx + (tipX - bx) * 1.6;
      const farTipY = by + (tipY - by) * 1.6;
      const p = `M ${p1x.toFixed(1)} ${p1y.toFixed(1)} L ${farTipX.toFixed(1)} ${farTipY.toFixed(1)} L ${p2x.toFixed(1)} ${p2y.toFixed(1)} Z`;
      return { tailPath: p, chainCircles: [] };
    }

    if (tailType === 'whisper_dashed') {
      const p = `M ${p1x.toFixed(1)} ${p1y.toFixed(1)} L ${tipX.toFixed(1)} ${tipY.toFixed(1)} L ${p2x.toFixed(1)} ${p2y.toFixed(1)} Z`;
      return { tailPath: p, chainCircles: [] };
    }

    // Default smooth horn
    const ctrlX = bx + (tipX - bx) * 0.45 + tx * 8;
    const ctrlY = by + (tipY - by) * 0.45 + ty * 8;
    const p = `M ${p1x.toFixed(1)} ${p1y.toFixed(1)} Q ${ctrlX.toFixed(1)} ${ctrlY.toFixed(1)} ${tipX.toFixed(1)} ${tipY.toFixed(1)} Q ${bx.toFixed(1)} ${by.toFixed(1)} ${p2x.toFixed(1)} ${p2y.toFixed(1)} Z`;
    return { tailPath: p, chainCircles: [] };
  }, [shape, tailType, m.tail_path, m.tail_chain_circles, geometryIsCurrent, cx, cy, rx, ry, tipX, tipY]);

  // Compute accents
  const accentElements = useMemo(() => {
    // If backend provided pre-computed accent paths, render them!
    if (Array.isArray(m.accent_paths) && m.accent_paths.length > 0) {
      return m.accent_paths.map((pth: string, idx: number) => (
        <path key={`acc-path-${idx}`} d={pth} stroke={strokeColor} strokeWidth={strokeWidth} fill="none" strokeLinecap="round" />
      ));
    }

    if (accent === 'speedline_needles' || shape === 'explosive_blast') {
      const needles: React.ReactNode[] = [];
      const count = 8;
      for (let i = 0; i < count; i++) {
        const ang = (2 * Math.PI * i) / count;
        const sx = cx + rx * Math.cos(ang) * 1.35;
        const sy = cy + ry * Math.sin(ang) * 1.35;
        const ex = cx + rx * Math.cos(ang) * 1.75;
        const ey = cy + ry * Math.sin(ang) * 1.75;
        needles.push(
          <line
            key={`needle-${i}`}
            x1={sx}
            y1={sy}
            x2={ex}
            y2={ey}
            stroke={strokeColor}
            strokeWidth={2}
            strokeLinecap="round"
          />
        );
      }
      return needles;
    }

    if (accent === 'anger_vein_cross') {
      const ax = x + width - 6;
      const ay = y - 6;
      return (
        <g key="anger-cross" stroke="#E11D48" strokeWidth={3} strokeLinecap="round" fill="none">
          <path d={`M ${ax - 10} ${ay - 5} C ${ax - 5} ${ay - 1} ${ax - 5} ${ay + 1} ${ax - 10} ${ay + 5}`} />
          <path d={`M ${ax + 10} ${ay - 5} C ${ax + 5} ${ay - 1} ${ax + 5} ${ay + 1} ${ax + 10} ${ay + 5}`} />
          <path d={`M ${ax - 5} ${ay - 10} C ${ax - 1} ${ay - 5} ${ax + 1} ${ay - 5} ${ax + 5} ${ay - 10}`} />
          <path d={`M ${ax - 5} ${ay + 10} C ${ax - 1} ${ay + 5} ${ax + 1} ${ay + 5} ${ax + 5} ${ay + 10}`} />
        </g>
      );
    }

    if (accent === 'shock_marks') {
      const sx = x + width + 4;
      const sy = y - 10;
      return (
        <g key="shock-marks" stroke={strokeColor} strokeWidth={2.5} strokeLinecap="round">
          <line x1={sx} y1={sy} x2={sx + 8} y2={sy - 12} />
          <line x1={sx + 10} y1={sy + 2} x2={sx + 22} y2={sy - 6} />
          <line x1={sx + 14} y1={sy + 14} x2={sx + 28} y2={sy + 10} />
        </g>
      );
    }

    if (accent === 'electric_sparks') {
      const ex = x - 12;
      const ey = y - 8;
      const d = `M ${ex} ${ey} L ${ex + 8} ${ey + 12} L ${ex + 3} ${ey + 13} L ${ex + 12} ${ey + 26}`;
      return [<path key="elec-1" d={d} stroke="#EAB308" strokeWidth={2.5} fill="none" strokeLinecap="round" />];
    }

    if (accent === 'sparkles' || shape === 'affection_heart') {
      const spX = x + width + 10;
      const spY = y - 10;
      const d = `M ${spX} ${spY - 10} Q ${spX} ${spY} ${spX + 10} ${spY} Q ${spX} ${spY} ${spX} ${spY + 10} Q ${spX} ${spY} ${spX - 10} ${spY} Q ${spX} ${spY} ${spX} ${spY - 10} Z`;
      return [<path key="sparkle-1" d={d} fill={strokeColor} />];
    }

    if (accent === 'sweat_drop' || shape === 'fear_tremble') {
      const swX = x + width + 8;
      const swY = y + 8;
      const d = `M ${swX} ${swY - 12} Q ${swX + 7} ${swY} ${swX} ${swY + 8} Q ${swX - 7} ${swY} ${swX} ${swY - 12} Z`;
      return [<path key="sweat-1" d={d} fill="#4AA3DF" stroke={strokeColor} strokeWidth={1.5} />];
    }

    return [];
  }, [accent, shape, m.accent_paths, cx, cy, rx, ry, x, y, width, strokeColor, strokeWidth]);

  // Text bounding box inset
  const textX = x + padX;
  const textY = y + padY;
  const textW = Math.max(10, width - padX * 2);
  const textH = Math.max(10, height - padY * 2);

  const alignment =
    m.align === 'center'
      ? 'center'
      : m.align === 'right'
      ? 'flex-end'
      : 'flex-start';

  const rotationDeg = Number(m.rotation_deg || 0);
  const flipH = Boolean(m.flip_h);
  const flipV = Boolean(m.flip_v);
  const scaleX = flipH ? -1 : 1;
  const scaleY = flipV ? -1 : 1;
  const transformAttr =
    rotationDeg !== 0 || flipH || flipV
      ? `translate(${cx}, ${cy}) rotate(${rotationDeg}) scale(${scaleX}, ${scaleY}) translate(${-cx}, ${-cy})`
      : undefined;

  return (
    <g className="speech-bubble-layer" data-layer-id={layer.layer_id} transform={transformAttr}>
      {/* 1. Manga Halftone Screentone Drop Shadow */}
      {halftoneShadow && (unifiedPath || bubblePath) && (
        <g transform="translate(10, 12)">
          {unifiedPath ? (
            <path d={unifiedPath} fill="url(#manga-halftone-pattern)" />
          ) : (
            <>
              {bubblePath && <path d={bubblePath} transform={organicPathTransform} fill="url(#manga-halftone-pattern)" />}
              {tailPath && <path d={tailPath} fill="url(#manga-halftone-pattern)" />}
            </>
          )}
        </g>
      )}

      {/* 2a. 3D Ribbon Folds & Shadows */}
      {ribbonFoldPaths.map((foldD: string, idx: number) => (
        <path
          key={`ribbon-fold-${idx}`}
          d={foldD}
          fill={idx % 2 === 1 ? '#D4D4D8' : fillColor}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinejoin="round"
        />
      ))}

      {/* 2b. Secondary Tail (Dual Pointer / Chorus) */}
      {secondaryTailPath && (
        <path
          d={secondaryTailPath}
          fill={fillColor}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}

      {/* 2c. Primary Bubble Tail (rendered separately only when unifiedPath is absent) */}
      {!unifiedPath && tailPath && (
        <path
          d={tailPath}
          fill={fillColor}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDash || (tailType === 'whisper_dashed' ? '5 4' : undefined)}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}

      {/* 3. Thought Chain Circles */}
      {(chainCircles as [number, number, number][]).map(([ccx, ccy, crad]: [number, number, number], idx: number) => (
        <circle
          key={`chain-${idx}`}
          cx={ccx}
          cy={ccy}
          r={crad}
          fill={fillColor}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
        />
      ))}

      {/* 4. Main Bubble Outline & Fill (Unified vector if present, or procedural outline) */}
      {unifiedPath ? (
        <path
          d={unifiedPath}
          fill={fillColor}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDash || undefined}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ) : bubblePath ? (
        <path
          d={bubblePath}
          transform={organicPathTransform}
          fill={fillColor}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDash || undefined}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ) : null}

      {/* 4b. Concentric Double Stroke for DOUBLE_BORDER_IMPACT */}
      {doubleStrokePath && (
        <path
          d={doubleStrokePath}
          fill="none"
          stroke={strokeColor}
          strokeWidth={Math.max(1.5, strokeWidth * 0.7)}
          strokeLinejoin="round"
        />
      )}

      {/* 5. Accents (Needles, Sparkles, Sweat drops, Anger Cross, Sparks) */}
      {accentElements}

      {/* 6. Enclosed Text Block */}
      <foreignObject x={textX} y={textY} width={textW} height={textH}>
        <div
          style={{
            width: '100%',
            height: '100%',
            boxSizing: 'border-box',
            overflow: 'hidden',
            color: textColor,
            fontFamily: String(m.font_family || (shape === 'shout_burst' || shape === 'explosive_blast' ? 'Bangers' : 'Comic Neue')) + ", 'Noto Sans Arabic', sans-serif",
            fontSize,
            fontWeight: m.font_weight || 'normal',
            lineHeight: Number(m.line_height || 1.25),
            textAlign: String(m.align || 'center') as any,
            direction: textDirection,
            unicodeBidi: 'plaintext',
            whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere',
            display: 'flex',
            alignItems: 'center',
            justifyContent: alignment,
          }}
        >
          {textValue}
        </div>
      </foreignObject>

      {/* 7. Interactive Tail Tip Handle (Only when text layer is selected) */}
      {isSelected && tailType !== 'none' && shape !== 'none' && (
        <g className="tail-handle-group">
          <line
            x1={cx}
            y1={cy}
            x2={tipX}
            y2={tipY}
            stroke="#3B82F6"
            strokeWidth={1.5 / zoom}
            strokeDasharray="4 4"
            opacity={0.6}
          />
          <circle
            cx={tipX}
            cy={tipY}
            r={7 / zoom}
            fill="#3B82F6"
            stroke="#FFFFFF"
            strokeWidth={2 / zoom}
            style={{ cursor: 'crosshair' }}
            onPointerDown={(e) => onPointerDownTailHandle?.(e, layer.layer_id)}
          />
        </g>
      )}
    </g>
  );
};
