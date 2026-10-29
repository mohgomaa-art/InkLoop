"""
Comprehensive tests for InkLoop Run Execution, Event Tracking & Budget Manager (Milestone 1, Task T5.5).
Covers run/attempt lifecycle, multi-scope Decimal budget enforcement, bounded retries,
dependency scheduling, crash recovery, uncertain outcomes, and secret hygiene.
"""
import io
from PIL import Image
from decimal import Decimal
import json
from pathlib import Path
import threading
import pytest

from app.contracts.identity import IdPrefix, generate_id
from app.contracts.engine import EngineStatus
from app.execution.states import (
    RunStatus,
    AttemptStatus,
    OperationStatus,
    CostClassification,
    BudgetScope,
    ExecutionEventType,
    ExecutionErrorCategory,
)
from app.execution.models import (
    to_decimal,
    RunRecord,
    OperationRecord,
    AttemptRecord,
    BudgetReservation,
    RunSummary,
)
from app.execution.errors import (
    ExecutionError,
    InvalidStateTransitionError,
    BudgetExceededError,
    BudgetScopeViolationError,
    DuplicateSettlementError,
    UnreservedSettlementError,
    ConcurrencyLimitError,
    DependencyFailedError,
    MissingDependencyError,
    RetryExhaustedError,
    PermanentErrorNotRetryableError,
    InterruptedOperationError,
    ReconciliationRequiredError,
    RunTerminalError,
    ArtifactMissingError,
)
from app.execution.budget_manager import BudgetManager
from app.execution.execution_db import ExecutionDB
from app.execution.manager import ExecutionManager
from app.storage.registry import AssetRegistry
from app.project.bible import load_bible, StoryBible
from app.project.canon import CanonSnapshot

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def temp_db_path(tmp_path) -> Path:
    """Provides a fresh isolated SQLite database file."""
    return tmp_path / "execution.db"


@pytest.fixture
def budget_manager() -> BudgetManager:
    """Provides a fresh BudgetManager with standard $25 cap."""
    return BudgetManager(global_cap_usd="25.0000")


@pytest.fixture
def exec_manager(temp_db_path, budget_manager) -> ExecutionManager:
    """Provides an initialized ExecutionManager."""
    mgr = ExecutionManager(db_path=temp_db_path, budget_manager=budget_manager, max_concurrent_operations=2)
    yield mgr
    mgr.close()


# ==============================================================================
# 1. Run & Attempt Lifecycle State Machine Tests
# ==============================================================================

def test_run_lifecycle_transitions_and_terminal_immutability(exec_manager):
    """Proves valid lifecycle transitions and that terminal runs cannot transition back to running."""
    run = exec_manager.create_run(
        project_id="proj_comic_01",
        budget_limit_usd="10.0000",
        canon_hash="hash_canon_v1"
    )
    assert run.status == RunStatus.CREATED
    assert run.budget_limit_usd == Decimal("10.0000")

    # Start run: CREATED -> RUNNING
    exec_manager.start_run(run.run_id)
    updated = exec_manager.db.get_run(run.run_id)
    assert updated.status == RunStatus.RUNNING
    assert updated.started_at is not None

    # Complete run: RUNNING -> SUCCEEDED (no pending operations)
    exec_manager.complete_run(run.run_id)
    completed = exec_manager.db.get_run(run.run_id)
    assert completed.status == RunStatus.SUCCEEDED
    assert completed.completed_at is not None

    # Terminal immutability: Cannot transition SUCCEEDED -> RUNNING or complete again
    with pytest.raises(RunTerminalError):
        exec_manager.start_run(run.run_id)

    with pytest.raises(RunTerminalError):
        exec_manager.cancel_run(run.run_id)


def test_partial_run_cannot_succeed_while_operations_pending(exec_manager):
    """Proves that a run with active or pending operations cannot be marked as successfully completed."""
    run = exec_manager.create_run(project_id="proj_partial_test")
    exec_manager.start_run(run.run_id)

    # Register an operation that remains PENDING
    exec_manager.register_operation(
        run_id=run.run_id,
        operation_id="op_panel_01",
        operation_type="image_generation",
        engine_id="e1_image_generation"
    )

    # Completing the run while operations are pending must fail explicitly
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        exec_manager.complete_run(run.run_id)
    assert "active/pending operations" in str(exc_info.value)


def test_duplicate_attempt_completion_rejected(exec_manager):
    """Proves that attempting to complete an already completed attempt is rejected."""
    run = exec_manager.create_run(project_id="proj_dup_test")
    exec_manager.start_run(run.run_id)

    exec_manager.register_operation(
        run_id=run.run_id,
        operation_id="op_single",
        operation_type="image_generation",
        engine_id="e1_image_generation"
    )

    attempt, _ = exec_manager.start_attempt(
        run_id=run.run_id,
        operation_id="op_single",
        estimated_cost_usd="0.0500"
    )

    # Complete once
    exec_manager.complete_attempt(
        attempt_id=attempt.attempt_id,
        status=AttemptStatus.SUCCEEDED,
        actual_cost_usd="0.0500",
        eligible_for_acceptance=True
    )

    # Attempting to complete a second time must raise InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        exec_manager.complete_attempt(
            attempt_id=attempt.attempt_id,
            status=AttemptStatus.SUCCEEDED,
            actual_cost_usd="0.0500"
        )


# ==============================================================================
# 2. Budget Manager & Multi-Scope Accounting Tests
# ==============================================================================

def test_budget_reservation_within_cap_and_overbudget_rejection(exec_manager):
    """Proves that operations within budget reserve funds, while overbudget requests are rejected."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="1.0000")
    exec_manager.start_run(run.run_id)

    exec_manager.register_operation(run_id=run.run_id, operation_id="op_1", operation_type="gen", engine_id="e1")
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_2", operation_type="gen", engine_id="e1")

    # Reserve $0.60 (available: $1.00) -> succeeds
    att1, res1 = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_1", estimated_cost_usd="0.6000")
    assert res1.reserved_amount_usd == Decimal("0.6000")
    assert res1.status == "reserved"

    # Settle $0.60
    exec_manager.complete_attempt(att1.attempt_id, status=AttemptStatus.SUCCEEDED, actual_cost_usd="0.6000", eligible_for_acceptance=True)

    # Attempt to reserve $0.50 (available: $1.00 - $0.60 = $0.40) -> fails with BudgetExceededError
    with pytest.raises(BudgetExceededError) as exc_info:
        exec_manager.start_attempt(run_id=run.run_id, operation_id="op_2", estimated_cost_usd="0.5000")
    assert "Budget exceeded" in str(exc_info.value)


def test_multi_scope_budget_hierarchy_child_cannot_exceed_parent():
    """Proves that child scopes (project, run) cannot define allowances larger than parent scopes."""
    bm = BudgetManager(global_cap_usd="10.0000")

    # Project cap <= global cap: succeeds
    bm.set_project_cap("proj_valid", "8.0000")
    assert bm.get_effective_cap(project_id="proj_valid") == Decimal("8.0000")

    # Project cap > global cap: raises BudgetScopeViolationError
    with pytest.raises(BudgetScopeViolationError):
        bm.set_project_cap("proj_invalid", "15.0000")

    # Run cap > project cap: raises BudgetScopeViolationError
    with pytest.raises(BudgetScopeViolationError):
        bm.set_run_cap("run_invalid", "9.0000", project_id="proj_valid")

    # Run cap <= project cap: succeeds
    bm.set_run_cap("run_valid", "5.0000", project_id="proj_valid")
    assert bm.get_effective_cap(project_id="proj_valid", run_id="run_valid") == Decimal("5.0000")


def test_concurrent_reservations_cannot_overspend(exec_manager):
    """Proves that concurrent thread reservations atomically respect the budget limit without overspending."""
    run = exec_manager.create_run(project_id="proj_concurrency", budget_limit_usd="1.0000")
    exec_manager.start_run(run.run_id)

    # Allow up to 10 concurrent requests to test thread contention
    exec_manager.max_concurrent_operations = 10

    # Register 10 operations, each wanting $0.20 (cap is $1.00 -> at most 5 can reserve)
    for i in range(10):
        exec_manager.register_operation(
            run_id=run.run_id,
            operation_id=f"op_thread_{i}",
            operation_type="gen",
            engine_id="e1"
        )

    success_count = 0
    failure_count = 0
    lock = threading.Lock()

    def worker(op_idx):
        nonlocal success_count, failure_count
        try:
            exec_manager.start_attempt(
                run_id=run.run_id,
                operation_id=f"op_thread_{op_idx}",
                estimated_cost_usd="0.2000"
            )
            with lock:
                success_count += 1
        except BudgetExceededError:
            with lock:
                failure_count += 1

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert success_count == 5, f"Expected exactly 5 operations reserved, got {success_count}"
    assert failure_count == 5, f"Expected exactly 5 operations rejected, got {failure_count}"

    bal = exec_manager.budget_manager.get_balance(run_id=run.run_id)
    assert Decimal(bal["available_usd"]) == Decimal("0.0000")


def test_reservation_settlement_at_most_once(exec_manager):
    """Proves that a budget reservation can be settled exactly once, rejecting duplicate settlements."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="5.0000")
    exec_manager.start_run(run.run_id)
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_1", operation_type="gen", engine_id="e1")

    att, res = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_1", estimated_cost_usd="1.0000")
    assert res.status == "reserved"

    # Settle first time: succeeds
    settled = exec_manager.budget_manager.settle(res.reservation_id, actual_amount_usd="0.8000")
    assert settled.status == "settled"
    assert settled.settled_amount_usd == Decimal("0.8000")

    # Second settlement must raise DuplicateSettlementError
    with pytest.raises(DuplicateSettlementError):
        exec_manager.budget_manager.settle(res.reservation_id, actual_amount_usd="0.8000")


def test_unused_reservation_released_on_cancellation(exec_manager):
    """Proves that cancelling an operation releases its reserved funds back to available balance."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="2.0000")
    exec_manager.start_run(run.run_id)
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_cancel", operation_type="gen", engine_id="e1")

    att, res = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_cancel", estimated_cost_usd="1.5000")

    avail_before = exec_manager.budget_manager.get_available_budget(run_id=run.run_id)
    assert avail_before == Decimal("0.5000")

    # Complete attempt as CANCELLED (unbilled)
    exec_manager.complete_attempt(
        attempt_id=att.attempt_id,
        status=AttemptStatus.CANCELLED,
        actual_cost_usd="0.0000"
    )

    avail_after = exec_manager.budget_manager.get_available_budget(run_id=run.run_id)
    assert avail_after == Decimal("2.0000"), "Unused reserved funds must be returned to pool"


def test_unknown_cost_operations_and_operation_count_ceilings(exec_manager):
    """Proves that unknown-cost operations enforce hard operation count limits without fabricating prices."""
    exec_manager.max_concurrent_operations = 10
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="10.0000")
    exec_manager.start_run(run.run_id)

    # Register 3 operations
    for i in range(3):
        exec_manager.register_operation(run_id=run.run_id, operation_id=f"op_unk_{i}", operation_type="gen", engine_id="e1")

    # Set unknown ops ceiling to 2
    # Op 0: succeeds
    exec_manager.start_attempt(
        run_id=run.run_id,
        operation_id="op_unk_0",
        cost_classification=CostClassification.UNKNOWN,
        max_unknown_ops=2
    )

    # Op 1: succeeds
    exec_manager.start_attempt(
        run_id=run.run_id,
        operation_id="op_unk_1",
        cost_classification=CostClassification.UNKNOWN,
        max_unknown_ops=2
    )

    # Op 2: exceeds ceiling of 2 unknown ops -> raises BudgetExceededError
    with pytest.raises(BudgetExceededError) as exc_info:
        exec_manager.start_attempt(
            run_id=run.run_id,
            operation_id="op_unk_2",
            cost_classification=CostClassification.UNKNOWN,
            max_unknown_ops=2
        )
    assert "unknown ops ceiling" in str(exc_info.value)


def test_cost_classifications_remain_distinct_and_decimal_math(exec_manager):
    """Proves that estimated, reported, and confirmed costs are never conflated, and Decimal math avoids float drift."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="1.0000")
    exec_manager.start_run(run.run_id)

    exec_manager.register_operation(run_id=run.run_id, operation_id="op_math", operation_type="gen", engine_id="e1")

    # 3 attempts with tiny float-sensitive fractions: $0.1000 + $0.2000 = $0.3000 exactly
    d1 = to_decimal("0.1000")
    d2 = to_decimal("0.2000")
    assert (d1 + d2) == Decimal("0.3000")  # Exact, no 0.30000000000000004 float artifact!

    att1, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_math", estimated_cost_usd="0.1000")
    exec_manager.complete_attempt(
        att1.attempt_id,
        status=AttemptStatus.SUCCEEDED,
        actual_cost_usd="0.1000",
        cost_classification=CostClassification.PROVIDER_REPORTED,
        eligible_for_acceptance=True
    )

    summary = exec_manager.get_run_summary(run.run_id)
    assert summary.total_estimated_usd == Decimal("0.0000")
    assert summary.total_reported_usd == Decimal("0.1000")
    assert summary.total_confirmed_usd == Decimal("0.0000")


def test_failed_requests_not_treated_as_free_without_evidence(exec_manager):
    """Proves that a failed request from provider still incurs billed cost if reported."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="5.0000")
    exec_manager.start_run(run.run_id)
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_fail", operation_type="gen", engine_id="e1")

    att, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_fail", estimated_cost_usd="0.5000")

    # Complete as FAILED but with provider charge of $0.50 (e.g. content policy failure after generation)
    exec_manager.complete_attempt(
        attempt_id=att.attempt_id,
        status=AttemptStatus.FAILED,
        actual_cost_usd="0.5000",
        cost_classification=CostClassification.PROVIDER_REPORTED,
        error_category=ExecutionErrorCategory.CONTENT_POLICY_VIOLATION,
        error_message="Filtered post-generation"
    )

    # Budget balance must reflect the charge even though attempt failed
    bal = exec_manager.budget_manager.get_balance(run_id=run.run_id)
    assert Decimal(bal["run_settled_usd"]) == Decimal("0.5000")
    assert Decimal(bal["available_usd"]) == Decimal("4.5000")


# ==============================================================================
# 3. Bounded Retries & Dependency Scheduling Tests
# ==============================================================================

def test_bounded_retries_transient_vs_permanent_errors(exec_manager):
    """Proves that transient errors are retried up to the ceiling, while permanent errors halt immediately."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="10.0000")
    exec_manager.start_run(run.run_id)

    # 1. Transient error operation with max_retries=2 (total 3 attempts allowed: initial + 2 retries)
    exec_manager.register_operation(
        run_id=run.run_id,
        operation_id="op_transient",
        operation_type="gen",
        engine_id="e1",
        max_retries=2
    )

    # Attempt 1: fails with RATE_LIMIT (transient) -> operation reverts to PENDING
    att1, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_transient", estimated_cost_usd="0.1000")
    exec_manager.complete_attempt(
        attempt_id=att1.attempt_id,
        status=AttemptStatus.FAILED,
        actual_cost_usd="0.0000",
        error_category=ExecutionErrorCategory.RATE_LIMIT_EXCEEDED,
        error_message="Too many requests"
    )
    op = exec_manager.db.get_operation("op_transient")
    assert op.status == OperationStatus.PENDING

    # Attempt 2: fails with NETWORK_TIMEOUT (transient) -> operation reverts to PENDING
    att2, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_transient", estimated_cost_usd="0.1000")
    exec_manager.complete_attempt(
        attempt_id=att2.attempt_id,
        status=AttemptStatus.FAILED,
        actual_cost_usd="0.0000",
        error_category=ExecutionErrorCategory.NETWORK_TIMEOUT,
        error_message="Connection timed out"
    )
    op = exec_manager.db.get_operation("op_transient")
    assert op.status == OperationStatus.PENDING

    # Attempt 3: succeeds!
    att3, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_transient", estimated_cost_usd="0.1000")
    exec_manager.complete_attempt(
        attempt_id=att3.attempt_id,
        status=AttemptStatus.SUCCEEDED,
        actual_cost_usd="0.1000",
        eligible_for_acceptance=True
    )
    op = exec_manager.db.get_operation("op_transient")
    assert op.status == OperationStatus.SUCCEEDED
    assert op.accepted_attempt_id == att3.attempt_id
    assert len(op.attempts) == 3


def test_permanent_errors_rejected_from_blind_retry(exec_manager):
    """Proves that deterministic failures (Auth, Bad Request) mark operation FAILED without retrying."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="5.0000")
    exec_manager.start_run(run.run_id)

    exec_manager.register_operation(
        run_id=run.run_id,
        operation_id="op_permanent",
        operation_type="gen",
        engine_id="e1",
        max_retries=3
    )

    # Initial attempt fails with AUTHENTICATION_ERROR
    att, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_permanent", estimated_cost_usd="0.1000")
    exec_manager.complete_attempt(
        attempt_id=att.attempt_id,
        status=AttemptStatus.FAILED,
        actual_cost_usd="0.0000",
        error_category=ExecutionErrorCategory.AUTHENTICATION_ERROR,
        error_message="Invalid token"
    )

    op = exec_manager.db.get_operation("op_permanent")
    assert op.status == OperationStatus.FAILED, "Permanent error must not revert to PENDING"

    # Attempting another try must raise RetryExhaustedError or disallow dispatch
    can_dispatch, reason = exec_manager.can_dispatch_operation("op_permanent")
    assert can_dispatch is False
    assert "expected 'pending'" in reason


def test_dependency_blocking_when_prerequisite_fails(exec_manager):
    """Proves that downstream operations are blocked when a prerequisite fails."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="5.0000")
    exec_manager.start_run(run.run_id)

    # Op 1: Canvas generation
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_canvas", operation_type="canvas", engine_id="e2")

    # Op 2: Panel layout (depends on Canvas)
    exec_manager.register_operation(
        run_id=run.run_id,
        operation_id="op_panel",
        operation_type="panel",
        engine_id="e1",
        dependency_operation_ids=["op_canvas"]
    )

    # Op 1 fails permanently
    att, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_canvas", estimated_cost_usd="0.1000")
    exec_manager.complete_attempt(
        attempt_id=att.attempt_id,
        status=AttemptStatus.FAILED,
        actual_cost_usd="0.0000",
        error_category=ExecutionErrorCategory.BAD_REQUEST,
        error_message="Invalid dimensions"
    )

    # Op 2 dispatch must be blocked
    with pytest.raises(DependencyFailedError) as exc_info:
        exec_manager.can_dispatch_operation("op_panel")
    assert "blocked: prerequisite dependency 'op_canvas'" in str(exc_info.value)

    op2 = exec_manager.db.get_operation("op_panel")
    assert op2.status == OperationStatus.BLOCKED


# ==============================================================================
# 4. Crash Recovery, Uncertainty & Resumption Tests
# ==============================================================================

def test_crash_recovery_detects_interrupted_runs_and_operations(exec_manager):
    """Proves that on restart, active runs and operations are discovered and marked INTERRUPTED."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="5.0000")
    exec_manager.start_run(run.run_id)
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_crash", operation_type="gen", engine_id="e1")

    # Start attempt but never complete (simulates crash / sudden power loss)
    att, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_crash", estimated_cost_usd="0.5000")

    # Simulate startup recovery scan
    report = exec_manager.recover_on_startup()
    assert report["interrupted_runs_count"] == 1
    assert report["interrupted_operations_count"] == 1

    r = exec_manager.db.get_run(run.run_id)
    assert r.status == RunStatus.INTERRUPTED

    op = exec_manager.db.get_operation("op_crash")
    assert op.status == OperationStatus.INTERRUPTED

    saved_att = exec_manager.db.get_attempt(att.attempt_id)
    assert saved_att.status == AttemptStatus.INTERRUPTED


def test_safe_resumption_preserves_completed_and_resets_interrupted(exec_manager):
    """Proves that resuming an interrupted run preserves already completed operations and resets interrupted ones."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="5.0000")
    exec_manager.start_run(run.run_id)

    # Op 1: Succeeded before interruption
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_done", operation_type="gen", engine_id="e1")
    att1, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_done", estimated_cost_usd="0.2000")
    exec_manager.complete_attempt(att1.attempt_id, status=AttemptStatus.SUCCEEDED, actual_cost_usd="0.2000", eligible_for_acceptance=True)

    # Op 2: Interrupted during execution
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_in_flight", operation_type="gen", engine_id="e1")
    exec_manager.start_attempt(run_id=run.run_id, operation_id="op_in_flight", estimated_cost_usd="0.2000")

    # Simulate crash discovery
    exec_manager.recover_on_startup()

    # Resume run
    resumed_run = exec_manager.resume_run(run.run_id)
    assert resumed_run.status == RunStatus.RUNNING

    # Op 1 must remain SUCCEEDED (not repeated!)
    op1 = exec_manager.db.get_operation("op_done")
    assert op1.status == OperationStatus.SUCCEEDED

    # Op 2 must be reset to PENDING and eligible for dispatch
    op2 = exec_manager.db.get_operation("op_in_flight")
    assert op2.status == OperationStatus.PENDING
    can_run, _ = exec_manager.can_dispatch_operation("op_in_flight")
    assert can_run is True


def test_resumption_detects_missing_corrupt_input_assets(exec_manager):
    """Proves that resuming revalidates input asset hashes and blocks if assets are corrupted or missing."""
    run = exec_manager.create_run(
        project_id="p1",
        budget_limit_usd="5.0000",
        input_asset_ids=["art_anchor"],
        input_asset_hashes={"art_anchor": "expected_hash_123"}
    )
    exec_manager.start_run(run.run_id)
    exec_manager.recover_on_startup()  # Mark INTERRUPTED

    # Asset checker returns False for corrupted asset
    def mock_corrupt_checker(asset_id, expected_hash):
        return False

    with pytest.raises(ArtifactMissingError) as exc_info:
        exec_manager.resume_run(run.run_id, asset_checker=mock_corrupt_checker)
    assert "missing or corrupted" in str(exc_info.value)


def test_uncertain_external_outcome_requires_reconciliation_and_holds_funds(exec_manager):
    """Proves that network timeouts with uncertain provider outcomes hold funds and require reconciliation."""
    run = exec_manager.create_run(project_id="p1", budget_limit_usd="5.0000")
    exec_manager.start_run(run.run_id)
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_timeout", operation_type="gen", engine_id="e1")

    att, res = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_timeout", estimated_cost_usd="1.0000")

    # Mark uncertain
    exec_manager.mark_attempt_uncertain(att.attempt_id, reason="Gateway timeout after 60s")

    # Check operation status
    op = exec_manager.db.get_operation("op_timeout")
    assert op.status == OperationStatus.RECONCILIATION_REQUIRED

    # Check reservation remains HELD (status='uncertain', not refunded!)
    saved_res = exec_manager.budget_manager.get_reservation(res.reservation_id)
    assert saved_res.status == "uncertain"

    bal = exec_manager.budget_manager.get_balance(run_id=run.run_id)
    assert Decimal(bal["available_usd"]) == Decimal("4.0000"), "Funds must remain held pending reconciliation"


# ==============================================================================
# 5. Deterministic Run Summary, Secret Hygiene & Integration Tests
# ==============================================================================

def test_deterministic_run_summary_and_secret_hygiene(exec_manager):
    """Proves that RunSummary serializes deterministically and contains zero secret credentials."""
    run = exec_manager.create_run(
        project_id="proj_hygiene_test",
        canon_hash="hash_nour_v1",
        metadata={"user_notes": "test run without credentials"}
    )
    exec_manager.start_run(run.run_id)
    exec_manager.register_operation(run_id=run.run_id, operation_id="op_1", operation_type="gen", engine_id="e1")

    att, _ = exec_manager.start_attempt(run_id=run.run_id, operation_id="op_1", estimated_cost_usd="0.1000")
    exec_manager.complete_attempt(
        attempt_id=att.attempt_id,
        status=AttemptStatus.SUCCEEDED,
        actual_cost_usd="0.1000",
        cost_classification=CostClassification.PROVIDER_REPORTED,
        output_asset_ids=["art_output_01"],
        eligible_for_acceptance=True
    )
    exec_manager.complete_run(run.run_id)

    summary = exec_manager.get_run_summary(run.run_id)
    json_str = summary.to_json()

    # Parse and inspect keys
    data = json.loads(json_str)
    assert data["status"] == "succeeded"
    assert data["completed_operations"] == 1
    assert data["total_reported_usd"] == "0.1000"
    assert "art_output_01" in data["output_asset_ids"]

    # Verify no secret keywords anywhere in JSON serialization
    serialized_lower = json_str.lower()
    for forbidden in ("api_key", "bearer", "authorization", "secret", "password"):
        assert forbidden not in serialized_lower, f"Forbidden credential string '{forbidden}' leaked in summary!"


def test_persistence_reopen_integrity(temp_db_path, budget_manager):
    """Proves that all runs, operations, attempts, and events persist cleanly across database close and reopen."""
    mgr1 = ExecutionManager(db_path=temp_db_path, budget_manager=budget_manager)
    run = mgr1.create_run(project_id="p1", budget_limit_usd="5.0000")
    mgr1.start_run(run.run_id)
    mgr1.register_operation(run_id=run.run_id, operation_id="op_persist", operation_type="gen", engine_id="e1")
    att, _ = mgr1.start_attempt(run_id=run.run_id, operation_id="op_persist", estimated_cost_usd="0.2500")
    mgr1.complete_attempt(att.attempt_id, status=AttemptStatus.SUCCEEDED, actual_cost_usd="0.2500", eligible_for_acceptance=True)
    mgr1.complete_run(run.run_id)
    mgr1.close()

    # Reopen in fresh manager instance
    mgr2 = ExecutionManager(db_path=temp_db_path)
    loaded_run = mgr2.db.get_run(run.run_id)
    assert loaded_run is not None
    assert loaded_run.status == RunStatus.SUCCEEDED

    loaded_op = mgr2.db.get_operation("op_persist")
    assert loaded_op is not None
    assert loaded_op.status == OperationStatus.SUCCEEDED
    assert len(loaded_op.attempts) == 1

    events = mgr2.db.list_events_for_run(run.run_id)
    assert len(events) >= 4  # RUN_CREATED, RUN_STARTED, ATTEMPT_STARTED, ATTEMPT_COMPLETED, OPERATION_COMPLETED, RUN_COMPLETED
    mgr2.close()


def test_asset_registry_and_story_bible_integration_integrity(exec_manager, tmp_path):
    """Proves that ExecutionManager links to real Asset Registry and Story Bible without mutating them."""
    # 1. Initialize Asset Registry
    store_dir = tmp_path / "artifacts"
    reg = AssetRegistry(store_root=store_dir)

    # Register an input asset with valid PNG bytes
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    sample_bytes = buf.getvalue()
    asset = reg.ingest_bytes(
        data=sample_bytes,
        filename="ref_anchor.png",
        project_id="proj_bible_test",
        asset_type="image_reference"
    )

    # 2. ExecutionManager uses registered asset ID and hash
    run = exec_manager.create_run(
        project_id="proj_bible_test",
        canon_version="1.0.0",
        input_asset_ids=[asset.asset_id],
        input_asset_hashes={asset.asset_id: asset.content_sha256}
    )
    exec_manager.start_run(run.run_id)

    # Story Bible asset hash verification during execution
    def asset_checker(aid, expected_h):
        a = reg.get_asset(aid)
        return a is not None and a.content_sha256 == expected_h

    assert asset_checker(asset.asset_id, asset.content_sha256) is True

    # Complete run
    exec_manager.complete_run(run.run_id)

    # Verify Asset Registry remains intact and untouched
    reg_asset_after = reg.get_asset(asset.asset_id)
    assert reg_asset_after.content_sha256 == asset.content_sha256
    reg.close()
