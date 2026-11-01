"""
InkLoop Human-in-the-Loop Approval & Policy Governance.
Ensures irreversible mutations and high-spend operations cannot be executed
without an explicit, cryptographically verifiable approval record.
"""
import json
import threading
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.config import PROJECT_ROOT
from app.agent.schemas import ApprovalRequest, ApprovalStatus

class ApprovalError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message

class ApprovalManager:
    """Manages durable approval records bound to project, canon hash, and operation scope."""
    _instance: Optional["ApprovalManager"] = None
    _lock = threading.RLock()

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or (PROJECT_ROOT / "runs" / "approvals.json")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._lock = threading.RLock()
        self._load()

    @classmethod
    def get_instance(cls) -> "ApprovalManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load(self) -> None:
        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                self._approvals = {
                    k: ApprovalRequest.model_validate(v) for k, v in data.items()
                }
            except Exception:
                self._approvals = {}

    def _save(self) -> None:
        payload = {k: v.model_dump() for k, v in self._approvals.items()}
        self.store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def create_request(
        self,
        project_id: str,
        operation: str,
        scope: str,
        consequence: str,
        affected_resources: List[str],
        canon_hash: str,
        arguments: Dict[str, Any],
        reversibility: str = "IRREVERSIBLE",
        cost_exposure_usd: Optional[float] = 0.0,
        plan_id: Optional[str] = None,
        step_id: Optional[str] = None,
        proposed_changes: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """Creates a pending approval record bound to specific inputs and canon hash."""
        with self._lock:
            args_str = json.dumps(arguments, sort_keys=True)
            args_hash = hashlib.sha256(args_str.encode("utf-8")).hexdigest()
            appr_id = f"appr_{hashlib.sha256(f'{operation}:{scope}:{args_hash}'.encode()).hexdigest()[:12]}"

            req = ApprovalRequest(
                approval_id=appr_id,
                plan_id=plan_id,
                step_id=step_id,
                operation=operation,
                scope=scope,
                affected_resources=affected_resources,
                reversibility=reversibility,
                consequence=consequence,
                cost_exposure_usd=cost_exposure_usd,
                status=ApprovalStatus.PENDING,
                canon_hash_at_request=canon_hash,
                arguments_hash=args_hash,
                proposed_changes=proposed_changes,
            )
            self._approvals[appr_id] = req
            self._save()
            return req

    def get_request(self, approval_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            return self._approvals.get(approval_id)

    def list_requests(self, project_id: Optional[str] = None, status: Optional[ApprovalStatus] = None) -> List[ApprovalRequest]:
        with self._lock:
            results = list(self._approvals.values())
            if status:
                results = [r for r in results if r.status == status]
            return results

    def submit_decision(self, approval_id: str, decision: str, rationale: Optional[str] = None) -> ApprovalRequest:
        """Applies an operator decision ('APPROVE' or 'REJECT') to a pending approval."""
        with self._lock:
            req = self._approvals.get(approval_id)
            if not req:
                raise ApprovalError("ERR_APPROVAL_NOT_FOUND", f"Approval request {approval_id} not found.")
            if req.status != ApprovalStatus.PENDING:
                target_status = ApprovalStatus.APPROVED if decision.upper() in ("APPROVE", "APPROVED") else ApprovalStatus.REJECTED
                if req.status == target_status:
                    # Idempotent re-submission of identical decision
                    return req
                raise ApprovalError(
                    "ERR_APPROVAL_ALREADY_DECIDED",
                    f"Approval request {approval_id} is already in state {req.status.value}."
                )

            now = datetime.now(timezone.utc).isoformat()
            if decision.upper() in ("APPROVE", "APPROVED"):
                req.status = ApprovalStatus.APPROVED
                req.decision = "APPROVED"
            else:
                req.status = ApprovalStatus.REJECTED
                req.decision = "REJECTED"

            req.decided_at = now
            req.decision_rationale = rationale
            self._save()
            return req

    def validate_permission_to_execute(
        self,
        approval_id: Optional[str],
        current_canon_hash: str,
        arguments: Dict[str, Any],
    ) -> bool:
        """
        Verifies that an approval exists, is APPROVED, has matching arguments hash,
        and that canon has not drifted since the approval was requested.
        """
        if not approval_id:
            return False

        with self._lock:
            req = self._approvals.get(approval_id)
            if not req or req.status != ApprovalStatus.APPROVED:
                return False

            # Check canon staleness
            if req.canon_hash_at_request and req.canon_hash_at_request != current_canon_hash:
                req.status = ApprovalStatus.INVALIDATED
                self._save()
                return False

            # Check arguments drift
            args_str = json.dumps(arguments, sort_keys=True)
            args_hash = hashlib.sha256(args_str.encode("utf-8")).hexdigest()
            if req.arguments_hash and req.arguments_hash != args_hash:
                req.status = ApprovalStatus.INVALIDATED
                self._save()
                return False

            return True
