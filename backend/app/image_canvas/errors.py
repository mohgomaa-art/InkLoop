"""
InkLoop Image-Canvas Integration Engine (E3) - Error Definitions.
Defines machine-readable, typed domain exceptions mapping to InkLoop ErrorCodes.
"""
from typing import Optional, Dict, Any
from app.contracts.errors import ErrorCode

class PlacementError(Exception):
    """Base exception for all Image-Canvas Integration Engine (E3) errors."""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.INVALID_SCHEMA, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class InvalidPlacementGeometryError(PlacementError):
    """Raised when target slot or source image has zero, negative, or non-finite dimensions."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.ZERO_OR_NEGATIVE_DIMENSION, details=details)

class AssetResolutionError(PlacementError):
    """Raised when an input artifact reference cannot be resolved from the asset registry or storage."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.UNKNOWN_ENTITY_REFERENCE, details=details)

class UnsupportedImageFormatError(PlacementError):
    """Raised when source asset content cannot be parsed as a supported raster format (PNG, WebP, JPEG)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.INVALID_SCHEMA, details=details)

class AllocationLimitExceededError(PlacementError):
    """Raised when source or target image dimensions exceed memory safety thresholds."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.ZERO_OR_NEGATIVE_DIMENSION, details=details)

class AspectRatioDistortionError(PlacementError):
    """Raised when fitting violates aspect ratio constraints without explicit distortion approval."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.ASPECT_RATIO_DISTORTION, details=details)
