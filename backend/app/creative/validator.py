"""
Cross-Document Coherence and Canon Conflict Engine.
Performs deterministic, multi-category quality and consistency checks
across Story Bible, Characters, Relationships, World Systems, Narrative Arcs,
Visual Styles, and Machine-Readable Creative Contracts.
"""
from typing import List, Dict, Any, Optional
from app.creative.schemas import (
    CreativePackage,
    CoherenceFinding,
    FindingSeverity,
    FindingCategory,
    ValidationResult,
    CharacterIdentityProfile,
)
from app.project.bible import StoryBible

class CreativeCoherenceValidator:
    """Validates structural and semantic consistency across a CreativePackage."""

    def validate_package(
        self,
        package: CreativePackage,
        existing_bible: Optional[StoryBible] = None,
        active_bible: Optional[StoryBible] = None,
    ) -> ValidationResult:
        bible = existing_bible or active_bible
        findings: List[CoherenceFinding] = []

        # 1. Character Invariants & Psychological Coherence
        findings.extend(self._validate_characters(package.characters))

        # 2. Ensemble & Relationship Referential Integrity
        findings.extend(self._validate_relationships(package))

        # 3. World & Supernatural Rule Constraints (Cost/Limitation check)
        findings.extend(self._validate_world_rules(package.world_bible))

        # 4. Narrative Structure & Chapter Progression
        findings.extend(self._validate_narrative_structure(package.narrative_structure, package.characters))

        # 5. Visual Style Independence
        findings.extend(self._validate_style_profile(package.style_profile))

        # 6. Canon Conflict Checks (Against Existing StoryBible)
        if bible:
            findings.extend(self._detect_canon_conflicts(package, bible))

        # Has errors?
        has_errors = any(f.severity == FindingSeverity.ERROR for f in findings)

        return ValidationResult(
            project_id=package.project_id,
            is_coherent=not has_errors,
            findings=findings,
        )

    # Alias for convenience
    validate = validate_package


    def _validate_characters(self, characters: Dict[str, CharacterIdentityProfile]) -> List[CoherenceFinding]:
        findings = []
        if not characters:
            findings.append(CoherenceFinding(
                finding_id="char_empty_cast",
                severity=FindingSeverity.ERROR,
                category=FindingCategory.CHARACTER,
                message="No characters defined in Creative Package.",
                affected_artefact="characters",
                evidence="Cast dictionary is empty.",
                suggested_correction="Define at least one primary protagonist.",
            ))
            return findings

        char_list = list(characters.values())

        # Check individual character requirements
        for char in char_list:
            if not char.external_goal or len(char.external_goal.strip()) < 5:
                findings.append(CoherenceFinding(
                    finding_id=f"char_{char.character_id}_missing_goal",
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.CHARACTER,
                    message=f"Character '{char.name}' lacks a concrete external goal.",
                    affected_artefact=f"character:{char.character_id}",
                    evidence=f"external_goal = '{char.external_goal}'",
                    suggested_correction="Specify what this character is actively trying to achieve in the story.",
                ))

            if not char.internal_need or len(char.internal_need.strip()) < 5:
                findings.append(CoherenceFinding(
                    finding_id=f"char_{char.character_id}_missing_need",
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.CHARACTER,
                    message=f"Character '{char.name}' lacks an internal emotional need or moral wound.",
                    affected_artefact=f"character:{char.character_id}",
                    evidence=f"internal_need = '{char.internal_need}'",
                    suggested_correction="Define the psychological flaw or wound the character must confront.",
                ))

            if not char.visual_invariants or len(char.visual_invariants) == 0:
                findings.append(CoherenceFinding(
                    finding_id=f"char_{char.character_id}_no_invariants",
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.VISUAL,
                    message=f"Character '{char.name}' has zero visual invariants defined.",
                    affected_artefact=f"character:{char.character_id}",
                    evidence="visual_invariants list is empty",
                    suggested_correction="Define at least 2 mandatory visual invariants (e.g. hair streak, glasses, signature coat).",
                ))

        # Check for duplicate / redundant characters
        for i in range(len(char_list)):
            for j in range(i + 1, len(char_list)):
                c1, c2 = char_list[i], char_list[j]
                if c1.role.lower() == c2.role.lower() and c1.role.lower() in ["protagonist", "mentor"]:
                    findings.append(CoherenceFinding(
                        finding_id=f"char_duplicate_role_{c1.character_id}_{c2.character_id}",
                        severity=FindingSeverity.WARNING,
                        category=FindingCategory.CHARACTER,
                        message=f"Potential role overlap between '{c1.name}' and '{c2.name}'.",
                        affected_artefact="characters",
                        evidence=f"Both characters are assigned the primary role '{c1.role}'.",
                        suggested_correction="Differentiate their narrative functions (e.g. one as Deuteragonist or Foil).",
                    ))

        return findings

    def _validate_relationships(self, package: CreativePackage) -> List[CoherenceFinding]:
        findings = []
        cast_ids = set(package.characters.keys())
        graph = package.relationship_graph

        for edge in graph.edges:
            if edge.source_character_id not in cast_ids:
                findings.append(CoherenceFinding(
                    finding_id=f"rel_missing_source_{edge.source_character_id}",
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.CONTRACT,
                    message=f"Relationship references undeclared character '{edge.source_character_id}'.",
                    affected_artefact="relationship_graph",
                    evidence=f"Source ID '{edge.source_character_id}' not found in package characters.",
                    suggested_correction="Add character to cast or update relationship source.",
                ))
            if edge.target_character_id not in cast_ids:
                findings.append(CoherenceFinding(
                    finding_id=f"rel_missing_target_{edge.target_character_id}",
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.CONTRACT,
                    message=f"Relationship references undeclared character '{edge.target_character_id}'.",
                    affected_artefact="relationship_graph",
                    evidence=f"Target ID '{edge.target_character_id}' not found in package characters.",
                    suggested_correction="Add character to cast or update relationship target.",
                ))

        return findings

    def _validate_world_rules(self, world_bible) -> List[CoherenceFinding]:
        findings = []
        for ability in world_bible.supernatural_or_tech_rules:
            # Rule: Powers MUST have costs and limits to preserve narrative stakes!
            ability_id = getattr(ability, "ability_id", getattr(ability, "name", "unknown"))
            if not ability.cost_or_strain or len(ability.cost_or_strain.strip()) < 4:
                findings.append(CoherenceFinding(
                    finding_id=f"world_unlimited_power_{ability.name}",
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.WORLD,
                    title="Unbounded Power Violation",
                    entity_id=ability_id,
                    message=f"Supernatural ability '{ability.name}' lacks a defined cost or strain.",
                    affected_artefact="world_bible",
                    evidence=f"cost_or_strain is empty or trivial ('{ability.cost_or_strain}')",
                    suggested_correction="Specify the physical, mental, or resource cost of invoking this power.",
                ))

            if not ability.absolute_limit or len(ability.absolute_limit.strip()) < 4:
                findings.append(CoherenceFinding(
                    finding_id=f"world_no_limit_{ability.name}",
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.WORLD,
                    title="Missing Power Limit",
                    entity_id=ability_id,
                    message=f"Supernatural ability '{ability.name}' lacks an absolute limitation or failure boundary.",
                    affected_artefact="world_bible",
                    evidence=f"absolute_limit = '{ability.absolute_limit}'",
                    suggested_correction="Define what the ability cannot do or circumstances where it fails.",
                ))

        return findings

    def _validate_narrative_structure(self, structure, characters) -> List[CoherenceFinding]:
        findings = []
        cast_ids = set(characters.keys())

        if not structure.chapters:
            findings.append(CoherenceFinding(
                finding_id="narrative_no_chapters",
                severity=FindingSeverity.WARNING,
                category=FindingCategory.STORY,
                message="Narrative structure has no chapter or episode outlines.",
                affected_artefact="narrative_structure",
                evidence="chapters list is empty",
                suggested_correction="Generate at least 3 chapters with turning points and cliffhangers.",
            ))
            return findings

        for ch in structure.chapters:
            if not ch.turning_point or len(ch.turning_point.strip()) < 5:
                findings.append(CoherenceFinding(
                    finding_id=f"narrative_ch{ch.chapter_number}_no_pivot",
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.STORY,
                    message=f"Chapter {ch.chapter_number} '{ch.title}' lacks a decisive turning point.",
                    affected_artefact=f"chapter:{ch.chapter_number}",
                    evidence=f"turning_point = '{ch.turning_point}'",
                    suggested_correction="Specify what knowledge, danger, or status changes in this chapter.",
                ))

            for sc in ch.scene_candidates:
                for cid in sc.participating_character_ids:
                    if cid not in cast_ids:
                        findings.append(CoherenceFinding(
                            finding_id=f"narrative_scene_{sc.scene_id}_undeclared_char",
                            severity=FindingSeverity.ERROR,
                            category=FindingCategory.CONTRACT,
                            message=f"Scene '{sc.title}' contains undeclared character '{cid}'.",
                            affected_artefact=f"scene:{sc.scene_id}",
                            evidence=f"Character '{cid}' is in scene participants but not in cast.",
                            suggested_correction=f"Register '{cid}' in Character Bible or remove from scene.",
                        ))

        return findings

    def _validate_style_profile(self, style) -> List[CoherenceFinding]:
        findings = []
        if not style.line_art_rules:
            findings.append(CoherenceFinding(
                finding_id="style_no_lineart_rules",
                severity=FindingSeverity.WARNING,
                category=FindingCategory.VISUAL,
                message="Visual Style Profile lacks linework rules.",
                affected_artefact="style_profile",
                evidence="line_art_rules is empty",
                suggested_correction="Specify contour line weights, brush dynamics, and ink density.",
            ))

        if not style.negative_constraints:
            findings.append(CoherenceFinding(
                finding_id="style_no_negative_constraints",
                severity=FindingSeverity.SUGGESTION,
                category=FindingCategory.VISUAL,
                message="Visual Style Profile has no negative constraints.",
                affected_artefact="style_profile",
                evidence="negative_constraints list is empty",
                suggested_correction="Define styles to avoid (e.g. 'no 3D render', 'no soft gradients').",
            ))

        return findings

    def _detect_canon_conflicts(
        self,
        package: CreativePackage,
        existing_bible: StoryBible
    ) -> List[CoherenceFinding]:
        findings = []

        # Check existing characters for invariant erosion
        for cid, existing_char in existing_bible.characters.items():
            if cid in package.characters:
                new_char = package.characters[cid]
                existing_invariants = set(existing_char.visual_invariants)
                new_invariants = set(new_char.visual_invariants)

                missing_invariants = existing_invariants - new_invariants
                if missing_invariants:
                    findings.append(CoherenceFinding(
                        finding_id=f"canon_conflict_{cid}_invariants_dropped",
                        severity=FindingSeverity.ERROR,
                        category=FindingCategory.CANON_CONFLICT,
                        title="Canon Conflict: Dropped Invariants",
                        entity_id=cid,
                        message=f"Proposal removes canonical invariant(s) from character '{existing_char.name}'.",
                        affected_artefact=f"character:{cid}",
                        evidence=f"Approved canon requires: {sorted(list(missing_invariants))}. Proposal omitted them.",
                        suggested_correction="Retain all approved invariants in character profile or submit formal mutation proposal.",
                    ))

                # Check hair color or explicit contradiction
                existing_hair = "black" if (
                    any("black" in inv.lower() for inv in existing_invariants) or
                    any("black" in getattr(attr, "text", "").lower() for attr in getattr(existing_char, "attributes", []))
                ) else None
                new_hair = "blonde" if any("blonde" in inv.lower() for inv in new_invariants) else None
                if existing_hair and new_hair and existing_hair != new_hair:
                    findings.append(CoherenceFinding(
                        finding_id=f"canon_conflict_{cid}_hair_contradiction",
                        severity=FindingSeverity.ERROR,
                        category=FindingCategory.CANON_CONFLICT,
                        title="Canon Conflict: Hair Color Contradiction",
                        entity_id=cid,
                        message=f"Character '{existing_char.name}' hair color contradicts canon ({existing_hair} vs {new_hair}).",
                        affected_artefact=f"character:{cid}",
                        evidence=f"Approved canon hair: {existing_hair}. Proposal sets: {new_hair}.",
                        suggested_correction="Retain approved hair color or propose formal canon mutation.",
                    ))

                # Check name changes
                if new_char.name != existing_char.name:
                    findings.append(CoherenceFinding(
                        finding_id=f"canon_conflict_{cid}_name_changed",
                        severity=FindingSeverity.WARNING,
                        category=FindingCategory.CANON_CONFLICT,
                        title="Canon Conflict: Name Changed",
                        entity_id=cid,
                        message=f"Character '{cid}' name changed from '{existing_char.name}' to '{new_char.name}'.",
                        affected_artefact=f"character:{cid}",
                        evidence=f"Original name '{existing_char.name}' -> New name '{new_char.name}'",
                        suggested_correction="Confirm rename with human operator approval before committing to canon.",
                    ))

        return findings
