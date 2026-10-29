"""
Story State Timeline and deterministic state resolution for InkLoop.
Manages append-only story state events, transition validation, and historical resolution.
Maintains strict separation between mutable narrative state and immutable canon.
"""
from typing import List, Dict, Optional, Literal, Any, Set
from pydantic import BaseModel, Field, field_validator

class StateTimelineError(Exception):
    """Base exception for story state timeline errors."""
    pass

class InvalidStateEventError(StateTimelineError):
    """Raised when an event fails schema or validation rules."""
    pass

class UndeclaredEntityError(StateTimelineError):
    """Raised when an event refers to an entity not declared in the Story Bible."""
    pass

class ContradictoryTransitionError(StateTimelineError):
    """Raised when a state event contradicts previous state or asserts an invalid transition."""
    pass

ContradictoryStateError = ContradictoryTransitionError

class DuplicateEventConflictError(StateTimelineError):
    """Raised when an event ID is duplicated with conflicting payload."""
    pass

class StoryStateEvent(BaseModel):
    """
    Append-only record of a narrative state transition.
    Captures what is currently true in the story without rewriting canon.
    """
    event_id: str = Field(..., description="Unique event identifier (e.g. UUID)")
    sequence_number: int = Field(..., description="Strictly monotonic integer sequence order")
    scene_id: str = Field(..., description="Scene identifier (e.g. 'scene_01')")
    panel_id: str = Field(..., description="Panel identifier (e.g. 'scene_01_p1' or 'p1')")
    entity_type: Literal["character", "location", "prop", "world"] = Field(..., description="Target entity category")
    entity_id: str = Field(..., description="Declared entity ID or 'world'")
    property_path: str = Field(..., description="Dot-delimited property path (e.g. 'clothing.jacket_state', 'held_props')")
    previous_value: Optional[Any] = Field(default=None, description="Expected previous value when known")
    new_value: Any = Field(..., description="New value assigned to the property")
    source_ref: Optional[str] = Field(default=None, description="Story beat or script source producing this event")
    timestamp: str = Field(..., description="ISO 8601 timestamp of event creation")
    schema_version: str = Field(default="1.0.0", description="Event schema version")

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("event_id cannot be empty")
        return clean

    @field_validator("sequence_number")
    @classmethod
    def validate_sequence_number(cls, v: int) -> int:
        if v < 0:
            raise ValueError("sequence_number must be non-negative")
        return v

    @field_validator("property_path")
    @classmethod
    def validate_property_path(cls, v: str) -> str:
        clean = v.strip()
        if not clean or ".." in clean or clean.startswith(".") or clean.endswith("."):
            raise ValueError(f"Invalid property_path '{v}': must be valid dot-delimited string")
        return clean

class StateResolutionResult(BaseModel):
    """
    The effective state resolved for a specific scene or panel,
    along with an explanation ledger of contributing events.
    """
    target_scene_id: Optional[str] = None
    target_panel_id: Optional[str] = None
    target_sequence_threshold: Optional[int] = None
    effective_state: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Mapping of entity_id -> {property_path: value}"
    )
    contributing_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Audit trail of events that produced this effective state"
    )
    unresolved_conflicts: List[str] = Field(
        default_factory=list,
        description="List of detected conflicts or contradictory transitions"
    )

def set_nested_value(d: Dict[str, Any], path: str, value: Any) -> None:
    """Sets a value in a nested dictionary using dot-delimited path."""
    parts = path.split(".")
    curr = d
    for part in parts[:-1]:
        if part not in curr or not isinstance(curr[part], dict):
            curr[part] = {}
        curr = curr[part]
    curr[parts[-1]] = value

def get_nested_value(d: Dict[str, Any], path: str) -> Optional[Any]:
    """Retrieves a value from a nested dictionary using dot-delimited path."""
    parts = path.split(".")
    curr = d
    for part in parts:
        if not isinstance(curr, dict) or part not in curr:
            return None
        curr = curr[part]
    return curr

def validate_event_against_bible(
    event: StoryStateEvent,
    declared_characters: Set[str],
    declared_locations: Set[str],
    declared_props: Set[str],
    allowed_property_paths: Optional[Dict[str, Set[str]]] = None
) -> None:
    """
    Validates that the event refers to an entity declared in the Story Bible,
    and checks property paths against declared state-relevant properties when configured.
    """
    entity_type = event.entity_type
    entity_id = event.entity_id.lower()

    if entity_type == "world":
        if entity_id != "world":
            raise UndeclaredEntityError(f"World entity_id must be 'world', got '{event.entity_id}'")
    elif entity_type == "character":
        if entity_id not in declared_characters:
            raise UndeclaredEntityError(
                f"Undeclared character '{event.entity_id}'. Declared characters: {sorted(declared_characters)}"
            )
    elif entity_type == "location":
        if entity_id not in declared_locations:
            raise UndeclaredEntityError(
                f"Undeclared location '{event.entity_id}'. Declared locations: {sorted(declared_locations)}"
            )
    elif entity_type == "prop":
        if entity_id not in declared_props:
            raise UndeclaredEntityError(
                f"Undeclared prop '{event.entity_id}'. Declared props: {sorted(declared_props)}"
            )
    else:
        raise InvalidStateEventError(f"Unsupported entity_type: '{entity_type}'")

    if allowed_property_paths and entity_id in allowed_property_paths:
        allowed_set = allowed_property_paths[entity_id]
        # Check if root property path matches an allowed property
        root_prop = event.property_path.split(".")[0]
        if root_prop not in allowed_set and event.property_path not in allowed_set:
            raise InvalidStateEventError(
                f"Property path '{event.property_path}' not declared in state-relevant properties for '{entity_id}'. "
                f"Allowed: {sorted(allowed_set)}"
            )

def resolve_timeline_state(
    events: List[StoryStateEvent],
    target_scene_or_panel: Optional[str] = None,
    strict_transitions: bool = True
) -> StateResolutionResult:
    """
    Deterministically resolves effective story state up to the target scene or panel.
    Guarantees:
    1. Stable ordering: sorted by sequence_number ascending, then timestamp, then event_id.
    2. Idempotency: duplicate event_id with identical payload ignored; conflicting duplicate raises error.
    3. Contradiction check: validates previous_value when specified.
    4. Explanations: records contributing events in order.
    5. Non-mutating: does not modify event objects or external definitions.
    """
    if not events:
        return StateResolutionResult(
            target_scene_id=target_scene_or_panel,
            target_panel_id=target_scene_or_panel,
            effective_state={},
            contributing_events=[],
            unresolved_conflicts=[]
        )

    # Deterministic sorting
    sorted_events = sorted(events, key=lambda e: (e.sequence_number, e.timestamp, e.event_id))

    # Determine cutoff threshold if target_scene_or_panel specified
    cutoff_seq: Optional[int] = None
    target_scene_id: Optional[str] = None
    target_panel_id: Optional[str] = None

    if target_scene_or_panel:
        matching_seqs = [
            e.sequence_number for e in sorted_events
            if e.panel_id == target_scene_or_panel or e.scene_id == target_scene_or_panel
        ]
        if matching_seqs:
            cutoff_seq = max(matching_seqs)
            target_panel_id = target_scene_or_panel
            target_scene_id = target_scene_or_panel
        else:
            # If target looks like an integer sequence number
            if target_scene_or_panel.isdigit():
                cutoff_seq = int(target_scene_or_panel)
            else:
                # Target panel hasn't occurred yet or no events for it; empty state
                return StateResolutionResult(
                    target_scene_id=target_scene_or_panel,
                    target_panel_id=target_scene_or_panel,
                    target_sequence_threshold=None,
                    effective_state={},
                    contributing_events=[],
                    unresolved_conflicts=[f"No events found matching scene/panel '{target_scene_or_panel}'"]
                )

    seen_events: Dict[str, StoryStateEvent] = {}
    effective_state: Dict[str, Dict[str, Any]] = {}
    contributing: List[Dict[str, Any]] = []
    conflicts: List[str] = []

    for event in sorted_events:
        if cutoff_seq is not None and event.sequence_number > cutoff_seq:
            break

        # Duplicate event check
        if event.event_id in seen_events:
            existing = seen_events[event.event_id]
            if existing.model_dump() == event.model_dump():
                # Idempotent skip
                continue
            else:
                msg = (
                    f"Duplicate event_id '{event.event_id}' with conflicting payload: "
                    f"existing={existing.model_dump()}, new={event.model_dump()}"
                )
                if strict_transitions:
                    raise DuplicateEventConflictError(msg)
                conflicts.append(msg)
                continue

        seen_events[event.event_id] = event

        entity_key = f"{event.entity_type}:{event.entity_id}"
        if entity_key not in effective_state:
            effective_state[entity_key] = {}

        entity_state = effective_state[entity_key]
        current_val = get_nested_value(entity_state, event.property_path)

        # Contradiction check: if previous_value specified, verify it matches
        if event.previous_value is not None:
            if current_val != event.previous_value:
                msg = (
                    f"Contradictory state transition in event '{event.event_id}' for '{entity_key}.{event.property_path}': "
                    f"event expects previous_value='{event.previous_value}', but current state is '{current_val}'"
                )
                if strict_transitions:
                    raise ContradictoryTransitionError(msg)
                conflicts.append(msg)

        # Apply state mutation
        set_nested_value(entity_state, event.property_path, event.new_value)

        contributing.append({
            "event_id": event.event_id,
            "sequence_number": event.sequence_number,
            "scene_id": event.scene_id,
            "panel_id": event.panel_id,
            "entity": entity_key,
            "property_path": event.property_path,
            "previous_value": current_val,
            "new_value": event.new_value,
            "timestamp": event.timestamp,
            "source_ref": event.source_ref
        })

    return StateResolutionResult(
        target_scene_id=target_scene_id,
        target_panel_id=target_panel_id,
        target_sequence_threshold=cutoff_seq,
        effective_state=effective_state,
        contributing_events=contributing,
        unresolved_conflicts=conflicts
    )


StoryStateSnapshot = StateResolutionResult


class StoryStateTimeline(BaseModel):
    """
    Encapsulated timeline managing an ordered sequence of narrative state events
    for a specific execution run. Guarantees deterministic state resolution and run isolation.
    """
    run_id: str = Field(default="default_run", description="Execution run identifier")
    project_id: str = Field(..., description="Target project identifier")
    canon_version: int = Field(default=1, description="Canon version this timeline is anchored to")
    events: List[StoryStateEvent] = Field(default_factory=list, description="Ordered timeline events")

    def append_event(self, event: StoryStateEvent, canon: Optional[Any] = None) -> StoryStateEvent:
        """Appends an event after validating against canon entities and transition invariants."""
        if canon is not None:
            char_keys = set(canon.characters.keys()) if hasattr(canon, "characters") else set()
            loc_keys = set(canon.locations.keys()) if hasattr(canon, "locations") else set()
            prop_keys = set(canon.props.keys()) if hasattr(canon, "props") else set()
            validate_event_against_bible(event, char_keys, loc_keys, prop_keys)

        # Contradiction and ordering check
        new_events = self.events + [event]
        resolve_timeline_state(new_events, strict_transitions=True)
        self.events.append(event)
        return event

    def resolve_state_at(
        self,
        scene_or_panel_id: Optional[str] = None,
        sequence_threshold: Optional[int] = None
    ) -> StateResolutionResult:
        """Deterministically resolves effective state at the specified boundary."""
        target = str(sequence_threshold) if sequence_threshold is not None else scene_or_panel_id
        return resolve_timeline_state(self.events, target_scene_or_panel=target, strict_transitions=False)
