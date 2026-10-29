"""
InkLoop Shared Identity and Entity Reference Contracts.
Defines canonical identifier prefixes, slug formats, validation, and entity relationships.
"""
import re
import uuid
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class IdPrefix(str, Enum):
    PROJECT = "proj"
    STORY = "story"
    CHAPTER = "ch"
    SCENE = "scene"
    PAGE = "page"
    PANEL = "panel"
    CHARACTER = "char"
    CHARACTER_VERSION = "char_ver"
    ASSET = "asset"
    ARTIFACT = "art"
    RUN = "run"
    ATTEMPT = "att"
    QA = "qa"
    FONT = "font"
    TEXT = "txt"
    BUBBLE = "bbl"
    EFFECT = "fx"
    CANVAS = "canvas"
    TAXONOMY = "tax"
    OPERATION = "op"
    EVENT = "evt"
    RESERVATION = "res"

# Strict slug and identifier regex pattern: prefix_slug_random or prefix_number
# e.g., 'proj_inkloop_01', 'panel_scene01_02', 'art_01h8x...'
ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")

def is_valid_id(entity_id: str, expected_prefix: Optional[IdPrefix] = None) -> bool:
    """Checks whether an identifier complies with InkLoop naming conventions."""
    if not entity_id or not isinstance(entity_id, str):
        return False
    if not ID_PATTERN.match(entity_id):
        return False
    if expected_prefix:
        if not entity_id.startswith(f"{expected_prefix.value}_"):
            return False
    return True

def generate_id(prefix: IdPrefix, slug: Optional[str] = None) -> str:
    """Generates a structured, collision-resistant identifier with standard prefix."""
    clean_slug = ""
    if slug:
        clean_slug = re.sub(r"[^a-z0-9]+", "_", slug.lower().strip()).strip("_")
    short_uuid = uuid.uuid4().hex[:8]
    if clean_slug:
        return f"{prefix.value}_{clean_slug}_{short_uuid}"
    return f"{prefix.value}_{short_uuid}"

class EntityRef(BaseModel):
    """Generic reference to an entity with an explicit type and optional version."""
    id: str = Field(..., description="Canonical entity ID (e.g. 'char_nour_01')")
    prefix: IdPrefix = Field(..., description="Entity category prefix")
    version: Optional[str] = Field(default=None, description="Optional semantic version or revision string")

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not ID_PATTERN.match(v):
            raise ValueError(f"Identifier '{v}' does not match canonical pattern 'prefix_slug_...'")
        return v

# Specialized typed entity references to ensure type safety in pipelines
class ProjectRef(BaseModel):
    project_id: str = Field(..., description="Project identifier (e.g. 'proj_inkloop_demo')")

class StoryRef(BaseModel):
    project_id: str
    story_id: str
    story_version: int = 1

class ChapterRef(BaseModel):
    story_id: str
    chapter_id: str
    order: int = 1

class SceneRef(BaseModel):
    story_id: str
    scene_id: str
    order: int

class PageRef(BaseModel):
    project_id: str
    page_id: str
    page_number: int

class PanelRef(BaseModel):
    page_id: str
    panel_id: str
    order_in_page: int
    scene_id: Optional[str] = None

class CharacterRef(BaseModel):
    character_id: str
    canonical_version: int = 1
    variant_id: Optional[str] = None

class AssetRef(BaseModel):
    asset_id: str
    version: int = 1
    content_sha256: str

class ArtifactRef(BaseModel):
    artifact_id: str
    run_id: str
    mime_type: str

class RunRef(BaseModel):
    run_id: str
    attempt_id: str
