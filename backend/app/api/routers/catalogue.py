"""
Image Knowledge Catalogue & Research Governance API Router.
Exposes the 60-group taxonomy register, canonical elements, research claims,
formal promotion workflows, and structured licensing rights.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from app.catalogue.register import TaxonomyRegister, CoverageStatus, EvidenceClass, ClaimConfidence
from app.catalogue.governance import (
    PromotionWorkflow,
    PromotionReviewRecord,
    ReviewDecision,
    create_default_license_registry,
    LicenseRegistry,
)
from app.catalogue.retrieval_models import KnowledgeRetrievalRequest, KnowledgeRetrievalResult
from app.catalogue.retrieval import get_default_knowledge_retriever, KnowledgeRetriever
from app.catalogue.errors import RetrievalError, InvalidRetrievalRequestError, NoEligibleKnowledgeError

router = APIRouter(prefix="/catalogue", tags=["Knowledge Catalogue & Governance"])

_taxonomy_instance: Optional[TaxonomyRegister] = None
_workflow_instance: Optional[PromotionWorkflow] = None
_license_instance: Optional[LicenseRegistry] = None

def get_taxonomy() -> TaxonomyRegister:
    global _taxonomy_instance
    if _taxonomy_instance is None:
        _taxonomy_instance = TaxonomyRegister()
    return _taxonomy_instance

def get_workflow() -> PromotionWorkflow:
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = PromotionWorkflow()
    return _workflow_instance

def get_licenses() -> LicenseRegistry:
    global _license_instance
    if _license_instance is None:
        _license_instance = create_default_license_registry()
    return _license_instance

class PromoteGroupRequest(BaseModel):
    group_id: str
    target_status: str = Field(..., description="'RESEARCHED' or 'VALIDATED'")
    reviewer_id: str
    reviewer_role: str
    rationale: str
    verified_evidence_ids: List[str]

@router.get("/summary")
def get_catalogue_summary() -> Dict[str, Any]:
    """Retrieve high-level coverage summary across all 60 taxonomy groups."""
    tax = get_taxonomy()
    summary = tax.get_summary()
    return summary.model_dump()

@router.get("/groups")
def list_groups() -> List[Dict[str, Any]]:
    """List all 60 taxonomy groups with their coverage and empirical validation status."""
    tax = get_taxonomy()
    groups = tax.list_groups()
    return [
        {
            "group_id": g.group_id,
            "group_number": g.group_number,
            "name": g.canonical_name,
            "description": g.image_generation_relevance,
            "coverage_status": g.status.value,
            "element_count": len(g.canonical_elements),
            "claims_count": len(g.claims),
            "recipes_count": len(g.recipes),
            "is_empirically_validated": g.is_empirically_validated,
            "has_recorded_experiments": g.has_recorded_experiments,
            "active_research_gaps": g.research_gaps,
        }
        for g in groups
    ]

@router.get("/groups/{group_id}")
def get_group_detail(group_id: str) -> Dict[str, Any]:
    """Retrieve full detail for a specific taxonomy group including claims, recipes, and sources."""
    tax = get_taxonomy()
    group = tax.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_1005_UNKNOWN_ENTITY_REFERENCE", "message": f"Group {group_id} not found"}
        )
    data = group.model_dump()
    data["coverage_status"] = group.status.value
    return data

@router.get("/licenses")
def list_licenses() -> List[Dict[str, Any]]:
    """List all tracked licenses with targets and commercial safety clearance."""
    reg = get_licenses()
    licenses = reg.list_licenses()
    return [l.model_dump() for l in licenses]

@router.post("/reviews/promote")
def promote_group_status(req: PromoteGroupRequest) -> Dict[str, Any]:
    """
    Submit a formal review to promote a taxonomy group's coverage status.
    Enforces fail-closed validation: unverified claims or missing evidence trigger REJECTED decision.
    """
    tax = get_taxonomy()
    workflow = get_workflow()
    group = tax.get_group(req.group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_1005_UNKNOWN_ENTITY_REFERENCE", "message": f"Group {req.group_id} not found"}
        )

    try:
        target_cov = CoverageStatus(req.target_status.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_1001_INVALID_SCHEMA", "message": f"Invalid target status: {req.target_status}"}
        )

    review_record = workflow.review_group(
        group=group,
        target_status=target_cov,
        reviewer_id=req.reviewer_id,
        reviewer_role=req.reviewer_role,
        rationale=req.rationale,
        verified_evidence_ids=req.verified_evidence_ids,
    )

    if review_record.decision == ReviewDecision.APPROVED:
        group.status = target_cov
        tax.add_or_update_group(group)
        tax.save()

    return review_record.model_dump()

@router.get("/reviews")
def list_reviews() -> List[Dict[str, Any]]:
    """List all immutable promotion audit records."""
    workflow = get_workflow()
    return [r.model_dump() for r in workflow.list_reviews()]

@router.post("/retrieve")
def retrieve_knowledge(req: KnowledgeRetrievalRequest) -> Dict[str, Any]:
    """
    Retrieve deterministic, bounded knowledge records relevant to the current scene context.
    Enforces compatibility, status thresholds, and returns selection hash for context fingerprinting.
    """
    retriever = get_default_knowledge_retriever()
    try:
        result = retriever.retrieve(req)
        return result.model_dump()
    except NoEligibleKnowledgeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": e.error_code, "message": str(e), "details": e.details}
        )
    except RetrievalError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": e.error_code, "message": str(e), "details": e.details}
        )

@router.post("/explain")
def explain_retrieval(req: KnowledgeRetrievalRequest) -> Dict[str, Any]:
    """
    Dry-run / explain operation showing evaluated candidates, relevance scores,
    exclusion reasons, budget utilization, and inserted prompt clauses without making model calls.
    """
    retriever = get_default_knowledge_retriever()
    try:
        result = retriever.retrieve(req)
        explanation = retriever.explain(req)
        return {
            "scene_id": req.scene_id,
            "catalogue_version": result.catalogue_version,
            "selection_hash": result.selection_hash,
            "selected_record_ids": result.selected_record_ids,
            "positive_clauses": result.positive_prompt_clauses,
            "negative_clauses": result.negative_prompt_clauses,
            "budget_consumed": result.budget_consumed,
            "provenance_sources": [s.model_dump() for s in result.provenance_sources],
            "explanation_markdown": explanation,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_RETRIEVAL_EXPLAIN_FAILED", "message": str(e)}
        )
