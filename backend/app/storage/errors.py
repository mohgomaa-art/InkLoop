"""
InkLoop Asset Registry & Artifact Store - Exceptions.
"""
from typing import Optional, Any


class StorageError(Exception):
    """Base exception for all storage and asset registry operations."""
    def __init__(self, message: str, code: str = "STORAGE_ERROR", details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error_code": self.code,
            "message": self.message,
            "details": self.details,
        }


class AssetNotFoundError(StorageError):
    """Raised when an asset ID or file cannot be located in the registry or managed store."""
    def __init__(self, message: str, asset_id: Optional[str] = None):
        super().__init__(message, code="ASSET_NOT_FOUND", details={"asset_id": asset_id})


class AssetIntegrityError(StorageError):
    """Raised when actual file content does not match recorded SHA-256 hash or metadata."""
    def __init__(self, message: str, asset_id: Optional[str] = None, expected_hash: Optional[str] = None, actual_hash: Optional[str] = None):
        super().__init__(
            message,
            code="ASSET_INTEGRITY_MISMATCH",
            details={"asset_id": asset_id, "expected_hash": expected_hash, "actual_hash": actual_hash}
        )


class PathTraversalSecurityError(StorageError):
    """Raised when a file path attempts directory traversal or escapes allowed storage boundaries."""
    def __init__(self, message: str, path: Optional[str] = None):
        super().__init__(message, code="PATH_TRAVERSAL_DETECTED", details={"path": path})


class StorageRootEscapeError(StorageError):
    """Raised when managed storage root boundaries are violated."""
    def __init__(self, message: str, target_path: Optional[str] = None):
        super().__init__(message, code="STORAGE_ROOT_ESCAPE", details={"target_path": target_path})


class UnsupportedAssetTypeError(StorageError):
    """Raised when an unregistered or prohibited asset type is supplied."""
    def __init__(self, message: str, asset_type: Optional[str] = None):
        super().__init__(message, code="UNSUPPORTED_ASSET_TYPE", details={"asset_type": asset_type})


class InvalidFileFormatError(StorageError):
    """Raised when a file's binary content does not match its claimed MIME type or fails validation."""
    def __init__(self, message: str, claimed_type: Optional[str] = None, detected_issue: Optional[str] = None):
        full_msg = f"{detected_issue}: {message}" if detected_issue and not message.startswith(detected_issue) else message
        super().__init__(
            full_msg,
            code="INVALID_FILE_FORMAT",
            details={"claimed_type": claimed_type, "detected_issue": detected_issue}
        )
        self.detected_issue = detected_issue


class UnregisteredParentError(StorageError):
    """Raised when registering a derivative referencing non-existent parent asset IDs."""
    def __init__(self, message: str, missing_parent_id: Optional[str] = None):
        super().__init__(message, code="UNREGISTERED_PARENT_ASSET", details={"missing_parent_id": missing_parent_id})


class LineageCycleError(StorageError):
    """Raised when a derivative registration would introduce a circular lineage dependency."""
    def __init__(self, message: str, asset_id: Optional[str] = None):
        super().__init__(message, code="LINEAGE_CYCLE_DETECTED", details={"asset_id": asset_id})


class DuplicateAssetConflictError(StorageError):
    """Raised when an asset ID is re-registered with conflicting, non-identical metadata."""
    def __init__(self, message: str, asset_id: Optional[str] = None):
        super().__init__(message, code="DUPLICATE_ASSET_CONFLICT", details={"asset_id": asset_id})
