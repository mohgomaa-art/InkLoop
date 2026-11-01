"""
Visual Evaluation, Scientific Benchmarks & Regression Corpus API Router.
Exposes empirical M0 visual feasibility metrics with Wilson score confidence intervals,
the 7-domain regression corpus with honest engine readiness gating, and blind human evaluation sheets.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status

from app.evaluation.m0_adapter import load_m0_execution_summary, build_m0_experiment_plan
from app.evaluation.regression import VisualRegressionCorpus
from app.evaluation.blinding import BlindingService

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Regressions"])

_corpus_instance: Optional[VisualRegressionCorpus] = None

def get_corpus() -> VisualRegressionCorpus:
    global _corpus_instance
    if _corpus_instance is None:
        _corpus_instance = VisualRegressionCorpus()
    return _corpus_instance

@router.get("/benchmarks/m0")
def get_m0_benchmark() -> Dict[str, Any]:
    """
    Retrieve empirical M0 feasibility benchmark results.
    Includes Wilson score confidence intervals, Arm A vs Arm B comparisons, exact latencies,
    reported token usages, and scientific limits (exploratory feasibility N=6).
    """
    try:
        summary = load_m0_execution_summary()
        return summary.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "ERR_6003_ENGINE_CRASH", "message": f"Failed loading M0 summary: {e}"}
        )

@router.get("/regressions")
def get_regression_corpus() -> Dict[str, Any]:
    """
    Retrieve the 7-domain visual regression test corpus.
    Maintains strict fail-closed readiness: unimplemented engines (E2, E4-E7, S8)
    evaluate honestly as BLOCKED_BY_ENGINE without false passes.
    """
    corpus = get_corpus()
    cases = corpus.list_cases()
    readiness = corpus.get_readiness_inventory()
    
    return {
        "readiness_inventory": readiness,
        "cases": [c.model_dump() for c in cases],
    }

@router.get("/readiness")
def get_engine_readiness() -> Dict[str, Any]:
    """Retrieve explicit implementation and readiness status across all 10 system engines."""
    corpus = get_corpus()
    return corpus.get_readiness_inventory()
