"""Typed, resumable creative production state for Agent-to-Canvas stories."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field


ProductionStatus = Literal[
    "preflight", "generating", "assembling", "verifying", "needs_attention", "completed", "failed"
]
PanelProductionStatus = Literal[
    "pending", "generating", "generated", "placed", "needs_attention", "failed"
]


class PanelProduction(BaseModel):
    model_config = ConfigDict(extra="allow")

    panel_id: str
    page_number: int = Field(ge=1)
    status: PanelProductionStatus = "pending"
    character_ids: List[str] = Field(default_factory=list)
    character_versions: Dict[str, int] = Field(default_factory=dict)
    prop_ids: List[str] = Field(default_factory=list)
    prop_versions: Dict[str, int] = Field(default_factory=dict)
    prop_states: Dict[str, str] = Field(default_factory=dict)
    prop_reference_asset_ids: List[str] = Field(default_factory=list)
    style_profile_id: Optional[str] = None
    style_profile_version: Optional[int] = None
    asset_id: Optional[str] = None
    asset_sha256: Optional[str] = None
    generation_attempts: int = 0
    automatic_retries: int = 0
    manual_retries: int = 0
    processed_generation_call_ids: List[str] = Field(default_factory=list)
    image_layer_id: Optional[str] = None
    replacement_expected_asset_id: Optional[str] = None
    text_layer_ids: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)


class PageProduction(BaseModel):
    model_config = ConfigDict(extra="allow")

    page_number: int = Field(ge=1)
    page_id: str
    panel_ids: List[str] = Field(default_factory=list)
    revision: Optional[int] = None
    status: Literal["pending", "created", "assembled", "needs_attention", "failed"] = "pending"
    verification: Dict[str, Any] = Field(default_factory=dict)
    composite_artifact_id: Optional[str] = None
    composite_image_url: Optional[str] = None


class StoryProductionJob(BaseModel):
    """Durable resumable job snapshot stored with its owning Agent session."""
    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.3.0"
    job_id: str
    run_id: str
    project_id: str
    source_request_message_id: str
    source_plan_call_id: str
    goal: str = "Generate and place all planned artwork, save every requested Canvas page, and verify every page."
    target_page_count: Optional[int] = Field(default=None, ge=1, le=50)
    page_panel_counts: Dict[str, int] = Field(default_factory=dict)
    stage: str = "queued"
    status: ProductionStatus = "preflight"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    plan: Dict[str, Any]
    reading_direction: Optional[str] = Field(default="ltr", description="Reading direction for page generation ('ltr' or 'rtl')")
    page_panel_count: int = Field(default=6, ge=1, le=24)
    pages: List[PageProduction] = Field(default_factory=list)
    panels: Dict[str, PanelProduction] = Field(default_factory=dict)
    selected_character_ids: List[str] = Field(default_factory=list)
    prop_versions: Dict[str, int] = Field(default_factory=dict)
    prop_snapshots: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    style_profile_id: Optional[str] = None
    style_profile_version: Optional[int] = None
    style_snapshot: Optional[Dict[str, Any]] = None
    location_id: Optional[str] = None
    location_version: Optional[int] = None
    location_snapshot: Optional[Dict[str, Any]] = None
    assumptions: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    export_artifact_id: Optional[str] = None
    export_download_url: Optional[str] = None
    export_file_path: Optional[str] = None


def stable_job_id(project_id: str, session_id: str, plan_call_id: str) -> str:
    digest = hashlib.sha256(f"{project_id}|{session_id}|{plan_call_id}".encode()).hexdigest()[:16]
    return f"storyjob_{digest}"


def stable_page_id(job_id: str, page_number: int) -> str:
    digest = hashlib.sha256(f"{job_id}|page|{page_number}".encode()).hexdigest()[:12]
    return f"page_story_{digest}"


def production_action_requested(text: str) -> bool:
    query = (text or "").casefold().strip()
    if not query:
        return False
    # If the text is a multi-paragraph story submission (>= 180 chars or markdown headings),
    # never treat narrative prose (e.g. 'continue', 'finish') as an immediate production command
    # unless it explicitly opens with an imperative production directive.
    is_story = (len(query) >= 180) or bool(re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", text or "") and len(query) >= 100)
    if is_story:
        first_lines = "\n".join(query.splitlines()[:2])
        return bool(re.search(r"^(?:start|create|build|generate|make|produce)\s+(?:comic|production|pages?|panels?)\b", first_lines))

    return bool(
        re.fullmatch(r"(?:start|do it|go ahead|continue|finish|proceed|resume)[!.]*", query)
        or re.search(
            r"\b(?:proceed|generate\s+(?:all\s+)?(?:the\s+)?(?:story\s+)?panels?|"
            r"make\s+(?:all\s+)?(?:the\s+)?(?:story\s+)?panels?|"
            r"make\s+(?:all\s+)?(?:the\s+)?images?|create\s+(?:all\s+)?(?:the\s+)?(?:story\s+)?panels?|"
            r"create\s+(?:all\s+)?(?:the\s+)?images?|retry(?:\s+(?:panel\s+)?[a-z0-9][a-z0-9_-]*)?|"
            r"regenerate(?:\s+(?:panel\s+)?[a-z0-9][a-z0-9_-]*)?|replace\s+(?:the\s+)?(?:panels?|artwork)|"
            r"assemble|add\s+to\s+(?:the\s+)?canvas|canvas|page\s+editor|start\s+(?:production|generating)|"
            r"continue\s+production|resume\s+production|finish\s+production)\b|(?:أكمل|تابع|ابدأ|أضف.*كانفس)",
            query,
        )
    )


def lettering_only_requested(text: str) -> bool:
    """Recognize an explicit request to finish lettering on saved artwork only."""
    query = (text or "").casefold().strip()
    if not query:
        return False
    if re.search(r"\b(?:don't|dont|do not|never|stop|without)\b.{0,35}\b(?:bubble|balloon|lettering|dialogue|caption|text)\w*\b", query):
        return False
    asks_for_lettering = bool(
        re.search(r"\b(?:bubble|balloon|lettering|dialogue|caption)\w*\b", query)
        or re.search(r"\b(?:speech|comic)\s+text\b", query)
        or re.search(r"\b(?:bubbles?|balloons?)\s+(?:and|&|\+)\s+text\b", query)
        or re.search(r"\btext\s+(?:and|&|\+)\s+(?:bubbles?|balloons?)\b", query)
    )
    asks_to_change = bool(re.search(r"\b(?:add|put|make|create|continue|finish|complete|write|place|insert)\b", query))
    artwork_negation = re.compile(
        r"\b(?:don't|dont|do not|never|without)\s+(?:edit|change|generate|regenerate|replace|redraw)\s+(?:the\s+)?(?:image|artwork|panel|picture)s?\b"
    )
    positive_query = artwork_negation.sub("", query)
    asks_for_new_art = bool(re.search(r"\b(?:generate|regenerate|replace|redraw|change|edit)\b.{0,30}\b(?:image|artwork|panel|picture)s?\b", positive_query))
    return asks_for_lettering and asks_to_change and not asks_for_new_art


def saved_job_ready_for_lettering(job: Dict[str, Any]) -> bool:
    """Return true only when a durable job has complete placed artwork and persisted pages."""
    if not isinstance(job, dict) or not job.get("job_id") or not job.get("plan"):
        return False
    plans = job.get("plan", {}).get("plans") or []
    panels = job.get("panels") or {}
    pages = job.get("pages") or []
    plan_ids = [
        str(item.get("panel_id")) for item in plans
        if isinstance(item, dict) and item.get("panel_id")
    ]
    if (
        not plans or not pages or len(plan_ids) != len(plans)
        or len(plan_ids) != len(set(plan_ids)) or set(panels) != set(plan_ids)
        or any(not isinstance(panel, dict) for panel in panels.values())
    ):
        return False
    if not all(
        item.get("status") in ("placed", "needs_attention") and item.get("asset_id")
        for item in panels.values() if isinstance(item, dict)
    ):
        return False
    expected_page_count = int(job.get("target_page_count") or len(pages))
    page_numbers = [page.get("page_number") for page in pages if isinstance(page, dict)]
    page_ids = [page.get("page_id") for page in pages if isinstance(page, dict)]
    page_panel_ids = [
        str(panel_id)
        for page in pages if isinstance(page, dict)
        for panel_id in (page.get("panel_ids") or [])
    ]
    return (
        len(pages) == expected_page_count
        and len(page_numbers) == len(pages)
        and all(isinstance(number, int) for number in page_numbers)
        and sorted(page_numbers) == list(range(1, expected_page_count + 1))
        and all(isinstance(page_id, str) and page_id for page_id in page_ids)
        and len(page_ids) == len(set(page_ids))
        and len(page_panel_ids) == len(set(page_panel_ids))
        and set(page_panel_ids) == set(plan_ids)
        and all(
            isinstance(page, dict)
            and page.get("status") in ("assembled", "needs_attention")
            and page.get("revision") is not None
            and page.get("page_id")
            and page.get("panel_ids")
            for page in pages
        )
    )


def selected_cast_repair_requested(text: str) -> bool:
    """Require an explicit repair verb plus a character/cast target before replacing saved artwork."""
    query = (text or "").casefold()
    return bool(
        re.search(r"\b(?:regenerate|re-generate|replace|redo|repair|fix)\b", query)
        and re.search(r"\b(?:selected\s+characters?|character\s+references?|cast|identity|panels?)\b", query)
    )


def _number(value: str) -> Optional[int]:
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    return int(value) if value.isdigit() else words.get(value.casefold())


def group_panels(plans: Sequence[Dict[str, Any]], request_texts: Sequence[str], default_page_size: int = 6) -> List[List[Dict[str, Any]]]:
    """Respect typed page numbers, then explicit page sizing, then six-panel pages."""
    if not plans:
        return []
    page_numbers = [p.get("page_number") for p in plans]
    if all(isinstance(n, int) and n > 0 for n in page_numbers):
        ordered: Dict[int, List[Dict[str, Any]]] = {}
        for plan, number in zip(plans, page_numbers):
            ordered.setdefault(number, []).append(plan)
        return [ordered[number] for number in sorted(ordered)]

    full_text = "\n".join(request_texts).casefold()
    page_size = None
    match = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+panels?\s+per\s+page\b", full_text)
    if match:
        page_size = _number(match.group(1))
    if not page_size:
        match = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)[ -]?pages?\b", full_text)
        explicit_pages = _number(match.group(1)) if match else None
        if explicit_pages and len(plans) % explicit_pages == 0:
            page_size = len(plans) // explicit_pages
    page_size = page_size if page_size and 1 <= page_size <= 24 else default_page_size
    return [list(plans[index:index + page_size]) for index in range(0, len(plans), page_size)]


_WORKFLOW_SKILL_RULES = (
    (
        "story_to_canvas.md",
        re.compile(r"\b(story|comic|manga|manhwa|webtoon|panel|page|chapter|scene|script|قصة|مانجا|مانهوا|لوحة|صفحة)\b", re.I),
        {"planning.plan_panels", "canvas.create_page_from_template", "canvas.verify_page"},
    ),
    (
        "comic-story-planning/SKILL.md",
        re.compile(r"\b(story\s+plan|plan\s+story|storytelling|narrative|script|plot|premise|beats?|character\s+arc|scene\s+craft|comics?\s+adaptation|تخطيط\s+قصة|حبكة|سيناريو)\b", re.I),
        {"planning.plan_panels", "canvas.create_page_from_template", "canvas.verify_page"},
    ),
    (
        "character_style_continuity.md",
        re.compile(r"\b(character|cast|canon|identity|style|reference|location|prop|شخصية|شخصيات|أسلوب|مرجع)\b", re.I),
        {"canon.inspect_characters", "canon.inspect_reference_anchor", "generation.generate_image"},
    ),
    (
        "natural-character-performance/SKILL.md",
        re.compile(r"\b(performance|acting|expression|emotion|eye\s+gaze|gaze|eyes?|posture|pose|body\s+language|believable|crossed\s+eyes|مظهر|تعبير|عيون|نظرة|أداء)\b", re.I),
        {"generation.check_readiness", "generation.generate_image"},
    ),
    (
        "image_generation_and_verification.md",
        re.compile(r"\b(generate|draw|illustrate|image|artwork|reference|create|انشئ|ارسم|ولد|صورة)\b", re.I),
        {"generation.check_readiness", "generation.generate_image"},
    ),
    (
        "canvas_layout_and_editing.md",
        re.compile(r"\b(canvas|page|panel|layout|reshape|place|editor|geometry|لوحة|صفحة|تخطيط)\b", re.I),
        {"canvas.create_page_from_template", "canvas.reshape_panel", "canvas.verify_page"},
    ),
    (
        "lettering_bubbles_typography.md",
        re.compile(r"\b(dialogue|text|lettering|bubble|balloon|tail|font|caption|sound effect|فقاعة|حوار|خط|نص)\b", re.I),
        {"canvas.add_speech_bubble", "editor.add_text_layer"},
    ),
    (
        "production_verification_recovery_export.md",
        re.compile(r"\b(verify|verification|check|resume|continue|recover|retry|export|finish|completed|saved|تحقق|أكمل|تابع|استعادة)\b", re.I),
        {"canvas.verify_page", "image.verify_visual_consistency", "execution.get_budget_allowance"},
    ),
)


def load_relevant_workflow_skills(text: str, callable_tool_ids: set[str]) -> str:
    """Load concise workflow guidance only when its real callable tools and intent match."""
    query = (text or "").strip()
    lowered = query.casefold()
    affirmative = bool(re.search(r"\b(yes|yes pls|yes please|start|go ahead|do it|continue|finish|resume|proceed)\b", lowered))
    has_comic_context = bool(re.search(r"\b(comic|manga|manhwa|webtoon|panels?|canvas page)\b", lowered))
    direct_production_request = bool(
        re.search(r"\b(create|make|generate|turn|build|produce|draw|illustrate)\b", lowered)
        and has_comic_context
    )
    # A short confirmation inherits the immediately preceding offer from chat context.
    full_pipeline = direct_production_request or (affirmative and has_comic_context)
    selected = []
    skills_dir = Path(__file__).with_name("skills")
    for filename, trigger, required_tools in _WORKFLOW_SKILL_RULES:
        if not required_tools.issubset(callable_tool_ids):
            continue
        if not full_pipeline and not trigger.search(query):
            continue
        path = skills_dir / filename
        if path.is_file():
            selected.append(path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(selected)


def corrected_character_ids(
    plans: Sequence[Dict[str, Any]],
    user_texts: Sequence[str],
    canonical_characters: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Correct explicitly role-labeled IDs only when the canon name resolves uniquely."""
    role_pairs: Dict[str, str] = {}
    for text in user_texts:
        for character_id, role in re.findall(
            r"`?\b(char_[a-z0-9_-]+)\b`?\s*(?:—|–|-|:)\s*(?:the\s+)?(protagonist|muse)\b",
            text,
            flags=re.IGNORECASE,
        ):
            role_pairs[character_id] = role.casefold()

    canonical_by_name: Dict[str, List[str]] = {}
    for character_id, character in canonical_characters.items():
        name = str(getattr(character, "name", "") if not isinstance(character, dict) else character.get("name", ""))
        canonical_by_name.setdefault(name.strip().casefold(), []).append(character_id)

    resolved: Dict[str, str] = {}
    explicit_ids = set(role_pairs)
    for old_id, role in role_pairs.items():
        candidates = canonical_by_name.get(role, [])
        if not candidates and role == "protagonist":
            muse_ids = canonical_by_name.get("muse", [])
            remaining = explicit_ids.intersection(canonical_characters) - set(muse_ids)
            if len(remaining) == 1:
                candidates = list(remaining)
            else:
                # With exactly two explicitly named canonical references, the
                # protagonist is the unique non-Muse character from that pair.
                canon_remaining = set(canonical_characters) - set(muse_ids)
                candidates = list(canon_remaining) if len(canon_remaining) == 1 else []
        if len(candidates) == 1:
            resolved[old_id] = candidates[0]

    corrected: List[Dict[str, Any]] = []
    for source in plans:
        plan = dict(source)
        if "character_ids" in plan:
            plan["character_ids"] = list(dict.fromkeys(resolved.get(cid, cid) for cid in plan.get("character_ids", [])))
        text_plan = plan.get("text")
        if isinstance(text_plan, dict) and text_plan.get("speaker_id"):
            text_plan = dict(text_plan)
            text_plan["speaker_id"] = resolved.get(text_plan["speaker_id"], text_plan["speaker_id"])
            plan["text"] = text_plan
        corrected.append(plan)
    # IDs are sometimes listed as inline code in the creator's prompt.
    # Preserve role resolution only for a unique canonical name match.
    return corrected, {old: new for old, new in resolved.items() if old != new}
