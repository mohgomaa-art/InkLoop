"""
InkLoop Canvas Generation Engine (E2) - Error and Exception Definitions.
Defines machine-readable, typed domain exceptions mapping to InkLoop ErrorCodes.
"""
from typing import Optional, Dict, Any
from app.contracts.errors import ErrorCode

class CanvasError(Exception):
    """Base exception for all Canvas Generation Engine (E2) errors."""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.INVALID_SCHEMA, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class CanvasGeometryError(CanvasError):
    """Base exception for spatial and geometry errors in canvas layouts."""
    pass

class InvalidDimensionError(CanvasGeometryError):
    """Raised when canvas, page, margin, or panel dimensions are zero, negative, or non-finite."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.ZERO_OR_NEGATIVE_DIMENSION, details=details)

class OutOfBoundsLayoutError(CanvasGeometryError):
    """Raised when a panel extends outside permissible canvas trim or bleed boundaries."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.OUT_OF_BOUNDS, details=details)

class UnintendedOverlapError(CanvasGeometryError):
    """Raised when two panels intersect without explicit intentional overlap declaration."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.PANEL_UNINTENDED_OVERLAP, details=details)

class ImpossibleLayoutError(CanvasGeometryError):
    """Raised when requested margins, gutters, or panel counts cannot fit within canvas extents."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.IMPOSSIBLE_FIT, details=details)

class TemplateNotFoundError(CanvasError):
    """Raised when an unknown or unsupported layout template name is requested."""
    def __init__(self, template_name: str, available_templates: Optional[list] = None):
        msg = f"Unknown layout template: '{template_name}'."
        if available_templates:
            msg += f" Available templates: {available_templates}"
        super().__init__(msg, code=ErrorCode.INVALID_SCHEMA, details={"template": template_name, "available": available_templates or []})

class AllocationLimitExceededError(CanvasError):
    """Raised when requested canvas dimensions or pixel counts exceed memory safety ceilings."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=ErrorCode.ZERO_OR_NEGATIVE_DIMENSION, details=details)
