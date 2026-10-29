"""
InkLoop Image Generation Knowledge Catalogue - Enums & Taxonomies.
Defines authoritative coverage states, evidence classes, claim confidences,
rule categories, and outcome verdicts for the Image Generation Engine.
"""
from enum import Enum


class CoverageStatus(str, Enum):
    """
    Lifecycle status of a taxonomy group or concept in the catalogue.
    Incompleteness must be explicitly visible.
    """
    UNRESEARCHED = "unresearched"
    RESEARCHED = "researched"
    EXPERIMENTALLY_TESTED = "experimentally_tested"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"


class EvidenceClass(str, Enum):
    """
    Authoritative classification of evidence provenance.
    Separates primary provider documentation from unverified claims.
    """
    PRIMARY_PROVIDER_DOC = "primary_provider_doc"
    PEER_REVIEWED_RESEARCH = "peer_reviewed_research"
    INKLOOP_EXPERIMENT = "inkloop_experiment"
    SECONDARY_TECHNICAL = "secondary_technical"
    ANECDOTAL_UNVERIFIED = "anecdotal_unverified"


class ClaimConfidence(str, Enum):
    """
    Confidence classification for research claims (Task T6.1).
    Distinguishes verifiable facts from working hypotheses.
    """
    FACT = "fact"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    EXPERIMENTAL_RESULT = "experimental_result"
    UNKNOWN = "unknown"


class RuleType(str, Enum):
    """Category of image-generation directive or constraint."""
    POSITIVE_GUIDANCE = "positive_guidance"
    NEGATIVE_CONSTRAINT = "negative_constraint"
    COMPATIBILITY_RULE = "compatibility_rule"
    CONFLICT_RESOLUTION = "conflict_resolution"
    MODEL_LIMITATION = "model_limitation"


class OutcomeVerdict(str, Enum):
    """Empirical evaluation result for a recipe or experiment."""
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    UNTESTED = "untested"


class ConflictPriority(str, Enum):
    """Priority resolution when two prompt directives or visual constraints clash."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LicenseType(str, Enum):
    """Classification of asset and software licensing terms."""
    OPEN_FONT_LICENSE = "open_font_license"
    OPEN_SOURCE_PERMISSIVE = "open_source_permissive"
    PROPRIETARY_ORIGINAL = "proprietary_original"
    MODEL_PROVIDER_TERMS = "model_provider_terms"
    CREATIVE_COMMONS = "creative_commons"
    PUBLIC_DOMAIN = "public_domain"
    UNKNOWN = "unknown"


class LicenseTargetType(str, Enum):
    """Target entity subject to licensing governance."""
    FONT = "font"
    SOFTWARE_LIBRARY = "software_library"
    MODEL_GENERATED = "model_generated"
    REFERENCE_IMAGE = "reference_image"
    EXTERNAL_DATASET = "external_dataset"


class ReviewDecision(str, Enum):
    """Decision outcome of a research promotion review."""
    APPROVED_PROMOTION = "approved_promotion"
    REJECTED = "rejected"
    MORE_EVIDENCE_NEEDED = "more_evidence_needed"

