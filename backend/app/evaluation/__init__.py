"""
InkLoop Visual Evaluation & Experimental Design Framework (Task T6.2).
Public API exports for controlled experiments, frozen configurations, blind human
evaluation, uncertainty analysis, visual regression corpus, and historical M0 preservation.
"""
from app.evaluation.enums import (
    ExperimentType,
    ExperimentStatus,
    ReproducibilityLevel,
    EvaluationDimension,
    EvaluationVerdict,
    EvaluatorType,
    SampleOutcomeStatus,
    RegressionDomain,
    RegressionReadiness,
)
from app.evaluation.uncertainty import (
    wilson_score_interval,
    cohens_kappa,
    reconcile_sample_denominator,
)
from app.evaluation.models import (
    FrozenConfig,
    ExperimentArm,
    ExperimentPlan,
    SampleExecutionRecord,
    EvaluationDimensionResult,
    EvaluationRecord,
    UncertaintySummary,
    ExperimentExecutionSummary,
    compute_deterministic_hash,
)
from app.evaluation.blinding import (
    BlindEvaluationItem,
    BlindEvaluationSheet,
    BlindingKeyEntry,
    BlindingKeyMap,
    HumanJudgmentRecord,
    AdjudicatedSampleResult,
    AdjudicationReport,
    BlindingService,
)
from app.evaluation.regression import (
    VisualRegressionCase,
    RegressionEvaluationResult,
    VisualRegressionCorpus,
)
from app.evaluation.m0_adapter import (
    build_m0_experiment_plan,
    load_m0_execution_summary,
    NOUR_REF_SHA256,
)

__all__ = [
    # Enums
    "ExperimentType",
    "ExperimentStatus",
    "ReproducibilityLevel",
    "EvaluationDimension",
    "EvaluationVerdict",
    "EvaluatorType",
    "SampleOutcomeStatus",
    "RegressionDomain",
    "RegressionReadiness",
    # Uncertainty
    "wilson_score_interval",
    "cohens_kappa",
    "reconcile_sample_denominator",
    # Models
    "FrozenConfig",
    "ExperimentArm",
    "ExperimentPlan",
    "SampleExecutionRecord",
    "EvaluationDimensionResult",
    "EvaluationRecord",
    "UncertaintySummary",
    "ExperimentExecutionSummary",
    "compute_deterministic_hash",
    # Blinding
    "BlindEvaluationItem",
    "BlindEvaluationSheet",
    "BlindingKeyEntry",
    "BlindingKeyMap",
    "HumanJudgmentRecord",
    "AdjudicatedSampleResult",
    "AdjudicationReport",
    "BlindingService",
    # Regression
    "VisualRegressionCase",
    "RegressionEvaluationResult",
    "VisualRegressionCorpus",
    # M0 Preservation
    "build_m0_experiment_plan",
    "load_m0_execution_summary",
    "NOUR_REF_SHA256",
]
