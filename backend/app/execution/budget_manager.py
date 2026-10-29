"""
InkLoop Thread-Safe Multi-Scope Budget Manager.
Enforces atomic budget reservation and settlement across Global, Project, Run,
and Operation scopes using exact Python Decimal arithmetic.
"""
from decimal import Decimal
import threading
from typing import Optional, Dict, Any, Union

from app.contracts.identity import IdPrefix, generate_id
from app.execution.states import CostClassification, BudgetScope
from app.execution.models import BudgetLimit, BudgetReservation, to_decimal, utc_now_iso
from app.execution.errors import (
    BudgetExceededError,
    BudgetScopeViolationError,
    DuplicateSettlementError,
    UnreservedSettlementError,
)


class BudgetManager:
    """
    Thread-safe, multi-scope Budget Manager.
    Guarantees:
    - Pre-dispatch atomic reservation: operations cannot run if funds are insufficient.
    - Exact Decimal monetary math: avoids binary float drift.
    - Scope hierarchy: child scopes can never exceed stricter parent ceilings.
    - Exactly-once settlement: duplicate settlements are rejected.
    - Distinction between estimates, provider reports, and billing confirmations.
    - Unknown cost handling: enforces operation limits when pricing is unknown.
    """

    def __init__(
        self,
        global_cap_usd: Union[int, float, str, Decimal] = "25.0000",
        project_caps: Optional[Dict[str, Decimal]] = None,
        run_caps: Optional[Dict[str, Decimal]] = None,
    ):
        self._lock = threading.RLock()
        self.global_cap_usd = to_decimal(global_cap_usd)
        self.project_caps: Dict[str, Decimal] = {}
        if project_caps:
            for pid, cap in project_caps.items():
                self.set_project_cap(pid, cap)

        self.run_caps: Dict[str, Decimal] = {}
        if run_caps:
            for rid, cap in run_caps.items():
                self.set_run_cap(rid, cap)

        # Active reservations keyed by reservation_id
        self._reservations: Dict[str, BudgetReservation] = {}

        # Accounting ledgers keyed by scope identifier
        # Global key: "global"
        # Project key: "proj:<project_id>"
        # Run key: "run:<run_id>"
        self._settled_by_scope: Dict[str, Decimal] = {}
        self._reserved_by_scope: Dict[str, Decimal] = {}
        self._released_by_scope: Dict[str, Decimal] = {}
        self._unknown_cost_ops_count: Dict[str, int] = {}

    def set_project_cap(self, project_id: str, cap_usd: Union[int, float, str, Decimal]) -> Decimal:
        """Sets a project-level spending cap, ensuring it does not exceed the global cap."""
        with self._lock:
            dec_cap = to_decimal(cap_usd)
            if dec_cap > self.global_cap_usd:
                raise BudgetScopeViolationError(
                    child_scope=f"project '{project_id}'",
                    child_limit=str(dec_cap),
                    parent_scope="global",
                    parent_limit=str(self.global_cap_usd)
                )
            self.project_caps[project_id] = dec_cap
            return dec_cap

    def set_run_cap(
        self,
        run_id: str,
        cap_usd: Union[int, float, str, Decimal],
        project_id: Optional[str] = None
    ) -> Decimal:
        """Sets a run-level spending cap, ensuring it does not exceed parent project or global caps."""
        with self._lock:
            dec_cap = to_decimal(cap_usd)
            parent_cap = self.global_cap_usd
            parent_name = "global"

            if project_id and project_id in self.project_caps:
                parent_cap = min(parent_cap, self.project_caps[project_id])
                parent_name = f"project '{project_id}'"

            if dec_cap > parent_cap:
                raise BudgetScopeViolationError(
                    child_scope=f"run '{run_id}'",
                    child_limit=str(dec_cap),
                    parent_scope=parent_name,
                    parent_limit=str(parent_cap)
                )
            self.run_caps[run_id] = dec_cap
            return dec_cap

    def get_effective_cap(
        self,
        project_id: Optional[str] = None,
        run_id: Optional[str] = None,
        operation_cap_usd: Optional[Decimal] = None
    ) -> Decimal:
        """Calculates the strictest effective cap across applicable scopes."""
        with self._lock:
            caps = [self.global_cap_usd]
            if project_id and project_id in self.project_caps:
                caps.append(self.project_caps[project_id])
            if run_id and run_id in self.run_caps:
                caps.append(self.run_caps[run_id])
            if operation_cap_usd is not None:
                caps.append(to_decimal(operation_cap_usd))
            return min(caps)

    def _scope_keys(self, project_id: Optional[str], run_id: Optional[str]) -> list[str]:
        """Returns list of applicable scope keys from narrowest to widest."""
        keys = ["global"]
        if project_id:
            keys.append(f"proj:{project_id}")
        if run_id:
            keys.append(f"run:{run_id}")
        return keys

    def get_available_budget(
        self,
        project_id: Optional[str] = None,
        run_id: Optional[str] = None,
        operation_cap_usd: Optional[Decimal] = None
    ) -> Decimal:
        """Returns the remaining uncommitted budget across all relevant scopes."""
        with self._lock:
            effective_cap = self.get_effective_cap(project_id, run_id, operation_cap_usd)

            # Find maximum committed funds across the active hierarchy
            scope_keys = self._scope_keys(project_id, run_id)
            min_remaining = effective_cap

            for key in scope_keys:
                settled = self._settled_by_scope.get(key, Decimal("0.0000"))
                reserved = self._reserved_by_scope.get(key, Decimal("0.0000"))
                committed = settled + reserved

                # Cap for this specific key
                if key == "global":
                    cap = self.global_cap_usd
                elif key.startswith("proj:"):
                    pid = key.split(":", 1)[1]
                    cap = self.project_caps.get(pid, self.global_cap_usd)
                elif key.startswith("run:"):
                    rid = key.split(":", 1)[1]
                    cap = self.run_caps.get(rid, self.global_cap_usd)
                else:
                    cap = self.global_cap_usd

                rem = cap - committed
                if rem < min_remaining:
                    min_remaining = rem

            return max(Decimal("0.0000"), min_remaining)

    def reserve(
        self,
        run_id: str,
        operation_id: str,
        attempt_id: str,
        amount_usd: Union[int, float, str, Decimal],
        classification: CostClassification = CostClassification.RESERVED,
        project_id: Optional[str] = None,
        scope: BudgetScope = BudgetScope.RUN,
        max_unknown_ops: Optional[int] = None,
    ) -> BudgetReservation:
        """
        Atomically reserves funds before an operation attempt is dispatched.
        Raises BudgetExceededError if requested amount exceeds remaining allowance.
        """
        with self._lock:
            dec_amount = to_decimal(amount_usd)
            available = self.get_available_budget(project_id, run_id)

            if dec_amount > available:
                raise BudgetExceededError(
                    requested_usd=str(dec_amount),
                    available_usd=str(available),
                    scope=scope.value,
                    entity_id=f"run={run_id},op={operation_id},att={attempt_id}"
                )

            # Check unknown cost ops ceiling if applicable
            if classification == CostClassification.UNKNOWN and max_unknown_ops is not None:
                current_unknown = self._unknown_cost_ops_count.get(run_id, 0)
                if current_unknown >= max_unknown_ops:
                    raise BudgetExceededError(
                        requested_usd=str(dec_amount),
                        available_usd=str(available),
                        scope="unknown_ops_ceiling",
                        entity_id=f"run={run_id} reached unknown ops ceiling {max_unknown_ops}"
                    )
                self._unknown_cost_ops_count[run_id] = current_unknown + 1

            # Commit reservation to all applicable scope ledgers
            for key in self._scope_keys(project_id, run_id):
                self._reserved_by_scope[key] = self._reserved_by_scope.get(key, Decimal("0.0000")) + dec_amount

            reservation_id = generate_id(IdPrefix.RESERVATION, slug=f"r_{attempt_id}")
            reservation = BudgetReservation(
                reservation_id=reservation_id,
                run_id=run_id,
                operation_id=operation_id,
                attempt_id=attempt_id,
                scope=scope,
                reserved_amount_usd=dec_amount,
                status="reserved",
                cost_classification=classification,
                created_at=utc_now_iso(),
            )
            self._reservations[reservation_id] = reservation
            return reservation

    def settle(
        self,
        reservation_id: str,
        actual_amount_usd: Optional[Union[int, float, str, Decimal]] = None,
        classification: CostClassification = CostClassification.PROVIDER_REPORTED,
        project_id: Optional[str] = None,
    ) -> BudgetReservation:
        """
        Settles a prior reservation exactly once.
        Adjusts ledgers by releasing the difference if actual < reserved,
        or absorbing additional spend if actual > reserved.
        """
        with self._lock:
            if reservation_id not in self._reservations:
                raise UnreservedSettlementError(reservation_id)

            res = self._reservations[reservation_id]
            if res.status != "reserved":
                raise DuplicateSettlementError(reservation_id, res.status)

            reserved = res.reserved_amount_usd
            settled_amount = to_decimal(actual_amount_usd) if actual_amount_usd is not None else reserved

            # Update ledgers across scopes
            for key in self._scope_keys(project_id, res.run_id):
                # Subtract reserved amount from active reservations
                self._reserved_by_scope[key] = max(
                    Decimal("0.0000"),
                    self._reserved_by_scope.get(key, Decimal("0.0000")) - reserved
                )
                # Add settled amount to confirmed spend
                self._settled_by_scope[key] = self._settled_by_scope.get(key, Decimal("0.0000")) + settled_amount

            res.status = "settled"
            res.settled_amount_usd = settled_amount
            res.settled_at = utc_now_iso()
            res.cost_classification = classification
            return res

    def release(
        self,
        reservation_id: str,
        reason: str = "cancelled_or_unbilled",
        project_id: Optional[str] = None,
    ) -> BudgetReservation:
        """
        Releases an unused budget reservation back to the available pool.
        """
        with self._lock:
            if reservation_id not in self._reservations:
                raise UnreservedSettlementError(reservation_id)

            res = self._reservations[reservation_id]
            if res.status != "reserved":
                raise DuplicateSettlementError(reservation_id, res.status)

            reserved = res.reserved_amount_usd
            for key in self._scope_keys(project_id, res.run_id):
                self._reserved_by_scope[key] = max(
                    Decimal("0.0000"),
                    self._reserved_by_scope.get(key, Decimal("0.0000")) - reserved
                )
                self._released_by_scope[key] = self._released_by_scope.get(key, Decimal("0.0000")) + reserved

            res.status = "released"
            res.details["release_reason"] = reason
            return res

    def mark_uncertain(
        self,
        reservation_id: str,
        reason: str = "network_timeout_or_interruption"
    ) -> BudgetReservation:
        """
        Marks a reservation as uncertain (e.g. lost response on remote call).
        Keeps the reservation held in reserved funds until reconciliation.
        """
        with self._lock:
            if reservation_id not in self._reservations:
                raise UnreservedSettlementError(reservation_id)

            res = self._reservations[reservation_id]
            if res.status != "reserved":
                raise DuplicateSettlementError(reservation_id, res.status)

            res.status = "uncertain"
            res.details["uncertain_reason"] = reason
            return res

    def get_reservation(self, reservation_id: str) -> Optional[BudgetReservation]:
        """Retrieves a reservation by ID."""
        with self._lock:
            return self._reservations.get(reservation_id)

    def get_balance(
        self,
        project_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Provides a detailed balance breakdown for monitoring."""
        with self._lock:
            effective_cap = self.get_effective_cap(project_id, run_id)
            available = self.get_available_budget(project_id, run_id)

            global_settled = self._settled_by_scope.get("global", Decimal("0.0000"))
            global_reserved = self._reserved_by_scope.get("global", Decimal("0.0000"))

            run_settled = Decimal("0.0000")
            run_reserved = Decimal("0.0000")
            if run_id:
                run_settled = self._settled_by_scope.get(f"run:{run_id}", Decimal("0.0000"))
                run_reserved = self._reserved_by_scope.get(f"run:{run_id}", Decimal("0.0000"))

            return {
                "effective_cap_usd": str(effective_cap),
                "available_usd": str(available),
                "global_settled_usd": str(global_settled),
                "global_reserved_usd": str(global_reserved),
                "run_settled_usd": str(run_settled) if run_id else None,
                "run_reserved_usd": str(run_reserved) if run_id else None,
                "is_exhausted": available <= Decimal("0.0000"),
            }
