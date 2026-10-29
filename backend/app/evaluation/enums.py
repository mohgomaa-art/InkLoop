"""
InkLoop Visual Evaluation & Experimental Design - Enums & Classifications (Task T6.2).
Defines standard experiment types, reproducibility levels, evaluation dimensions,
verdicts, sample outcome classifications, and visual regression domains.
"""
from enum import Enum


class ExperimentType(str, Enum):
    """Methodological intent of an experiment."""
    EXPLORATORY = "exploratory"
    CONFIRMATORY = "confirmatory"


class ExperimentStatus(str, Enum):
    """Lifecycle status of an experiment specification."""
    DRAFT = "draft"
    FROZEN = "frozen"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"


class ReproducibilityLevel(str, Enum):
    """
    Explicit reproducibility guarantee for a frozen configuration.
    Bitwise pixel determinism is never falsely promised for hosted diffusion models.
    """
    REPRODUCIBLE = "reproducible"              # Exact prompt, params, inputs, and provider seed locked
    PARTIALLY_REPRODUCIBLE = "partially_reproducible"  # Seed unsupported or model update possible, inputs locked
    CANNOT_BE_REPRODUCED = "cannot_be_reproduced"      # Ephemeral/untracked parameters or missing inputs


class EvaluationDimension(str, Enum):
    """Structured assessment dimensions for visual evaluation."""
    CHARACTER_IDENTITY = "character_identity"
    DEFINING_ATTRIBUTES = "defining_attributes"
    STYLE_CONSISTENCY = "style_consistency"
    POSE_AND_ACTION = "pose_and_action"
    COMPOSITION_FRAMING = "composition_framing"
    LIGHTING_AND_CONTRAST = "lighting_and_contrast"
    REFERENCE_ADHERENCE = "reference_adherence"
    UNREQUESTED_CONTENT = "unrequested_content"
    GENERATION_DEFECTS = "generation_defects"
    EVALUABILITY = "evaluability"


class EvaluationVerdict(str, Enum):
    """
    Empirical judgment outcome for an evaluated artifact.
    Distinguishes evaluator decisions from pipeline execution success.
    """
    PASS = "pass"
    FAIL = "fail"
    NEEDS_HUMAN = "needs_human"
    NOT_EVALUABLE = "not_evaluable"


class EvaluatorType(str, Enum):
    """Classification of the evaluation actor."""
    AUTOMATED_VERIFIER = "automated_verifier"  # Code/heuristics/SAM/CLIP
    LLM_JUDGE = "llm_judge"                    # Vision LLM (evaluator, not ground truth)
    HUMAN_EXPERT = "human_expert"              # Domain expert artist/editor
    HUMAN_CROWD = "human_crowd"                # Blind human rater panel


class SampleOutcomeStatus(str, Enum):
    """
    Strict sample lifecycle status ensuring every sample is preserved in denominators.
    No selective deletion of inconvenient outcomes.
    """
    SUCCESS = "success"        # Generated and fully evaluable
    FAILED = "failed"          # Generation error, timeout, or policy crash
    FILTERED = "filtered"      # Dropped by pre-evaluation filter (safety, bad format)
    UNRESOLVED = "unresolved"  # Ambiguous outcome, missing artifact, or evaluator timeout
    CANCELLED = "cancelled"    # Aborted before execution due to run cap/budget
    UNFINISHED = "unfinished"  # Planned but never dispatched


class RegressionDomain(str, Enum):
    """Authoritative visual regression corpus domains."""
    COMPOSITION_FRAMING = "composition_framing"
    CHARACTER_REFERENCE_CONSISTENCY = "character_reference_consistency"
    GENERATION_DEFECTS = "generation_defects"
    TEXT_RENDERING = "text_rendering"
    SPEECH_BUBBLE_GEOMETRY = "speech_bubble_geometry"
    EFFECTS_MOTION = "effects_motion"
    EXPORT_RECONSTRUCTION = "export_reconstruction"


class RegressionReadiness(str, Enum):
    """Readiness state for visual regression test cases."""
    READY = "ready"                        # Test fixtures and producing engine fully operational
    PLANNED = "planned"                    # Case designed but execution pending
    BLOCKED_BY_ENGINE = "blocked_by_engine"# Producing engine is not implemented yet
