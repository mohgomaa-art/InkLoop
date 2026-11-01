"""
InkLoop Image File Inspector & Safety Gate.
Enforces strict file size bounds, decompression-bomb guards, magic-byte inspection,
and streaming SHA-256 verification without credential or path leakage.
"""
import io
import hashlib
import re
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from PIL import Image

from app.config import PROJECT_ROOT
from app.contracts.identity import generate_id, IdPrefix
from app.agent.schemas import AgentAttachment

# Security bounds
MAX_FILE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_IMAGE_WIDTH = 8192
MAX_IMAGE_HEIGHT = 8192
MAX_PIXEL_COUNT = 67_108_864  # ~67 Megapixels guard against decompression bombs
_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_ATTACHMENT_ID_RE = re.compile(r"^att_[a-f0-9]{12}$")

# Accepted magic headers
MAGIC_HEADERS = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",  # WebP begins with RIFF....WEBP
}

class ImageInspectionError(Exception):
    """Raised when an image attachment violates security or format invariants."""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message

def detect_mime_from_bytes(data: bytes) -> str:
    """Verifies file type strictly from magic bytes."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    raise ImageInspectionError("ERR_ATTACHMENT_INVALID_FORMAT", "Unsupported image format. Allowed formats: PNG, JPEG, WebP.")


def _attachment_project_dir(project_id: str) -> Path:
    if not _PROJECT_ID_RE.fullmatch(project_id):
        raise ImageInspectionError("ERR_INVALID_PROJECT_ID", "Project ID contains unsupported characters.")
    root = (PROJECT_ROOT / "runs" / "artifact_store" / "attachments").resolve()
    project_dir = root / project_id
    if project_dir.is_symlink() or project_dir.resolve().parent != root:
        raise ImageInspectionError("ERR_INVALID_PROJECT_ID", "Project attachment directory is invalid.")
    return project_dir


def resolve_attachment_path(attachment_id: str, project_id: str = "default_project") -> Path:
    """Resolve a client-safe attachment or registered asset ID to a trusted image file."""
    if _ATTACHMENT_ID_RE.fullmatch(attachment_id or ""):
        project_dir = _attachment_project_dir(project_id)
        for suffix in (".png", ".jpg", ".webp"):
            candidate = project_dir / f"{attachment_id}{suffix}"
            if candidate.is_file() and not candidate.is_symlink():
                if candidate.stat().st_size > MAX_FILE_BYTES:
                    raise ImageInspectionError("ERR_ATTACHMENT_TOO_LARGE", "Stored image exceeds the supported attachment size.")
                resolved = candidate.resolve()
                if resolved.parent == project_dir.resolve():
                    content = resolved.read_bytes()
                    if not hashlib.sha256(content).hexdigest().startswith(attachment_id.removeprefix("att_")):
                        raise ImageInspectionError("ERR_ATTACHMENT_INTEGRITY", "Stored attachment failed its content hash check.")
                    detect_mime_from_bytes(content)
                    return resolved
        raise ImageInspectionError("ERR_ATTACHMENT_NOT_FOUND", "Attachment was not found in this project.")

    # Generated and library assets are resolved through the content-addressed registry,
    # which validates the ID and never accepts a caller-provided filesystem path.
    try:
        from app.api.routers.assets import get_registry
        registry = get_registry()
        metadata = registry.get_asset(attachment_id)
        if metadata is None or metadata.mime_type not in ("image/png", "image/jpeg", "image/webp") or metadata.byte_size > MAX_FILE_BYTES:
            raise ImageInspectionError("ERR_ATTACHMENT_NOT_FOUND", "Attachment or registered image asset was not found.")
        is_shared_canonical = bool(metadata.extra_metadata.get("is_canonical_anchor"))
        if metadata.project_id != project_id and not is_shared_canonical:
            raise ImageInspectionError("ERR_ATTACHMENT_NOT_FOUND", "Attachment or registered asset was not found in this project.")
        resolved_asset = registry.resolve_asset(attachment_id, verify_integrity=True)
        path = Path(resolved_asset.absolute_path).resolve(strict=True)
        store_root = (PROJECT_ROOT / "runs" / "artifact_store").resolve()
        if path.is_file() and path.is_relative_to(store_root):
            return path
    except ImageInspectionError:
        raise
    except Exception:
        pass
    raise ImageInspectionError("ERR_ATTACHMENT_NOT_FOUND", "Attachment or registered asset was not found.")

def inspect_image_bytes(data: bytes, filename: str = "attachment.png", project_id: str = "default_project") -> AgentAttachment:
    """
    Safely inspects raw image bytes, calculates SHA-256, verifies dimensions,
    guards against decompression bombs, and stores in the project attachment repository.
    """
    # 1. Size guard
    byte_len = len(data)
    if byte_len == 0:
        raise ImageInspectionError("ERR_ATTACHMENT_ZERO_BYTES", "Image data is empty (0 bytes).")
    if byte_len > MAX_FILE_BYTES:
        raise ImageInspectionError(
            "ERR_ATTACHMENT_TOO_LARGE",
            f"Image file exceeds maximum allowable size of 15MB (received {byte_len} bytes)."
        )

    # 2. Magic bytes inspection
    mime_type = detect_mime_from_bytes(data)

    # 3. Streaming SHA-256 digest
    sha256 = hashlib.sha256(data).hexdigest()

    # 4. Safe decode & decompression bomb check
    try:
        # Avoid PIL decompression bomb dos
        Image.MAX_IMAGE_PIXELS = MAX_PIXEL_COUNT
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            if width <= 0 or height <= 0:
                raise ImageInspectionError("ERR_ATTACHMENT_INVALID_DIMENSIONS", "Image dimensions must be strictly positive.")
            if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
                raise ImageInspectionError(
                    "ERR_ATTACHMENT_DIMENSIONS_EXCEEDED",
                    f"Image dimensions ({width}x{height}) exceed maximum allowed limit of {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}."
                )
            if width * height > MAX_PIXEL_COUNT:
                raise ImageInspectionError(
                    "ERR_ATTACHMENT_DECOMPRESSION_BOMB",
                    "Image pixel volume exceeds maximum safe decompression capacity."
                )
    except ImageInspectionError:
        raise
    except Exception as e:
        raise ImageInspectionError("ERR_ATTACHMENT_DECODE_FAILED", f"Failed to decode image: {e}")

    # 5. Persist safely in project-scoped storage
    att_dir = _attachment_project_dir(project_id)
    att_dir.mkdir(parents=True, exist_ok=True)

    att_id = f"att_{sha256[:12]}"
    ext = ".png" if mime_type == "image/png" else (".jpg" if mime_type == "image/jpeg" else ".webp")
    storage_path = att_dir / f"{att_id}{ext}"
    if storage_path.exists():
        if storage_path.is_symlink() or not storage_path.is_file():
            raise ImageInspectionError("ERR_ATTACHMENT_INTEGRITY", "Stored attachment path is invalid.")
        existing_hash = hashlib.sha256(storage_path.read_bytes()).hexdigest()
        if existing_hash != sha256:
            raise ImageInspectionError("ERR_ATTACHMENT_ID_COLLISION", "Attachment identifier collides with different stored image content.")
    else:
        storage_path.write_bytes(data)

    return AgentAttachment(
        attachment_id=att_id,
        filename=Path(filename).name,  # Strip any directory traversal
        mime_type=mime_type,
        byte_size=byte_len,
        content_sha256=sha256,
        width=width,
        height=height,
        is_canonical_anchor=False,
    )
