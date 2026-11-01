"""Shared Bubble Service implementing the single command & data layer for lettering (B6).

Used by both Agent Capability Registry tools (bubble.add, bubble.update, etc.)
and Canvas API routes. Replaces duplicate implementations across UI and Agent.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from app.canvas.bubble_registry import BUBBLE_TYPE_BY_ID, BUBBLE_TYPES, BubbleTypeSpec
from app.canvas.bubble_vector import BubbleVectorBuilder, UnifiedVectorBubble
from app.canvas.placement_engine import (
    BubblePlacementRequest,
    BubblePlacementResult,
    PlacementEngine,
    PlacementError,
    ProtectedRegion,
)
from app.contracts.geometry import Point, Rect
from app.contracts.identity import IdPrefix, generate_id
from app.editor.models import EditablePageDocument, EditorLayer, LayerKind
from app.text.lettering_layout import LetteringValidationError, count_words, layout_lettering_text


class BubbleServiceError(ValueError):
    """Structured error for bubble operations with actionable diagnostic details."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


class BubbleService:
    """Single implementation of bubble creation, layout, positioning, and updates."""

    def __init__(self):
        self.vector_builder = BubbleVectorBuilder()
        self.placement_engine = PlacementEngine()

    def add_bubble(
        self,
        document: EditablePageDocument,
        panel_id: str,
        type_id: str,
        text: str,
        reading_order: int = 1,
        speaker_character_id: Optional[str] = None,
        speaker: Optional[str] = None,
        bubble_id: Optional[str] = None,
        position: Optional[Dict[str, float]] = None,
        tail_target: Optional[Dict[str, float]] = None,
        font_family: str = "Comic Neue",
        preferred_font_size: Optional[float] = None,
        protected_regions: Optional[Sequence[ProtectedRegion | Rect | Dict[str, Any]]] = None,
        reading_direction: str = "ltr",
        selected_character_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Validate, place, and add a single typed bubble to a page document."""
        slot = document.layout.get_panel(panel_id)
        if slot is None:
            raise BubbleServiceError("ERR_PANEL_NOT_FOUND", f"Panel '{panel_id}' does not exist on page '{document.page_id}'.")

        spec = BUBBLE_TYPE_BY_ID.get(type_id)
        if spec is None:
            allowed_ids = [t.type_id for t in BUBBLE_TYPES]
            raise BubbleServiceError(
                "ERR_BUBBLE_TYPE_INVALID",
                f"Invalid type_id '{type_id}'. Allowed type_ids are: {', '.join(allowed_ids)}. "
                "Example: {'type_id': 'speech.normal', 'text': 'Hello', 'speaker_character_id': 'char_hero'}",
                {"type_id": type_id, "allowed_type_ids": allowed_ids},
            )

        text = str(text or "")
        if not text.strip():
            raise BubbleServiceError(
                "ERR_BUBBLE_TEXT_REQUIRED",
                "Speech bubble text must contain at least one visible character.",
                {"type_id": type_id},
            )

        words = count_words(text)
        if words > spec.word_limit:
            raise BubbleServiceError(
                "ERR_LETTERING_WORD_LIMIT",
                f"{spec.label} allows at most {spec.word_limit} words; received {words}. Shorten the line or split it across multiple bubbles.",
                {"type_id": type_id, "word_count": words, "word_limit": spec.word_limit},
            )

        # Validate speaker requirement
        if spec.tail_required:
            if not speaker_character_id and speaker:
                speaker_character_id = speaker
            if not speaker_character_id:
                raise BubbleServiceError(
                    "ERR_BUBBLE_SPEAKER_REQUIRED",
                    f"{spec.label} requires a speaker_character_id. Provide the character ID or name. "
                    "Example: {'type_id': 'speech.normal', 'text': '...', 'speaker_character_id': 'char_01'}",
                    {"type_id": type_id},
                )
        else:
            # For narration, caption, sfx: speaker is null
            if speaker_character_id and type_id in {"narration.box", "caption.timeplace", "sfx.text"}:
                speaker_character_id = None

        stable_bubble_id = bubble_id or generate_id(IdPrefix.BUBBLE)
        stable_layer_id = f"layer_{stable_bubble_id}"

        # Resolve protected regions
        faces_to_protect = list(protected_regions or [])
        if not faces_to_protect:
            # Inspect existing panel layers for known character anchors / bounds
            for existing in document.layers:
                if existing.panel_id == panel_id and existing.metadata.get("protected_regions"):
                    faces_to_protect.extend(existing.metadata["protected_regions"])

        # Sizing and placement
        req = BubblePlacementRequest(
            bubble_id=stable_bubble_id,
            type_id=type_id,
            text=text,
            reading_order=reading_order,
            speaker_character_id=speaker_character_id,
            speaker_anchor=Point(x=float(tail_target["x"]), y=float(tail_target["y"])) if tail_target and "x" in tail_target else None,
            font_family=font_family,
            preferred_font_size=preferred_font_size,
        )

        trim = document.layout.trim_box

        # Run placement engine or use manual override if provided
        if position and "x" in position and "y" in position:
            layout = layout_lettering_text(
                text=text,
                type_id=type_id,
                max_width_px=slot.rect.width * 0.55,
                max_height_px=slot.rect.height * 0.38,
                font_family=font_family,
                requested_font_size_px=preferred_font_size,
            )
            bw = max(80.0, layout.content_width_px * 1.28 + 32.0)
            bh = max(44.0, layout.content_height_px * 1.25 + 24.0)
            bx = float(position["x"])
            by = float(position["y"])
            t_tip = Point(x=float(tail_target["x"]), y=float(tail_target["y"])) if tail_target and "x" in tail_target else None
            placed_res = BubblePlacementResult(
                bubble_id=stable_bubble_id,
                type_id=type_id,
                rect=Rect(x=bx, y=by, width=bw, height=bh),
                tail_target=t_tip,
                layout=layout,
                reading_order=reading_order,
                speaker_character_id=speaker_character_id,
                in_gutter=False,
            )
        else:
            existing_panel_bubbles = [
                l for l in document.layers
                if l.kind == LayerKind.TEXT and l.panel_id == panel_id and l.metadata.get("bubble_id")
            ]
            all_reqs = []
            for ex in existing_panel_bubbles:
                m_ex = ex.metadata
                t_ex = m_ex.get("type_id") or m_ex.get("semantic_type") or "speech.normal"
                all_reqs.append(BubblePlacementRequest(
                    bubble_id=m_ex["bubble_id"],
                    type_id=t_ex,
                    text=m_ex.get("text", ""),
                    reading_order=int(m_ex.get("reading_order", 1)),
                    speaker_character_id=m_ex.get("speaker_character_id"),
                    speaker_anchor=Point(x=float(m_ex["tail_target"]["x"]), y=float(m_ex["tail_target"]["y"])) if m_ex.get("tail_target") and "x" in m_ex["tail_target"] else None,
                    font_family=m_ex.get("font_family", "Comic Neue"),
                    preferred_font_size=m_ex.get("font_size"),
                ))
            all_reqs.append(req)
            all_reqs.sort(key=lambda r: r.reading_order)

            try:
                results = self.placement_engine.place_bubbles(
                    panel_rect=slot.rect,
                    bubbles=all_reqs,
                    protected_regions=faces_to_protect,
                    reading_direction=reading_direction,
                    page_safe_margin=trim,
                    allow_gutter_bleed=True,
                )
                res_by_id = {r.bubble_id: r for r in results}
                placed_res = res_by_id[stable_bubble_id]

                # Update existing panel layers with their newly placed positions
                for ex in existing_panel_bubbles:
                    b_id = ex.metadata["bubble_id"]
                    if b_id in res_by_id:
                        r_ex = res_by_id[b_id]
                        spec_ex = BUBBLE_TYPE_BY_ID[r_ex.type_id]
                        vec_ex = self.vector_builder.build_bubble_vector(
                            bounds=r_ex.rect,
                            type_id=r_ex.type_id,
                            shape=spec_ex.default_shape,
                            tail_type=spec_ex.default_tail,
                            tail_target=r_ex.tail_target,
                            bubble_id=b_id,
                            pad_x=r_ex.pad_x,
                            pad_y=r_ex.pad_y,
                        )
                        ex.metadata.update({
                            "x": r_ex.rect.x,
                            "y": r_ex.rect.y,
                            "width": r_ex.rect.width,
                            "height": r_ex.rect.height,
                            "font_size": r_ex.layout.font_size_px,
                            "lines": r_ex.layout.lines,
                            "svg_path": vec_ex.unified_path,
                            "unified_path": vec_ex.unified_path,
                            "tail_chain_circles": vec_ex.chain_circles,
                            "stroke_dash": vec_ex.stroke_dash,
                            "tail_target": {"x": vec_ex.tail_tip.x, "y": vec_ex.tail_tip.y} if vec_ex.tail_tip else None,
                            "in_gutter": r_ex.in_gutter,
                        })
            except PlacementError as exc:
                raise BubbleServiceError(exc.code, exc.message, exc.details) from exc

        # Construct single closed vector geometry
        vector = self.vector_builder.build_bubble_vector(
            bounds=placed_res.rect,
            type_id=type_id,
            shape=spec.default_shape,
            tail_type=spec.default_tail,
            tail_target=placed_res.tail_target,
            bubble_id=stable_bubble_id,
            pad_x=placed_res.pad_x,
            pad_y=placed_res.pad_y,
        )

        # Assemble EditorLayer metadata
        metadata = {
            "bubble_id": stable_bubble_id,
            "type_id": type_id,
            "semantic_type": type_id,
            "reading_order": reading_order,
            "speaker_character_id": speaker_character_id,
            "speaker": speaker or speaker_character_id,
            "text": text,
            "lines": placed_res.layout.lines,
            "x": placed_res.rect.x,
            "y": placed_res.rect.y,
            "width": placed_res.rect.width,
            "height": placed_res.rect.height,
            "font_size": placed_res.layout.font_size_px,
            "font_family": font_family,
            "line_height": 1.2,
            "bubble_shape": spec.default_shape,
            "tail_type": spec.default_tail,
            "svg_path": vector.unified_path,
            "unified_path": vector.unified_path,
            "tail_chain_circles": vector.chain_circles,
            "stroke_dash": vector.stroke_dash,
            "tail_target": {"x": vector.tail_tip.x, "y": vector.tail_tip.y} if vector.tail_tip else None,
            "padding_x": placed_res.pad_x,
            "padding_y": placed_res.pad_y,
            "in_gutter": placed_res.in_gutter,
            "bubble_geometry_version": 3,
        }

        layer = EditorLayer(
            layer_id=stable_layer_id,
            kind=LayerKind.TEXT,
            label=f"{spec.label} [{stable_bubble_id}]",
            panel_id=panel_id,
            z_index=10 + reading_order,
            metadata=metadata,
        )

        document.layers.append(layer)

        return {
            "bubble_id": stable_bubble_id,
            "layer_id": stable_layer_id,
            "panel_id": panel_id,
            "type_id": type_id,
            "text": text,
            "reading_order": reading_order,
            "speaker_character_id": speaker_character_id,
            "rect": {"x": placed_res.rect.x, "y": placed_res.rect.y, "width": placed_res.rect.width, "height": placed_res.rect.height},
            "tail_target": metadata["tail_target"],
            "font_size": placed_res.layout.font_size_px,
            "lines": placed_res.layout.lines,
            "in_gutter": placed_res.in_gutter,
        }

    def remove_bubble(self, document: EditablePageDocument, bubble_id: str) -> bool:
        """Remove a bubble layer by bubble_id or layer_id."""
        initial_count = len(document.layers)
        document.layers = [
            l for l in document.layers
            if l.metadata.get("bubble_id") != bubble_id and l.layer_id != bubble_id
        ]
        return len(document.layers) < initial_count

    def list_bubbles(self, document: EditablePageDocument, panel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all bubbles on the document or for a specific panel."""
        results = []
        for l in document.layers:
            if l.kind == LayerKind.TEXT and l.metadata.get("bubble_id"):
                if panel_id is None or l.panel_id == panel_id:
                    results.append({
                        "bubble_id": l.metadata.get("bubble_id"),
                        "layer_id": l.layer_id,
                        "panel_id": l.panel_id,
                        "type_id": l.metadata.get("type_id") or l.metadata.get("semantic_type", "speech.normal"),
                        "text": l.metadata.get("text", ""),
                        "reading_order": l.metadata.get("reading_order", 1),
                        "speaker_character_id": l.metadata.get("speaker_character_id"),
                        "x": l.metadata.get("x", 0),
                        "y": l.metadata.get("y", 0),
                        "width": l.metadata.get("width", 0),
                        "height": l.metadata.get("height", 0),
                    })
        results.sort(key=lambda b: (b["panel_id"] or "", b["reading_order"]))
        return results

    def update_bubble(
        self,
        document: EditablePageDocument,
        bubble_id: str,
        properties: Dict[str, Any],
        protected_regions: Optional[Sequence[ProtectedRegion | Rect | Dict[str, Any]]] = None,
        reading_direction: str = "ltr",
    ) -> Dict[str, Any]:
        """Update an existing bubble's text, type, position, or tail target."""
        layer = next(
            (l for l in document.layers if l.metadata.get("bubble_id") == bubble_id or l.layer_id == bubble_id),
            None,
        )
        if not layer:
            raise BubbleServiceError("ERR_BUBBLE_NOT_FOUND", f"Bubble '{bubble_id}' was not found on page '{document.page_id}'.")

        m = layer.metadata
        panel_id = layer.panel_id
        slot = document.layout.get_panel(panel_id) if panel_id else None
        if not slot:
            raise BubbleServiceError("ERR_PANEL_NOT_FOUND", f"Panel '{panel_id}' does not exist on page '{document.page_id}'.")

        text = str(properties.get("text") if "text" in properties else m.get("text", ""))
        type_id = properties.get("type_id") or m.get("type_id") or m.get("semantic_type") or "speech.normal"
        reading_order = int(properties.get("reading_order", m.get("reading_order", 1)))
        speaker_character_id = properties.get("speaker_character_id", m.get("speaker_character_id"))
        font_family = properties.get("font_family", m.get("font_family", "Comic Neue"))
        font_size = properties.get("font_size", m.get("font_size"))
        position = properties.get("position")
        tail_target = properties.get("tail_target")

        spec = BUBBLE_TYPE_BY_ID.get(type_id)
        if spec is None:
            allowed_ids = [t.type_id for t in BUBBLE_TYPES]
            raise BubbleServiceError(
                "ERR_BUBBLE_TYPE_INVALID",
                f"Invalid type_id '{type_id}'. Allowed type_ids are: {', '.join(allowed_ids)}.",
                {"type_id": type_id, "allowed_type_ids": allowed_ids},
            )

        if not text.strip():
            raise BubbleServiceError(
                "ERR_BUBBLE_TEXT_REQUIRED",
                "Speech bubble text must contain at least one visible character.",
                {"type_id": type_id},
            )

        words = count_words(text)
        if words > spec.word_limit:
            raise BubbleServiceError(
                "ERR_LETTERING_WORD_LIMIT",
                f"{spec.label} allows at most {spec.word_limit} words; received {words}. Shorten the line or split it across multiple bubbles.",
                {"type_id": type_id, "word_count": words, "word_limit": spec.word_limit},
            )

        if spec.tail_required and not speaker_character_id:
            raise BubbleServiceError(
                "ERR_BUBBLE_SPEAKER_REQUIRED",
                f"{spec.label} requires a speaker_character_id. Provide the character ID or name.",
                {"type_id": type_id},
            )

        if position and "x" in position and "y" in position:
            layout = layout_lettering_text(
                text=text,
                type_id=type_id,
                max_width_px=slot.rect.width * 0.55,
                max_height_px=slot.rect.height * 0.38,
                font_family=font_family,
                requested_font_size_px=font_size,
            )
            bw = max(80.0, layout.content_width_px * 1.28 + 32.0)
            bh = max(44.0, layout.content_height_px * 1.25 + 24.0)
            bx = float(position["x"])
            by = float(position["y"])
            t_tip = Point(x=float(tail_target["x"]), y=float(tail_target["y"])) if tail_target and "x" in tail_target else None
            placed_rect = Rect(x=bx, y=by, width=bw, height=bh)
            pad_x = 16.0
            pad_y = 12.0
            in_gutter = False
        else:
            req = BubblePlacementRequest(
                bubble_id=bubble_id,
                type_id=type_id,
                text=text,
                reading_order=reading_order,
                speaker_character_id=speaker_character_id,
                speaker_anchor=Point(x=float(tail_target["x"]), y=float(tail_target["y"])) if tail_target and "x" in tail_target else None,
                font_family=font_family,
                preferred_font_size=font_size,
            )
            trim = document.layout.trim_box
            try:
                results = self.placement_engine.place_bubbles(
                    panel_rect=slot.rect,
                    bubbles=[req],
                    protected_regions=protected_regions or [],
                    reading_direction=reading_direction,
                    page_safe_margin=trim,
                    allow_gutter_bleed=True,
                )
                placed = results[0]
                placed_rect = placed.rect
                t_tip = placed.tail_target
                layout = placed.layout
                pad_x = placed.pad_x
                pad_y = placed.pad_y
                in_gutter = placed.in_gutter
            except PlacementError as exc:
                raise BubbleServiceError(exc.code, exc.message, exc.details) from exc

        vector = self.vector_builder.build_bubble_vector(
            bounds=placed_rect,
            type_id=type_id,
            shape=spec.default_shape,
            tail_type=spec.default_tail,
            tail_target=t_tip,
            bubble_id=bubble_id,
            pad_x=pad_x,
            pad_y=pad_y,
        )

        m.update({
            "bubble_id": bubble_id,
            "type_id": type_id,
            "semantic_type": type_id,
            "reading_order": reading_order,
            "speaker_character_id": speaker_character_id,
            "text": text,
            "lines": layout.lines,
            "x": placed_rect.x,
            "y": placed_rect.y,
            "width": placed_rect.width,
            "height": placed_rect.height,
            "font_size": layout.font_size_px,
            "font_family": font_family,
            "bubble_shape": spec.default_shape,
            "tail_type": spec.default_tail,
            "svg_path": vector.unified_path,
            "unified_path": vector.unified_path,
            "tail_chain_circles": vector.chain_circles,
            "stroke_dash": vector.stroke_dash,
            "tail_target": {"x": vector.tail_tip.x, "y": vector.tail_tip.y} if vector.tail_tip else None,
            "padding_x": pad_x,
            "padding_y": pad_y,
            "in_gutter": in_gutter,
        })

        return {
            "bubble_id": bubble_id,
            "layer_id": layer.layer_id,
            "panel_id": panel_id,
            "type_id": type_id,
            "text": text,
            "reading_order": reading_order,
            "speaker_character_id": speaker_character_id,
            "rect": {"x": placed_rect.x, "y": placed_rect.y, "width": placed_rect.width, "height": placed_rect.height},
            "tail_target": m["tail_target"],
            "font_size": layout.font_size_px,
            "lines": layout.lines,
            "in_gutter": in_gutter,
        }

    def place_all(
        self,
        document: EditablePageDocument,
        panel_id: str,
        reading_direction: str = "ltr",
        protected_regions: Optional[Sequence[ProtectedRegion | Rect | Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Re-place all bubbles within a panel to optimize spacing and reading order."""
        slot = document.layout.get_panel(panel_id)
        if slot is None:
            raise BubbleServiceError("ERR_PANEL_NOT_FOUND", f"Panel '{panel_id}' does not exist on page '{document.page_id}'.")

        bubble_layers = [l for l in document.layers if l.kind == LayerKind.TEXT and l.panel_id == panel_id and l.metadata.get("bubble_id")]
        if not bubble_layers:
            return []

        # Check if legacy document has missing or unassigned reading_orders
        has_explicit_orders = any(l.metadata.get("reading_order") is not None for l in bubble_layers)
        if not has_explicit_orders:
            is_rtl = reading_direction.lower() == "rtl"
            bubble_layers = sorted(
                bubble_layers,
                key=lambda l: (
                    float(l.metadata.get("y", 0.0)),
                    -float(l.metadata.get("x", 0.0)) if is_rtl else float(l.metadata.get("x", 0.0)),
                )
            )
            for idx, l in enumerate(bubble_layers):
                l.metadata["reading_order"] = idx + 1

        # Resolve protected regions and speaker anchors
        resolved_protected = list(protected_regions or [])
        detected_anchors: List[Point] = []

        img_layer = next((l for l in document.layers if l.panel_id == panel_id and l.kind == LayerKind.IMAGE), None)
        if img_layer and img_layer.source_asset_id:
            try:
                from app.api.routers.assets import get_registry
                from app.canvas.character_locator import detect_panel_protected_regions
                asset_reg = get_registry()
                resolved = asset_reg.resolve_asset(img_layer.source_asset_id, verify_integrity=False)
                img_faces, detected_anchors = detect_panel_protected_regions(resolved.absolute_path, slot.rect)
                resolved_protected.extend(img_faces)
            except Exception:
                pass

        for existing in document.layers:
            if existing.panel_id == panel_id and existing.metadata.get("protected_regions"):
                resolved_protected.extend(existing.metadata["protected_regions"])

        panel_layer = next((l for l in document.layers if l.panel_id == panel_id and l.kind == LayerKind.PANEL), None)
        known_anchors = panel_layer.metadata.get("character_anchors", {}) if panel_layer else {}

        bubble_reqs = []
        for idx, l in enumerate(bubble_layers):
            m = l.metadata
            type_id = m.get("type_id") or m.get("semantic_type") or "speech.normal"
            spk_id = m.get("speaker_character_id")

            spk_anchor = None
            prev_target = m.get("tail_target")
            if spk_id and isinstance(known_anchors, dict) and spk_id in known_anchors:
                cand = known_anchors[spk_id]
                if isinstance(cand, dict) and "x" in cand and "y" in cand:
                    spk_anchor = Point(x=float(cand["x"]), y=float(cand["y"]))
            elif isinstance(prev_target, dict) and "x" in prev_target and "y" in prev_target:
                spk_anchor = Point(x=float(prev_target["x"]), y=float(prev_target["y"]))
            elif spk_id and detected_anchors:
                unique_speakers = list(dict.fromkeys(bl.metadata.get("speaker_character_id") for bl in bubble_layers if bl.metadata.get("speaker_character_id")))
                sorted_anchors = sorted(detected_anchors, key=lambda pt: pt.x)
                if spk_id in unique_speakers and sorted_anchors:
                    spk_idx = unique_speakers.index(spk_id)
                    anchor_idx = min(spk_idx, int((spk_idx / max(1, len(unique_speakers) - 1)) * (len(sorted_anchors) - 1)))
                    spk_anchor = sorted_anchors[anchor_idx]

            bubble_reqs.append(BubblePlacementRequest(
                bubble_id=m["bubble_id"],
                type_id=type_id,
                text=m["text"],
                reading_order=int(m.get("reading_order") or (idx + 1)),
                speaker_character_id=spk_id,
                speaker_anchor=spk_anchor,
                font_family=m.get("font_family", "Comic Neue"),
                preferred_font_size=m.get("font_size"),
            ))

        trim = document.layout.trim_box
        # Protect other panels so gutter bleed stays strictly out of adjacent panels' artwork
        other_panel_regions = [
            ProtectedRegion(x=slot_other.rect.x, y=slot_other.rect.y, width=slot_other.rect.width, height=slot_other.rect.height, label="panel")
            for slot_other in getattr(document.layout, "panel_slots", [])
            if slot_other.panel_id != panel_id and slot_other.rect is not None
        ]
        all_protected = resolved_protected + other_panel_regions

        try:
            results = self.placement_engine.place_bubbles(
                panel_rect=slot.rect,
                bubbles=bubble_reqs,
                protected_regions=all_protected,
                reading_direction=reading_direction,
                page_safe_margin=trim,
                allow_gutter_bleed=True,
            )
        except PlacementError as exc:
            raise BubbleServiceError(exc.code, exc.message, exc.details) from exc

        res_by_id = {r.bubble_id: r for r in results}
        updated = []
        for l in bubble_layers:
            b_id = l.metadata["bubble_id"]
            if b_id in res_by_id:
                r = res_by_id[b_id]
                spec = BUBBLE_TYPE_BY_ID[r.type_id]
                vector = self.vector_builder.build_bubble_vector(
                    bounds=r.rect,
                    type_id=r.type_id,
                    shape=spec.default_shape,
                    tail_type=spec.default_tail,
                    tail_target=r.tail_target,
                    bubble_id=b_id,
                    pad_x=r.pad_x,
                    pad_y=r.pad_y,
                )
                l.metadata.update({
                    "x": r.rect.x,
                    "y": r.rect.y,
                    "width": r.rect.width,
                    "height": r.rect.height,
                    "font_size": r.layout.font_size_px,
                    "lines": r.layout.lines,
                    "svg_path": vector.unified_path,
                    "unified_path": vector.unified_path,
                    "tail_target": {"x": vector.tail_tip.x, "y": vector.tail_tip.y} if vector.tail_tip else None,
                    "in_gutter": r.in_gutter,
                })
                updated.append(b_id)

        return [{"placed_bubble_ids": updated, "panel_id": panel_id}]
