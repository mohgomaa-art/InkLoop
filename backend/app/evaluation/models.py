"""
InkLoop Visual Evaluation & Experimental Design Data Models (Task T6.2).
Provides machine-readable schemas for frozen configurations, experiment plans,
sample-level execution tracking, structured visual evaluations, and denominator-checked summaries.
"""
from datetime import datetime, timezone
import hashlib
import json
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict

from app.evaluation.enums import (
    ExperimentType,
    ExperimentStatus,
    ReproducibilityLevel,
    EvaluationDimension,
    EvaluationVerdict,
    EvaluatorType,
    SampleOutcomeStatus,
)
from app.execution.models import CostRecord
from app.evaluation.uncertainty import reconcile_sample_denominator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_deterministic_hash(data: Dict[str, Any]) -> str:
    """Computes a stable SHA-256 hash over deterministically sorted JSON."""
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_secrets_recursively(obj: Any, key_name: str = "") -> None:
    """Recursively audits fields to prevent accidental credential or secret token leakage."""
    k_lower = key_name.lower()
    if any(sec in k_lower for sec in ["api_key", "secret", "authorization", "bearer", "token", "password"]):
        raise ValueError(f"Security violation: Secret field '{key_name}' cannot be placed in FrozenConfig.")
    if isinstance(obj, str):
        if any(sec in obj.lower() for sec in ["bearer ", "eyjhb", "sk-", "api_key="]):
            raise ValueError(f"Security violation: Detected potential secret or token value in '{key_name}'.")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            check_secrets_recursively(v, k)
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            check_secrets_recursively(item, key_name)


class FrozenConfig(BaseModel):
    """
    Immutable frozen configuration specifying all request parameters and inputs.
    Any change to prompt, model, reference asset, or params produces a distinct hash.
    Strictly prohibits secrets, auth headers, or raw API keys.
    """
    provider: str = Field(..., description="Target model provider (e.g. 'meta_ai')")
    model_name: str = Field(..., description="Exact model identifier (e.g. 'muse-image-1.0')")
    adapter_version: str = Field(default="1.0.0", description="Image adapter version")
    prompt: str = Field(..., description="Exact positive prompt clause")
    negative_constraints: List[str] = Field(default_factory=list, description="Negative prompt constraints")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Generation parameters (endpoint, dimensions, n)")
    reference_requirements: Optional[str] = Field(default=None, description="Reference image specs if required")
    input_artifact_ids: List[str] = Field(default_factory=list, description="IDs of input artifacts from Asset Registry")
    input_artifact_hashes: Dict[str, str] = Field(default_factory=dict, description="Artifact ID to SHA-256 mapping")
    canon_snapshot_hash: Optional[str] = Field(default=None, description="Canon snapshot digest if anchored to story canon")
    environment: str = Field(default="production", description="Runtime environment")
    code_version: str = Field(default="1.0.0", description="Git commit or package version")
    seed: Optional[int] = Field(default=None, description="Seed if supported by provider")
    seed_supported: bool = Field(default=False, description="Whether the provider actually supports deterministic seeds")
    reproducibility: ReproducibilityLevel = Field(
        default=ReproducibilityLevel.PARTIALLY_REPRODUCIBLE,
        description="Explicit reproducibility rating"
    )
    config_hash: str = Field(default="", description="Cryptographic digest of this frozen configuration")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def prevent_secret_leakage_and_hash(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Secret hygiene check across all top-level and nested fields
            for key, val in values.items():
                check_secrets_recursively(val, key)

            # Compute hash if missing or empty
            if not values.get("config_hash"):
                hash_payload = {
                    "provider": values.get("provider"),
                    "model_name": values.get("model_name"),
                    "adapter_version": values.get("adapter_version", "1.0.0"),
                    "prompt": values.get("prompt"),
                    "negative_constraints": sorted(values.get("negative_constraints", [])),
                    "parameters": values.get("parameters", {}),
                    "input_artifact_hashes": values.get("input_artifact_hashes", {}),
                    "canon_snapshot_hash": values.get("canon_snapshot_hash"),
                    "seed": values.get("seed"),
                }
                values["config_hash"] = compute_deterministic_hash(hash_payload)
        return values


class ExperimentArm(BaseModel):
    """
    Controlled arm or treatment variant within an experiment.
    """
    arm_id: str = Field(..., description="Stable arm identifier (e.g. 'arm_a_text_only', 'arm_b_anchored')")
    name: str = Field(..., description="Human-readable arm title")
    description: str = Field(..., description="Operational definition of this arm")
    is_control: bool = Field(default=False, description="Whether this arm serves as the baseline control")
    factors_changed: List[str] = Field(default_factory=list, description="Independent variable(s) being altered")
    variables_held_constant: List[str] = Field(default_factory=list, description="Confounders held strictly identical")
    planned_samples: int = Field(..., ge=1, description="Number of planned samples in this arm")
    frozen_config: FrozenConfig = Field(..., description="Immutable frozen configuration for this arm")
    inclusion_rules: List[str] = Field(default_factory=list, description="Criteria for sample inclusion")
    exclusion_rules: List[str] = Field(default_factory=list, description="Criteria for sample exclusion")

    model_config = ConfigDict(extra="forbid")


class ExperimentPlan(BaseModel):
    """
    Pre-declared, versioned experiment specification.
    Separates hypotheses and experimental intentions from empirical run results.
    """
    experiment_id: str = Field(..., description="Stable experiment ID (e.g. 'exp_m0_feasibility')")
    schema_version: str = Field(default="1.0.0", description="Protocol schema version")
    title: str = Field(..., description="Title of the experiment")
    research_question: str = Field(..., description="Core empirical question being addressed")
    predeclared_hypothesis: str = Field(..., description="Exact formulation of hypothesis before execution")
    experiment_type: ExperimentType = Field(default=ExperimentType.CONFIRMATORY)
    taxonomy_group_ids: List[str] = Field(default_factory=list, description="Applicable taxonomy groups")
    claim_ids: List[str] = Field(default_factory=list, description="Claims being evaluated")
    rule_ids: List[str] = Field(default_factory=list, description="Generation rules being tested")
    primary_metric: str = Field(..., description="Primary success metric (e.g. 'first_pass_yield')")
    secondary_metrics: List[str] = Field(default_factory=list, description="Secondary metrics (latency, token usage, cost)")
    threats_to_validity: List[str] = Field(default_factory=list, description="Confounders and limitations")
    limits_on_generalization: List[str] = Field(default_factory=list, description="Scope boundaries of conclusions")
    planned_analysis: str = Field(..., description="Planned statistical test or evaluation rubric")
    decision_criteria: Dict[str, Any] = Field(default_factory=dict, description="Criteria for confirming hypothesis")
    arms: List[ExperimentArm] = Field(..., description="Experimental comparison arms")
    is_executed: bool = Field(default=False, description="Must remain False for an unexecuted plan")
    created_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_plan_invariants(self) -> "ExperimentPlan":
        if not self.arms:
            raise ValueError(f"ExperimentPlan '{self.experiment_id}' must define at least one arm.")
        arm_ids = [arm.arm_id for arm in self.arms]
        if len(arm_ids) != len(set(arm_ids)):
            raise ValueError(f"ExperimentPlan '{self.experiment_id}' contains duplicate arm IDs: {arm_ids}.")
        return self


class SampleExecutionRecord(BaseModel):
    """
    Execution trace for an individual sample attempt in an experiment.
    Ensures complete failure accounting: every dispatched sample is retained.
    """
    sample_id: str = Field(..., description="Unique sample identifier (e.g. 'samp_scene01_arm_a')")
    experiment_id: str = Field(..., description="Parent experiment ID")
    arm_id: str = Field(..., description="Associated arm ID")
    scene_id: Optional[str] = Field(default=None, description="Scene identifier if benchmark scene")
    repetition_index: int = Field(default=0, ge=0)
    status: SampleOutcomeStatus = Field(..., description="Outcome classification (SUCCESS, FAILED, FILTERED, UNRESOLVED, etc.)")
    run_id: Optional[str] = Field(default=None, description="Execution Manager Run ID")
    attempt_id: Optional[str] = Field(default=None, description="Execution Manager Attempt ID")
    request_id: Optional[str] = Field(default=None, description="Provider request ID if dispatched")
    latency_seconds: Optional[float] = Field(default=None, ge=0.0)
    input_artifact_ids: List[str] = Field(default_factory=list)
    output_artifact_id: Optional[str] = Field(default=None)
    output_sha256: Optional[str] = Field(default=None)
    reported_usage: Optional[Dict[str, Any]] = Field(default=None, description="Provider-reported tokens or compute")
    cost_record: Optional[CostRecord] = Field(default=None, description="Structured cost record")
    failure_reason: Optional[str] = Field(default=None)
    filter_reason: Optional[str] = Field(default=None)
    executed_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    @model_validator(mode="after")
    def validate_sample_integrity(self) -> "SampleExecutionRecord":
        if self.status == SampleOutcomeStatus.SUCCESS:
            if not self.output_sha256 and not self.output_artifact_id:
                raise ValueError(f"Sample '{self.sample_id}' marked SUCCESS must record output_sha256 or output_artifact_id.")
        elif self.status == SampleOutcomeStatus.FAILED:
            if not self.failure_reason:
                raise ValueError(f"Sample '{self.sample_id}' marked FAILED must specify a failure_reason.")
        elif self.status == SampleOutcomeStatus.FILTERED:
            if not self.filter_reason:
                raise ValueError(f"Sample '{self.sample_id}' marked FILTERED must specify a filter_reason.")
        return self


class EvaluationDimensionResult(BaseModel):
    """Assessment of a single visual dimension."""
    dimension: EvaluationDimension
    verdict: EvaluationVerdict
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class EvaluationRecord(BaseModel):
    """
    Common evaluation record capturing automated checks, LLM judges, or human judgments.
    """
    evaluation_id: str = Field(..., description="Unique evaluation record ID")
    experiment_id: str = Field(..., description="Parent experiment ID")
    arm_id: str = Field(..., description="Parent arm ID")
    sample_id: str = Field(..., description="Evaluated sample ID")
    evaluator_type: EvaluatorType = Field(...)
    evaluator_id: str = Field(..., description="Model name or rater identifier")
    overall_verdict: EvaluationVerdict = Field(...)
    is_evaluable: bool = Field(default=True, description="Whether the sample was evaluable or degraded beyond inspection")
    dimension_results: Dict[str, EvaluationDimensionResult] = Field(default_factory=dict)
    evidence_notes: Optional[str] = None
    evaluator_metadata: Dict[str, Any] = Field(default_factory=dict, description="Scoring prompt hash, instructions, model parameters")
    evaluated_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")


class UncertaintySummary(BaseModel):
    """Formal statistical uncertainty record for a metric."""
    metric_name: str
    sample_size: int
    success_count: int
    failure_count: int
    filtered_count: int
    unresolved_count: int
    point_estimate: float = Field(..., ge=0.0, le=1.0)
    confidence_interval_low: float = Field(..., ge=0.0, le=1.0)
    confidence_interval_high: float = Field(..., ge=0.0, le=1.0)
    confidence_level: float = Field(default=0.95)
    method: str = Field(default="wilson_score_interval")
    method_rationale: str = Field(default="Wilson score interval maintains coverage for small samples and near-boundary proportions.")
    limitations: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ExperimentExecutionSummary(BaseModel):
    """
    Audited empirical summary of an executed experiment.
    Guarantees strict sample denominator reconciliation.
    """
    experiment_id: str
    title: str
    experiment_plan: ExperimentPlan
    total_planned_samples: int
    total_started_samples: int
    total_completed_samples: int
    total_failed_samples: int
    total_filtered_samples: int
    total_unresolved_samples: int
    total_unfinished_samples: int = Field(default=0)
    first_pass_yield: Dict[str, float] = Field(default_factory=dict, description="Arm ID to pass rate mapping")
    average_latency_seconds: Dict[str, float] = Field(default_factory=dict)
    reported_usage_summary: Dict[str, Any] = Field(default_factory=dict)
    sample_records: List[SampleExecutionRecord] = Field(default_factory=list)
    evaluation_records: List[EvaluationRecord] = Field(default_factory=list)
    uncertainty_summaries: List[UncertaintySummary] = Field(default_factory=list)
    denominator_audit: Dict[str, Any] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_summary_denominators(self) -> "ExperimentExecutionSummary":
        """Enforces that all samples reconcile with denominator rules."""
        audit = reconcile_sample_denominator(
            planned=self.total_planned_samples,
            completed=self.total_completed_samples,
            failed=self.total_failed_samples,
            filtered=self.total_filtered_samples,
            unresolved=self.total_unresolved_samples,
            unfinished=self.total_unfinished_samples,
        )
        # Verify counts match length of sample_records
        total_accounted = (
            self.total_completed_samples
            + self.total_failed_samples
            + self.total_filtered_samples
            + self.total_unresolved_samples
            + self.total_unfinished_samples
        )
        if total_accounted != self.total_planned_samples:
            raise ValueError(f"Summary total accounted ({total_accounted}) does not match planned ({self.total_planned_samples}).")
        return self
