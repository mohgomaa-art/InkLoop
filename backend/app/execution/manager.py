"""
InkLoop Execution Manager.
Coordinates run lifecycle, operation dependency scheduling, attempt tracking,
atomic budget reservation & settlement, bounded retries, append-only event logging,
and crash recovery.
"""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import threading
from typing import Optional, List, Dict, Any, Tuple, Union

from app.contracts.identity import IdPrefix, generate_id
from app.contracts.engine import EngineStatus, QualityVerdict
from app.execution.states import (
    RunStatus,
    AttemptStatus,
    OperationStatus,
    CostClassification,
    BudgetScope,
    ExecutionEventType,
    ExecutionErrorCategory,
    ALLOWED_RUN_TRANSITIONS,
    ALLOWED_ATTEMPT_TRANSITIONS,
    ALLOWED_OPERATION_TRANSITIONS,
    PERMANENT_ERROR_CATEGORIES,
)
from app.execution.models import (
    RunRecord,
    OperationRecord,
    AttemptRecord,
    ExecutionEvent,
    BudgetReservation,
    RunSummary,
    to_decimal,
    utc_now_iso,
)
from app.execution.errors import (
    ExecutionError,
    InvalidStateTransitionError,
    BudgetExceededError,
    ConcurrencyLimitError,
    DependencyFailedError,
    MissingDependencyError,
    RetryExhaustedError,
    PermanentErrorNotRetryableError,
    InterruptedOperationError,
    ReconciliationRequiredError,
    RunTerminalError,
    ArtifactMissingError,
    RunNotFoundError,
    OperationNotFoundError,
    AttemptNotFoundError,
)
from app.execution.budget_manager import BudgetManager
from app.execution.execution_db import ExecutionDB


class ExecutionManager:
    """
    Central execution management engine for InkLoop.
    Implements Task T5.5:
    - Run and attempt lifecycle state machines
    - Bounded retries and cancellation
    - Atomic budget reservations and settlements (multi-scope Decimal arithmetic)
    - Append-only event history
    - Crash recovery and safe resumption
    - Sanitized diagnostics and secret hygiene
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        budget_manager: Optional[BudgetManager] = None,
        max_concurrent_operations: int = 2,
    ):
        actual_db_path = db_path if db_path is not None else Path("runs/execution.db")
        self.db = ExecutionDB(actual_db_path)
        self.budget_manager = budget_manager or BudgetManager()
        self.max_concurrent_operations = max_concurrent_operations
        self._lock = threading.RLock()

    # --- Run Lifecycle ---

    def create_run(
        self,
        project_id: str,
        canon_version: Optional[str] = None,
        canon_hash: Optional[str] = None,
        engine_id: Optional[str] = None,
        engine_version: Optional[str] = None,
        config_hash: Optional[str] = None,
        input_asset_ids: Optional[List[str]] = None,
        input_asset_hashes: Optional[Dict[str, str]] = None,
        required_output_asset_ids: Optional[List[str]] = None,
        budget_limit_usd: Union[int, float, str, Decimal] = "25.0000",
        dry_run: bool = False,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RunRecord:
        """Creates and stores a new run record in CREATED state."""
        with self._lock:
            actual_run_id = run_id or generate_id(IdPrefix.RUN, slug=project_id)
            dec_budget = to_decimal(budget_limit_usd)

            # Register run cap with budget manager
            self.budget_manager.set_run_cap(
                run_id=actual_run_id,
                cap_usd=dec_budget,
                project_id=project_id
            )

            run = RunRecord(
                run_id=actual_run_id,
                project_id=project_id,
                canon_version=canon_version,
                canon_hash=canon_hash,
                engine_id=engine_id,
                engine_version=engine_version,
                config_hash=config_hash,
                status=RunStatus.CREATED,
                input_asset_ids=input_asset_ids or [],
                input_asset_hashes=input_asset_hashes or {},
                required_output_asset_ids=required_output_asset_ids or [],
                budget_limit_usd=dec_budget,
                dry_run=dry_run,
                created_at=utc_now_iso(),
                metadata=metadata or {},
            )
            self.db.save_run(run)

            self._log_event(
                run_id=actual_run_id,
                event_type=ExecutionEventType.RUN_CREATED,
                data={
                    "project_id": project_id,
                    "budget_limit_usd": str(dec_budget),
                    "dry_run": dry_run,
                    "canon_hash": canon_hash,
                }
            )
            return run

    def start_run(self, run_id: str) -> RunRecord:
        """Transitions a run from CREATED or QUEUED to RUNNING."""
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
                raise RunTerminalError(run_id, run.status.value)
            if run.status not in (RunStatus.CREATED, RunStatus.QUEUED):
                raise InvalidStateTransitionError("run", run.status.value, RunStatus.RUNNING.value, run_id)

            started_at = utc_now_iso()
            self.db.update_run_status(run_id, RunStatus.RUNNING, started_at=started_at)
            run.status = RunStatus.RUNNING
            run.started_at = started_at

            self._log_event(
                run_id=run_id,
                event_type=ExecutionEventType.RUN_STARTED,
                data={"started_at": started_at}
            )
            return run

    def complete_run(self, run_id: str) -> RunRecord:
        """
        Completes a run, verifying all operations.
        Cannot complete with SUCCEEDED if any operation failed, is pending, or is blocked.
        """
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
                raise RunTerminalError(run_id, run.status.value)

            operations = self.db.list_operations_for_run(run_id)
            completed_at = utc_now_iso()

            # Check if any operation is still active or pending
            active_ops = [op for op in operations if op.status in (OperationStatus.RUNNING, OperationStatus.QUEUED, OperationStatus.PENDING)]
            if active_ops:
                raise InvalidStateTransitionError(
                    "run",
                    run.status.value,
                    RunStatus.SUCCEEDED.value,
                    f"{run_id} (has {len(active_ops)} active/pending operations)"
                )

            # Check if any operation failed, was blocked, or was interrupted
            failed_ops = [op for op in operations if op.status in (
                OperationStatus.FAILED,
                OperationStatus.BLOCKED,
                OperationStatus.INTERRUPTED,
                OperationStatus.RECONCILIATION_REQUIRED,
                OperationStatus.CANCELLED
            )]

            if failed_ops:
                final_status = RunStatus.FAILED
                event_type = ExecutionEventType.RUN_FAILED
            else:
                final_status = RunStatus.SUCCEEDED
                event_type = ExecutionEventType.RUN_COMPLETED

            self.db.update_run_status(run_id, final_status, completed_at=completed_at)
            run.status = final_status
            run.completed_at = completed_at

            self._log_event(
                run_id=run_id,
                event_type=event_type,
                data={
                    "completed_at": completed_at,
                    "total_operations": len(operations),
                    "failed_operations": len(failed_ops),
                }
            )
            return run

    def mark_run_needs_review(self, run_id: str, reason: str) -> RunRecord:
        """Keep a resumable creative run open when a provider/tool needs attention."""
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status not in (RunStatus.RUNNING, RunStatus.INTERRUPTED, RunStatus.NEEDS_REVIEW):
                raise InvalidStateTransitionError("run", run.status.value, RunStatus.NEEDS_REVIEW.value, run_id)
            self.db.update_run_status(run_id, RunStatus.NEEDS_REVIEW)
            run.status = RunStatus.NEEDS_REVIEW
            self._log_event(
                run_id=run_id,
                event_type=ExecutionEventType.RUN_NEEDS_REVIEW,
                data={"reason": reason[:500]},
            )
            return run

    def resume_needs_review_run(self, run_id: str) -> RunRecord:
        """Resume a reviewable run after its persisted workflow checkpoint is inspected."""
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status not in (RunStatus.NEEDS_REVIEW, RunStatus.INTERRUPTED):
                raise InvalidStateTransitionError("run", run.status.value, RunStatus.RUNNING.value, run_id)
            self.db.update_run_status(run_id, RunStatus.RUNNING)
            run.status = RunStatus.RUNNING
            self._log_event(
                run_id=run_id,
                event_type=ExecutionEventType.RECOVERY_RECONCILED,
                data={"resumed_from": "needs_review"},
            )
            return run

    def cancel_run(self, run_id: str, reason: str = "user_cancelled") -> RunRecord:
        """Cancels an active or created run, releasing all unused reservations."""
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
                raise RunTerminalError(run_id, run.status.value)

            completed_at = utc_now_iso()
            self.db.update_run_status(run_id, RunStatus.CANCELLED, completed_at=completed_at)
            run.status = RunStatus.CANCELLED
            run.completed_at = completed_at

            # Cancel all non-terminal operations
            for op in self.db.list_operations_for_run(run_id):
                if op.status not in (OperationStatus.SUCCEEDED, OperationStatus.FAILED, OperationStatus.CANCELLED):
                    self.db.update_operation_status(op.operation_id, OperationStatus.CANCELLED, completed_at=completed_at)
                    self._log_event(
                        run_id=run_id,
                        operation_id=op.operation_id,
                        event_type=ExecutionEventType.OPERATION_CANCELLED,
                        data={"reason": reason}
                    )

            # Release unused reservations for this run
            for res in self.db.list_reservations_for_run(run_id):
                if res.status == "reserved":
                    self.budget_manager.release(res.reservation_id, reason=reason)
                    res.status = "released"
                    self.db.save_reservation(res)
                    self._log_event(
                        run_id=run_id,
                        event_type=ExecutionEventType.BUDGET_RELEASED,
                        data={"reservation_id": res.reservation_id, "amount_usd": str(res.reserved_amount_usd)}
                    )

            self._log_event(
                run_id=run_id,
                event_type=ExecutionEventType.RUN_CANCELLED,
                data={"reason": reason, "completed_at": completed_at}
            )
            return run

    # --- Operation Scheduling & Execution ---

    def register_operation(
        self,
        run_id: str,
        operation_id: str,
        operation_type: str,
        engine_id: str,
        declared_input_asset_ids: Optional[List[str]] = None,
        dependency_operation_ids: Optional[List[str]] = None,
        required_output_types: Optional[List[str]] = None,
        max_retries: int = 2,
        timeout_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationRecord:
        """Registers a declarative operation record within a run."""
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
                raise RunTerminalError(run_id, run.status.value)

            op = OperationRecord(
                operation_id=operation_id,
                run_id=run_id,
                operation_type=operation_type,
                engine_id=engine_id,
                declared_input_asset_ids=declared_input_asset_ids or [],
                dependency_operation_ids=dependency_operation_ids or [],
                required_output_types=required_output_types or [],
                max_retries=max_retries,
                timeout_seconds=timeout_seconds,
                status=OperationStatus.PENDING,
                created_at=utc_now_iso(),
                metadata=metadata or {},
            )
            self.db.save_operation(op)

            self._log_event(
                run_id=run_id,
                operation_id=operation_id,
                event_type=ExecutionEventType.OPERATION_REGISTERED,
                data={
                    "operation_type": operation_type,
                    "engine_id": engine_id,
                    "dependencies": op.dependency_operation_ids,
                }
            )
            return op

    def can_dispatch_operation(self, operation_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validates whether an operation is eligible for dispatch:
        1. Status must be PENDING.
        2. All prerequisite dependency operations must be SUCCEEDED.
        3. Concurrency ceiling must not be exceeded.
        """
        with self._lock:
            op = self._get_operation_or_raise(operation_id)
            if op.status != OperationStatus.PENDING:
                return False, f"Operation is in status '{op.status.value}', expected 'pending'"

            # Verify dependencies
            for dep_id in op.dependency_operation_ids:
                dep = self.db.get_operation(dep_id)
                if not dep:
                    raise MissingDependencyError(operation_id, dep_id)

                if dep.status in (OperationStatus.FAILED, OperationStatus.CANCELLED, OperationStatus.BLOCKED):
                    # Prerequisite failed: mark this operation BLOCKED
                    self.db.update_operation_status(operation_id, OperationStatus.BLOCKED)
                    self._log_event(
                        run_id=op.run_id,
                        operation_id=operation_id,
                        event_type=ExecutionEventType.OPERATION_BLOCKED,
                        data={"failed_dependency": dep_id, "dependency_status": dep.status.value}
                    )
                    raise DependencyFailedError(operation_id, dep_id, dep.status.value)

                if dep.status != OperationStatus.SUCCEEDED:
                    return False, f"Prerequisite '{dep_id}' is '{dep.status.value}', not 'succeeded'"

            # Verify active concurrency
            active_count = len(self.db.find_interrupted_operations())  # Returns RUNNING operations
            if active_count >= self.max_concurrent_operations:
                return False, f"Concurrency limit reached ({active_count}/{self.max_concurrent_operations})"

            return True, None

    def start_attempt(
        self,
        run_id: str,
        operation_id: str,
        engine_id: Optional[str] = None,
        engine_version: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        estimated_cost_usd: Union[int, float, str, Decimal] = "0.0000",
        cost_classification: CostClassification = CostClassification.ESTIMATED,
        input_asset_ids: Optional[List[str]] = None,
        input_asset_hashes: Optional[Dict[str, str]] = None,
        max_unknown_ops: Optional[int] = None,
    ) -> Tuple[AttemptRecord, BudgetReservation]:
        """
        Starts an operation attempt with atomic budget reservation:
        1. Checks run is RUNNING.
        2. Verifies dependencies and concurrency.
        3. Enforces retry ceiling.
        4. Atomically reserves budget BEFORE dispatch.
        5. Persists attempt and marks operation RUNNING.
        """
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status != RunStatus.RUNNING:
                if run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
                    raise RunTerminalError(run_id, run.status.value)
                raise InvalidStateTransitionError("run", run.status.value, RunStatus.RUNNING.value, run_id)

            op = self._get_operation_or_raise(operation_id)
            can_run, reason = self.can_dispatch_operation(operation_id)
            if not can_run:
                raise ExecutionError(f"Cannot dispatch operation '{operation_id}': {reason}")

            # Enforce retry limit
            existing_attempts = self.db.list_attempts_for_operation(operation_id)
            attempt_number = len(existing_attempts) + 1
            if attempt_number > (op.max_retries + 1):
                raise RetryExhaustedError(operation_id, len(existing_attempts), op.max_retries)

            attempt_id = generate_id(IdPrefix.ATTEMPT, slug=f"{operation_id}_{attempt_number}")

            # Pre-dispatch atomic budget reservation
            reservation = self.budget_manager.reserve(
                run_id=run_id,
                operation_id=operation_id,
                attempt_id=attempt_id,
                amount_usd=estimated_cost_usd,
                classification=cost_classification,
                project_id=run.project_id,
                scope=BudgetScope.RUN,
                max_unknown_ops=max_unknown_ops,
            )
            self.db.save_reservation(reservation)

            self._log_event(
                run_id=run_id,
                operation_id=operation_id,
                attempt_id=attempt_id,
                event_type=ExecutionEventType.BUDGET_RESERVED,
                data={
                    "reservation_id": reservation.reservation_id,
                    "amount_usd": str(reservation.reserved_amount_usd),
                    "classification": cost_classification.value,
                }
            )

            started_at = utc_now_iso()
            attempt = AttemptRecord(
                attempt_id=attempt_id,
                run_id=run_id,
                operation_id=operation_id,
                attempt_number=attempt_number,
                status=AttemptStatus.STARTED,
                engine_id=engine_id or op.engine_id,
                engine_version=engine_version,
                model=model,
                provider=provider,
                started_at=started_at,
                input_asset_ids=input_asset_ids or op.declared_input_asset_ids,
                input_asset_hashes=input_asset_hashes or {},
                cost_amount_usd=to_decimal(estimated_cost_usd),
                cost_classification=cost_classification,
            )
            self.db.save_attempt(attempt)

            # Update operation to RUNNING
            self.db.update_operation_status(
                operation_id=operation_id,
                status=OperationStatus.RUNNING,
                current_attempt_id=attempt_id
            )

            self._log_event(
                run_id=run_id,
                operation_id=operation_id,
                attempt_id=attempt_id,
                event_type=ExecutionEventType.ATTEMPT_STARTED,
                data={"attempt_number": attempt_number, "model": model}
            )
            return attempt, reservation

    def complete_attempt(
        self,
        attempt_id: str,
        status: AttemptStatus,
        actual_cost_usd: Optional[Union[int, float, str, Decimal]] = None,
        cost_classification: CostClassification = CostClassification.PROVIDER_REPORTED,
        output_asset_ids: Optional[List[str]] = None,
        output_asset_hashes: Optional[Dict[str, str]] = None,
        usage: Optional[Dict[str, Any]] = None,
        error_category: Optional[ExecutionErrorCategory] = None,
        error_message: Optional[str] = None,
        is_retryable: Optional[bool] = None,
        verification_verdict: Optional[str] = None,
        eligible_for_acceptance: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ) -> AttemptRecord:
        """
        Completes an attempt, settling the budget reservation and updating operation status.
        """
        with self._lock:
            attempt = self.db.get_attempt(attempt_id)
            if not attempt:
                raise AttemptNotFoundError(attempt_id)

            if attempt.status != AttemptStatus.STARTED:
                raise InvalidStateTransitionError("attempt", attempt.status.value, status.value, attempt_id)

            completed_at = utc_now_iso()
            duration = None
            try:
                start_dt = datetime.fromisoformat(attempt.started_at)
                end_dt = datetime.fromisoformat(completed_at)
                duration = round((end_dt - start_dt).total_seconds(), 4)
            except Exception:
                pass

            # Settle or release budget reservation
            reservations = [r for r in self.db.list_reservations_for_run(attempt.run_id) if r.attempt_id == attempt_id]
            if reservations:
                res = reservations[0]
                if status == AttemptStatus.CANCELLED and (actual_cost_usd is None or actual_cost_usd == 0):
                    self.budget_manager.release(res.reservation_id, reason="attempt_cancelled")
                    res.status = "released"
                    self.db.save_reservation(res)
                    self._log_event(
                        run_id=attempt.run_id,
                        operation_id=attempt.operation_id,
                        attempt_id=attempt_id,
                        event_type=ExecutionEventType.BUDGET_RELEASED,
                        data={"reservation_id": res.reservation_id}
                    )
                else:
                    settled_res = self.budget_manager.settle(
                        reservation_id=res.reservation_id,
                        actual_amount_usd=actual_cost_usd,
                        classification=cost_classification,
                    )
                    self.db.save_reservation(settled_res)
                    self._log_event(
                        run_id=attempt.run_id,
                        operation_id=attempt.operation_id,
                        attempt_id=attempt_id,
                        event_type=ExecutionEventType.BUDGET_SETTLED,
                        data={
                            "reservation_id": settled_res.reservation_id,
                            "settled_amount_usd": str(settled_res.settled_amount_usd),
                            "classification": cost_classification.value,
                        }
                    )

            # Determine retryability
            err_cat_str = error_category.value if error_category else None
            auto_retryable = False
            if status == AttemptStatus.FAILED:
                if error_category in PERMANENT_ERROR_CATEGORIES:
                    auto_retryable = False
                elif is_retryable is not None:
                    auto_retryable = is_retryable
                else:
                    auto_retryable = True

            # A budget reservation is an estimate, not evidence of provider spend.
            # Keep the attempt's actual cost unknown when the provider supplied no cost.
            final_cost = to_decimal(actual_cost_usd) if actual_cost_usd is not None else None
            attempt.status = status
            attempt.completed_at = completed_at
            attempt.duration_seconds = duration
            attempt.output_asset_ids = output_asset_ids or []
            attempt.output_asset_hashes = output_asset_hashes or {}
            attempt.usage = usage or {}
            attempt.cost_amount_usd = final_cost
            attempt.cost_classification = cost_classification
            attempt.error_category = err_cat_str
            attempt.sanitized_error = error_message
            attempt.is_retryable = auto_retryable
            attempt.verification_verdict = verification_verdict
            attempt.eligible_for_acceptance = eligible_for_acceptance
            if details:
                attempt.details.update(details)

            self.db.save_attempt(attempt)

            # Update parent operation status
            op = self._get_operation_or_raise(attempt.operation_id)
            if status == AttemptStatus.SUCCEEDED and eligible_for_acceptance:
                self.db.update_operation_status(
                    operation_id=op.operation_id,
                    status=OperationStatus.SUCCEEDED,
                    accepted_attempt_id=attempt_id,
                    output_asset_ids=output_asset_ids,
                    completed_at=completed_at,
                )
                self._log_event(
                    run_id=attempt.run_id,
                    operation_id=op.operation_id,
                    attempt_id=attempt_id,
                    event_type=ExecutionEventType.OPERATION_COMPLETED,
                    data={"accepted_attempt_id": attempt_id, "output_asset_ids": output_asset_ids}
                )
            elif status == AttemptStatus.FAILED:
                if auto_retryable and (attempt.attempt_number <= op.max_retries):
                    # Operation returns to PENDING for bounded retry
                    self.db.update_operation_status(
                        operation_id=op.operation_id,
                        status=OperationStatus.PENDING,
                        current_attempt_id=None,
                    )
                    self._log_event(
                        run_id=attempt.run_id,
                        operation_id=op.operation_id,
                        attempt_id=attempt_id,
                        event_type=ExecutionEventType.ATTEMPT_FAILED,
                        data={
                            "error_category": err_cat_str,
                            "attempt_number": attempt.attempt_number,
                            "retry_permitted": True,
                        }
                    )
                else:
                    # Retries exhausted or permanent failure
                    self.db.update_operation_status(
                        operation_id=op.operation_id,
                        status=OperationStatus.FAILED,
                        completed_at=completed_at,
                    )
                    self._log_event(
                        run_id=attempt.run_id,
                        operation_id=op.operation_id,
                        attempt_id=attempt_id,
                        event_type=ExecutionEventType.OPERATION_FAILED,
                        data={
                            "error_category": err_cat_str,
                            "error_message": error_message,
                            "attempts_made": attempt.attempt_number,
                            "max_retries": op.max_retries,
                        }
                    )
            else:
                self._log_event(
                    run_id=attempt.run_id,
                    operation_id=op.operation_id,
                    attempt_id=attempt_id,
                    event_type=ExecutionEventType.ATTEMPT_COMPLETED,
                    data={"status": status.value}
                )

            return attempt

    def mark_attempt_uncertain(
        self,
        attempt_id: str,
        reason: str = "remote_timeout_or_lost_response"
    ) -> AttemptRecord:
        """
        Marks an attempt as interrupted with uncertain external outcome.
        Reservations remain held (funds NOT released/refunded).
        Operation is marked RECONCILIATION_REQUIRED.
        """
        with self._lock:
            attempt = self.db.get_attempt(attempt_id)
            if not attempt:
                raise AttemptNotFoundError(attempt_id)

            attempt.status = AttemptStatus.INTERRUPTED
            attempt.completed_at = utc_now_iso()
            attempt.error_category = ExecutionErrorCategory.RECONCILIATION_REQUIRED.value
            attempt.sanitized_error = f"Uncertain remote outcome: {reason}"
            self.db.save_attempt(attempt)

            # Mark reservation as uncertain (held!)
            reservations = [r for r in self.db.list_reservations_for_run(attempt.run_id) if r.attempt_id == attempt_id]
            if reservations:
                uncertain_res = self.budget_manager.mark_uncertain(reservations[0].reservation_id, reason=reason)
                self.db.save_reservation(uncertain_res)

            # Mark operation RECONCILIATION_REQUIRED
            self.db.update_operation_status(
                operation_id=attempt.operation_id,
                status=OperationStatus.RECONCILIATION_REQUIRED
            )

            self._log_event(
                run_id=attempt.run_id,
                operation_id=attempt.operation_id,
                attempt_id=attempt_id,
                event_type=ExecutionEventType.BUDGET_UNCERTAIN,
                data={"reason": reason}
            )
            return attempt

    # --- Crash Recovery & Resume ---

    def recover_on_startup(self) -> Dict[str, Any]:
        """
        Scans persistence store for interrupted runs and operations left active during a crash.
        Transitions running entities to INTERRUPTED state and flags uncertain reservations.
        """
        with self._lock:
            interrupted_runs = self.db.find_interrupted_runs()
            interrupted_ops = self.db.find_interrupted_operations()
            uncertain_reservations = self.db.find_uncertain_reservations()

            # Mark active operations as INTERRUPTED
            for op in interrupted_ops:
                self.db.update_operation_status(op.operation_id, OperationStatus.INTERRUPTED)
                if op.current_attempt_id:
                    att = self.db.get_attempt(op.current_attempt_id)
                    if att and att.status == AttemptStatus.STARTED:
                        att.status = AttemptStatus.INTERRUPTED
                        att.sanitized_error = "Process terminated unexpectedly during execution"
                        self.db.save_attempt(att)

                self._log_event(
                    run_id=op.run_id,
                    operation_id=op.operation_id,
                    event_type=ExecutionEventType.OPERATION_INTERRUPTED,
                    data={"reason": "crash_recovery_discovery"}
                )

            # Mark active runs as INTERRUPTED
            for r in interrupted_runs:
                self.db.update_run_status(r.run_id, RunStatus.INTERRUPTED)
                self._log_event(
                    run_id=r.run_id,
                    event_type=ExecutionEventType.RUN_INTERRUPTED,
                    data={"reason": "crash_recovery_discovery"}
                )

            return {
                "interrupted_runs_count": len(interrupted_runs),
                "interrupted_operations_count": len(interrupted_ops),
                "uncertain_reservations_count": len(uncertain_reservations),
                "interrupted_run_ids": [r.run_id for r in interrupted_runs],
                "interrupted_operation_ids": [op.operation_id for op in interrupted_ops],
            }

    def resume_run(
        self,
        run_id: str,
        asset_checker: Optional[Any] = None
    ) -> RunRecord:
        """
        Safely resumes an interrupted run:
        1. Validates that input assets still exist and match hashes.
        2. Preserves already completed (SUCCEEDED) operations without re-running them.
        3. Resets INTERRUPTED operations to PENDING.
        4. Transitions run back to RUNNING.
        """
        with self._lock:
            run = self._get_run_or_raise(run_id)
            if run.status != RunStatus.INTERRUPTED:
                raise InvalidStateTransitionError("run", run.status.value, RunStatus.RUNNING.value, run_id)

            # Validate input asset hashes if checker supplied
            if asset_checker and run.input_asset_hashes:
                for asset_id, expected_hash in run.input_asset_hashes.items():
                    verified = asset_checker(asset_id, expected_hash)
                    if not verified:
                        raise ArtifactMissingError(asset_id, expected_hash, "Integrity check failed during resume")

            # Reset interrupted operations back to PENDING
            ops = self.db.list_operations_for_run(run_id)
            resumed_op_count = 0
            for op in ops:
                if op.status == OperationStatus.INTERRUPTED:
                    self.db.update_operation_status(op.operation_id, OperationStatus.PENDING, current_attempt_id=None)
                    resumed_op_count += 1

            self.db.update_run_status(run_id, RunStatus.RUNNING)
            run.status = RunStatus.RUNNING

            self._log_event(
                run_id=run_id,
                event_type=ExecutionEventType.RECOVERY_RECONCILED,
                data={"resumed_operations_count": resumed_op_count}
            )
            self._log_event(
                run_id=run_id,
                event_type=ExecutionEventType.RUN_STARTED,
                data={"resumed": True}
            )
            return run

    # --- Run Summary Serializer ---

    def get_run_summary(self, run_id: str) -> RunSummary:
        """
        Produces a deterministic, auditable machine-readable summary of the run.
        Contains zero API keys, headers, or binary blobs.
        """
        with self._lock:
            run = self._get_run_or_raise(run_id)
            operations = self.db.list_operations_for_run(run_id)
            attempts = self.db.list_attempts_for_run(run_id)
            events = self.db.list_events_for_run(run_id)

            total_estimated = Decimal("0.0000")
            total_reserved = Decimal("0.0000")
            total_reported = Decimal("0.0000")
            total_confirmed = Decimal("0.0000")
            missing_cost = 0

            for att in attempts:
                if att.cost_classification == CostClassification.UNKNOWN or att.cost_amount_usd is None:
                    missing_cost += 1
                elif att.cost_amount_usd is not None:
                    if att.cost_classification == CostClassification.ESTIMATED:
                        total_estimated += att.cost_amount_usd
                    elif att.cost_classification == CostClassification.RESERVED:
                        total_reserved += att.cost_amount_usd
                    elif att.cost_classification == CostClassification.PROVIDER_REPORTED:
                        total_reported += att.cost_amount_usd
                    elif att.cost_classification == CostClassification.BILLING_CONFIRMED:
                        total_confirmed += att.cost_amount_usd

            duration = None
            if run.started_at and run.completed_at:
                try:
                    s_dt = datetime.fromisoformat(run.started_at)
                    e_dt = datetime.fromisoformat(run.completed_at)
                    duration = round((e_dt - s_dt).total_seconds(), 4)
                except Exception:
                    pass

            completed_ops = sum(1 for op in operations if op.status == OperationStatus.SUCCEEDED)
            failed_ops = sum(1 for op in operations if op.status == OperationStatus.FAILED)
            blocked_ops = sum(1 for op in operations if op.status == OperationStatus.BLOCKED)
            interrupted_ops = sum(1 for op in operations if op.status == OperationStatus.INTERRUPTED)
            reconcile_ops = sum(1 for op in operations if op.status == OperationStatus.RECONCILIATION_REQUIRED)

            # Collect unique output assets
            output_assets = []
            for op in operations:
                output_assets.extend(op.output_asset_ids)

            return RunSummary(
                run_id=run.run_id,
                project_id=run.project_id,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_seconds=duration,
                dry_run=run.dry_run,
                total_operations=len(operations),
                completed_operations=completed_ops,
                failed_operations=failed_ops,
                blocked_operations=blocked_ops,
                interrupted_operations=interrupted_ops,
                reconciliation_required_operations=reconcile_ops,
                total_attempts=len(attempts),
                total_estimated_usd=total_estimated,
                total_reserved_usd=total_reserved,
                total_reported_usd=total_reported,
                total_confirmed_usd=total_confirmed,
                missing_cost_count=missing_cost,
                output_asset_ids=sorted(list(set(output_assets))),
                event_count=len(events),
            )

    # --- Internal Helpers ---

    def _get_run_or_raise(self, run_id: str) -> RunRecord:
        run = self.db.get_run(run_id)
        if not run:
            raise RunNotFoundError(run_id)
        return run

    def _get_operation_or_raise(self, operation_id: str) -> OperationRecord:
        op = self.db.get_operation(operation_id)
        if not op:
            raise OperationNotFoundError(operation_id)
        return op

    def _log_event(
        self,
        run_id: str,
        event_type: ExecutionEventType,
        data: Dict[str, Any],
        operation_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
    ) -> None:
        """Appends a sanitized, structured event to the audit trail."""
        # Sanitize data against secret leakage
        sanitized_data = {
            k: v for k, v in data.items()
            if not any(sub in k.lower() for sub in ("key", "token", "auth", "secret", "password"))
        }
        event_id = generate_id(IdPrefix.EVENT, slug=event_type.value)
        event = ExecutionEvent(
            event_id=event_id,
            run_id=run_id,
            operation_id=operation_id,
            attempt_id=attempt_id,
            event_type=event_type,
            timestamp=utc_now_iso(),
            data=sanitized_data,
        )
        self.db.append_event(event)

    def close(self) -> None:
        """Closes any underlying resources."""
        self.db.close()
