"""
S6: Final Compositor Engine.
Deterministically renders and composites all page production layers
(Background, E3 Art, E7 Effects, E6 Speech Bubbles, E5 Lettering, E2 Borders)
without mutating or flattening the raw source assets.
"""
from io import BytesIO
import hashlib
import math
from pathlib import Path
from typing import Optional, List, Any
from PIL import Image

from app.contracts.geometry import Size, AssetFormat, ColorSpace
from app.contracts.artifacts import AssetType
from app.contracts.engine import CompositorParams, CompositorOutput
from app.storage.registry import AssetRegistry


class FinalCompositor:
    """Specialist Final Compositor Engine (S6)."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("runs/composites")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def composite_page(
        self,
        params: CompositorParams,
        asset_registry: AssetRegistry,
        canvas_dimensions: Optional[Size] = None,
        project_id: str = "default_project",
    ) -> CompositorOutput:
        """
        Loads all ordered layer artifacts, composites them with Pillow RGBA alpha blending,
        saves the output PNG, computes SHA-256 digest, and ingests the composite artifact.
        """
        # Determine canvas dimensions
        width = int(canvas_dimensions.width) if canvas_dimensions else 1200
        height = int(canvas_dimensions.height) if canvas_dimensions else 1800

        # Create master white background canvas
        base = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        valid_layers_count = 0

        for layer_id in params.ordered_layer_artifact_ids:
            try:
                resolved = asset_registry.resolve_asset(layer_id, verify_integrity=True)
                if not resolved.absolute_path.exists():
                    continue
                layer_img = Image.open(resolved.absolute_path).convert("RGBA")
                # Resize if necessary or paste with alpha
                if layer_img.size != (width, height):
                    # Center or paste at top-left
                    base.alpha_composite(layer_img.resize((width, height), Image.Resampling.LANCZOS))
                else:
                    base.alpha_composite(layer_img)
                valid_layers_count += 1
            except Exception:
                # If layer is not on disk or not an image, continue compositing remaining layers
                continue

        # Save composite output
        composite_id = f"composite_{hashlib.sha256(str(params.ordered_layer_artifact_ids).encode()).hexdigest()[:12]}"
        output_filename = f"{composite_id}.png"
        output_path = self.output_dir / output_filename

        base_rgb = base.convert("RGB")
        base_rgb.save(output_path, format="PNG", dpi=(params.dpi, params.dpi))

        output_bytes = output_path.read_bytes()
        content_hash = hashlib.sha256(output_bytes).hexdigest()

        # Ingest composite artifact into AssetRegistry
        asset = asset_registry.ingest_bytes(
            output_bytes,
            output_filename,
            project_id=project_id,
            asset_type=AssetType.GENERIC_ARTIFACT,
            name=f"Composite Page {composite_id}",
            parent_asset_ids=params.ordered_layer_artifact_ids,
            lineage_operation="final_compositor_render",
            extra_metadata={
                "dpi": params.dpi,
                "width": width,
                "height": height,
                "layer_count": valid_layers_count,
            },
        )

        return CompositorOutput(
            composite_page_artifact_id=asset.asset_id,
            dimensions=Size(width=float(width), height=float(height)),
            dpi=params.dpi,
            output_file_path=str(output_path),
            sha256=content_hash,
            layer_count=valid_layers_count,
        )

    def composite_page_document(
        self,
        page_doc: Any,
        asset_registry: AssetRegistry,
        project_id: Optional[str] = None,
    ) -> CompositorOutput:
        """
        Renders and composites an EditablePageDocument into a high-resolution 300 DPI page composite.
        Renders panel art (with polygon masks if applicable), speech bubbles, text lettering, and borders.
        """
        from app.text.typography import TypographyEngine, shape_arabic
        from PIL import ImageDraw

        pid = project_id or getattr(page_doc, "project_id", "default_project")
        layout = getattr(page_doc, "layout", None)
        canvas_spec = getattr(layout, "canvas_spec", None) if layout else None

        if canvas_spec:
            width = int(getattr(canvas_spec, "width_px", getattr(getattr(canvas_spec, "dimensions", None), "width", 1200)))
            height = int(getattr(canvas_spec, "height_px", getattr(getattr(canvas_spec, "dimensions", None), "height", 1800)))
        else:
            width = 1200
            height = 1800
        dpi = int(canvas_spec.dpi) if canvas_spec else 300

        base = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(base)

        slot_map = {}
        if layout and hasattr(layout, "panel_slots"):
            for slot in layout.panel_slots:
                slot_map[slot.panel_id] = slot

        layers = getattr(page_doc, "layers", [])
        sorted_layers = sorted(layers, key=lambda l: getattr(l, "z_index", 0))

        parent_asset_ids = []
        valid_layer_count = 0

        # 1. Render Image Layers
        for layer in sorted_layers:
            if not getattr(layer, "visible", True):
                continue
            kind = getattr(layer, "kind", None)
            kind_val = getattr(kind, "value", str(kind or "")).lower()

            if kind_val == "image" and getattr(layer, "source_asset_id", None):
                src_id = layer.source_asset_id
                panel_id = getattr(layer, "panel_id", None)
                slot = slot_map.get(panel_id)
                if not slot:
                    continue

                try:
                    resolved = asset_registry.resolve_asset(src_id, verify_integrity=True)
                    if resolved.absolute_path.exists():
                        img = Image.open(resolved.absolute_path).convert("RGBA")
                        slot_rect = slot.rect
                        target_w = max(10, int(slot_rect.width))
                        target_h = max(10, int(slot_rect.height))

                        fit_mode = getattr(layer, "fit_mode", "cover")
                        sw, sh = img.size
                        if fit_mode == "contain":
                            scale = min(target_w / sw, target_h / sh)
                            rw, rh = int(sw * scale), int(sh * scale)
                            scaled_img = img.resize((max(1, rw), max(1, rh)), Image.Resampling.LANCZOS)
                            panel_img = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 255))
                            ox = (target_w - rw) // 2
                            oy = (target_h - rh) // 2
                            panel_img.paste(scaled_img, (ox, oy), scaled_img)
                        else:  # cover
                            scale = max(target_w / sw, target_h / sh)
                            rw, rh = int(sw * scale), int(sh * scale)
                            scaled_img = img.resize((max(1, rw), max(1, rh)), Image.Resampling.LANCZOS)
                            ox = (rw - target_w) // 2
                            oy = (rh - target_h) // 2
                            panel_img = scaled_img.crop((ox, oy, ox + target_w, oy + target_h))

                        poly_verts = getattr(slot, "polygon_vertices", None)
                        if getattr(slot, "has_polygon", False) and poly_verts:
                            poly_pts = [(getattr(p, "x", p[0]) - slot_rect.x, getattr(p, "y", p[1]) - slot_rect.y) for p in poly_verts]
                            mask = Image.new("L", (target_w, target_h), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.polygon(poly_pts, fill=255)
                            base.paste(panel_img, (int(slot_rect.x), int(slot_rect.y)), mask)
                        else:
                            base.paste(panel_img, (int(slot_rect.x), int(slot_rect.y)), panel_img)

                        parent_asset_ids.append(src_id)
                        valid_layer_count += 1
                except Exception:
                    pass

        # 2. Render Panel Borders
        for slot in slot_map.values():
            slot_rect = slot.rect
            poly_verts = getattr(slot, "polygon_vertices", None)
            if getattr(slot, "has_polygon", False) and poly_verts:
                pts = [(getattr(p, "x", p[0]), getattr(p, "y", p[1])) for p in poly_verts]
                draw.polygon(pts, outline="#111111", width=3)
            else:
                draw.rectangle(
                    [slot_rect.x, slot_rect.y, slot_rect.x + slot_rect.width, slot_rect.y + slot_rect.height],
                    outline="#111111",
                    width=3,
                )

        # 3. Render Lines
        for layer in sorted_layers:
            if not getattr(layer, "visible", True):
                continue
            kind = getattr(layer, "kind", None)
            kind_val = getattr(kind, "value", str(kind or "")).lower()
            if kind_val == "line":
                meta = getattr(layer, "metadata", {})
                x1 = meta.get("x1", 0)
                y1 = meta.get("y1", 0)
                x2 = meta.get("x2", 0)
                y2 = meta.get("y2", 0)
                stroke_w = int(meta.get("stroke_width", 2))
                color = meta.get("color", "#111111")
                draw.line([(x1, y1), (x2, y2)], fill=color, width=stroke_w)
                valid_layer_count += 1

        # 4. Render Text & Speech Bubbles
        typo_engine = TypographyEngine()
        for layer in sorted_layers:
            if not getattr(layer, "visible", True):
                continue
            kind = getattr(layer, "kind", None)
            kind_val = getattr(kind, "value", str(kind or "")).lower()
            if kind_val == "text":
                meta = getattr(layer, "metadata", {})
                raw_text = meta.get("text", "")
                if not raw_text:
                    continue

                tx = float(meta.get("x", 50))
                ty = float(meta.get("y", 50))
                tw = float(meta.get("width", 200))
                th = float(meta.get("height", 80))
                bubble_shape_str = str(meta.get("bubble_shape", "rounded_rectangle")).lower()
                tail_target = meta.get("tail_target")
                if isinstance(tail_target, dict):
                    tail_x = tail_target.get("x")
                    tail_y = tail_target.get("y")
                else:
                    tail_x = meta.get("tail_x", meta.get("tail_tip_x"))
                    tail_y = meta.get("tail_y", meta.get("tail_tip_y"))

                cx = tx + tw / 2.0
                cy = ty + th / 2.0
                rx = tw / 2.0
                ry = th / 2.0

                # 1. Procedural Perimeter Tail & Body Rendering (Seamless Fills Then Strokes)
                tail_pts = None
                chain_circles = meta.get("tail_chain_circles") or []
                if tail_x is not None and tail_y is not None:
                    tip_x, tip_y = float(tail_x), float(tail_y)
                    dx = tip_x - cx
                    dy = tip_y - cy
                    dist = math.hypot(dx, dy)
                    if dist > 1.0:
                        ux = dx / dist
                        uy = dy / dist
                        boundary_scale = 1.0 / math.sqrt((ux / max(rx, 1.0)) ** 2 + (uy / max(ry, 1.0)) ** 2)
                        root_x = cx + ux * boundary_scale * 0.95
                        root_y = cy + uy * boundary_scale * 0.95
                        base_w = min(14.0, max(8.0, min(tw, th) * 0.12))
                        p1 = (root_x - uy * base_w, root_y + ux * base_w)
                        p2 = (root_x + uy * base_w, root_y - ux * base_w)
                        tail_pts = [p1, (tip_x, tip_y), p2]
                    else:
                        tail_pts = [(tx + tw / 2 - 8, ty + th - 2), (tip_x, tip_y), (tx + tw / 2 + 8, ty + th - 2)]

                # Fills first
                if tail_pts and not chain_circles:
                    draw.polygon(tail_pts, fill="#FFFFFF", outline=None)
                for circle in chain_circles:
                    if len(circle) >= 3:
                        ccx, ccy, cr = circle[0], circle[1], circle[2]
                        draw.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], fill="#FFFFFF", outline="#111111", width=2)

                if "oval" in bubble_shape_str:
                    draw.ellipse([tx, ty, tx + tw, ty + th], fill="#FFFFFF", outline="#111111", width=3)
                elif "shout" in bubble_shape_str or "burst" in bubble_shape_str or "impact" in bubble_shape_str:
                    num_pts = 20
                    pts = []
                    for i in range(num_pts):
                        ang = (2.0 * math.pi * i) / num_pts
                        sc = 1.12 if (i % 2 == 1) else 0.88
                        pts.append((tx + tw / 2 + (tw / 2) * math.cos(ang) * sc, ty + th / 2 + (th / 2) * math.sin(ang) * sc))
                    draw.polygon(pts, fill="#FFFFFF", outline="#111111", width=3)
                else:
                    draw.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=16, fill="#FFFFFF", outline="#111111", width=3)

                # Then stroke the tail outer sides so tail merges with body
                if tail_pts and not chain_circles:
                    draw.line([tail_pts[0], tail_pts[1]], fill="#111111", width=3)
                    draw.line([tail_pts[1], tail_pts[2]], fill="#111111", width=3)

                # 3. Comic Typography Auto-Fitting & Diamond Line Wrapping
                is_arabic = any('\u0600' <= c <= '\u06FF' for c in raw_text)
                shaped = shape_arabic(raw_text) if is_arabic else raw_text
                font_name = "NotoSansArabic" if is_arabic else "ComicNeue"

                usable_w = tw * 0.76 if "oval" in bubble_shape_str else max(40.0, tw - 24.0)
                usable_h = th * 0.72 if "oval" in bubble_shape_str else max(30.0, th - 20.0)

                words = shaped.split()
                if not words:
                    lines = [shaped]
                elif shaped.count("\n") > 0:
                    lines = shaped.splitlines()
                elif len(words) <= 2:
                    lines = [" ".join(words)]
                else:
                    total_chars = len(shaped)
                    k_target = max(2, min(5, round(math.sqrt(0.36 * total_chars))))
                    best_lines = None
                    best_score = float("inf")
                    for k in range(max(1, k_target - 1), min(len(words) + 1, k_target + 2)):
                        avg_chars = total_chars / k
                        cand_lines = []
                        cur = []
                        cur_len = 0
                        for w in words:
                            w_len = len(w)
                            if not cur:
                                cur.append(w)
                                cur_len = w_len
                            elif (cur_len + 1 + w_len) <= avg_chars * 1.25 and len(cand_lines) < k - 1:
                                cur.append(w)
                                cur_len += 1 + w_len
                            elif len(cand_lines) == k - 1:
                                cur.append(w)
                                cur_len += 1 + w_len
                            else:
                                cand_lines.append(" ".join(cur))
                                cur = [w]
                                cur_len = w_len
                        if cur:
                            cand_lines.append(" ".join(cur))
                        lengths = [len(l) for l in cand_lines]
                        score = max(lengths) - min(lengths)
                        if score < best_score:
                            best_score = score
                            best_lines = cand_lines
                    lines = best_lines or [shaped]

                base_font_size = float(meta.get("font_size", 20))
                opt_font_size = base_font_size
                for test_size in range(max(15, int(base_font_size - 4)), 33):
                    test_font, _ = typo_engine.resolve_font(font_name, test_size)
                    test_lh = int(test_size * 1.28)
                    test_tot_h = len(lines) * test_lh
                    test_max_w = max((draw.textbbox((0, 0), l, font=test_font)[2] - draw.textbbox((0, 0), l, font=test_font)[0]) for l in lines)
                    if test_tot_h <= usable_h and test_max_w <= usable_w:
                        opt_font_size = float(test_size)
                    else:
                        break

                font, _ = typo_engine.resolve_font(font_name, opt_font_size)
                line_h = int(opt_font_size * 1.28)
                text_block_h = len(lines) * line_h
                start_y = ty + (th - text_block_h) / 2.0

                for line in lines:
                    bb = draw.textbbox((0, 0), line, font=font)
                    lw = bb[2] - bb[0]
                    line_x = tx + (tw - lw) / 2.0
                    draw.text((line_x, start_y), line, font=font, fill="#111111")
                    start_y += line_h

                valid_layer_count += 1

        page_id = getattr(page_doc, "page_id", "page_unknown")
        rev = getattr(page_doc, "revision", 0)
        output_filename = f"composite_{page_id}_rev{rev}.png"
        output_path = self.output_dir / output_filename

        base_rgb = base.convert("RGB")
        base_rgb.save(output_path, format="PNG", dpi=(dpi, dpi))

        output_bytes = output_path.read_bytes()
        content_hash = hashlib.sha256(output_bytes).hexdigest()

        asset = asset_registry.ingest_bytes(
            output_bytes,
            output_filename,
            project_id=pid,
            asset_type=AssetType.GENERIC_ARTIFACT,
            name=f"Composite Page {page_id} (Rev {rev})",
            parent_asset_ids=parent_asset_ids,
            lineage_operation="composite_page_document",
            extra_metadata={
                "page_id": page_id,
                "revision": rev,
                "dpi": dpi,
                "width": width,
                "height": height,
                "layer_count": valid_layer_count,
            },
        )

        return CompositorOutput(
            composite_page_artifact_id=asset.asset_id,
            dimensions=Size(width=float(width), height=float(height)),
            dpi=dpi,
            output_file_path=str(output_path),
            sha256=content_hash,
            layer_count=valid_layer_count,
        )
