"""
InkLoop Canvas Generation Engine (E2) - Layout Template Registry.
Maps LayoutTemplateId enums to verified deterministic layout generator instances.
Includes canonical comic layouts and creator-defined custom geometry.
"""
from typing import Dict, Type, Union, List, Any, Optional

from app.canvas.models import LayoutTemplateId
from app.canvas.errors import TemplateNotFoundError
from app.canvas.templates.base import BaseLayoutTemplate
from app.canvas.templates.manga_grid import MangaGridLayoutTemplate
from app.canvas.templates.six_panel import SixPanelClassicTemplate
from app.canvas.templates.four_koma import FourKomaTemplate
from app.canvas.templates.dynamic_shonen import DynamicShonenTemplate
from app.canvas.templates.webtoon import WebtoonVerticalTemplate
from app.canvas.templates.three_panel_hero import ThreePanelHeroTemplate
from app.canvas.templates.three_panel_slanted import ThreePanelSlantedTemplate
from app.canvas.templates.five_panel_action import FivePanelActionTemplate
from app.canvas.templates.four_panel_cinematic import FourPanelCinematicTemplate
from app.canvas.templates.diagonal_slash_battle import DiagonalSlashBattleTemplate
from app.canvas.templates.shonen_climax_spread import ShonenClimaxSpreadTemplate
from app.canvas.templates.nine_panel_grid import NinePanelGridTemplate
from app.canvas.templates.two_panel_dramatic_spread import TwoPanelDramaticSpreadTemplate
from app.canvas.templates.seven_panel_action_burst import SevenPanelActionBurstTemplate
from app.canvas.templates.eight_panel_manhwa import EightPanelManhwaTemplate
from app.canvas.templates.three_tier_action_slant import ThreeTierActionSlantTemplate
from app.canvas.templates.custom import CustomLayoutTemplate

TEMPLATE_CLASSES: Dict[LayoutTemplateId, Type[BaseLayoutTemplate]] = {
    LayoutTemplateId.MANGA_GRID: MangaGridLayoutTemplate,
    LayoutTemplateId.SIX_PANEL_CLASSIC: SixPanelClassicTemplate,
    LayoutTemplateId.FOUR_KOMA: FourKomaTemplate,
    LayoutTemplateId.DYNAMIC_SHONEN: DynamicShonenTemplate,
    LayoutTemplateId.WEBTOON_VERTICAL: WebtoonVerticalTemplate,
    LayoutTemplateId.THREE_PANEL_HERO: ThreePanelHeroTemplate,
    LayoutTemplateId.THREE_PANEL_SLANTED: ThreePanelSlantedTemplate,
    LayoutTemplateId.FIVE_PANEL_ACTION: FivePanelActionTemplate,
    LayoutTemplateId.FOUR_PANEL_CINEMATIC: FourPanelCinematicTemplate,
    LayoutTemplateId.DIAGONAL_SLASH_BATTLE: DiagonalSlashBattleTemplate,
    LayoutTemplateId.SHONEN_CLIMAX_SPREAD: ShonenClimaxSpreadTemplate,
    LayoutTemplateId.NINE_PANEL_GRID: NinePanelGridTemplate,
    LayoutTemplateId.TWO_PANEL_DRAMATIC_SPREAD: TwoPanelDramaticSpreadTemplate,
    LayoutTemplateId.SEVEN_PANEL_ACTION_BURST: SevenPanelActionBurstTemplate,
    LayoutTemplateId.EIGHT_PANEL_MANHWA: EightPanelManhwaTemplate,
    LayoutTemplateId.THREE_TIER_ACTION_SLANT: ThreeTierActionSlantTemplate,
    LayoutTemplateId.CUSTOM: CustomLayoutTemplate,
}


def resolve_template_id(template_id: Union[str, LayoutTemplateId]) -> Optional[LayoutTemplateId]:
    """Resolves string, enum, or friendly alias to a canonical LayoutTemplateId."""
    if isinstance(template_id, LayoutTemplateId):
        return template_id
    if not isinstance(template_id, str):
        return None

    norm = template_id.lower().strip().replace("-", "_")

    # Direct match on enum value or name
    for tid in LayoutTemplateId:
        if tid.value == norm or tid.name.lower() == norm:
            return tid

    # Contextual alias matching
    if "slash" in norm or "battle" in norm or ("diagonal" in norm and "6" in norm):
        return LayoutTemplateId.DIAGONAL_SLASH_BATTLE
    if "three_tier" in norm or "chevron" in norm or ("slant" in norm and "tier" in norm):
        return LayoutTemplateId.THREE_TIER_ACTION_SLANT
    if "climax" in norm or ("hero" in norm and "spread" in norm):
        return LayoutTemplateId.SHONEN_CLIMAX_SPREAD
    if "cinematic" in norm or ("letterbox" in norm and "4" in norm):
        return LayoutTemplateId.FOUR_PANEL_CINEMATIC
    if "nine" in norm or "9" in norm or "watchmen" in norm:
        return LayoutTemplateId.NINE_PANEL_GRID
    if "two" in norm or "2_panel" in norm or "dramatic_spread" in norm:
        return LayoutTemplateId.TWO_PANEL_DRAMATIC_SPREAD
    if "seven" in norm or "7" in norm or "burst" in norm:
        return LayoutTemplateId.SEVEN_PANEL_ACTION_BURST
    if "manhwa" in norm or "8_panel" in norm or "eight" in norm:
        return LayoutTemplateId.EIGHT_PANEL_MANHWA
    if "hero" in norm or "3_panel_hero" in norm:
        return LayoutTemplateId.THREE_PANEL_HERO
    if "slanted" in norm or "3_panel_slanted" in norm:
        return LayoutTemplateId.THREE_PANEL_SLANTED
    if "five" in norm or "5" in norm:
        return LayoutTemplateId.FIVE_PANEL_ACTION
    if "shonen" in norm or "dynamic" in norm:
        return LayoutTemplateId.DYNAMIC_SHONEN
    if "4" in norm and "koma" in norm:
        return LayoutTemplateId.FOUR_KOMA
    if "6" in norm or "six" in norm:
        return LayoutTemplateId.SIX_PANEL_CLASSIC
    if "webtoon" in norm or "scroll" in norm:
        return LayoutTemplateId.WEBTOON_VERTICAL
    if "manga" in norm or "grid" in norm:
        return LayoutTemplateId.MANGA_GRID

    return None


def get_template(template_id: Union[str, LayoutTemplateId]) -> BaseLayoutTemplate:
    """Retrieves and instantiates the requested layout template by ID or string name."""
    target_id = resolve_template_id(template_id)

    if target_id is None or target_id not in TEMPLATE_CLASSES:
        available = [t.value for t in LayoutTemplateId]
        raise TemplateNotFoundError(str(template_id), available_templates=available)

    return TEMPLATE_CLASSES[target_id]()


def list_templates() -> List[Dict[str, Any]]:
    """Returns metadata for all registered layout templates."""
    results = []
    for tid, cls_ref in TEMPLATE_CLASSES.items():
        inst = cls_ref()
        results.append({
            "id": tid.value,
            "name": tid.name,
            "version": inst.version,
            "description": inst.description,
        })
    return results


__all__ = [
    "BaseLayoutTemplate",
    "MangaGridLayoutTemplate",
    "SixPanelClassicTemplate",
    "FourKomaTemplate",
    "DynamicShonenTemplate",
    "WebtoonVerticalTemplate",
    "ThreePanelHeroTemplate",
    "ThreePanelSlantedTemplate",
    "FivePanelActionTemplate",
    "FourPanelCinematicTemplate",
    "DiagonalSlashBattleTemplate",
    "ShonenClimaxSpreadTemplate",
    "NinePanelGridTemplate",
    "TwoPanelDramaticSpreadTemplate",
    "SevenPanelActionBurstTemplate",
    "EightPanelManhwaTemplate",
    "ThreeTierActionSlantTemplate",
    "CustomLayoutTemplate",
    "TEMPLATE_CLASSES",
    "resolve_template_id",
    "get_template",
    "list_templates",
]
