"""
InkLoop S9 Agent Coordinator.
Orchestrates the model-driven tool loop, authoritative context resolution,
budget headroom enforcement, approval gating, and durable trace persistence.
"""
import os
import sys
import re
import json
import time
from typing import Callable
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.config import PROJECT_ROOT, InkLoopConfig
from app.project.bible import load_bible, save_bible, create_canonical_nour_bible, StoryBible
from app.execution.manager import ExecutionManager

logger = logging.getLogger(__name__)

def _get_project_bible(project_id: str) -> StoryBible:
    clean_id = "".join(c for c in project_id if c.isalnum() or c in ("_", "-"))
    p = PROJECT_ROOT / "runs" / clean_id
    p.mkdir(parents=True, exist_ok=True)
    bible_path = p / "bible.json"
    if not bible_path.exists():
        bible = create_canonical_nour_bible(PROJECT_ROOT)
        bible.project_id = project_id
        save_bible(bible, bible_path)
    else:
        bible = load_bible(bible_path)
    if not bible.canon_hash:
        bible.canon_hash = bible.create_canon_snapshot().canon_hash
    return bible

from app.agent.schemas import (
    AgentMessage,
    AgentSession,
    AgentAttachment,
    ModelUsage,
    ToolCall,
    ToolResult,
    AgentPlan,
    AgentPlanStatus,
    AgentStep,
    PendingStoryAction,
)
from app.agent.registry import CapabilityRegistry
from app.agent.model_client import AgentModelClient
from app.agent.session_store import SessionStore
from app.agent.approvals import ApprovalManager
from app.agent.production import (
    StoryProductionJob,
    load_relevant_workflow_skills,
    lettering_only_requested,
    production_action_requested,
    saved_job_ready_for_lettering,
    selected_cast_repair_requested,
)
from app.agent.panel_plan_recovery import (
    collapse_incomplete_planner_retries,
    explicit_request_panel_count,
    normalize_panel_spelling,
    panel_plan_retry_is_duplicate,
    recover_panel_plan_arguments,
)
import app.agent.story_to_canvas as story_to_canvas_module
from app.agent.story_to_canvas import StoryToCanvasWorkflow

_ORIGINAL_STORY_WORKFLOW = StoryToCanvasWorkflow

def _resolve_story_to_canvas_workflow():
    """Dynamically resolve StoryToCanvasWorkflow, supporting monkeypatching in either coordinator or story_to_canvas."""
    current_coord = sys.modules[__name__].__dict__.get("StoryToCanvasWorkflow")
    if current_coord is not None and current_coord is not _ORIGINAL_STORY_WORKFLOW:
        return current_coord
    return getattr(story_to_canvas_module, "StoryToCanvasWorkflow", StoryToCanvasWorkflow)

MAX_TOOL_ROUNDS = max(1, min(15, int(os.getenv("INKLOOP_MAX_TOOL_ROUNDS", "8"))))

_COMPACT_PANEL_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string", "description": "Current project scope; the coordinator supplies this when omitted."},
        "scene_id": {"type": "string", "description": "Short stable ID for this story section; may be omitted when a scene summary or source title is available."},
        "scene_summary": {"type": "string", "description": "One concise summary grounded in the supplied story."},
        "panel_count": {"type": "integer", "minimum": 1, "maximum": 24, "description": "Use the explicit count in the creator's current request."},
        "panel_outline": {
            "type": "array",
            "minItems": 1,
            "maxItems": 24,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
            "description": "Return exactly one concise visual story event per requested panel, in story order. This is not dialogue, narration copy, or a caption. Do not put actions or plot summaries in character speech.",
        },
        "panel_dialogue": {
            "type": "array",
            "maxItems": 24,
            "description": "Optional audible character dialogue only. Omit this field when no short, plausible spoken line adds value; never fill every panel. Use a speaker_id from the creator-selected cast. Aim for 8 words or fewer and never exceed 12 words for newly drafted dialogue. Copy exact creator-authored dialogue unchanged even when it is longer.",
            "items": {
                "type": "object",
                "properties": {
                    "panel_index": {"type": "integer", "minimum": 1, "maximum": 24},
                    "speaker_id": {"type": "string", "minLength": 1, "maxLength": 128},
                    "text_content": {"type": "string", "minLength": 1, "maxLength": 500},
                },
                "required": ["panel_index", "speaker_id", "text_content"],
                "additionalProperties": False,
            },
        },
        "reading_direction": {"type": "string", "enum": ["rtl", "ltr"]},
    },
    "required": ["panel_count", "panel_outline"],
    "additionalProperties": False,
}


def _tools_for_turn(
    tools,
    text: str,
    expected_page_count: Optional[int] = None,
    selected_character_profiles: Optional[List[Dict[str, Any]]] = None,
    available_object_profiles: Optional[List[Dict[str, Any]]] = None,
):
    """Keep the model's tool schema focused on the creator's current task."""
    tools = [tool for tool in tools if tool.tool_id != "planning.plan_lettering"]
    query = normalize_panel_spelling((text or "").strip().lower())
    is_export_request = bool(re.search(r"\b(export|print|pdf|package|publish|تصدير|طباعة)\b", query))
    if re.fullmatch(r"(?:hi|hello|hey|thanks|thank you|مرحبا|اهلا|شكرا)[!.\s]*", query):
        return []
    is_affirmation = bool(re.fullmatch(r"(?:start|yes|yes\s+pls|yes\s+please|do\s+it|go\s+ahead|proceed|sure|yep|yeah|ok|okay|continue|finish|resume)[!.\s]*", query))
    is_sequential_plan_request = bool(re.search(
        r"\b(?:draft|create|prepare|build)\b.{0,80}\b(?:sequential|generation|execution)\s+plan\b",
        query,
    ))
    if is_sequential_plan_request:
        plan_tool = next((tool for tool in tools if tool.tool_id == "plan.draft_plan"), None)
        if plan_tool is not None:
            return [plan_tool]
    is_direct_art_request = bool(re.search(
        r"\b(?:generate|draw|create|make)\s+(?:(?:a|one|single)\s+)?(?:new\s+)?(?:image|picture|artwork)\b",
        query,
    ))
    if is_direct_art_request:
        direct_art_tools = {
            "generation.check_readiness", "generation.generate_image",
            "canon.inspect_characters", "canon.inspect_reference_anchor", "assets.list_assets",
        }
        selected = [tool for tool in tools if tool.tool_id in direct_art_tools]
        if any(tool.tool_id == "generation.generate_image" for tool in selected):
            return selected
    is_story = len(query) >= 180 or bool(re.search(r"\b(story(?!\s+bible)|part\s+\w+|chapter|scene|script|قصة|فصل|مشهد)\b", query))
    is_planning_explicit = bool(_requested_single_page_panel_count(query) or _is_explicit_story_plan_request(query) or _is_new_panel_plan_request(query))
    is_plan_control = bool(re.fullmatch(r"\s*(?:start|skip|no|yes|yes\s+please|go\s+ahead|proceed|continue)[!.\s]*", query))
    requested_panel_count = _requested_single_page_panel_count(query)
    requested_pages = _requested_page_count(query) or (None if is_plan_control else expected_page_count)
    # A story without an explicit page count gets a one-page review plan. This
    # keeps recurring-object identities available to the typed story planner
    # instead of sending story requests through the flat outline-only schema.
    if not requested_pages and is_story and not is_plan_control:
        requested_pages = 1
    if requested_pages:
        planner = next((tool for tool in tools if tool.tool_id == "planning.plan_panels"), None)
        if planner is not None:
            selected_profiles = [
                item for item in (selected_character_profiles or [])
                if isinstance(item, dict) and item.get("character_id")
            ]
            cast_instruction = (
                "The creator selected these Canon characters: "
                + ", ".join(
                    f"{item.get('name') or item['character_id']} ({item['character_id']})"
                    for item in selected_profiles
                )
                + ". Use these IDs in page beats when possible; exact selected display names are accepted and resolved. Keep story_cast empty; do not invent unselected or story-local cast members."
                if selected_profiles else
                "No Canon characters are selected. Create a story-local cast in the blueprint; do not add it to Canon."
            )
            object_instruction = (
                "Use the object profiles from the active project's object library in the system context. Reuse the same prop_id for the same physical object and list it in every panel where it appears. Keep state changes such as lit/carried separate from identity. Add a recurring_objects draft only for a genuinely new physical design; do not duplicate an existing library object."
            )
            known_object_rows = [
                item for item in (available_object_profiles or [])
                if isinstance(item, dict) and item.get("prop_id")
            ]
            if known_object_rows:
                object_instruction += " Existing object IDs: " + "; ".join(
                    f"{item.get('prop_id')} ({item.get('name') or 'unnamed'})@v{item.get('version', 1)}"
                    for item in known_object_rows
                ) + "."
            one_page_counts = {1: requested_panel_count} if requested_pages == 1 and requested_panel_count else None
            return [planner.model_copy(update={
                "purpose": (
                    f"Create a complete reviewable story blueprint with exactly {requested_pages} ordered pages. "
                    "Choose a different panel count for each page when story pacing calls for it; do not force a uniform grid. "
                    f"Preserve the creator's facts. {cast_instruction} {object_instruction} Every page needs a summary and at least one visual beat. "
                    + (f"Page 1 must contain exactly {requested_panel_count} beats, as explicitly requested. " if one_page_counts else "")
                    + "This only plans; it does not generate images or Canvas pages."
                ),
                "parameters_schema": _story_blueprint_schema(requested_pages, selected_profiles, one_page_counts),
            })]
    if is_planning_explicit:
        planner = next((tool for tool in tools if tool.tool_id == "planning.plan_panels"), None)
        if planner is not None:
            return [planner.model_copy(update={
                "purpose": "Outline one source-grounded visual event per panel; optionally provide short audible dialogue with a selected speaker ID. Never turn action descriptions into dialogue. The coordinator validates the registered narrative beat schema. No images or page geometry are created by this tool.",
                "parameters_schema": _COMPACT_PANEL_PLAN_SCHEMA,
            })]
    if is_story or is_affirmation:
        planner = next((tool for tool in tools if tool.tool_id == "planning.plan_panels"), None)
        if planner is not None:
            compact_planner = planner.model_copy(update={
                "purpose": "Outline one source-grounded visual event per panel; optionally provide short audible dialogue with a selected speaker ID. Never turn action descriptions into dialogue. The coordinator validates the registered narrative beat schema. No images or page geometry are created by this tool.",
                "parameters_schema": _COMPACT_PANEL_PLAN_SCHEMA,
            })
            core_tools = [
                t for t in tools
                if t.tool_id != "planning.plan_panels"
                and t.domain in ("canon", "generation", "canvas", "editor", "execution", "planning", "verification")
            ]
            return [compact_planner, *core_tools]
    domains = set()
    if re.search(r"\b(budget|cost|spend|price|رصيد|تكلفة)\b", query):
        domains.add("execution")
    if re.search(r"\b(export|print|pdf|package|publish|تصدير|طباعة)\b", query):
        domains.update({"editor", "canvas", "export", "verification"})
    if re.search(r"\b(bubble|balloon|dialogue|speech|tail|panel|canvas|page|editor|zoom|scale|resize|fit|transform|move|layer|spacing|gutter|gap|custom|scratch|polygon|geometry|layout|فقاعة|حوار|لوحة|تكبير|تصغير|تعديل|مسافة|فجوة|مخصص|مضلّع)\b", query):
        domains.update({"canvas", "planning", "generation", "canon", "text", "editor"})
    if re.search(r"\b(inspect|analy[sz]e|count|attachment|upload|reference|image|صورة|افحص|حلل)\b", query):
        domains.update({"inspection", "verification"})
    if re.search(r"\b(character|cast|canon(?:ical)?|story bible|شخصية|شخصيات|قانون)\b", query):
        domains.update({"canon", "creative", "verification"})
    if re.search(r"\b(story(?!\s+bible)|world|project|chapter|scene|قصة|عالم|مشروع|فصل|مشهد)\b", query):
        domains.update({"creative", "planning", "canon", "generation"})
    if re.search(r"\b(style|location|prop|reference|أسلوب|موقع|مرجع)\b", query):
        domains.update({"creative", "canon", "generation"})
    if re.search(r"\b(generate|draw|create|make|illustrate|artwork|image|ولد|ارسم|انشئ)\b", query):
        domains.update({"generation", "planning", "canvas", "canon"})
    if is_export_request:
        domains = {"editor", "canvas", "export", "verification"}
    if not domains:
        return tools
    selected = [tool for tool in tools if tool.domain in domains]
    return selected or tools


def _requested_page_count(text: str) -> Optional[int]:
    """Parse an explicit page count without confusing panels-per-page with total pages."""
    query = normalize_panel_spelling((text or "").casefold())
    if re.search(r"\bpanels?\s+per\s+page\b", query):
        page_match = re.search(r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+pages?\b", query)
    else:
        page_match = re.search(r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s*(?:-| )?pages?\b", query)
    if not page_match:
        return None
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    }
    raw_count = page_match.group(1)
    count = int(raw_count) if raw_count.isdigit() else words[raw_count]
    return count


def _story_blueprint_schema(
    page_count: int,
    selected_character_profiles: Optional[List[Dict[str, Any]]] = None,
    requested_panel_counts: Optional[Dict[int, int]] = None,
) -> Dict[str, Any]:
    from app.planning.panel_planner import StoryBlueprintDraft

    schema = StoryBlueprintDraft.model_json_schema()
    schema["properties"]["page_count"] = {
        "type": "integer", "enum": [page_count],
        "description": "Must exactly match the creator's explicit page count.",
    }
    schema["properties"]["pages"]["minItems"] = page_count
    schema["properties"]["pages"]["maxItems"] = page_count
    if requested_panel_counts:
        page_schema = schema.get("$defs", {}).get("StoryPageDraft", {}).get("properties", {})
        beats_schema = page_schema.get("beats", {})
        for page_number, panel_count in requested_panel_counts.items():
            if page_number == 1 and page_count == 1:
                beats_schema["minItems"] = panel_count
                beats_schema["maxItems"] = panel_count
                beats_schema["description"] = f"The creator explicitly requested exactly {panel_count} panels on this one-page story."
    selected_profiles = [
        item for item in (selected_character_profiles or [])
        if isinstance(item, dict) and item.get("character_id")
    ]
    selected_ids = list(dict.fromkeys(str(item["character_id"]) for item in selected_profiles))
    if selected_ids:
        # The generic blueprint used to advertise local-cast fields even when
        # a creator had explicitly selected Canon characters. Constrain the
        # model-facing schema to that authoritative cast.
        schema["properties"]["story_cast"]["maxItems"] = 0
        schema["properties"]["story_cast"]["description"] = (
            "Must be empty because the creator selected Canon characters."
        )
        definitions = schema.get("$defs", {})
        beat_properties = definitions.get("StoryBeatDraft", {}).get("properties", {})
        character_ids = beat_properties.get("character_ids", {})
        character_ids["items"] = {
            "type": "string",
            "enum": selected_ids,
            "description": "Only IDs selected by the creator are allowed.",
        }
        character_ids["description"] = "Use selected Canon IDs only; an empty list inherits the selected cast."
        selected_names = list(dict.fromkeys(
            str(item.get("name") or "").strip()
            for item in selected_profiles
            if str(item.get("name") or "").strip()
        ))
        visible_names = beat_properties.get("visible_character_names", {})
        visible_names["maxItems"] = max(1, len(selected_ids))
        visible_names["items"] = {
            "type": "string",
            "enum": selected_names,
            "description": "A display name from the creator-selected Canon cast; the coordinator resolves it to its stable ID.",
        }
        visible_names["description"] = "If names are used, use only exact display names from the selected Canon cast; the coordinator resolves them to IDs."
        text_properties = definitions.get("PanelTextPlan", {}).get("properties", {})
        speaker_name = text_properties.get("speaker_name", {})
        speaker_name["anyOf"] = [
            {"type": "string", "enum": selected_names},
            {"type": "null"},
        ]
        speaker_name["description"] = "Optional exact display name from the creator-selected cast; the coordinator resolves it to speaker_id."
        speaker_id = text_properties.get("speaker_id", {})
        speaker_id["enum"] = [*selected_ids, None]
        speaker_id["description"] = "Use the selected Canon ID for a speaking or thinking character; otherwise null."
    return schema


def _needs_model_follow_up(user_text: str, results: List[ToolResult], registry) -> bool:
    """Allow one extra reasoning call only for an explicit multi-step request."""
    if any(result.error_code in {"ERR_BUBBLE_SPEAKER_REQUIRED", "ERR_BUBBLE_TAIL_ANCHOR_REQUIRED"} for result in results):
        return True
    # A rejected typed panel plan is safe to correct once: no generation or
    # Canvas mutation has happened yet, and the model receives the exact field
    # validation errors for its revised plan. The global round limit bounds it.
    if any(
        result.tool_id == "planning.plan_panels"
        and result.error_code in {
            "ERR_INVALID_PANEL_PLAN",
            "ERR_INVALID_STORY_PLAN",
            "ERR_SCHEMA_VALIDATION_FAILED",
            "ERR_PANEL_PLAN_SOURCE_REQUIRED",
        }
        for result in results
    ):
        return True
    if any(
        result.tool_id == "planning.plan_lettering"
        and result.error_code in {
            "ERR_SCHEMA_VALIDATION_FAILED",
            "ERR_LETTERING_PANEL_SCOPE",
            "ERR_INVALID_LETTERING_PLAN",
            "ERR_LETTERING_SPEAKER_REQUIRED",
            "ERR_LETTERING_SPEAKER_SCOPE",
            "ERR_LETTERING_LINE_TOO_LONG",
            "ERR_LETTERING_WORD_LIMIT",
        }
        for result in results
    ):
        return True
    if not any(result.status == "success" for result in results):
        return False
    completed_ids = {result.tool_id for result in results if result.status == "success"}
    if "planning.plan_panels" in completed_ids and (
        _requested_single_page_panel_count(user_text) or _is_explicit_story_plan_request(user_text)
    ):
        return False
    if "planning.plan_panels" in completed_ids and "generation.generate_image" in completed_ids:
        # The coordinator completes the remaining planned generation and page
        # assembly deterministically; another model turn would only repeat the
        # same plan in prose and increase token cost.
        return False
    text = (user_text or "").lower()
    asks_for_action = bool(re.search(
        r"\b(create|add|make|generate|draw|apply|update|revise|propose|place|"
        r"start|proceed|yes|do\s+it|go\s+ahead|continue|finish|complete|"
        r"turn|comic|panels?|scene|page|"
        r"أضف|أنشئ|ارسم|ولد|ابدأ|أكمل|نعم|تابع)\b",
        text
    ))
    for result in results:
        tool_id = result.tool_id
        if tool_id in {"planning.plan_panels", "canvas.create_page_from_template", "canon.inspect_characters", "canon.inspect_reference_anchor", "creative.get_package", "creative.develop_universe"} and asks_for_action:
            return True
    return False


def _latest_current_turn_panel_plan(results: List[ToolResult]) -> Optional[ToolResult]:
    """Return the newest successful plan produced for the current user turn."""
    return next((
        result for result in reversed(results)
        if result.tool_id == "planning.plan_panels"
        and result.status == "success"
        and (result.output or {}).get("plans")
    ), None)


def _latest_current_turn_panel_plan_failure(results: List[ToolResult]) -> Optional[ToolResult]:
    """Return the newest failed/blocked panel plan from this chat turn."""
    return next((
        result for result in reversed(results)
        if result.tool_id == "planning.plan_panels"
        and result.status in {"failed", "blocked"}
    ), None)


def _requested_single_page_panel_count(text: str) -> Optional[int]:
    """Return an explicit one-page panel count; never infer a count from prose."""
    query = normalize_panel_spelling(text or "").casefold()
    if not re.search(r"\b(?:1|one)\s*(?:comic\s*)?page\b", query):
        return None
    match = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+panels?\b", query)
    if not match:
        return None
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    count = int(match.group(1)) if match.group(1).isdigit() else words[match.group(1)]
    return count if 1 <= count <= 24 else None


def _pending_panel_count_is_default(action: Any) -> bool:
    if not isinstance(action, dict):
        return False
    source = action.get("panel_count_source")
    return source == "default" or (source is None and not action.get("plan"))


def _is_explicit_story_plan_request(text: str) -> bool:
    query = normalize_panel_spelling(text or "").casefold()
    return bool(
        re.search(r"\b\d{1,2}\s*(?:-| )?pages?\b", query)
        or re.search(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten)[ -]?pages?\b", query)
        or re.search(r"\b\d{1,2}\s+panels?\s+per\s+page\b", query)
        or re.search(r"\bpanels?\s+per\s+page\b", query)
    )


def _is_plan_only_story_request(text: str) -> bool:
    query = normalize_panel_spelling(text or "").casefold().strip()
    return bool(
        re.search(r"\b(?:without|don't|dont|do not|no)\b.{0,40}\b(?:images?|artwork|generation|production)\b", query)
        or re.search(r"\b(?:plan|outline|blueprint)\s+only\b|\b(?:for review|preview only)\b", query)
        or re.match(r"^(?:plan|outline|blueprint)\b", query)
        or re.match(r"^(?:make|create|write|draft)\s+(?:a|the)\s+(?:story\s+)?(?:plan|outline|blueprint)\b", query)
    )


def _is_explicit_story_creation_request(text: str) -> bool:
    """Creation requests with an exact page count should start after a valid plan."""
    query = normalize_panel_spelling(text or "").casefold().strip()
    if not query or not _is_explicit_story_plan_request(query) or _is_plan_only_story_request(query):
        return False
    return bool(re.search(r"\b(?:make|create|generate|build|produce|draw)\b", query))


def _is_new_panel_plan_request(text: str) -> bool:
    query = normalize_panel_spelling(text or "").casefold()
    return bool(re.search(r"\b(?:make|create|generate|build|draw)\s+(?:some\s+|new\s+|the\s+)?(?:comic\s+)?panels?\b", query))


def _message_value(message, key: str, default=None):
    return message.get(key, default) if isinstance(message, dict) else getattr(message, key, default)


def _latest_saved_story_job(session, project_id: str):
    """Return the newest project scoped checkpoint, including interrupted turns."""
    metadata = _message_value(session, "metadata", {}) or {}
    jobs = metadata.get("story_production_jobs", {}) if isinstance(metadata, dict) else {}
    candidates = []
    if isinstance(jobs, dict):
        for value in jobs.values():
            if not isinstance(value, dict) or value.get("project_id") != project_id:
                continue
            plan = value.get("plan")
            if isinstance(plan, dict) and plan.get("plans"):
                candidates.append(value)
    return max(candidates, key=lambda item: str(item.get("updated_at", "")), default=None)


def _is_pending_page_story_continuation(session, text: str, project_id: str) -> bool:
    """Only explicit resume commands may claim an older saved production job."""
    query = (text or "").casefold().strip()
    if not query:
        return False
    is_story = (len(query) >= 180) or bool(re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", text or "") and len(query) >= 100)
    if is_story:
        return False
    # Pure affirmations ('yes', 'yes pls') accept adaptation offers and are handled by the plan review flow
    is_pure_affirmation = bool(re.fullmatch(r"\s*(?:yes|yes\s+pls|yes\s+please|sure|yep|yeah|ok|okay|نعم|ماشي|أكيد)\s*[!.]*\s*", query))
    pending_action = (getattr(session, "metadata", {}) or {}).get("pending_story_action")
    if is_pure_affirmation and pending_action and pending_action.get("status") in ("offer_made", "plan_ready"):
        return False

    resume_requested = bool(
        re.fullmatch(r"(?:start|do\s+it|go\s+ahead|go|continue|finish|resume|proceed)(?:\s+(?:production|comic|panels?|generation|it))?[!.]*", query)
        or re.search(r"\b(?:continue|resume|finish|proceed)\b", query)
        or re.search(r"\b(?:continue|resume|finish|assemble|start)\s+(?:the\s+)?(?:saved\s+)?(?:story|production|panels?|canvas|comic)\b", query)
        or re.search(r"\badd\s+to\s+(?:the\s+)?canvas\b", query)
        or re.search(r"\bretry\s+(?:(?:failed\s+)?panel\s+)?[a-z0-9][a-z0-9_-]*\b", query)
        or selected_cast_repair_requested(query)
        or re.search(r"\b(?:تابع|أكمل|استأنف|ابدأ)\b", query)
    )
    if not resume_requested:
        return False
    messages = _message_value(session, "messages", []) or []
    plan_index = None
    for idx in range(len(messages) - 1, -1, -1):
        message = messages[idx]
        if _message_value(message, "role") != "assistant":
            continue
        for result in (_message_value(message, "tool_results", []) or []):
            if (
                _message_value(result, "tool_id") == "planning.plan_panels"
                and _message_value(result, "status") == "success"
                and (_message_value(result, "output", {}) or {}).get("plans")
            ):
                plan_index = idx
                break
        if plan_index is not None:
            break
    has_prior_story = any(
        (len((_message_value(m, "text", "") or "").strip()) >= 120)
        or bool(re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", _message_value(m, "text", "") or ""))
        for m in messages if _message_value(m, "role") == "user"
    )
    has_pending_action = bool((getattr(session, "metadata", {}) or {}).get("pending_story_action"))
    if plan_index is None and _latest_saved_story_job(session, project_id) is None and not has_prior_story and not has_pending_action:
        return False
    # A single verified page is not proof the whole story completed. The
    # workflow itself is idempotent, so always resume it (or return its saved
    # completed status) instead of asking the model to plan/search again.
    return True

def _extract_story_title_and_hash(text: str) -> tuple[str, str]:
    """Extract clean title and cryptographic content hash for a story text."""
    cleaned = (text or "").strip()
    headings = re.findall(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(.+)$", cleaned)
    if len(headings) >= 2:
        title = f"{headings[0]} — {headings[1]}"
    elif headings:
        title = headings[0]
    else:
        first_line = cleaned.splitlines()[0] if cleaned else "Story Brief"
        title = first_line[:60]
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    return title.strip(" *#_"), digest


def _find_matching_saved_plan_for_story(project_id: str, story_text: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Finds an exact matching plan saved in the project for this story.
    Strictly reuses a successful plan only when its project and exact source-story
    hash or normalized content match; otherwise returns (None, None) so a
    fresh outline is created.
    """
    story_clean = (story_text or "").strip()
    if not story_clean:
        return None, None
    norm_text = " ".join(story_clean.split())
    story_hash = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
    story_prefix = norm_text[:250].casefold()
    sessions_dir = PROJECT_ROOT / "runs" / "agent_sessions"
    if not sessions_dir.exists():
        return None, None

    exact_hash_candidates = []

    for session_file in sessions_dir.glob("*.json"):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or data.get("project_id") != project_id:
                continue

            session_messages = data.get("messages", []) or []
            session_matched_story = False
            for m in session_messages:
                if m.get("role") == "user":
                    m_txt = (m.get("text", "") or "").strip()
                    norm_m = " ".join(m_txt.split())
                    m_hash = hashlib.sha256(norm_m.encode("utf-8")).hexdigest()
                    if m_hash == story_hash or (len(norm_m) >= 200 and len(norm_text) >= 200 and norm_m[:250].casefold() == story_prefix):
                        session_matched_story = True
                        break

            if not session_matched_story:
                continue

            for m in session_messages:
                for res in (m.get("tool_results", []) or []):
                    if res.get("tool_id") == "planning.plan_panels" and res.get("status") == "success":
                        out = res.get("output", {})
                        plans = out.get("plans", [])
                        if not plans:
                            continue
                        call_id = res.get("call_id")
                        exact_hash_candidates.append((out, call_id))
        except Exception:
            continue

    if exact_hash_candidates:
        return max(exact_hash_candidates, key=lambda c: len(c[0].get("plans", [])))
    return None, None


class AgentCoordinator:
    """Central project-level agent orchestrating specialist tool execution and chat."""

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        model_client: Optional[AgentModelClient] = None,
        session_store: Optional[SessionStore] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ):
        self.registry = registry or CapabilityRegistry.get_instance()
        self.model_client = model_client or AgentModelClient()
        self.session_store = session_store or SessionStore.get_instance()
        self.approval_manager = approval_manager or ApprovalManager.get_instance()

    def process_chat_turn(
        self,
        project_id: str,
        user_text: str,
        attachments: Optional[List[AgentAttachment]] = None,
        session_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        spend_limit_usd: Optional[float] = None,
        offline_mode: Optional[bool] = None,
        selected_character_ids: Optional[List[str]] = None,
        selected_style_profile_id: Optional[str] = None,
        selected_style_version: Optional[int] = None,
        selected_location_id: Optional[str] = None,
        selected_location_version: Optional[int] = None,
        activity_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        canvas_page_id: Optional[str] = None,
        canvas_panel_id: Optional[str] = None,
        canvas_expected_revision: Optional[int] = None,
    ) -> AgentMessage:
        """
        Executes a complete multimodal chat turn:
        1. Loads authoritative project context & budgets.
        2. Dispatches model-driven tool selection loop (bounded, max 2 rounds).
        3. Enforces budget headroom, schema validation, and approval gates.
        4. Persists durable session turn and event trace.
        """
        if offline_mode is None:
            offline_mode = os.getenv("INKLOOP_OFFLINE_MODE", "0") in ("1", "true", "True")

        attachments = attachments or []
        session_id = session_id or f"session_{project_id}"
        session = self.session_store.get_session(session_id)
        if session and session.project_id != project_id:
            # Reject a stale chat ID before adding this project's prompt or running tools.
            raise ValueError(
                "This Agent chat belongs to a different project. Start a new chat for the active project; your message was not saved."
            )
        if not session:
            session = self.session_store.create_session(project_id=project_id, session_id=session_id)

        # 1. Load authoritative project context & budgets
        bible = _get_project_bible(project_id)
        selected_character_ids = list(selected_character_ids or [])
        if not selected_character_ids and user_text:
            text_lower = user_text.lower()
            detected = [
                cid for cid, char in bible.characters.items()
                if cid.lower() in text_lower or (getattr(char, "name", None) and char.name.lower() in text_lower)
            ]
            if detected:
                selected_character_ids = detected
            elif session and session.messages:
                # Resolve pronouns ("him", "her", "he", "she") or short follow-ups ("anything", "continue")
                pronouns_or_followup = {"him", "her", "he", "she", "them", "they", "his", "hers", "anything", "whatever", "continue", "yes", "do it"}
                words = set(re.findall(r"\b\w+\b", text_lower))
                if words & pronouns_or_followup:
                    for prev_m in reversed(session.messages[-6:]):
                        prev_txt = (prev_m.text or "").lower()
                        for cid, char in bible.characters.items():
                            if cid.lower() in prev_txt or (getattr(char, "name", None) and char.name.lower() in prev_txt):
                                selected_character_ids = [cid]
                                break
                        if selected_character_ids:
                            break

        unknown_characters = sorted(set(selected_character_ids) - set(bible.characters))
        if unknown_characters:
            raise ValueError(f"Selected characters are not declared in the active Story Bible: {', '.join(unknown_characters)}")

        canvas_target = None
        if canvas_page_id or canvas_panel_id or canvas_expected_revision is not None:
            if not canvas_page_id or not canvas_panel_id or canvas_expected_revision is None:
                raise ValueError("Canvas placement needs a selected page, panel, and page revision.")
            _page_store, canvas_document = self.registry._editor_page(canvas_page_id, {"project_id": project_id})
            if canvas_document.revision != canvas_expected_revision:
                raise ValueError(
                    f"Canvas page changed from revision {canvas_expected_revision} to {canvas_document.revision}; refresh the editor and retry."
                )
            if canvas_document.layout.get_panel(canvas_panel_id) is None:
                raise ValueError(f"Selected panel '{canvas_panel_id}' is not on Canvas page '{canvas_page_id}'.")
            target_slot = canvas_document.layout.get_panel(canvas_panel_id)
            from app.editor.models import LayerKind
            panel_layers = [
                layer for layer in canvas_document.layers
                if layer.panel_id == canvas_panel_id
            ]
            panel_artwork = next((
                layer for layer in panel_layers if layer.kind == LayerKind.IMAGE
            ), None)
            canvas_target = {
                "page_id": canvas_page_id,
                "panel_id": canvas_panel_id,
                "expected_revision": canvas_expected_revision,
                "replace_existing": panel_artwork is not None,
                # The active persisted panel is the authority for image shape.
                # The provider only treats these values as an aspect-ratio hint.
                "width": max(1, round(target_slot.rect.width)),
                "height": max(1, round(target_slot.rect.height)),
            }

        canvas_page_context = None
        if canvas_page_id:
            # Give the model the authoritative IDs and current contents from the
            # same page document the manual editor opens. This prevents guessed
            # panel IDs and lets it target dialogue/artwork to the correct slot.
            page_for_context = canvas_document
            from app.editor.models import LayerKind
            layers_by_panel: Dict[str, List[Dict[str, Any]]] = {}
            for layer in page_for_context.layers:
                if not layer.panel_id:
                    continue
                summary = {
                    "layer_id": layer.layer_id,
                    "kind": layer.kind.value,
                    "source_asset_id": layer.source_asset_id,
                }
                if layer.kind == LayerKind.TEXT:
                    summary["text"] = str(layer.metadata.get("text") or "")[:160]
                    summary["bubble_id"] = layer.metadata.get("bubble_id")
                    summary["bubble_shape"] = layer.metadata.get("bubble_shape")
                    summary["speaker"] = layer.metadata.get("speaker")
                    summary["speaker_character_id"] = layer.metadata.get("speaker_character_id")
                    summary["tail_target"] = layer.metadata.get("tail_target")
                layers_by_panel.setdefault(layer.panel_id, []).append(summary)
            page_trim = getattr(page_for_context.layout, "trim_box", None)
            if page_trim is None:
                from app.contracts.geometry import Rect
                slots = page_for_context.layout.panel_slots
                page_trim = Rect(
                    x=min((slot.rect.x for slot in slots), default=0),
                    y=min((slot.rect.y for slot in slots), default=0),
                    width=max((slot.rect.x + slot.rect.width for slot in slots), default=1) - min((slot.rect.x for slot in slots), default=0),
                    height=max((slot.rect.y + slot.rect.height for slot in slots), default=1) - min((slot.rect.y for slot in slots), default=0),
                )
            canvas_page_context = {
                "page_id": page_for_context.page_id,
                "project_id": page_for_context.project_id,
                "revision": page_for_context.revision,
                "trim_box": page_trim.model_dump(mode="json"),
                "reading_order_panel_ids": list(page_for_context.layout.reading_order_panel_ids),
                "panels": [
                    {
                        "panel_id": slot.panel_id,
                        "reading_order": slot.reading_order,
                        "rect": slot.rect.model_dump(mode="json"),
                        "story_beat": (getattr(getattr(getattr(slot, "descriptor", None), "narrative", None), "scene_beat_description", None) or "")[:220] or None,
                        "layers": layers_by_panel.get(slot.panel_id, []),
                    }
                    for slot in page_for_context.layout.panel_slots
                ],
            }

        selected_style_profile = None
        if selected_style_profile_id:
            from app.creative.storage import get_creative_profile_store
            selected_style_profile = get_creative_profile_store().get_style_profile(project_id, selected_style_profile_id)
            if not selected_style_profile:
                raise ValueError(f"Selected style profile '{selected_style_profile_id}' was not found in the active project.")
            if selected_style_version is not None and selected_style_profile.version != selected_style_version:
                raise ValueError(f"Selected style profile changed from version {selected_style_version} to {selected_style_profile.version}; refresh the style selection.")

        selected_location = None
        if selected_location_id:
            from app.creative.service import CreativeDirectorService
            package = CreativeDirectorService.get_instance().get_package(project_id)
            selected_location = package.world_bible.locations.get(selected_location_id) if package else None
            if not selected_location:
                raise ValueError(f"Selected location '{selected_location_id}' was not found in the active project.")
            if selected_location_version is not None and selected_location.version != selected_location_version:
                raise ValueError(f"Selected location changed from version {selected_location_version} to {selected_location.version}; refresh the location selection.")
        canon_hash = bible.canon_hash or ""
        bible_ver = getattr(bible, "bible_version", getattr(bible, "version", 1))

        from app.api.routers.execution import get_execution_manager
        em = get_execution_manager()
        avail_budget = float(em.budget_manager.get_available_budget())

        # Parse requested run budget ceiling if present in query or spend_limit_usd
        req_cap = spend_limit_usd
        if req_cap is None and user_text:
            m = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", user_text)
            if m:
                req_cap = float(m.group(1))

        effective_cap = min(avail_budget, req_cap) if req_cap is not None else avail_budget

        available_object_profiles = []
        bible_props = getattr(bible, "props", {}) or {}
        for prop_id, prop in sorted(bible_props.items(), key=lambda item: str(item[0])):
            ref_assets = list(getattr(prop, "reference_assets", []) or [])
            available_object_profiles.append({
                "prop_id": str(prop_id),
                "version": str(getattr(prop, "version", 1) or 1),
                "name": str(getattr(prop, "name", prop_id) or prop_id),
                "description": str(getattr(prop, "description", "") or "")[:400],
                "form_and_proportions": str(getattr(prop, "form_and_proportions", "") or "")[:400],
                "materials": list(getattr(prop, "materials", []) or [])[:8],
                "palette": list(getattr(prop, "palette", []) or [])[:8],
                "components": list(getattr(prop, "components", []) or [])[:12],
                "distinctive_marks": list(getattr(prop, "distinctive_marks", []) or [])[:8],
                "stable_invariants": list(getattr(prop, "stable_invariants", []) or getattr(prop, "required_attributes", []) or [])[:12],
                "allowed_states": list(getattr(prop, "allowed_states", []) or getattr(prop, "permitted_variations", []) or [])[:12],
                "approval_status": str(getattr(prop, "approval_status", "approved")),
                "reference_asset_ids": [str(ref.asset_id) for ref in ref_assets if getattr(ref, "asset_id", None)],
            })

        project_ctx = {
            "project_id": project_id,
            "canon_hash": canon_hash,
            "bible_version": bible_ver,
            "available_budget_usd": avail_budget,
            "project_available_budget_usd": avail_budget,
            "requested_run_budget_cap_usd": req_cap,
            "effective_run_budget_cap_usd": effective_cap,
            "approval_id": approval_id,
            "offline_mode": offline_mode,
            "selected_character_ids": selected_character_ids,
            "declared_characters": list(bible.characters.keys()),
            "selected_character_profiles": [
                {
                    "character_id": character_id,
                    "name": getattr(bible.characters[character_id], "name", character_id),
                    "entity_kind": getattr(bible.characters[character_id], "entity_kind", "unspecified being"),
                    "morphology": getattr(bible.characters[character_id], "morphology", ""),
                    "surface_description": getattr(bible.characters[character_id], "surface_description", ""),
                    "visual_invariants": list(getattr(bible.characters[character_id], "visual_invariants", []) or []),
                    "clothing_attributes": list(getattr(bible.characters[character_id], "clothing_attributes", []) or []),
                    "canon_version": getattr(bible.characters[character_id], "canon_version", 1),
                }
                for character_id in selected_character_ids if character_id in bible.characters
            ],
            "available_object_profiles": available_object_profiles,
            "selected_style_profile": ({
                "profile_id": selected_style_profile.profile_id,
                "version": selected_style_profile.version,
                "name": selected_style_profile.name,
                "status": selected_style_profile.status.value if hasattr(selected_style_profile.status, "value") else str(selected_style_profile.status),
                "style_prompt_core": selected_style_profile.style_prompt_core,
                "negative_constraints": selected_style_profile.negative_constraints,
                "reference_asset_ids": [ref.asset_id for ref in selected_style_profile.references],
                "analysis_summary": selected_style_profile.analysis.analysis_summary if selected_style_profile.analysis else None,
            } if selected_style_profile else None),
            "selected_location": ({
                "location_id": selected_location.location_id,
                "version": selected_location.version,
                "name": selected_location.name,
                "atmosphere": selected_location.atmosphere,
                "spatial_layout": selected_location.spatial_layout,
                "visual_anchors": selected_location.visual_anchors,
                "lighting_conditions": selected_location.lighting_conditions,
                "continuity_rules": selected_location.continuity_rules,
                "zones": selected_location.zones,
                "environment_details": selected_location.environment_details,
            } if selected_location else None),
            "canvas_target": canvas_target,
            "canvas_page_context": canvas_page_context,
        }

        # 2. Record User Turn
        user_msg = AgentMessage(
            message_id=f"msg_user_{int(time.time()*1000)}",
            role="user",
            text=user_text,
            attachments=attachments,
            request_context={
                "selected_character_ids": list(selected_character_ids),
                "selected_style_profile_id": selected_style_profile_id,
                "selected_style_version": selected_style_version,
                "selected_location_id": selected_location_id,
                "selected_location_version": selected_location_version,
                "spend_limit_usd": req_cap,
                "canvas_page_id": canvas_page_id,
                "canvas_panel_id": canvas_panel_id,
                "canvas_expected_revision": canvas_expected_revision,
            },
        )
        self.session_store.append_message(session_id, user_msg)

        # Check pending story adaptation action state
        session_meta = getattr(session, "metadata", {}) or {}
        pending_action = session_meta.get("pending_story_action")
        if isinstance(pending_action, dict) and pending_action.get("status") == "plan_ready":
            saved_plans = (pending_action.get("plan") or {}).get("plans")
            story_blueprint = (pending_action.get("plan") or {}).get("story_blueprint") or {}
            expected_pages = pending_action.get("page_count")
            pages_valid = (
                expected_pages is None
                or (len(story_blueprint.get("pages") or []) == expected_pages
                    and int((pending_action.get("plan") or {}).get("page_count") or 0) == expected_pages)
            )
            if not isinstance(saved_plans, list) or not saved_plans or len(saved_plans) != pending_action.get("panel_count") or not pages_valid:
                # Older builds could mark the default six-panel offer ready
                # even though planning failed. Demote that false-ready state
                # before it can be offered or resumed as a saved plan.
                pending_action["status"] = "offer_made"
                pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
                session.metadata["pending_story_action"] = pending_action
                self.session_store.save_session(session)
        is_clean_affirmation = bool(re.fullmatch(r"\s*(?:yes|yes\s+pls|yes\s+please|sure|yep|yeah|ok|okay|نعم|ماشي|أكيد)\s*[!.]*\s*", (user_text or "").casefold()))
        requested_page_count = _requested_page_count(user_text)
        is_skip_request = bool(re.fullmatch(r"\s*(?:skip|no|no\s+thanks|cancel\s+plan|discard\s+plan)[!.\s]*", (user_text or "").casefold()))

        if requested_page_count is not None and (requested_page_count < 1 or requested_page_count > 50):
            if pending_action and pending_action.get("page_count"):
                pending_action["status"] = "needs_attention"
                pending_action["plan_invalidated"] = True
                pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
                session.metadata["pending_story_action"] = pending_action
                self.session_store.save_session(session)
            limit_msg = AgentMessage(
                message_id=f"msg_page_limit_{int(time.time()*1000)}",
                role="assistant",
                text=f"I can plan between 1 and 50 pages in one story job. This request asks for {requested_page_count} pages, so I stopped before planning or generating anything.",
                activity_state="idle",
                pending_story_action=PendingStoryAction.model_validate(pending_action) if pending_action else None,
            )
            self.session_store.append_message(session_id, limit_msg)
            return limit_msg

        if pending_action and pending_action.get("status") == "plan_ready" and is_skip_request:
            pending_action["status"] = "skipped"
            pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
            session.metadata["pending_story_action"] = pending_action
            self.session_store.save_session(session)
            skipped_msg = AgentMessage(
                message_id=f"msg_skip_{int(time.time()*1000)}",
                role="assistant",
                text="Plan skipped. No images were generated and no Canvas pages were created. You can ask for a revised plan whenever you’re ready.",
                activity_state="idle",
                pending_story_action=PendingStoryAction.model_validate(pending_action),
            )
            self.session_store.append_message(session_id, skipped_msg)
            return skipped_msg

        explicit_start_command = bool(re.fullmatch(
            r"\s*(?:start|start\s+production|go\s+ahead|proceed|continue\s+production|resume\s+production|yes|yes\s+please)[!.\s]*",
            (user_text or "").casefold(),
        ))
        if (
            pending_action
            and pending_action.get("page_count")
            and pending_action.get("status") != "plan_ready"
            and explicit_start_command
            and not (
                isinstance(pending_action.get("plan"), dict)
                and bool(pending_action.get("plan", {}).get("plans"))
                and not pending_action.get("plan_invalidated")
            )
            and (pending_action.get("plan_invalidated") or _latest_saved_story_job(session, project_id) is None)
        ):
            blocked_msg = AgentMessage(
                message_id=f"msg_plan_gate_{int(time.time()*1000)}",
                role="assistant",
                text="There is no validated page plan to start yet. I have not generated images. Ask for the story plan again or describe the change you want, and I’ll prepare a complete plan for review first.",
                activity_state="idle",
                pending_story_action=PendingStoryAction.model_validate(pending_action),
            )
            self.session_store.append_message(session_id, blocked_msg)
            return blocked_msg

        is_story_submission = (len(user_text.strip()) >= 180) or bool(re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", user_text) and len(user_text.strip()) >= 120)
        if is_story_submission:
            title, story_hash = _extract_story_title_and_hash(user_text)
            matched_plan, plan_cid = _find_matching_saved_plan_for_story(project_id, user_text)
            if requested_page_count and matched_plan and int(matched_plan.get("page_count") or 0) != requested_page_count:
                matched_plan, plan_cid = None, None
            creator_panel_count = _requested_single_page_panel_count(user_text) or explicit_request_panel_count(user_text)
            if matched_plan:
                pending_panel_count = len(matched_plan.get("plans", []))
                panel_count_source = "saved_plan"
            elif creator_panel_count is not None:
                pending_panel_count = creator_panel_count
                panel_count_source = "creator_request"
            else:
                _, count_warning, _ = recover_panel_plan_arguments(
                    {},
                    current_request=user_text,
                    recent_user_texts=[(user_msg.message_id, user_text)],
                    character_names={cid: str(getattr(c, "name", "") or "") for cid, c in bible.characters.items()},
                    selected_character_ids=selected_character_ids,
                )
                pending_panel_count = int((count_warning or {}).get("panel_count") or 6)
                panel_count_source = "default"
            pending_action = {
                "schema_version": "1.0.0",
                "action_type": "adapt_story_to_comic",
                "source_message_id": user_msg.message_id,
                "source_story_hash": story_hash,
                "source_title": title,
                "status": "plan_ready" if matched_plan else "offer_made",
                "panel_count": int((matched_plan or {}).get("total_panel_count") or pending_panel_count),
                "panel_count_source": panel_count_source,
                "page_count": requested_page_count,
                "total_panel_count": int((matched_plan or {}).get("total_panel_count") or pending_panel_count) if matched_plan else (pending_panel_count if not requested_page_count else 0),
                "page_panel_counts": dict((matched_plan or {}).get("page_panel_counts") or {}),
                "estimated_cost_usd": None,
                "assumptions": list((matched_plan or {}).get("assumptions") or []),
                "plan": matched_plan,
                "plan_call_id": plan_cid,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            session.metadata["pending_story_action"] = pending_action
            self.session_store.save_session(session)

        elif requested_page_count and requested_page_count > 1:
            title, story_hash = _extract_story_title_and_hash(user_text)
            pending_action = {
                "schema_version": "1.1.0",
                "action_type": "produce_story_book",
                "source_message_id": user_msg.message_id,
                "source_story_hash": story_hash,
                "source_title": title,
                "status": "planning",
                "panel_count": 0,
                "total_panel_count": 0,
                "page_count": requested_page_count,
                "page_panel_counts": {},
                "estimated_cost_usd": None,
                "assumptions": [],
                "panel_count_source": "page_request",
                "plan": None,
                "plan_call_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            session.metadata["pending_story_action"] = pending_action
            self.session_store.save_session(session)

        elif pending_action and pending_action.get("status") in ("offer_made", "plan_ready") and is_clean_affirmation and not pending_action.get("page_count"):
            # Creator accepted the adaptation offer!
            plan_call = None
            plan_result = None
            plan_error = None
            if not pending_action.get("plan"):
                source_text = ""
                for m in session.messages:
                    if m.message_id == pending_action.get("source_message_id"):
                        source_text = m.text
                        break
                if not source_text:
                    for m in reversed(session.messages):
                        if m.role == "user" and len((m.text or "").strip()) >= 80:
                            source_text = m.text
                            break
                if source_text:
                    matched_plan, plan_cid = _find_matching_saved_plan_for_story(project_id, source_text)
                    if matched_plan:
                        pending_action["plan"] = matched_plan
                        pending_action["plan_call_id"] = plan_cid
                        pending_action["panel_count"] = len(matched_plan.get("plans", []))
                        pending_action["panel_count_source"] = "saved_plan"

            if not pending_action.get("plan"):
                repaired_args, repair_warning, repair_error = recover_panel_plan_arguments(
                    {},
                    current_request=user_text,
                    recent_user_texts=[(m.message_id, m.text) for m in session.messages if m.role == "user"],
                    character_names={cid: str(getattr(c, "name", "") or "") for cid, c in bible.characters.items()},
                    selected_character_ids=selected_character_ids,
                    expected_panel_count=pending_action.get("panel_count"),
                    expected_panel_count_is_default=_pending_panel_count_is_default(pending_action),
                )
                if repair_error:
                    plan_error = repair_error
                elif repaired_args.get("beats"):
                    tool_context = {**project_ctx, "_agent_chat": True}
                    tool_context["_user_text"] = user_text
                    tool_context["_authored_user_texts"] = [
                        str(_message_value(message, "text", ""))
                        for message in session.messages
                        if _message_value(message, "role") == "user"
                    ] + [user_text]
                    if repair_warning:
                        tool_context["_panel_plan_input_warnings"] = [repair_warning]
                    repaired_args.pop("panel_count", None)
                    repaired_args.pop("panel_outline", None)
                    plan_call = ToolCall(call_id=f"plan_auto_{int(time.time()*1000)}", tool_id="planning.plan_panels", arguments=repaired_args)
                    if activity_callback:
                        activity_callback({"call_id": plan_call.call_id, "tool_id": plan_call.tool_id, "status": "running"})
                    plan_result = self.registry.dispatch(plan_call, tool_context)
                    if plan_result.status == "success" and (plan_result.output or {}).get("plans"):
                        pending_action["plan"] = plan_result.output
                        pending_action["plan_call_id"] = plan_call.call_id
                        pending_action["panel_count"] = len(plan_result.output["plans"])
                        pending_action["panel_count_source"] = "saved_plan"
                    else:
                        plan_error = plan_result.error or "The planner did not return a saved panel plan."
                    if activity_callback:
                        activity_callback({
                            "call_id": plan_call.call_id,
                            "tool_id": plan_call.tool_id,
                            "status": plan_result.status,
                            "duration_seconds": plan_result.duration_seconds,
                            "error": plan_result.error,
                        })

            has_plan = bool((pending_action.get("plan") or {}).get("plans"))
            pending_action["status"] = "plan_ready" if has_plan else "offer_made"
            pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
            session.metadata["pending_story_action"] = pending_action
            self.session_store.save_session(session)

            p_count = pending_action.get("panel_count", 6)
            title = pending_action.get("source_title", "Story")
            plan_obj = pending_action.get("plan") or {}
            scene_summary = plan_obj.get("scene_summary") or title
            if has_plan:
                affirmation_reply = (
                    f"### Comic Adaptation Plan Ready: {title}\n\n"
                    f"I have prepared the **{p_count}-panel comic plan** for this story.\n"
                    f"- **Scene:** {scene_summary}\n"
                    f"- **Panels:** {p_count} planned beats across page layout\n"
                    f"- **Characters:** {', '.join(selected_character_ids) or 'Canonical cast'}\n"
                    f"- **Status:** Verified and ready for production\n\n"
                    f"> Reply **'start'**, **'continue'**, or click **Start Production** above to begin generating artwork and assembling Canvas pages."
                )
            else:
                affirmation_reply = (
                    f"I couldn't prepare a valid panel plan for **{title}**, so production has not started.\n\n"
                    f"{plan_error or 'No saved plan was returned.'}"
                )
            assistant_msg = AgentMessage(
                message_id=f"msg_asst_{int(time.time()*1000)}",
                role="assistant",
                text=affirmation_reply,
                tool_calls=[plan_call] if plan_call else [],
                tool_results=[plan_result] if plan_result else [],
                activity_state="idle",
                pending_story_action=PendingStoryAction.model_validate(pending_action),
            )
            self.session_store.append_message(session_id, assistant_msg)
            return assistant_msg

        # 3. Iterative Tool Loop
        # The image-generator chat only advertises implemented tools within its
        # own workflow. The registry checks both status and adapter presence.
        expected_page_count = (
            int(pending_action.get("page_count"))
            if isinstance(pending_action, dict) and pending_action.get("page_count")
            else None
        )
        is_page_plan_edit = bool(
            pending_action
            and pending_action.get("status") == "plan_ready"
            and expected_page_count
            and not lettering_only_requested(user_text)
            and not (is_clean_affirmation or production_action_requested(user_text) or is_skip_request)
        )
        available_tools = _tools_for_turn(
            self.registry.list_image_chat_tools(), user_text,
            expected_page_count=expected_page_count,
            selected_character_profiles=project_ctx.get("selected_character_profiles"),
            available_object_profiles=available_object_profiles,
        )
        pending_page_start = bool(
            pending_action
            and pending_action.get("status") == "plan_ready"
            and pending_action.get("page_count")
            and (is_clean_affirmation or production_action_requested(user_text))
        )
        lettering_request = lettering_only_requested(user_text)
        saved_lettering_job = _latest_saved_story_job(session, project_id) if lettering_request else None
        lettering_job_ready = saved_job_ready_for_lettering(saved_lettering_job)
        if lettering_request and lettering_job_ready:
            # A lettering continuation inherits the exact project and cast of its
            # saved artwork job, even when the composer selection is empty.
            selected_character_ids = [
                character_id for character_id in (saved_lettering_job.get("selected_character_ids") or [])
                if character_id in bible.characters
            ]
            project_ctx["selected_character_ids"] = selected_character_ids
            project_ctx["selected_character_profiles"] = [
                {
                    "character_id": character_id,
                    "name": getattr(bible.characters[character_id], "name", character_id),
                    "entity_kind": getattr(bible.characters[character_id], "entity_kind", "unspecified being"),
                    "visual_invariants": list(getattr(bible.characters[character_id], "visual_invariants", []) or []),
                    "canon_version": getattr(bible.characters[character_id], "canon_version", 1),
                }
                for character_id in selected_character_ids
            ]
            panel_rows = []
            saved_panels = saved_lettering_job.get("panels") or {}
            story_local_cast = saved_lettering_job.get("plan", {}).get("story_local_cast") or []
            story_local_by_id = {
                str(item.get("speaker_id")): item
                for item in story_local_cast if isinstance(item, dict) and item.get("speaker_id")
            }
            for panel in saved_lettering_job.get("plan", {}).get("plans", []) or []:
                if not isinstance(panel, dict) or not panel.get("panel_id"):
                    continue
                panel_id = str(panel["panel_id"])
                production_panel = saved_panels.get(panel_id) or {}
                character_ids = list(production_panel.get("character_ids") or panel.get("character_ids") or [])
                panel_rows.append({
                    "panel_id": panel_id,
                    "page_number": production_panel.get("page_number") or panel.get("page_number"),
                    "story_event": panel.get("story_event"),
                    "visual_focus": panel.get("visual_focus"),
                    "narrative_function": panel.get("narrative_function"),
                    "emotional_intent": panel.get("emotional_intent"),
                    "character_ids": character_ids,
                    "saved_text": panel.get("text") if (panel.get("text") or {}).get("text_content") else None,
                    "characters": [
                        {
                            "character_id": character_id,
                            "name": (
                                getattr(bible.characters[character_id], "name", character_id)
                                if character_id in bible.characters
                                else str((story_local_by_id.get(character_id) or {}).get("name") or character_id)
                            ),
                            "is_story_local": character_id in story_local_by_id,
                            "visual_description": (story_local_by_id.get(character_id) or {}).get("visual_description"),
                        }
                        for character_id in character_ids
                    ],
                    "existing_text_layer_ids": list(production_panel.get("text_layer_ids") or []),
                })
            project_ctx["saved_lettering_context"] = {
                "job_id": saved_lettering_job.get("job_id"),
                "project_id": project_id,
                    "goal": "Add only model-planned editable text/bubbles to this saved page set; preserve every existing artwork asset and page geometry.",
                "pages": [
                    {"page_number": page.get("page_number"), "page_id": page.get("page_id"), "revision": page.get("revision")}
                    for page in saved_lettering_job.get("pages", []) if isinstance(page, dict)
                ],
                "panels": panel_rows,
                "rules": [
                    "Use only these exact panel IDs and each panel's selected character IDs.",
                    "Base text on saved story events and visual focus; do not reinterpret non-story source documents as plot.",
                    "Choose spoken dialogue, internal thought, concise narration/caption, or no text per panel.",
                    "Never put an action description in a speech balloon. A silent panel is valid.",
                    "Aim for 8 spoken words or fewer; never draft more than 12 words in one dialogue balloon.",
                    "Treat saved_text on a panel as immutable and do not duplicate or rewrite it.",
                    "This continuation cannot create, replace, regenerate, or transform artwork or page geometry.",
                ],
            }
        resume_saved_page_story = (
            not lettering_request
            and (_is_pending_page_story_continuation(session, user_text, project_id) or pending_page_start)
        )
        if lettering_request:
            lettering_tool = next((tool for tool in self.registry.list_image_chat_tools() if tool.tool_id == "planning.plan_lettering"), None)
            available_tools = [lettering_tool] if lettering_tool and lettering_job_ready else []
        elif resume_saved_page_story:
            available_tools = []
        # Select just-in-time workflow guidance from the actual recent chat context
        # and callable registry. A short confirmation inherits the prior offer/story.
        skill_context = "\n".join(message.text for message in session.messages[-8:]) + "\n" + user_text
        # Skill guidance must match what this specific model turn can actually
        # call, not merely tools that exist somewhere in the wider registry.
        available_tool_ids = {tool.tool_id for tool in available_tools}
        workflow_skills = load_relevant_workflow_skills(skill_context, available_tool_ids)
        if workflow_skills:
            project_ctx["workflow_skill"] = workflow_skills
        allowed_tool_ids = {tool.tool_id for tool in available_tools}
        active_tool_calls: List[ToolCall] = []
        active_tool_results: List[ToolResult] = []
        executed_hashes = set()
        activity_label = (
            "Planning lettering for the saved panels..." if lettering_request and lettering_job_ready
            else "Resuming the saved story plan and Canvas work..." if resume_saved_page_story
            else "Analyzing request and project state..."
        )
        final_text: Optional[str] = (
            "I could not find a saved Canvas story with complete placed artwork in this chat to continue with lettering. I did not create or change any artwork."
            if lettering_request and not lettering_job_ready else None
        )
        production_job = None

        # Build message history for model client
        history: List[Dict[str, Any]] = []
        for m in session.messages[-6:]:  # compact recent context; do not resend old attachments
            text_content = m.text
            if m.message_id != user_msg.message_id and m.role == "user" and len(text_content) > 300:
                t, h = _extract_story_title_and_hash(text_content)
                p_count = pending_action.get("panel_count", 6) if isinstance(pending_action, dict) else 6
                p_status = pending_action.get("status", "recorded") if isinstance(pending_action, dict) else "recorded"
                text_content = (
                    f"[Source Story Brief: '{t}' "
                    f"(SHA-256: {h[:12]}..., {len(m.text)} chars) — "
                    f"plan: {p_count} panels, status: {p_status}]"
                )
            history.append({
                "role": m.role,
                "content": text_content,
                "attachments": [a.model_dump() for a in m.attachments] if m.message_id == user_msg.message_id else [],
            })

        usage_rows = []
        model_calls = 0
        skip_model_loop = resume_saved_page_story or (lettering_request and not lettering_job_ready)
        for round_idx in ([] if skip_model_loop else range(1, MAX_TOOL_ROUNDS + 1)):
            tool_calls, direct_text, step_label = self.model_client.plan_next_action(
                messages=history,
                available_tools=available_tools,
                project_context=project_ctx,
                iteration=round_idx,
            )
            model_calls += 1
            provider_usage = getattr(self.model_client, "last_usage", None)
            usage_rows.append(provider_usage if isinstance(provider_usage, dict) else None)

            if step_label:
                activity_label = step_label

            if direct_text:
                lower_reply = direct_text.casefold()
                final_model_failed = any(marker in lower_reply for marker in (
                    "model provider returned http",
                    "model provider timed out",
                    "model provider could not be reached",
                    "model provider is unavailable",
                    "model api key is not configured",
                ))
                prior_success = any(result.status == "success" for result in active_tool_results)
                if final_model_failed and prior_success:
                    # A failed follow-up language-model request must not erase or
                    # contradict work already completed by registered tools.
                    final_text = self.model_client._synthesize_grounded_response(
                        user_text, active_tool_results, project_ctx
                    )
                    final_text += (
                        "\n\nThe final response-model request failed after these tools ran. "
                        "The tool results above show which work completed."
                    )
                else:
                    final_text = direct_text
                break

            if not tool_calls:
                break

            tool_calls = collapse_incomplete_planner_retries(tool_calls)

            # Execute tool calls for this round
            round_results: List[ToolResult] = []
            round_tool_calls: List[ToolCall] = []
            for tc in tool_calls:
                if tc.tool_id not in allowed_tool_ids:
                    blocked = ToolResult(
                        call_id=tc.call_id,
                        tool_id=tc.tool_id,
                        status="blocked",
                        error="This action is outside the image-generator chat's available tools. No change was made.",
                        error_code="ERR_TOOL_OUT_OF_SCOPE",
                    )
                    active_tool_calls.append(tc)
                    round_tool_calls.append(tc)
                    active_tool_results.append(blocked)
                    round_results.append(blocked)
                    if activity_callback:
                        activity_callback({
                            "call_id": tc.call_id,
                            "tool_id": tc.tool_id,
                            "status": "blocked",
                            "error": blocked.error,
                        })
                    continue

                if tc.tool_id == "generation.generate_image":
                    if canvas_target:
                        tc.arguments["width"] = canvas_target["width"]
                        tc.arguments["height"] = canvas_target["height"]
                    if project_ctx.get("selected_style_profile"):
                        chosen_style = project_ctx["selected_style_profile"]
                        tc.arguments["style_profile_id"] = chosen_style["profile_id"]
                        tc.arguments["style_profile_version"] = chosen_style["version"]
                    if project_ctx.get("selected_location"):
                        chosen_location = project_ctx["selected_location"]
                        tc.arguments["location_id"] = chosen_location["location_id"]
                        tc.arguments["location_version"] = chosen_location["version"]
                    if selected_character_ids:
                        # The global selection is only an allow-list. A typed panel
                        # plan's scoped cast remains authoritative for that image.
                        panel_plan_context = tc.arguments.get("panel_plan") or {}
                        planned_cast = panel_plan_context.get("character_ids")
                        if isinstance(panel_plan_context, dict) and "character_ids" in panel_plan_context:
                            planned_cast = list(planned_cast or [])
                            if not set(planned_cast).issubset(set(selected_character_ids)):
                                blocked = ToolResult(
                                    call_id=tc.call_id,
                                    tool_id=tc.tool_id,
                                    status="blocked",
                                    error="The panel plan includes a character outside the creator-selected cast. No image was generated.",
                                    error_code="ERR_PANEL_CAST_OUTSIDE_SELECTION",
                                )
                                active_tool_calls.append(tc)
                                round_tool_calls.append(tc)
                                round_results.append(blocked)
                                active_tool_results.append(blocked)
                                continue
                            tc.arguments["character_ids"] = list(planned_cast)
                        else:
                            tc.arguments["character_ids"] = list(selected_character_ids)

                # Loop detection: check if exact call has already been executed in this turn
                args_hash = hashlib.sha256(json.dumps(tc.arguments, sort_keys=True).encode()).hexdigest()
                call_key = f"{tc.tool_id}:{args_hash}"
                if call_key in executed_hashes:
                    # Duplicate loop detected, break to prevent infinite invocation
                    active_tool_calls.append(tc)
                    round_tool_calls.append(tc)
                    round_results.append(ToolResult(
                        call_id=tc.call_id,
                        tool_id=tc.tool_id,
                        status="blocked",
                        error="Duplicate tool call detected in the same execution turn.",
                        error_code="ERR_LOOP_DETECTED",
                    ))
                    if activity_callback:
                        activity_callback({"call_id": tc.call_id, "tool_id": tc.tool_id, "status": "blocked", "error": "Duplicate tool call detected."})
                    continue

                executed_hashes.add(call_key)
                active_tool_calls.append(tc)
                round_tool_calls.append(tc)
                if activity_callback:
                    activity_callback({"call_id": tc.call_id, "tool_id": tc.tool_id, "status": "running"})

                # Check spend headroom against the tighter governing ceiling
                tool_def = self.registry.get_tool(tc.tool_id)
                if tool_def and tool_def.estimated_cost_usd and tool_def.estimated_cost_usd > 0:
                    if effective_cap < tool_def.estimated_cost_usd:
                        cap_desc = f"requested run ceiling ${req_cap:.4f}" if req_cap is not None else f"available budget ${avail_budget:.4f}"
                        round_results.append(ToolResult(
                            call_id=tc.call_id,
                            tool_id=tc.tool_id,
                            status="blocked",
                            error=f"Execution budget exceeded. Required ${tool_def.estimated_cost_usd:.4f}, but {cap_desc} is insufficient.",
                            error_code="ERR_BUDGET_EXCEEDED",
                        ))
                        if activity_callback:
                            activity_callback({"call_id": tc.call_id, "tool_id": tc.tool_id, "status": "blocked", "error": "Execution budget is insufficient."})
                        continue

                # Repair an incomplete planner call from explicit user source
                # text and count. The repair is extractive and is recorded in
                # tool output; it never invents story facts or speaker IDs.
                tool_context = {**project_ctx, "_agent_chat": True}
                if tc.tool_id == "planning.plan_panels":
                    tool_context["_user_text"] = user_text
                    tool_context["_authored_user_texts"] = [
                        str(_message_value(message, "text", ""))
                        for message in session.messages
                        if _message_value(message, "role") == "user"
                    ] + [user_text]
                if tc.tool_id == "planning.plan_lettering":
                    tool_context["_saved_lettering_context"] = project_ctx.get("saved_lettering_context")
                if tc.tool_id == "planning.plan_panels" and isinstance(tc.arguments, dict) and "pages" in tc.arguments:
                    # The typed page blueprint bypasses flat panel-outline
                    # extraction and is checked against the requested page count.
                    tool_context["_expected_page_count"] = (
                        pending_action.get("page_count") if pending_action else None
                    ) or _requested_page_count(user_text)
                    tool_context["_allow_uniform_page_panels"] = bool(re.search(
                        r"\b(?:uniform|same\s+(?:panel\s+)?count|equal\s+(?:panel\s+)?count|identical\s+grid)\b",
                        user_text,
                        re.IGNORECASE,
                    ))
                    res = self.registry.dispatch(tc, tool_context)
                elif tc.tool_id == "planning.plan_panels":
                    recent_user_texts = [
                        (_message_value(message, "message_id", ""), str(_message_value(message, "text", "")))
                        for message in session.messages
                        if _message_value(message, "role") == "user"
                    ]
                    character_names = {
                        character_id: str(getattr(character, "name", "") or "")
                        for character_id, character in bible.characters.items()
                    }
                    repaired_args, repair_warning, repair_error = recover_panel_plan_arguments(
                        tc.arguments,
                        current_request=user_text,
                        recent_user_texts=recent_user_texts,
                        character_names=character_names,
                        selected_character_ids=selected_character_ids,
                        expected_panel_count=(
                            pending_action.get("panel_count")
                            if isinstance(pending_action, dict)
                            and pending_action.get("status") in ("offer_made", "plan_ready")
                            else None
                        ),
                        expected_panel_count_is_default=_pending_panel_count_is_default(pending_action),
                    )
                    if repair_error:
                        res = ToolResult(
                            call_id=tc.call_id,
                            tool_id=tc.tool_id,
                            status="failed",
                            error=repair_error,
                            error_code="ERR_PANEL_PLAN_SOURCE_REQUIRED",
                        )
                    else:
                        # These are inputs to the compact Agent-facing planner
                        # contract only; the registered planner accepts the
                        # fully expanded scene/beats schema instead.
                        if panel_plan_retry_is_duplicate(
                            repaired_args,
                            active_tool_results,
                            active_tool_calls,
                        ):
                            tc.arguments = repaired_args
                            duplicate_plan = ToolResult(
                                call_id=tc.call_id,
                                tool_id=tc.tool_id,
                                status="blocked",
                                error=(
                                    "This panel plan repeats the current plan, or the one allowed correction was already used. "
                                    "No planning call was run."
                                ),
                                error_code="ERR_DUPLICATE_PANEL_PLAN",
                            )
                            active_tool_calls.append(tc)
                            round_tool_calls.append(tc)
                            active_tool_results.append(duplicate_plan)
                            round_results.append(duplicate_plan)
                            continue
                        repaired_args.pop("panel_count", None)
                        repaired_args.pop("panel_outline", None)
                        tc.arguments = repaired_args
                        if repair_warning:
                            tool_context["_panel_plan_input_warnings"] = [repair_warning]
                        res = self.registry.dispatch(tc, tool_context)
                else:
                    res = self.registry.dispatch(tc, tool_context)
                active_tool_results.append(res)
                round_results.append(res)
                if (
                    tc.tool_id == "planning.plan_panels"
                    and res.status == "success"
                    and isinstance(res.output, dict)
                    and res.output.get("plans")
                    and pending_action
                ):
                    pending_action["plan"] = res.output
                    pending_action["plan_call_id"] = res.call_id
                    pending_action["panel_count"] = len(res.output["plans"])
                    pending_action["total_panel_count"] = int(res.output.get("total_panel_count") or len(res.output["plans"]))
                    if res.output.get("story_blueprint"):
                        pending_action["page_count"] = int(res.output.get("page_count") or pending_action.get("page_count") or 0)
                        pending_action["page_panel_counts"] = dict(res.output.get("page_panel_counts") or {})
                        pending_action["assumptions"] = list(res.output.get("assumptions") or [])
                        per_panel_cost = float(getattr(self.registry.get_tool("generation.generate_image"), "estimated_cost_usd", 0.0) or 0.0)
                        pending_action["estimated_cost_usd"] = round(per_panel_cost * len(res.output["plans"]), 4) if per_panel_cost > 0 else None
                    pending_action["panel_count_source"] = "saved_plan"
                    pending_action["status"] = "plan_ready"
                    pending_action["plan_invalidated"] = False
                    pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
                    session.metadata["pending_story_action"] = pending_action
                    self.session_store.save_session(session)
                if activity_callback:
                    activity_callback({
                        "call_id": tc.call_id,
                        "tool_id": tc.tool_id,
                        "status": res.status,
                        "duration_seconds": res.duration_seconds,
                        "error": res.error,
                        "approval_id": res.approval_id,
                    })

                # A creator-selected Canvas target means generated art should be
                # inserted into that same persisted page document via the normal
                # registered Canvas tool. Revision checks keep this fail-closed.
                generation_output = res.output if isinstance(res.output, dict) else {}
                if (
                    tc.tool_id == "generation.generate_image"
                    and res.status == "success"
                    and canvas_target
                    and generation_output.get("asset_id")
                ):
                    place_call = ToolCall(
                        call_id=f"{tc.call_id}_canvas_place",
                        tool_id="canvas.place_panel_artwork",
                        arguments={
                            "page_id": canvas_target["page_id"],
                            "expected_revision": canvas_target["expected_revision"],
                            "panel_id": canvas_target["panel_id"],
                            "asset_id": generation_output["asset_id"],
                            "fit_mode": "cover",
                            "replace_existing": canvas_target["replace_existing"],
                        },
                    )
                    active_tool_calls.append(place_call)
                    round_tool_calls.append(place_call)
                    if activity_callback:
                        activity_callback({"call_id": place_call.call_id, "tool_id": place_call.tool_id, "status": "running"})
                    place_result = self.registry.dispatch(place_call, {**project_ctx, "_agent_chat": True})
                    active_tool_results.append(place_result)
                    round_results.append(place_result)
                    if place_result.status == "success" and isinstance(place_result.output, dict):
                        canvas_target["expected_revision"] = place_result.output.get(
                            "revision", canvas_target["expected_revision"]
                        )
                    if activity_callback:
                        activity_callback({
                            "call_id": place_call.call_id,
                            "tool_id": place_call.tool_id,
                            "status": place_result.status,
                            "duration_seconds": place_result.duration_seconds,
                            "error": place_result.error,
                        })

                # If an action required approval, stop the loop to wait for human operator
                if res.status == "gated":
                    break

            # Update history with assistant tool call invocation and tool results for next model iteration
            history.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "call_id": tc.call_id,
                        "tool_id": tc.tool_id,
                        "arguments": tc.arguments,
                    }
                    for tc in round_tool_calls
                ],
            })
            history.append({
                "role": "tool",
                "content": "Tool outputs",
                "tool_results": round_results,
            })

            # If any tool was gated, halt loop
            if any(r.status == "gated" for r in round_results):
                final_text = (
                    f"### Action Gated: Human Approval Required\n\n"
                    f"The operation `{round_results[0].tool_id}` was intercepted by the Approval Gate.\n\n"
                    f"- **Approval ID:** `{round_results[0].approval_id}`\n"
                    f"- **Reason:** {round_results[0].error}\n\n"
                    f"> Please review and sign this action in the Approval Queue to proceed."
                )
                break

            if round_idx >= MAX_TOOL_ROUNDS or not _needs_model_follow_up(user_text, round_results, self.registry):
                break

        # Lettering is a separate continuation of an already verified job. The
        # original page plan and artwork IDs are reused; the workflow below has
        # a hard text-only execution path.
        if lettering_request and lettering_job_ready:
            lettering_result = next((
                result for result in reversed(active_tool_results)
                if result.tool_id == "planning.plan_lettering"
            ), None)
            if not lettering_result or lettering_result.status != "success":
                final_text = (
                    "I couldn't validate a lettering plan for the saved panels, so no page changes were made. "
                    "The tool result above shows the planning error; the existing artwork remains untouched."
                )
            else:
                plan_call_id = str(saved_lettering_job.get("source_plan_call_id") or "saved_plan")
                source_message_id = str(saved_lettering_job.get("source_request_message_id") or "")
                saved_plan_result = ToolResult(
                    call_id=plan_call_id,
                    tool_id="planning.plan_panels",
                    status="success",
                    output=saved_lettering_job.get("plan") or {},
                )
                lettering_workflow = None
                try:
                    lettering_workflow = _resolve_story_to_canvas_workflow()(
                        registry=self.registry,
                        session_store=self.session_store,
                        session=session,
                        project_id=project_id,
                        plan_result=saved_plan_result,
                        plan_call_id=plan_call_id,
                        source_request_message_id=source_message_id,
                        request_texts=[user_text],
                        selected_character_ids=list(saved_lettering_job.get("selected_character_ids") or []),
                        selected_style_profile=None,
                        selected_location=None,
                        canonical_characters=bible.characters,
                        execution_manager=em,
                        effective_budget_usd=effective_cap,
                        offline_mode=offline_mode,
                        activity_callback=activity_callback,
                        lettering_only=True,
                        lettering_plan=lettering_result.output,
                    )
                    production_job, final_text = lettering_workflow.run([], [])
                    active_tool_calls.extend(lettering_workflow.calls)
                    active_tool_results.extend(lettering_workflow.results)
                except Exception as exc:
                    logger.exception("Agent lettering continuation failed before it could report a result")
                    if lettering_workflow is not None:
                        active_tool_calls.extend(lettering_workflow.calls)
                        active_tool_results.extend(lettering_workflow.results)
                    final_text = (
                        f"Lettering continuation stopped with {type(exc).__name__}: {exc}. "
                        "No artwork generation or replacement was requested; inspect the tool results before retrying."
                    )

        # Resume an approved plan through real generation and persisted Canvas tools.
        # Explicit create requests with an exact page count start in the same turn
        # after planning succeeds. Plan-only requests remain reviewable.
        is_multi_page_request = bool(requested_page_count and requested_page_count > 1)
        production_requested = not lettering_request and (
            (_requested_single_page_panel_count(user_text) is not None and not is_multi_page_request and not _is_plan_only_story_request(user_text))
            or production_action_requested(user_text)
            or resume_saved_page_story
            or _is_explicit_story_creation_request(user_text)
        )
        plan_result = None
        plan_call_id = None
        plan_message_index = None
        source_request_index = None
        if production_requested:
            # A plan completed in this turn is the creator's freshest intent.
            # Prefer it over an older pending action or saved session plan.
            current_turn_plan_result = _latest_current_turn_panel_plan(active_tool_results)
            if current_turn_plan_result is not None:
                plan_result = current_turn_plan_result
                plan_call_id = current_turn_plan_result.call_id
                plan_message_index = len(session.messages)
                if pending_action:
                    pending_action["plan"] = current_turn_plan_result.output
                    pending_action["plan_call_id"] = current_turn_plan_result.call_id
                    pending_action["panel_count"] = len(current_turn_plan_result.output.get("plans") or [])
                    pending_action["panel_count_source"] = "saved_plan"
                    pending_action["status"] = "plan_ready"
                    pending_action["plan_invalidated"] = False
                    pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
                    session.metadata["pending_story_action"] = pending_action
                    self.session_store.save_session(session)
            else:
                # A failed plan in this turn must not fall through to a stale
                # pending/saved plan and produce a different story by accident.
                current_turn_plan_failure = _latest_current_turn_panel_plan_failure(active_tool_results)
                if current_turn_plan_failure is not None:
                    plan_result = current_turn_plan_failure
                    plan_call_id = current_turn_plan_failure.call_id
                    plan_message_index = len(session.messages)

            # Check pending story action plan first
            if plan_result is None and pending_action:
                if not pending_action.get("plan"):
                    source_text = ""
                    for m in session.messages:
                        if m.message_id == pending_action.get("source_message_id"):
                            source_text = m.text
                            break
                    if not source_text:
                        for m in reversed(session.messages):
                            if m.role == "user" and len((m.text or "").strip()) >= 80:
                                source_text = m.text
                                break
                    if source_text:
                        matched_plan, plan_cid = _find_matching_saved_plan_for_story(project_id, source_text)
                        if matched_plan:
                            pending_action["plan"] = matched_plan
                            pending_action["plan_call_id"] = plan_cid
                            pending_action["panel_count"] = len(matched_plan.get("plans", []))
                            pending_action["panel_count_source"] = "saved_plan"
                    if not pending_action.get("plan"):
                        repaired_args, _, _ = recover_panel_plan_arguments(
                            {},
                            current_request=user_text,
                            recent_user_texts=[(m.message_id, m.text) for m in session.messages if m.role == "user"],
                            character_names={cid: str(getattr(c, "name", "") or "") for cid, c in bible.characters.items()},
                            selected_character_ids=selected_character_ids,
                            expected_panel_count=pending_action.get("panel_count"),
                            expected_panel_count_is_default=_pending_panel_count_is_default(pending_action),
                        )
                        if repaired_args.get("beats"):
                            tool_context = {**project_ctx, "_agent_chat": True}
                            tool_context["_user_text"] = user_text
                            tool_context["_authored_user_texts"] = [
                                str(_message_value(message, "text", ""))
                                for message in session.messages
                                if _message_value(message, "role") == "user"
                            ] + [user_text]
                            repaired_args.pop("panel_count", None)
                            repaired_args.pop("panel_outline", None)
                            plan_call = ToolCall(call_id=f"plan_auto_{int(time.time()*1000)}", tool_id="planning.plan_panels", arguments=repaired_args)
                            plan_res = self.registry.dispatch(plan_call, tool_context)
                            if plan_res.status == "success" and (plan_res.output or {}).get("plans"):
                                pending_action["plan"] = plan_res.output
                                pending_action["plan_call_id"] = plan_call.call_id
                                pending_action["panel_count"] = len(plan_res.output["plans"])
                                pending_action["panel_count_source"] = "saved_plan"
                                active_tool_calls.append(plan_call)
                                active_tool_results.append(plan_res)

                if pending_action.get("plan"):
                    plan_result = ToolResult(
                        call_id=str(pending_action.get("plan_call_id") or "saved_plan"),
                        tool_id="planning.plan_panels",
                        status="success",
                        output=pending_action["plan"],
                    )
                    plan_call_id = str(pending_action.get("plan_call_id") or "saved_plan")
                    plan_message_index = len(session.messages)

            if plan_result is None:
                for idx in range(len(session.messages) - 1, -1, -1):
                    candidate = session.messages[idx]
                    if _message_value(candidate, "role") != "assistant":
                        continue
                    found = next((
                        result for result in reversed(_message_value(candidate, "tool_results", []) or [])
                        if _message_value(result, "tool_id") == "planning.plan_panels"
                        and _message_value(result, "status") == "success"
                        and (_message_value(result, "output", {}) or {}).get("plans")
                    ), None)
                    if found is not None:
                        plan_result = found
                        plan_call_id = _message_value(found, "call_id")
                        plan_message_index = idx
                        break
            if plan_result is None:
                active_plan_result = next((
                    result for result in reversed(active_tool_results)
                    if result.tool_id == "planning.plan_panels" and result.status == "success"
                    and (result.output or {}).get("plans")
                ), None)
                if active_plan_result is not None:
                    plan_result = active_plan_result
                    plan_call_id = active_plan_result.call_id
                    plan_message_index = len(session.messages)

            # A process may stop after persisting a job checkpoint but before
            # appending the assistant's planning/tool message. Resume directly
            # from that durable plan instead of asking the model to plan again.
            if plan_result is None:
                saved_job = _latest_saved_story_job(session, project_id)
                if saved_job is not None:
                    plan_call_id = str(saved_job.get("source_plan_call_id") or "saved_plan")
                    plan_result = ToolResult(
                        call_id=plan_call_id,
                        tool_id="planning.plan_panels",
                        status="success",
                        output=saved_job.get("plan"),
                    )
                    plan_message_index = next((
                        idx for idx, message in enumerate(session.messages)
                        if _message_value(message, "message_id") == saved_job.get("source_request_message_id")
                    ), len(session.messages) - 1)

            # If no plan exists yet, synthesize one from the user's story text in this or recent turns
            if plan_result is None:
                recent_user_texts = [
                    (_message_value(message, "message_id", ""), str(_message_value(message, "text", "")))
                    for message in session.messages
                    if _message_value(message, "role") == "user"
                ]
                character_names = {
                    character_id: str(getattr(character, "name", "") or "")
                    for character_id, character in bible.characters.items()
                }
                repaired_args, repair_warning, repair_error = recover_panel_plan_arguments(
                    {},
                    current_request=user_text,
                    recent_user_texts=recent_user_texts,
                    character_names=character_names,
                    selected_character_ids=selected_character_ids,
                    expected_panel_count=(
                        pending_action.get("panel_count")
                        if isinstance(pending_action, dict)
                        and pending_action.get("status") in ("offer_made", "plan_ready")
                        else None
                    ),
                    expected_panel_count_is_default=_pending_panel_count_is_default(pending_action),
                )
                if not repair_error and repaired_args.get("beats"):
                    tool_context = {**project_ctx, "_agent_chat": True}
                    tool_context["_user_text"] = user_text
                    tool_context["_authored_user_texts"] = [
                        str(_message_value(message, "text", ""))
                        for message in session.messages
                        if _message_value(message, "role") == "user"
                    ] + [user_text]
                    repaired_args.pop("panel_count", None)
                    repaired_args.pop("panel_outline", None)
                    plan_call = ToolCall(
                        call_id=f"plan_auto_{int(time.time()*1000)}",
                        tool_id="planning.plan_panels",
                        arguments=repaired_args,
                    )
                    active_tool_calls.append(plan_call)
                    if activity_callback:
                        activity_callback({"call_id": plan_call.call_id, "tool_id": plan_call.tool_id, "status": "running"})
                    plan_res = self.registry.dispatch(plan_call, tool_context)
                    active_tool_results.append(plan_res)
                    if activity_callback:
                        activity_callback({
                            "call_id": plan_call.call_id,
                            "tool_id": plan_call.tool_id,
                            "status": plan_res.status,
                            "duration_seconds": plan_res.duration_seconds,
                            "error": plan_res.error,
                        })
                    if plan_res.status == "success" and (plan_res.output or {}).get("plans"):
                        plan_result = plan_res
                        plan_call_id = plan_call.call_id
                        plan_message_index = len(session.messages)

        if production_requested and plan_result is not None and plan_result.status == "success" and canvas_target is None:
            if plan_message_index == len(session.messages):
                source_request_index = max(
                    (idx for idx, message in enumerate(session.messages) if _message_value(message, "role") == "user"),
                    default=0,
                )
            else:
                source_request_index = max(
                    (idx for idx, message in enumerate(session.messages[:plan_message_index + 1]) if _message_value(message, "role") == "user"),
                    default=0,
                )
            if pending_action and pending_action.get("source_message_id"):
                original_source_index = next((
                    idx for idx, message in enumerate(session.messages)
                    if _message_value(message, "message_id") == pending_action.get("source_message_id")
                ), None)
                if original_source_index is not None:
                    source_request_index = original_source_index
            source_message = session.messages[source_request_index] if session.messages else {}
            request_texts = [
                str(_message_value(message, "text", ""))
                for message in session.messages[source_request_index:]
                if _message_value(message, "role") == "user"
            ]
            plan_idx_for_history = plan_message_index if plan_message_index < len(session.messages) else len(session.messages)
            prior_results = [
                result
                for message in session.messages[plan_idx_for_history + 1:]
                if _message_value(message, "role") == "assistant"
                for result in (_message_value(message, "tool_results", []) or [])
            ]
            prior_calls = [
                call
                for message in session.messages[plan_idx_for_history + 1:]
                if _message_value(message, "role") == "assistant"
                for call in (_message_value(message, "tool_calls", []) or [])
            ]
            # The current request is already saved in the session; these lists
            # add only current-turn tools, if planning and execution were one turn.
            prior_results.extend(result for result in active_tool_results if result.call_id != plan_call_id)
            prior_calls.extend(call for call in active_tool_calls if call.call_id != plan_call_id)
            request_texts.append(user_text) if not request_texts or request_texts[-1] != user_text else None
            style_snapshot = project_ctx.get("selected_style_profile")
            location_snapshot = project_ctx.get("selected_location")
            workflow = None
            try:
                if pending_action and pending_action.get("page_count"):
                    pending_action["status"] = "running"
                    pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
                    session.metadata["pending_story_action"] = pending_action
                    self.session_store.save_session(session)
                workflow = _resolve_story_to_canvas_workflow()(
                    registry=self.registry,
                    session_store=self.session_store,
                    session=session,
                    project_id=project_id,
                    plan_result=plan_result,
                    plan_call_id=plan_call_id or "saved_plan",
                    source_request_message_id=_message_value(source_message, "message_id", ""),
                    request_texts=request_texts,
                    selected_character_ids=selected_character_ids,
                    selected_style_profile=style_snapshot,
                    selected_location=location_snapshot,
                    canonical_characters=bible.characters,
                    execution_manager=em,
                    effective_budget_usd=effective_cap,
                    offline_mode=offline_mode,
                    activity_callback=activity_callback,
                )
                production_job, workflow_text = workflow.run(prior_results, prior_calls)
                active_tool_calls.extend(workflow.calls)
                active_tool_results.extend(workflow.results)
                final_text = workflow_text
                if pending_action:
                    # The adaptation action mirrors the durable production
                    # result. A completed planning turn is not the same as a
                    # successfully generated, assembled, and verified page.
                    pending_action["status"] = (
                        "completed" if production_job.status == "completed" else "needs_attention"
                    )
                    pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
                    session.metadata["pending_story_action"] = pending_action
                    self.session_store.save_session(session)
            except Exception as exc:
                logger.exception("Story-to-Canvas workflow failed before it could report a result")
                if pending_action and pending_action.get("page_count"):
                    pending_action["status"] = "needs_attention"
                    pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
                    session.metadata["pending_story_action"] = pending_action
                    self.session_store.save_session(session)
                if workflow is not None:
                    active_tool_calls.extend(workflow.calls)
                    active_tool_results.extend(workflow.results)
                saved_jobs = session.metadata.get("story_production_jobs", {})
                saved_job = next((
                    item for item in saved_jobs.values()
                    if item.get("source_plan_call_id") == (plan_call_id or "saved_plan")
                ), None)
                if saved_job:
                    try:
                        production_job = StoryProductionJob.model_validate(saved_job)
                    except Exception:
                        production_job = None
                final_text = (
                    f"Story production stopped with an internal workflow error: {type(exc).__name__}: {exc}. "
                    "Any written checkpoints and completed tool results are shown above; resume this saved plan to continue."
                )

        current_page_plan_succeeded = any(
            result.tool_id == "planning.plan_panels"
            and result.status == "success"
            and isinstance(result.output, dict)
            and bool(result.output.get("story_blueprint"))
            for result in active_tool_results
        )
        if is_page_plan_edit and not current_page_plan_succeeded and not production_requested:
            pending_action["status"] = "needs_attention"
            pending_action["plan_invalidated"] = True
            pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
            session.metadata["pending_story_action"] = pending_action
            self.session_store.save_session(session)
            final_text = (
                "I could not confirm a revised story plan, so the earlier plan is no longer marked ready. "
                "No artwork was generated. The planning error above shows what needs correction."
            )

        if (
            pending_action
            and pending_action.get("page_count")
            and pending_action.get("status") in ("planning", "offer_made")
            and not (pending_action.get("plan") or {}).get("story_blueprint")
            and not lettering_request
            and not production_requested
        ):
            pending_action["status"] = "needs_attention"
            pending_action["updated_at"] = datetime.now(timezone.utc).isoformat()
            session.metadata["pending_story_action"] = pending_action
            self.session_store.save_session(session)

        if pending_action and pending_action.get("page_count") and pending_action.get("status") == "plan_ready" and not lettering_request and not production_requested:
            output = pending_action.get("plan") or {}
            blueprint = output.get("story_blueprint") or {}
            total_panels = int(pending_action.get("total_panel_count") or len(output.get("plans") or []))
            page_count = int(pending_action.get("page_count") or len(page_rows))
            costs = (
                f" Estimated generation cost: about ${pending_action['estimated_cost_usd']:.2f}; actual provider cost can vary."
                if pending_action.get("estimated_cost_usd") is not None
                else " Generation cost could not be estimated from the configured provider."
            )
            final_text = (
                f"### Story plan ready: {blueprint.get('title') or pending_action.get('source_title') or 'New story'}\n\n"
                f"I prepared exactly **{page_count} pages** with **{total_panels} panels**. "
                "Panel density varies by page to follow the story. Review the page outline below, then choose **Start** or **Skip**."
                + costs
            )

        if not final_text:
            final_text = self.model_client._synthesize_grounded_response(
                user_text, active_tool_results, project_ctx
            )

        # 4. Check if a plan or approval was generated
        active_plan = None
        pending_approval = None
        for tr in active_tool_results:
            if tr.tool_id == "plan.draft_plan" and tr.status == "success" and tr.output:
                try:
                    active_plan = AgentPlan(**tr.output)
                except Exception:
                    pass
            if tr.status == "gated" and tr.approval_id:
                pending_approval = self.approval_manager.get_request(tr.approval_id)
            elif tr.tool_id == "canon.propose_character_mutation" and tr.status == "success" and isinstance(tr.output, dict):
                prop_id = tr.output.get("proposal_id")
                change_desc = tr.output.get("change_description", "Character mutation proposal")
                pending_approval = self.approval_manager.create_request(
                    project_id=project_id,
                    operation="canon.apply_approved_mutation",
                    scope="canon:mutation",
                    consequence=f"Mutates Story Bible by applying proposal {prop_id}: {change_desc}",
                    affected_resources=[project_id],
                    canon_hash=canon_hash,
                    arguments={"project_id": project_id, "proposal_id": prop_id},
                    reversibility="REVERSIBLE",
                )

        # Collect any generated assets/artifacts to attach to assistant turn
        assistant_attachments: List[AgentAttachment] = []
        for tr in active_tool_results:
            for art in (getattr(tr, "artifacts", []) or []):
                if isinstance(art, dict) and art.get("asset_id"):
                    aid = art["asset_id"]
                    if not any(a.attachment_id == aid for a in assistant_attachments):
                        assistant_attachments.append(AgentAttachment(
                            attachment_id=aid,
                            filename=art.get("filename", "generated.png"),
                            mime_type=art.get("mime_type", "image/png"),
                            byte_size=art.get("byte_size", 0),
                            content_sha256=art.get("sha256", "") or art.get("content_sha256", ""),
                            width=art.get("width"),
                            height=art.get("height"),
                            asset_id=aid,
                        ))
            if isinstance(getattr(tr, "output", None), dict):
                out = tr.output
                if out.get("asset_id"):
                    aid = out["asset_id"]
                    if not any(a.attachment_id == aid for a in assistant_attachments):
                        assistant_attachments.append(AgentAttachment(
                            attachment_id=aid,
                            filename=out.get("filename") or out.get("logical_filename") or f"{out.get('panel_id', 'panel')}.png",
                            mime_type=out.get("mime_type", "image/png"),
                            byte_size=out.get("byte_size", 0),
                            content_sha256=out.get("content_sha256", ""),
                            width=out.get("width"),
                            height=out.get("height"),
                            asset_id=aid,
                        ))
                for sub_art in (out.get("_artifacts", []) or out.get("artifacts", []) or []):
                    if isinstance(sub_art, dict) and sub_art.get("asset_id"):
                        aid = sub_art["asset_id"]
                        if not any(a.attachment_id == aid for a in assistant_attachments):
                            assistant_attachments.append(AgentAttachment(
                                attachment_id=aid,
                                filename=sub_art.get("filename") or sub_art.get("logical_filename") or f"{aid}.png",
                                mime_type=sub_art.get("mime_type", "image/png"),
                                byte_size=sub_art.get("byte_size", 0),
                                content_sha256=sub_art.get("content_sha256", "") or sub_art.get("sha256", ""),
                                width=sub_art.get("width"),
                                height=sub_art.get("height"),
                                asset_id=aid,
                            ))

        # Guarantee: any generated image must be previewed directly in the chat text
        for att in assistant_attachments:
            if att.mime_type.startswith("image/") or att.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                img_url = f"/api/v1/assets/{att.asset_id or att.attachment_id}/file"
                if img_url not in (final_text or ""):
                    label = att.filename.rsplit(".", 1)[0]
                    final_text = (final_text or "").rstrip() + f"\n\n![{label}]({img_url})\n"

        reported_rows = [row for row in usage_rows if row is not None]
        usage_status = "unavailable" if not reported_rows else ("reported" if len(reported_rows) == model_calls else "partial")
        def usage_total(key: str) -> Optional[int]:
            values = [row[key] for row in reported_rows if key in row]
            return sum(values) if values else None
        model_usage = ModelUsage(
            status=usage_status,
            model_calls=model_calls,
            input_tokens=usage_total("input_tokens"),
            output_tokens=usage_total("output_tokens"),
            total_tokens=usage_total("total_tokens"),
        )

        # 5. Construct Assistant Response Turn
        assistant_msg = AgentMessage(
            message_id=f"msg_ast_{int(time.time()*1000)}",
            role="assistant",
            text=final_text,
            attachments=assistant_attachments,
            tool_calls=active_tool_calls,
            tool_results=active_tool_results,
            activity_state="waiting_approval" if pending_approval else ("idle" if not active_tool_calls else "reviewing_results"),
            activity_label=activity_label if active_tool_calls else None,
            plan=active_plan,
            pending_approval=pending_approval,
            project_available_budget_usd=avail_budget,
            requested_run_budget_cap_usd=req_cap,
            model_usage=model_usage,
            production_job=production_job.model_dump(mode="json") if production_job is not None else None,
            pending_story_action=PendingStoryAction.model_validate(pending_action) if pending_action else None,
        )
        self.session_store.append_message(session_id, assistant_msg)

        # 6. Record trace event in ExecutionManager
        try:
            from app.execution.states import ExecutionEventType
            run = em.db.get_run(session_id)
            if not run:
                em.create_run(
                    run_id=session_id,
                    project_id=project_id,
                    canon_hash=canon_hash or "unhashed",
                    canon_version=str(bible_ver),
                    budget_limit_usd=avail_budget,
                )
            em._log_event(
                run_id=session_id,
                event_type=ExecutionEventType.RUN_COMPLETED,
                data={
                    "project_id": project_id,
                    "event_name": "agent_turn_completed",
                    "tool_calls_count": len(active_tool_calls),
                    "tool_results_count": len(active_tool_results),
                    "canon_hash": canon_hash,
                    "project_available_budget_usd": avail_budget,
                    "requested_run_budget_cap_usd": req_cap,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record trace event: {e}")

        return assistant_msg

    def create_plan(
        self,
        project_id: str,
        goal: str,
        spend_limit_usd: Optional[float] = None,
    ) -> AgentPlan:
        """
        Creates and deterministically validates an Agent execution plan using the registry.
        """
        arguments = {
            "project_id": project_id,
            "goal": goal,
        }
        if spend_limit_usd is not None:
            arguments["requested_run_budget_cap_usd"] = spend_limit_usd

        tool_call = ToolCall(
            call_id=f"call_{int(time.time()*1000)}",
            tool_id="plan.draft_plan",
            arguments=arguments,
        )
        res = self.registry.dispatch(tool_call, {"project_id": project_id, "requested_run_budget_cap_usd": spend_limit_usd})
        if res.status == "success" and res.output:
            return AgentPlan(**res.output)
        raise RuntimeError(f"Plan generation failed: {res.error}")
