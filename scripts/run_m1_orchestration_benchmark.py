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
    args = parser.parse_args()

    config = InkLoopConfig.load()

    print("=================================================================")
    print("INKLOOP M1: SIX-PANEL GENERATION ORCHESTRATION BENCHMARK")
    print("=================================================================")
    print(f"Mode: {'LIVE META API' if args.live else 'DETERMINISTIC SIMULATED ADAPTER'}")
    print(f"Model: {config.muse_image_model}")
    print(f"Max retries per panel: {config.max_retries_per_panel}")
    print(f"Global spend cap: ${config.global_spend_cap_usd:.2f}")
    print(f"Credentials present: {config.has_credentials} ({config.mask_key()})")

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
    orchestrator = BatchOrchestrator(config=config, adapter=adapter, run_log_dir=log_dir)

    batch_spec = create_m0_benchmark_batch_spec(
        batch_id=args.batch_id,
        max_retries=config.max_retries_per_panel,
        spend_cap_usd=config.global_spend_cap_usd,
        output_dir=str(out_path)
    )

    print(f"\n[*] Starting orchestration for {len(batch_spec.scenes)} scenes...")
    summary = orchestrator.orchestrate_batch(batch_spec)

    print("\n-------------------------------------------------------------")
    print("BATCH ORCHESTRATION SUMMARY")
    print("-------------------------------------------------------------")
    print(f"Batch ID:           {summary.batch_id}")
    print(f"Status:             {summary.status.value}")
    print(f"Total Panels:       {summary.total_panels}")
    print(f"Successful:         {summary.successful_panels}")
    print(f"Failed:             {summary.failed_panels}")
    print(f"Unresolved:         {summary.unresolved_panels}")
    print(f"Total Attempts:     {summary.total_attempts}")
    print(f"Total Duration:     {summary.total_duration_seconds}s")
    print(f"Known Cost:         ${summary.known_cost_usd or 0.0:.4f}")
    print(f"Missing Cost Info:  {summary.missing_cost_information}")
    print(f"Missing Usage Info: {summary.missing_usage_information}")

    print("\n-------------------------------------------------------------")
    print("PANEL RESULTS & ARTIFACTS")
    print("-------------------------------------------------------------")
    for p in summary.panel_results:
        print(f"[{p.panel_id}] Status: {p.status.value} | Attempts: {p.attempts_count} | Output: {p.output_asset_path}")
        print(f"         SHA-256: {p.output_content_hash}")
        print(f"         Context Fingerprint: {p.context_fingerprint[:16]}...")

    print(f"\n[+] Complete auditable batch record written to:")
    print(f"    {log_dir / (summary.batch_id + '.json')}")

    if summary.status.value == "COMPLETED":
        print("\n[+] ACCEPTANCE GATE: PASS (All panels successfully generated and verified)")
        sys.exit(0)
    else:
        print(f"\n[!] ACCEPTANCE GATE: {summary.status.value}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
