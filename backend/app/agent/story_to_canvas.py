"""Deterministic, checkpointed production of an approved story into persisted Canvas pages."""
from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

from app.agent.production import (
    PageProduction,
    PanelProduction,
    StoryProductionJob,
    corrected_character_ids,
    group_panels,
    selected_cast_repair_requested,
    stable_job_id,
    stable_page_id,
)
from app.agent.schemas import ToolCall, ToolResult


def _value(item: Any, key: str, default=None):
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _transient_provider_error(result: Any) -> bool:
    code = str(_value(result, "error_code", "") or "").upper()
    message = str(_value(result, "error", "") or "").casefold()
    return code in {"ERR_PROVIDER_TIMEOUT", "ERR_PROVIDER_UNAVAILABLE", "ERR_IMAGE_GENERATION_FAILED"} and any(
        marker in message for marker in ("temporarily unavailable", "timed out", "timeout", "rate limit", "http 5", "server_error", "try again")
    )


def _hash_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _dialogue_direction(text: str) -> str:
    """Resolve the first strong character so SVG foreignObject text lays out correctly."""
    for char in text:
        bidi = unicodedata.bidirectional(char)
        if bidi in {"R", "AL"}:
            return "rtl"
        if bidi == "L":
            return "ltr"
    return "ltr"


def _scratch_geometry_from_plans(plans: Sequence[Dict[str, Any]], reading_direction: str) -> List[Dict[str, Any]]:
    """Translate narrative shape preferences into real editable custom panel cuts."""
    ordered = sorted(plans, key=lambda item: int(item.get("reading_order_index", 1)))
    if not ordered:
        return []
    rows: List[List[Dict[str, Any]]] = []
    index = 0
    while index < len(ordered):
        current = ordered[index]
        shape = str(current.get("shape_preference", "square") or "square").split(".")[-1].casefold()
        if shape in {"panoramic", "narrow_strip"} or index + 1 == len(ordered):
            rows.append([current])
            index += 1
            continue
        following = ordered[index + 1]
        following_shape = str(following.get("shape_preference", "square") or "square").split(".")[-1].casefold()
        if following_shape in {"panoramic", "narrow_strip"}:
            rows.append([current])
            index += 1
            continue
        rows.append([current, following])
        index += 2

    def row_weight(row: List[Dict[str, Any]]) -> float:
        values = [str(p.get("shape_preference", "square") or "square").split(".")[-1].casefold() for p in row]
        functions = [str(p.get("narrative_function", "")).split(".")[-1].casefold() for p in row]
        if "panoramic" in values:
            return 0.68
        if "narrow_strip" in values:
            return 0.40
        if "trapezoid" in values or any("action" in value or "impact" in value for value in functions):
            return 1.24
        if "vertical_rectangle" in values:
            return 1.18
        if any(value in {"establishing", "aftermath"} for value in functions):
            return 0.92
        return 1.0

    vertical_gap = 0.018
    horizontal_gap = 0.022
    total_available_height = 1.0 - vertical_gap * (len(rows) - 1)
    weights = [row_weight(row) for row in rows]
    total_weight = sum(weights)
    output: List[Dict[str, Any]] = []
    y = 0.0
    rtl = str(reading_direction).casefold() == "rtl"
    for row_index, row in enumerate(rows):
        # Use the exact remaining extent for the final row. Repeated floating
        # point additions can otherwise produce y + height = 1.0000000000000002,
        # which the strict custom-page contract correctly rejects as out of bounds.
        remaining_gaps = len(rows) - row_index - 1
        max_height = max(0.0, 1.0 - y - vertical_gap * remaining_gaps)
        weighted_height = total_available_height * weights[row_index] / total_weight
        row_height = max_height if row_index == len(rows) - 1 else min(weighted_height, max_height)
        gap = horizontal_gap if len(row) > 1 else 0.0
        if len(row) == 1:
            widths = [1.0]
        else:
            row_shapes = [str(p.get("shape_preference", "square") or "square").split(".")[-1].casefold() for p in row]
            vertical_indices = [i for i, value in enumerate(row_shapes) if value == "vertical_rectangle"]
            if len(vertical_indices) == 1:
                narrow_index = vertical_indices[0]
                ratios = [0.38, 0.62]
                if narrow_index == 1:
                    ratios = [0.62, 0.38]
            elif any(value in {"trapezoid", "parallelogram", "triangle_wedge"} for value in row_shapes):
                ratios = [0.56, 0.44]
            else:
                ratios = [0.5, 0.5]
            widths = [(1.0 - gap) * ratio for ratio in ratios]

        positions = []
        if len(row) == 1:
            positions = [(0.0, widths[0])]
        else:
            logical_x = [0.0, widths[0] + gap]
            if rtl:
                positions = [(logical_x[1], widths[1]), (logical_x[0], widths[0])]
            else:
                positions = list(zip(logical_x, widths))

        for local_index, item in enumerate(row):
            shape = str(item.get("shape_preference", "square") or "square").split(".")[-1].casefold()
            x, width = positions[local_index]
            panel_id = str(item["panel_id"])
            reading_order = int(item.get("reading_order_index", len(output) + 1))
            definition: Dict[str, Any] = {"panel_id": panel_id, "reading_order": reading_order, "z_index": reading_order}
            if shape in {"trapezoid", "parallelogram", "triangle_wedge", "general_polygon", "custom_path", "oval", "circular", "curved_organic"}:
                slant = min(width * 0.12, 0.06)
                if shape in {"oval", "circular"}:
                    import math
                    count = 12
                    cx, cy = x + width / 2.0, y + row_height / 2.0
                    definition["polygon"] = [
                        {"x": cx + width * 0.48 * math.cos(2 * math.pi * i / count), "y": cy + row_height * 0.48 * math.sin(2 * math.pi * i / count)}
                        for i in range(count)
                    ]
                elif shape == "triangle_wedge":
                    definition["polygon"] = [
                        {"x": x + slant, "y": y}, {"x": x + width, "y": y + row_height * 0.5},
                        {"x": x + slant, "y": y + row_height},
                    ]
                elif shape == "parallelogram":
                    direction = -1.0 if reading_order % 2 else 1.0
                    shift = slant * direction
                    definition["polygon"] = [
                        {"x": x + max(0, shift), "y": y}, {"x": x + width + min(0, shift), "y": y},
                        {"x": x + width - max(0, shift), "y": y + row_height}, {"x": x - min(0, shift), "y": y + row_height},
                    ]
                elif shape in {"general_polygon", "custom_path", "curved_organic"}:
                    definition["polygon"] = [
                        {"x": x + slant, "y": y}, {"x": x + width * 0.82, "y": y + row_height * 0.04},
                        {"x": x + width, "y": y + row_height * 0.58}, {"x": x + width * 0.88, "y": y + row_height},
                        {"x": x + width * 0.12, "y": y + row_height * 0.94}, {"x": x, "y": y + row_height * 0.36},
                    ]
                else:
                    # Alternate the diagonal so consecutive action panels do not
                    # become a repeated square grid with merely different labels.
                    if reading_order % 2:
                        points = [(x + slant, y), (x + width, y), (x + width - slant, y + row_height), (x, y + row_height)]
                    else:
                        points = [(x, y), (x + width - slant, y), (x + width, y + row_height), (x + slant, y + row_height)]
                    definition["polygon"] = [{"x": px, "y": py} for px, py in points]
            else:
                definition["rect"] = {"x": x, "y": y, "width": width, "height": row_height}
            output.append(definition)
        if row_index < len(rows) - 1:
            y += row_height + vertical_gap
    return output


def _fallback_layout_template(plans: Sequence[Dict[str, Any]], request_texts: Sequence[str]) -> Tuple[str, Dict[str, Any], bool]:
    """Choose a count-compatible non-grid layout when custom geometry is unavailable."""
    count = len(plans)
    context = " ".join(request_texts).casefold() + " " + " ".join(
        " ".join(str(plan.get(key, "")) for key in ("story_event", "emotional_intent", "narrative_function", "shape_preference"))
        for plan in plans
    ).casefold()
    custom_requested = any(term in context for term in ("scratch", "custom panel", "custom layout", "custom geometry"))
    action = bool(re.search(r"\b(?:fight|battle|combat|punch(?:es|ed|ing)?|strike|slash|chase|explosion|impact|action|attack)\b", context)) or any(
        str(plan.get("shape_preference", "")).casefold() in {"trapezoid", "parallelogram", "triangle_wedge"}
        for plan in plans
    )
    comedy = any(term in context for term in ("four-koma", "4-koma", "four koma", "four panel joke", "setup and punchline"))
    reveal = any(term in context for term in ("cinematic", "dramatic reveal", "climax", "major reveal"))

    if custom_requested:
        return "custom", {}, True
    if action:
        by_count = {3: "three_panel_slanted", 4: "three_tier_action_slant", 5: "five_panel_action", 6: "diagonal_slash_battle", 7: "seven_panel_action_burst"}
        if count in by_count:
            return by_count[count], {"panel_ids": [p["panel_id"] for p in plans]}, False
        if count == 2:
            return "two_panel_dramatic_spread", {"panel_ids": [p["panel_id"] for p in plans]}, False
    if comedy and count == 4:
        return "four_koma", {"panel_ids": [p["panel_id"] for p in plans]}, False
    if reveal and count == 4:
        return "four_panel_cinematic", {"panel_ids": [p["panel_id"] for p in plans]}, False
    by_count = {
        1: ("manga_grid", {"rows": 1, "cols": 1}),
        2: ("two_panel_dramatic_spread", {}),
        3: ("three_panel_hero", {}),
        4: ("manga_grid", {"rows": 2, "cols": 2}),
        5: ("five_panel_action", {}),
        6: ("six_panel_classic", {}),
        7: ("seven_panel_action_burst", {}),
        8: ("eight_panel_manhwa", {}),
        9: ("nine_panel_grid", {}),
    }
    template, params = by_count.get(count, ("manga_grid", {"rows": (count + 1) // 2, "cols": 2}))
    return template, {"panel_ids": [p["panel_id"] for p in plans], **params}, False


class StoryToCanvasWorkflow:
    """Runs approved panel plans through registered generation and editor tools."""

    def __init__(
        self,
        *,
        registry,
        session_store,
        session,
        project_id: str,
        plan_result: Any,
        plan_call_id: str,
        source_request_message_id: str,
        request_texts: Sequence[str],
        selected_character_ids: Sequence[str],
        selected_style_profile: Optional[Dict[str, Any]],
        selected_location: Optional[Dict[str, Any]],
        canonical_characters: Dict[str, Any],
        execution_manager,
        effective_budget_usd: float,
        offline_mode: bool,
        activity_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        lettering_only: bool = False,
        lettering_plan: Optional[Dict[str, Any]] = None,
    ):
        self.registry = registry
        self.session_store = session_store
        self.session = session
        self.project_id = project_id
        self.plan_result = plan_result
        self.plan_call_id = plan_call_id
        self.source_request_message_id = source_request_message_id
        self.request_texts = list(request_texts)
        self.selected_character_ids = list(selected_character_ids)
        self.selected_style_profile = selected_style_profile or None
        self.selected_location = selected_location or None
        self.canonical_characters = canonical_characters
        self.execution_manager = execution_manager
        self.effective_budget_usd = max(0.0, float(effective_budget_usd or 0.0))
        self.offline_mode = offline_mode
        self.activity_callback = activity_callback
        self.lettering_only = bool(lettering_only)
        self.lettering_plan = lettering_plan or None
        self.calls: List[ToolCall] = []
        self.results: List[ToolResult] = []
        self.dispatch_context = {"project_id": project_id, "_agent_chat": True}

    def run(self, prior_results: Sequence[Any], prior_calls: Sequence[Any]) -> Tuple[StoryProductionJob, str]:
        if self.lettering_only:
            return self._run_lettering_only()
        plan_data = _value(self.plan_result, "output", {}) or {}
        if self.session.project_id != self.project_id:
            raise PermissionError("The saved Agent session is not scoped to the active project.")
        plan_project_id = plan_data.get("project_id")
        if plan_project_id and plan_project_id != self.project_id:
            raise PermissionError("The approved panel plan belongs to a different project.")
        source_plans = [dict(item) for item in plan_data.get("plans", []) if isinstance(item, dict)]
        if not source_plans:
            raise ValueError("The saved story plan has no typed panel plans to produce.")

        all_texts = list(self.request_texts)
        corrected_plans, id_corrections = corrected_character_ids(
            source_plans, all_texts, self.canonical_characters
        )
        # After a refresh the composer may have no current selection. Recover
        # only context recorded on successful image calls from this plan; every
        # asset still passes the project, version, style, and reference checks.
        if self.selected_style_profile is None:
            self.selected_style_profile = self._recover_profile_snapshot(
                prior_results, "style_profile_id", "style_profile_version", "profile_id"
            )
        if self.selected_location is None:
            self.selected_location = self._recover_profile_snapshot(
                prior_results, "location_id", "location_version", "location_id"
            )
        if not self.selected_character_ids:
            self.selected_character_ids = self._recover_selected_cast(prior_results, prior_calls)
        inherited_cast_panels = self._apply_selected_cast_defaults(
            corrected_plans, self.selected_character_ids, self.canonical_characters
        )
        self._recover_explicit_caption(corrected_plans, all_texts)
        groups = group_panels(corrected_plans, all_texts)
        expected_page_count = plan_data.get("page_count")
        if expected_page_count is not None:
            expected_page_count = int(expected_page_count)
            group_page_numbers = sorted({int(plan.get("page_number") or 0) for plan in corrected_plans})
            if len(groups) != expected_page_count or group_page_numbers != list(range(1, expected_page_count + 1)):
                raise ValueError(
                    f"The approved story blueprint requires exactly {expected_page_count} pages, "
                    f"but its compiled panels cover {len(groups)} pages with page numbers {group_page_numbers}."
                )
        for page_number, group in enumerate(groups, start=1):
            for plan in group:
                plan["page_number"] = page_number

        job_id = stable_job_id(self.project_id, self.session.session_id, self.plan_call_id)
        stored_jobs = self.session.metadata.setdefault("story_production_jobs", {})
        current_job = stored_jobs.get(job_id)
        if current_job:
            job = StoryProductionJob.model_validate(current_job)
            self._restore_job_context(job)
            if self._sync_resumed_selection_allowlist(job, self.selected_character_ids):
                self._checkpoint(job, "selected_cast_allowlist_refreshed")
            # The persisted job plan is already canon-normalized. Reapplying a
            # role correction on each resume could swap the same two IDs back.
            corrected_plans = [dict(item) for item in job.plan.get("plans", [])]
            id_corrections = {}
            plan_by_id = {item["panel_id"]: item for item in corrected_plans}
            groups = [
                [plan_by_id[panel_id] for panel_id in page.panel_ids if panel_id in plan_by_id]
                for page in sorted(job.pages, key=lambda item: item.page_number)
            ]
            page_already_assembled = self._already_assembled(job)
            cast_mismatches = self._saved_cast_mismatches(job) if (job.status == "completed" or page_already_assembled) else []
            if cast_mismatches:
                latest_request = self.request_texts[-1] if self.request_texts else ""
                if selected_cast_repair_requested(latest_request):
                    try:
                        self._prepare_selected_cast_repair(job, corrected_plans, cast_mismatches)
                        plan_by_id = {item["panel_id"]: item for item in job.plan["plans"]}
                        page_already_assembled = False
                    except Exception as exc:
                        job.status = "needs_attention"
                        message = f"Selected-character repair was not started: {exc}"
                        if message not in job.errors:
                            job.errors.append(message)
                        self._checkpoint(job, "selected_cast_repair_preflight_failed")
                        return job, self._summary(job, message)
                else:
                    attention = (
                        "Selected character identity context is missing from generation receipts for panels: "
                        + ", ".join(cast_mismatches)
                        + ". The saved artwork is preserved and must be replaced to correct those panels."
                    )
                    if attention not in job.errors:
                        job.errors.append(attention)
                    job.status = "needs_attention"
                    self._checkpoint(job, "saved_panel_cast_mismatch")
                    return job, self._summary(
                        job,
                        "The Canvas page is saved, but its generation receipts show that the selected characters were omitted from "
                        + ", ".join(cast_mismatches)
                        + ". I left the existing artwork untouched; those panels need replacement with the selected character references.",
                    )
            if job.status == "completed":
                return job, self._summary(job, "This approved story is already assembled in Canvas.")
            if page_already_assembled:
                panel_count = len(job.panels)
                return job, self._summary(
                    job,
                    f"I found your saved {panel_count}-panel story and Canvas page in this chat. "
                    "Those panels are already generated and placed, so I kept the existing work without making duplicates.",
                )
        else:
            panels = {}
            for plan in corrected_plans:
                panel_id = plan["panel_id"]
                declared_ids = list(plan.get("character_ids", [])) if "character_ids" in plan else list(self.selected_character_ids)
                versions = {
                    cid: int(getattr(self.canonical_characters[cid], "canon_version", getattr(self.canonical_characters[cid], "version", 1)) or 1)
                    for cid in declared_ids if cid in self.canonical_characters
                }
                panels[panel_id] = PanelProduction(
                    panel_id=panel_id,
                    page_number=int(plan["page_number"]),
                    character_ids=declared_ids,
                    character_versions=versions,
                    prop_ids=list(plan.get("prop_ids") or []),
                    prop_states={str(key): str(value) for key, value in (plan.get("prop_states") or {}).items()},
                    style_profile_id=(self.selected_style_profile or {}).get("profile_id"),
                    style_profile_version=(self.selected_style_profile or {}).get("version"),
                    provenance={
                        "plan_call_id": self.plan_call_id,
                        "scene_id": plan.get("scene_id"),
                        "location_id": (self.selected_location or {}).get("location_id"),
                        "location_version": (self.selected_location or {}).get("version"),
                    },
                )
            pages = [
                PageProduction(
                    page_number=index,
                    page_id=stable_page_id(job_id, index),
                    panel_ids=[item["panel_id"] for item in group],
                )
                for index, group in enumerate(groups, start=1)
            ]
            # Composer selections are an allow-list. IDs the creator explicitly
            # named in this approved production request are also authorized, so
            # a temporarily stale composer selection cannot silently omit a
            # character the creator expressly requested.
            explicitly_named_ids = {
                id_corrections.get(character_id, character_id)
                for text in all_texts
                for character_id in re.findall(r"\bchar_[a-z0-9_-]+\b", text, flags=re.IGNORECASE)
                if id_corrections.get(character_id, character_id) in self.canonical_characters
            }
            approved_ids = list(dict.fromkeys([
                *self.selected_character_ids,
                *(id_corrections.get(cid, cid) for cid in explicitly_named_ids),
            ]))
            approved_ids = [cid for cid in approved_ids if cid in self.canonical_characters]
            if not approved_ids:
                approved_ids = list(dict.fromkeys(
                    cid for plan in corrected_plans for cid in plan.get("character_ids", [])
                ))
            if id_corrections:
                approved_ids = list(dict.fromkeys(id_corrections.get(cid, cid) for cid in approved_ids))
            job = StoryProductionJob(
                job_id=job_id,
                run_id=job_id,
                project_id=self.project_id,
                source_request_message_id=self.source_request_message_id,
                source_plan_call_id=self.plan_call_id,
                goal=(
                    f"Create exactly {expected_page_count} Canvas pages, generate and place all {len(corrected_plans)} planned artworks, "
                    "and verify every saved page."
                    if expected_page_count is not None
                    else f"Generate and place all {len(corrected_plans)} planned artworks, assemble their Canvas pages, and verify each saved page."
                ),
                target_page_count=expected_page_count or len(groups),
                page_panel_counts={str(index): len(group) for index, group in enumerate(groups, start=1)},
                plan={**plan_data, "plans": corrected_plans, "schema_version": "1.1.0"},
                page_panel_count=max((len(group) for group in groups), default=6),
                pages=pages,
                panels=panels,
                selected_character_ids=approved_ids,
                style_profile_id=(self.selected_style_profile or {}).get("profile_id"),
                style_profile_version=(self.selected_style_profile or {}).get("version"),
                style_snapshot=self.selected_style_profile,
                location_id=(self.selected_location or {}).get("location_id"),
                location_version=(self.selected_location or {}).get("version"),
                location_snapshot=self.selected_location,
                assumptions=list(plan_data.get("assumptions") or []),
            )
            if inherited_cast_panels:
                job.assumptions.append(
                    "Creator-selected character references were applied as the default cast for panels with no explicit cast: "
                    + ", ".join(inherited_cast_panels)
                    + ". Intentional character-free panels must be marked characterless."
                )
            if id_corrections:
                job.assumptions.append("Canonical role IDs corrected by unique Story Bible names: " + ", ".join(
                    f"{old} → {new}" for old, new in sorted(id_corrections.items())
                ))
            missing_text = [
                p["panel_id"] for p in corrected_plans
                if (p.get("text") or {}).get("carrier", "none") not in ("none", "")
                and not str((p.get("text") or {}).get("text_content") or "").strip()
            ]
            if missing_text:
                job.assumptions.append(
                    "Approved panel plan specified lettering carriers but no exact text for: " + ", ".join(missing_text)
                )

        plan_by_id = {item["panel_id"]: item for item in job.plan["plans"]}
        try:
            self._prepare_story_object_drafts(job, plan_by_id)
        except Exception as exc:
            job.status = "needs_attention"
            message = f"Recurring object setup failed before Canvas production: {exc}"
            if message not in job.errors:
                job.errors.append(message)
            self._checkpoint(job, "object_draft_preflight_failed")
            return job, self._summary(job, message)
        self._load_prior_panel_results(job, plan_by_id, prior_results, prior_calls)
        self._recover_checkpointed_generation_results(job)
        cast_scope_errors = self._selected_cast_scope_errors(job)
        if cast_scope_errors:
            for panel_id, message in cast_scope_errors.items():
                panel = job.panels[panel_id]
                if not panel.asset_id:
                    panel.status = "needs_attention"
                    panel.error = message
            names_by_id = {
                character_id: str(getattr(character, "name", "") or character_id)
                for character_id, character in self.canonical_characters.items()
            }
            missing_names = sorted({
                names_by_id.get(character_id, character_id)
                for message in cast_scope_errors.values()
                for character_id in re.findall(r"\b(?:char_[a-z0-9_-]+|nour)\b", message, flags=re.IGNORECASE)
            })
            job.status = "needs_attention"
            summary = (
                "The saved panel plan needs characters that are not selected for this run"
                + (": " + ", ".join(missing_names) if missing_names else "")
                + ". I paused before generating or placing any more artwork. Select those characters or revise the plan's cast, then resume."
            )
            if summary not in job.errors:
                job.errors.append(summary)
            self._checkpoint(job, "selected_cast_preflight_failed")
            return job, self._summary(job, summary)
        self._clear_resolved_selected_cast_failures(job)
        missing_assets = [panel for panel in job.panels.values() if not panel.asset_id]
        missing_text = []
        required_tools = {"canvas.place_panel_artwork", "canvas.verify_page", "canvas.inspect_page_spacing"}
        if missing_assets and not self.offline_mode:
            required_tools.add("generation.generate_image")
        for plan in job.plan["plans"]:
            lines = plan.get("script_lines") or []
            if not lines and plan.get("text"):
                t = plan["text"]
                if str(t.get("text_content") or "").strip():
                    lines = [t]
            for line in lines:
                content = str(line.get("text") or line.get("text_content") or "").strip()
                if not content:
                    continue
                c = line.get("carrier", "speech_bubble")
                if hasattr(c, "value"):
                    c = c.value
                k = line.get("kind") or line.get("content_kind")
                if hasattr(k, "value"):
                    k = k.value
                tid = line.get("type_id")
                if c in ("caption", "narration_box", "narration") or k in ("narration", "date_or_place") or tid in ("narration.box", "caption.timeplace"):
                    required_tools.add("editor.add_text_layer")
                    if not self._text_layer_tool_available("caption"):
                        missing_text.append(plan["panel_id"])
                elif c in ("speech_bubble", "thought_bubble") or k in ("spoken_dialogue", "emotional_speech", "internal_thought"):
                    required_tools.add("canvas.add_speech_bubble")
                    if not self._text_layer_tool_available(c):
                        missing_text.append(plan["panel_id"])
                elif c not in ("none", ""):
                    required_tools.add("editor.add_text_layer")
                    if not self._text_layer_tool_available(c):
                        missing_text.append(plan["panel_id"])
        available_ids = self._available_tool_ids()
        if not ({"canvas.create_page_from_template", "canvas.create_custom_page"} & available_ids):
            job.status = "needs_attention"
            job.errors.append("No registered Canvas page-creation tool is available; the production page was not created.")
            self._checkpoint(job, "page_creation_tool_unavailable")
            return job, self._summary(job, "Production stopped because the Canvas page-creation tool is unavailable.")
        unavailable = sorted(required_tools - available_ids)
        if unavailable:
            job.status = "needs_attention"
            job.errors.append("Required registered tools are unavailable: " + ", ".join(unavailable))
            self._checkpoint(job, "tool_preflight_failed")
            return job, self._summary(job, "Production stopped before mutation because required Canvas/provider tools are unavailable.")
        if missing_assets and self.offline_mode:
            job.status = "needs_attention"
            job.errors.append("Live image generation is disabled in explicit offline mode; no simulated artwork was substituted.")
            self._checkpoint(job, "offline_provider_blocked")
            return job, self._summary(job, "Production is paused: live image generation is unavailable in offline mode.")

        generation_tool = self.registry.get_tool("generation.generate_image") if missing_assets else None
        unit_cost = getattr(generation_tool, "estimated_cost_usd", None) if generation_tool else 0.0
        required_estimate = len(missing_assets) * float(unit_cost or 0.0)
        if missing_assets and (unit_cost is None or float(unit_cost) <= 0):
            job.status = "needs_attention"
            job.errors.append("The image tool has no usable per-image cost estimate; generation was not started.")
            self._checkpoint(job, "budget_estimate_unavailable")
            return job, self._summary(job, "Production is paused because the configured image tool has no usable cost estimate.")
        if required_estimate > self.effective_budget_usd:
            job.status = "needs_attention"
            job.errors.append(
                f"Estimated remaining generation cost ${required_estimate:.4f} exceeds the available run budget ${self.effective_budget_usd:.4f}."
            )
            self._checkpoint(job, "budget_preflight_blocked")
            return job, self._summary(job, "Production is paused by the current budget; no missing images were generated.")

        self._start_execution_run(job)
        self._checkpoint(job, "preflight_passed")
        self._ensure_pages(job, groups)
        self._generate_missing(job, plan_by_id, prior_results, prior_calls, unit_cost or 0.0)
        self._place_assets(job, plan_by_id)
        self._place_text(job, plan_by_id)
        self._verify_pages(job, plan_by_id)
        self._composite_and_export_pages(job)

        planned_panel_count = len(job.plan.get("plans") or [])
        expected_pages = job.target_page_count or len(job.pages)
        expected_page_numbers = list(range(1, expected_pages + 1)) if expected_pages else []
        all_panels_placed = (
            len(job.panels) == planned_panel_count
            and all(panel.status == "placed" and panel.asset_id for panel in job.panels.values())
        )
        all_pages_verified = (
            len(job.pages) == expected_pages
            and sorted(page.page_number for page in job.pages) == expected_page_numbers
            and all(
                page.status == "assembled"
                and page.revision is not None
                and page.verification.get("passed") is True
                for page in job.pages
            )
        )
        if not all_panels_placed:
            job.errors.append("The job goal is not complete because one or more planned artworks are not saved in Canvas.")
        if not all_pages_verified:
            job.errors.append(f"The job goal is not complete because all {expected_pages} requested pages are not saved and verified.")
        has_missing_lettering = any(
            (plan.get("text") or {}).get("carrier", "none") not in ("none", "")
            and not str((plan.get("text") or {}).get("text_content") or "").strip()
            for plan in job.plan["plans"]
        )
        if has_missing_lettering:
            lettering_attention = (
                "The approved panel plan reserved lettering carriers but contains no exact text. "
                "No dialogue or captions were invented; add the wording in Canvas to finish lettering."
            )
            if lettering_attention not in job.errors:
                job.errors.append(lettering_attention)
        job.status = "completed" if all_panels_placed and all_pages_verified and not has_missing_lettering else "needs_attention"
        self._checkpoint(job, "production_completed" if job.status == "completed" else "production_needs_attention")
        self._finish_execution_run(job)
        return job, self._summary(job)

    def _run_lettering_only(self) -> Tuple[StoryProductionJob, str]:
        """Continue a verified saved job with editable text tools only."""
        from app.agent.production import saved_job_ready_for_lettering
        from app.editor.models import LayerKind
        from app.planning.panel_planner import PanelTextPlan, TextContentKind
        import re

        if self.session.project_id != self.project_id:
            raise PermissionError("The saved Agent session is not scoped to the active project.")
        plan_output = _value(self.lettering_plan, "output", self.lettering_plan) or {}
        job_id = str(plan_output.get("job_id") or "")
        saved_jobs = self.session.metadata.get("story_production_jobs", {})
        raw_job = saved_jobs.get(job_id) if isinstance(saved_jobs, dict) else None
        if not isinstance(raw_job, dict) or raw_job.get("project_id") != self.project_id:
            raise PermissionError("The lettering plan does not refer to a saved job in the active project.")
        if not saved_job_ready_for_lettering(raw_job):
            job = StoryProductionJob.model_validate(raw_job)
            return self._lettering_attention(job, "The saved job no longer has complete placed artwork and persisted pages; lettering was not started.")
        job = StoryProductionJob.model_validate(raw_job)
        if job.project_id != self.project_id:
            raise PermissionError("The saved Canvas job belongs to a different project.")

        original_plans = [dict(item) for item in job.plan.get("plans", []) if isinstance(item, dict)]
        plans_by_id = {str(item.get("panel_id")): item for item in original_plans if item.get("panel_id")}
        decisions = plan_output.get("decisions") or []
        decision_ids = [str(item.get("panel_id")) for item in decisions if isinstance(item, dict)]
        if len(decision_ids) != len(set(decision_ids)) or set(decision_ids) != set(plans_by_id):
            return self._lettering_attention(job, "The model's lettering plan did not match the saved panel IDs exactly; no Canvas changes were made.")
        decisions_by_id = {str(item["panel_id"]): item for item in decisions}

        # Preflight every saved page before creating any text layer. A stale or
        # incomplete page must not produce a partially lettered book.
        page_docs = {}
        original_text_layer_ids = {}
        for page in job.pages:
            doc = self._page_document(page.page_id)
            if doc is None or doc.project_id != self.project_id:
                return self._lettering_attention(job, f"Saved Canvas page {page.page_id} could not be reopened in this project; lettering was not started.")
            doc_panel_ids = {slot.panel_id for slot in doc.layout.panel_slots}
            if set(page.panel_ids) != doc_panel_ids:
                return self._lettering_attention(job, f"Saved Canvas page {page.page_id} no longer matches the job's panel IDs; lettering was not started.")
            if page.verification.get("spacing_valid") is False:
                return self._lettering_attention(job, f"Page {page.page_id} has a saved spacing failure; lettering was not started.")
            page_docs[page.page_id] = doc
            original_text_layer_ids[page.page_id] = {
                layer.layer_id for layer in doc.layers if layer.kind == LayerKind.TEXT
            }

        updated_plans = {panel_id: dict(plan) for panel_id, plan in plans_by_id.items()}
        for panel_id, decision in decisions_by_id.items():
            panel = job.panels.get(panel_id)
            if (
                not panel
                or panel.status not in ("placed", "needs_attention")
                or not panel.asset_id
                or (panel.status == "needs_attention" and not self._is_lettering_failure(panel.error))
            ):
                return self._lettering_attention(job, f"Panel {panel_id} has no verified saved artwork; lettering was not started.")
            page = next((item for item in job.pages if panel_id in item.panel_ids), None)
            doc = page_docs.get(page.page_id) if page else None
            if not doc:
                return self._lettering_attention(job, f"Panel {panel_id} is not linked to a saved Canvas page; lettering was not started.")
            image_layer = next((layer for layer in doc.layers if layer.panel_id == panel_id and layer.kind == LayerKind.IMAGE), None)
            if not image_layer or image_layer.source_asset_id != panel.asset_id:
                return self._lettering_attention(job, f"Panel {panel_id}'s Canvas artwork does not match the saved production asset; lettering was not started.")

            try:
                text_plan = PanelTextPlan.model_validate(decision.get("text") or {})
            except Exception as exc:
                return self._lettering_attention(job, f"Panel {panel_id} has an invalid lettering decision ({exc}); no Canvas changes were made.")
            content = (text_plan.text_content or "").strip()
            if text_plan.content_kind in (TextContentKind.SPOKEN_DIALOGUE, TextContentKind.EMOTIONAL_SPEECH, TextContentKind.INTERNAL_THOUGHT):
                if text_plan.speaker_id not in set(panel.character_ids):
                    return self._lettering_attention(job, f"Panel {panel_id} uses a speaker outside its selected cast; no Canvas changes were made.")
            if text_plan.content_kind in (TextContentKind.SPOKEN_DIALOGUE, TextContentKind.EMOTIONAL_SPEECH):
                if len(re.findall(r"\S+", content)) > 12:
                    return self._lettering_attention(job, f"New dialogue in panel {panel_id} exceeds 12 words; no Canvas changes were made.")

            existing_text_layers = [layer for layer in doc.layers if layer.panel_id == panel_id and layer.kind == LayerKind.TEXT]
            existing_plan_text = updated_plans[panel_id].get("text") or {}
            if existing_text_layers:
                existing_content = str(existing_plan_text.get("text_content") or "").strip()
                expected_speaker = existing_plan_text.get("speaker_id")
                if not existing_content or any(
                    str(layer.metadata.get("text") or "").strip() != existing_content
                    or layer.metadata.get("speaker_character_id") != expected_speaker
                    for layer in existing_text_layers
                ):
                    return self._lettering_attention(job, f"Panel {panel_id} contains existing text that is not represented by the saved plan; the Agent left it untouched.")
                if content and content != existing_content:
                    return self._lettering_attention(job, f"Panel {panel_id} already has different saved wording; the Agent will not replace or duplicate it.")
                # Keep the saved wording and its provenance; this follow-up is additive only.
                continue

            row = dict(updated_plans[panel_id])
            row["text"] = text_plan.model_dump(mode="json")
            row["delivery"] = decision.get("delivery")
            row["emotional_intent"] = decision.get("emotional_intent") or row.get("emotional_intent")
            updated_plans[panel_id] = row

        available_ids = self._available_tool_ids()
        for decision in decisions:
            panel_id = str(decision.get("panel_id"))
            # Existing-text panels were preserved above; only preflight tools for new content.
            if any(layer.panel_id == panel_id and layer.kind == LayerKind.TEXT for layer in page_docs[
                next(page.page_id for page in job.pages if panel_id in page.panel_ids)
            ].layers):
                continue
            text_plan = updated_plans[panel_id].get("text") or {}
            carrier = text_plan.get("carrier")
            text = str(text_plan.get("text_content") or "").strip()
            if not text or carrier in (None, "none", ""):
                continue
            required_tool = "canvas.add_speech_bubble" if carrier in ("speech_bubble", "thought_bubble") else "editor.add_text_layer"
            if required_tool not in available_ids:
                return self._lettering_attention(job, f"Required lettering tool {required_tool} is unavailable; no Canvas changes were made.")
        if "canvas.verify_page" not in available_ids:
            return self._lettering_attention(job, "The saved pages cannot be safely verified; lettering was not started.")

        # Verify the saved page assets before allowing the first mutation.
        for page in job.pages:
            doc = page_docs[page.page_id]
            expected_artworks = [
                {"panel_id": panel_id, "asset_id": job.panels[panel_id].asset_id}
                for panel_id in page.panel_ids
            ]
            call = ToolCall(
                call_id=f"{job.job_id}_lettering_preflight_{page.page_number}",
                tool_id="canvas.verify_page",
                arguments={
                    "page_id": page.page_id,
                    "expected_revision": doc.revision,
                    "expected_panel_ids": page.panel_ids,
                    "required_artwork_panel_ids": page.panel_ids,
                    "expected_artworks": expected_artworks,
                    "expected_texts": [
                        {"panel_id": layer.panel_id, "text": layer.metadata.get("text", ""), "speaker_character_id": layer.metadata.get("speaker_character_id")}
                        for layer in doc.layers if layer.kind == LayerKind.TEXT and layer.panel_id in page.panel_ids
                    ],
                },
            )
            result = self._dispatch(call)
            if result.status != "success" or not (result.output or {}).get("passed"):
                return self._lettering_attention(job, f"Page {page.page_id} failed saved-artwork verification; no lettering was added.")

        job.plan["plans"] = [updated_plans[item["panel_id"]] for item in original_plans]
        lettering_history = list(job.plan.get("lettering_continuations") or [])
        lettering_history.append({
            "last_request_message_id": self.session.messages[-1].message_id if self.session.messages else None,
            "tool_call_id": _value(self.lettering_plan, "call_id"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "model_tool:planning.plan_lettering",
            "panel_ids": [str(item.get("panel_id")) for item in decisions],
        })
        job.plan["lettering_continuations"] = lettering_history
        job.schema_version = "1.4.0"
        job.lettering_goal = "Add requested editable lettering to the saved Canvas pages and verify the revisions without changing artwork or geometry."
        job.status = "assembling"
        self._checkpoint(job, "lettering_preflight_passed")

        plan_by_id = {item["panel_id"]: item for item in job.plan["plans"]}
        self._place_text(job, plan_by_id)
        self._verify_pages(job, plan_by_id)
        self._composite_and_export_pages(job)

        all_art_unchanged = all(
            job.panels[panel_id].asset_id
            and any(
                layer.kind == LayerKind.IMAGE and layer.panel_id == panel_id
                and layer.source_asset_id == job.panels[panel_id].asset_id
                for layer in (self._page_document(page.page_id).layers if self._page_document(page.page_id) else [])
            )
            for page in job.pages for panel_id in page.panel_ids
        )
        all_pages_verified = all(
            page.status == "assembled" and page.verification.get("passed") is True
            for page in job.pages
        )
        recovered_panels = []
        if all_art_unchanged and all_pages_verified:
            for panel_id, panel in job.panels.items():
                if panel.status == "needs_attention" and self._is_lettering_failure(panel.error):
                    panel.status = "placed"
                    panel.error = None
                    recovered_panels.append(panel_id)
            if recovered_panels:
                job.errors = [
                    error for error in job.errors
                    if not any(error.startswith(f"Panel {panel_id} text placement failed:") for panel_id in recovered_panels)
                ]
        all_panels_placed = all(panel.status == "placed" and panel.asset_id for panel in job.panels.values())
        job.status = "completed" if all_art_unchanged and all_pages_verified and all_panels_placed else "needs_attention"
        if not all_art_unchanged:
            job.errors.append("Post-lettering verification could not confirm every original artwork asset remained placed.")
        self._checkpoint(job, "lettering_completed" if job.status == "completed" else "lettering_needs_attention")
        new_text_layer_count = sum(
            1 for page in job.pages
            for layer in (self._page_document(page.page_id).layers if self._page_document(page.page_id) else [])
            if layer.kind == LayerKind.TEXT and layer.layer_id not in original_text_layer_ids.get(page.page_id, set())
        )
        if new_text_layer_count:
            lead = f"Added and verified {new_text_layer_count} editable lettering layer(s) on the saved Canvas pages. Existing artwork assets and panel geometry were preserved."
        elif any(original_text_layer_ids.values()):
            lead = "No new lettering was needed for this continuation; existing editable text and artwork were preserved and verified."
        else:
            lead = "The story planner found no lettering needed for these saved visual beats; the pages were re-verified and no text was added."
        return job, self._summary(job, lead)

    def _lettering_attention(self, job: StoryProductionJob, message: str) -> Tuple[StoryProductionJob, str]:
        job.status = "needs_attention"
        job.errors.append(message)
        self._checkpoint(job, "lettering_preflight_needs_attention")
        return job, self._summary(job, message)

    @staticmethod
    def _is_lettering_failure(message: Optional[str]) -> bool:
        lowered = str(message or "").casefold()
        return any(marker in lowered for marker in (
            "letter", "text", "bubble", "speaker", "dialogue", "caption", "wording", "overflow",
        ))

    def _available_tool_ids(self) -> set[str]:
        try:
            return {tool.tool_id for tool in self.registry.list_tools(callable_only=True)}
        except TypeError:
            return {tool.tool_id for tool in self.registry.list_image_chat_tools()}
        except Exception:
            return set()

    @staticmethod
    def _already_assembled(job: StoryProductionJob) -> bool:
        """Recognize a verified saved page even when lettering still needs attention."""
        plans = job.plan.get("plans", [])
        planned_panel_ids = [
            str(item.get("panel_id")) for item in plans
            if isinstance(item, dict) and item.get("panel_id")
        ]
        if not planned_panel_ids or len(set(planned_panel_ids)) != len(planned_panel_ids):
            return False
        if set(job.panels) != set(planned_panel_ids):
            return False
        if not all(panel.status == "placed" and panel.asset_id for panel in job.panels.values()):
            return False
        page_panel_ids = [panel_id for page in job.pages for panel_id in page.panel_ids]
        if sorted(page_panel_ids) != sorted(planned_panel_ids):
            return False
        expected_pages = job.target_page_count or len(job.pages)
        return len(job.pages) == expected_pages and sorted(page.page_number for page in job.pages) == list(range(1, expected_pages + 1)) and bool(job.pages) and all(
            page.status == "assembled"
            and page.revision is not None
            and page.verification.get("passed") is True
            for page in job.pages
        )

    @staticmethod
    def _saved_cast_mismatches(job: StoryProductionJob) -> List[str]:
        """Find panels whose successful generation receipt omitted the saved cast."""
        mismatches = []
        for plan in job.plan.get("plans", []):
            if not isinstance(plan, dict) or not plan.get("panel_id"):
                continue
            panel_id = str(plan["panel_id"])
            panel = job.panels.get(panel_id)
            if panel is None:
                continue
            expected = list(plan.get("character_ids") or [])
            if not expected and not plan.get("characterless"):
                expected = list(job.selected_character_ids)
            generated = list(panel.provenance.get("character_ids") or [])
            if expected and (set(generated) != set(expected) or set(panel.character_ids) != set(expected)):
                mismatches.append(panel_id)
        return mismatches

    @staticmethod
    def _selected_cast_scope_errors(job: StoryProductionJob) -> Dict[str, str]:
        """Find planned cast IDs outside the creator's approved run allow-list."""
        allowed = set(job.selected_character_ids)
        if not allowed:
            return {}
        errors: Dict[str, str] = {}
        for plan in job.plan.get("plans", []):
            if not isinstance(plan, dict) or not plan.get("panel_id"):
                continue
            panel_id = str(plan["panel_id"])
            panel = job.panels.get(panel_id)
            if panel is None or plan.get("characterless"):
                continue
            planned_ids = set(panel.character_ids or plan.get("character_ids") or [])
            unselected = sorted(planned_ids - allowed)
            if unselected:
                errors[panel_id] = (
                    "The approved panel cast contains characters outside the current selected/reference allow-list: "
                    + ", ".join(unselected)
                )
        return errors

    @staticmethod
    def _sync_resumed_selection_allowlist(job: StoryProductionJob, selected_character_ids: Sequence[str]) -> bool:
        """Accept an explicit refreshed selection only when it covers the saved plan's full cast."""
        selected = list(dict.fromkeys(selected_character_ids or []))
        if not selected or set(selected) == set(job.selected_character_ids):
            return False
        planned_ids = {
            character_id
            for plan in job.plan.get("plans", [])
            if isinstance(plan, dict) and not plan.get("characterless")
            for character_id in (plan.get("character_ids") or [])
        }
        if not planned_ids.issubset(set(selected)):
            return False
        job.selected_character_ids = selected
        assumption = (
            "The creator refreshed the selected-character allow-list before resuming; "
            "the saved per-panel cast and existing artwork were preserved."
        )
        if assumption not in job.assumptions:
            job.assumptions.append(assumption)
        return True

    @staticmethod
    def _clear_resolved_selected_cast_failures(job: StoryProductionJob) -> None:
        """Requeue only local cast blocks after the creator selects the saved plan's full cast."""
        panel_ids = set()
        for panel in job.panels.values():
            if (
                panel.status == "needs_attention"
                and (panel.error or "").startswith("The approved panel cast contains characters outside the current selected/reference allow-list:")
                and set(panel.character_ids).issubset(set(job.selected_character_ids))
            ):
                panel.status = "pending"
                panel.error = None
                panel_ids.add(panel.panel_id)
        if panel_ids:
            job.errors = [
                error for error in job.errors
                if not any(error == f"Panel {panel_id} character scope needs attention." for panel_id in panel_ids)
                and not error.startswith("The saved panel plan needs characters that are not selected for this run")
            ]

    def _prepare_selected_cast_repair(
        self, job: StoryProductionJob, plans: List[Dict[str, Any]], mismatch_panel_ids: Sequence[str]
    ) -> None:
        """Checkpoint a scoped repair; only the exact old artwork layer may be replaced later."""
        selected_ids = list(job.selected_character_ids)
        if not selected_ids:
            raise ValueError("The saved job has no creator-selected character IDs to apply.")
        missing = [character_id for character_id in selected_ids if character_id not in self.canonical_characters]
        if missing:
            raise ValueError("Selected characters are no longer available in this project's Canon: " + ", ".join(missing))
        plan_by_id = {str(plan.get("panel_id")): plan for plan in plans}
        panels_by_id = job.panels
        current_layer_ids = {}
        from app.editor.models import LayerKind

        for panel_id in mismatch_panel_ids:
            plan = plan_by_id.get(panel_id)
            panel = panels_by_id.get(panel_id)
            if plan is None or panel is None or not panel.asset_id:
                raise ValueError(f"Panel {panel_id} no longer has the saved mismatched artwork expected for repair.")
            page = next((item for item in job.pages if panel_id in item.panel_ids), None)
            doc = self._page_document(page.page_id) if page else None
            if doc is None or doc.project_id != self.project_id:
                raise ValueError(f"The saved Canvas page for {panel_id} could not be verified in the active project.")
            current = next((
                layer for layer in doc.layers
                if layer.panel_id == panel_id and layer.kind == LayerKind.IMAGE
            ), None)
            if current is None or current.source_asset_id != panel.asset_id:
                raise ValueError(
                    f"Panel {panel_id}'s current Canvas artwork changed after the saved job; it was preserved. Refresh before repairing."
                )
            current_layer_ids[panel_id] = current.layer_id

        selected_names = [str(getattr(self.canonical_characters[cid], "name", "") or cid) for cid in selected_ids]
        for panel_id in mismatch_panel_ids:
            plan = plan_by_id[panel_id]
            panel = panels_by_id[panel_id]
            previous_asset_id = panel.asset_id
            panel.provenance["previous_generation_provenance"] = {
                key: value for key, value in panel.provenance.items()
                if key not in {"checkpointed_generation_result", "previous_generation_provenance"}
            }
            panel.replacement_expected_asset_id = previous_asset_id
            panel.image_layer_id = current_layer_ids[panel_id]
            panel.character_ids = list(selected_ids)
            panel.character_versions = {
                cid: int(getattr(self.canonical_characters[cid], "canon_version", getattr(self.canonical_characters[cid], "version", 1)) or 1)
                for cid in selected_ids
            }
            panel.asset_id = None
            panel.asset_sha256 = None
            panel.status = "pending"
            panel.error = None
            plan["character_ids"] = list(selected_ids)
            plan["characterless"] = False
            plan["character_selection_source"] = "creator_selected_default"
            instruction = (
                " Creator-selected cast: " + ", ".join(selected_names)
                + ". Include these exact canonical characters using their supplied identity reference images; do not substitute generic people or creatures."
            )
            brief = str(plan.get("image_brief") or "").strip()
            if instruction not in brief:
                plan["image_brief"] = brief + instruction
            for page in job.pages:
                if panel_id in page.panel_ids:
                    page.status = "created"
                    break

        job.plan["plans"] = plans
        job.plan["schema_version"] = "1.2.0"
        job.errors = [
            error for error in job.errors
            if "Selected character identity context is missing from generation receipts" not in error
        ]
        assumption = (
            "Creator requested replacement of panels missing selected-cast references: "
            + ", ".join(mismatch_panel_ids)
            + ". Previous source assets are retained in the library and Canvas layer replacement is scoped by asset ID."
        )
        if assumption not in job.assumptions:
            job.assumptions.append(assumption)
        repair_fingerprint = hashlib.sha256(
            "|".join([job.job_id, *sorted(mismatch_panel_ids), *selected_ids]).encode("utf-8")
        ).hexdigest()[:10]
        job.run_id = f"{job.job_id}_castrepair_{repair_fingerprint}"
        job.status = "preflight"
        self._checkpoint(job, "selected_cast_repair_prepared")

    def _text_layer_tool_available(self, carrier: str) -> bool:
        return "canvas.add_speech_bubble" in self._available_tool_ids() if carrier in ("speech_bubble", "thought_bubble") else "editor.add_text_layer" in self._available_tool_ids()

    def _checkpoint(self, job: StoryProductionJob, stage: str) -> None:
        job.updated_at = datetime.now(timezone.utc).isoformat()
        job.stage = stage
        self.session.active_run_id = job.run_id
        self.session.metadata.setdefault("story_production_jobs", {})[job.job_id] = job.model_dump(mode="json")
        save = getattr(self.session_store, "save_session", None)
        if callable(save):
            save(self.session)
        if self.activity_callback:
            try:
                self.activity_callback({
                    "production_job": {
                        "schema_version": job.schema_version,
                        "job_id": job.job_id,
                        "run_id": job.run_id,
                        "project_id": job.project_id,
                        "goal": job.goal,
                        "target_page_count": job.target_page_count,
                        "page_panel_counts": dict(job.page_panel_counts),
                        "stage": job.stage,
                        "status": job.status,
                        "updated_at": job.updated_at,
                        "pages": [page.model_dump(mode="json") for page in job.pages],
                        "panels": {
                            panel_id: panel.model_dump(mode="json", include={
                                "panel_id", "page_number", "status", "asset_id",
                                "generation_attempts", "automatic_retries", "manual_retries", "error",
                            })
                            for panel_id, panel in job.panels.items()
                        },
                        "errors": list(job.errors),
                    },
                    "stage": stage,
                })
            except Exception:
                # Progress transport is optional; the durable checkpoint above
                # remains authoritative if the browser has disconnected.
                pass
        try:
            from app.execution.states import ExecutionEventType
            if self.execution_manager.db.get_run(job.run_id):
                self.execution_manager._log_event(
                    run_id=job.run_id,
                    event_type=ExecutionEventType.CREATIVE_JOB_CHECKPOINT,
                    data={"job_id": job.job_id, "stage": stage, "status": job.status,
                          "completed_panels": sum(panel.status == "placed" for panel in job.panels.values()),
                          "total_panels": len(job.panels), "page_ids": [page.page_id for page in job.pages]},
                )
        except Exception:
            # The session checkpoint is authoritative; a secondary event ledger
            # issue must not cause already-persisted page mutations to be repeated.
            pass

    def _start_execution_run(self, job: StoryProductionJob) -> None:
        try:
            from app.execution.states import RunStatus
            run = self.execution_manager.db.get_run(job.run_id)
            if run is None:
                self.execution_manager.create_run(
                    project_id=self.project_id,
                    canon_hash=getattr(self, "canon_hash", None),
                    budget_limit_usd=max(self.effective_budget_usd, 0.0001),
                    run_id=job.run_id,
                    metadata={"kind": "story_to_canvas", "job_id": job.job_id, "schema_version": job.schema_version},
                )
                run = self.execution_manager.db.get_run(job.run_id)
            if run is None:
                return
            if run.status in (RunStatus.CREATED, RunStatus.QUEUED):
                self.execution_manager.start_run(job.run_id)
            elif run.status in (RunStatus.NEEDS_REVIEW, RunStatus.INTERRUPTED):
                self.execution_manager.resume_needs_review_run(job.run_id)
        except Exception:
            # The durable session job remains resumable if the optional ledger
            # is unavailable; the final response reports only the primary state.
            return

    def _finish_execution_run(self, job: StoryProductionJob) -> None:
        try:
            if job.status == "completed":
                self.execution_manager.complete_run(job.run_id)
            else:
                self.execution_manager.mark_run_needs_review(job.run_id, "; ".join(job.errors) or "Production needs creator attention.")
        except Exception:
            return

    def _recover_explicit_caption(self, plans: List[Dict[str, Any]], texts: Sequence[str]) -> None:
        caption = None
        for text in texts:
            match = re.search(r"(?:^|\n)\s*Caption\s*:\s*\n+(.+?)(?:\n\s*\n|\Z)", text, re.IGNORECASE | re.DOTALL)
            if match:
                caption = match.group(1).strip()
        if not caption:
            return
        candidates = [p for p in plans if (p.get("text") or {}).get("carrier") == "caption"]
        if not candidates:
            candidates = [
                plan for plan in plans
                if (plan.get("text") or {}).get("content_kind") == "none"
                or (plan.get("text") or {}).get("carrier", "none") in ("none", "")
            ][:1]
        if len(candidates) == 1:
            text_plan = candidates[0].setdefault("text", {})
            text_plan.update({
                "content_kind": "narration",
                "carrier": "caption",
                "text_content": caption,
                "reserve_space": True,
            })

    @staticmethod
    def _apply_selected_cast_defaults(
        plans: List[Dict[str, Any]], selected_character_ids: Sequence[str], canonical_characters: Dict[str, Any]
    ) -> List[str]:
        """Keep older or incomplete panel plans from silently dropping the active cast."""
        if not selected_character_ids:
            return []
        inherited = []
        names = [
            str(getattr(canonical_characters.get(cid), "name", "") or cid)
            for cid in selected_character_ids
        ]
        for plan in plans:
            if plan.get("characterless") or plan.get("character_ids"):
                continue
            panel_id = str(plan.get("panel_id") or "")
            plan["character_ids"] = list(selected_character_ids)
            plan["character_selection_source"] = "creator_selected_default"
            cast_text = ", ".join(names)
            instruction = (
                f" Creator-selected cast for this panel: {cast_text}. Include these characters and preserve their canonical identities from the supplied references; do not substitute generic people or creatures."
            )
            brief = str(plan.get("image_brief") or "").strip()
            if instruction.strip() not in brief:
                plan["image_brief"] = (brief + instruction).strip()
            inherited.append(panel_id)
        return inherited

    def _prepare_story_object_drafts(self, job: StoryProductionJob, plan_by_id: Dict[str, Dict[str, Any]]) -> None:
        """Persist planner-declared recurring objects as project drafts before Canvas work."""
        from app.config import PROJECT_ROOT
        from app.project.bible import load_bible, save_bible, VersionConflictError
        from app.project.canon import PropAnalysisRecord, PropDefinition, PropIdentityFeature

        planned_objects = job.plan.get("recurring_objects") or []
        requested_ids = list(dict.fromkeys(
            str(prop_id).strip().lower()
            for plan in plan_by_id.values()
            for prop_id in (plan.get("prop_ids") or [])
            if str(prop_id).strip()
        ))
        planned_ids = {
            str((raw if isinstance(raw, dict) else raw.model_dump(mode="json")).get("prop_id") or "").strip().lower()
            for raw in planned_objects
        }
        for prop_id in sorted(planned_ids):
            use_count = sum(
                prop_id in {str(item).strip().lower() for item in (plan.get("prop_ids") or [])}
                for plan in plan_by_id.values()
            )
            if use_count < 2:
                raise ValueError(
                    f"Recurring object draft '{prop_id}' must be selected in at least two planned panels before production can save it."
                )
        if not requested_ids and not planned_objects:
            return
        if not self.project_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in self.project_id):
            raise ValueError("The active project ID is not a safe Story Bible path segment.")
        runs_root = (PROJECT_ROOT / "runs").resolve()
        bible_path = (runs_root / self.project_id / "bible.json").resolve()
        try:
            bible_path.relative_to(runs_root)
        except ValueError as exc:
            raise ValueError("The active project Story Bible resolves outside project storage.") from exc
        if not bible_path.is_file():
            raise ValueError("The active project Story Bible is missing; no object records were written.")
        bible = load_bible(bible_path)
        if bible.project_id != self.project_id:
            raise PermissionError("The active Story Bible belongs to a different project.")

        changed = False
        for raw in planned_objects:
            spec = dict(raw) if isinstance(raw, dict) else raw.model_dump(mode="json")
            prop_id = str(spec.get("prop_id") or "").strip().lower()
            name = str(spec.get("name") or "").strip()
            description = str(spec.get("description") or "").strip()
            if not prop_id or not name or not description:
                raise ValueError("A recurring object draft is missing its stable ID, name, or description.")
            existing = bible.props.get(prop_id)
            if existing:
                if existing.approval_status != "draft":
                    raise ValueError(f"Object '{prop_id}' already exists in Canon. The plan cannot overwrite or redefine it.")
                if existing.draft_job_id and existing.draft_job_id != job.job_id:
                    raise ValueError(f"Object ID '{prop_id}' is already reserved by another story draft; choose a different physical object ID.")
                if existing.draft_job_id != job.job_id and (
                    existing.name.casefold() != name.casefold()
                    or existing.description.strip() != description
                    or list(existing.stable_invariants) != list(spec.get("stable_invariants") or [])
                ):
                    raise ValueError(f"Draft object '{prop_id}' already has creator-edited details. The plan will not overwrite them.")
                continue

            stable_traits = list(dict.fromkeys(
                str(value).strip()
                for value in [*(spec.get("stable_invariants") or []), spec.get("form_and_proportions", "")]
                if str(value).strip()
            ))
            features = [
                PropIdentityFeature(
                    feature_id=f"{prop_id}_planned_{index}",
                    label="Planned identity trait",
                    description=trait,
                    stability="stable",
                    provenance="model_inference",
                    evidence_asset_ids=[],
                )
                for index, trait in enumerate(stable_traits, start=1)
            ]
            uncertain = list(spec.get("uncertain_traits") or [])
            uncertain.append("No object reference image has been analyzed yet; visual identity is text-drafted and unverified.")
            bible.props[prop_id] = PropDefinition(
                prop_id=prop_id,
                name=name,
                description=description,
                form_and_proportions=str(spec.get("form_and_proportions") or ""),
                materials=[str(item) for item in spec.get("materials", [])],
                palette=[str(item) for item in spec.get("palette", [])],
                components=[str(item) for item in spec.get("components", [])],
                distinctive_marks=[str(item) for item in spec.get("distinctive_marks", [])],
                required_attributes=list(spec.get("stable_invariants") or []),
                stable_invariants=list(spec.get("stable_invariants") or []),
                allowed_states=list(spec.get("allowed_states") or []),
                permitted_variations=list(spec.get("allowed_states") or []),
                uncertain_traits=uncertain,
                identity_features=features,
                trait_provenance={
                    key: "model_inference"
                    for key in ("description", "form_and_proportions", "materials", "palette", "components", "distinctive_marks", "stable_invariants", "allowed_states")
                },
                analysis=PropAnalysisRecord(
                    analysis_status="not_run",
                    analysis_source="agent_story_plan_text_only",
                    unknown_or_occluded=list(spec.get("uncertain_traits") or []) + ["No visual reference has been analyzed."],
                ),
                draft_origin="agent_story_plan",
                draft_job_id=job.job_id,
                approval_status="draft",
            )
            changed = True

        if changed:
            old_version = bible.bible_version
            bible.bible_version = old_version + 1
            try:
                save_bible(bible, target_path=bible_path, expected_version=old_version)
            except VersionConflictError as exc:
                raise RuntimeError(f"Story Bible changed while saving recurring object drafts: {exc}") from exc
            bible = load_bible(bible_path)

        missing = sorted(set(requested_ids) - set(bible.props))
        if missing:
            raise ValueError("The plan selected object IDs missing from the active project: " + ", ".join(missing))
        pinned_versions = dict(job.prop_versions)
        job.prop_versions = {}
        job.prop_snapshots = {}
        for prop_id in requested_ids:
            prop = bible.props[prop_id]
            current_version = int(prop.version or 1)
            pinned_version = pinned_versions.get(prop_id)
            if pinned_version is not None and int(pinned_version) != current_version:
                raise ValueError(f"Recurring object '{prop_id}' changed from version {pinned_version} during this job; refresh the plan before continuing.")
            job.prop_versions[prop_id] = int(pinned_version or current_version)
            job.prop_snapshots[prop_id] = {
                "prop_id": prop_id,
                "version": current_version,
                "name": prop.name,
                "description": prop.description,
                "stable_invariants": list(prop.stable_invariants or prop.required_attributes),
                "materials": list(prop.materials),
                "palette": list(prop.palette),
                "components": list(prop.components),
                "distinctive_marks": list(prop.distinctive_marks),
                "allowed_states": list(prop.allowed_states or prop.permitted_variations),
                "approval_status": prop.approval_status,
            }
        for panel_id, panel in job.panels.items():
            plan = plan_by_id.get(panel_id, {})
            prop_ids = list(dict.fromkeys(str(item).strip().lower() for item in (plan.get("prop_ids") or [])))
            prop_states = {str(key).strip().lower(): str(value).strip() for key, value in (plan.get("prop_states") or {}).items() if str(value).strip()}
            if set(prop_states) - set(prop_ids):
                raise ValueError(f"Panel {panel_id} has an object state for an object that is not selected in that panel.")
            if panel.asset_id and panel.prop_ids and panel.prop_ids != prop_ids:
                raise ValueError(f"Saved panel {panel_id} has a different object cast than the approved plan.")
            panel.prop_ids = prop_ids
            panel.prop_states = prop_states
            panel.prop_versions = {prop_id: job.prop_versions[prop_id] for prop_id in prop_ids}
            if not panel.asset_id:
                panel.prop_reference_asset_ids_by_prop = {
                    prop_id: [ref.asset_id for ref in (bible.props[prop_id].reference_assets or [])]
                    for prop_id in prop_ids
                }
                panel.prop_reference_asset_ids = list(dict.fromkeys(
                    asset_id for values in panel.prop_reference_asset_ids_by_prop.values() for asset_id in values
                ))
            panel.provenance.update({"prop_ids": list(prop_ids), "prop_versions": dict(panel.prop_versions), "prop_states": dict(prop_states)})
        job.plan["prop_versions"] = dict(job.prop_versions)

    def _refresh_panel_prop_references(self, panel: PanelProduction) -> List[str]:
        """Reload exact current refs before a panel call, including a prior panel's new anchor."""
        if not panel.prop_ids:
            return []
        from app.config import PROJECT_ROOT
        from app.project.bible import load_bible
        bible = load_bible(PROJECT_ROOT / "runs" / self.project_id / "bible.json")
        by_prop: Dict[str, List[str]] = {}
        for prop_id in panel.prop_ids:
            prop = bible.props.get(prop_id)
            if prop is None:
                raise ValueError(f"Recurring object '{prop_id}' disappeared from the active project Story Bible.")
            expected_version = panel.prop_versions.get(prop_id)
            if expected_version is not None and int(prop.version or 1) != int(expected_version):
                raise ValueError(f"Recurring object '{prop_id}' changed from version {expected_version} during this job; refresh the plan before continuing.")
            by_prop[prop_id] = [ref.asset_id for ref in (prop.reference_assets or [])]
        panel.prop_reference_asset_ids_by_prop = by_prop
        panel.prop_reference_asset_ids = list(dict.fromkeys(asset_id for ids in by_prop.values() for asset_id in ids))
        return panel.prop_reference_asset_ids

    @staticmethod
    def _prior_generated_unanchored_object(job: StoryProductionJob, panel_id: str, prop_id: str) -> Optional[PanelProduction]:
        """Find an earlier generated occurrence whose provisional object anchor was not saved."""
        ordered_ids = list(job.panels)
        try:
            current_index = ordered_ids.index(panel_id)
        except ValueError:
            return None
        for earlier_id in ordered_ids[:current_index]:
            earlier = job.panels[earlier_id]
            if (
                prop_id in earlier.prop_ids
                and earlier.asset_id
                and not (earlier.prop_reference_asset_ids_by_prop or {}).get(prop_id)
            ):
                return earlier
        return None

    def _persist_object_anchor(self, prop_id: str, asset_id: str, job_id: str) -> None:
        """Attach a real registered generation as provisional visual evidence without changing identity traits."""
        from app.config import PROJECT_ROOT
        from app.api.routers.assets import get_registry
        from app.project.asset_refs import AssetRef
        from app.project.bible import load_bible, save_bible, VersionConflictError

        resolved = get_registry().resolve_asset(asset_id, verify_integrity=True)
        if resolved.metadata.project_id != self.project_id:
            raise PermissionError(f"Generated object anchor '{asset_id}' belongs to another project.")
        if resolved.metadata.validation_state != "valid" or resolved.metadata.extra_metadata.get("is_simulated") is True:
            raise ValueError("A simulated or invalid image cannot become an object reference anchor.")
        if resolved.metadata.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise ValueError("The generated object anchor has an unsupported image MIME type.")
        try:
            relative_path = str(resolved.absolute_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
        except ValueError as exc:
            raise ValueError("The generated object anchor is outside project storage.") from exc
        bible_path = PROJECT_ROOT / "runs" / self.project_id / "bible.json"
        bible = load_bible(bible_path)
        prop = bible.props.get(prop_id)
        if prop is None:
            raise ValueError(f"Object draft '{prop_id}' disappeared before its visual anchor could be saved.")
        if prop.approval_status != "draft":
            raise ValueError(f"Approved object '{prop_id}' has no reference; Canon cannot be silently changed to add an anchor.")
        if any(ref.asset_id == asset_id for ref in prop.reference_assets):
            return
        if prop.reference_assets:
            return
        old_version = bible.bible_version
        prop.reference_assets.append(AssetRef(
            asset_id=asset_id,
            path=relative_path,
            asset_type="prop_ref",
            expected_hash=resolved.metadata.content_sha256,
            mime_type=resolved.metadata.mime_type,
            file_size_bytes=resolved.metadata.byte_size,
            provenance={"source": "story_production_first_visual_anchor", "job_id": job_id},
        ))
        prop.analysis.unknown_or_occluded = list(dict.fromkeys([
            *prop.analysis.unknown_or_occluded,
            "A generated provisional reference is attached; visual identity consistency has not been independently verified.",
        ]))
        old_version = bible.bible_version
        bible.bible_version = old_version + 1
        try:
            save_bible(bible, target_path=bible_path, expected_version=old_version)
        except VersionConflictError as exc:
            raise RuntimeError(f"Story Bible changed while saving generated object anchor: {exc}") from exc

    def _load_prior_panel_results(self, job, plan_by_id, prior_results, prior_calls) -> None:
        calls_by_id = {_value(call, "call_id"): call for call in prior_calls}
        for result in prior_results:
            if _value(result, "tool_id") != "generation.generate_image":
                continue
            output = _value(result, "output", {}) or {}
            call = calls_by_id.get(_value(result, "call_id"))
            arguments = _value(call, "arguments", {}) or {}
            panel_id = output.get("panel_id") or arguments.get("panel_id")
            if panel_id not in job.panels:
                continue
            panel = job.panels[panel_id]
            call_id = _value(result, "call_id")
            if call_id and call_id in panel.processed_generation_call_ids:
                continue
            if call_id:
                panel.processed_generation_call_ids.append(call_id)
            panel.generation_attempts = max(panel.generation_attempts, 0) + 1
            if _value(result, "status") != "success" or not output.get("asset_id"):
                panel.error = _value(result, "error") or "Previous image generation did not return a registered asset."
                panel.provenance["previous_failure_code"] = _value(result, "error_code")
                continue
            if self._asset_matches_panel(output, panel, allow_selected_cast_superset=True):
                panel.asset_id = output["asset_id"]
                panel.asset_sha256 = output.get("content_sha256")
                panel.provenance = {
                    "character_ids": output.get("character_ids"),
                    "character_versions": output.get("character_versions"),
                    "style_profile_id": output.get("style_profile_id"),
                    "style_profile_version": output.get("style_profile_version"),
                    "prop_ids": output.get("prop_ids"),
                    "prop_versions": output.get("prop_versions"),
                    "prop_states": output.get("prop_states"),
                    "prop_reference_asset_ids": output.get("prop_reference_asset_ids"),
                    "object_anchor_ids": output.get("object_anchor_ids"),
                    "object_visual_verification_status": output.get("object_visual_verification_status", "NOT_RUN"),
                    "reference_asset_ids": output.get("reference_asset_ids"),
                    "context_fingerprint": output.get("context_fingerprint"),
                    "asset_verified": True,
                }
                extra_selected_ids = sorted(set(output.get("character_ids") or []) - set(panel.character_ids))
                if extra_selected_ids:
                    panel.provenance.update({
                        "planned_character_ids": list(panel.character_ids),
                        "additional_selected_character_context": extra_selected_ids,
                        "cast_scope_note": (
                            "Prior artwork was generated with additional creator-selected character references. "
                            "Canvas verification checks asset placement and links, not visual character identity."
                        ),
                    })
                panel.status = "generated"
                for prop_id in output.get("object_anchor_ids") or []:
                    try:
                        self._persist_object_anchor(prop_id, output["asset_id"], job.job_id)
                    except Exception as exc:
                        panel.provenance.setdefault("object_anchor_errors", []).append(str(exc))
                        job.errors.append(f"Panel {panel_id} artwork exists, but its object anchor could not be saved: {exc}")
            else:
                panel.error = "Previous successful image has missing or incompatible cast/style/reference provenance; it will not be reused."
                panel.provenance["rejected_asset_id"] = output.get("asset_id")

    def _recover_checkpointed_generation_results(self, job: StoryProductionJob) -> None:
        """Recover a provider result saved before a process interruption."""
        for panel in job.panels.values():
            if panel.status != "generating":
                continue
            saved = panel.provenance.get("checkpointed_generation_result")
            if not saved:
                continue
            try:
                result = ToolResult.model_validate(saved)
            except Exception:
                continue
            output = result.output or {}
            if result.status == "success" and output.get("asset_id") and self._asset_matches_panel(output, panel):
                panel.asset_id = output["asset_id"]
                panel.asset_sha256 = output.get("content_sha256")
                panel.provenance.update({
                    "character_ids": output.get("character_ids"),
                    "character_versions": output.get("character_versions"),
                    "style_profile_id": output.get("style_profile_id"),
                    "style_profile_version": output.get("style_profile_version"),
                    "prop_ids": output.get("prop_ids"),
                    "prop_versions": output.get("prop_versions"),
                    "prop_states": output.get("prop_states"),
                    "prop_reference_asset_ids": output.get("prop_reference_asset_ids"),
                    "object_anchor_ids": output.get("object_anchor_ids"),
                    "object_visual_verification_status": output.get("object_visual_verification_status", "NOT_RUN"),
                    "character_reference_asset_ids": output.get("character_reference_asset_ids"),
                    "reference_asset_ids": output.get("reference_asset_ids"),
                    "context_fingerprint": output.get("context_fingerprint"),
                    "is_simulated": output.get("is_simulated", False),
                    "asset_verified": True,
                })
                panel.status = "generated"
                panel.error = None
                for prop_id in output.get("object_anchor_ids") or []:
                    try:
                        self._persist_object_anchor(prop_id, output["asset_id"], job.job_id)
                    except Exception as exc:
                        panel.provenance.setdefault("object_anchor_errors", []).append(str(exc))
                        job.errors.append(f"Recovered panel {panel.panel_id} artwork exists, but its object anchor could not be saved: {exc}")
            elif _transient_provider_error(result) and panel.automatic_retries == 0:
                # The failed attempt is checkpointed, so the coordinator may
                # now make exactly its one retry without risking a duplicate
                # request for an unknown in-flight operation.
                panel.automatic_retries = 1
                panel.status = "pending"
                panel.error = result.error
            else:
                panel.status = "needs_attention"
                panel.error = result.error or "The checkpointed generation result did not contain a compatible registered asset."
            self._checkpoint(job, f"panel_{panel.panel_id}_generation_result_recovered")

    def _asset_matches_panel(
        self,
        output: Dict[str, Any],
        panel: PanelProduction,
        *,
        allow_selected_cast_superset: bool = False,
    ) -> bool:
        if output.get("panel_id") != panel.panel_id or not output.get("asset_id"):
            return False
        actual_character_ids = list(output.get("character_ids") or [])
        exact_cast = actual_character_ids == panel.character_ids
        selected_cast_superset = (
            allow_selected_cast_superset
            and set(panel.character_ids).issubset(set(actual_character_ids))
            and set(actual_character_ids).issubset(set(self.selected_character_ids))
        )
        if not (exact_cast or selected_cast_superset):
            return False
        actual_versions = output.get("character_versions") or {}
        expected_actual_versions = {
            cid: int(getattr(self.canonical_characters[cid], "canon_version", getattr(self.canonical_characters[cid], "version", 1)) or 1)
            for cid in actual_character_ids if cid in self.canonical_characters
        }
        if set(expected_actual_versions) != set(actual_character_ids):
            return False
        if any(actual_versions.get(cid) != version for cid, version in expected_actual_versions.items()):
            return False
        if panel.character_versions and any(actual_versions.get(cid) != version for cid, version in panel.character_versions.items()):
            return False
        actual_prop_ids = list(output.get("prop_ids") or [])
        if actual_prop_ids != panel.prop_ids:
            return False
        actual_prop_versions = output.get("prop_versions") or {}
        if any(actual_prop_versions.get(prop_id) != version for prop_id, version in panel.prop_versions.items()):
            return False
        if panel.prop_ids:
            actual_states = output.get("prop_states") or {}
            if {key: str(value) for key, value in actual_states.items()} != panel.prop_states:
                return False
            anchor_ids = set(output.get("object_anchor_ids") or [])
            object_roles: Dict[str, List[str]] = {}
            for role in output.get("reference_image_roles") or []:
                if role.get("role") == "object_reference" and role.get("prop_id"):
                    object_roles.setdefault(str(role["prop_id"]), []).append(str(role.get("asset_id") or ""))
            for prop_id in panel.prop_ids:
                expected_object_refs = list((panel.prop_reference_asset_ids_by_prop or {}).get(prop_id, []))
                actual_object_refs = object_roles.get(prop_id, [])
                if prop_id in anchor_ids:
                    expected_object_refs = []
                if set(actual_object_refs) != set(expected_object_refs) or len(actual_object_refs) != len(expected_object_refs):
                    return False
            expected_all_object_refs = [
                asset_id for prop_id, refs in (panel.prop_reference_asset_ids_by_prop or {}).items()
                for asset_id in ([] if prop_id in anchor_ids else refs)
            ]
            if set(output.get("prop_reference_asset_ids") or []) != set(expected_all_object_refs):
                return False
        if output.get("style_profile_id") != panel.style_profile_id or output.get("style_profile_version") != panel.style_profile_version:
            return False
        expected_refs = self._expected_character_reference_ids(
            actual_character_ids if selected_cast_superset else panel.character_ids
        )
        actual_refs = list(output.get("character_reference_asset_ids") or [])
        # The generation boundary selects one verified, non-simulated reference
        # per character. A Story Bible can contain old duplicate aliases; require
        # each returned reference to be an allowed Bible reference, not every
        # historical alias to be sent to the provider.
        roles = output.get("reference_image_roles") or []
        character_roles = {
            item.get("character_id")
            for item in roles
            if item.get("role") == "character_reference" and item.get("character_id")
        }
        if expected_refs:
            if not actual_refs or not set(actual_refs).issubset(set(expected_refs)):
                return False
            if not roles or character_roles != set(actual_character_ids):
                return False
            if len(actual_refs) != len(actual_character_ids):
                return False
        expected_style_refs = list((self.selected_style_profile or {}).get("reference_asset_ids") or [])
        actual_style_refs = list(output.get("style_reference_asset_ids") or [])
        if expected_style_refs and set(expected_style_refs) != set(actual_style_refs):
            return False
        expected_location = panel.provenance.get("location_id")
        if expected_location and (output.get("location_id") != expected_location or output.get("location_version") != panel.provenance.get("location_version")):
            return False
        if output.get("is_simulated") is True:
            return False
        try:
            from app.api.routers.assets import get_registry
            resolved = get_registry().resolve_asset(output["asset_id"], verify_integrity=True)
            return resolved.metadata.project_id == self.project_id
        except Exception:
            return False

    @staticmethod
    def _recover_profile_snapshot(
        prior_results: Sequence[Any], id_key: str, version_key: str, snapshot_id_key: str
    ) -> Optional[Dict[str, Any]]:
        snapshots = {
            (_value(_value(result, "output", {}) or {}, id_key), _value(_value(result, "output", {}) or {}, version_key))
            for result in prior_results
            if _value(result, "tool_id") == "generation.generate_image"
            and _value(result, "status") == "success"
            and _value(_value(result, "output", {}) or {}, id_key)
        }
        if len(snapshots) != 1:
            return None
        profile_id, version = next(iter(snapshots))
        return {snapshot_id_key: profile_id, "version": version} if profile_id and version is not None else None

    def _restore_job_context(self, job: Any) -> None:
        """Restore the saved creative selections for a resumed durable job."""
        if self.selected_style_profile is None:
            self.selected_style_profile = job.style_snapshot
        if self.selected_location is None:
            self.selected_location = job.location_snapshot
        if not self.selected_character_ids:
            self.selected_character_ids = list(job.selected_character_ids)

    @staticmethod
    def _recover_selected_cast(prior_results: Sequence[Any], prior_calls: Sequence[Any]) -> List[str]:
        calls_by_id = {_value(call, "call_id"): call for call in prior_calls}
        selected: List[str] = []
        for result in prior_results:
            if _value(result, "tool_id") != "generation.generate_image" or _value(result, "status") != "success":
                continue
            call = calls_by_id.get(_value(result, "call_id"))
            arguments = _value(call, "arguments", {}) or {}
            for character_id in arguments.get("character_ids", []) or []:
                if character_id not in selected:
                    selected.append(character_id)
        return selected

    def _expected_character_reference_ids(self, character_ids: Sequence[str]) -> List[str]:
        refs = []
        for character_id in character_ids:
            character = self.canonical_characters.get(character_id)
            for ref in getattr(character, "reference_assets", []) if character else []:
                asset_id = getattr(ref, "asset_id", None)
                if asset_id:
                    refs.append(asset_id)
        return list(dict.fromkeys(refs))

    def _dispatch(self, call: ToolCall, context: Optional[Dict[str, Any]] = None) -> ToolResult:
        self.calls.append(call)
        if self.activity_callback:
            self.activity_callback({"call_id": call.call_id, "tool_id": call.tool_id, "status": "running"})
        result = self.registry.dispatch(call, {**self.dispatch_context, **(context or {})})
        self.results.append(result)
        if self.activity_callback:
            self.activity_callback({"call_id": call.call_id, "tool_id": call.tool_id, "status": result.status,
                                    "duration_seconds": result.duration_seconds, "error": result.error})
        return result

    def _ensure_pages(self, job: StoryProductionJob, groups: Sequence[Sequence[Dict[str, Any]]]) -> None:
        job.status = "assembling"
        self._checkpoint(job, "canvas_page_creation_started")
        for page, plans in zip(job.pages, groups):
            existing = self._page_document(page.page_id)
            if existing is not None:
                if existing.project_id != self.project_id:
                    page.status = "failed"
                    job.errors.append(f"Page ID {page.page_id} exists in another project; no mutation was made.")
                    continue
                page.revision = existing.revision
                page.status = "created"
                self._inspect_page_spacing(job, page)
                self._checkpoint(job, f"page_{page.page_number}_reused")
                continue
            panel_ids = list(page.panel_ids)
            count = len(panel_ids)
            page_local_plans = []
            for index, source_plan in enumerate(plans, start=1):
                page_plan = dict(source_plan)
                # The story keeps global order in its persisted plan, while
                # each Canvas document's reading order is local to that page.
                page_plan["reading_order_index"] = index
                page_plan["page_number"] = page.page_number
                page_local_plans.append(page_plan)
            use_custom_canvas = "canvas.create_custom_page" in self._available_tool_ids()
            if use_custom_canvas:
                tool_id = "canvas.create_custom_page"
                page_arguments = {
                    "project_id": self.project_id,
                    "page_id": page.page_id,
                    "reading_direction": job.plan.get("reading_direction", "ltr"),
                    "panel_geometry": _scratch_geometry_from_plans(page_local_plans, job.plan.get("reading_direction", "ltr")),
                    "panel_plans": page_local_plans,
                }
            else:
                template, params, custom_requested = _fallback_layout_template(page_local_plans, self.request_texts)
                if custom_requested:
                    page.status = "needs_attention"
                    message = "This request needs custom scratched panel geometry, but the registered Canvas custom-page tool is unavailable. No grid substitute was created."
                    job.errors.append(message)
                    for panel_id in panel_ids:
                        job.panels[panel_id].status = "needs_attention"
                        job.panels[panel_id].error = message
                    self._checkpoint(job, f"page_{page.page_number}_custom_geometry_unavailable")
                    continue
                tool_id = "canvas.create_page_from_template"
                page_arguments = {
                    "project_id": self.project_id,
                    "page_id": page.page_id,
                    "layout_template": template,
                    "template_parameters": params,
                    "reading_direction": job.plan.get("reading_direction", "ltr"),
                    "panel_plans": page_local_plans,
                }
            call = ToolCall(
                call_id=f"{job.job_id}_page_{page.page_number}_create",
                tool_id=tool_id,
                arguments=page_arguments,
            )
            self._checkpoint(job, f"page_{page.page_number}_creation_started")
            result = self._dispatch(call)
            output = result.output or {}
            if result.status == "success" and output.get("page_id") == page.page_id and set(output.get("panel_ids", [])) == set(panel_ids):
                page.revision = output.get("revision")
                page.status = "created"
                self._inspect_page_spacing(job, page)
            else:
                page.status = "failed"
                page.error = result.error or "The Canvas tool did not return the expected persisted page and panel IDs."
                job.errors.append(f"Page {page.page_number} creation failed: {page.error}")
            self._checkpoint(job, f"page_{page.page_number}_{page.status}")

    def _inspect_page_spacing(self, job: StoryProductionJob, page: PageProduction) -> None:
        """Run geometry QA against the persisted page before generating artwork."""
        call = ToolCall(
            call_id=f"{job.job_id}_page_{page.page_number}_spacing",
            tool_id="canvas.inspect_page_spacing",
            arguments={"page_id": page.page_id},
        )
        result = self._dispatch(call)
        output = result.output or {}
        page.verification["spacing"] = output
        problems: List[str] = []
        if result.status != "success" or output.get("page_id") != page.page_id:
            problems.append(result.error or "The spacing inspector did not verify the persisted page.")
        else:
            measured_panels = output.get("panels") or []
            if {item.get("panel_id") for item in measured_panels} != set(page.panel_ids):
                problems.append("The spacing inspector did not return measurements for every page panel.")
            if any("measured_margins_px" not in item or "margin_clearance_valid" not in item for item in measured_panels):
                problems.append("The spacing inspector did not return measured page-margin clearances.")
            if output.get("overlapping_panel_pairs"):
                problems.append("Panel boundaries overlap: " + ", ".join("/".join(pair) for pair in output["overlapping_panel_pairs"]))
            minimum_gap = output.get("minimum_edge_gap_px")
            if len(page.panel_ids) > 1 and minimum_gap is None:
                problems.append("The spacing inspector did not return a measured gutter for this multi-panel page.")
            if minimum_gap is not None and float(minimum_gap) < 10.0:
                problems.append(f"The smallest panel gutter is {float(minimum_gap):.1f}px; at least 10px is required.")
            if output.get("margin_clearance_valid") is False:
                problems.append("One or more panel edges cross the configured page margin without an intentional full-bleed declaration.")
            if minimum_gap is not None and float(minimum_gap) > 24.0:
                note = f"Page {page.page_number} has a measured {float(minimum_gap):.1f}px minimum gutter, wider than the 10–24px target; the saved layout was retained for review."
                if note not in job.assumptions:
                    job.assumptions.append(note)
            if any(item.get("margin_clearance_valid") is False for item in measured_panels):
                problems.append("At least one measured panel margin is below its configured page-safe inset.")
        page.verification["spacing_valid"] = not problems
        page.verification["spacing_errors"] = problems
        if problems:
            page.status = "needs_attention"
            message = f"Page {page.page_number} spacing check needs attention: " + " ".join(problems)
            if message not in job.errors:
                job.errors.append(message)
            for panel_id in page.panel_ids:
                panel = job.panels[panel_id]
                if not panel.asset_id:
                    panel.status = "needs_attention"
                    panel.error = "Page spacing must be corrected before generating this panel's artwork."

    def _generate_missing(self, job, plan_by_id, prior_results, prior_calls, unit_cost: float) -> None:
        job.status = "generating"
        self._checkpoint(job, "generation_started")
        call_args = {_value(call, "call_id"): _value(call, "arguments", {}) or {} for call in prior_calls}
        prior_failed: Dict[str, List[Any]] = {}
        for result in prior_results:
            if _value(result, "tool_id") != "generation.generate_image" or _value(result, "status") == "success":
                continue
            args = call_args.get(_value(result, "call_id"), {})
            panel_id = ((_value(result, "output", {}) or {}).get("panel_id") or args.get("panel_id"))
            if panel_id in job.panels:
                prior_failed.setdefault(panel_id, []).append(result)

        spent_estimate = 0.0
        latest_request = self.request_texts[-1].casefold() if self.request_texts else ""
        explicit_retry = bool(re.search(r"\bretry\b", latest_request))
        retry_target_match = re.search(r"\bretry\s+(?:panel\s+)?([a-z0-9][a-z0-9_-]*)", latest_request) if explicit_retry else None
        retry_target = retry_target_match.group(1).strip(" .,:;!?`") if retry_target_match else None
        for panel_id, panel in job.panels.items():
            if panel.asset_id:
                continue
            panel_page = next((item for item in job.pages if item.page_number == panel.page_number), None)
            if panel_page and getattr(panel_page, "verification", {}).get("spacing_valid") is False:
                panel.status = "needs_attention"
                panel.error = "Generation is paused until the persisted page passes spacing validation."
                continue
            # An interrupted in-flight provider request has uncertain billing;
            # do not silently spend again after a process restart.
            if panel.status == "generating":
                panel.status = "needs_attention"
                panel.error = "Previous generation stopped before a result was checkpointed; inspect provider/run history before retrying."
                job.errors.append(f"Panel {panel_id} has an uncertain generation attempt.")
                self._checkpoint(job, f"panel_{panel_id}_generation_uncertain")
                continue
            if panel.status == "needs_attention":
                targeted = bool(retry_target and retry_target.casefold() == panel_id.casefold())
                if retry_target and not targeted:
                    target_digits = re.sub(r"\D", "", retry_target)
                    panel_digits = re.sub(r"\D", "", panel_id.casefold())
                    targeted = bool(target_digits and target_digits == panel_digits)
                failed_panel_count = sum(item.status in ("failed", "needs_attention") for item in job.panels.values())
                if not explicit_retry or (retry_target and not targeted) or (not retry_target and failed_panel_count != 1):
                    continue
                panel.manual_retries += 1
                panel.status = "pending"
                panel.error = None
            failed_history = prior_failed.get(panel_id, [])
            failed_history_transient = bool(failed_history and _transient_provider_error(failed_history[-1]))
            if failed_history and not failed_history_transient:
                panel.status = "needs_attention"
                panel.error = panel.error or str(_value(failed_history[-1], "error", "Previous generation failed."))
                job.errors.append(f"Panel {panel_id} had a non-transient provider/tool failure and was not retried.")
                continue
            plan = plan_by_id[panel_id]
            planned_ids = list(panel.character_ids)
            unselected = set(planned_ids) - set(job.selected_character_ids)
            if unselected:
                panel.status = "needs_attention"
                panel.error = "The approved panel cast contains characters outside the current selected/reference allow-list: " + ", ".join(sorted(unselected))
                job.errors.append(f"Panel {panel_id} character scope needs attention.")
                continue
            for cid in planned_ids:
                if cid not in self.canonical_characters:
                    panel.status = "needs_attention"
                    panel.error = f"Canonical character '{cid}' is not present in the active project."
                    job.errors.append(f"Panel {panel_id} references missing character {cid}.")
                    break
            if panel.status == "needs_attention":
                continue
            if spent_estimate + unit_cost > self.effective_budget_usd:
                panel.status = "needs_attention"
                panel.error = "The remaining run budget is below the configured image estimate."
                job.errors.append(f"Generation stopped at panel {panel_id} because of the run budget.")
                continue

            page = next((item for item in job.pages if item.page_number == panel.page_number), None)
            page_doc = self._page_document(page.page_id) if page else None
            slot = page_doc.layout.get_panel(panel_id) if page_doc else None
            context = {"selected_character_ids": planned_ids}
            try:
                self._refresh_panel_prop_references(panel)
            except Exception as exc:
                panel.status = "needs_attention"
                panel.error = f"Object reference preflight failed: {exc}"
                job.errors.append(f"Panel {panel_id} object reference needs attention: {panel.error}")
                self._checkpoint(job, f"panel_{panel_id}_object_reference_preflight_failed")
                continue
            object_anchor_ids = []
            for prop_id in panel.prop_ids:
                if (panel.prop_reference_asset_ids_by_prop or {}).get(prop_id):
                    continue
                prior_unanchored = self._prior_generated_unanchored_object(job, panel_id, prop_id)
                if prior_unanchored:
                    anchor_error = next(iter(prior_unanchored.provenance.get("object_anchor_errors") or []), None)
                    panel.status = "needs_attention"
                    panel.error = (
                        f"Object '{prop_id}' appeared in an earlier generated panel, but its visual reference was not saved. "
                        "This panel was not generated without the required object reference."
                    )
                    if anchor_error:
                        panel.error += f" Anchor error: {anchor_error}"
                    job.errors.append(f"Panel {panel_id} object continuity needs attention: {panel.error}")
                    self._checkpoint(job, f"panel_{panel_id}_prior_object_anchor_missing")
                    break
                first_pending_panel = next((
                    candidate for candidate in job.panels.values()
                    if prop_id in candidate.prop_ids and not candidate.asset_id
                ), None)
                snapshot = job.prop_snapshots.get(prop_id) or {}
                if first_pending_panel and first_pending_panel.panel_id == panel_id and snapshot.get("approval_status") == "draft":
                    object_anchor_ids.append(prop_id)
            if panel.status == "needs_attention":
                continue
            if len(object_anchor_ids) > 1:
                panel.status = "needs_attention"
                panel.error = "This panel is the first appearance of multiple unreferenced objects. Separate their first appearances or attach reference pictures so each object gets its own verified reference."
                job.errors.append(f"Panel {panel_id} cannot safely establish more than one new object identity from a single image.")
                self._checkpoint(job, f"panel_{panel_id}_multiple_object_anchors_blocked")
                continue
            if panel.prop_ids:
                context["selected_prop_ids"] = list(panel.prop_ids)
                context["prop_states"] = dict(panel.prop_states)
            if self.selected_style_profile:
                context["selected_style_profile"] = self.selected_style_profile
            if self.selected_location:
                context["selected_location"] = self.selected_location
            arguments = {
                "prompt": plan.get("image_brief") or plan.get("story_event", ""),
                "panel_id": panel_id,
                "scene_id": plan.get("scene_id"),
                "character_ids": planned_ids,
                "prop_ids": list(panel.prop_ids),
                "prop_versions": dict(panel.prop_versions),
                "prop_states": dict(panel.prop_states),
                "panel_plan": plan,
            }
            if object_anchor_ids:
                arguments["object_anchor_ids"] = object_anchor_ids
            if slot:
                arguments["width"] = max(1, round(slot.rect.width))
                arguments["height"] = max(1, round(slot.rect.height))
            if panel.style_profile_id:
                arguments["style_profile_id"] = panel.style_profile_id
                arguments["style_profile_version"] = panel.style_profile_version
            if panel.provenance.get("location_id"):
                arguments["location_id"] = panel.provenance["location_id"]
                arguments["location_version"] = panel.provenance.get("location_version")

            # A known prior transient failure consumes this panel's one
            # automatic retry. New failures may receive exactly one retry.
            retry_already_used = panel.automatic_retries >= 1 or bool(failed_history_transient and not explicit_retry)
            # A transient failure already recorded in the chat is the first
            # failed attempt. The next call is its single allowed retry.
            if failed_history_transient and not explicit_retry and panel.automatic_retries == 0:
                panel.automatic_retries = 1
            attempt_count = 0
            max_attempts = 1 if retry_already_used else 2
            while attempt_count < max_attempts:
                attempt_count += 1
                panel.generation_attempts += 1
                panel.status = "generating"
                panel.error = None
                self._checkpoint(job, f"panel_{panel_id}_generation_attempt_{panel.generation_attempts}")
                call = ToolCall(
                    call_id=f"{job.job_id}_gen_{panel_id}_attempt_{panel.generation_attempts}",
                    tool_id="generation.generate_image",
                    arguments=arguments,
                )
                panel.processed_generation_call_ids.append(call.call_id)
                result = self._dispatch(call, context)
                panel.provenance["checkpointed_generation_result"] = result.model_dump(mode="json")
                self._checkpoint(job, f"panel_{panel_id}_generation_result_received")
                output = result.output or {}
                spent_estimate += unit_cost
                if result.status == "success" and output.get("asset_id") and self._asset_matches_panel(output, panel):
                    panel.asset_id = output["asset_id"]
                    panel.asset_sha256 = output.get("content_sha256")
                    panel.provenance = {
                        "character_ids": output.get("character_ids"),
                        "character_versions": output.get("character_versions"),
                        "style_profile_id": output.get("style_profile_id"),
                        "style_profile_version": output.get("style_profile_version"),
                        "character_reference_asset_ids": output.get("character_reference_asset_ids"),
                        "reference_asset_ids": output.get("reference_asset_ids"),
                        "prop_ids": output.get("prop_ids"),
                        "prop_versions": output.get("prop_versions"),
                        "prop_states": output.get("prop_states"),
                        "prop_reference_asset_ids": output.get("prop_reference_asset_ids"),
                        "object_anchor_ids": output.get("object_anchor_ids"),
                        "object_visual_verification_status": output.get("object_visual_verification_status", "NOT_RUN"),
                        "context_fingerprint": output.get("context_fingerprint"),
                        "is_simulated": output.get("is_simulated", False),
                        "asset_verified": True,
                    }
                    panel.status = "generated"
                    panel.error = None
                    for prop_id in output.get("object_anchor_ids") or []:
                        try:
                            self._persist_object_anchor(prop_id, output["asset_id"], job.job_id)
                        except Exception as exc:
                            anchor_error = f"Generated panel artwork is saved, but object '{prop_id}' anchor persistence failed: {exc}"
                            if anchor_error not in job.errors:
                                job.errors.append(anchor_error)
                            panel.provenance.setdefault("object_anchor_errors", []).append(anchor_error)
                    self._checkpoint(job, f"panel_{panel_id}_generated")
                    break
                error = result.error or "Generation did not return a compatible registered image asset."
                if result.status == "success" and output.get("asset_id"):
                    error = "Generated asset provenance does not match the planned panel cast/style/reference versions; it was not placed."
                panel.error = error
                if not retry_already_used and _transient_provider_error(result):
                    panel_order = list(job.panels)
                    current_index = panel_order.index(panel_id)
                    future_base_estimate = sum(
                        unit_cost for future_id in panel_order[current_index + 1:]
                        if not job.panels[future_id].asset_id
                    )
                    if spent_estimate + unit_cost + future_base_estimate > self.effective_budget_usd:
                        panel.status = "needs_attention"
                        panel.error = f"A transient error occurred, but the budget does not cover one retry plus the remaining planned panels (estimate ${spent_estimate + unit_cost + future_base_estimate:.4f})."
                        job.errors.append(f"Panel {panel_id} automatic retry was skipped by the remaining budget.")
                        self._checkpoint(job, f"panel_{panel_id}_retry_budget_blocked")
                        break
                    retry_already_used = True
                    panel.automatic_retries += 1
                    panel.status = "pending"
                    self._checkpoint(job, f"panel_{panel_id}_transient_retry_scheduled")
                    continue
                panel.status = "needs_attention"
                job.errors.append(f"Panel {panel_id} generation needs attention: {error}")
                self._checkpoint(job, f"panel_{panel_id}_generation_failed")
                break

    def _place_assets(self, job, plan_by_id) -> None:
        job.status = "assembling"
        self._checkpoint(job, "artwork_placement_started")
        for panel_id, panel in job.panels.items():
            if not panel.asset_id:
                continue
            page = next((item for item in job.pages if item.page_number == panel.page_number), None)
            if not page or page.status == "failed":
                panel.status = "needs_attention"
                panel.error = "The Canvas page for this panel was not created."
                continue
            if getattr(page, "verification", {}).get("spacing_valid") is False:
                panel.status = "needs_attention"
                panel.error = "Canvas placement is paused until the page spacing issue is resolved."
                continue
            doc = self._page_document(page.page_id)
            if doc is None:
                panel.status = "needs_attention"
                panel.error = "The persisted Canvas page could not be reopened."
                continue
            from app.editor.models import LayerKind
            current = next((layer for layer in doc.layers if layer.panel_id == panel_id and layer.kind == LayerKind.IMAGE), None)
            if current and current.source_asset_id == panel.asset_id:
                panel.image_layer_id = current.layer_id
                panel.replacement_expected_asset_id = None
                panel.status = "placed"
                continue
            replacing_expected_asset = bool(
                current
                and panel.replacement_expected_asset_id
                and current.layer_id == panel.image_layer_id
                and current.source_asset_id == panel.replacement_expected_asset_id
            )
            if current and not replacing_expected_asset:
                panel.status = "needs_attention"
                panel.error = "This panel already contains different artwork; it was preserved and not overwritten."
                job.errors.append(f"Panel {panel_id} already had user artwork; the workflow did not replace it.")
                continue
            call = ToolCall(
                call_id=f"{job.job_id}_place_{panel_id}",
                tool_id="canvas.place_panel_artwork",
                arguments={"page_id": page.page_id, "expected_revision": doc.revision,
                           "panel_id": panel_id, "asset_id": panel.asset_id, "fit_mode": "contain",
                           "replace_existing": replacing_expected_asset},
            )
            self._checkpoint(job, f"panel_{panel_id}_placement_started")
            result = self._dispatch(call)
            if result.status == "success" and (result.output or {}).get("page_id") == page.page_id:
                panel.image_layer_id = (result.output or {}).get("layer_id")
                if replacing_expected_asset:
                    panel.provenance["replaced_asset_id"] = panel.replacement_expected_asset_id
                    panel.replacement_expected_asset_id = None
                panel.status = "placed"
                page.revision = (result.output or {}).get("revision", doc.revision)
                page.status = "assembled"
            else:
                panel.status = "needs_attention"
                panel.error = result.error or "Canvas did not confirm artwork placement."
                job.errors.append(f"Panel {panel_id} placement failed: {panel.error}")
            self._checkpoint(job, f"panel_{panel_id}_{panel.status}")

    def _place_text(self, job, plan_by_id) -> None:
        local_cast = {
            str(item.get("speaker_id")): str(item.get("name"))
            for item in ((getattr(job, "plan", {}) or {}).get("story_local_cast") or [])
            if isinstance(item, dict) and item.get("speaker_id") and item.get("name")
        }
        for panel_id, plan in plan_by_id.items():
            panel = job.panels[panel_id]
            visible_local_names = {str(name).casefold() for name in (plan.get("story_local_character_names") or [])}
            panel_local_speakers = {
                speaker_id: name for speaker_id, name in local_cast.items()
                if name.casefold() in visible_local_names
            }

            # Determine lines to place from script_lines or backward-compatible text_plan
            raw_script_lines = plan.get("script_lines")
            lines_to_place = []
            if raw_script_lines and isinstance(raw_script_lines, list):
                lines_to_place = list(raw_script_lines)
            else:
                text_plan = plan.get("text") or {}
                raw_content = text_plan.get("text_content")
                content = str(raw_content) if raw_content is not None else ""
                carrier, speaker_id, correction, validation_error = self._resolve_agent_text_carrier(
                    text_plan, panel.character_ids, panel_local_speakers
                )
                if validation_error:
                    panel.status = "needs_attention"
                    panel.error = validation_error
                    message = f"Panel {panel_id} lettering was not placed: {validation_error}"
                    if message not in job.errors:
                        job.errors.append(message)
                    self._checkpoint(job, f"panel_{panel_id}_text_rejected")
                    continue
                if correction:
                    note = f"Panel {panel_id}: {correction}"
                    if note not in job.assumptions:
                        job.assumptions.append(note)
                if content.strip() and carrier not in ("none", ""):
                    lines_to_place = [{
                        "text": content,
                        "carrier": carrier,
                        "speaker_id": speaker_id,
                        "speaker_name": text_plan.get("speaker_name"),
                        "reading_order": 1,
                        "delivery": text_plan.get("delivery") or plan.get("delivery"),
                        "emotional_intent": text_plan.get("emotional_intent") or plan.get("emotional_intent"),
                        "type_id": text_plan.get("type_id"),
                    }]

            if not lines_to_place:
                # Silent panel: zero bubbles placed
                continue

            page = next((item for item in job.pages if item.page_number == panel.page_number), None)
            doc = self._page_document(page.page_id) if page else None
            if page and getattr(page, "verification", {}).get("spacing_valid") is False:
                panel.status = "needs_attention"
                panel.error = "Lettering is paused until the page spacing issue is resolved."
                continue
            if not doc:
                continue

            from app.editor.models import LayerKind
            placed_for_this_panel = []

            # If multiple lines are present, ensure reading orders are strictly distinct and sequential
            explicit_orders = [line_item.get("reading_order") for line_item in lines_to_place]
            has_duplicates = len(set(explicit_orders)) < len(explicit_orders) or any(o is None for o in explicit_orders)

            for line_idx, line_item in enumerate(lines_to_place, start=1):
                content = str(line_item.get("text") or "").strip()
                if not content:
                    continue
                speaker_id = line_item.get("speaker_character_id") or line_item.get("speaker_id")
                raw_carrier = line_item.get("carrier")
                carrier_val = getattr(raw_carrier, "value", raw_carrier) or "speech_bubble"
                raw_kind = line_item.get("kind") or line_item.get("content_kind")
                kind_val = getattr(raw_kind, "value", raw_kind)
                type_id_val = line_item.get("type_id")
                order_idx = line_idx if has_duplicates else int(line_item.get("reading_order", line_idx))

                existing = next((
                    layer for layer in doc.layers
                    if layer.panel_id == panel_id and layer.kind == LayerKind.TEXT
                    and layer.metadata.get("text") == content
                    and (not speaker_id or layer.metadata.get("speaker_character_id") == speaker_id)
                ), None)
                if existing:
                    panel.text_layer_ids = list(dict.fromkeys([*panel.text_layer_ids, existing.layer_id]))
                    continue

                slot = doc.layout.get_panel(panel_id)

                # Semantic classification:
                # 1. Narrator text / scene descriptions / captions
                is_caption = (
                    carrier_val in ("caption", "narration_box", "narration", "caption_box")
                    or kind_val in ("narration", "date_or_place")
                    or type_id_val in ("narration.box", "caption.timeplace")
                )
                # 2. Character internal monologue (thoughts)
                is_thought = not is_caption and (
                    carrier_val in ("thought_bubble", "thought")
                    or kind_val == "internal_thought"
                    or type_id_val == "thought.cloud"
                )
                # 3. Spoken character dialogue
                is_speech = not is_caption and not is_thought and (
                    carrier_val in ("speech_bubble", "speech")
                    or kind_val in ("spoken_dialogue", "emotional_speech")
                    or type_id_val in ("speech.normal", "speech.shout", "speech.whisper", "speech.offpanel")
                    or bool(speaker_id)
                )

                if is_caption:
                    # Dedicated narration/caption placement tool: editor.add_text_layer
                    call_id = f"{job.job_id}_text_{panel_id}" if len(lines_to_place) == 1 else f"{job.job_id}_text_{panel_id}_{order_idx}"
                    layer_id = _hash_id("caption", job.job_id, panel_id, f"{order_idx}_{content}")
                    resolved_type = type_id_val if type_id_val in ("narration.box", "caption.timeplace") else "narration.box"
                    args = {
                        "page_id": page.page_id,
                        "expected_revision": doc.revision,
                        "panel_id": panel_id,
                        "text": content,
                        "layer_id": layer_id,
                        "type_id": resolved_type,
                        "reading_order": order_idx,
                        "font_family": "Comic Neue",
                        "font_size": 18,
                        "font_weight": "bold",
                        "align": "center",
                        "direction": "auto",
                    }
                    tool_id = "editor.add_text_layer"
                elif is_speech or is_thought:
                    effective_carrier = "thought_bubble" if is_thought else "speech_bubble"
                    if is_speech:
                        if not speaker_id:
                            panel.status = "needs_attention"
                            panel.error = "Spoken words need a named speaker from this panel's selected characters."
                            job.errors.append(f"Panel {panel_id} lettering was not placed: {panel.error}")
                            self._checkpoint(job, f"panel_{panel_id}_text_rejected")
                            continue
                        if speaker_id not in panel.character_ids and speaker_id not in panel_local_speakers:
                            panel.status = "needs_attention"
                            panel.error = f"Speaker '{speaker_id}' is not in this panel's selected or story-local cast; no speech balloon was created."
                            job.errors.append(f"Panel {panel_id} lettering was not placed: {panel.error}")
                            self._checkpoint(job, f"panel_{panel_id}_text_rejected")
                            continue

                    anchor = self._saved_character_anchor(doc, panel_id, speaker_id) if speaker_id else None
                    from app.canvas.bubble_stylist import recommend_bubble_style
                    emotional_intent = (
                        line_item.get("emotional_intent")
                        or plan.get("emotional_intent")
                        or line_item.get("delivery")
                        or ""
                    )
                    narrative_function = plan.get("narrative_function")
                    rec = recommend_bubble_style(
                        emotional_intent=emotional_intent or content,
                        narrative_function=narrative_function,
                        carrier=effective_carrier,
                        delivery=line_item.get("delivery") or plan.get("delivery"),
                        action_context=plan.get("story_event") or plan.get("visual_focus"),
                        story_event=plan.get("story_event"),
                        dialogue_text=content,
                    )
                    call_id = f"{job.job_id}_text_{panel_id}" if len(lines_to_place) == 1 else f"{job.job_id}_text_{panel_id}_{order_idx}"
                    resolved_type = (
                        type_id_val if type_id_val in ("speech.normal", "speech.shout", "speech.whisper", "thought.cloud", "speech.offpanel")
                        else ("thought.cloud" if is_thought else "speech.normal")
                    )
                    args = {
                        "page_id": page.page_id,
                        "expected_revision": doc.revision,
                        "panel_id": panel_id,
                        "text": content,
                        "layer_id": _hash_id("bubble", job.job_id, panel_id, f"{order_idx}_{content}"),
                        "type_id": resolved_type,
                        "reading_order": order_idx,
                        "speaker_character_id": speaker_id,
                        "speaker": line_item.get("speaker_name") if speaker_id in panel_local_speakers else None,
                        "emotional_intent": emotional_intent or content,
                        "narrative_function": narrative_function,
                        "delivery": line_item.get("delivery") or plan.get("delivery"),
                        "carrier": effective_carrier,
                        "action_context": plan.get("story_event") or plan.get("visual_focus"),
                        "story_event": plan.get("story_event"),
                        "dialogue_text": content,
                        "bubble_shape": rec.shape.value,
                        "tail_type": rec.tail_type.value,
                        "accent": rec.accent.value,
                        "has_halftone_shadow": rec.halftone_shadow,
                        "font_family": "Comic Neue",
                        "font_size": 24,
                        "font_weight": "bold",
                        "line_height": 1.2,
                        "align": "center",
                        "direction": _dialogue_direction(content),
                    }
                    if rec.inverted_dark_mode:
                        args["inverted_dark_mode"] = True
                    if anchor:
                        args["tail_target"] = anchor
                    tool_id = "canvas.add_speech_bubble"
                else:
                    call_id = f"{job.job_id}_text_{panel_id}" if len(lines_to_place) == 1 else f"{job.job_id}_text_{panel_id}_{order_idx}"
                    args = {
                        "page_id": page.page_id,
                        "expected_revision": doc.revision,
                        "panel_id": panel_id,
                        "text": content,
                        "layer_id": _hash_id("text", job.job_id, panel_id, f"{order_idx}_{content}"),
                        "font_family": "Comic Neue",
                        "font_size": 18,
                        "font_weight": "bold",
                        "align": "center",
                        "direction": "auto",
                    }
                    tool_id = "editor.add_text_layer"

                if args.get("position") is None:
                    args.pop("position", None)
                args = {k: v for k, v in args.items() if v is not None}
                call = ToolCall(call_id=call_id, tool_id=tool_id, arguments=args)
                self._checkpoint(job, f"panel_{panel_id}_text_started")
                result = self._dispatch(call, {
                    "selected_character_ids": panel.character_ids,
                    "_story_local_speakers": panel_local_speakers,
                })
                output = result.output or {}
                layer_id = output.get("layer_id")
                if result.status == "success" and layer_id:
                    panel.text_layer_ids = list(dict.fromkeys([*panel.text_layer_ids, layer_id]))
                    page.revision = output.get("revision", doc.revision)
                    doc = self._page_document(page.page_id)
                    placed_for_this_panel.append(layer_id)
                else:
                    panel.status = "needs_attention"
                    panel.error = result.error or "Canvas did not confirm the editable text/bubble layer."
                    job.errors.append(f"Panel {panel_id} text placement failed: {panel.error}")
                self._checkpoint(job, f"panel_{panel_id}_text_result")

            if len(placed_for_this_panel) > 1 and doc:
                from app.canvas.bubble_service import BubbleService
                try:
                    dir_val = (
                        getattr(job, "reading_direction", None)
                        or (job.plan.get("reading_direction") if isinstance(getattr(job, "plan", None), dict) else None)
                        or "ltr"
                    )
                    BubbleService().place_all(
                        document=doc,
                        panel_id=panel_id,
                        reading_direction=dir_val,
                    )
                    store = self._page_store(page.page_id)
                    store.save(doc.page_id, doc.revision, doc)
                    doc = self._page_document(page.page_id)
                    page.revision = doc.revision
                except Exception as exc:
                    logger.warning(
                        "Automatic multi-bubble placement failed for panel %s on page %s: %s",
                        panel_id, page.page_id, exc, exc_info=True
                    )
                    job.errors.append(f"Panel {panel_id} lettering warning: {str(exc)}")

    @staticmethod
    def _resolve_agent_text_carrier(text_plan, selected_character_ids, story_local_speakers=None):
        """Enforce the text meaning/carrier contract before any Canvas mutation."""
        raw_kind = text_plan.get("content_kind") or text_plan.get("kind")
        content_kind = getattr(raw_kind, "value", raw_kind)
        requested_carrier = str(text_plan.get("carrier", "none") or "none")
        type_id = text_plan.get("type_id")
        carrier = requested_carrier
        speaker_id = text_plan.get("speaker_id") or text_plan.get("speaker_character_id")
        selected = set(selected_character_ids or [])
        local_speakers = story_local_speakers or {}
        correction = None

        if content_kind in ("spoken_dialogue", "emotional_speech"):
            carrier = "speech_bubble"
        elif content_kind == "internal_thought":
            carrier = "thought_bubble"
        elif content_kind in ("narration", "date_or_place"):
            carrier = "caption"
        elif content_kind == "none":
            carrier = "none"
        elif type_id in ("narration.box", "caption.timeplace"):
            carrier = "caption"
        elif type_id in ("speech.normal", "speech.shout", "speech.whisper", "speech.offpanel"):
            carrier = "speech_bubble"
        elif type_id == "thought.cloud":
            carrier = "thought_bubble"
        elif content_kind is None and requested_carrier == "speech_bubble":
            # Legacy saved plans did not always include content_kind. Preserve
            # them only when they carry an explicit, selected speaker ID.
            content_kind = "spoken_dialogue"

        if carrier in ("caption", "narration_box", "narration"):
            speaker_id = None

        if carrier != requested_carrier:
            correction = (
                f"routed {content_kind or type_id or 'untyped text'} to {carrier} instead of {requested_carrier}; "
                "text meaning determines its Canvas carrier."
            )

        if carrier == "speech_bubble":
            if not speaker_id:
                return carrier, speaker_id, correction, "Spoken words need a named speaker from this panel's selected characters."
            if speaker_id not in selected and speaker_id not in local_speakers:
                return carrier, speaker_id, correction, (
                    f"Speaker '{speaker_id}' is not in this panel's selected or story-local cast; no speech balloon was created."
                )
        elif speaker_id and carrier == "thought_bubble" and speaker_id not in selected and speaker_id not in local_speakers:
            return carrier, speaker_id, correction, (
                f"Thought speaker '{speaker_id}' is not in this panel's selected or story-local cast; no thought bubble was created."
            )

        return carrier, speaker_id, correction, None

    def _saved_character_anchor(self, doc, panel_id: str, character_id: Optional[str]):
        if not character_id:
            return None
        image_layer = next((layer for layer in doc.layers if layer.panel_id == panel_id and layer.kind.value == "image"), None)
        current_asset_id = image_layer.source_asset_id if image_layer else None
        for layer in doc.layers:
            if layer.panel_id == panel_id and layer.metadata.get("speaker_character_id") == character_id:
                if layer.metadata.get("tail_anchor_character_id") == character_id and layer.metadata.get("tail_anchor_source") in {"creator_confirmed", "saved_character_anchor"}:
                    # A creator-confirmed point from a replaced image is stale.
                    # Legacy points without source provenance are only usable
                    # while the panel still has no artwork.
                    if layer.metadata.get("tail_anchor_asset_id") != current_asset_id:
                        continue
                    target = layer.metadata.get("tail_target")
                    if isinstance(target, dict) and "x" in target and "y" in target:
                        return target
        panel_layer = next((layer for layer in doc.layers if layer.panel_id == panel_id and layer.kind.value == "panel"), None)
        anchors = panel_layer.metadata.get("character_anchors", {}) if panel_layer else {}
        if current_asset_id is not None:
            anchor_assets = panel_layer.metadata.get("character_anchor_asset_ids", {}) if panel_layer else {}
            if not isinstance(anchor_assets, dict) or anchor_assets.get(character_id) != current_asset_id:
                return None
        anchor = anchors.get(character_id) if isinstance(anchors, dict) else None
        return anchor if isinstance(anchor, dict) and "x" in anchor and "y" in anchor else None

    def _verify_pages(self, job, plan_by_id) -> None:
        job.status = "verifying"
        for page in job.pages:
            doc = self._page_document(page.page_id)
            if not doc:
                page.status = "needs_attention"
                spacing_verification = {
                    key: value for key, value in page.verification.items()
                    if key.startswith("spacing")
                }
                page.verification = {"passed": False, "failures": ["Persisted page could not be reopened."], "visual_verification": "not_run", **spacing_verification}
                continue
            expected_artworks = [
                {"panel_id": panel_id, "asset_id": job.panels[panel_id].asset_id}
                for panel_id in page.panel_ids if job.panels[panel_id].asset_id
            ]
            expected_texts = []
            for panel_id in page.panel_ids:
                panel_plan = plan_by_id.get(panel_id) or {}
                raw_script_lines = panel_plan.get("script_lines")
                if raw_script_lines and isinstance(raw_script_lines, list):
                    for line in raw_script_lines:
                        txt = str(line.get("text") or "").strip()
                        if txt:
                            spk = line.get("speaker_character_id") or line.get("speaker_id")
                            c_val = getattr(line.get("carrier"), "value", line.get("carrier"))
                            k_val = getattr(line.get("kind") or line.get("content_kind"), "value", line.get("kind") or line.get("content_kind"))
                            t_val = line.get("type_id")
                            if c_val in ("caption", "narration_box", "narration") or k_val in ("narration", "date_or_place") or t_val in ("narration.box", "caption.timeplace"):
                                spk = None
                            expected_texts.append({"panel_id": panel_id, "text": txt, "speaker_character_id": spk})
                else:
                    text_plan = panel_plan.get("text") or {}
                    content = str(text_plan.get("text_content") or "").strip()
                    if content:
                        c_val = getattr(text_plan.get("carrier"), "value", text_plan.get("carrier"))
                        k_val = getattr(text_plan.get("kind") or text_plan.get("content_kind"), "value", text_plan.get("kind") or text_plan.get("content_kind"))
                        t_val = text_plan.get("type_id")
                        spk = text_plan.get("speaker_id") or text_plan.get("speaker_character_id")
                        if c_val in ("caption", "narration_box", "narration") or k_val in ("narration", "date_or_place") or t_val in ("narration.box", "caption.timeplace"):
                            spk = None
                        expected_texts.append({"panel_id": panel_id, "text": content, "speaker_character_id": spk})
            call = ToolCall(
                call_id=f"{job.job_id}_verify_page_{page.page_number}",
                tool_id="canvas.verify_page",
                arguments={
                    "page_id": page.page_id, "expected_revision": doc.revision,
                    "expected_panel_ids": page.panel_ids,
                    "required_artwork_panel_ids": page.panel_ids,
                    "expected_artworks": expected_artworks,
                    "expected_texts": expected_texts,
                },
            )
            self._checkpoint(job, f"page_{page.page_number}_verification_started")
            result = self._dispatch(call)
            spacing_verification = {
                key: value for key, value in page.verification.items()
                if key.startswith("spacing")
            }
            page.verification = {
                **(result.output or {"passed": False, "failures": [result.error or "Verification tool returned no result."], "visual_verification": "not_run"}),
                **spacing_verification,
            }
            if page.verification.get("spacing_valid") is False:
                failures = list(page.verification.get("failures") or [])
                failures.extend(page.verification.get("spacing_errors") or ["Saved page spacing did not pass production QA."])
                page.verification["failures"] = list(dict.fromkeys(failures))
                page.verification["passed"] = False
            page.revision = page.verification.get("revision", doc.revision)
            page.status = "assembled" if result.status == "success" and page.verification.get("passed") else "needs_attention"
            if page.status != "assembled":
                job.errors.extend(page.verification.get("failures", []) or [result.error or f"Page {page.page_number} verification failed."])
            self._checkpoint(job, f"page_{page.page_number}_verified")

    def _composite_and_export_pages(self, job) -> None:
        available = self._available_tool_ids()
        if "canvas.composite_page" not in available:
            return
        composite_ids = []
        for page in job.pages:
            if page.status in ("failed", "needs_attention"):
                continue
            call = ToolCall(
                call_id=f"{job.job_id}_composite_page_{page.page_number}",
                tool_id="canvas.composite_page",
                arguments={"page_id": page.page_id, "project_id": self.project_id},
            )
            self._checkpoint(job, f"page_{page.page_number}_compositing")
            res = self._dispatch(call)
            if res.status == "success" and isinstance(res.output, dict):
                art_id = res.output.get("composite_page_artifact_id")
                page.composite_artifact_id = art_id
                page.composite_image_url = res.output.get("composite_image_url")
                if art_id:
                    composite_ids.append(art_id)
            else:
                job.errors.append(f"Page {page.page_number} composition note: {res.error}")

        if composite_ids and "export.generate_comic_book" in available:
            exp_call = ToolCall(
                call_id=f"{job.job_id}_export_comic_book",
                tool_id="export.generate_comic_book",
                arguments={
                    "page_ids": [p.page_id for p in job.pages if p.status not in ("failed", "needs_attention")],
                    "project_id": self.project_id,
                    "target_format": "pdf",
                },
            )
            self._checkpoint(job, "export_delivery_started")
            exp_res = self._dispatch(exp_call)
            if exp_res.status == "success" and isinstance(exp_res.output, dict):
                job.export_artifact_id = exp_res.output.get("export_artifact_id")
                job.export_download_url = exp_res.output.get("download_url")
                job.export_file_path = exp_res.output.get("file_path")
            else:
                job.errors.append(f"Export delivery note: {exp_res.error}")

    def _page_store(self, page_id: str):
        store, _ = self.registry._editor_page(page_id, {"project_id": self.project_id})
        return store

    def _page_document(self, page_id: str):
        try:
            _store, doc = self.registry._editor_page(page_id, {"project_id": self.project_id})
            return doc
        except Exception:
            return None

    @staticmethod
    def _summary(job: StoryProductionJob, lead: Optional[str] = None) -> str:
        lines = [lead] if lead else []
        pages = sum(
            page.revision is not None and page.status in ("created", "assembled", "needs_attention")
            for page in job.pages
        )
        placed = sum(panel.status == "placed" for panel in job.panels.values())
        total = len(job.panels)
        label = "completed" if job.status == "completed" else "needs attention"
        lines.append(f"Story production {label}: {placed}/{total} panels placed across {pages}/{len(job.pages)} persisted Canvas pages.")
        for page in job.pages:
            if page.revision is not None and page.status in ("created", "assembled", "needs_attention"):
                comp_url = getattr(page, "composite_image_url", None)
                comp_txt = f" | [Composite Preview]({comp_url})" if comp_url else ""
                lines.append(f"Page {page.page_number}: `{page.page_id}` (revision {page.revision or 'unknown'}; {page.status}). Open: `#/editor?page={page.page_id}`{comp_txt}")
        for panel in job.panels.values():
            if panel.status in ("failed", "needs_attention"):
                lines.append(f"Panel `{panel.panel_id}` needs attention: {panel.error or 'production did not complete'}")
        if getattr(job, "export_download_url", None):
            lines.append(f"**Finished Book Delivery:** [Download Print-Ready PDF]({job.export_download_url})")
        if any(
            (plan.get("text") or {}).get("carrier", "none") not in ("none", "")
            and not str((plan.get("text") or {}).get("text_content") or "").strip()
            for plan in job.plan.get("plans", [])
        ):
            lines.append("No lettering was added because the approved panel plan did not include exact wording; nothing was invented.")
        if job.status == "needs_attention":
            for error in dict.fromkeys(job.errors):
                lines.append(f"- {error}")
        if any(page.verification.get("visual_verification") == "not_run" for page in job.pages):
            lines.append("Canvas structure, artwork links, and available text records were checked. Visual identity verification was not run.")
        return "\n\n".join(lines)
