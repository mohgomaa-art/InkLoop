"""
InkLoop Text Generation Engine - Public Package Exports (Milestone M5 / Workstream E4).
"""
from app.text.enums import (
    ScriptBlockKind,
    DialogueDelivery,
    CaptionKind,
    SFXCategory,
    TextLanguage,
    TextDirection,
    SourceMode,
    DiagnosticSeverity,
    DiagnosticCode,
)
from app.text.models import (
    SpeakerRef,
    TextProvenance,
    TextValidationDiagnostic,
    ScriptBlock,
    TextScriptManifest,
    TextValidationRequest,
    TextValidationResult,
    TextGenerationRequest,
    TextGenerationResult,
    compute_sha256,
)
from app.text.errors import (
    TextEngineError,
    TextValidationError,
    UndeclaredSpeakerError,
    ExactTextAlterationError,
    NarrativeContinuityConflictError,
    TextAdapterError,
    TextGenerationBlockedError,
)
from app.text.validator import TextDomainValidator
from app.text.adapters import (
    BaseTextGenerationAdapter,
    SimulatedTextGenerationAdapter,
    MetaTextGenerationAdapter,
)
from app.text.engine import TextGenerationEngine

__all__ = [
    "ScriptBlockKind",
    "DialogueDelivery",
    "CaptionKind",
    "SFXCategory",
    "TextLanguage",
    "TextDirection",
    "SourceMode",
    "DiagnosticSeverity",
    "DiagnosticCode",
    "SpeakerRef",
    "TextProvenance",
    "TextValidationDiagnostic",
    "ScriptBlock",
    "TextScriptManifest",
    "TextValidationRequest",
    "TextValidationResult",
    "TextGenerationRequest",
    "TextGenerationResult",
    "compute_sha256",
    "TextEngineError",
    "TextValidationError",
    "UndeclaredSpeakerError",
    "ExactTextAlterationError",
    "NarrativeContinuityConflictError",
    "TextAdapterError",
    "TextGenerationBlockedError",
    "TextDomainValidator",
    "BaseTextGenerationAdapter",
    "SimulatedTextGenerationAdapter",
    "MetaTextGenerationAdapter",
    "TextGenerationEngine",
]
