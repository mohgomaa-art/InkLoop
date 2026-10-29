"""
InkLoop Asset Registry - Physical Artifact Store.
Manages content-addressed disk storage, atomic file writes, path traversal prevention,
and immutable artifact retention.
"""
import os
import time
import hashlib
from pathlib import Path
from typing import Union, Tuple, Optional

from app.storage.errors import (
    PathTraversalSecurityError,
    StorageRootEscapeError,
    AssetIntegrityError,
    AssetNotFoundError,
)


def compute_bytes_sha256(data: bytes) -> str:
    """Computes hexadecimal SHA-256 checksum for byte content."""
    return hashlib.sha256(data).hexdigest().lower()


def compute_file_sha256(path: Path, chunk_size: int = 65536) -> str:
    """Computes hexadecimal SHA-256 checksum for a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


class ArtifactStore:
    """
    Physical file storage abstraction with content-addressed layout and atomic writes.
    Layout: <store_root>/objects/<hash_prefix>/<sha256><ext>
    """

    def __init__(self, root_dir: Union[str, Path]):
        self.root_dir = Path(root_dir).resolve()
        self.objects_dir = (self.root_dir / "objects").resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.objects_dir.mkdir(parents=True, exist_ok=True)

    def _assert_within_root(self, target_path: Path) -> Path:
        """Enforces that a resolved path strictly resides within the managed storage root."""
        resolved = target_path.resolve()
        try:
            resolved.relative_to(self.root_dir)
        except ValueError:
            raise StorageRootEscapeError(
                f"Storage path escape detected: '{target_path}' escapes managed root '{self.root_dir}'",
                target_path=str(target_path)
            )
        return resolved

    def get_content_path(self, sha256: str, extension: str) -> Tuple[Path, str]:
        """
        Determines the content-addressed destination on disk.
        Returns (absolute_path, relative_path_from_root).
        """
        clean_hash = sha256.lower().strip()
        prefix = clean_hash[:2]
        ext = extension.lower().strip()
        if not ext.startswith("."):
            ext = f".{ext}"

        dest_dir = self.objects_dir / prefix
        dest_file = dest_dir / f"{clean_hash}{ext}"
        self._assert_within_root(dest_file)

        rel_path = str(dest_file.relative_to(self.root_dir)).replace("\\", "/")
        return dest_file, rel_path

    def write_bytes_atomic(self, data: bytes, sha256: str, extension: str) -> Tuple[Path, str]:
        """
        Atomically persists byte data into content-addressed storage.
        If file already exists with identical content, returns existing path without rewriting.
        """
        dest_file, rel_path = self.get_content_path(sha256, extension)
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if dest_file.exists():
            # Verify existing file matches expected hash
            existing_hash = compute_file_sha256(dest_file)
            if existing_hash == sha256:
                return dest_file, rel_path
            # If hash mismatch on disk, overwrite safely with correct content
            pass

        tmp_file = dest_file.with_suffix(f".tmp.{os.getpid()}.{time.time_ns()}")
        try:
            with open(tmp_file, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, dest_file)
        finally:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

        return dest_file, rel_path

    def ingest_file(self, source_path: Union[str, Path], extension: Optional[str] = None) -> Tuple[str, int, Path, str]:
        """
        Ingests an external file into content-addressed managed storage.
        Returns: (sha256, byte_size, absolute_managed_path, relative_managed_path)
        """
        src = Path(source_path).resolve()
        if not src.is_file():
            raise AssetNotFoundError(f"Source file not found at '{src}'", asset_id=str(source_path))

        ext = extension or src.suffix
        content = src.read_bytes()
        sha256 = compute_bytes_sha256(content)
        byte_size = len(content)

        dest_file, rel_path = self.write_bytes_atomic(content, sha256, ext)
        return sha256, byte_size, dest_file, rel_path

    def resolve_managed_path(self, relative_path: str, verify_exists: bool = True) -> Path:
        """
        Resolves a relative storage path to an absolute path, preventing directory traversal.
        """
        # Guard against traversal characters in relative_path
        clean_rel = relative_path.replace("\\", "/").strip()
        if ".." in clean_rel or clean_rel.startswith("/"):
            raise PathTraversalSecurityError(
                f"Path traversal detected in relative path: '{relative_path}'",
                path=relative_path
            )

        target = (self.root_dir / clean_rel).resolve()
        self._assert_within_root(target)

        if verify_exists and not target.is_file():
            raise AssetNotFoundError(
                f"Managed asset file does not exist at '{target}'",
                asset_id=clean_rel
            )

        return target

    def verify_integrity(self, relative_path: str, expected_sha256: str) -> bool:
        """Checks whether a stored file exists and matches its expected SHA-256 digest."""
        target = self.resolve_managed_path(relative_path, verify_exists=False)
        if not target.is_file():
            return False
        actual = compute_file_sha256(target)
        return actual.lower() == expected_sha256.lower().strip()
