"""
InkLoop Run Execution & State Machine Definitions.
Enforces deterministic lifecycle states and validated transitions for runs,
operations, attempts, budget reservations, and append-only event streams.
"""
from enum import Enum
from typing import Dict, Set


class RunStatus(str, Enum):
    """Lifecycle status of an entire execution run."""
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    NEEDS_REVIEW = "needs_review"


class AttemptStatus(str, Enum):
    """Lifecycle status of an individual operation attempt."""
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class OperationStatus(str, Enum):
    """Lifecycle status of a logical operation within a run."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    INTERRUPTED = "interrupted"
    NEEDS_REVIEW = "needs_review"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class CostClassification(str, Enum):
    """
    Cost classification semantics.
    Estimates must NEVER be conflated with confirmed provider billing.
    """
    ESTIMATED = "estimated"
    RESERVED = "reserved"
    PROVIDER_REPORTED = "provider_reported"
    BILLING_CONFIRMED = "billing_confirmed"
    UNKNOWN = "unknown"


class BudgetScope(str, Enum):
    """Hierarchical budget scopes."""
    GLOBAL = "global"
    PROJECT = "project"
    RUN = "run"
    OPERATION = "operation"


class ExecutionEventType(str, Enum):
    """Typed events for the append-only audit trail."""
    RUN_CREATED = "run_created"
    RUN_QUEUED = "run_queued"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    RUN_INTERRUPTED = "run_interrupted"
    RUN_NEEDS_REVIEW = "run_needs_review"

    OPERATION_REGISTERED = "operation_registered"
    OPERATION_QUEUED = "operation_queued"
    OPERATION_STARTED = "operation_started"
    OPERATION_COMPLETED = "operation_completed"
    OPERATION_FAILED = "operation_failed"
    OPERATION_BLOCKED = "operation_blocked"
    OPERATION_CANCELLED = "operation_cancelled"
    OPERATION_INTERRUPTED = "operation_interrupted"
    OPERATION_NEEDS_REVIEW = "operation_needs_review"

    ATTEMPT_STARTED = "attempt_started"
    ATTEMPT_COMPLETED = "attempt_completed"
    ATTEMPT_FAILED = "attempt_failed"
    ATTEMPT_CANCELLED = "attempt_cancelled"
    ATTEMPT_INTERRUPTED = "attempt_interrupted"

    BUDGET_RESERVED = "budget_reserved"
    BUDGET_SETTLED = "budget_settled"
    BUDGET_RELEASED = "budget_released"
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_UNCERTAIN = "budget_uncertain"

    RECOVERY_DISCOVERED = "recovery_discovered"
    RECOVERY_RECONCILED = "recovery_reconciled"


class ExecutionErrorCategory(str, Enum):
    """Sanitized failure diagnostic categories."""
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    CONTENT_POLICY_VIOLATION = "CONTENT_POLICY_VIOLATION"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    SERVER_ERROR = "SERVER_ERROR"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    CONCURRENCY_LIMIT_EXCEEDED = "CONCURRENCY_LIMIT_EXCEEDED"
    DEPENDENCY_FAILED = "DEPENDENCY_FAILED"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    INTERRUPTED = "INTERRUPTED"
    CORRUPT_ARTIFACT = "CORRUPT_ARTIFACT"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    UNKNOWN = "UNKNOWN"


# Deterministic transition matrices
ALLOWED_RUN_TRANSITIONS: Dict[RunStatus, Set[RunStatus]] = {
    RunStatus.CREATED: {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.INTERRUPTED, RunStatus.NEEDS_REVIEW},
    RunStatus.INTERRUPTED: {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.NEEDS_REVIEW},
    RunStatus.NEEDS_REVIEW: {RunStatus.RUNNING, RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.SUCCEEDED: set(),  # Terminal
    RunStatus.FAILED: set(),     # Terminal
    RunStatus.CANCELLED: set(),  # Terminal
}

ALLOWED_ATTEMPT_TRANSITIONS: Dict[AttemptStatus, Set[AttemptStatus]] = {
    AttemptStatus.STARTED: {AttemptStatus.SUCCEEDED, AttemptStatus.FAILED, AttemptStatus.CANCELLED, AttemptStatus.INTERRUPTED},
    AttemptStatus.SUCCEEDED: set(),  # Terminal
    AttemptStatus.FAILED: set(),     # Terminal
    AttemptStatus.CANCELLED: set(),  # Terminal
    AttemptStatus.INTERRUPTED: set(),  # Terminal for this attempt
}

ALLOWED_OPERATION_TRANSITIONS: Dict[OperationStatus, Set[OperationStatus]] = {
    OperationStatus.PENDING: {OperationStatus.QUEUED, OperationStatus.RUNNING, OperationStatus.BLOCKED, OperationStatus.CANCELLED},
    OperationStatus.QUEUED: {OperationStatus.RUNNING, OperationStatus.BLOCKED, OperationStatus.CANCELLED},
    OperationStatus.RUNNING: {
        OperationStatus.SUCCEEDED,
        OperationStatus.FAILED,
        OperationStatus.CANCELLED,
        OperationStatus.INTERRUPTED,
        OperationStatus.NEEDS_REVIEW,
        OperationStatus.RECONCILIATION_REQUIRED,
        OperationStatus.PENDING,  # Retrying after non-terminal failure
    },
    OperationStatus.BLOCKED: {OperationStatus.PENDING, OperationStatus.CANCELLED, OperationStatus.FAILED},
    OperationStatus.INTERRUPTED: {OperationStatus.RUNNING, OperationStatus.FAILED, OperationStatus.CANCELLED, OperationStatus.RECONCILIATION_REQUIRED, OperationStatus.PENDING},
    OperationStatus.RECONCILIATION_REQUIRED: {OperationStatus.SUCCEEDED, OperationStatus.FAILED, OperationStatus.RUNNING, OperationStatus.CANCELLED},
    OperationStatus.NEEDS_REVIEW: {OperationStatus.RUNNING, OperationStatus.SUCCEEDED, OperationStatus.FAILED, OperationStatus.CANCELLED},
    OperationStatus.SUCCEEDED: set(),  # Terminal
    OperationStatus.FAILED: set(),     # Terminal
    OperationStatus.CANCELLED: set(),  # Terminal
}

PERMANENT_ERROR_CATEGORIES: Set[ExecutionErrorCategory] = {
    ExecutionErrorCategory.AUTHENTICATION_ERROR,
    ExecutionErrorCategory.BAD_REQUEST,
    ExecutionErrorCategory.BUDGET_EXCEEDED,
    ExecutionErrorCategory.DEPENDENCY_FAILED,
    ExecutionErrorCategory.CORRUPT_ARTIFACT,
}
