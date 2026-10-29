"""
InkLoop Execution & Budget Data Models.
Uses Python Decimal for exact financial and currency accounting.
Guarantees clean serialization without binary blobs or secret credentials.
"""
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

from app.execution.states import (
    RunStatus,
    AttemptStatus,
    OperationStatus,
    CostClassification,
    BudgetScope,
    ExecutionEventType,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_decimal(val: Union[int, float, str, Decimal]) -> Decimal:
    """Converts a numeric value to a sanitized Decimal with 4 decimal places."""
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.0001"))
    if isinstance(val, float):
        return Decimal(str(round(val, 6))).quantize(Decimal("0.0001"))
    return Decimal(str(val)).quantize(Decimal("0.0001"))


class CostRecord(BaseModel):
    """Structured record of a cost determination with explicit classification."""
    amount_usd: Decimal = Field(..., description="Cost in USD using Decimal arithmetic")
    classification: CostClassification = Field(..., description="Classification (estimated, reserved, provider_reported, billing_confirmed, unknown)")
    reported_at: str = Field(default_factory=utc_now_iso)
    source: str = Field(default="local_accounting", description="Source of cost figure")
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BudgetLimit(BaseModel):
    """Hierarchical budget limit definitions across scopes."""
    global_cap_usd: Decimal = Field(default_factory=lambda: Decimal("25.0000"))
    project_cap_usd: Optional[Decimal] = None
    run_cap_usd: Optional[Decimal] = None
    operation_cap_usd: Optional[Decimal] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def effective_cap(self, scope: BudgetScope) -> Decimal:
        """
        Returns the effective cap for a given scope, enforcing that child scopes
        can never exceed a stricter parent scope.
        """
        caps = [self.global_cap_usd]
        if scope in (BudgetScope.PROJECT, BudgetScope.RUN, BudgetScope.OPERATION) and self.project_cap_usd is not None:
            caps.append(self.project_cap_usd)
        if scope in (BudgetScope.RUN, BudgetScope.OPERATION) and self.run_cap_usd is not None:
            caps.append(self.run_cap_usd)
        if scope == BudgetScope.OPERATION and self.operation_cap_usd is not None:
            caps.append(self.operation_cap_usd)
        return min(caps)


class BudgetReservation(BaseModel):
    """Durable budget reservation record for atomic fund commitment."""
    reservation_id: str
    run_id: str
    operation_id: str
    attempt_id: str
    scope: BudgetScope
    reserved_amount_usd: Decimal
    settled_amount_usd: Optional[Decimal] = None
    status: str = Field(default="reserved", description="'reserved', 'settled', 'released', or 'uncertain'")
    cost_classification: CostClassification
    created_at: str = Field(default_factory=utc_now_iso)
    settled_at: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AttemptRecord(BaseModel):
    """Immutable audit record for a single operation execution attempt."""
    attempt_id: str
    run_id: str
    operation_id: str
    attempt_number: int
    status: AttemptStatus
    engine_id: Optional[str] = None
    engine_version: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    request_id: Optional[str] = None
    input_asset_ids: List[str] = Field(default_factory=list)
    input_asset_hashes: Dict[str, str] = Field(default_factory=dict)
    output_asset_ids: List[str] = Field(default_factory=list)
    output_asset_hashes: Dict[str, str] = Field(default_factory=dict)
    error_category: Optional[str] = None
    sanitized_error: Optional[str] = None
    retry_reason: Optional[str] = None
    is_retryable: bool = False
    usage: Dict[str, Any] = Field(default_factory=dict)
    cost_amount_usd: Optional[Decimal] = None
    cost_classification: CostClassification = CostClassification.UNKNOWN
    eligible_for_acceptance: bool = False
    verification_verdict: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OperationRecord(BaseModel):
    """Declarative operation record within an execution run."""
    operation_id: str
    run_id: str
    operation_type: str
    engine_id: str
    declared_input_asset_ids: List[str] = Field(default_factory=list)
    dependency_operation_ids: List[str] = Field(default_factory=list)
    required_output_types: List[str] = Field(default_factory=list)
    max_retries: int = 2
    timeout_seconds: Optional[float] = None
    status: OperationStatus = OperationStatus.PENDING
    attempts: List[AttemptRecord] = Field(default_factory=list)
    current_attempt_id: Optional[str] = None
    accepted_attempt_id: Optional[str] = None
    output_asset_ids: List[str] = Field(default_factory=list)
    output_asset_hashes: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RunRecord(BaseModel):
    """Authoritative execution run record."""
    run_id: str
    project_id: str
    canon_version: Optional[str] = None
    canon_hash: Optional[str] = None
    engine_id: Optional[str] = None
    engine_version: Optional[str] = None
    config_hash: Optional[str] = None
    status: RunStatus = RunStatus.CREATED
    input_asset_ids: List[str] = Field(default_factory=list)
    input_asset_hashes: Dict[str, str] = Field(default_factory=dict)
    required_output_asset_ids: List[str] = Field(default_factory=list)
    budget_limit_usd: Decimal = Field(default_factory=lambda: Decimal("25.0000"))
    dry_run: bool = False
    created_at: str = Field(default_factory=utc_now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExecutionEvent(BaseModel):
    """Typed append-only audit event."""
    event_id: str
    run_id: str
    operation_id: Optional[str] = None
    attempt_id: Optional[str] = None
    event_type: ExecutionEventType
    timestamp: str = Field(default_factory=utc_now_iso)
    schema_version: str = "1.0.0"
    data: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RunSummary(BaseModel):
    """Deterministic, auditable summary of an entire run execution."""
    run_id: str
    project_id: str
    status: RunStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    dry_run: bool = False
    total_operations: int = 0
    completed_operations: int = 0
    failed_operations: int = 0
    blocked_operations: int = 0
    interrupted_operations: int = 0
    reconciliation_required_operations: int = 0
    total_attempts: int = 0
    total_estimated_usd: Decimal = Field(default_factory=lambda: Decimal("0.0000"))
    total_reserved_usd: Decimal = Field(default_factory=lambda: Decimal("0.0000"))
    total_reported_usd: Decimal = Field(default_factory=lambda: Decimal("0.0000"))
    total_confirmed_usd: Decimal = Field(default_factory=lambda: Decimal("0.0000"))
    missing_cost_count: int = 0
    output_asset_ids: List[str] = Field(default_factory=list)
    event_count: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary with Decimals converted to strings."""
        d = self.model_dump()
        d["status"] = self.status.value
        d["total_estimated_usd"] = str(self.total_estimated_usd)
        d["total_reserved_usd"] = str(self.total_reserved_usd)
        d["total_reported_usd"] = str(self.total_reported_usd)
        d["total_confirmed_usd"] = str(self.total_confirmed_usd)
        return d

    def to_json(self, indent: int = 2) -> str:
        """Deterministic JSON output sorted by key."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
