"""
InkLoop Asset Registry & Artifact Store (Milestone 1, Task T5.4).
"""
from app.storage.errors import (
    StorageError,
    AssetNotFoundError,
    AssetIntegrityError,
    PathTraversalSecurityError,
    StorageRootEscapeError,
    UnsupportedAssetTypeError,
    InvalidFileFormatError,
    UnregisteredParentError,
    LineageCycleError,
    DuplicateAssetConflictError,
)
from app.storage.models import (
    AssetMetadata,
    ResolvedAsset,
    AssetFilter,
    AssetManifestDocument,
    utc_now_iso,
)
from app.storage.format_validator import (
    validate_file_content,
    IMAGE_EXTENSIONS,
    FONT_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
)
from app.storage.artifact_store import (
    ArtifactStore,
    compute_bytes_sha256,
    compute_file_sha256,
)
from app.storage.registry_db import RegistryDB
from app.storage.registry import AssetRegistry

__all__ = [
    # Core Registry Service
    "AssetRegistry",
    "ArtifactStore",
    "RegistryDB",
    # Models
    "AssetMetadata",
    "ResolvedAsset",
    "AssetFilter",
    "AssetManifestDocument",
    "utc_now_iso",
    # Validation & Utilities
    "validate_file_content",
    "compute_bytes_sha256",
    "compute_file_sha256",
    "IMAGE_EXTENSIONS",
    "FONT_EXTENSIONS",
    "DOCUMENT_EXTENSIONS",
    # Errors
    "StorageError",
    "AssetNotFoundError",
    "AssetIntegrityError",
    "PathTraversalSecurityError",
    "StorageRootEscapeError",
    "UnsupportedAssetTypeError",
    "InvalidFileFormatError",
    "UnregisteredParentError",
    "LineageCycleError",
    "DuplicateAssetConflictError",
]
