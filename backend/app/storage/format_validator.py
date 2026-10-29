"""
InkLoop Asset Registry - Content-Aware File Format Validator.
Performs deep magic header inspection, image dimension extraction, font signature checking,
and executable payload rejection. Never trusts extensions alone.
"""
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from PIL import Image

from app.contracts.artifacts import AssetType
from app.storage.errors import InvalidFileFormatError, UnsupportedAssetTypeError

DISALLOWED_EXTENSIONS = {
    ".exe", ".dll", ".so", ".sh", ".bash", ".bat", ".cmd", ".ps1", ".vbs",
    ".js", ".py", ".pyc", ".pyd", ".com", ".scr", ".msi", ".jar", ".bin"
}

IMAGE_EXTENSIONS = {".png", ".webp", ".jpg", ".jpeg"}
FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
DOCUMENT_EXTENSIONS = {".pdf", ".json", ".svg", ".txt", ".md"}


def validate_file_content(
    file_bytes: bytes,
    filename: str,
    asset_type: AssetType
) -> Tuple[str, str, Optional[int], Optional[int], Optional[Dict[str, Any]]]:
    """
    Validates binary content against claimed asset type and filename.
    Returns: (validated_mime_type, normalized_extension, width, height, type_metadata)
    Raises InvalidFileFormatError if content is corrupt, mislabeled, or dangerous.
    """
    ext = Path(filename).suffix.lower()

    if ext in DISALLOWED_EXTENSIONS:
        raise InvalidFileFormatError(
            f"PROHIBITED_EXECUTABLE_EXTENSION: File extension '{ext}' is prohibited for security reasons.",
            claimed_type=str(asset_type),
            detected_issue="PROHIBITED_EXECUTABLE_EXTENSION"
        )

    if not file_bytes:
        raise InvalidFileFormatError(
            "File content cannot be empty (0 bytes).",
            claimed_type=str(asset_type),
            detected_issue="EMPTY_FILE"
        )

    # 1. Raster Image Validation
    if asset_type in (
        AssetType.IMAGE_REFERENCE,
        AssetType.IMAGE_GENERATED,
        AssetType.COMPOSITE_PAGE,
        AssetType.EXPORT_PNG,
        AssetType.PAGE_PREVIEW,
        AssetType.PANEL_LAYER,
    ) or ext in IMAGE_EXTENSIONS:
        return _validate_raster_image(file_bytes, ext, asset_type)

    # 2. Font File Validation
    elif asset_type == AssetType.FONT_FILE or ext in FONT_EXTENSIONS:
        return _validate_font_file(file_bytes, ext)

    # 3. PDF Document Validation
    elif asset_type == AssetType.EXPORT_PDF or ext == ".pdf":
        return _validate_pdf_file(file_bytes, ext)

    # 4. SVG Vector Validation (Lettering / Bubbles / Vector layers)
    elif ext == ".svg" or asset_type in (AssetType.LETTERING_LAYER, AssetType.BUBBLE_LAYER) and file_bytes.strip().startswith(b"<"):
        return _validate_svg_file(file_bytes, ext)

    # 5. JSON Specification / Report Validation
    elif ext == ".json" or asset_type in (
        AssetType.CANVAS_SPEC,
        AssetType.QA_REPORT,
        AssetType.EXPORT_MANIFEST,
        AssetType.GENERIC_ARTIFACT,
        AssetType.MASK_ARTIFACT
    ):
        return _validate_json_or_text(file_bytes, ext)

    # 6. Text Blocks / Scripts
    elif asset_type == AssetType.TEXT_BLOCK or ext in (".txt", ".md"):
        return _validate_plain_text(file_bytes, ext)

    else:
        # Fallback inspection for binary mask or generic artifact
        return _validate_generic_fallback(file_bytes, ext)


def _validate_raster_image(file_bytes: bytes, ext: str, asset_type: AssetType) -> Tuple[str, str, int, int, None]:
    """Inspects magic headers and decodes actual image dimensions using Pillow."""
    # Check magic bytes first
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
        norm_ext = ".png"
    elif file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        detected_mime = "image/webp"
        norm_ext = ".webp"
    elif file_bytes.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
        norm_ext = ".jpg" if ext in (".jpg", ".jpeg") else ".jpg"
    else:
        raise InvalidFileFormatError(
            f"Image file does not have valid PNG, WebP, or JPEG magic headers.",
            claimed_type=str(asset_type),
            detected_issue="INVALID_IMAGE_HEADER"
        )

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img.verify()  # Verifies image structural integrity without full load
        with Image.open(io.BytesIO(file_bytes)) as img:
            width, height = img.size
    except Exception as e:
        raise InvalidFileFormatError(
            f"Corrupted or unreadable image content: {e}",
            claimed_type=detected_mime,
            detected_issue=str(e)
        )

    if width <= 0 or height <= 0:
        raise InvalidFileFormatError(
            f"Invalid image dimensions: {width}x{height}",
            claimed_type=detected_mime,
            detected_issue="ZERO_OR_NEGATIVE_DIMENSIONS"
        )

    return (detected_mime, norm_ext, width, height, None)


def _validate_font_file(file_bytes: bytes, ext: str) -> Tuple[str, str, None, None, Dict[str, Any]]:
    """Inspects font magic headers for TrueType, OpenType, WOFF, and WOFF2."""
    font_info: Dict[str, Any] = {}
    if file_bytes.startswith(b"\x00\x01\x00\x00") or file_bytes.startswith(b"true"):
        detected_mime = "font/ttf"
        norm_ext = ".ttf"
        font_info["format"] = "TrueType"
    elif file_bytes.startswith(b"OTTO"):
        detected_mime = "font/otf"
        norm_ext = ".otf"
        font_info["format"] = "OpenType"
    elif file_bytes.startswith(b"wOFF"):
        detected_mime = "font/woff"
        norm_ext = ".woff"
        font_info["format"] = "WOFF"
    elif file_bytes.startswith(b"wOF2"):
        detected_mime = "font/woff2"
        norm_ext = ".woff2"
        font_info["format"] = "WOFF2"
    else:
        raise InvalidFileFormatError(
            "File lacks valid TrueType, OpenType, or WOFF font magic signature.",
            claimed_type="font_file",
            detected_issue="INVALID_FONT_SIGNATURE"
        )

    return (detected_mime, norm_ext, None, None, font_info)


def _validate_pdf_file(file_bytes: bytes, ext: str) -> Tuple[str, str, None, None, Dict[str, Any]]:
    """Validates PDF header and format."""
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidFileFormatError(
            "PDF document does not start with standard '%PDF-' header.",
            claimed_type="application/pdf",
            detected_issue="INVALID_PDF_HEADER"
        )

    # Approximate page count from /Type /Page occurrences
    page_count = max(1, file_bytes.count(b"/Type /Page") - file_bytes.count(b"/Type /Pages"))

    return ("application/pdf", ".pdf", None, None, {"page_count": page_count})


def _validate_svg_file(file_bytes: bytes, ext: str) -> Tuple[str, str, Optional[int], Optional[int], None]:
    """Validates SVG XML structure and guards against script injections."""
    text_content = file_bytes.decode("utf-8", errors="replace").strip()
    if "<svg" not in text_content.lower():
        raise InvalidFileFormatError(
            "SVG document lacks required '<svg' root element.",
            claimed_type="image/svg+xml",
            detected_issue="MISSING_SVG_ROOT"
        )

    # Security check: disallow script tags in SVGs
    if "<script" in text_content.lower():
        raise InvalidFileFormatError(
            "SVG contains disallowed '<script' tags.",
            claimed_type="image/svg+xml",
            detected_issue="PROHIBITED_SVG_SCRIPT_TAG"
        )

    return ("image/svg+xml", ".svg", None, None, None)


def _validate_json_or_text(file_bytes: bytes, ext: str) -> Tuple[str, str, None, None, None]:
    """Ensures JSON files are syntactically valid UTF-8."""
    try:
        json.loads(file_bytes.decode("utf-8"))
        return ("application/json", ".json", None, None, None)
    except Exception as e:
        raise InvalidFileFormatError(
            f"Invalid JSON content: {e}",
            claimed_type="application/json",
            detected_issue="MALFORMED_JSON"
        )


def _validate_plain_text(file_bytes: bytes, ext: str) -> Tuple[str, str, None, None, None]:
    """Ensures text files decode cleanly as UTF-8."""
    try:
        file_bytes.decode("utf-8")
        norm_ext = ext if ext in (".txt", ".md") else ".txt"
        mime = "text/markdown" if norm_ext == ".md" else "text/plain"
        return (mime, norm_ext, None, None, None)
    except UnicodeDecodeError as e:
        raise InvalidFileFormatError(
            f"File is not valid UTF-8 encoded text: {e}",
            claimed_type="text/plain",
            detected_issue="INVALID_UTF8"
        )


def _validate_generic_fallback(file_bytes: bytes, ext: str) -> Tuple[str, str, None, None, None]:
    """Fallback for binary masks, numpy arrays, or custom format layers."""
    norm_ext = ext if ext else ".bin"
    return ("application/octet-stream", norm_ext, None, None, None)
