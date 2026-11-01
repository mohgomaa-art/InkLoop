"""S5 narrative and panel planning API."""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.canvas.engine import CanvasEngine
from app.canvas.errors import CanvasError
from app.canvas.models import CanvasSpec, LayoutTemplateId, PageSpec
from app.planning.panel_planner import (
    PanelPlanningRequest,
    attach_panel_plans,
    plan_panels,
)

router = APIRouter(prefix="/planning", tags=["Scene and Panel Planning (S5)"])


class PlannedCanvasRequest(BaseModel):
    """Orchestrate the independent S5 plan and E2 layout, then join by panel ID."""
    model_config = ConfigDict(extra="forbid")

    planning: PanelPlanningRequest
    canvas_spec: CanvasSpec
    page_spec: PageSpec
    template_id: LayoutTemplateId
    template_params: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_reading_direction(self) -> "PlannedCanvasRequest":
        if self.planning.reading_direction != self.page_spec.reading_direction:
            raise ValueError("Planning and E2 page reading_direction must match.")
        return self


@router.post("/panels", summary="Plan story beats as distinct narrative panels")
def create_panel_plan(payload: PanelPlanningRequest):
    """Return deterministic shot/composition plans for explicitly structured story beats."""
    try:
        return plan_panels(payload).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/panels/layout", summary="Plan panels and annotate an E2 layout")
def create_planned_layout(payload: PlannedCanvasRequest):
    """Compose S5 descriptors with E2's actual geometry, without conflating the engines."""
    try:
        planning = plan_panels(payload.planning)
        layout = CanvasEngine.generate_layout(
            payload.canvas_spec,
            payload.page_spec,
            template_id=payload.template_id,
            **payload.template_params,
        )
        annotated = attach_panel_plans(layout, planning)
        return {"planning": planning.model_dump(mode="json"), "layout": annotated.model_dump(mode="json")}
    except CanvasError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": exc.code.value, "message": str(exc), "details": exc.details},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
