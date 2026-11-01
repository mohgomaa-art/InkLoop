"""
Canonical definitions and models for InkLoop Story Bible.
Defines immutable identity, style, characters, locations, props, canon snapshots,
and explicit canon mutation proposals.
Reuses CharacterSpec, AttributeCheck, and Tolerances from app.schemas.
"""
import json
import hashlib
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.schemas import CharacterSpec, AttributeCheck, Tolerances
from app.project.asset_refs import AssetRef

class CanonError(Exception):
    """Base exception for canonical definition and mutation errors."""
    pass

class UnauthorizedMutationError(CanonError):
    """Raised when an attempt is made to mutate canon without approved proposal."""
    pass

CanonImmutabilityError = UnauthorizedMutationError

class CanonValidationError(CanonError):
    """Raised when canonical definitions fail validation."""
    pass

class ProjectSpec(BaseModel):
    """
    Project-level metadata and configuration.
    Guarantees preservation of the user's original unadulterated story text.
    """
    project_id: str = Field(..., description="Stable unique project identifier")
    schema_version: str = Field(default="1.0.0", description="Story Bible schema version")
    bible_version: int = Field(default=1, description="Monotonic integer version of the Bible definition")
    title: str = Field(default="Untitled Comic", description="Project title")
    language: str = Field(default="ar", description="Primary project language code (e.g. 'ar', 'en')")
    reading_direction: Literal["rtl", "ltr"] = Field(default="rtl", description="Reading direction")
    user_story_text: Optional[str] = Field(
        default=None,
        description="Original immutable user-supplied story text; must never be silently altered or rewritten"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
    status: Literal["draft", "validated", "locked"] = Field(default="draft")

class StyleDefinition(BaseModel):
    """
    Approved visual identity and constraints for an InkLoop project.
    Stores project-level artistic decisions, not the full 60-group taxonomy catalogue.
    """
    style_id: str = Field(..., description="Stable style identifier (e.g. 'manga_ink_screentone')")
    version: int = Field(default=1, description="Version of the style definition")
    name: str = Field(..., description="Human-readable style name")
    medium: str = Field(..., description="Rendering medium (e.g. 'digital ink', 'traditional screentone')")
    rendering_approach: str = Field(..., description="Visual approach (e.g. 'black-and-white high contrast with screentone')")
    line_art_rules: List[str] = Field(default_factory=list, description="Rules governing line weight and contours")
    tonal_rules: List[str] = Field(default_factory=list, description="Rules for screentone density, hatching, and solid blacks")
    palette_or_screentone: Dict[str, Any] = Field(default_factory=dict, description="Screentone specifications or palette rules")
    background_detail_rules: str = Field(default="", description="Guidance on background density vs subject focus")
    lighting_constraints: List[str] = Field(default_factory=list, description="Canonical lighting rules")
    positive_constraints: List[str] = Field(default_factory=list, description="Required positive visual tokens/rules")
    negative_constraints: List[str] = Field(default_factory=list, description="Forbidden elements (e.g. 'no color', 'no 3D render')")
    reference_assets: List[AssetRef] = Field(default_factory=list, description="Approved style reference assets")
    provenance: Optional[Dict[str, Any]] = Field(default=None, description="Creation provenance and asset author")

class CharacterDefinition(BaseModel):
    """
    Canonical character specification.
    Defines identity, invariants, required/optional checklist attributes, and approved reference sheets.
    """
    character_id: str = Field(..., description="Stable character ID in lowercase (e.g. 'nour')")
    name: str = Field(..., description="Canonical character display name")
    entity_kind: str = Field(default="unspecified being", description="Open vocabulary for any creator-defined kind of being")
    morphology: str = Field(default="", description="Declared form/body plan; absent human features must not be inferred")
    surface_description: str = Field(default="", description="Declared material, color, texture, and pattern")
    physical_height_cm: Optional[float] = Field(default=None, description="Canonical physical height in centimeters (e.g. 25.0, 175.0)")
    proportion_constraints: Optional[Dict[str, Any]] = Field(default=None, description="Structured proportion guidelines (e.g. {'head_ratio': 0.60, 'body_ratio': 0.40})")
    description: str = Field(default="", description="Narrative role, personality, and background")
    canon_version: int = Field(default=1, description="Version of the character canon")
    attributes: List[AttributeCheck] = Field(..., description="Machine-readable checklist attributes for verifier")
    tolerances: Tolerances = Field(default_factory=lambda: Tolerances(face_check_applicable=False), description="Verification tolerances; face-specific checks are opt-in for profiles with declared face landmarks")
    clothing_attributes: List[str] = Field(default_factory=list, description="Canonical clothing traits")
    clothing_traits: List[str] = Field(default_factory=list, description="Alias for clothing_attributes")
    outfits: Dict[str, Any] = Field(default_factory=dict, description="Declared outfits for this character")
    visual_invariants: List[str] = Field(default_factory=list, description="Invariants that must never change")
    restrictions: List[str] = Field(default_factory=list, description="Character-specific negative constraints")
    reference_assets: List[AssetRef] = Field(default_factory=list, description="Approved multi-view reference sheets")
    expressions: Dict[str, str] = Field(default_factory=dict, description="Map of supported expression name to asset ID")
    views: Dict[str, str] = Field(default_factory=dict, description="Map of supported camera view to asset ID")
    approval_status: Literal["approved", "draft", "deprecated"] = Field(default="approved", description="Approval state")

    @field_validator("character_id")
    @classmethod
    def validate_character_id(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not v_clean or not v_clean.isalnum() and "_" not in v_clean:
            raise ValueError(f"Invalid character_id '{v}': must be lowercase alphanumeric with underscores")
        return v_clean

    def get_attribute(self, attr_id: str) -> Optional[AttributeCheck]:
        """Find an attribute by its identifier."""
        for attr in self.attributes:
            if attr.id == attr_id:
                return attr
        return None

    def to_character_spec(self) -> CharacterSpec:
        """Converts to existing CharacterSpec schema for direct compatibility with M0 verifiers and orchestrator."""
        return CharacterSpec(
            id=self.character_id,
            name=self.name,
            entity_kind=self.entity_kind,
            morphology=self.morphology,
            surface_description=self.surface_description,
            physical_height_cm=self.physical_height_cm,
            proportion_constraints=self.proportion_constraints,
            attributes=self.attributes,
            tolerances=self.tolerances,
            visual_invariants=list(self.visual_invariants),
            restrictions=list(self.restrictions),
            clothing_attributes=list(self.clothing_attributes),
        )

class LocationDefinition(BaseModel):
    """Canonical location specification for recurring environments."""
    location_id: str = Field(..., description="Stable location identifier (e.g. 'cafe_interior')")
    version: int = Field(default=1, description="Specification version")
    name: str = Field(..., description="Canonical location name")
    description: str = Field(..., description="Detailed architectural and environmental description")
    required_attributes: List[str] = Field(default_factory=list, description="Mandatory visual features")
    reference_assets: List[AssetRef] = Field(default_factory=list, description="Approved location reference images")
    relationships: List[str] = Field(default_factory=list, description="Relationships to other declared entities")
    permitted_variations: List[str] = Field(default_factory=list, description="Explicitly permitted variations")
    state_relevant_properties: List[str] = Field(
        default_factory=lambda: ["time_of_day", "weather", "lighting", "damage_state"],
        description="Allowed mutable state fields for this location"
    )
    approval_status: Literal["approved", "draft", "deprecated"] = Field(default="approved")

    @field_validator("location_id")
    @classmethod
    def validate_location_id(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not v_clean:
            raise ValueError("location_id cannot be empty")
        return v_clean

class PropIdentityFeature(BaseModel):
    """Evidence-linked object trait, kept separate from scene-specific state."""
    feature_id: str
    label: str
    description: str
    stability: Literal["stable", "state", "unknown"] = "stable"
    provenance: Literal["user_authored", "model_observation", "model_inference", "unknown"] = "unknown"
    evidence_asset_ids: List[str] = Field(default_factory=list)


class PropAnalysisRecord(BaseModel):
    """Honest analysis provenance for an object reference set."""
    analysis_status: Literal["unknown", "completed", "partial", "not_run"] = "not_run"
    analysis_source: str = "unknown"
    model_id: Optional[str] = None
    observed_summary: str = ""
    inferred_purpose: str = ""
    unknown_or_occluded: List[str] = Field(default_factory=list)
    creator_authored_facts: List[str] = Field(default_factory=list)
    analyzed_at: Optional[str] = None


class PropDefinition(BaseModel):
    """Canonical prop specification for recurring narrative objects."""
    prop_id: str = Field(..., description="Stable prop identifier (e.g. 'brass_key')")
    version: int = Field(default=1, description="Specification version")
    name: str = Field(..., description="Canonical prop name")
    description: str = Field(..., description="Physical and visual description of the prop")
    required_attributes: List[str] = Field(default_factory=list, description="Mandatory visual attributes")
    reference_assets: List[AssetRef] = Field(default_factory=list, description="Approved visual references")
    form_and_proportions: str = Field(default="", description="Observed object silhouette, construction, and relative proportions")
    materials: List[str] = Field(default_factory=list, description="Observed or creator-authored surface materials")
    palette: List[str] = Field(default_factory=list, description="Observed or creator-authored colors")
    components: List[str] = Field(default_factory=list, description="Distinct parts and how they connect")
    distinctive_marks: List[str] = Field(default_factory=list, description="Engravings, patterns, attachments, or identifying marks")
    stable_invariants: List[str] = Field(default_factory=list, description="Object identity traits preserved across scenes")
    allowed_states: List[str] = Field(default_factory=list, description="Allowed state changes that do not change object identity")
    uncertain_traits: List[str] = Field(default_factory=list, description="Traits not established by available references")
    identity_features: List[PropIdentityFeature] = Field(default_factory=list, description="Evidence-backed object observations and inferences")
    trait_provenance: Dict[str, Literal["user_authored", "model_observation", "model_inference", "unknown"]] = Field(default_factory=dict, description="Source for each editable identity trait field")
    analysis: PropAnalysisRecord = Field(default_factory=PropAnalysisRecord)
    creator_notes: str = Field(default="", description="Creator-authored details kept separate from image analysis")
    draft_origin: Literal["creator", "object_studio", "agent_story_plan", "unknown"] = "unknown"
    draft_job_id: Optional[str] = Field(default=None, description="Owning resumable story-production job for agent-created drafts")
    associated_character_ids: List[str] = Field(default_factory=list, description="Characters who own or use this prop")
    permitted_variations: List[str] = Field(default_factory=list, description="Explicitly permitted variations")
    relationships: List[str] = Field(default_factory=list, description="Relationships to other declared entities")
    state_relevant_properties: List[str] = Field(
        default_factory=lambda: ["holder_id", "condition", "location_id"],
        description="Allowed mutable state fields for this prop"
    )
    approval_status: Literal["approved", "draft", "deprecated"] = Field(default="approved")

    @field_validator("prop_id")
    @classmethod
    def validate_prop_id(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not v_clean:
            raise ValueError("prop_id cannot be empty")
        return v_clean

class CanonMutationProposal(BaseModel):
    """
    Explicit proposal to mutate canonical specifications.
    Proposals require approval; they never mutate canon automatically.
    """
    proposal_id: str = Field(..., description="Unique proposal identifier")
    project_id: str = Field(..., description="Target project ID")
    target_type: Literal["character", "style", "location", "prop"] = Field(..., description="Target entity category")
    target_id: str = Field(..., description="Target entity identifier")
    change_description: str = Field(..., description="Reason and description of proposed modification")
    proposed_changes: Dict[str, Any] = Field(..., description="Key-value mapping of proposed changes")
    status: Literal["pending", "approved", "rejected"] = Field(default="pending")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    approved_at: Optional[str] = Field(default=None, description="ISO 8601 approval timestamp")
    approved_by: Optional[str] = Field(default=None, description="User or role authorizing the mutation")
    rejection_reason: Optional[str] = Field(default=None, description="Reason for rejection if status is rejected")
    rejection_reason: Optional[str] = Field(default=None, description="Reason if proposal was rejected")

class ReadOnlyDict(dict):
    """
    Immutable mapping used by CanonSnapshot to protect entity registries
    from direct item assignment, in-place deletion, clearing, or mutation.
    Returns deep copies of stored models and collections on item access to ensure
    nested mutations cannot alter the snapshot's internal canonical state.
    """
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        super().__init__(data or {})

    def __getitem__(self, key: str) -> Any:
        val = super().__getitem__(key)
        if hasattr(val, "model_copy"):
            return val.model_copy(deep=True)
        elif isinstance(val, (dict, list, set)):
            import copy
            return copy.deepcopy(val)
        return val

    def get(self, key: str, default: Any = None) -> Any:
        if key in self:
            return self[key]
        return default

    def values(self) -> List[Any]:
        return [self[k] for k in self.keys()]

    def items(self) -> List[tuple[str, Any]]:
        return [(k, self[k]) for k in self.keys()]

    def copy(self) -> Dict[str, Any]:
        return {k: self[k] for k in self.keys()}

    def __copy__(self) -> "ReadOnlyDict":
        return ReadOnlyDict({k: self[k] for k in self.keys()})

    def __deepcopy__(self, memo: Any) -> "ReadOnlyDict":
        return ReadOnlyDict({k: self[k] for k in self.keys()})

    def __setitem__(self, key: str, value: Any) -> None:
        raise UnauthorizedMutationError(
            f"Cannot modify CanonSnapshot mapping: canon is immutable. "
            f"Attempted to set key '{key}'. Canonical changes must use propose_canon_mutation and apply_canon_mutation."
        )

    def __delitem__(self, key: str) -> None:
        raise UnauthorizedMutationError(
            f"Cannot modify CanonSnapshot mapping: canon is immutable. "
            f"Attempted to delete key '{key}'. Canonical changes must use propose_canon_mutation and apply_canon_mutation."
        )

    def clear(self) -> None:
        raise UnauthorizedMutationError(
            "Cannot modify CanonSnapshot mapping: canon is immutable. Attempted to clear mapping."
        )

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise UnauthorizedMutationError(
            "Cannot modify CanonSnapshot mapping: canon is immutable. Attempted to pop item."
        )

    def popitem(self) -> Any:
        raise UnauthorizedMutationError(
            "Cannot modify CanonSnapshot mapping: canon is immutable. Attempted to pop item."
        )

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise UnauthorizedMutationError(
            "Cannot modify CanonSnapshot mapping: canon is immutable. Attempted to update mapping."
        )

    def setdefault(self, *args: Any, **kwargs: Any) -> Any:
        raise UnauthorizedMutationError(
            "Cannot modify CanonSnapshot mapping: canon is immutable. Attempted to call setdefault."
        )

    def __ior__(self, other: Any) -> "ReadOnlyDict":
        raise UnauthorizedMutationError(
            "Cannot modify CanonSnapshot mapping: canon is immutable. "
            "Attempted in-place |= merge. Canonical changes must use propose_canon_mutation and apply_canon_mutation."
        )


class CanonSnapshot(BaseModel):
    """
    Deterministic, deeply immutable snapshot of a project's canon at a specific version.
    Includes a cryptographic content hash computed over sorted canonical definitions.
    Guarantees that no external consumer can mutate canonical state either through getter methods,
    public dictionary access, nested attribute mutation, or input reference aliasing.
    """
    project_id: str
    schema_version: str
    bible_version: int
    canon_hash: str = Field(..., description="SHA-256 hash of canonical definitions")
    created_at: str
    style: StyleDefinition
    characters: Dict[str, CharacterDefinition]
    locations: Dict[str, LocationDefinition]
    props: Dict[str, PropDefinition]

    model_config = ConfigDict(frozen=True)

    def model_post_init(self, __context: Any) -> None:
        """Enforces deep isolation by deep-copying all nested mutable models and wrapping registries in ReadOnlyDict."""
        object.__setattr__(self, "style", self.style.model_copy(deep=True))
        object.__setattr__(
            self,
            "characters",
            ReadOnlyDict({k: v.model_copy(deep=True) for k, v in self.characters.items()})
        )
        object.__setattr__(
            self,
            "locations",
            ReadOnlyDict({k: v.model_copy(deep=True) for k, v in self.locations.items()})
        )
        object.__setattr__(
            self,
            "props",
            ReadOnlyDict({k: v.model_copy(deep=True) for k, v in self.props.items()})
        )

    def __getattribute__(self, name: str) -> Any:
        val = super().__getattribute__(name)
        if name == "style" and hasattr(val, "model_copy"):
            return val.model_copy(deep=True)
        return val

    def __setattr__(self, name: str, value: Any) -> None:
        raise UnauthorizedMutationError(
            f"CanonSnapshot is immutable. Attempted to mutate '{name}' in Canon v{self.bible_version} "
            f"({self.canon_hash[:12]}...). Canonical changes must use propose_canon_mutation and apply_canon_mutation."
        )

    def __delattr__(self, name: str) -> None:
        raise UnauthorizedMutationError(
            f"CanonSnapshot is immutable. Attempted to delete '{name}' in Canon v{self.bible_version} "
            f"({self.canon_hash[:12]}...). Canonical changes must use propose_canon_mutation and apply_canon_mutation."
        )

    def is_entity_declared(self, entity_type: str, entity_id: str) -> bool:
        """Checks if a character, location, or prop has been canonically declared."""
        cid = entity_id.lower().strip()
        if entity_type == "character":
            return cid in self.characters
        elif entity_type == "location":
            return cid in self.locations
        elif entity_type == "prop":
            return cid in self.props
        elif entity_type in ("world", "scene", "environment"):
            return True
        return False

    def get_character(self, character_id: str) -> CharacterDefinition:
        """Retrieves a deep-copied character definition to preserve snapshot immutability."""
        cid = character_id.lower().strip()
        if cid not in self.characters:
            raise CanonError(f"Character '{character_id}' not found in Canon v{self.bible_version}")
        return self.characters[cid].model_copy(deep=True)

    def get_location(self, location_id: str) -> LocationDefinition:
        """Retrieves a deep-copied location definition to preserve snapshot immutability."""
        lid = location_id.lower().strip()
        if lid not in self.locations:
            raise CanonError(f"Location '{location_id}' not found in Canon v{self.bible_version}")
        return self.locations[lid].model_copy(deep=True)

    def get_prop(self, prop_id: str) -> PropDefinition:
        """Retrieves a deep-copied prop definition to preserve snapshot immutability."""
        pid = prop_id.lower().strip()
        if pid not in self.props:
            raise CanonError(f"Prop '{prop_id}' not found in Canon v{self.bible_version}")
        return self.props[pid].model_copy(deep=True)

    def get_style(self) -> StyleDefinition:
        """Retrieves a deep-copied style definition to preserve snapshot immutability."""
        return self.style.model_copy(deep=True)

    @classmethod
    def compute_canon_hash(
        cls,
        style: StyleDefinition,
        characters: Dict[str, CharacterDefinition],
        locations: Dict[str, LocationDefinition],
        props: Dict[str, PropDefinition]
    ) -> str:
        """Computes deterministic SHA-256 digest of canonical entities."""
        canonical_dict = {
            "style": style.model_dump(mode="json"),
            "characters": {k: v.model_dump(mode="json") for k, v in sorted(characters.items())},
            "locations": {k: v.model_dump(mode="json") for k, v in sorted(locations.items())},
            "props": {k: v.model_dump(mode="json") for k, v in sorted(props.items())},
        }
        serialized = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_story_bible(
        self,
        language: str = "ar",
        reading_direction: Literal["rtl", "ltr"] = "rtl",
        user_story_text: Optional[str] = None
    ) -> Any:
        """
        Reconstructs a fully functional StoryBible from this immutable snapshot.
        Guarantees that the reconstructed bible's canon snapshot hash matches this snapshot's hash.
        """
        from app.project.bible import StoryBible
        return StoryBible(
            project_id=self.project_id,
            schema_version=self.schema_version,
            bible_version=self.bible_version,
            created_at=self.created_at,
            updated_at=self.created_at,
            status="validated",
            language=language,
            reading_direction=reading_direction,
            user_story_text=user_story_text,
            style=self.style.model_copy(deep=True),
            characters={k: v.model_copy(deep=True) for k, v in self.characters.items()},
            locations={k: v.model_copy(deep=True) for k, v in self.locations.items()},
            props={k: v.model_copy(deep=True) for k, v in self.props.items()}
        )


# Aliases for cross-module compatibility
StyleBible = StyleDefinition
LocationSpec = LocationDefinition
PropSpec = PropDefinition

