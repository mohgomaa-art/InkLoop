"""
E5: Typography & Font Shaping Engine.
Handles typeface management, Arabic RTL bidirectional text shaping,
accurate text measurement with Pillow, word wrapping, and overflow detection.
"""
from io import BytesIO
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Union
from PIL import Image, ImageDraw, ImageFont

try:
    from bidi.algorithm import get_display
except ImportError:
    def get_display(text: str) -> str:
        return text

from app.contracts.geometry import Rect, Point
from app.contracts.artifacts import AssetType
from app.contracts.engine import TypographyParams, TypographyOutput
from app.storage.registry import AssetRegistry


# Arabic character joining tables for pure-Python deterministic shaping
ARABIC_JOINING = {
    '\u0621': ('\uFE80', None, None, None), # Hamza
    '\u0622': ('\uFE81', None, None, '\uFE82'), # Alef with Madda
    '\u0623': ('\uFE83', None, None, '\uFE84'), # Alef with Hamza above
    '\u0624': ('\uFE85', None, None, '\uFE86'), # Waw with Hamza
    '\u0625': ('\uFE87', None, None, '\uFE88'), # Alef with Hamza below
    '\u0626': ('\uFE89', '\uFE8B', '\uFE8C', '\uFE8A'), # Yeh with Hamza
    '\u0627': ('\uFE8D', None, None, '\uFE8E'), # Alef
    '\u0628': ('\uFE8F', '\uFE91', '\uFE92', '\uFE90'), # Beh
    '\u0629': ('\uFE93', None, None, '\uFE94'), # Teh Marbuta
    '\u062A': ('\uFE95', '\uFE97', '\uFE98', '\uFE96'), # Teh
    '\u062B': ('\uFE99', '\uFE9B', '\uFE9C', '\uFE9A'), # Theh
    '\u062C': ('\uFE9D', '\uFE9F', '\uFEA0', '\uFE9E'), # Jeem
    '\u062D': ('\uFEA1', '\uFEA3', '\uFEA4', '\uFEA2'), # Hah
    '\u062E': ('\uFEA5', '\uFEA7', '\uFEA8', '\uFEA6'), # Khah
    '\u062F': ('\uFEA9', None, None, '\uFEAA'), # Dal
    '\u0630': ('\uFEAB', None, None, '\uFEAC'), # Thal
    '\u0631': ('\uFEAD', None, None, '\uFEAE'), # Reh
    '\u0632': ('\uFEAF', None, None, '\uFEB0'), # Zain
    '\u0633': ('\uFEB1', '\uFEB3', '\uFEB4', '\uFEB2'), # Seen
    '\u0634': ('\uFEB5', '\uFEB7', '\uFEB8', '\uFEB6'), # Sheen
    '\u0635': ('\uFEB9', '\uFEBB', '\uFEBC', '\uFEBA'), # Sad
    '\u0636': ('\uFEBD', '\uFEBF', '\uFEC0', '\uFEBE'), # Dad
    '\u0637': ('\uFEC1', '\uFEC3', '\uFEC4', '\uFEC2'), # Tah
    '\u0638': ('\uFEC5', '\uFEC7', '\uFEC8', '\uFEC6'), # Zah
    '\u0639': ('\uFEC9', '\uFECB', '\uFECC', '\uFECA'), # Ain
    '\u063A': ('\uFECD', '\uFECF', '\uFED0', '\uFECE'), # Ghain
    '\u0641': ('\uFED1', '\uFED3', '\uFED4', '\uFED2'), # Feh
    '\u0642': ('\uFED5', '\uFED7', '\uFED8', '\uFED6'), # Qaf
    '\u0643': ('\uFED9', '\uFEDB', '\uFEDC', '\uFEDA'), # Kaf
    '\u0644': ('\uFEDD', '\uFEDF', '\uFEE0', '\uFEDE'), # Lam
    '\u0645': ('\uFEE1', '\uFEE3', '\uFEE4', '\uFEE2'), # Meem
    '\u0646': ('\uFEE5', '\uFEE7', '\uFEE8', '\uFEE6'), # Noon
    '\u0647': ('\uFEE9', '\uFEEB', '\uFEEC', '\uFEEA'), # Heh
    '\u0648': ('\uFEED', None, None, '\uFEEE'), # Waw
    '\u0649': ('\uFEEF', None, None, '\uFEF0'), # Alef Maksura
    '\u064A': ('\uFEF1', '\uFEF3', '\uFEF4', '\uFEF2'), # Yeh
}

def shape_arabic(text: str) -> str:
    """Connects cursive Arabic letters into initial, medial, final, or isolated glyphs."""
    if not any('\u0600' <= char <= '\u06FF' for char in text):
        return text

    n = len(text)
    shaped = []
    for i, ch in enumerate(text):
        if ch not in ARABIC_JOINING:
            shaped.append(ch)
            continue

        iso, ini, med, fin = ARABIC_JOINING[ch]
        # Check if preceding character can connect from the right
        prev_connects = False
        if i > 0 and text[i - 1] in ARABIC_JOINING:
            p_iso, p_ini, p_med, p_fin = ARABIC_JOINING[text[i - 1]]
            prev_connects = (p_ini is not None)

        # Check if succeeding character can connect from the left
        next_connects = False
        if i < n - 1 and text[i + 1] in ARABIC_JOINING:
            next_connects = True

        if prev_connects and next_connects and med:
            shaped.append(med)
        elif prev_connects and fin:
            shaped.append(fin)
        elif next_connects and ini:
            shaped.append(ini)
        else:
            shaped.append(iso)

    return get_display("".join(shaped))


class TypographyEngine:
    """Specialist Typography & Font Engine (E5)."""

    def __init__(self, font_dir: Optional[Path] = None):
        self.font_dir = font_dir

    def resolve_font(self, font_family: str, font_size_pt: float) -> Tuple[ImageFont.ImageFont, str]:
        """Resolves font from bundled assets, configured font_dir, system fonts, or default."""
        size_px = max(10, int(font_size_pt * 1.333))

        # 1. Search font_dir if explicitly provided
        if self.font_dir and Path(self.font_dir).exists():
            for ext in (".woff2", ".ttf", ".otf", ".woff"):
                candidate = Path(self.font_dir) / f"{font_family}{ext}"
                if candidate.exists():
                    try:
                        return ImageFont.truetype(str(candidate), size_px), font_family
                    except Exception:
                        pass

        # 2. Search bundled fonts in frontend/public/fonts
        bundled_dirs = [
            Path("frontend/public/fonts"),
            Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "public" / "fonts",
        ]
        font_map = {
            "cairo": "NotoSansArabic-Bold",
            "tajawal": "NotoSansArabic-Regular",
            "amiri": "NotoSansArabic-Regular",
            "noto": "NotoSansArabic-Regular",
            "notosans": "NotoSansArabic-Regular",
            "notosansarabic": "NotoSansArabic-Regular",
            "arabic": "NotoSansArabic-Regular",
            "bangers": "Bangers-Regular",
            "comic neue": "ComicNeue-Bold",
            "comicneue": "ComicNeue-Bold",
            "comic": "ComicNeue-Bold",
        }
        normalized_name = font_family.lower().replace("-", "").replace(" ", "")
        target_name = font_map.get(normalized_name, font_family)

        for bdir in bundled_dirs:
            if bdir.exists():
                for ext in (".woff2", ".ttf", ".otf"):
                    for candidate_stem in (
                        target_name,
                        font_family,
                        f"{font_family}-Regular",
                        f"{font_family}-Bold",
                        "NotoSansArabic-Regular",
                        "ComicNeue-Bold",
                    ):
                        candidate = bdir / f"{candidate_stem}{ext}"
                        if candidate.exists():
                            try:
                                return ImageFont.truetype(str(candidate), size_px), candidate_stem
                            except Exception:
                                pass

        # 3. Search system fonts fallback
        for system_candidate in [
            f"C:/Windows/Fonts/{font_family}.ttf",
            f"C:/Windows/Fonts/arial.ttf",
            f"C:/Windows/Fonts/seguiemj.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            if Path(system_candidate).exists():
                try:
                    return ImageFont.truetype(system_candidate, size_px), Path(system_candidate).stem
                except Exception:
                    pass

        return ImageFont.load_default(), "default"

    def shape_and_measure_text(
        self,
        params: TypographyParams,
        asset_registry: Optional[AssetRegistry] = None,
        project_id: str = "default_project",
    ) -> TypographyOutput:
        """
        Shapes Arabic/mixed text, calculates word wrapping within max_width_px,
        measures total pixel bounding box, and creates a lettering layer artifact.
        """
        font, actual_font = self.resolve_font(params.font_family, params.font_size_pt)
        is_arabic = params.language.lower() in ("ar", "arabic") or any('\u0600' <= c <= '\u06FF' for c in params.text_content)

        # 1. Shape text
        processed_raw = shape_arabic(params.text_content) if is_arabic else params.text_content

        # 2. Wrap lines
        words = processed_raw.split(" ")
        lines: List[str] = []
        current_line: List[str] = []

        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy_img)

        for w in words:
            candidate = " ".join(current_line + [w])
            bbox = draw.textbbox((0, 0), candidate, font=font)
            line_w = bbox[2] - bbox[0]
            if line_w <= params.max_width_px or not current_line:
                current_line.append(w)
            else:
                lines.append(" ".join(current_line))
                current_line = [w]

        if current_line:
            lines.append(" ".join(current_line))

        line_count = len(lines)
        line_height = int(params.font_size_pt * params.line_height_multiplier * 1.333)
        total_height = max(line_count * line_height, 20)
        max_line_width = 0

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            max_line_width = max(max_line_width, bbox[2] - bbox[0])

        max_line_width = max(max_line_width, 10)
        text_overflow = max_line_width > params.max_width_px

        # 3. Render lettering layer onto transparent RGBA canvas
        layer_img = Image.new("RGBA", (int(max_line_width + 10), int(total_height + 10)), (0, 0, 0, 0))
        layer_draw = ImageDraw.Draw(layer_img)

        y_offset = 5
        for line in lines:
            layer_draw.text((5, y_offset), line, font=font, fill=params.color_hex)
            y_offset += line_height

        # 4. Ingest into asset registry if supplied
        buf = BytesIO()
        layer_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        artifact_id = f"lettering_{hashlib.sha256(png_bytes).hexdigest()[:12]}"

        if asset_registry:
            asset = asset_registry.ingest_bytes(
                png_bytes,
                f"{artifact_id}.png",
                project_id=project_id,
                asset_type=AssetType.GENERIC_ARTIFACT,
                name=f"Lettering layer for {params.text_block_artifact_id}",
                extra_metadata={
                    "font_family": actual_font,
                    "font_size_pt": params.font_size_pt,
                    "language": params.language,
                    "line_count": line_count,
                },
            )
            artifact_id = asset.asset_id

        return TypographyOutput(
            lettering_layer_artifact_id=artifact_id,
            measured_bounds=Rect(x=0, y=0, width=float(max_line_width), height=float(total_height)),
            line_count=line_count,
            actual_font_used=actual_font,
            text_overflow=text_overflow,
        )

    def render_text_block_to_layer(
        self,
        script_block: Any,
        max_width_px: float = 300.0,
        font_family: Optional[str] = None,
        font_size_pt: float = 16.0,
        color_hex: str = "#111111",
        asset_registry: Optional[AssetRegistry] = None,
        project_id: str = "default_project",
    ) -> TypographyOutput:
        """
        Renders a structured ScriptBlock directly into a measured TypographyOutput artifact.
        """
        lang = getattr(script_block, "language", None)
        lang_str = getattr(lang, "value", str(lang or "ar")).lower()
        if not font_family:
            font_family = "NotoSansArabic" if "ar" in lang_str else "ComicNeue"

        text_content = getattr(script_block, "text_content", str(script_block))
        block_id = getattr(script_block, "block_id", "blk_direct")

        params = TypographyParams(
            text_block_artifact_id=block_id,
            text_content=text_content,
            font_family=font_family,
            font_size_pt=font_size_pt,
            max_width_px=max_width_px,
            color_hex=color_hex,
            language=lang_str,
        )
        return self.shape_and_measure_text(params, asset_registry=asset_registry, project_id=project_id)
