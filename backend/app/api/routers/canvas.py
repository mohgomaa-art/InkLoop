"""
InkLoop Canvas API Router.
Exposes REST endpoints for querying layout templates, generating canvas layouts,
and retrieving deterministic SVG structural previews.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, status, HTTPException, Query
from fastapi.responses import Response

from app.contracts.engine import CanvasGenerationParams, CanvasGenerationOutput
from app.canvas.models import CanvasSpec, PageSpec, LayoutTemplateId, CanvasLayoutResult
from app.canvas.templates import resolve_template_id
from app.canvas.engine import CanvasEngine
from app.canvas.errors import CanvasError
from app.canvas.catalogue import list_panel_layout_presets, list_bubble_presets

router = APIRouter(prefix="/canvas", tags=["Canvas Generation Engine (E2)"])

@router.get("/templates", summary="List available layout templates")
def get_layout_templates():
    """Returns metadata for all supported deterministic canvas layout templates."""
    return {
        "templates": CanvasEngine.list_templates(),
        "count": len(CanvasEngine.list_templates()),
    }

@router.get("/panel-layout-presets", summary="Search the 100 stable-ID panel layout recipes")
def get_panel_layout_presets(query: str = Query(default=""), limit: int = Query(default=100, ge=1, le=100)):
    presets = list_panel_layout_presets(query=query, limit=limit)
    return {"presets": presets, "count": len(presets), "total": 100}

@router.get("/bubble-presets", summary="Search the 50 stable-ID speech bubble presets")
def get_bubble_presets(query: str = Query(default=""), limit: int = Query(default=50, ge=1, le=50)):
    presets = list_bubble_presets(query=query, limit=limit)
    return {"presets": presets, "count": len(presets), "total": 50}

@router.post("/generate", summary="Generate deterministic canvas layout")
def generate_canvas(params: CanvasGenerationParams):
    """
    Generates a deterministic canvas layout matching the requested page format,
    margins, gutters, bleed, and template configuration.
    """
    try:
        output: CanvasGenerationOutput = CanvasEngine.generate_from_params(params)
        return output
    except CanvasError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": e.code.value if hasattr(e, "code") else "ERR_2001", "message": str(e), "details": getattr(e, "details", {})}
        )

@router.post("/layout", summary="Generate canonical E2 layout for editing")
def generate_canonical_layout(params: CanvasGenerationParams):
    """Returns the full E2 layout contract, including polygons and explicit reading order."""
    try:
        # Resolve the canonical result using the same mapping as generate_from_params.
        fmt = params.page_format.lower()
        if "a4" in fmt: cs = CanvasSpec.create_a4(dpi=params.dpi)
        elif "b5" in fmt: cs = CanvasSpec.create_b5(dpi=params.dpi)
        elif "webtoon" in fmt: cs = CanvasSpec.create_webtoon(dpi=params.dpi)
        else: cs = CanvasSpec(width_px=params.width_px, height_px=params.height_px, dpi=params.dpi)
        from app.canvas.models import ReadingDirection
        from app.contracts.identity import generate_id, IdPrefix
        direction = ReadingDirection.RTL if params.reading_direction.lower() == "rtl" else ReadingDirection.LTR
        page = PageSpec(page_id=generate_id(IdPrefix.PAGE, "layout"), reading_direction=direction)
        template_parameters = dict(params.template_parameters or {})
        if params.panel_preset_id:
            from app.canvas.catalogue import get_panel_layout_preset
            preset = get_panel_layout_preset(params.panel_preset_id)
            if preset is None:
                raise HTTPException(status_code=404, detail={"message": f"Unknown panel layout preset '{params.panel_preset_id}'."})
            template_id = resolve_template_id(preset["template_id"])
            template_parameters = dict(preset["template_parameters"])
        else:
            template_id = resolve_template_id(params.layout_template)
        if template_id is None:
            raise HTTPException(status_code=422, detail={"message": f"Unknown layout template '{params.layout_template}'."})
        layout = CanvasEngine.generate_layout(cs, page, template_id=template_id, **template_parameters)
        layout.layout_preset_id = params.panel_preset_id
        return layout.model_dump(mode="json")
    except CanvasError as e:
        raise HTTPException(status_code=422, detail={"message": str(e)})

@router.post("/preview/svg", summary="Generate SVG structural preview")
def generate_svg_preview(params: CanvasGenerationParams):
    """Generates a self-contained SVG structural preview of the generated canvas layout."""
    try:
        # Convert params to layout result
        fmt_str = params.page_format.lower()
        if "a4" in fmt_str:
            cs = CanvasSpec.create_a4(dpi=params.dpi)
        elif "b5" in fmt_str:
            cs = CanvasSpec.create_b5(dpi=params.dpi)
        elif "webtoon" in fmt_str:
            cs = CanvasSpec.create_webtoon(dpi=params.dpi)
        else:
            cs = CanvasSpec(width_px=params.width_px, height_px=params.height_px, dpi=params.dpi)

        ps = PageSpec(page_id="page_preview")
        template_id = resolve_template_id(params.layout_template) or LayoutTemplateId.MANGA_GRID
        result = CanvasEngine.generate_layout(cs, ps, template_id=template_id)
        svg_content = CanvasEngine.generate_svg_preview(result)
        return Response(content=svg_content, media_type="image/svg+xml")
    except CanvasError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": e.code.value if hasattr(e, "code") else "ERR_2001", "message": str(e), "details": getattr(e, "details", {})}
        )


@router.post("/bubbles/recommend", summary="Autonomous story-to-bubble style recommendation")
def recommend_bubble(payload: Dict[str, Any]):
    """Returns autonomous speech bubble style recommendation based on narrative signals."""
    from app.canvas.bubble_stylist import recommend_bubble_style
    rec = recommend_bubble_style(
        emotional_intent=payload.get("emotional_intent", ""),
        narrative_function=payload.get("narrative_function"),
        delivery=payload.get("delivery"),
        carrier=payload.get("carrier"),
        sfx_category=payload.get("sfx_category"),
    )
    return rec.model_dump(mode="json")


@router.post("/bubbles/geometry", summary="Calculate procedural vector bubble geometry")
def calculate_bubble_geometry(payload: Dict[str, Any]):
    """Calculates SVG vector paths for bubble outline, tail, shadow, and accents."""
    from app.canvas.speech_bubble import SpeechBubbleEngine
    from app.canvas.bubble_models import BubbleShape, TailType
    from app.contracts.geometry import Rect, Point

    bounds_dict = payload.get("bounds", {})
    bounds = Rect(
        x=float(bounds_dict.get("x", 0.0)),
        y=float(bounds_dict.get("y", 0.0)),
        width=max(40.0, float(bounds_dict.get("width", 240.0))),
        height=max(30.0, float(bounds_dict.get("height", 120.0))),
    )

    tail_target = None
    if "tail_target" in payload and payload["tail_target"]:
        tt = payload["tail_target"]
        tail_target = Point(x=float(tt.get("x", 0.0)), y=float(tt.get("y", 0.0)))

    shape_str = str(payload.get("shape", "oval")).lower()
    shape = BubbleShape.OVAL
    for s in BubbleShape:
        if s.value == shape_str:
            shape = s
            break

    tail_str = str(payload.get("tail_type", "smooth_pointer")).lower()
    tail_type = TailType.SMOOTH_POINTER
    for t in TailType:
        if t.value == tail_str:
            tail_type = t
            break

    engine = SpeechBubbleEngine()
    geo = engine.generate_vector_geometry(
        bounds=bounds,
        shape=shape,
        tail_type=tail_type,
        tail_target=tail_target,
        padding_x=float(payload.get("padding_x", 24.0)),
        padding_y=float(payload.get("padding_y", 18.0)),
    )
    return geo.model_dump(mode="json")

