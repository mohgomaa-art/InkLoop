"""Measured lettering layout shared by bubble planning and renderers."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import ImageFont

from app.canvas.bubble_registry import BUBBLE_TYPE_BY_ID
from app.text.typography import TypographyEngine, shape_arabic


_WORD_PATTERN = re.compile(r"(?u)[\w]+(?:[’'-][\w]+)*")
_ARABIC_PATTERN = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")


def count_words(text: str) -> int:
    return len(_WORD_PATTERN.findall(text or ""))


class LetteringValidationError(ValueError):
    """A machine-readable lettering contract error."""

    def __init__(self, code: str, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


@dataclass(frozen=True)
class LetteringLayout:
    type_id: str
    text: str
    lines: List[str]
    direction: str
    font_family: str
    measured_font_family: str
    font_size_px: int
    min_font_size_px: int
    max_font_size_px: int
    word_limit: int
    max_lines: int
    line_height_px: float
    content_width_px: float
    content_height_px: float
    available_width_px: float
    available_height_px: float
    word_count: int
    line_count: int
    measurement_source: str
    overflow: bool
    diagnostics: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def type_id_for_text(
    *,
    type_id: Optional[str] = None,
    carrier: Optional[str] = None,
    content_kind: Optional[str] = None,
    delivery: Optional[str] = None,
) -> str:
    """Resolve old carrier/content-kind values to a canonical type ID."""
    if type_id:
        if type_id not in BUBBLE_TYPE_BY_ID:
            raise LetteringValidationError(
                "ERR_BUBBLE_TYPE_UNKNOWN",
                f"Unknown bubble type '{type_id}'.",
                {"type_id": type_id, "valid_type_ids": list(BUBBLE_TYPE_BY_ID)},
            )
        return type_id
    carrier_key = str(carrier or "").strip().casefold().replace("-", "_")
    kind_key = str(content_kind or "").strip().casefold().replace("-", "_")
    delivery_key = str(delivery or "").strip().casefold()
    if carrier_key in {"thought", "thought_bubble", "thought_cloud"} or kind_key == "internal_thought":
        return "thought.cloud"
    if carrier_key in {"off_panel", "offpanel", "off_panel_bubble", "radio", "broadcast"} or delivery_key in {"remote", "off_panel", "offpanel"}:
        return "speech.offpanel"
    if carrier_key in {"narration", "narration_box", "narration_caption"}:
        return "narration.box"
    if kind_key == "date_or_place":
        return "caption.timeplace"
    if carrier_key in {"caption", "caption_box", "time_place"}:
        return "narration.box" if kind_key == "narration" else "caption.timeplace"
    if carrier_key in {"sfx", "sound_effect", "sfx_text"} or kind_key in {"sound_effect", "sfx"}:
        return "sfx.text"
    if delivery_key in {"shout", "shouting", "yell", "scream"}:
        return "speech.shout"
    if delivery_key in {"whisper", "whispering"}:
        return "speech.whisper"
    return "speech.normal"


def _shape_for_measurement(value: str) -> str:
    return shape_arabic(value) if _ARABIC_PATTERN.search(value or "") else value


def _measure(font: Any, value: str) -> float:
    shaped = _shape_for_measurement(value)
    try:
        return float(font.getlength(shaped))
    except (AttributeError, TypeError):
        box = font.getbbox(shaped)
        return float(max(0, box[2] - box[0]))


def _wrap_text(text: str, width: float, font: Any) -> List[str]:
    """Wrap at word boundaries, preserving explicit authored line breaks."""
    lines: List[str] = []
    for paragraph in (text or "").splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            proposal = f"{current} {word}".strip()
            if current and _measure(font, proposal) > width:
                lines.append(current)
                current = word
            else:
                current = proposal
        if current:
            lines.append(current)
    return lines or [""]


def layout_lettering_text(
    text: str,
    type_id: str,
    *,
    max_width_px: float,
    max_height_px: float,
    font_family: str = "Comic Neue",
    requested_font_size_px: Optional[float] = None,
    line_height_multiplier: float = 1.15,
    font_path: Optional[str | Path] = None,
    typography_engine: Optional[TypographyEngine] = None,
) -> LetteringLayout:
    """Measure, wrap, and fit exact text within the registered type contract.

    A word-limit violation is an error with fields callers can return directly.
    If even the minimum registered font cannot fit, the original words remain
    intact and the result carries an explicit overflow diagnostic.
    """
    spec = BUBBLE_TYPE_BY_ID.get(type_id)
    if spec is None:
        raise LetteringValidationError(
            "ERR_BUBBLE_TYPE_UNKNOWN", f"Unknown bubble type '{type_id}'.",
            {"type_id": type_id, "valid_type_ids": list(BUBBLE_TYPE_BY_ID)},
        )
    text = str(text or "")
    if not text.strip():
        raise LetteringValidationError(
            "ERR_LETTERING_TEXT_REQUIRED", "Lettering text must contain at least one visible character.",
            {"type_id": type_id},
        )
    words = count_words(text)
    if words > spec.word_limit:
        raise LetteringValidationError(
            "ERR_LETTERING_WORD_LIMIT",
            f"{spec.label} allows at most {spec.word_limit} words; received {words}. Edit or split the line.",
            {"type_id": type_id, "word_count": words, "word_limit": spec.word_limit},
        )
    if max_width_px <= 0 or max_height_px <= 0:
        raise LetteringValidationError(
            "ERR_LETTERING_AREA_INVALID", "Lettering needs a positive available width and height.",
            {"available_width_px": max_width_px, "available_height_px": max_height_px},
        )

    engine = typography_engine or TypographyEngine()
    requested = spec.max_font_px if requested_font_size_px is None else int(round(requested_font_size_px))
    requested = max(spec.min_font_px, min(spec.max_font_px, requested))
    use_arabic_font = bool(_ARABIC_PATTERN.search(text)) and not any(
        marker in font_family.casefold() for marker in ("arabic", "noto")
    )
    resolved_family = "NotoSansArabic" if use_arabic_font else font_family
    direction = "rtl" if _ARABIC_PATTERN.search(text) else "ltr"
    candidates: List[Tuple[int, Any, str, List[str], float, float, float]] = []

    for font_px in range(requested, spec.min_font_px - 1, -1):
        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), font_px)
                actual_family = Path(font_path).stem
            except (OSError, ValueError) as exc:
                raise LetteringValidationError(
                    "ERR_FONT_ASSET_UNAVAILABLE", "The selected font could not be loaded for measurement.",
                    {"font_family": font_family, "font_path": str(font_path)},
                ) from exc
        else:
            font, actual_family = engine.resolve_font(resolved_family, font_px / 1.333)
        lines = _wrap_text(text, max_width_px, font)
        line_widths = [_measure(font, line) for line in lines]
        line_height = max(1.0, font_px * float(line_height_multiplier))
        content_width = max(line_widths, default=0.0)
        content_height = len(lines) * line_height
        candidates.append((font_px, font, actual_family, lines, content_width, content_height, line_height))
        if (
            len(lines) <= spec.max_lines
            and content_width <= max_width_px + 0.5
            and content_height <= max_height_px + 0.5
        ):
            return LetteringLayout(
                type_id=type_id, text=text, lines=lines, direction=direction,
                font_family=font_family, measured_font_family=actual_family,
                font_size_px=font_px, min_font_size_px=spec.min_font_px,
                max_font_size_px=spec.max_font_px, word_limit=spec.word_limit,
                max_lines=spec.max_lines, line_height_px=round(line_height, 2),
                content_width_px=round(content_width, 2), content_height_px=round(content_height, 2),
                available_width_px=round(max_width_px, 2), available_height_px=round(max_height_px, 2),
                word_count=words, line_count=len(lines), measurement_source="Pillow shaped-font metrics",
                overflow=False, diagnostics=[],
            )

    font_px, _font, actual_family, lines, content_width, content_height, line_height = candidates[-1]
    diagnostic_code = "ERR_LETTERING_LINE_LIMIT" if len(lines) > spec.max_lines else "ERR_LETTERING_MIN_FONT_OVERFLOW"
    diagnostic_message = (
        f"Text needs {len(lines)} lines, above the {spec.max_lines}-line {spec.label.lower()} limit."
        if diagnostic_code == "ERR_LETTERING_LINE_LIMIT"
        else f"Text still exceeds the {spec.label.lower()} area at the {spec.min_font_px}px minimum font size."
    )
    diagnostic = {
        "code": diagnostic_code,
        "message": diagnostic_message,
        "details": {
            "type_id": type_id,
            "font_size_px": spec.min_font_px,
            "max_lines": spec.max_lines,
            "line_count": len(lines),
            "content_width_px": round(content_width, 2),
            "content_height_px": round(content_height, 2),
            "available_width_px": round(max_width_px, 2),
            "available_height_px": round(max_height_px, 2),
        },
    }
    return LetteringLayout(
        type_id=type_id, text=text, lines=lines, direction=direction,
        font_family=font_family, measured_font_family=actual_family,
        font_size_px=font_px, min_font_size_px=spec.min_font_px,
        max_font_size_px=spec.max_font_px, word_limit=spec.word_limit,
        max_lines=spec.max_lines, line_height_px=round(line_height, 2),
        content_width_px=round(content_width, 2), content_height_px=round(content_height, 2),
        available_width_px=round(max_width_px, 2), available_height_px=round(max_height_px, 2),
        word_count=words, line_count=len(lines), measurement_source="Pillow shaped-font metrics",
        overflow=True, diagnostics=[diagnostic],
    )
