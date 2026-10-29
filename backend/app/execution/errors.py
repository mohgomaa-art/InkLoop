"""
InkLoop Execution & Budget Subsystem - Structured Exceptions.
"""
from typing import Optional, Any, Dict


class ExecutionError(Exception):
    """Base exception for all execution, run-tracking, and budget operations."""
    def __init__(self, message: str, code: str = "EXECUTION_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.code,
            "message": self.message,
            "details": self.details,
        }


class InvalidStateTransitionError(ExecutionError):
    """Raised when an illegal lifecycle transition is attempted."""
    def __init__(self, entity_type: str, current_state: str, attempted_state: str, entity_id: Optional[str] = None):
        super().__init__(
            f"Invalid {entity_type} state transition from '{current_state}' to '{attempted_state}' (id='{entity_id}').",
            code="INVALID_STATE_TRANSITION",
            details={
                "entity_type": entity_type,
                "current_state": current_state,
                "attempted_state": attempted_state,
                "entity_id": entity_id,
            }
        )


class BudgetExceededError(ExecutionError):
    """Raised when an operation or run reservation exceeds the effective spend ceiling."""
    def __init__(self, requested_usd: str, available_usd: str, scope: str, entity_id: Optional[str] = None):
        super().__init__(
            f"Budget exceeded in scope '{scope}': requested ${requested_usd} USD but only ${available_usd} USD available (id='{entity_id}').",
            code="BUDGET_EXCEEDED",
            details={
                "requested_usd": requested_usd,
                "available_usd": available_usd,
                "scope": scope,
                "entity_id": entity_id,
            }
        )


class BudgetScopeViolationError(ExecutionError):
    """Raised when a child budget scope attempts to define a limit exceeding a parent scope."""
    def __init__(self, child_scope: str, child_limit: str, parent_scope: str, parent_limit: str):
        super().__init__(
            f"Scope violation: {child_scope} limit (${child_limit}) cannot exceed parent {parent_scope} limit (${parent_limit}).",
            code="BUDGET_SCOPE_VIOLATION",
            details={
                "child_scope": child_scope,
                "child_limit": child_limit,
                "parent_scope": parent_scope,
                "parent_limit": parent_limit,
            }
        )


class DuplicateSettlementError(ExecutionError):
    """Raised when a budget reservation is settled or released multiple times."""
    def __init__(self, reservation_id: str, current_status: str):
        super().__init__(
            f"Duplicate settlement prohibited: reservation '{reservation_id}' is already in status '{current_status}'.",
            code="DUPLICATE_SETTLEMENT",
            details={"reservation_id": reservation_id, "current_status": current_status}
        )


class UnreservedSettlementError(ExecutionError):
    """Raised when attempting to settle a non-existent or unreserved budget item."""
    def __init__(self, reservation_id: str):
        super().__init__(
            f"Cannot settle unreserved budget item '{reservation_id}'.",
            code="UNRESERVED_SETTLEMENT",
            details={"reservation_id": reservation_id}
        )


class ConcurrencyLimitError(ExecutionError):
    """Raised when attempting to dispatch operations exceeding active concurrency ceiling."""
    def __init__(self, active_count: int, max_concurrency: int):
        super().__init__(
            f"Concurrency ceiling reached: {active_count} active operations exceeds maximum {max_concurrency}.",
            code="CONCURRENCY_LIMIT_EXCEEDED",
            details={"active_count": active_count, "max_concurrency": max_concurrency}
        )


class DependencyFailedError(ExecutionError):
    """Raised when an operation cannot be dispatched because a required dependency failed or was blocked."""
    def __init__(self, operation_id: str, failed_dependency_id: str, dependency_status: str):
        super().__init__(
            f"Operation '{operation_id}' blocked: prerequisite dependency '{failed_dependency_id}' has status '{dependency_status}'.",
            code="DEPENDENCY_FAILED",
            details={
                "operation_id": operation_id,
                "failed_dependency_id": failed_dependency_id,
                "dependency_status": dependency_status,
            }
        )


class MissingDependencyError(ExecutionError):
    """Raised when a declared prerequisite dependency does not exist in the run."""
    def __init__(self, operation_id: str, missing_dependency_id: str):
        super().__init__(
            f"Operation '{operation_id}' references non-existent dependency '{missing_dependency_id}'.",
            code="MISSING_DEPENDENCY",
            details={"operation_id": operation_id, "missing_dependency_id": missing_dependency_id}
        )


class RetryExhaustedError(ExecutionError):
    """Raised when an operation has exhausted its configured maximum retry ceiling."""
    def __init__(self, operation_id: str, attempts_made: int, max_retries: int):
        super().__init__(
            f"Retry ceiling exhausted for operation '{operation_id}': made {attempts_made} attempts (max retries: {max_retries}).",
            code="RETRY_EXHAUSTED",
            details={"operation_id": operation_id, "attempts_made": attempts_made, "max_retries": max_retries}
        )


class PermanentErrorNotRetryableError(ExecutionError):
    """Raised when attempting to retry a deterministic, non-retryable error."""
    def __init__(self, operation_id: str, error_category: str, reason: str):
        super().__init__(
            f"Operation '{operation_id}' failed with permanent non-retryable error '{error_category}': {reason}.",
            code="PERMANENT_ERROR_NOT_RETRYABLE",
            details={"operation_id": operation_id, "error_category": error_category, "reason": reason}
        )


class InterruptedOperationError(ExecutionError):
    """Raised or recorded when an operation was interrupted by process crash or abrupt termination."""
    def __init__(self, operation_id: str, attempt_id: Optional[str] = None):
        super().__init__(
            f"Operation '{operation_id}' (attempt='{attempt_id}') was interrupted and left in an indeterminate state.",
            code="INTERRUPTED_OPERATION",
            details={"operation_id": operation_id, "attempt_id": attempt_id}
        )


class ReconciliationRequiredError(ExecutionError):
    """Raised when an external call outcome is unknown and requires manual or explicit reconciliation."""
    def __init__(self, operation_id: str, attempt_id: str, reservation_id: Optional[str] = None):
        super().__init__(
            f"Reconciliation required for operation '{operation_id}' (attempt='{attempt_id}'): external provider outcome is uncertain.",
            code="RECONCILIATION_REQUIRED",
            details={"operation_id": operation_id, "attempt_id": attempt_id, "reservation_id": reservation_id}
        )


class RunTerminalError(ExecutionError):
    """Raised when an operation or modification is attempted on a run in terminal state."""
    def __init__(self, run_id: str, status: str):
        super().__init__(
            f"Run '{run_id}' is in terminal status '{status}' and cannot accept new operations or state changes.",
            code="RUN_TERMINAL",
            details={"run_id": run_id, "status": status}
        )


class ArtifactMissingError(ExecutionError):
    """Raised when a required registered input or output artifact is missing or corrupted on disk."""
    def __init__(self, asset_id: str, expected_hash: Optional[str] = None, details: Optional[str] = None):
        super().__init__(
            f"Artifact '{asset_id}' is missing or corrupted. Expected hash: '{expected_hash}'. {details or ''}",
            code="ARTIFACT_MISSING_OR_CORRUPT",
            details={"asset_id": asset_id, "expected_hash": expected_hash}
        )


class RunNotFoundError(ExecutionError):
    def __init__(self, run_id: str):
        super().__init__(f"Run '{run_id}' not found in execution ledger.", code="RUN_NOT_FOUND", details={"run_id": run_id})


class OperationNotFoundError(ExecutionError):
    def __init__(self, operation_id: str):
        super().__init__(f"Operation '{operation_id}' not found.", code="OPERATION_NOT_FOUND", details={"operation_id": operation_id})


class AttemptNotFoundError(ExecutionError):
    def __init__(self, attempt_id: str):
        super().__init__(f"Attempt '{attempt_id}' not found.", code="ATTEMPT_NOT_FOUND", details={"attempt_id": attempt_id})


class ReservationNotFoundError(ExecutionError):
    def __init__(self, reservation_id: str):
        super().__init__(f"Reservation '{reservation_id}' not found.", code="RESERVATION_NOT_FOUND", details={"reservation_id": reservation_id})
