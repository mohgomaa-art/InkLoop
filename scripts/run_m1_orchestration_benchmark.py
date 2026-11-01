#!/usr/bin/env python3
"""
InkLoop M1 Six-Panel Generation Orchestration Runner.
Executes the canonical six-scene benchmark batch through BatchOrchestrator.
Supports both deterministic simulated mode (default, 0 credits) and optional live API mode.
"""
import sys
import argparse
from pathlib import Path

# Resolve backend path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import InkLoopConfig
from app.orchestrator import BatchOrchestrator
from app.image_adapter import (
    SimulatedImageGenerationAdapter,
    MetaImageGenerationAdapter,
)
from tests.fixtures.benchmark_fixtures import create_m0_benchmark_batch_spec

def main():
    parser = argparse.ArgumentParser(description="InkLoop M1 Six-Panel Orchestration Benchmark Runner")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute against live Meta Model API (costs API credits; requires MODEL_API_KEY in .env)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="runs/m1_orchestrations/m0_benchmark",
        help="Output directory for generated panel images"
    )
    parser.add_argument(
        "--batch-id",
        type=str,
        default="benchmark_six_panel_m1",
        help="Batch run identifier"
    )
    parser.add_argument(
        "--require-verification",
        action="store_true",
        help="Enforce visual verification gate before accepting panels"
    )
    parser.add_argument(
        "--mock-verifier",
        action="store_true",
        help="Inject deterministic simulated mock verifier for offline pipeline testing"
    )
    args = parser.parse_args()

    config = InkLoopConfig.load()

    # Determine verifier configuration
    verifier_fn = None
    if args.mock_verifier:
        from app.verification import SimulatedVisualVerificationService
        verification_service = SimulatedVisualVerificationService(config=config)
        verifier_fn = verification_service.verify_panel
        verifier_label = "SIMULATED VISUAL VERIFICATION SERVICE (Multi-tier L0+L1+L2; Offline deterministic test; not live consistency proof)"
    elif args.require_verification and args.live and config.has_credentials:
        from app.verification import VisualVerificationService, VerificationMode
        verification_service = VisualVerificationService(config=config, mode=VerificationMode.LIVE)
        verifier_fn = verification_service.verify_panel
        verifier_label = "LIVE META VISUAL VERIFICATION SERVICE (Multi-tier L0 Code + L1 SAM + L2 Muse Spark)"
    else:
        verifier_label = "NONE (Orchestration benchmark only; visual verification unexecuted)"

    print("=================================================================")
    print("INKLOOP M1: SIX-PANEL GENERATION ORCHESTRATION BENCHMARK")
    print("=================================================================")
    print(f"Generation Mode:   {'LIVE META API' if args.live else 'DETERMINISTIC SIMULATED ADAPTER'}")
    print(f"Verification Mode: {verifier_label}")
    print(f"Model:             {config.muse_image_model}")
    print(f"Max retries:       {config.max_retries_per_panel}")
    print(f"Global spend cap:  ${config.global_spend_cap_usd:.2f}")
    print(f"Credentials:       {config.has_credentials} ({config.mask_key()})")

    if args.live:
        if not config.has_credentials:
            print("[!] ERROR: Live mode requested but MODEL_API_KEY is not configured.", file=sys.stderr)
            sys.exit(1)
        adapter = MetaImageGenerationAdapter(config=config, timeout_seconds=60.0)
    else:
        adapter = SimulatedImageGenerationAdapter(
            default_success=True,
            simulated_usage={"input_tokens": 12400, "output_tokens": 1000, "total_tokens": 13400},
            simulated_cost=0.01,
            duration_seconds=0.05
        )

    out_path = PROJECT_ROOT / args.output_dir
    log_dir = PROJECT_ROOT / "runs" / "batches"
    orchestrator = BatchOrchestrator(config=config, adapter=adapter, run_log_dir=log_dir, verifier=verifier_fn)

    batch_spec = create_m0_benchmark_batch_spec(
        batch_id=args.batch_id,
        max_retries=config.max_retries_per_panel,
        spend_cap_usd=config.global_spend_cap_usd,
        output_dir=str(out_path)
    )
    batch_spec.require_verification = args.require_verification

    print(f"\n[*] Starting orchestration for {len(batch_spec.scenes)} scenes...")
    summary = orchestrator.orchestrate_batch(batch_spec)

    print("\n-------------------------------------------------------------")
    print("BATCH ORCHESTRATION SUMMARY")
    print("-------------------------------------------------------------")
    print(f"Batch ID:           {summary.batch_id}")
    print(f"Status:             {summary.status.value}")
    print(f"Simulated Mode:     {summary.is_simulated}")
    print(f"Cost Mode:          {summary.cost_mode}")
    print(f"Total Panels:       {summary.total_panels}")
    print(f"Generated Panels:   {summary.generated_panels} / {summary.total_panels}")
    print(f"Verified Panels:    {summary.verified_panels} / {summary.total_panels}")
    print(f"Unverified Panels:  {summary.unverified_panels} / {summary.total_panels}")
    print(f"Pipeline Accepted:  {summary.successful_panels} / {summary.total_panels}")
    print(f"Failed:             {summary.failed_panels}")
    print(f"Unresolved:         {summary.unresolved_panels}")
    print(f"Total Attempts:     {summary.total_attempts}")
    print(f"Total Duration:     {summary.total_duration_seconds}s")
    print(f"Real Provider Cost: ${summary.known_cost_usd or 0.0:.4f}")
    if summary.simulated_cost_usd is not None:
        print(f"Simulated Cost:     ${summary.simulated_cost_usd:.4f} (synthetic test fixture)")
    print(f"Missing Cost Info:  {summary.missing_cost_information}")
    print(f"Missing Usage Info: {summary.missing_usage_information}")

    print("\n-------------------------------------------------------------")
    print("PANEL RESULTS & ARTIFACTS")
    print("-------------------------------------------------------------")
    for p in summary.panel_results:
        print(f"[{p.panel_id}] Status: {p.status.value} | Verification: {p.verification_status} | Attempts: {p.attempts_count} | Output: {p.output_asset_path}")
        print(f"         SHA-256: {p.output_content_hash}")
        print(f"         Context Fingerprint: {p.context_fingerprint[:16]}...")

    print(f"\n[+] Complete auditable batch record written to:")
    print(f"    {log_dir / (summary.batch_id + '.json')}")

    if summary.status.value == "COMPLETED":
        if args.mock_verifier:
            print("\n[+] ACCEPTANCE GATE: PASS (All panels successfully generated and verified via deterministic mock verifier)")
            print("    NOTE: Mock verification validates orchestration flow only; it is not evidence of live visual consistency.")
        elif summary.verified_panels == summary.total_panels:
            print("\n[+] ACCEPTANCE GATE: PASS (All panels successfully generated and verified by active verifier)")
        else:
            print("\n[+] ACCEPTANCE GATE: PASS (Orchestration succeeded: 6/6 panels generated. Visual verification: UNVERIFIED / PENDING downstream verification)")
        sys.exit(0)
    elif summary.status.value == "COMPLETED_WITH_FAILURES" and summary.unverified_panels > 0 and not args.require_verification:
        print("\n[+] ACCEPTANCE GATE: PASS (Batch orchestration succeeded: panels generated; visual verification pending downstream gate)")
        sys.exit(0)
    else:
        print(f"\n[!] ACCEPTANCE GATE: {summary.status.value}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
