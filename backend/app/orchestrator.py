"""
Six-Panel Batch Generation Orchestrator for InkLoop.
Coordinates multi-panel generation with independent context isolation,
bounded retries, spend cap enforcement, resumability, and complete auditable attempt logging.
"""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Union

from app.config import InkLoopConfig, PROJECT_ROOT
from app.schemas import (
    BatchSpec,
    BatchSummary,
    BatchStatus,
    SceneSpec,
    PanelResult,
    PanelStatus,
    PanelContextPacket,
    GenerationAttemptRecord,
    ErrorCategory,
    RetryDecision,
    ReferenceAsset,
    VerificationResult,
)
from app.context_builder import build_panel_context_packet
from app.image_adapter import (
    ImageGenerationAdapter,
    SimulatedImageGenerationAdapter,
    GenerationRequest,
    GenerationResponse,
)
from app.execution import AttemptStatus, CostClassification, ExecutionErrorCategory

class BatchOrchestrator:
    """
    Core backend service for orchestrating multi-panel comic generation batches.
    Guarantees:
    - Pure-code independent context assembly per panel (no cross-panel conversational drift).
    - Bounded retries respecting per-panel retry ceilings and global spend caps.
    - Zero credential leakage in attempts, logs, or persistent records.
    - Transparent accounting distinguishing live provider costs from synthetic simulation fixtures.
    - Full reproducibility and safe resumability without redundant re-generation.
    - Distinct semantics between generation success, visual verification, and panel acceptance.
    """

    def __init__(
        self,
        config: InkLoopConfig,
        adapter: ImageGenerationAdapter,
        run_log_dir: Optional[Path] = None,
        verifier: Optional[Callable[[Optional[ReferenceAsset], bytes, Any], VerificationResult]] = None,
        execution_manager: Optional[Any] = None,
        asset_registry: Optional[Any] = None,
    ):
        self.config = config
        self.adapter = adapter
        self.run_log_dir = run_log_dir or (PROJECT_ROOT / "runs" / "batches")
        self.run_log_dir.mkdir(parents=True, exist_ok=True)
        self.verifier = verifier
        self.execution_manager = execution_manager
        self.asset_registry = asset_registry
        self._execution_attempt_ids: Dict[str, str] = {}

    def _resolve_reference_bytes(self, asset: ReferenceAsset) -> Optional[bytes]:
        """Resolves raw bytes for a canonical reference asset if accessible on disk."""
        p = Path(asset.file_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if p.exists() and p.is_file():
            try:
                return p.read_bytes()
            except Exception:
                return None
        return None

    def _compute_sha256(self, data: bytes) -> str:
        """Computes SHA-256 hash from raw output bytes."""
        return hashlib.sha256(data).hexdigest()

    def _build_attempt_metadata(self, packet: PanelContextPacket, resp: Optional[GenerationResponse] = None) -> Dict[str, Any]:
        """Combines adapter response metadata with deterministic knowledge catalogue provenance."""
        meta = dict(resp.sanitized_metadata) if (resp and resp.sanitized_metadata) else {}
        if packet.knowledge_selection_hash:
            meta["catalogue_version"] = packet.catalogue_version
            meta["knowledge_selection_hash"] = packet.knowledge_selection_hash
            meta["selected_knowledge_ids"] = packet.selected_knowledge_ids
            meta["knowledge_provenance_ids"] = packet.knowledge_provenance_ids
        return meta

    def _is_retryable_error(self, category: Optional[ErrorCategory]) -> bool:
        """
        Determines if an error category qualifies for bounded retry.
        Permanent errors (Auth, Bad Request) must never enter retry loops.
        """
        if category in (
            ErrorCategory.RATE_LIMIT_EXCEEDED,
            ErrorCategory.SERVER_ERROR,
            ErrorCategory.NETWORK_TIMEOUT,
            ErrorCategory.CONTENT_POLICY_VIOLATION,
        ):
            return True
        return False

    def _record_execution_manager_attempt(
        self,
        batch_id: str,
        panel_id: str,
        attempt_id: str,
        resp: Optional[GenerationResponse],
        v_status: str,
        v_result: Optional[VerificationResult],
        output_path_str: Optional[str],
        output_content_hash: Optional[str] = None,
        retryable: bool = False,
        error_category: Optional[ExecutionErrorCategory] = None,
        error_message: Optional[str] = None,
        eligible_for_acceptance: bool = False,
    ) -> None:
        """Records attempt outcome into append-only ExecutionManager if configured."""
        if self.execution_manager is None:
            return
        execution_attempt_id = self._execution_attempt_ids.pop(attempt_id, None)
        if execution_attempt_id is None:
            raise RuntimeError(f"Execution Manager attempt was not started for '{attempt_id}'.")
        try:
            is_simulated = bool(resp and resp.is_simulated)
            if resp is not None and resp.cost_usd is not None:
                cost_classification = CostClassification.ESTIMATED if is_simulated else CostClassification.PROVIDER_REPORTED
            else:
                cost_classification = CostClassification.UNKNOWN
            self.execution_manager.complete_attempt(
                attempt_id=execution_attempt_id,
                status=AttemptStatus.SUCCEEDED if eligible_for_acceptance else AttemptStatus.FAILED,
                actual_cost_usd=resp.cost_usd if resp is not None else None,
                cost_classification=cost_classification,
                output_asset_ids=[f"asset_{panel_id}"] if output_path_str else [],
                output_asset_hashes={f"asset_{panel_id}": output_content_hash} if output_path_str and output_content_hash else {},
                usage=resp.usage if resp and resp.usage else None,
                error_category=error_category if not eligible_for_acceptance else None,
                error_message=error_message if not eligible_for_acceptance else None,
                is_retryable=retryable if not eligible_for_acceptance else False,
                verification_verdict=v_status,
                eligible_for_acceptance=eligible_for_acceptance,
                details={"verification_status": v_status,
                         "verification_rejection_reason": v_result.rejection_reason if v_result else None},
            )
        except Exception:
            self._execution_attempt_ids[attempt_id] = execution_attempt_id
            raise

    def orchestrate_batch(
        self,
        batch_spec: BatchSpec,
        prior_attempt_offsets: Optional[Dict[str, int]] = None
    ) -> BatchSummary:
        """
        Executes generation for all scenes in a validated batch specification.
        Maintains canonical scene ordering and logs every attempt independently.
        """
        batch_id = batch_spec.batch_id
        start_time_iso = datetime.now(timezone.utc).isoformat()
        start_t = datetime.now(timezone.utc)

        # 1. Preserve canonical scene ordering
        sorted_scenes = sorted(batch_spec.scenes, key=lambda s: s.scene_index)
        bible_version_str = str(getattr(batch_spec.story_bible, "bible_version", getattr(batch_spec.story_bible, "version", "1.0.0")))

        # Setup output storage if requested
        output_dir_path: Optional[Path] = None
        if batch_spec.output_dir:
            output_dir_path = Path(batch_spec.output_dir)
            if not output_dir_path.is_absolute():
                output_dir_path = PROJECT_ROOT / output_dir_path
            output_dir_path.mkdir(parents=True, exist_ok=True)

        all_attempts: List[GenerationAttemptRecord] = []
        panel_results: List[PanelResult] = []
        cumulative_cost: float = 0.0
        missing_cost = False
        missing_usage = False
        accumulated_usage: Dict[str, Any] = {}
        budget_exhausted = False

        # Enforce global spending cap: caller cannot bypass config's global spend cap
        effective_spend_cap = min(batch_spec.spend_cap_usd, self.config.global_spend_cap_usd)

        # Simulation detection
        is_simulated = getattr(self.adapter, "is_simulated", False) or isinstance(self.adapter, SimulatedImageGenerationAdapter)

        max_retries = min(batch_spec.max_retries_per_panel, self.config.max_retries_per_panel)
        max_attempts = 1 + max_retries

        # Estimate per-operation cost for budget enforcement ($0.01 per image baseline)
        estimated_cost_per_op = 0.01
        attempt_offsets = prior_attempt_offsets or {}

        # Execution Manager integration: register run and operations if manager provided
        if self.execution_manager is not None:
            self.execution_manager.create_run(
                project_id=batch_spec.project_id,
                canon_version=bible_version_str,
                canon_hash=getattr(batch_spec.story_bible, "canon_hash", None),
                engine_id="orchestrator",
                engine_version="1.0.0",
                budget_limit_usd=effective_spend_cap,
                dry_run=is_simulated,
                run_id=batch_id,
            )
            self.execution_manager.start_run(batch_id)
            for sc in sorted_scenes:
                p_id = f"panel_{sc.scene_index + 1:02d}"
                self.execution_manager.register_operation(
                    run_id=batch_id,
                    operation_id=f"{batch_id}_{p_id}",
                    engine_id="image_generation",
                    operation_type="generate_panel",
                    max_retries=max_retries,
                )

        for scene in sorted_scenes:
            panel_id = f"panel_{scene.scene_index + 1:02d}"
            prior_offset = attempt_offsets.get(panel_id, 0)

            # 2. Build independent context packet (pure code, zero hidden state)
            packet = build_panel_context_packet(
                story_bible=batch_spec.story_bible,
                scene=scene,
                panel_id=panel_id,
                story_id=batch_spec.story_id,
                project_id=batch_spec.project_id,
                model=batch_spec.model,
            )

            # 3. Resolve canonical reference bytes for conditioning
            ref_bytes: Optional[bytes] = None
            if packet.reference_assets:
                ref_bytes = self._resolve_reference_bytes(packet.reference_assets[0])

            panel_accepted = False
            panel_status = PanelStatus.PENDING
            panel_attempts_count = 0
            accepted_attempt_id: Optional[str] = None
            accepted_output_path: Optional[str] = None
            accepted_output_hash: Optional[str] = None
            accepted_verif_result: Optional[VerificationResult] = None
            accepted_verif_status: str = "UNVERIFIED"

            # 4. Bounded retry loop for this panel
            for attempt_idx in range(1, max_attempts + 1):
                panel_attempts_count += 1
                total_attempt_number = prior_offset + attempt_idx
                retry_count = attempt_idx - 1
                attempt_id = f"{batch_id}_{panel_id}_att{total_attempt_number}"
                att_start_iso = datetime.now(timezone.utc).isoformat()
                att_start_t = datetime.now(timezone.utc)

                # Check budget cap before executing
                if cumulative_cost + estimated_cost_per_op > effective_spend_cap:
                    budget_exhausted = True
                    att_end_iso = datetime.now(timezone.utc).isoformat()
                    attempt_rec = GenerationAttemptRecord(
                        batch_id=batch_id,
                        panel_id=panel_id,
                        scene_id=scene.scene_id,
                        attempt_id=attempt_id,
                        attempt_number=total_attempt_number,
                        retry_count=retry_count,
                        is_simulated=is_simulated,
                        started_at=att_start_iso,
                        completed_at=att_end_iso,
                        duration_seconds=0.0,
                        story_bible_version=bible_version_str,
                        context_fingerprint=packet.context_fingerprint,
                        reference_asset_ids=[r.asset_id for r in packet.reference_assets],
                        reference_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                        model=batch_spec.model,
                        endpoint="POST /v1/images/edits" if ref_bytes else "POST /v1/images/generations",
                        sanitized_request_metadata={"error": "Spend cap exceeded"},
                        http_status=None,
                        error_category=ErrorCategory.BUDGET_EXCEEDED.value,
                        error_message=f"Effective spend cap of ${effective_spend_cap:.2f} reached.",
                        retry_decision=RetryDecision.BUDGET_EXHAUSTED.value,
                        retry_reason="Cumulative spend cap reached; aborting further attempts.",
                        final_panel_status=PanelStatus.FAILED.value,
                    )
                    all_attempts.append(attempt_rec)
                    break

                # Execution Manager attempt dispatch check
                if self.execution_manager is not None:
                    op_id = f"{batch_id}_{panel_id}"
                    manager_attempt, _ = self.execution_manager.start_attempt(
                        run_id=batch_id,
                        operation_id=op_id,
                        engine_id="image_generation",
                        engine_version="1.0.0",
                        model=batch_spec.model,
                        provider="meta",
                        estimated_cost_usd=estimated_cost_per_op,
                        cost_classification=CostClassification.ESTIMATED,
                        input_asset_ids=[r.asset_id for r in packet.reference_assets],
                        input_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                    )
                    self._execution_attempt_ids[attempt_id] = manager_attempt.attempt_id

                # Dispatch generation request
                gen_req = GenerationRequest(
                    prompt=packet.generation_prompt,
                    reference_bytes=ref_bytes,
                    reference_mime=packet.reference_assets[0].mime_type if packet.reference_assets else "image/png",
                    model=batch_spec.model,
                    panel_id=panel_id,
                    scene_id=scene.scene_id,
                    dimensions=packet.dimensions,
                    aspect_ratio=packet.aspect_ratio,
                )

                resp: GenerationResponse = self.adapter.generate(gen_req)
                att_end_iso = datetime.now(timezone.utc).isoformat()
                att_duration = resp.duration_seconds or round((datetime.now(timezone.utc) - att_start_t).total_seconds(), 3)

                # Track usage and cost accurately
                if resp.cost_usd is not None:
                    cumulative_cost += resp.cost_usd
                else:
                    missing_cost = True
                    cumulative_cost += estimated_cost_per_op

                if resp.usage is not None:
                    for k, v in resp.usage.items():
                        if isinstance(v, (int, float)):
                            accumulated_usage[k] = accumulated_usage.get(k, 0) + v
                else:
                    missing_usage = True

                # Evaluate response outcome
                if resp.success and resp.image_bytes:
                    output_hash = self._compute_sha256(resp.image_bytes)
                    output_path_str: Optional[str] = None

                    if output_dir_path:
                        out_file = output_dir_path / f"{panel_id}.png"
                        out_file.write_bytes(resp.image_bytes)
                        output_path_str = str(out_file)

                        # Asset Registry integration: register output panel with lineage DAG
                        if self.asset_registry is not None:
                            try:
                                parent_ids = [r.asset_id for r in packet.reference_assets if r.asset_id]
                                self.asset_registry.register_file(
                                    file_path=out_file,
                                    asset_id=f"asset_{panel_id}",
                                    project_id=batch_spec.project_id,
                                    artifact_type="panel_image",
                                    mime_type="image/png",
                                    parent_asset_ids=parent_ids,
                                    source_run_id=batch_id,
                                    source_operation_id=f"{batch_id}_{panel_id}",
                                    source_attempt_id=attempt_id,
                                )
                            except Exception:
                                pass

                    # Visual verification gate
                    v_result: Optional[VerificationResult] = None
                    v_status: str = "UNVERIFIED"
                    accepted_by_gate = False
                    current_panel_status = PanelStatus.ACCEPTED

                    if self.verifier is not None:
                        primary_char = packet.character_specs[0] if packet.character_specs else None
                        primary_ref = packet.reference_assets[0] if packet.reference_assets else None
                        try:
                            v_result = self.verifier(primary_ref, resp.image_bytes, primary_char)
                        except Exception:
                            v_result = None

                        if v_result and v_result.passed:
                            v_status = "PASSED"
                            accepted_by_gate = True
                            current_panel_status = PanelStatus.ACCEPTED
                        elif v_result:
                            has_unsure = any(v.verdict == "unsure" for v in v_result.verdicts)
                            v_status = "UNSURE" if has_unsure else "FAILED"
                            accepted_by_gate = False
                            current_panel_status = PanelStatus.REJECTED_BY_VERIFIER
                        else:
                            v_status = "UNVERIFIED"
                            accepted_by_gate = not batch_spec.require_verification
                            current_panel_status = PanelStatus.ACCEPTED if accepted_by_gate else PanelStatus.GENERATED_PENDING_VERIFICATION
                    else:
                        # Verifier not attached
                        v_status = "UNVERIFIED"
                        if batch_spec.require_verification:
                            accepted_by_gate = False
                            current_panel_status = PanelStatus.GENERATED_PENDING_VERIFICATION
                        else:
                            accepted_by_gate = True
                            current_panel_status = PanelStatus.ACCEPTED

                    # Handle verification pass or failure
                    if accepted_by_gate:
                        attempt_rec = GenerationAttemptRecord(
                            batch_id=batch_id,
                            panel_id=panel_id,
                            scene_id=scene.scene_id,
                            attempt_id=attempt_id,
                            attempt_number=total_attempt_number,
                            retry_count=retry_count,
                            is_simulated=is_simulated,
                            started_at=att_start_iso,
                            completed_at=att_end_iso,
                            duration_seconds=att_duration,
                            story_bible_version=bible_version_str,
                            context_fingerprint=packet.context_fingerprint,
                            reference_asset_ids=[r.asset_id for r in packet.reference_assets],
                            reference_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                            model=batch_spec.model,
                            endpoint=resp.endpoint,
                            sanitized_request_metadata=self._build_attempt_metadata(packet, resp),
                            http_status=resp.http_status,
                            error_category=None,
                            error_message=None,
                            retry_decision=RetryDecision.NONE_SUCCESS.value,
                            retry_reason=None,
                            usage=resp.usage,
                            cost_usd=resp.cost_usd,
                            output_asset_path=output_path_str,
                            output_asset_id=f"asset_{panel_id}",
                            output_content_hash=output_hash,
                            verification_status=v_status,
                            verification_result=v_result,
                            final_panel_status=current_panel_status.value,
                        )
                        all_attempts.append(attempt_rec)
                        self._record_execution_manager_attempt(
                            batch_id=batch_id,
                            panel_id=panel_id,
                            attempt_id=attempt_id,
                            resp=resp,
                            v_status=v_status,
                            v_result=v_result,
                            output_path_str=output_path_str,
                            output_content_hash=output_hash,
                            eligible_for_acceptance=True,
                        )
                        accepted_verif_status = v_status
                        accepted_verif_result = v_result

                        panel_accepted = True
                        panel_status = current_panel_status
                        accepted_attempt_id = attempt_id
                        accepted_output_path = output_path_str
                        accepted_output_hash = output_hash
                        accepted_verif_result = v_result
                        accepted_verif_status = v_status
                        break  # Accepted: terminate retry loop

                    elif batch_spec.require_verification and self.verifier is None:
                        # Generation succeeded but verification is required and unexecuted
                        attempt_rec = GenerationAttemptRecord(
                            batch_id=batch_id,
                            panel_id=panel_id,
                            scene_id=scene.scene_id,
                            attempt_id=attempt_id,
                            attempt_number=total_attempt_number,
                            retry_count=retry_count,
                            is_simulated=is_simulated,
                            started_at=att_start_iso,
                            completed_at=att_end_iso,
                            duration_seconds=att_duration,
                            story_bible_version=bible_version_str,
                            context_fingerprint=packet.context_fingerprint,
                            reference_asset_ids=[r.asset_id for r in packet.reference_assets],
                            reference_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                            model=batch_spec.model,
                            endpoint=resp.endpoint,
                            sanitized_request_metadata=self._build_attempt_metadata(packet, resp),
                            http_status=resp.http_status,
                            error_category=None,
                            error_message=None,
                            retry_decision=RetryDecision.NONE_SUCCESS.value,
                            retry_reason="Generated successfully; awaiting verification gate.",
                            usage=resp.usage,
                            cost_usd=resp.cost_usd,
                            output_asset_path=output_path_str,
                            output_asset_id=f"asset_{panel_id}",
                            output_content_hash=output_hash,
                            verification_status=v_status,
                            verification_result=None,
                            final_panel_status=PanelStatus.GENERATED_PENDING_VERIFICATION.value,
                        )
                        all_attempts.append(attempt_rec)
                        self._record_execution_manager_attempt(
                            batch_id=batch_id,
                            panel_id=panel_id,
                            attempt_id=attempt_id,
                            resp=resp,
                            v_status=v_status,
                            v_result=None,
                            output_path_str=output_path_str,
                            output_content_hash=output_hash,
                            eligible_for_acceptance=True,
                        )
                        accepted_verif_status = v_status
                        accepted_verif_result = v_result

                        panel_accepted = False
                        panel_status = PanelStatus.GENERATED_PENDING_VERIFICATION
                        accepted_attempt_id = attempt_id
                        accepted_output_path = output_path_str
                        accepted_output_hash = output_hash
                        accepted_verif_status = v_status
                        break

                    else:
                        # Verifier explicitly rejected candidate
                        if attempt_idx < max_attempts and v_status == "FAILED":
                            retry_dec = RetryDecision.RETRY_WITH_CORRECTION.value
                            retry_re = f"Visual verifier rejected candidate: {v_result.rejection_reason if v_result else 'Attribute check failed'}"
                            fin_status = PanelStatus.PENDING.value
                        else:
                            retry_dec = RetryDecision.MAX_RETRIES_REACHED.value
                            retry_re = f"Verification unresolved after attempt {attempt_idx}: {v_result.rejection_reason if v_result else 'Attribute check failed'}"
                            fin_status = PanelStatus.NEEDS_HUMAN.value

                        attempt_rec = GenerationAttemptRecord(
                            batch_id=batch_id,
                            panel_id=panel_id,
                            scene_id=scene.scene_id,
                            attempt_id=attempt_id,
                            attempt_number=total_attempt_number,
                            retry_count=retry_count,
                            is_simulated=is_simulated,
                            started_at=att_start_iso,
                            completed_at=att_end_iso,
                            duration_seconds=att_duration,
                            story_bible_version=bible_version_str,
                            context_fingerprint=packet.context_fingerprint,
                            reference_asset_ids=[r.asset_id for r in packet.reference_assets],
                            reference_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                            model=batch_spec.model,
                            endpoint=resp.endpoint,
                            sanitized_request_metadata=self._build_attempt_metadata(packet, resp),
                            http_status=resp.http_status,
                            error_category=ErrorCategory.UNKNOWN.value,
                            error_message=f"Verification rejection: {v_result.rejection_reason if v_result else 'Failed'}",
                            retry_decision=retry_dec,
                            retry_reason=retry_re,
                            usage=resp.usage,
                            cost_usd=resp.cost_usd,
                            output_asset_path=output_path_str,
                            output_asset_id=f"asset_{panel_id}",
                            output_content_hash=output_hash,
                            verification_status=v_status,
                            verification_result=v_result,
                            final_panel_status=fin_status,
                        )
                        all_attempts.append(attempt_rec)
                        self._record_execution_manager_attempt(
                            batch_id=batch_id,
                            panel_id=panel_id,
                            attempt_id=attempt_id,
                            resp=resp,
                            v_status=v_status,
                            v_result=v_result,
                            output_path_str=output_path_str,
                            output_content_hash=output_hash,
                            retryable=(v_status == "FAILED" and attempt_idx < max_attempts),
                            error_category=ExecutionErrorCategory.UNKNOWN,
                            error_message=f"Verification rejection: {v_result.rejection_reason if v_result else 'Failed'}",
                        )
                        accepted_verif_status = v_status
                        accepted_verif_result = v_result

                        if attempt_idx >= max_attempts or v_status == "UNSURE":
                            panel_status = PanelStatus.NEEDS_HUMAN
                            break
                        continue

                # Handle generation failure
                is_retryable = self._is_retryable_error(resp.error_category)
                if not is_retryable:
                    retry_decision = RetryDecision.DO_NOT_RETRY_PERMANENT.value
                    retry_reason = f"Non-retryable failure ({resp.error_category}): {resp.error_message}"
                    final_panel_status = PanelStatus.FAILED.value
                elif attempt_idx < max_attempts:
                    retry_decision = RetryDecision.RETRY_WITH_CORRECTION.value
                    retry_reason = f"Retryable error {resp.error_category}; scheduling attempt {attempt_idx + 1}/{max_attempts}"
                    final_panel_status = PanelStatus.PENDING.value
                else:
                    retry_decision = RetryDecision.MAX_RETRIES_REACHED.value
                    retry_reason = f"Attempt limit reached ({max_attempts} attempts exhausted)."
                    final_panel_status = PanelStatus.NEEDS_HUMAN.value

                attempt_rec = GenerationAttemptRecord(
                    batch_id=batch_id,
                    panel_id=panel_id,
                    scene_id=scene.scene_id,
                    attempt_id=attempt_id,
                    attempt_number=total_attempt_number,
                    retry_count=retry_count,
                    is_simulated=is_simulated,
                    started_at=att_start_iso,
                    completed_at=att_end_iso,
                    duration_seconds=att_duration,
                    story_bible_version=bible_version_str,
                    context_fingerprint=packet.context_fingerprint,
                    reference_asset_ids=[r.asset_id for r in packet.reference_assets],
                    reference_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                    model=batch_spec.model,
                    endpoint=resp.endpoint,
                    sanitized_request_metadata=self._build_attempt_metadata(packet, resp),
                    http_status=resp.http_status,
                    error_category=resp.error_category.value if resp.error_category else ErrorCategory.UNKNOWN.value,
                    error_message=resp.error_message,
                    retry_decision=retry_decision,
                    retry_reason=retry_reason,
                    usage=resp.usage,
                    cost_usd=resp.cost_usd,
                    output_asset_path=None,
                    output_asset_id=None,
                    output_content_hash=None,
                    final_panel_status=final_panel_status,
                )
                all_attempts.append(attempt_rec)
                self._record_execution_manager_attempt(
                    batch_id=batch_id,
                    panel_id=panel_id,
                    attempt_id=attempt_id,
                    resp=resp,
                    v_status="FAILED",
                    v_result=None,
                    output_path_str=None,
                    retryable=is_retryable and attempt_idx < max_attempts,
                    error_category=(
                        ExecutionErrorCategory(resp.error_category.value)
                        if resp.error_category and resp.error_category.value in {item.value for item in ExecutionErrorCategory}
                        else ExecutionErrorCategory.UNKNOWN
                    ),
                    error_message=resp.error_message,
                )

                if not is_retryable:
                    break  # Do not retry permanent errors

            # Final status for this panel
            if panel_accepted:
                p_status = panel_status
            elif panel_status in (PanelStatus.GENERATED_PENDING_VERIFICATION, PanelStatus.NEEDS_HUMAN, PanelStatus.REJECTED_BY_VERIFIER):
                p_status = panel_status
            elif budget_exhausted:
                p_status = PanelStatus.FAILED
            elif panel_attempts_count >= max_attempts:
                p_status = PanelStatus.NEEDS_HUMAN
            else:
                p_status = panel_status if panel_status != PanelStatus.PENDING else PanelStatus.FAILED

            panel_result = PanelResult(
                panel_id=panel_id,
                scene_id=scene.scene_id,
                scene_index=scene.scene_index,
                status=p_status,
                attempts_count=panel_attempts_count + prior_offset,
                accepted_attempt_id=accepted_attempt_id,
                output_asset_path=accepted_output_path,
                output_content_hash=accepted_output_hash,
                context_fingerprint=packet.context_fingerprint,
                verification_status=accepted_verif_status,
                verification_result=accepted_verif_result,
            )
            panel_results.append(panel_result)

            # Incremental checkpoint persistence to protect audit history against crashes
            self._persist_checkpoint(batch_id, batch_spec, sorted_scenes, panel_results, all_attempts, start_time_iso, bible_version_str, is_simulated)

            if budget_exhausted:
                # Fill remaining panels as failed due to budget
                cur_idx = sorted_scenes.index(scene)
                for rem_scene in sorted_scenes[cur_idx + 1:]:
                    rem_panel_id = f"panel_{rem_scene.scene_index + 1:02d}"
                    rem_packet = build_panel_context_packet(
                        story_bible=batch_spec.story_bible,
                        scene=rem_scene,
                        panel_id=rem_panel_id,
                        story_id=batch_spec.story_id,
                        project_id=batch_spec.project_id,
                        model=batch_spec.model,
                    )
                    panel_results.append(PanelResult(
                        panel_id=rem_panel_id,
                        scene_id=rem_scene.scene_id,
                        scene_index=rem_scene.scene_index,
                        status=PanelStatus.FAILED,
                        attempts_count=0,
                        context_fingerprint=rem_packet.context_fingerprint,
                    ))
                break

        # 5. Calculate batch completion metrics
        total_panels = len(sorted_scenes)
        generated_panels = sum(1 for p in panel_results if p.output_asset_path is not None)
        verified_panels = sum(1 for p in panel_results if p.verification_status == "PASSED")
        successful_panels = sum(1 for p in panel_results if p.status == PanelStatus.ACCEPTED)
        unverified_panels = sum(1 for p in panel_results if (p.output_asset_path is not None and p.verification_status != "PASSED") or p.status == PanelStatus.GENERATED_PENDING_VERIFICATION)
        failed_panels = sum(1 for p in panel_results if p.status in (PanelStatus.FAILED, PanelStatus.REJECTED_BY_VERIFIER))
        unresolved_panels = sum(1 for p in panel_results if p.status in (PanelStatus.PENDING, PanelStatus.NEEDS_HUMAN, PanelStatus.GENERATED_PENDING_VERIFICATION))

        if successful_panels == total_panels:
            batch_status = BatchStatus.COMPLETED
        elif successful_panels > 0 or unverified_panels > 0:
            batch_status = BatchStatus.COMPLETED_WITH_FAILURES
        else:
            batch_status = BatchStatus.FAILED

        attempts_per_panel = {p.panel_id: p.attempts_count for p in panel_results}
        end_time_iso = datetime.now(timezone.utc).isoformat()
        total_duration = round((datetime.now(timezone.utc) - start_t).total_seconds(), 3)

        # Segregate simulated from live provider accounting
        if is_simulated:
            cost_mode_str = "synthetic_simulated"
            known_cost_report = 0.0 if not missing_cost else None  # Zero real provider dollars spent in simulation
            known_usage_report = {} if not missing_usage else {}  # Zero real provider tokens consumed in simulation
            simulated_cost_report = round(cumulative_cost, 4) if not missing_cost else None
            simulated_usage_report = accumulated_usage if not missing_usage else None
            missing_cost_flag = missing_cost
            missing_usage_flag = missing_usage
        else:
            cost_mode_str = "real"
            known_cost_report = round(cumulative_cost, 4) if not missing_cost else None
            known_usage_report = accumulated_usage if not missing_usage else {}
            simulated_cost_report = None
            simulated_usage_report = None
            missing_cost_flag = missing_cost
            missing_usage_flag = missing_usage

        summary = BatchSummary(
            batch_id=batch_id,
            status=batch_status,
            project_id=batch_spec.project_id,
            story_id=batch_spec.story_id,
            bible_version=bible_version_str,
            total_panels=total_panels,
            successful_panels=successful_panels,
            generated_panels=generated_panels,
            verified_panels=verified_panels,
            failed_panels=failed_panels,
            unresolved_panels=unresolved_panels,
            unverified_panels=unverified_panels,
            total_attempts=len(all_attempts),
            attempts_per_panel=attempts_per_panel,
            total_duration_seconds=total_duration,
            started_at=start_time_iso,
            completed_at=end_time_iso,
            is_simulated=is_simulated,
            cost_mode=cost_mode_str,
            known_cost_usd=known_cost_report,
            simulated_cost_usd=simulated_cost_report,
            missing_cost_information=missing_cost_flag,
            known_usage=known_usage_report,
            simulated_usage=simulated_usage_report,
            missing_usage_information=missing_usage_flag,
            panel_results=panel_results,
            attempt_history=all_attempts,
            source_scenes=batch_spec.scenes,
            model=batch_spec.model,
            max_retries_per_panel=batch_spec.max_retries_per_panel,
            spend_cap_usd=batch_spec.spend_cap_usd,
            require_verification=batch_spec.require_verification,
            request_fingerprint=batch_spec.request_fingerprint,
        )

        # 6. Structured Persistence
        self._persist_batch_summary(summary)

        # Execution Manager run lifecycle completion
        if self.execution_manager is not None:
            if budget_exhausted:
                self.execution_manager.cancel_run(batch_id, reason="orchestrator_budget_exceeded")
            else:
                self.execution_manager.complete_run(batch_id)

        return summary

    def _persist_checkpoint(
        self,
        batch_id: str,
        batch_spec: BatchSpec,
        sorted_scenes: List[SceneSpec],
        panel_results: List[PanelResult],
        all_attempts: List[GenerationAttemptRecord],
        start_time_iso: str,
        bible_version_str: str,
        is_simulated: bool
    ):
        """Persists intermediate progress to disk so interrupted runs are durable."""
        temp_summary = BatchSummary(
            batch_id=batch_id,
            status=BatchStatus.RUNNING,
            project_id=batch_spec.project_id,
            story_id=batch_spec.story_id,
            bible_version=bible_version_str,
            total_panels=len(sorted_scenes),
            successful_panels=sum(1 for p in panel_results if p.status == PanelStatus.ACCEPTED),
            failed_panels=sum(1 for p in panel_results if p.status in (PanelStatus.FAILED, PanelStatus.REJECTED_BY_VERIFIER)),
            unresolved_panels=sum(1 for p in panel_results if p.status != PanelStatus.ACCEPTED),
            unverified_panels=sum(1 for p in panel_results if p.status == PanelStatus.GENERATED_PENDING_VERIFICATION),
            total_attempts=len(all_attempts),
            attempts_per_panel={p.panel_id: p.attempts_count for p in panel_results},
            total_duration_seconds=0.0,
            started_at=start_time_iso,
            completed_at=None,
            is_simulated=is_simulated,
            cost_mode="synthetic_simulated" if is_simulated else "real",
            panel_results=panel_results,
            attempt_history=all_attempts,
            source_scenes=batch_spec.scenes,
            model=batch_spec.model,
            max_retries_per_panel=batch_spec.max_retries_per_panel,
            spend_cap_usd=batch_spec.spend_cap_usd,
            require_verification=batch_spec.require_verification,
            request_fingerprint=batch_spec.request_fingerprint,
        )
        self._persist_batch_summary(temp_summary)

    def _persist_batch_summary(self, summary: BatchSummary) -> Path:
        """Persists structured machine-readable batch summary to runs store."""
        summary_file = self.run_log_dir / f"{summary.batch_id}.json"
        summary_json = summary.model_dump_json(indent=2)
        summary_file.write_text(summary_json, encoding="utf-8")
        return summary_file

    def resume_batch(
        self,
        batch_spec: BatchSpec,
        prior_summary: Optional[BatchSummary] = None
    ) -> BatchSummary:
        """
        Resumes a partial or failed batch without regenerating previously accepted panels.
        Validates context fingerprints to ensure inputs have not drifted before reusing results.
        Validates that referenced asset files physically exist on disk before reuse.
        Ensures resumed attempt numbering continues seamlessly without ID collisions.
        """
        if prior_summary is None:
            if not self.run_log_dir:
                raise ValueError("Cannot auto-load prior summary: run_log_dir is not configured.")
            summary_path = self.run_log_dir / f"{batch_spec.batch_id}.json"
            if not summary_path.is_file():
                raise FileNotFoundError(f"Prior batch summary not found at '{summary_path}' to resume.")
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            prior_summary = BatchSummary.model_validate(data)

        sorted_scenes = sorted(batch_spec.scenes, key=lambda s: s.scene_index)
        bible_version_str = str(getattr(batch_spec.story_bible, "bible_version", getattr(batch_spec.story_bible, "version", "1.0.0")))
        prior_panels_by_id = {p.panel_id: p for p in prior_summary.panel_results}
        prior_attempts_by_panel: Dict[str, List[GenerationAttemptRecord]] = {}
        for att in prior_summary.attempt_history:
            prior_attempts_by_panel.setdefault(att.panel_id, []).append(att)

        scenes_to_run: List[SceneSpec] = []
        reused_panel_results: Dict[str, PanelResult] = {}
        reused_attempts: List[GenerationAttemptRecord] = []
        prior_attempt_offsets: Dict[str, int] = {}

        for scene in sorted_scenes:
            panel_id = f"panel_{scene.scene_index + 1:02d}"
            cur_packet = build_panel_context_packet(
                story_bible=batch_spec.story_bible,
                scene=scene,
                panel_id=panel_id,
                story_id=batch_spec.story_id,
                project_id=batch_spec.project_id,
                model=batch_spec.model,
            )

            prior_panel = prior_panels_by_id.get(panel_id)

            # Check that output asset file physically exists on disk and satisfies integrity checks before deciding to reuse
            file_valid = True
            if prior_panel and prior_panel.output_asset_path:
                p_file = Path(prior_panel.output_asset_path)
                if not p_file.is_absolute():
                    p_file = PROJECT_ROOT / p_file
                if p_file.exists() and p_file.is_file() and p_file.stat().st_size > 0:
                    if prior_panel.output_content_hash:
                        try:
                            disk_hash = hashlib.sha256(p_file.read_bytes()).hexdigest()
                            file_valid = (disk_hash == prior_panel.output_content_hash)
                        except Exception:
                            file_valid = False
                    else:
                        file_valid = True
                else:
                    file_valid = False

            # Reusable if: was ACCEPTED, context fingerprint matches, and output file is verified intact
            if (
                prior_panel
                and prior_panel.status == PanelStatus.ACCEPTED
                and prior_panel.context_fingerprint == cur_packet.context_fingerprint
                and file_valid
            ):
                reused_panel_results[panel_id] = prior_panel
                reused_attempts.extend(prior_attempts_by_panel.get(panel_id, []))
            else:
                scenes_to_run.append(scene)
                # Track prior attempts count so resumed attempt IDs continue without collision
                prior_attempt_offsets[panel_id] = len(prior_attempts_by_panel.get(panel_id, []))
                # Preserve prior attempts for audit provenance
                reused_attempts.extend(prior_attempts_by_panel.get(panel_id, []))

        # If everything is already accepted and unchanged, return existing summary
        if not scenes_to_run:
            return prior_summary

        # Create a sub-batch spec for remaining scenes
        sub_spec = BatchSpec(
            batch_id=batch_spec.batch_id,
            project_id=batch_spec.project_id,
            story_id=batch_spec.story_id,
            story_bible=batch_spec.story_bible,
            scenes=scenes_to_run,
            model=batch_spec.model,
            max_retries_per_panel=batch_spec.max_retries_per_panel,
            spend_cap_usd=batch_spec.spend_cap_usd,
            output_dir=batch_spec.output_dir,
            require_verification=batch_spec.require_verification,
            request_fingerprint=prior_summary.request_fingerprint,
        )

        sub_summary = self.orchestrate_batch(sub_spec, prior_attempt_offsets=prior_attempt_offsets)

        # Merge reused panel results with freshly generated panel results
        fresh_panels_by_id = {p.panel_id: p for p in sub_summary.panel_results}
        combined_panel_results: List[PanelResult] = []
        for scene in sorted_scenes:
            panel_id = f"panel_{scene.scene_index + 1:02d}"
            if panel_id in reused_panel_results:
                combined_panel_results.append(reused_panel_results[panel_id])
            elif panel_id in fresh_panels_by_id:
                combined_panel_results.append(fresh_panels_by_id[panel_id])

        combined_attempts = reused_attempts + sub_summary.attempt_history

        total_panels = len(sorted_scenes)
        generated_panels = sum(1 for p in combined_panel_results if p.output_asset_path is not None)
        verified_panels = sum(1 for p in combined_panel_results if p.verification_status == "PASSED")
        successful_panels = sum(1 for p in combined_panel_results if p.status == PanelStatus.ACCEPTED)
        unverified_panels = sum(1 for p in combined_panel_results if p.verification_status in ("UNVERIFIED", "PENDING") or p.status == PanelStatus.GENERATED_PENDING_VERIFICATION)
        failed_panels = sum(1 for p in combined_panel_results if p.status in (PanelStatus.FAILED, PanelStatus.REJECTED_BY_VERIFIER))
        unresolved_panels = sum(1 for p in combined_panel_results if p.status in (PanelStatus.PENDING, PanelStatus.NEEDS_HUMAN, PanelStatus.GENERATED_PENDING_VERIFICATION))

        if successful_panels == total_panels:
            b_status = BatchStatus.COMPLETED
        elif successful_panels > 0 or unverified_panels > 0:
            b_status = BatchStatus.COMPLETED_WITH_FAILURES
        else:
            b_status = BatchStatus.FAILED

        merged_summary = BatchSummary(
            batch_id=batch_spec.batch_id,
            status=b_status,
            project_id=batch_spec.project_id,
            story_id=batch_spec.story_id,
            bible_version=bible_version_str,
            total_panels=total_panels,
            successful_panels=successful_panels,
            generated_panels=generated_panels,
            verified_panels=verified_panels,
            failed_panels=failed_panels,
            unresolved_panels=unresolved_panels,
            unverified_panels=unverified_panels,
            total_attempts=len(combined_attempts),
            attempts_per_panel={p.panel_id: p.attempts_count for p in combined_panel_results},
            total_duration_seconds=round(prior_summary.total_duration_seconds + sub_summary.total_duration_seconds, 3),
            started_at=prior_summary.started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            is_simulated=sub_summary.is_simulated,
            cost_mode=sub_summary.cost_mode,
            known_cost_usd=None if (prior_summary.missing_cost_information or sub_summary.missing_cost_information) else round((prior_summary.known_cost_usd or 0) + (sub_summary.known_cost_usd or 0), 4),
            simulated_cost_usd=round((prior_summary.simulated_cost_usd or 0) + (sub_summary.simulated_cost_usd or 0), 4) if sub_summary.simulated_cost_usd is not None else None,
            missing_cost_information=prior_summary.missing_cost_information or sub_summary.missing_cost_information,
            known_usage={**prior_summary.known_usage, **sub_summary.known_usage},
            simulated_usage={**(prior_summary.simulated_usage or {}), **(sub_summary.simulated_usage or {})},
            missing_usage_information=prior_summary.missing_usage_information or sub_summary.missing_usage_information,
            panel_results=combined_panel_results,
            attempt_history=combined_attempts,
            source_scenes=batch_spec.scenes,
            model=batch_spec.model,
            max_retries_per_panel=batch_spec.max_retries_per_panel,
            spend_cap_usd=batch_spec.spend_cap_usd,
            require_verification=batch_spec.require_verification,
            request_fingerprint=prior_summary.request_fingerprint,
        )

        self._persist_batch_summary(merged_summary)
        return merged_summary
