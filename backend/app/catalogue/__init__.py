"""
InkLoop Image Generation Knowledge Catalogue & Taxonomy Coverage Register.
Public API exports for Tasks T6.1, T6.2, and T6.3.
"""
from app.catalogue.enums import (
    CoverageStatus,
    EvidenceClass,
    ClaimConfidence,
    RuleType,
    OutcomeVerdict,
    ConflictPriority,
    LicenseType,
    LicenseTargetType,
    ReviewDecision,
)
from app.catalogue.models import (
    SourceRecord,
    ResearchClaim,
    GenerationRule,
    RecipeRecord,
    TaxonomyGroupRecord,
    CoverageSummary,
    LicenseRecord,
    PromotionReviewRecord,
)
from app.catalogue.register import TaxonomyRegister
from app.catalogue.governance import (
    LicenseRegistry,
    PromotionWorkflow,
    create_default_license_registry,
)
from app.catalogue.errors import (
    CatalogueError,
    RetrievalError,
    InvalidRetrievalRequestError,
    NoEligibleKnowledgeError,
    KnowledgeCompatibilityConflictError,
)
from app.catalogue.retrieval_models import (
    KnowledgeBudget,
    KnowledgeRetrievalPolicy,
    KnowledgeRetrievalRequest,
    CandidateEvaluation,
    KnowledgeRetrievalResult,
)
from app.catalogue.retrieval import (
    KnowledgeRetriever,
    get_default_knowledge_retriever,
)

__all__ = [
    "CoverageStatus",
    "EvidenceClass",
    "ClaimConfidence",
    "RuleType",
    "OutcomeVerdict",
    "ConflictPriority",
    "LicenseType",
    "LicenseTargetType",
    "ReviewDecision",
    "SourceRecord",
    "ResearchClaim",
    "GenerationRule",
    "RecipeRecord",
    "TaxonomyGroupRecord",
    "CoverageSummary",
    "LicenseRecord",
    "PromotionReviewRecord",
    "TaxonomyRegister",
    "LicenseRegistry",
    "PromotionWorkflow",
    "create_default_license_registry",
    "CatalogueError",
    "RetrievalError",
    "InvalidRetrievalRequestError",
    "NoEligibleKnowledgeError",
    "KnowledgeCompatibilityConflictError",
    "KnowledgeBudget",
    "KnowledgeRetrievalPolicy",
    "KnowledgeRetrievalRequest",
    "CandidateEvaluation",
    "KnowledgeRetrievalResult",
    "KnowledgeRetriever",
    "get_default_knowledge_retriever",
]
