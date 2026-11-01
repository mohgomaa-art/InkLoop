"""Versioned editor document contract, composed around the authoritative E2 layout."""
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, model_validator
from app.canvas.models import CanvasLayoutResult
from app.contracts.geometry import Transform2D


class LayerKind(str, Enum):
    PANEL = "panel"
    IMAGE = "image"
    TEXT = "text"
    LINE = "line"


class EditorLayer(BaseModel):
    layer_id: str
    kind: LayerKind
    label: str
    parent_id: Optional[str] = None
    visible: bool = True
    locked: bool = False
    z_index: int = 0
    source_asset_id: Optional[str] = None
    source_sha256: Optional[str] = None
    panel_id: Optional[str] = None
    # Image placement is independent from panel geometry and persists in E3 transform space.
    transform: Optional[Transform2D] = None
    fit_mode: Literal["cover", "contain"] = "cover"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def preserve_image_aspect_ratio(self):
        if self.kind == LayerKind.IMAGE and self.transform:
            if abs(abs(self.transform.scale_x) - abs(self.transform.scale_y)) > 1e-6:
                raise ValueError("Image layer scaling must preserve aspect ratio; scale_x must equal scale_y.")
        if self.kind == LayerKind.TEXT:
            text = self.metadata.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text layers require non-empty metadata.text.")
            for key in ("x", "y", "width", "font_size"):
                value = self.metadata.get(key)
                if not isinstance(value, (int, float)) or value <= 0 and key in ("width", "font_size"):
                    raise ValueError(f"Text layers require a valid metadata.{key}.")
        if self.kind == LayerKind.LINE:
            for key in ("x1", "y1", "x2", "y2", "stroke_width"):
                value = self.metadata.get(key)
                if not isinstance(value, (int, float)) or value <= 0 and key == "stroke_width":
                    raise ValueError(f"Line layers require a valid metadata.{key}.")
        return self


class EditablePageDocument(BaseModel):
    schema_version: str = "1.0.0"
    page_id: str
    project_id: str
    revision: int = Field(default=0, ge=0)
    layout: CanvasLayoutResult
    layers: List[EditorLayer] = Field(default_factory=list)
    source_artifact_ids: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_layer_references(self):
        ids = [layer.layer_id for layer in self.layers]
        if len(ids) != len(set(ids)):
            raise ValueError("Layer IDs must be unique.")
        known = set(ids)
        panels = {slot.panel_id for slot in self.layout.panel_slots}
        for layer in self.layers:
            if layer.parent_id and layer.parent_id not in known:
                raise ValueError(f"Unknown parent layer {layer.parent_id}.")
            if layer.panel_id and layer.panel_id not in panels:
                raise ValueError(f"Unknown panel {layer.panel_id}.")
            if layer.kind == LayerKind.IMAGE and not layer.source_asset_id:
                raise ValueError("Image layers require a registered source asset ID.")
        return self


class CreatePageRequest(BaseModel):
    project_id: str
    layout: CanvasLayoutResult
    source_artifact_ids: List[str] = Field(default_factory=list)


class SavePageRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    document: EditablePageDocument


class RestorePageRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    revision_to_restore: int = Field(ge=1)


class LayerPreviewRequest(BaseModel):
    transform: Transform2D = Field(default_factory=Transform2D)
    layout: Optional[CanvasLayoutResult] = None
