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
    description: str = Field(default="", description="Narrative role, personality, and background")
    canon_version: int = Field(default=1, description="Version of the character canon")
    attributes: List[AttributeCheck] = Field(..., description="Machine-readable checklist attributes for verifier")
    tolerances: Tolerances = Field(default_factory=Tolerances, description="Verification tolerances (e.g. min face px)")
    clothing_attributes: List[str] = Field(default_factory=list, description="Canonical clothing traits")
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
        """Converts to existing CharacterSpec schema for direct compatibility with M0 verifiers."""
        return CharacterSpec(
            id=self.character_id,
            attributes=self.attributes,
            tolerances=self.tolerances
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

class PropDefinition(BaseModel):
    """Canonical prop specification for recurring narrative objects."""
    prop_id: str = Field(..., description="Stable prop identifier (e.g. 'brass_key')")
    version: int = Field(default=1, description="Specification version")
    name: str = Field(..., description="Canonical prop name")
    description: str = Field(..., description="Physical and visual description of the prop")
    required_attributes: List[str] = Field(default_factory=list, description="Mandatory visual attributes")
    reference_assets: List[AssetRef] = Field(default_factory=list, description="Approved visual references")
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

class CanonSnapshot(BaseModel):
    """
    Deterministic, immutable snapshot of a project's canon at a specific version.
    Includes a cryptographic content hash computed over sorted canonical definitions.
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

    def __setattr__(self, name: str, value: Any) -> None:
        raise UnauthorizedMutationError(
            f"CanonSnapshot is immutable. Attempted to mutate '{name}' in Canon v{self.bible_version} "
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
        """Retrieves a character definition or raises CanonError."""
        cid = character_id.lower().strip()
        if cid not in self.characters:
            raise CanonError(f"Character '{character_id}' not found in Canon v{self.bible_version}")
        return self.characters[cid]

    def get_location(self, location_id: str) -> LocationDefinition:
        """Retrieves a location definition or raises CanonError."""
        lid = location_id.lower().strip()
        if lid not in self.locations:
            raise CanonError(f"Location '{location_id}' not found in Canon v{self.bible_version}")
        return self.locations[lid]

    def get_prop(self, prop_id: str) -> PropDefinition:
        """Retrieves a prop definition or raises CanonError."""
        pid = prop_id.lower().strip()
        if pid not in self.props:
            raise CanonError(f"Prop '{prop_id}' not found in Canon v{self.bible_version}")
        return self.props[pid]

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
