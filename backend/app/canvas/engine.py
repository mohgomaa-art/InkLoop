"""
InkLoop Canvas Generation Engine (E2) - Core Engine Service.
Orchestrates deterministic page layout generation, boundary validation, and preview rendering.
Acts as the central authority for canvas geometry and spatial layout calculations.
"""
from typing import Optional, Dict, Any, Union, List

from app.contracts.engine import CanvasGenerationParams, CanvasGenerationOutput
from app.contracts.identity import IdPrefix, generate_id
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    MarginSpec,
    GutterSpec,
    BleedSpec,
    SafeAreaSpec,
    PageFormat,
    PageType,
    ReadingDirection,
    LayoutTemplateId,
    CanvasLayoutResult,
    ValidationDiagnostic,
)
from app.canvas.templates import get_template, list_templates, resolve_template_id
from app.canvas.previews.svg import SVGPreviewGenerator, SVGPreviewConfig
from app.canvas.previews.raster import RasterPreviewGenerator, RasterPreviewConfig

class CanvasEngine:
    """
    Specialist Production Engine E2: Canvas Generation Engine.
    Produces deterministic manga/manhwa page layouts, validates spatial invariants,
    and generates reproducible structural SVG and raster previews.
    """

    @classmethod
    def generate_layout(
        cls,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        template_id: Union[str, LayoutTemplateId] = LayoutTemplateId.MANGA_GRID,
        **template_params: Any
    ) -> CanvasLayoutResult:
        """
        Generates a canonical layout result for the given canvas and page specifications.
        Validates all geometry bounds, containment, and overlap invariants.
        """
        template = get_template(template_id)
        result = template.generate(canvas_spec, page_spec, **template_params)
        return result

    @classmethod
    def generate_from_params(
        cls,
        params: CanvasGenerationParams,
        project_id: str = "proj_default",
        scope_id: Optional[str] = None
    ) -> CanvasGenerationOutput:
        """
        Executes canvas generation using the shared EngineRunRequest parameter envelope
        CanvasGenerationParams, producing a standardized CanvasGenerationOutput.
        """
        # Map page format string to PageFormat enum if possible
        fmt_str = params.page_format.lower()
        if "a4" in fmt_str:
            page_format = PageFormat.A4
        elif "b5" in fmt_str:
            page_format = PageFormat.B5
        elif "us" in fmt_str or "comic" in fmt_str:
            page_format = PageFormat.US_COMIC
        elif "webtoon" in fmt_str:
            page_format = PageFormat.WEBTOON_VERTICAL
        else:
            page_format = PageFormat.CUSTOM

        # Map margins, gutters, bleed
        m_dict = params.margins_px or {}
        margins = MarginSpec(
            top=m_dict.get("top", 120.0),
            bottom=m_dict.get("bottom", 120.0),
            left=m_dict.get("left", 100.0),
            right=m_dict.get("right", 100.0),
        )

        g_dict = params.gutters_px or {}
        gutters = GutterSpec(
            horizontal=g_dict.get("horizontal", 40.0),
            vertical=g_dict.get("vertical", 40.0),
        )

        bleed = BleedSpec.uniform(params.bleed_px)

        canvas_spec = CanvasSpec(
            page_format=page_format,
            width_px=params.width_px,
            height_px=params.height_px,
            dpi=params.dpi,
            margins=margins,
            gutters=gutters,
            bleed=bleed,
        )

        r_dir = ReadingDirection.RTL if params.reading_direction.lower() == "rtl" else ReadingDirection.LTR
        page_id = scope_id or generate_id(IdPrefix.PAGE, "layout")

        page_spec = PageSpec(
            page_id=page_id,
            reading_direction=r_dir,
        )

        # Stable catalogue presets resolve to existing deterministic templates.
        template_parameters = dict(params.template_parameters or {})
        layout_preset_id = params.panel_preset_id
        if layout_preset_id:
            from app.canvas.catalogue import get_panel_layout_preset
            preset = get_panel_layout_preset(layout_preset_id)
            if preset is None:
                from app.canvas.errors import TemplateNotFoundError
                raise TemplateNotFoundError(layout_preset_id, available_templates=[])
            template_id = resolve_template_id(preset["template_id"])
            if template_id is None:
                from app.canvas.errors import TemplateNotFoundError
                raise TemplateNotFoundError(preset["template_id"], available_templates=[])
            template_parameters = dict(preset["template_parameters"])
        else:
            template_id = resolve_template_id(params.layout_template)
            if template_id is None:
                from app.canvas.errors import TemplateNotFoundError
                raise TemplateNotFoundError(params.layout_template, available_templates=[])

        result = cls.generate_layout(canvas_spec, page_spec, template_id=template_id, **template_parameters)
        result.layout_preset_id = layout_preset_id
        artifact_id = generate_id(IdPrefix.ARTIFACT, f"canvas_{page_id}")
        return result.to_engine_output(artifact_id=artifact_id)

    @classmethod
    def generate_svg_preview(
        cls,
        result: CanvasLayoutResult,
        config: Optional[SVGPreviewConfig] = None
    ) -> str:
        """Produces a deterministic, valid SVG structural representation of the layout."""
        return SVGPreviewGenerator.generate(result, config)

    @classmethod
    def generate_raster_preview(
        cls,
        result: CanvasLayoutResult,
        config: Optional[RasterPreviewConfig] = None
    ) -> bytes:
        """Produces a PNG raster representation of the structural layout."""
        return RasterPreviewGenerator.render_png_bytes(result, config)

    @classmethod
    def list_templates(cls) -> List[Dict[str, Any]]:
        """Returns the list of all available layout templates and their capabilities."""
        return list_templates()
