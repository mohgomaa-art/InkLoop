"""
InkLoop Image Generation Knowledge Catalogue & Taxonomy Coverage Register.
Public API exports for Task T6.1.
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
]
