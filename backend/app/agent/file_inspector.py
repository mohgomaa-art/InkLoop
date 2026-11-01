"""Content-validated storage and text extraction for Agent image/document uploads."""
import hashlib
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app.agent.image_inspector import (
    ImageInspectionError,
    MAX_FILE_BYTES,
    _attachment_project_dir,
    detect_mime_from_bytes,
)
from app.agent.schemas import AgentAttachment

ALLOWED_DOCUMENT_MIMES = {
    "text/plain", "text/markdown", "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_EXTRACTED_CHARS = 100_000
_DOC_EXTENSIONS = {"text/plain": ".txt", "text/markdown": ".md", "application/pdf": ".pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"}


def _extract_document_text(data: bytes, mime: str) -> str:
    if mime in {"text/plain", "text/markdown"}:
        text = data.decode("utf-8-sig", errors="strict")
    elif mime == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data), strict=True)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ImageInspectionError("ERR_DOCUMENT_PARSE_FAILED", "PDF text could not be extracted.") from exc
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            text = "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
        except Exception as exc:
            raise ImageInspectionError("ERR_DOCUMENT_PARSE_FAILED", "DOCX text could not be extracted.") from exc
    text = text.strip()
    if not text:
        raise ImageInspectionError("ERR_DOCUMENT_EMPTY", "Document contains no extractable text.")
    return text[:MAX_EXTRACTED_CHARS]


def _detect_document_mime(data: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        try:
            data.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise ImageInspectionError("ERR_DOCUMENT_ENCODING", "Text documents must use UTF-8 encoding.") from exc
        return "text/markdown" if suffix == ".md" else "text/plain"
    if suffix == ".pdf" and data.startswith(b"%PDF-"):
        return "application/pdf"
    if suffix == ".docx" and data.startswith(b"PK\x03\x04"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    raise ImageInspectionError("ERR_ATTACHMENT_INVALID_FORMAT", "Supported files: PNG, JPEG, WebP, TXT, Markdown, PDF, DOCX.")


def inspect_document_bytes(data: bytes, filename: str, project_id: str = "default_project") -> AgentAttachment:
    if not data:
        raise ImageInspectionError("ERR_ATTACHMENT_ZERO_BYTES", "Document is empty (0 bytes).")
    if len(data) > MAX_FILE_BYTES:
        raise ImageInspectionError("ERR_ATTACHMENT_TOO_LARGE", "File exceeds the supported 15MB upload limit.")
    mime = _detect_document_mime(data, filename)
    _extract_document_text(data, mime)
    sha = hashlib.sha256(data).hexdigest()
    directory = _attachment_project_dir(project_id)
    directory.mkdir(parents=True, exist_ok=True)
    attachment_id = f"att_{sha[:12]}"
    path = directory / f"{attachment_id}{_DOC_EXTENSIONS[mime]}"
    if path.exists():
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ImageInspectionError("ERR_ATTACHMENT_INTEGRITY", "Stored document failed its content hash check.")
    else:
        path.write_bytes(data)
    return AgentAttachment(
        attachment_id=attachment_id,
        filename=Path(filename).name,
        mime_type=mime,
        byte_size=len(data),
        content_sha256=sha,
    )


def resolve_document_path(attachment_id: str, project_id: str) -> Path:
    if not re.fullmatch(r"att_[a-f0-9]{12}", attachment_id or ""):
        raise ImageInspectionError("ERR_ATTACHMENT_NOT_FOUND", "Document was not found in this project.")
    directory = _attachment_project_dir(project_id)
    for suffix in _DOC_EXTENSIONS.values():
        path = directory / f"{attachment_id}{suffix}"
        if path.is_file() and not path.is_symlink():
            content = path.read_bytes()
            if len(content) > MAX_FILE_BYTES or hashlib.sha256(content).hexdigest()[:12] != attachment_id[4:]:
                raise ImageInspectionError("ERR_ATTACHMENT_INTEGRITY", "Stored document failed its content hash check.")
            _extract_document_text(content, _mime_from_suffix(suffix))
            return path.resolve()
    raise ImageInspectionError("ERR_ATTACHMENT_NOT_FOUND", "Document was not found in this project.")


def _mime_from_suffix(suffix: str) -> str:
    return {value: key for key, value in _DOC_EXTENSIONS.items()}[suffix]


def extract_stored_document(path: Path) -> str:
    return _extract_document_text(path.read_bytes(), _mime_from_suffix(path.suffix.lower()))
