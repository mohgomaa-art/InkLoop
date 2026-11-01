import React, { useRef, useState } from 'react';

export interface TransformGizmoProps {
  x: number;
  y: number;
  width: number;
  height: number;
  rotationDeg?: number;
  scaleX?: number;
  scaleY?: number;
  zoom: number;
  flipH?: boolean;
  flipV?: boolean;
  disableBodyDrag?: boolean;
  onTranslate?: (dx: number, dy: number, isFinal: boolean) => void;
  onScale?: (scaleMultiplier: number, isFinal: boolean) => void;
  onRotate?: (newRotationDeg: number, isFinal: boolean) => void;
  toDocPoint: (e: React.PointerEvent) => { x: number; y: number };
}

export const TransformGizmo: React.FC<TransformGizmoProps> = ({
  x,
  y,
  width,
  height,
  rotationDeg = 0,
  scaleX = 1,
  scaleY = 1,
  zoom,
  flipH = false,
  flipV = false,
  disableBodyDrag = false,
  onTranslate,
  onScale,
  onRotate,
  toDocPoint,
}) => {
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);

  const interactionRef = useRef<{
    action: 'move' | 'rotate' | 'scale_corner';
    corner?: 'nw' | 'ne' | 'se' | 'sw';
    startDoc: { x: number; y: number };
    startRotation: number;
    startScale: number;
    currentScale?: number;
    center: { x: number; y: number };
    initDist: number;
  } | null>(null);

  const cx = x + width / 2;
  const cy = y + height / 2;
  const stemHeight = 28 / zoom;
  const handleRadius = 6 / zoom;
  const stemY = y - stemHeight;

  // Handle pointer down on rotation knob
  const handleRotationPointerDown = (e: React.PointerEvent) => {
    e.stopPropagation();
    const docP = toDocPoint(e);
    interactionRef.current = {
      action: 'rotate',
      startDoc: docP,
      startRotation: rotationDeg,
      startScale: scaleX,
      center: { x: cx, y: cy },
      initDist: Math.hypot(docP.x - cx, docP.y - cy),
    };
    setActiveAction('rotate');
    setActiveTooltip(`${Math.round(rotationDeg)}°`);
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
  };

  // Handle pointer down on corner scale handle
  const handleScalePointerDown = (e: React.PointerEvent, corner: 'nw' | 'ne' | 'se' | 'sw') => {
    e.stopPropagation();
    const docP = toDocPoint(e);
    const dist = Math.hypot(docP.x - cx, docP.y - cy);
    interactionRef.current = {
      action: 'scale_corner',
      corner,
      startDoc: docP,
      startRotation: rotationDeg,
      startScale: scaleX,
      currentScale: scaleX,
      center: { x: cx, y: cy },
      initDist: Math.max(10, dist),
    };
    setActiveAction('scale');
    setActiveTooltip(`${Math.round(scaleX * 100)}%`);
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
  };

  // Handle pointer down on body to move
  const handleBodyPointerDown = (e: React.PointerEvent) => {
    e.stopPropagation();
    const docP = toDocPoint(e);
    interactionRef.current = {
      action: 'move',
      startDoc: docP,
      startRotation: rotationDeg,
      startScale: scaleX,
      center: { x: cx, y: cy },
      initDist: 0,
    };
    setActiveAction('move');
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!interactionRef.current) return;
    const { action, center, initDist, startRotation, startScale } = interactionRef.current;
    const docP = toDocPoint(e);

    if (action === 'rotate') {
      const rad = Math.atan2(docP.y - center.y, docP.x - center.x);
      let deg = (rad * 180) / Math.PI + 90; // Top is 0 deg
      if (deg < 0) deg += 360;
      if (deg >= 360) deg -= 360;
      // Snap to 15 deg if Shift key pressed
      if (e.shiftKey) {
        deg = Math.round(deg / 15) * 15;
      } else {
        deg = Math.round(deg);
      }
      setActiveTooltip(`${deg}°`);
      onRotate?.(deg, false);
    } else if (action === 'scale_corner') {
      const currentDist = Math.hypot(docP.x - center.x, docP.y - center.y);
      const ratio = currentDist / initDist;
      let newScale = Math.max(0.1, Math.min(10, startScale * ratio));
      if (e.shiftKey) {
        newScale = Math.round(newScale * 10) / 10;
      }
      interactionRef.current.currentScale = newScale;
      setActiveTooltip(`${Math.round(newScale * 100)}%`);
      onScale?.(newScale, false);
    } else if (action === 'move') {
      const dx = docP.x - interactionRef.current.startDoc.x;
      const dy = docP.y - interactionRef.current.startDoc.y;
      onTranslate?.(dx, dy, false);
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!interactionRef.current) return;
    const { action } = interactionRef.current;
    const docP = toDocPoint(e);

    if (action === 'move') {
      const dx = docP.x - interactionRef.current.startDoc.x;
      const dy = docP.y - interactionRef.current.startDoc.y;
      onTranslate?.(dx, dy, true);
    } else if (action === 'rotate') {
      onRotate?.(rotationDeg, true);
    } else if (action === 'scale_corner') {
      const finalScale = interactionRef.current.currentScale ?? scaleX;
      onScale?.(finalScale, true);
    }

    interactionRef.current = null;
    setActiveAction(null);
    setActiveTooltip(null);
  };

  const cornerCursor = (corner: string) => {
    if (corner === 'nw' || corner === 'se') return 'nwse-resize';
    return 'nesw-resize';
  };

  return (
    <g
      className="transform-gizmo-container canvas-raw-manipulation canvas-selection-enter"
      transform={`translate(${cx}, ${cy}) rotate(${rotationDeg}) translate(${-cx}, ${-cy})`}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {/* 1. Transparent bounding box body for dragging */}
      <rect
        data-testid="transform-gizmo-body"
        x={x}
        y={y}
        width={width}
        height={height}
        fill="transparent"
        stroke="#3B82F6"
        strokeWidth={1.5 / zoom}
        strokeDasharray="4 3"
        pointerEvents={disableBodyDrag ? 'none' : undefined}
        style={{ cursor: disableBodyDrag ? 'default' : 'move' }}
        onPointerDown={disableBodyDrag ? undefined : handleBodyPointerDown}
      />

      {/* 2. Top Rotation Stem & Handle Knob */}
      <line
        x1={cx}
        y1={y}
        x2={cx}
        y2={stemY}
        stroke="#3B82F6"
        strokeWidth={1.5 / zoom}
      />
      <circle
        cx={cx}
        cy={stemY}
        r={handleRadius}
        fill="#FFFFFF"
        stroke="#3B82F6"
        strokeWidth={2 / zoom}
        style={{ cursor: 'grab' }}
        onPointerDown={handleRotationPointerDown}
      />

      {/* 3. Corner Proportional Scale Handles */}
      {[
        { corner: 'nw', px: x, py: y },
        { corner: 'ne', px: x + width, py: y },
        { corner: 'se', px: x + width, py: y + height },
        { corner: 'sw', px: x, py: y + height },
      ].map(({ corner, px, py }) => (
        <rect
          key={corner}
          x={px - handleRadius}
          y={py - handleRadius}
          width={handleRadius * 2}
          height={handleRadius * 2}
          fill="#FFFFFF"
          stroke="#3B82F6"
          strokeWidth={2 / zoom}
          style={{ cursor: cornerCursor(corner) }}
          onPointerDown={(e) => handleScalePointerDown(e, corner as any)}
        />
      ))}

      {/* 4. Live Tooltip Readout */}
      {activeTooltip && (
        <g transform={`translate(${cx}, ${stemY - 14 / zoom})`}>
          <rect
            x={-30 / zoom}
            y={-14 / zoom}
            width={60 / zoom}
            height={16 / zoom}
            rx={4 / zoom}
            fill="#1E293B"
            stroke="#475569"
            strokeWidth={1 / zoom}
          />
          <text
            x={0}
            y={-3 / zoom}
            textAnchor="middle"
            fill="#F8FAFC"
            fontSize={9 / zoom}
            fontFamily="monospace"
            fontWeight="bold"
          >
            {activeTooltip}
          </text>
        </g>
      )}
    </g>
  );
};
