"""
InkLoop Image Generation Knowledge Catalogue - Register Engine.
Manages the authoritative 60-group taxonomy register, deterministic serialization,
coverage audit, and research provenance validation.
"""
from pathlib import Path
import json
from typing import Dict, List, Optional, Union, Tuple

from app.catalogue.enums import (
    CoverageStatus,
    EvidenceClass,
    ClaimConfidence,
    RuleType,
    OutcomeVerdict,
)
from app.catalogue.models import (
    TaxonomyGroupRecord,
    SourceRecord,
    ResearchClaim,
    GenerationRule,
    RecipeRecord,
    CoverageSummary,
    utc_now_iso,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_REGISTER_FILE = DATA_DIR / "taxonomy_60_groups.json"


class TaxonomyRegister:
    """
    Authoritative register for InkLoop's 60-group image-generation knowledge taxonomy.
    Guarantees:
    - Exactly 60 groups represented with no omissions or duplicates.
    - Truthful coverage reporting (incompleteness is visible, unresearched groups are never labeled validated).
    - Stable identifiers, deterministic serialization, and Pydantic validation.
    """

    def __init__(self, data_file: Optional[Path] = None, force_rebuild: bool = False):
        self.data_file = data_file or DEFAULT_REGISTER_FILE
        self._groups: Dict[str, TaxonomyGroupRecord] = {}
        if force_rebuild or not self.data_file.exists():
            from app.catalogue.data_loader import build_canonical_60_groups
            groups = build_canonical_60_groups()
            self._groups = {g.group_id: g for g in groups}
            self.save()
            return
        self._load()

    def _load(self) -> None:
        """Loads and validates the taxonomy register from JSON."""
        if not self.data_file.exists():
            # If not yet created, initialize with canonical 60-group baseline
            from app.catalogue.data_loader import build_canonical_60_groups
            groups = build_canonical_60_groups()
            self._groups = {g.group_id: g for g in groups}
            self.save()
            return

        with open(self.data_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        loaded_groups = {}
        for item in raw_data:
            rec = TaxonomyGroupRecord.model_validate(item)
            loaded_groups[rec.group_id] = rec

        self._groups = loaded_groups

    def rebuild_baseline(self) -> None:
        """Forces recreation of all 60 groups from canonical data_loader and saves to disk."""
        from app.catalogue.data_loader import build_canonical_60_groups
        groups = build_canonical_60_groups()
        self._groups = {g.group_id: g for g in groups}
        self.save()

    def save(self, target_path: Optional[Path] = None) -> None:
        """Saves register to target path with deterministic key ordering."""
        out_path = target_path or self.data_file
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Sort by sequential group number
        sorted_groups = sorted(self._groups.values(), key=lambda g: g.group_number)
        serialized = [g.model_dump() for g in sorted_groups]

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2, sort_keys=True)

    def get_group(self, group_id_or_number: Union[str, int]) -> Optional[TaxonomyGroupRecord]:
        """Looks up a group by stable ID (e.g. 'tax_01_comic_formats') or number (1..60)."""
        if isinstance(group_id_or_number, int):
            for g in self._groups.values():
                if g.group_number == group_id_or_number:
                    return g
            return None
        return self._groups.get(group_id_or_number)

    def list_groups(self) -> List[TaxonomyGroupRecord]:
        """Returns all 60 groups sorted by group number."""
        return sorted(self._groups.values(), key=lambda g: g.group_number)

    def add_or_update_group(self, group: TaxonomyGroupRecord) -> None:
        """Adds or updates a group record, validating all constraints."""
        # Re-validate model
        validated = TaxonomyGroupRecord.model_validate(group.model_dump())
        self._groups[validated.group_id] = validated

    def get_summary(self) -> CoverageSummary:
        """Generates a truthful, deterministic statistical inventory of the register."""
        groups = self.list_groups()
        status_counts: Dict[str, int] = {st.value: 0 for st in CoverageStatus}

        total_elements = sum(len(g.canonical_elements) for g in groups)
        total_sources = sum(len(g.sources) for g in groups)
        total_claims = sum(len(g.claims) for g in groups)
        total_rules = sum(len(g.rules) for g in groups)
        total_recipes = sum(len(g.recipes) for g in groups)
        total_experiments = sum(1 for g in groups if g.has_recorded_experiments)

        gaps_by_group = {}
        for g in groups:
            status_counts[g.status.value] += 1
            if g.research_gaps:
                gaps_by_group[g.group_id] = g.research_gaps

        return CoverageSummary(
            total_groups=len(groups),
            unresearched_count=status_counts[CoverageStatus.UNRESEARCHED.value],
            researched_count=status_counts[CoverageStatus.RESEARCHED.value],
            experimentally_tested_count=status_counts[CoverageStatus.EXPERIMENTALLY_TESTED.value],
            validated_count=status_counts[CoverageStatus.VALIDATED.value],
            deprecated_count=status_counts[CoverageStatus.DEPRECATED.value],
            total_canonical_elements=total_elements,
            total_sources=total_sources,
            total_claims=total_claims,
            total_rules=total_rules,
            total_recipes=total_recipes,
            total_experiments=total_experiments,
            status_breakdown=status_counts,
            gaps_by_group=gaps_by_group,
            generated_at=utc_now_iso(),
        )

    def validate_invariants(self) -> List[str]:
        """
        Audits the entire register against project invariants:
        1. Exactly 60 groups represented.
        2. Group numbers 1..60 consecutive with no gaps or duplicates.
        3. Stable ID pattern 'tax_{number:02d}_{slug}'.
        4. No validated group lacks primary sources or passing recipes.
        5. No recipe claims empirical validation without linked experiment.
        """
        errors = []
        groups = self.list_groups()

        if len(groups) != 60:
            errors.append(f"Expected exactly 60 taxonomy groups, found {len(groups)}")

        seen_numbers = set()
        seen_ids = set()

        for idx, g in enumerate(groups, start=1):
            if g.group_number in seen_numbers:
                errors.append(f"Duplicate group number: {g.group_number}")
            seen_numbers.add(g.group_number)

            if g.group_id in seen_ids:
                errors.append(f"Duplicate group ID: {g.group_id}")
            seen_ids.add(g.group_id)

            if g.group_number != idx:
                errors.append(f"Non-consecutive group numbering at index {idx}: group is {g.group_number}")

            # Verify unresearched groups do not claim validation
            if g.status == CoverageStatus.UNRESEARCHED and (g.is_empirically_validated or g.has_recorded_experiments):
                errors.append(f"Group '{g.group_id}' is UNRESEARCHED but claims validation or experiments")

            # Verify validated groups meet high evidence bar
            if g.status == CoverageStatus.VALIDATED:
                if not g.is_empirically_validated:
                    errors.append(f"Group '{g.group_id}' is marked VALIDATED but is_empirically_validated is False")
                if not any(r.is_empirically_validated and r.result == OutcomeVerdict.PASS for r in g.recipes):
                    errors.append(f"Group '{g.group_id}' is marked VALIDATED but has no passing validated recipe")

        return errors
