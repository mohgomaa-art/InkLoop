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
)
from app.catalogue.models import (
    SourceRecord,
    ResearchClaim,
    GenerationRule,
    RecipeRecord,
    TaxonomyGroupRecord,
    CoverageSummary,
)
from app.catalogue.register import TaxonomyRegister

__all__ = [
    "CoverageStatus",
    "EvidenceClass",
    "ClaimConfidence",
    "RuleType",
    "OutcomeVerdict",
    "ConflictPriority",
    "SourceRecord",
    "ResearchClaim",
    "GenerationRule",
    "RecipeRecord",
    "TaxonomyGroupRecord",
    "CoverageSummary",
    "TaxonomyRegister",
]
