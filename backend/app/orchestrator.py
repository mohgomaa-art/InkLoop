"""
Six-Panel Batch Generation Orchestrator for InkLoop.
Coordinates multi-panel generation with independent context isolation,
bounded retries, spend cap enforcement, and complete auditable attempt logging.
"""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.config import InkLoopConfig, PROJECT_ROOT
from app.schemas import (
    BatchSpec,
    BatchSummary,
    BatchStatus,
    SceneSpec,
    PanelResult,
    PanelStatus,
    GenerationAttemptRecord,
    ErrorCategory,
    RetryDecision,
    ReferenceAsset,
)
from app.context_builder import build_panel_context_packet
from app.image_adapter import (
    ImageGenerationAdapter,
    GenerationRequest,
    GenerationResponse,
)

class BatchOrchestrator:
    """
    Core backend service for orchestrating multi-panel comic generation batches.
    Guarantees:
    - Pure-code independent context assembly per panel (no cross-panel conversational drift).
    - Bounded retries respecting per-panel retry ceilings and global spend caps.
    - Zero credential leakage in attempts, logs, or persistent records.
    - Full reproducibility and resumability without redundant re-generation.
    """

    def __init__(
        self,
        config: InkLoopConfig,
        adapter: ImageGenerationAdapter,
        run_log_dir: Optional[Path] = None,
    ):
        self.config = config
        self.adapter = adapter
        self.run_log_dir = run_log_dir or (PROJECT_ROOT / "runs" / "batches")
        self.run_log_dir.mkdir(parents=True, exist_ok=True)

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

    def orchestrate_batch(self, batch_spec: BatchSpec) -> BatchSummary:
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

        max_retries = min(batch_spec.max_retries_per_panel, self.config.max_retries_per_panel)
        max_attempts = 1 + max_retries

        # Estimate per-operation cost for budget enforcement ($0.01 per image baseline)
        estimated_cost_per_op = 0.01

        for scene in sorted_scenes:
            panel_id = f"panel_{scene.scene_index + 1:02d}"

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
            panel_attempts_count = 0
            accepted_attempt_id: Optional[str] = None
            accepted_output_path: Optional[str] = None
            accepted_output_hash: Optional[str] = None

            # 4. Bounded retry loop for this panel
            for attempt_idx in range(1, max_attempts + 1):
                panel_attempts_count += 1
                attempt_id = f"{batch_id}_{panel_id}_att{attempt_idx}"
                att_start_iso = datetime.now(timezone.utc).isoformat()
                att_start_t = datetime.now(timezone.utc)

                # Check budget cap before executing
                if cumulative_cost + estimated_cost_per_op > batch_spec.spend_cap_usd:
                    budget_exhausted = True
                    att_end_iso = datetime.now(timezone.utc).isoformat()
                    attempt_rec = GenerationAttemptRecord(
                        batch_id=batch_id,
                        panel_id=panel_id,
                        scene_id=scene.scene_id,
                        attempt_id=attempt_id,
                        attempt_number=attempt_idx,
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
                        error_message=f"Global spend cap of ${batch_spec.spend_cap_usd:.2f} reached.",
                        retry_decision=RetryDecision.BUDGET_EXHAUSTED.value,
                        retry_reason="Cumulative spend cap reached; aborting further attempts.",
                        final_panel_status=PanelStatus.FAILED.value,
                    )
                    all_attempts.append(attempt_rec)
                    break

                # Dispatch generation request
                gen_req = GenerationRequest(
                    prompt=packet.generation_prompt,
                    reference_bytes=ref_bytes,
                    reference_mime=packet.reference_assets[0].mime_type if packet.reference_assets else "image/png",
                    model=batch_spec.model,
                    panel_id=panel_id,
                    scene_id=scene.scene_id,
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

                if resp.usage:
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

                    attempt_rec = GenerationAttemptRecord(
                        batch_id=batch_id,
                        panel_id=panel_id,
                        scene_id=scene.scene_id,
                        attempt_id=attempt_id,
                        attempt_number=attempt_idx,
                        started_at=att_start_iso,
                        completed_at=att_end_iso,
                        duration_seconds=att_duration,
                        story_bible_version=bible_version_str,
                        context_fingerprint=packet.context_fingerprint,
                        reference_asset_ids=[r.asset_id for r in packet.reference_assets],
                        reference_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                        model=batch_spec.model,
                        endpoint=resp.endpoint,
                        sanitized_request_metadata=resp.sanitized_metadata,
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
                        verification_status="UNVERIFIED",
                        final_panel_status=PanelStatus.ACCEPTED.value,
                    )
                    all_attempts.append(attempt_rec)

                    panel_accepted = True
                    accepted_attempt_id = attempt_id
                    accepted_output_path = output_path_str
                    accepted_output_hash = output_hash
                    break  # Success: terminate retry loop for this panel

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
                    attempt_number=attempt_idx,
                    started_at=att_start_iso,
                    completed_at=att_end_iso,
                    duration_seconds=att_duration,
                    story_bible_version=bible_version_str,
                    context_fingerprint=packet.context_fingerprint,
                    reference_asset_ids=[r.asset_id for r in packet.reference_assets],
                    reference_asset_hashes={r.asset_id: r.content_hash for r in packet.reference_assets},
                    model=batch_spec.model,
                    endpoint=resp.endpoint,
                    sanitized_request_metadata=resp.sanitized_metadata,
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

                if not is_retryable:
                    break  # Do not retry permanent errors

            # Final status for this panel
            if panel_accepted:
                p_status = PanelStatus.ACCEPTED
            elif budget_exhausted:
                p_status = PanelStatus.FAILED
            elif panel_attempts_count >= max_attempts:
                p_status = PanelStatus.NEEDS_HUMAN
            else:
                p_status = PanelStatus.FAILED

            panel_result = PanelResult(
                panel_id=panel_id,
                scene_id=scene.scene_id,
                scene_index=scene.scene_index,
                status=p_status,
                attempts_count=panel_attempts_count,
                accepted_attempt_id=accepted_attempt_id,
                output_asset_path=accepted_output_path,
                output_content_hash=accepted_output_hash,
                context_fingerprint=packet.context_fingerprint,
            )
            panel_results.append(panel_result)

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
        successful_panels = sum(1 for p in panel_results if p.status == PanelStatus.ACCEPTED)
        failed_panels = sum(1 for p in panel_results if p.status == PanelStatus.FAILED)
        unresolved_panels = sum(1 for p in panel_results if p.status in (PanelStatus.PENDING, PanelStatus.NEEDS_HUMAN))

        if successful_panels == total_panels:
            batch_status = BatchStatus.COMPLETED
        elif successful_panels > 0:
            batch_status = BatchStatus.COMPLETED_WITH_FAILURES
        else:
            batch_status = BatchStatus.FAILED

        attempts_per_panel = {p.panel_id: p.attempts_count for p in panel_results}
        end_time_iso = datetime.now(timezone.utc).isoformat()
        total_duration = round((datetime.now(timezone.utc) - start_t).total_seconds(), 3)

        summary = BatchSummary(
            batch_id=batch_id,
            status=batch_status,
            story_id=batch_spec.story_id,
            bible_version=bible_version_str,
            total_panels=total_panels,
            successful_panels=successful_panels,
            failed_panels=failed_panels,
            unresolved_panels=unresolved_panels,
            total_attempts=len(all_attempts),
            attempts_per_panel=attempts_per_panel,
            total_duration_seconds=total_duration,
            started_at=start_time_iso,
            completed_at=end_time_iso,
            known_cost_usd=round(cumulative_cost, 4) if not missing_cost else None,
            missing_cost_information=missing_cost,
            known_usage=accumulated_usage,
            missing_usage_information=missing_usage,
            panel_results=panel_results,
            attempt_history=all_attempts,
        )

        # 6. Structured Persistence
        self._persist_batch_summary(summary)
        return summary

    def _persist_batch_summary(self, summary: BatchSummary) -> Path:
        """Persists structured machine-readable batch summary to runs store."""
        summary_file = self.run_log_dir / f"{summary.batch_id}.json"
        summary_json = summary.model_dump_json(indent=2)
        summary_file.write_text(summary_json, encoding="utf-8")
        return summary_file

    def resume_batch(
        self,
        batch_spec: BatchSpec,
        prior_summary: BatchSummary
    ) -> BatchSummary:
        """
        Resumes a partial or failed batch without regenerating previously accepted panels.
        Validates context fingerprints to ensure inputs have not drifted before reusing results.
        """
        sorted_scenes = sorted(batch_spec.scenes, key=lambda s: s.scene_index)
        bible_version_str = str(getattr(batch_spec.story_bible, "bible_version", getattr(batch_spec.story_bible, "version", "1.0.0")))
        prior_panels_by_id = {p.panel_id: p for p in prior_summary.panel_results}
        prior_attempts_by_panel: Dict[str, List[GenerationAttemptRecord]] = {}
        for att in prior_summary.attempt_history:
            prior_attempts_by_panel.setdefault(att.panel_id, []).append(att)

        scenes_to_run: List[SceneSpec] = []
        reused_panel_results: Dict[str, PanelResult] = {}
        reused_attempts: List[GenerationAttemptRecord] = []

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
            # Reusable if: was ACCEPTED, and context fingerprint exactly matches current inputs
            if (
                prior_panel
                and prior_panel.status == PanelStatus.ACCEPTED
                and prior_panel.context_fingerprint == cur_packet.context_fingerprint
            ):
                reused_panel_results[panel_id] = prior_panel
                reused_attempts.extend(prior_attempts_by_panel.get(panel_id, []))
            else:
                scenes_to_run.append(scene)

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
        )

        sub_summary = self.orchestrate_batch(sub_spec)

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
        successful_panels = sum(1 for p in combined_panel_results if p.status == PanelStatus.ACCEPTED)
        failed_panels = sum(1 for p in combined_panel_results if p.status == PanelStatus.FAILED)
        unresolved_panels = sum(1 for p in combined_panel_results if p.status in (PanelStatus.PENDING, PanelStatus.NEEDS_HUMAN))

        if successful_panels == total_panels:
            b_status = BatchStatus.COMPLETED
        elif successful_panels > 0:
            b_status = BatchStatus.COMPLETED_WITH_FAILURES
        else:
            b_status = BatchStatus.FAILED

        merged_summary = BatchSummary(
            batch_id=batch_spec.batch_id,
            status=b_status,
            story_id=batch_spec.story_id,
            bible_version=bible_version_str,
            total_panels=total_panels,
            successful_panels=successful_panels,
            failed_panels=failed_panels,
            unresolved_panels=unresolved_panels,
            total_attempts=len(combined_attempts),
            attempts_per_panel={p.panel_id: p.attempts_count for p in combined_panel_results},
            total_duration_seconds=round(prior_summary.total_duration_seconds + sub_summary.total_duration_seconds, 3),
            started_at=prior_summary.started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            known_cost_usd=None if (prior_summary.missing_cost_information or sub_summary.missing_cost_information) else round((prior_summary.known_cost_usd or 0) + (sub_summary.known_cost_usd or 0), 4),
            missing_cost_information=prior_summary.missing_cost_information or sub_summary.missing_cost_information,
            known_usage={**prior_summary.known_usage, **sub_summary.known_usage},
            missing_usage_information=prior_summary.missing_usage_information or sub_summary.missing_usage_information,
            panel_results=combined_panel_results,
            attempt_history=combined_attempts,
        )

        self._persist_batch_summary(merged_summary)
        return merged_summary
