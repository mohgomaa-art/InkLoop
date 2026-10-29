"""
InkLoop Execution Database (SQLite) Persistence.
Manages durable storage for runs, operations, attempts, events, and budget reservations
with WAL mode, foreign keys, secondary indexes, and crash-recovery queries.
"""
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import threading
from typing import Optional, List, Dict, Any, Union

from app.execution.states import (
    RunStatus,
    AttemptStatus,
    OperationStatus,
    CostClassification,
    BudgetScope,
    ExecutionEventType,
)
from app.execution.models import (
    RunRecord,
    OperationRecord,
    AttemptRecord,
    ExecutionEvent,
    BudgetReservation,
    to_decimal,
)


class ExecutionDB:
    """
    SQLite-backed database for run execution, attempts, events, and budget ledgers.
    Thread-safe and restart-safe.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates connection configured for WAL mode and foreign keys."""
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_database(self) -> None:
        """Initializes tables and indexes."""
        with self._lock:
            with self._get_connection() as conn:
                conn.executescript(f"""
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER PRIMARY KEY,
                    installed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    canon_version TEXT,
                    canon_hash TEXT,
                    engine_id TEXT,
                    engine_version TEXT,
                    config_hash TEXT,
                    status TEXT NOT NULL,
                    input_asset_ids_json TEXT NOT NULL,
                    input_asset_hashes_json TEXT NOT NULL,
                    required_output_asset_ids_json TEXT NOT NULL,
                    budget_limit_usd TEXT NOT NULL,
                    dry_run INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    engine_id TEXT NOT NULL,
                    declared_inputs_json TEXT NOT NULL,
                    dependencies_json TEXT NOT NULL,
                    required_outputs_json TEXT NOT NULL,
                    max_retries INTEGER NOT NULL,
                    timeout_seconds REAL,
                    status TEXT NOT NULL,
                    current_attempt_id TEXT,
                    accepted_attempt_id TEXT,
                    output_asset_ids_json TEXT NOT NULL,
                    output_asset_hashes_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    engine_id TEXT,
                    engine_version TEXT,
                    model TEXT,
                    provider TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL,
                    request_id TEXT,
                    input_asset_ids_json TEXT NOT NULL,
                    input_asset_hashes_json TEXT NOT NULL,
                    output_asset_ids_json TEXT NOT NULL,
                    output_asset_hashes_json TEXT NOT NULL,
                    error_category TEXT,
                    sanitized_error TEXT,
                    retry_reason TEXT,
                    is_retryable INTEGER NOT NULL,
                    usage_json TEXT NOT NULL,
                    cost_amount_usd TEXT,
                    cost_classification TEXT NOT NULL,
                    eligible_for_acceptance INTEGER NOT NULL,
                    verification_verdict TEXT,
                    details_json TEXT NOT NULL,
                    FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    operation_id TEXT,
                    attempt_id TEXT,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS reservations (
                    reservation_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    reserved_amount_usd TEXT NOT NULL,
                    settled_amount_usd TEXT,
                    status TEXT NOT NULL,
                    cost_classification TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    settled_at TEXT,
                    details_json TEXT NOT NULL
                );

                -- Indexes for fast lookups and crash recovery
                CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);
                CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
                CREATE INDEX IF NOT EXISTS idx_operations_run ON operations(run_id);
                CREATE INDEX IF NOT EXISTS idx_operations_status ON operations(status);
                CREATE INDEX IF NOT EXISTS idx_attempts_run ON attempts(run_id);
                CREATE INDEX IF NOT EXISTS idx_attempts_op ON attempts(operation_id);
                CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_reservations_run ON reservations(run_id);
                CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);
                """)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_info (version, installed_at) VALUES (?, datetime('now'))",
                    (self.SCHEMA_VERSION,)
                )

    # --- Run Persistence ---

    def save_run(self, run: RunRecord) -> None:
        """Inserts or replaces a run record."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT OR REPLACE INTO runs (
                    run_id, project_id, canon_version, canon_hash, engine_id, engine_version,
                    config_hash, status, input_asset_ids_json, input_asset_hashes_json,
                    required_output_asset_ids_json, budget_limit_usd, dry_run, created_at,
                    started_at, completed_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run.run_id,
                    run.project_id,
                    run.canon_version,
                    run.canon_hash,
                    run.engine_id,
                    run.engine_version,
                    run.config_hash,
                    run.status.value,
                    json.dumps(run.input_asset_ids),
                    json.dumps(run.input_asset_hashes),
                    json.dumps(run.required_output_asset_ids),
                    str(run.budget_limit_usd),
                    1 if run.dry_run else 0,
                    run.created_at,
                    run.started_at,
                    run.completed_at,
                    json.dumps(run.metadata),
                ))

    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None
    ) -> None:
        """Updates run status and timestamps."""
        with self._lock:
            with self._get_connection() as conn:
                if started_at and completed_at:
                    conn.execute(
                        "UPDATE runs SET status = ?, started_at = ?, completed_at = ? WHERE run_id = ?",
                        (status.value, started_at, completed_at, run_id)
                    )
                elif started_at:
                    conn.execute(
                        "UPDATE runs SET status = ?, started_at = ? WHERE run_id = ?",
                        (status.value, started_at, run_id)
                    )
                elif completed_at:
                    conn.execute(
                        "UPDATE runs SET status = ?, completed_at = ? WHERE run_id = ?",
                        (status.value, completed_at, run_id)
                    )
                else:
                    conn.execute(
                        "UPDATE runs SET status = ? WHERE run_id = ?",
                        (status.value, run_id)
                    )

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Loads a run record by ID."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return RunRecord(
                    run_id=row["run_id"],
                    project_id=row["project_id"],
                    canon_version=row["canon_version"],
                    canon_hash=row["canon_hash"],
                    engine_id=row["engine_id"],
                    engine_version=row["engine_version"],
                    config_hash=row["config_hash"],
                    status=RunStatus(row["status"]),
                    input_asset_ids=json.loads(row["input_asset_ids_json"]),
                    input_asset_hashes=json.loads(row["input_asset_hashes_json"]),
                    required_output_asset_ids=json.loads(row["required_output_asset_ids_json"]),
                    budget_limit_usd=to_decimal(row["budget_limit_usd"]),
                    dry_run=bool(row["dry_run"]),
                    created_at=row["created_at"],
                    started_at=row["started_at"],
                    completed_at=row["completed_at"],
                    metadata=json.loads(row["metadata_json"]),
                )

    def list_runs(self, project_id: Optional[str] = None) -> List[RunRecord]:
        """Lists runs optionally filtered by project ID."""
        with self._lock:
            with self._get_connection() as conn:
                if project_id:
                    cur = conn.execute("SELECT * FROM runs WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
                else:
                    cur = conn.execute("SELECT * FROM runs ORDER BY created_at ASC")
                results = []
                for row in cur.fetchall():
                    results.append(RunRecord(
                        run_id=row["run_id"],
                        project_id=row["project_id"],
                        canon_version=row["canon_version"],
                        canon_hash=row["canon_hash"],
                        engine_id=row["engine_id"],
                        engine_version=row["engine_version"],
                        config_hash=row["config_hash"],
                        status=RunStatus(row["status"]),
                        input_asset_ids=json.loads(row["input_asset_ids_json"]),
                        input_asset_hashes=json.loads(row["input_asset_hashes_json"]),
                        required_output_asset_ids=json.loads(row["required_output_asset_ids_json"]),
                        budget_limit_usd=to_decimal(row["budget_limit_usd"]),
                        dry_run=bool(row["dry_run"]),
                        created_at=row["created_at"],
                        started_at=row["started_at"],
                        completed_at=row["completed_at"],
                        metadata=json.loads(row["metadata_json"]),
                    ))
                return results

    # --- Operation Persistence ---

    def save_operation(self, op: OperationRecord) -> None:
        """Inserts or updates an operation record."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT OR REPLACE INTO operations (
                    operation_id, run_id, operation_type, engine_id, declared_inputs_json,
                    dependencies_json, required_outputs_json, max_retries, timeout_seconds,
                    status, current_attempt_id, accepted_attempt_id, output_asset_ids_json,
                    output_asset_hashes_json, created_at, completed_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    op.operation_id,
                    op.run_id,
                    op.operation_type,
                    op.engine_id,
                    json.dumps(op.declared_input_asset_ids),
                    json.dumps(op.dependency_operation_ids),
                    json.dumps(op.required_output_types),
                    op.max_retries,
                    op.timeout_seconds,
                    op.status.value,
                    op.current_attempt_id,
                    op.accepted_attempt_id,
                    json.dumps(op.output_asset_ids),
                    json.dumps(op.output_asset_hashes),
                    op.created_at,
                    op.completed_at,
                    json.dumps(op.metadata),
                ))

    def update_operation_status(
        self,
        operation_id: str,
        status: OperationStatus,
        current_attempt_id: Optional[str] = None,
        accepted_attempt_id: Optional[str] = None,
        output_asset_ids: Optional[List[str]] = None,
        completed_at: Optional[str] = None
    ) -> None:
        """Updates operation status and links."""
        with self._lock:
            with self._get_connection() as conn:
                updates = ["status = ?"]
                params: List[Any] = [status.value]

                if current_attempt_id is not None:
                    updates.append("current_attempt_id = ?")
                    params.append(current_attempt_id)
                if accepted_attempt_id is not None:
                    updates.append("accepted_attempt_id = ?")
                    params.append(accepted_attempt_id)
                if output_asset_ids is not None:
                    updates.append("output_asset_ids_json = ?")
                    params.append(json.dumps(output_asset_ids))
                if completed_at is not None:
                    updates.append("completed_at = ?")
                    params.append(completed_at)

                params.append(operation_id)
                query = f"UPDATE operations SET {', '.join(updates)} WHERE operation_id = ?"
                conn.execute(query, tuple(params))

    def get_operation(self, operation_id: str) -> Optional[OperationRecord]:
        """Loads an operation record with its attempts."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM operations WHERE operation_id = ?", (operation_id,))
                row = cur.fetchone()
                if not row:
                    return None

                attempts = self.list_attempts_for_operation(operation_id)
                return OperationRecord(
                    operation_id=row["operation_id"],
                    run_id=row["run_id"],
                    operation_type=row["operation_type"],
                    engine_id=row["engine_id"],
                    declared_input_asset_ids=json.loads(row["declared_inputs_json"]),
                    dependency_operation_ids=json.loads(row["dependencies_json"]),
                    required_output_types=json.loads(row["required_outputs_json"]),
                    max_retries=row["max_retries"],
                    timeout_seconds=row["timeout_seconds"],
                    status=OperationStatus(row["status"]),
                    attempts=attempts,
                    current_attempt_id=row["current_attempt_id"],
                    accepted_attempt_id=row["accepted_attempt_id"],
                    output_asset_ids=json.loads(row["output_asset_ids_json"]),
                    output_asset_hashes=json.loads(row["output_asset_hashes_json"]),
                    created_at=row["created_at"],
                    completed_at=row["completed_at"],
                    metadata=json.loads(row["metadata_json"]),
                )

    def list_operations_for_run(self, run_id: str) -> List[OperationRecord]:
        """Loads all operations belonging to a run."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM operations WHERE run_id = ? ORDER BY created_at ASC",
                    (run_id,)
                )
                ops = []
                for row in cur.fetchall():
                    op_id = row["operation_id"]
                    attempts = self.list_attempts_for_operation(op_id)
                    ops.append(OperationRecord(
                        operation_id=op_id,
                        run_id=row["run_id"],
                        operation_type=row["operation_type"],
                        engine_id=row["engine_id"],
                        declared_input_asset_ids=json.loads(row["declared_inputs_json"]),
                        dependency_operation_ids=json.loads(row["dependencies_json"]),
                        required_output_types=json.loads(row["required_outputs_json"]),
                        max_retries=row["max_retries"],
                        timeout_seconds=row["timeout_seconds"],
                        status=OperationStatus(row["status"]),
                        attempts=attempts,
                        current_attempt_id=row["current_attempt_id"],
                        accepted_attempt_id=row["accepted_attempt_id"],
                        output_asset_ids=json.loads(row["output_asset_ids_json"]),
                        output_asset_hashes=json.loads(row["output_asset_hashes_json"]),
                        created_at=row["created_at"],
                        completed_at=row["completed_at"],
                        metadata=json.loads(row["metadata_json"]),
                    ))
                return ops

    # --- Attempt Persistence ---

    def save_attempt(self, attempt: AttemptRecord) -> None:
        """Inserts or updates an attempt record."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT OR REPLACE INTO attempts (
                    attempt_id, run_id, operation_id, attempt_number, status, engine_id,
                    engine_version, model, provider, started_at, completed_at, duration_seconds,
                    request_id, input_asset_ids_json, input_asset_hashes_json, output_asset_ids_json,
                    output_asset_hashes_json, error_category, sanitized_error, retry_reason,
                    is_retryable, usage_json, cost_amount_usd, cost_classification,
                    eligible_for_acceptance, verification_verdict, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    attempt.attempt_id,
                    attempt.run_id,
                    attempt.operation_id,
                    attempt.attempt_number,
                    attempt.status.value,
                    attempt.engine_id,
                    attempt.engine_version,
                    attempt.model,
                    attempt.provider,
                    attempt.started_at,
                    attempt.completed_at,
                    attempt.duration_seconds,
                    attempt.request_id,
                    json.dumps(attempt.input_asset_ids),
                    json.dumps(attempt.input_asset_hashes),
                    json.dumps(attempt.output_asset_ids),
                    json.dumps(attempt.output_asset_hashes),
                    attempt.error_category,
                    attempt.sanitized_error,
                    attempt.retry_reason,
                    1 if attempt.is_retryable else 0,
                    json.dumps(attempt.usage),
                    str(attempt.cost_amount_usd) if attempt.cost_amount_usd is not None else None,
                    attempt.cost_classification.value,
                    1 if attempt.eligible_for_acceptance else 0,
                    attempt.verification_verdict,
                    json.dumps(attempt.details),
                ))

    def get_attempt(self, attempt_id: str) -> Optional[AttemptRecord]:
        """Loads an attempt record by ID."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM attempts WHERE attempt_id = ?", (attempt_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_attempt(row)

    def list_attempts_for_operation(self, operation_id: str) -> List[AttemptRecord]:
        """Loads all attempts for an operation ordered by attempt number."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM attempts WHERE operation_id = ? ORDER BY attempt_number ASC",
                    (operation_id,)
                )
                return [self._row_to_attempt(r) for r in cur.fetchall()]

    def list_attempts_for_run(self, run_id: str) -> List[AttemptRecord]:
        """Loads all attempts for an entire run."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM attempts WHERE run_id = ? ORDER BY started_at ASC",
                    (run_id,)
                )
                return [self._row_to_attempt(r) for r in cur.fetchall()]

    def _row_to_attempt(self, row: sqlite3.Row) -> AttemptRecord:
        cost_val = row["cost_amount_usd"]
        return AttemptRecord(
            attempt_id=row["attempt_id"],
            run_id=row["run_id"],
            operation_id=row["operation_id"],
            attempt_number=row["attempt_number"],
            status=AttemptStatus(row["status"]),
            engine_id=row["engine_id"],
            engine_version=row["engine_version"],
            model=row["model"],
            provider=row["provider"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            duration_seconds=row["duration_seconds"],
            request_id=row["request_id"],
            input_asset_ids=json.loads(row["input_asset_ids_json"]),
            input_asset_hashes=json.loads(row["input_asset_hashes_json"]),
            output_asset_ids=json.loads(row["output_asset_ids_json"]),
            output_asset_hashes=json.loads(row["output_asset_hashes_json"]),
            error_category=row["error_category"],
            sanitized_error=row["sanitized_error"],
            retry_reason=row["retry_reason"],
            is_retryable=bool(row["is_retryable"]),
            usage=json.loads(row["usage_json"]),
            cost_amount_usd=to_decimal(cost_val) if cost_val is not None else None,
            cost_classification=CostClassification(row["cost_classification"]),
            eligible_for_acceptance=bool(row["eligible_for_acceptance"]),
            verification_verdict=row["verification_verdict"],
            details=json.loads(row["details_json"]),
        )

    # --- Append-Only Event Persistence ---

    def append_event(self, event: ExecutionEvent) -> None:
        """Appends a structured event to the audit trail."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT INTO events (
                    event_id, run_id, operation_id, attempt_id, event_type,
                    timestamp, schema_version, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.run_id,
                    event.operation_id,
                    event.attempt_id,
                    event.event_type.value,
                    event.timestamp,
                    event.schema_version,
                    json.dumps(event.data),
                ))

    def list_events_for_run(self, run_id: str) -> List[ExecutionEvent]:
        """Loads events for a run ordered by timestamp."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM events WHERE run_id = ? ORDER BY timestamp ASC",
                    (run_id,)
                )
                events = []
                for row in cur.fetchall():
                    events.append(ExecutionEvent(
                        event_id=row["event_id"],
                        run_id=row["run_id"],
                        operation_id=row["operation_id"],
                        attempt_id=row["attempt_id"],
                        event_type=ExecutionEventType(row["event_type"]),
                        timestamp=row["timestamp"],
                        schema_version=row["schema_version"],
                        data=json.loads(row["data_json"]),
                    ))
                return events

    # --- Budget Reservation Persistence ---

    def save_reservation(self, res: BudgetReservation) -> None:
        """Inserts or replaces a budget reservation."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT OR REPLACE INTO reservations (
                    reservation_id, run_id, operation_id, attempt_id, scope,
                    reserved_amount_usd, settled_amount_usd, status, cost_classification,
                    created_at, settled_at, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    res.reservation_id,
                    res.run_id,
                    res.operation_id,
                    res.attempt_id,
                    res.scope.value,
                    str(res.reserved_amount_usd),
                    str(res.settled_amount_usd) if res.settled_amount_usd is not None else None,
                    res.status,
                    res.cost_classification.value,
                    res.created_at,
                    res.settled_at,
                    json.dumps(res.details),
                ))

    def get_reservation(self, reservation_id: str) -> Optional[BudgetReservation]:
        """Loads a reservation by ID."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM reservations WHERE reservation_id = ?", (reservation_id,))
                row = cur.fetchone()
                if not row:
                    return None
                settled_val = row["settled_amount_usd"]
                return BudgetReservation(
                    reservation_id=row["reservation_id"],
                    run_id=row["run_id"],
                    operation_id=row["operation_id"],
                    attempt_id=row["attempt_id"],
                    scope=BudgetScope(row["scope"]),
                    reserved_amount_usd=to_decimal(row["reserved_amount_usd"]),
                    settled_amount_usd=to_decimal(settled_val) if settled_val is not None else None,
                    status=row["status"],
                    cost_classification=CostClassification(row["cost_classification"]),
                    created_at=row["created_at"],
                    settled_at=row["settled_at"],
                    details=json.loads(row["details_json"]),
                )

    def list_reservations_for_run(self, run_id: str) -> List[BudgetReservation]:
        """Loads all reservations for a run."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM reservations WHERE run_id = ? ORDER BY created_at ASC",
                    (run_id,)
                )
                results = []
                for row in cur.fetchall():
                    settled_val = row["settled_amount_usd"]
                    results.append(BudgetReservation(
                        reservation_id=row["reservation_id"],
                        run_id=row["run_id"],
                        operation_id=row["operation_id"],
                        attempt_id=row["attempt_id"],
                        scope=BudgetScope(row["scope"]),
                        reserved_amount_usd=to_decimal(row["reserved_amount_usd"]),
                        settled_amount_usd=to_decimal(settled_val) if settled_val is not None else None,
                        status=row["status"],
                        cost_classification=CostClassification(row["cost_classification"]),
                        created_at=row["created_at"],
                        settled_at=row["settled_at"],
                        details=json.loads(row["details_json"]),
                    ))
                return results

    # --- Crash Recovery Queries ---

    def find_interrupted_runs(self) -> List[RunRecord]:
        """Finds all runs that were running or queued when the process terminated."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM runs WHERE status IN (?, ?) ORDER BY created_at ASC",
                    (RunStatus.RUNNING.value, RunStatus.QUEUED.value)
                )
                results = []
                for row in cur.fetchall():
                    results.append(RunRecord(
                        run_id=row["run_id"],
                        project_id=row["project_id"],
                        canon_version=row["canon_version"],
                        canon_hash=row["canon_hash"],
                        engine_id=row["engine_id"],
                        engine_version=row["engine_version"],
                        config_hash=row["config_hash"],
                        status=RunStatus(row["status"]),
                        input_asset_ids=json.loads(row["input_asset_ids_json"]),
                        input_asset_hashes=json.loads(row["input_asset_hashes_json"]),
                        required_output_asset_ids=json.loads(row["required_output_asset_ids_json"]),
                        budget_limit_usd=to_decimal(row["budget_limit_usd"]),
                        dry_run=bool(row["dry_run"]),
                        created_at=row["created_at"],
                        started_at=row["started_at"],
                        completed_at=row["completed_at"],
                        metadata=json.loads(row["metadata_json"]),
                    ))
                return results

    def find_interrupted_operations(self) -> List[OperationRecord]:
        """Finds all operations that were running when the process terminated."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM operations WHERE status = ? ORDER BY created_at ASC",
                    (OperationStatus.RUNNING.value,)
                )
                ops = []
                for row in cur.fetchall():
                    op_id = row["operation_id"]
                    attempts = self.list_attempts_for_operation(op_id)
                    ops.append(OperationRecord(
                        operation_id=op_id,
                        run_id=row["run_id"],
                        operation_type=row["operation_type"],
                        engine_id=row["engine_id"],
                        declared_input_asset_ids=json.loads(row["declared_inputs_json"]),
                        dependency_operation_ids=json.loads(row["dependencies_json"]),
                        required_output_types=json.loads(row["required_outputs_json"]),
                        max_retries=row["max_retries"],
                        timeout_seconds=row["timeout_seconds"],
                        status=OperationStatus(row["status"]),
                        attempts=attempts,
                        current_attempt_id=row["current_attempt_id"],
                        accepted_attempt_id=row["accepted_attempt_id"],
                        output_asset_ids=json.loads(row["output_asset_ids_json"]),
                        output_asset_hashes=json.loads(row["output_asset_hashes_json"]),
                        created_at=row["created_at"],
                        completed_at=row["completed_at"],
                        metadata=json.loads(row["metadata_json"]),
                    ))
                return ops

    def find_uncertain_reservations(self) -> List[BudgetReservation]:
        """Finds all reservations in 'uncertain' or 'reserved' status requiring reconciliation."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM reservations WHERE status IN ('uncertain', 'reserved') ORDER BY created_at ASC"
                )
                results = []
                for row in cur.fetchall():
                    settled_val = row["settled_amount_usd"]
                    results.append(BudgetReservation(
                        reservation_id=row["reservation_id"],
                        run_id=row["run_id"],
                        operation_id=row["operation_id"],
                        attempt_id=row["attempt_id"],
                        scope=BudgetScope(row["scope"]),
                        reserved_amount_usd=to_decimal(row["reserved_amount_usd"]),
                        settled_amount_usd=to_decimal(settled_val) if settled_val is not None else None,
                        status=row["status"],
                        cost_classification=CostClassification(row["cost_classification"]),
                        created_at=row["created_at"],
                        settled_at=row["settled_at"],
                        details=json.loads(row["details_json"]),
                    ))
                return results

    def close(self) -> None:
        """Closes any shared resources if necessary."""
        pass
