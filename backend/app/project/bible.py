"""
Story Bible Service for InkLoop.
Provides file-based, deterministic loading, saving, validation, canon snapshots,
and state timeline management.
Acts as the external source of truth for all production engines.
"""
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Literal, Union, Any, Set
from pydantic import BaseModel, Field, field_validator

from app.schemas import CharacterSpec, AttributeCheck, Tolerances
from app.project.asset_refs import (
    AssetRef,
    validate_asset_ref,
    AssetIntegrityError,
    AssetNotFoundError,
    AssetHashMismatchError,
    PathTraversalError
)
from app.project.canon import (
    ProjectSpec,
    StyleDefinition,
    CharacterDefinition,
    LocationDefinition,
    PropDefinition,
    CanonMutationProposal,
    CanonSnapshot,
    CanonError,
    UnauthorizedMutationError,
    CanonValidationError
)
from app.project.story_state import (
    StoryStateEvent,
    StateResolutionResult,
    resolve_timeline_state,
    validate_event_against_bible,
    StateTimelineError,
    InvalidStateEventError,
    UndeclaredEntityError,
    ContradictoryTransitionError,
    DuplicateEventConflictError
)

SUPPORTED_SCHEMA_VERSIONS = {"1.0.0"}

class StoryBibleError(Exception):
    """Base exception for Story Bible errors."""
    pass

class UnsupportedSchemaVersionError(StoryBibleError):
    """Raised when encountering an unsupported schema version."""
    pass

class VersionConflictError(StoryBibleError):
    """Raised when an optimistic concurrency version check fails."""
    pass

class EntityNotFoundError(StoryBibleError):
    """Raised when a requested entity does not exist in the Bible."""
    pass

class MalformedBibleError(StoryBibleError):
    """Raised when Bible JSON is corrupt or invalid."""
    pass

class CanonMutationError(StoryBibleError):
    """Raised when a canon mutation cannot be applied."""
    pass

class ValidationReport(BaseModel):
    """Detailed report from Story Bible validation."""
    is_valid: bool
    schema_version: str
    bible_version: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_assets_count: int = 0

class StoryBible(BaseModel):
    """
    The master Story Bible record.
    External structured source of truth for characters, visual style, locations, and props.
    """
    project_id: str = Field(..., description="Unique project identifier")
    schema_version: str = Field(default="1.0.0", description="Schema version of the Bible specification")
    bible_version: int = Field(default=1, description="Monotonic integer version of the Bible definition")
    created_at: str = Field(..., description="ISO 8601 timestamp of creation")
    updated_at: str = Field(..., description="ISO 8601 timestamp of last update")
    status: Literal["draft", "validated", "locked"] = Field(default="draft", description="Lifecycle status")
    language: str = Field(default="ar", description="Primary project language (e.g. ar, en)")
    reading_direction: Literal["rtl", "ltr"] = Field(default="rtl", description="Reading direction")
    user_story_text: Optional[str] = Field(
        default=None,
        description="Original immutable user-supplied story text; preserved exactly without modification"
    )
    style: StyleDefinition = Field(..., description="Canonical style definition")
    characters: Dict[str, CharacterDefinition] = Field(..., description="Canonical character registry (id -> spec)")
    locations: Dict[str, LocationDefinition] = Field(default_factory=dict, description="Canonical location registry")
    props: Dict[str, PropDefinition] = Field(default_factory=dict, description="Canonical prop registry")

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v not in SUPPORTED_SCHEMA_VERSIONS:
            raise UnsupportedSchemaVersionError(
                f"Unsupported Story Bible schema version '{v}'. Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
        return v

    def get_canon_snapshot(self) -> CanonSnapshot:
        """Generates a deterministic, immutable CanonSnapshot with cryptographic content hash."""
        canon_hash = CanonSnapshot.compute_canon_hash(
            style=self.style,
            characters=self.characters,
            locations=self.locations,
            props=self.props
        )
        return CanonSnapshot(
            project_id=self.project_id,
            schema_version=self.schema_version,
            bible_version=self.bible_version,
            canon_hash=canon_hash,
            created_at=self.updated_at,
            style=self.style,
            characters=self.characters,
            locations=self.locations,
            props=self.props
        )

    def to_project_spec(self) -> ProjectSpec:
        """Extracts high-level project metadata and configuration."""
        return ProjectSpec(
            project_id=self.project_id,
            schema_version=self.schema_version,
            bible_version=self.bible_version,
            title=getattr(self, "title", "Untitled Comic"),
            language=self.language,
            reading_direction=self.reading_direction,
            user_story_text=self.user_story_text,
            created_at=self.created_at,
            updated_at=self.updated_at,
            status=self.status
        )

    def to_orchestrator_bible(self) -> Any:
        """
        Bridges the rich Story Bible to the simplified Orchestrator StoryBible contract in app.schemas,
        ensuring 100% interoperability with Agent 1's orchestrator and context builder.
        """
        from app.schemas import (
            StoryBible as SchemasStoryBible,
            StyleBible as SchemasStyleBible,
            ReferenceAsset as SchemasReferenceAsset
        )
        schemas_style = SchemasStyleBible(
            id=self.style.style_id,
            name=self.style.name,
            medium=self.style.medium,
            line_and_tone=self.style.rendering_approach,
            palette=str(self.style.palette_or_screentone),
            negative_rules=self.style.negative_constraints,
            version=str(self.style.version)
        )

        char_specs = {}
        char_assets = {}
        for cid, char in self.characters.items():
            char_specs[cid] = char.to_character_spec()
            if char.reference_assets:
                primary_asset = char.reference_assets[0]
                char_assets[cid] = SchemasReferenceAsset(
                    asset_id=primary_asset.asset_id,
                    file_path=primary_asset.path,
                    content_hash=primary_asset.expected_hash,
                    mime_type=primary_asset.mime_type,
                    description=primary_asset.provenance.get("description") if primary_asset.provenance else None
                )

        return SchemasStoryBible(
            bible_id=self.project_id,
            version=str(self.bible_version),
            project_id=self.project_id,
            style=schemas_style,
            characters=char_specs,
            character_assets=char_assets,
            story_facts=self.style.positive_constraints
        )

    def validate(
        self,
        project_root: Optional[Path] = None,
        verify_asset_hashes: bool = True
    ) -> ValidationReport:
        """Validates all entity references and asset integrity."""
        errors: List[str] = []
        warnings: List[str] = []
        validated_assets = 0

        # Validate schema version
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            errors.append(f"Unsupported schema version: '{self.schema_version}'")

        # Validate style references
        all_assets: List[AssetRef] = list(self.style.reference_assets)

        # Validate characters
        if not self.characters:
            warnings.append("Story Bible has no characters declared")
        for char_id, char in self.characters.items():
            if char_id != char.character_id:
                errors.append(f"Character key '{char_id}' does not match character_id '{char.character_id}'")
            if not char.attributes:
                errors.append(f"Character '{char_id}' has no attributes defined")
            all_assets.extend(char.reference_assets)

        # Validate locations
        for loc_id, loc in self.locations.items():
            if loc_id != loc.location_id:
                errors.append(f"Location key '{loc_id}' does not match location_id '{loc.location_id}'")
            all_assets.extend(loc.reference_assets)

        # Validate props
        for prop_id, prop in self.props.items():
            if prop_id != prop.prop_id:
                errors.append(f"Prop key '{prop_id}' does not match prop_id '{prop.prop_id}'")
            all_assets.extend(prop.reference_assets)

        # Validate assets on disk if project_root provided
        if project_root is not None:
            root_path = Path(project_root).resolve()
            for asset in all_assets:
                try:
                    validate_asset_ref(asset, root_path, verify_hash=verify_asset_hashes)
                    validated_assets += 1
                except (PathTraversalError, AssetNotFoundError, AssetHashMismatchError, AssetIntegrityError) as e:
                    errors.append(f"Asset validation failed for '{asset.asset_id}': {str(e)}")

        return ValidationReport(
            is_valid=(len(errors) == 0),
            schema_version=self.schema_version,
            bible_version=self.bible_version,
            errors=errors,
            warnings=warnings,
            validated_assets_count=validated_assets
        )

    def get_character(self, character_id: str) -> CharacterDefinition:
        char_id = character_id.lower()
        if char_id not in self.characters:
            raise EntityNotFoundError(f"Character '{character_id}' not found in Story Bible")
        return self.characters[char_id]

    def get_location(self, location_id: str) -> LocationDefinition:
        loc_id = location_id.lower()
        if loc_id not in self.locations:
            raise EntityNotFoundError(f"Location '{location_id}' not found in Story Bible")
        return self.locations[loc_id]

    def get_prop(self, prop_id: str) -> PropDefinition:
        p_id = prop_id.lower()
        if p_id not in self.props:
            raise EntityNotFoundError(f"Prop '{prop_id}' not found in Story Bible")
        return self.props[p_id]


# --- Persistence and Storage Helpers ---

def resolve_bible_paths(project_id_or_path: Union[str, Path]) -> tuple[Path, Path]:
    """
    Resolves project base directory and bible.json path.
    Accepts:
    1. Direct path to a bible.json file
    2. Path to a project directory
    3. Project ID (resolved relative to current working directory 'runs/<project_id>' or 'projects/<project_id>')
    """
    target = Path(project_id_or_path)
    if target.is_file() and target.name.endswith(".json"):
        return target.parent, target
    elif target.is_dir():
        return target, target / "bible.json"
    
    # Try common workspace conventions
    candidates = [
        Path.cwd() / "runs" / str(project_id_or_path),
        Path.cwd() / "projects" / str(project_id_or_path),
        Path.cwd() / str(project_id_or_path),
    ]
    for cand in candidates:
        if (cand / "bible.json").exists():
            return cand, cand / "bible.json"

    # Default to first candidate
    base_dir = candidates[0]
    return base_dir, base_dir / "bible.json"


def atomic_write_file(file_path: Path, content: str) -> None:
    """Writes content to file atomically using a temporary file and atomic rename."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_suffix(f".tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


# --- Public Service API Implementation ---

def load_bible(
    project_id_or_path: Union[str, Path],
    project_root: Optional[Path] = None
) -> StoryBible:
    """
    Loads and validates a StoryBible from disk.
    Rejects unsupported schema versions explicitly.
    """
    _, bible_file = resolve_bible_paths(project_id_or_path)
    if not bible_file.is_file():
        raise StoryBibleError(f"Story Bible file not found at '{bible_file}'")

    try:
        with open(bible_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise MalformedBibleError(f"Malformed JSON in Story Bible at '{bible_file}': {str(e)}")

    # Explicit schema version gate
    schema_ver = data.get("schema_version")
    if schema_ver not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSchemaVersionError(
            f"Unsupported Story Bible schema version '{schema_ver}'. Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    try:
        bible = StoryBible.model_validate(data)
    except Exception as e:
        raise MalformedBibleError(f"Failed to validate Story Bible schema from '{bible_file}': {str(e)}")

    return bible


def validate_bible(
    bible: StoryBible,
    project_root: Optional[Path] = None,
    verify_asset_hashes: bool = True
) -> ValidationReport:
    """Validates the Story Bible against schema rules and asset integrity."""
    return bible.validate(project_root=project_root, verify_asset_hashes=verify_asset_hashes)


def save_bible(
    bible: StoryBible,
    target_path: Optional[Union[str, Path]] = None,
    expected_version: Optional[int] = None
) -> Path:
    """
    Atomically saves a Story Bible to disk.
    Enforces optimistic concurrency checks if expected_version is provided.
    Preserves versioned canon snapshots in '<dir>/snapshots/<canon_hash>.json'.
    """
    if target_path:
        base_dir, bible_file = resolve_bible_paths(target_path)
    else:
        base_dir, bible_file = resolve_bible_paths(bible.project_id)

    # Concurrency / version check
    if expected_version is not None and bible_file.exists():
        existing = load_bible(bible_file)
        if existing.bible_version != expected_version:
            raise VersionConflictError(
                f"Version conflict on save: expected version {expected_version}, but disk has {existing.bible_version}"
            )

    # Bump update timestamp
    bible.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Save master bible JSON atomically
    bible_json = json.dumps(bible.model_dump(mode="json"), indent=2, sort_keys=True)
    atomic_write_file(bible_file, bible_json)

    # Save immutable canon snapshot
    snapshot = bible.get_canon_snapshot()
    snapshots_dir = base_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshots_dir / f"snapshot_v{bible.bible_version}_{snapshot.canon_hash[:12]}.json"
    snapshot_json = json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True)
    atomic_write_file(snapshot_file, snapshot_json)

    return bible_file


def get_canon_snapshot(
    project_id_or_path: Union[str, Path],
    version: Optional[int] = None
) -> CanonSnapshot:
    """Returns the immutable CanonSnapshot for the given project, optionally for a specific version."""
    bible = load_bible(project_id_or_path)
    if version is not None and version != bible.bible_version:
        base_dir, _ = resolve_bible_paths(project_id_or_path)
        snapshots_dir = base_dir / "snapshots"
        if snapshots_dir.is_dir():
            for f in snapshots_dir.glob(f"snapshot_v{version}_*.json"):
                with open(f, "r", encoding="utf-8") as sf:
                    return CanonSnapshot.model_validate(json.load(sf))
        raise EntityNotFoundError(f"Canon snapshot for version {version} not found in project '{bible.project_id}'")

    return bible.get_canon_snapshot()


def get_character_spec(
    project_id_or_path: Union[str, Path],
    character_id: str,
    canon_version: Optional[int] = None
) -> CharacterSpec:
    """Retrieves the machine-readable CharacterSpec for verifier and generator engines."""
    bible = load_bible(project_id_or_path)
    char = bible.get_character(character_id)
    if canon_version is not None and char.canon_version != canon_version:
        raise EntityNotFoundError(
            f"Character '{character_id}' version {canon_version} not found (current version: {char.canon_version})"
        )
    return char.to_character_spec()


def get_location_spec(
    project_id_or_path: Union[str, Path],
    location_id: str,
    canon_version: Optional[int] = None
) -> LocationDefinition:
    """Retrieves canonical specification for a recurring location."""
    bible = load_bible(project_id_or_path)
    loc = bible.get_location(location_id)
    if canon_version is not None and loc.version != canon_version:
        raise EntityNotFoundError(
            f"Location '{location_id}' version {canon_version} not found (current version: {loc.version})"
        )
    return loc


def get_prop_spec(
    project_id_or_path: Union[str, Path],
    prop_id: str,
    canon_version: Optional[int] = None
) -> PropDefinition:
    """Retrieves canonical specification for a recurring prop."""
    bible = load_bible(project_id_or_path)
    prop = bible.get_prop(prop_id)
    if canon_version is not None and prop.version != canon_version:
        raise EntityNotFoundError(
            f"Prop '{prop_id}' version {canon_version} not found (current version: {prop.version})"
        )
    return prop


def append_state_event(
    project_id_or_path: Union[str, Path],
    event: StoryStateEvent
) -> StoryStateEvent:
    """
    Appends a validated story-state event to the project's append-only state timeline.
    Enforces entity declaration checks and state transition consistency.
    """
    base_dir, bible_file = resolve_bible_paths(project_id_or_path)
    bible = load_bible(bible_file)

    # 1. Validate against declared entities
    validate_event_against_bible(
        event=event,
        declared_characters=set(bible.characters.keys()),
        declared_locations=set(bible.locations.keys()),
        declared_props=set(bible.props.keys())
    )

    state_file = base_dir / "state.jsonl"
    existing_events: List[StoryStateEvent] = []
    if state_file.is_file():
        with open(state_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    existing_events.append(StoryStateEvent.model_validate_json(line_str))

    # 2. Check duplicate / transition validity
    all_events = existing_events + [event]
    resolve_timeline_state(all_events, strict_transitions=True)

    # 3. Append to state.jsonl
    line_to_append = event.model_dump_json() + "\n"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "a", encoding="utf-8") as f:
        f.write(line_to_append)
        f.flush()
        os.fsync(f.fileno())

    return event


def resolve_state(
    project_id_or_path: Union[str, Path],
    scene_id_or_panel_id: Optional[str] = None
) -> StateResolutionResult:
    """
    Deterministically resolves the effective narrative state for a specific scene or panel.
    Read-only: does not modify state.jsonl or StoryBible.
    """
    base_dir, _ = resolve_bible_paths(project_id_or_path)
    state_file = base_dir / "state.jsonl"
    if not state_file.is_file():
        return StateResolutionResult(
            target_scene_id=scene_id_or_panel_id,
            target_panel_id=scene_id_or_panel_id,
            effective_state={},
            contributing_events=[],
            unresolved_conflicts=[]
        )

    events: List[StoryStateEvent] = []
    with open(state_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                events.append(StoryStateEvent.model_validate_json(line_str))

    return resolve_timeline_state(
        events=events,
        target_scene_or_panel=scene_id_or_panel_id,
        strict_transitions=False
    )


def validate_state_transition(
    project_id_or_path: Union[str, Path],
    event: StoryStateEvent
) -> bool:
    """
    Tests whether a proposed state event can be applied validly without raising an error.
    """
    base_dir, bible_file = resolve_bible_paths(project_id_or_path)
    bible = load_bible(bible_file)

    try:
        validate_event_against_bible(
            event=event,
            declared_characters=set(bible.characters.keys()),
            declared_locations=set(bible.locations.keys()),
            declared_props=set(bible.props.keys())
        )
    except Exception:
        return False

    state_file = base_dir / "state.jsonl"
    existing_events: List[StoryStateEvent] = []
    if state_file.is_file():
        with open(state_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    existing_events.append(StoryStateEvent.model_validate_json(line_str))

    try:
        resolve_timeline_state(existing_events + [event], strict_transitions=True)
        return True
    except Exception:
        return False


def propose_canon_mutation(
    project_id_or_path: Union[str, Path],
    proposal: CanonMutationProposal
) -> CanonMutationProposal:
    """
    Creates an explicit proposal to modify canonical specifications or declare new entities.
    Does NOT modify canonical data; logs the proposal for user approval.
    """
    base_dir, bible_file = resolve_bible_paths(project_id_or_path)
    bible = load_bible(bible_file)

    action = proposal.proposed_changes.get("action", "update")
    if action == "update":
        if proposal.target_type == "character" and proposal.target_id not in bible.characters:
            raise EntityNotFoundError(f"Target character '{proposal.target_id}' not found for mutation")
        elif proposal.target_type == "location" and proposal.target_id not in bible.locations:
            raise EntityNotFoundError(f"Target location '{proposal.target_id}' not found for mutation")
        elif proposal.target_type == "prop" and proposal.target_id not in bible.props:
            raise EntityNotFoundError(f"Target prop '{proposal.target_id}' not found for mutation")
        elif proposal.target_type == "style" and proposal.target_id != bible.style.style_id:
            raise EntityNotFoundError(f"Target style '{proposal.target_id}' does not match project style '{bible.style.style_id}'")
    elif action == "add":
        if proposal.target_type == "character" and proposal.target_id in bible.characters:
            raise CanonMutationError(f"Cannot add character '{proposal.target_id}': already declared in canon")
        elif proposal.target_type == "location" and proposal.target_id in bible.locations:
            raise CanonMutationError(f"Cannot add location '{proposal.target_id}': already declared in canon")
        elif proposal.target_type == "prop" and proposal.target_id in bible.props:
            raise CanonMutationError(f"Cannot add prop '{proposal.target_id}': already declared in canon")

    proposals_file = base_dir / "canon_proposals.jsonl"
    proposals_file.parent.mkdir(parents=True, exist_ok=True)
    with open(proposals_file, "a", encoding="utf-8") as f:
        f.write(proposal.model_dump_json() + "\n")
        f.flush()
        os.fsync(f.fileno())

    return proposal


def apply_canon_mutation(
    project_id_or_path: Union[str, Path],
    proposal_id: str,
    approved_by: str
) -> StoryBible:
    """
    Explicit, versioned operation to apply an approved canon mutation proposal.
    Increments bible_version, updates entity canon_version, and records audit trail.
    """
    base_dir, bible_file = resolve_bible_paths(project_id_or_path)
    bible = load_bible(bible_file)

    proposals_file = base_dir / "canon_proposals.jsonl"
    if not proposals_file.is_file():
        raise CanonMutationError("No canon proposals file found")

    target_proposal: Optional[CanonMutationProposal] = None
    all_proposals: List[CanonMutationProposal] = []
    with open(proposals_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                p = CanonMutationProposal.model_validate_json(line.strip())
                if p.proposal_id == proposal_id:
                    target_proposal = p
                all_proposals.append(p)

    if target_proposal is None:
        raise CanonMutationError(f"Proposal '{proposal_id}' not found")

    if target_proposal.status != "pending":
        raise CanonMutationError(f"Proposal '{proposal_id}' already has status '{target_proposal.status}'")

    # Authorize proposal
    target_proposal.status = "approved"
    target_proposal.approved_by = approved_by
    target_proposal.approved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Rewrite proposals file atomically
    rewritten_proposals = "\n".join(p.model_dump_json() for p in all_proposals) + "\n"
    atomic_write_file(proposals_file, rewritten_proposals)

    # Apply changes to Bible and bump versions
    old_version = bible.bible_version
    bible.bible_version += 1

    action = target_proposal.proposed_changes.get("action", "update")
    if target_proposal.target_type == "character":
        if action == "add" or target_proposal.target_id not in bible.characters:
            char_data = dict(target_proposal.proposed_changes)
            char_data.pop("action", None)
            char_data["character_id"] = target_proposal.target_id
            char_data.setdefault("canon_version", 1)
            char_data.setdefault("name", target_proposal.target_id.capitalize())
            new_char = CharacterDefinition.model_validate(char_data)
            bible.characters[target_proposal.target_id] = new_char
        else:
            char = bible.characters[target_proposal.target_id]
            char.canon_version += 1
            for k, v in target_proposal.proposed_changes.items():
                if k != "action" and hasattr(char, k):
                    setattr(char, k, v)
    elif target_proposal.target_type == "location":
        if action == "add" or target_proposal.target_id not in bible.locations:
            loc_data = dict(target_proposal.proposed_changes)
            loc_data.pop("action", None)
            loc_data["location_id"] = target_proposal.target_id
            loc_data.setdefault("version", 1)
            loc_data.setdefault("name", target_proposal.target_id.capitalize())
            loc_data.setdefault("description", "Declared location")
            new_loc = LocationDefinition.model_validate(loc_data)
            bible.locations[target_proposal.target_id] = new_loc
        else:
            loc = bible.locations[target_proposal.target_id]
            loc.version += 1
            for k, v in target_proposal.proposed_changes.items():
                if k != "action" and hasattr(loc, k):
                    setattr(loc, k, v)
    elif target_proposal.target_type == "prop":
        if action == "add" or target_proposal.target_id not in bible.props:
            prop_data = dict(target_proposal.proposed_changes)
            prop_data.pop("action", None)
            prop_data["prop_id"] = target_proposal.target_id
            prop_data.setdefault("version", 1)
            prop_data.setdefault("name", target_proposal.target_id.capitalize())
            prop_data.setdefault("description", "Declared prop")
            new_prop = PropDefinition.model_validate(prop_data)
            bible.props[target_proposal.target_id] = new_prop
        else:
            prop = bible.props[target_proposal.target_id]
            prop.version += 1
            for k, v in target_proposal.proposed_changes.items():
                if k != "action" and hasattr(prop, k):
                    setattr(prop, k, v)
    elif target_proposal.target_type == "style":
        bible.style.version += 1
        for k, v in target_proposal.proposed_changes.items():
            if k != "action" and hasattr(bible.style, k):
                setattr(bible.style, k, v)

    save_bible(bible, target_path=base_dir, expected_version=old_version)
    return bible


def reject_canon_mutation(
    project_id_or_path: Union[str, Path],
    proposal_id: str,
    rejected_by: str,
    reason: Optional[str] = None
) -> CanonMutationProposal:
    """
    Explicitly marks a Canon mutation proposal as rejected.
    Leaves the active Story Bible and Canon untouched.
    """
    base_dir, _ = resolve_bible_paths(project_id_or_path)
    proposals_file = base_dir / "canon_proposals.jsonl"
    if not proposals_file.is_file():
        raise CanonMutationError("No canon proposals file found")

    target_proposal: Optional[CanonMutationProposal] = None
    all_proposals: List[CanonMutationProposal] = []
    with open(proposals_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                p = CanonMutationProposal.model_validate_json(line.strip())
                if p.proposal_id == proposal_id:
                    target_proposal = p
                all_proposals.append(p)

    if target_proposal is None:
        raise CanonMutationError(f"Proposal '{proposal_id}' not found")

    if target_proposal.status != "pending":
        raise CanonMutationError(f"Proposal '{proposal_id}' already has status '{target_proposal.status}'")

    target_proposal.status = "rejected"
    target_proposal.approved_by = rejected_by
    target_proposal.approved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if reason:
        target_proposal.change_description += f" [REJECTED: {reason}]"

    rewritten_proposals = "\n".join(p.model_dump_json() for p in all_proposals) + "\n"
    atomic_write_file(proposals_file, rewritten_proposals)
    return target_proposal

    save_bible(bible, target_path=base_dir, expected_version=old_version)
    return bible


def get_continuity_context(
    project_id_or_path: Union[str, Path],
    scene_id_or_panel_id: str,
    active_character_ids: List[str],
    location_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assembles canonical definitions and current state for the Continuity Packet builder.
    """
    bible = load_bible(project_id_or_path)
    state_res = resolve_state(project_id_or_path, scene_id_or_panel_id)

    characters_payload: Dict[str, Dict[str, Any]] = {}
    for cid in active_character_ids:
        char = bible.get_character(cid)
        entity_key = f"character:{cid.lower()}"
        char_state = state_res.effective_state.get(entity_key, {})
        characters_payload[cid] = {
            "spec": char.to_character_spec().model_dump(),
            "reference_assets": [a.model_dump() for a in char.reference_assets],
            "visual_invariants": char.visual_invariants,
            "clothing_attributes": char.clothing_attributes,
            "restrictions": char.restrictions,
            "current_state": char_state
        }

    location_payload: Optional[Dict[str, Any]] = None
    if location_id:
        loc = bible.get_location(location_id)
        loc_key = f"location:{location_id.lower()}"
        location_payload = {
            "location_id": loc.location_id,
            "name": loc.name,
            "description": loc.description,
            "required_attributes": loc.required_attributes,
            "reference_assets": [a.model_dump() for a in loc.reference_assets],
            "current_state": state_res.effective_state.get(loc_key, {})
        }

    world_state = state_res.effective_state.get("world:world", {})

    return {
        "project_id": bible.project_id,
        "bible_version": bible.bible_version,
        "style": bible.style.model_dump(),
        "scene_id_or_panel_id": scene_id_or_panel_id,
        "active_characters": characters_payload,
        "location": location_payload,
        "world_state": world_state,
        "negative_constraints": bible.style.negative_constraints
    }


def create_canonical_nour_bible(
    project_root: Path,
    project_id: str = "inkloop_m0_nour"
) -> StoryBible:
    """
    Factory creating a verified StoryBible with Nour M0 reference asset and checklist attributes.
    Preserves exact SHA-256 and checklist verified during Milestone 0.
    """
    nour_ref_path = "runs/m0_visual/reference/nour_reference.png"
    nour_ref_hash = "b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644"

    style_ref = AssetRef(
        asset_id="asset_nour_ref_anchor",
        path=nour_ref_path,
        asset_type="character_sheet",
        expected_hash=nour_ref_hash,
        mime_type="image/png",
        provenance={"model": "muse-image-1.0", "milestone": "m0"}
    )

    style = StyleDefinition(
        style_id="manga_ink_screentone",
        name="Black-and-White Manga Ink with Screentone",
        medium="digital ink",
        rendering_approach="black-and-white high contrast with screentone",
        line_art_rules=[
            "Crisp dark ink contours",
            "Variable line weights emphasizing silhouette",
            "Fine architectural detail hatching"
        ],
        tonal_rules=[
            "Pure solid blacks for deep shadows and dark garments",
            "Halftone screentone for mid-tones and atmosphere",
            "Clean white negative space"
        ],
        palette_or_screentone={"type": "monochrome_screentone", "default_density_pct": 30},
        background_detail_rules="Detailed background in establishing shots; simplified high-contrast focus during action",
        positive_constraints=["manga ink", "clean lines", "screentone shading"],
        negative_constraints=["no color", "no photorealism", "no 3D CGI", "no text", "no speech bubbles"],
        reference_assets=[style_ref]
    )

    nour = CharacterDefinition(
        character_id="nour",
        name="Nour",
        canon_version=1,
        attributes=[
            AttributeCheck(
                id="hair",
                text="short messy black hair, one white streak on the left",
                required=True
            ),
            AttributeCheck(
                id="glasses",
                text="round glasses",
                required=True
            ),
            AttributeCheck(
                id="jacket",
                text="oversized hooded jacket, lightning-bolt patch on chest",
                required=True
            ),
            AttributeCheck(
                id="scar",
                text="small scar on right cheek",
                required=False
            )
        ],
        tolerances=Tolerances(min_face_px_for_check=80),
        clothing_attributes=["oversized hooded jacket with lightning-bolt chest patch"],
        visual_invariants=[
            "white hair streak always on character's left side",
            "round wireframe glasses frames"
        ],
        restrictions=["never bare-eyed unless explicitly scripted in canon proposal"],
        reference_assets=[style_ref],
        approval_status="approved"
    )

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return StoryBible(
        project_id=project_id,
        schema_version="1.0.0",
        bible_version=1,
        created_at=now_iso,
        updated_at=now_iso,
        status="validated",
        style=style,
        characters={"nour": nour},
        locations={},
        props={}
    )
