"""
Health, Configuration, and Diagnostic Router.
Provides safe system readiness checks and environment inspection without secret leakage.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter

from app.config import InkLoopConfig, PROJECT_ROOT

router = APIRouter(tags=["Health & Diagnostics"])

@router.get("/health")
def get_health() -> Dict[str, Any]:
    """Health check endpoint confirming server readiness."""
    return {
        "status": "healthy",
        "service": "InkLoop Comic Production Engine",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/config/diagnostics")
def get_diagnostics() -> Dict[str, Any]:
    """
    Returns sanitized operational diagnostics.
    Enforces strict secret hygiene: API keys and bearer tokens are never serialized.
    """
    config = InkLoopConfig.load()
    
    # Check paths
    runs_dir = PROJECT_ROOT / "runs"
    batches_dir = runs_dir / "batches"
    catalogue_file = PROJECT_ROOT / "backend" / "app" / "catalogue" / "data" / "taxonomy_60_groups.json"
    nour_ref_file = PROJECT_ROOT / "runs" / "m0_visual" / "reference" / "nour_reference.png"

    return {
        "provider": {
            "name": "Meta Model API",
            "base_url": config.meta_base_url,
            "configured": config.has_credentials,
            "models_available": [config.muse_image_model, config.muse_spark_model, config.sam_model],
            "api_key_masked": config.mask_key(),
            "notice": None if config.has_credentials else "MODEL_API_KEY is not set. Get your API key at https://dev.meta.ai and add it to your .env file.",
        },
        "storage": {
            "project_root": str(PROJECT_ROOT),
            "runs_directory_exists": runs_dir.exists(),
            "batches_directory_exists": batches_dir.exists(),
            "catalogue_register_exists": catalogue_file.exists(),
            "nour_reference_anchor_exists": nour_ref_file.exists(),
        },
        "budget_defaults": {
            "default_spend_cap_usd": float(config.global_spend_cap_usd),
            "default_max_retries": config.max_retries_per_panel,
            "concurrency_limit": config.max_concurrent_requests,
        },
        "system_status": {
            "m0_feasibility_gate": "PASSED_EMPIRICALLY",
            "m1_orchestrator": "READY",
            "visual_verification": "READY",
            "catalogue_60_groups": "FOUNDATION_ACTIVE",
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
    }
