"""Low-token, source-grounded repair for incomplete panel planner tool calls."""
from __future__ import annotations

import re
import json
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def normalize_panel_spelling(text: str) -> str:
    """Accept the common creator typo ``pannels`` without widening other intent."""
    return re.sub(r"\bpannels?\b", lambda match: "panel" + ("s" if match.group(0).casefold().endswith("s") else ""), text or "", flags=re.IGNORECASE)


def collapse_incomplete_planner_retries(tool_calls: Sequence[Any]) -> List[Any]:
    """Keep the most informative planner call when a model emits malformed retries together."""
    planner_calls = [call for call in tool_calls if getattr(call, "tool_id", None) == "planning.plan_panels"]
    if len(planner_calls) < 2:
        return list(tool_calls)
    arguments = [getattr(call, "arguments", {}) or {} for call in planner_calls]
    if not any(not args.get("scene_id") or not isinstance(args.get("beats"), list) or not args.get("beats") for args in arguments):
        return list(tool_calls)

    def completeness(args: Dict[str, Any]) -> tuple[int, int, int, int, int, int, int, int]:
        beats = args.get("beats")
        outline = args.get("panel_outline")
        outline_count = len(outline) if isinstance(outline, list) else 0
        panel_count = args.get("panel_count")
        count_matches_outline = isinstance(panel_count, int) and panel_count == outline_count and outline_count > 0
        return (
            int(isinstance(beats, list) and bool(beats)),
            int(bool(args.get("scene_id"))),
            int(bool(args.get("scene_summary"))),
            int(isinstance(panel_count, int) and panel_count > 0),
            int(count_matches_outline),
            outline_count,
            len(args.get("panel_dialogue") or []) if isinstance(args.get("panel_dialogue") or [], list) else 0,
            len(args),
        )

    # When two equally complete compact plans appear in one model response,
    # treat the later one as its explicit correction. Incomparable calls still
    # prefer the one with the richer, count-matched outline.
    selected = max(
        enumerate(planner_calls),
        key=lambda pair: (completeness(getattr(pair[1], "arguments", {}) or {}), pair[0]),
    )[1]
    first_index = next(index for index, call in enumerate(tool_calls) if getattr(call, "tool_id", None) == "planning.plan_panels")
    result = [call for call in tool_calls if getattr(call, "tool_id", None) != "planning.plan_panels"]
    result.insert(min(first_index, len(result)), selected)
    return result


def panel_plan_signature(arguments: Dict[str, Any]) -> str:
    """Stable signature used to distinguish a duplicate retry from a revised plan."""
    return json.dumps(arguments or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def panel_plan_retry_is_duplicate(
    arguments: Dict[str, Any],
    successful_results: Sequence[Any],
    prior_calls: Sequence[Any],
    *,
    max_successful_plans_per_turn: int = 2,
) -> bool:
    """Block identical repeats and cap successful planning at one correction."""
    successes = [
        result for result in successful_results
        if getattr(result, "tool_id", None) == "planning.plan_panels"
        and getattr(result, "status", None) == "success"
    ]
    if len(successes) >= max_successful_plans_per_turn:
        return True
    calls_by_id = {
        getattr(call, "call_id", None): call
        for call in prior_calls
        if getattr(call, "tool_id", None) == "planning.plan_panels"
    }
    current_signature = panel_plan_signature(arguments)
    for result in successes:
        previous = calls_by_id.get(getattr(result, "call_id", None))
        previous_arguments = getattr(previous, "arguments", None) if previous is not None else None
        if previous_arguments is not None and panel_plan_signature(previous_arguments) == current_signature:
            return True
    return False


def parse_panel_count(text: str) -> Optional[int]:
    query = normalize_panel_spelling(text).casefold()
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    match = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+panels?\b", query)
    if match:
        count = int(match.group(1)) if match.group(1).isdigit() else words[match.group(1)]
        if 1 <= count <= 24:
            return count
    return None


def _explicit_request_panel_count(text: str) -> Optional[int]:
    """Read a count from a concise command, avoiding incidental story numbers."""
    query = normalize_panel_spelling(text or "").casefold().strip()
    words = r"\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten"
    one_page = re.search(
        rf"\b(?:1|one)\s+(?:comic\s+)?page\b[\s\S]{{0,180}}?\b({words})\s+panels?\b",
        query,
    )
    if one_page:
        value = one_page.group(1)
        count = int(value) if value.isdigit() else {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }[value]
        return count if 1 <= count <= 24 else None
    if len(query) <= 240:
        return parse_panel_count(query)
    first_line = query.splitlines()[0].strip() if query.splitlines() else ""
    if len(first_line) <= 180 and re.search(r"\b(make|create|generate|draw|plan|revise|reshape|adapt|turn|convert)\b", first_line):
        return parse_panel_count(first_line)
    return None


def explicit_request_panel_count(text: str) -> Optional[int]:
    """Expose the conservative parser used to honor creator-authored counts."""
    return _explicit_request_panel_count(text)


def _story_sentences(source: str) -> List[str]:
    text = re.sub(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", " ", source or "")
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", " ", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"\*\*(.*?)\*\*|__(.*?)__|\*(.*?)\*|_(.*?)_", lambda m: next((group for group in m.groups() if group is not None), ""), text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if len(part.strip()) >= 20]


def _narrative_function(index: int, count: int, text: str) -> str:
    query = text.casefold()
    if index == 0:
        return "establishing"
    if re.search(r"\b(discover|realiz|reveal|announc|learn|find out|selection|selected|shortlisted)\w*\b", query):
        return "reveal"
    if re.search(r"[\"“‘].+[\"”’]", text):
        return "dialogue"
    if re.search(r"\b(think|felt|feels|worried|afraid|excited|paused|wonder|uncertain|realiz)\w*\b", query):
        return "reaction"
    if re.search(r"\b(open|read|check|close|start|build|click|run|submit|write|ask|answer)\w*\b", query):
        return "action_continuation"
    if index == count - 1:
        return "aftermath"
    return "transition"


def _word_count(text: str) -> int:
    return len(re.findall(r"(?u)\b[\w’'-]+\b", text or ""))


def _normalize_authored_text(text: str) -> str:
    """Compare source dialogue independent of Markdown emphasis and quote style."""
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = re.sub(r"(?<!\w)(?:\*{1,3}|_{1,3}|`+)|(?:\*{1,3}|_{1,3}|`+)(?!\w)", "", normalized)
    normalized = normalized.replace("‘", "'").replace("’", "'").replace("`", "'")
    normalized = normalized.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", normalized).strip()


def _apply_dialogue_length_policy(arguments: Dict[str, Any], authored_sources: Sequence[str]) -> List[str]:
    from app.canvas.bubble_registry import BUBBLE_TYPE_BY_ID
    from app.text.lettering_layout import type_id_for_text

    warnings: List[str] = []
    for beat in arguments.get("beats", []) or []:
        if not isinstance(beat, dict) or not isinstance(beat.get("text"), dict):
            continue
        text_plan = beat["text"]
        text_content = str(text_plan.get("text_content") or "")
        label = str(beat.get("panel_id") or beat.get("beat_id") or "panel")
        type_id = type_id_for_text(
            type_id=text_plan.get("type_id"),
            carrier=text_plan.get("carrier"),
            content_kind=text_plan.get("content_kind"),
            delivery=text_plan.get("delivery"),
        )
        word_limit = BUBBLE_TYPE_BY_ID[type_id].word_limit
        word_count = _word_count(text_content)
        if word_count > word_limit:
            normalized = _normalize_authored_text(text_content).casefold()
            is_verbatim = any(normalized in _normalize_authored_text(source).casefold() for source in authored_sources if source)
            origin = "creator-authored" if is_verbatim else "planned"
            warnings.append(
                f"{label}: preserved exact {origin} text at {word_count} words; {type_id} allows {word_limit}. "
                "Edit or split this line before lettering; no automatic condensation was applied."
            )
    return warnings


def recover_panel_plan_arguments(
    arguments: Dict[str, Any],
    *,
    current_request: str,
    recent_user_texts: Sequence[Tuple[str, str]],
    character_names: Dict[str, str],
    selected_character_ids: Optional[Sequence[str]] = None,
    expected_panel_count: Optional[int] = None,
    expected_panel_count_is_default: bool = False,
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str]]:
    """Expand a compact outline, or use extractive source prose as a strict fallback."""
    recovered = dict(arguments or {})
    missing_beats = not isinstance(recovered.get("beats"), list) or not recovered.get("beats")
    missing_scene = not str(recovered.get("scene_id") or "").strip()
    authored_sources = [
        _normalize_authored_text(current_request or ""),
        *(_normalize_authored_text(text) for _, text in recent_user_texts),
    ]
    if not missing_beats and not missing_scene:
        if recovered.get("panel_dialogue"):
            return recovered, None, "Use typed text fields inside each full panel beat; panel_dialogue is only for compact outlines. No panel plan or images were created."
        dialogue_warnings = _apply_dialogue_length_policy(recovered, authored_sources)
        recovered.pop("panel_count", None)
        recovered.pop("panel_outline", None)
        warning = {"dialogue_corrections": dialogue_warnings} if dialogue_warnings else None
        return recovered, warning, None

    source_id = ""
    source = ""
    # Prefer the newest substantial user-authored story, excluding the current
    # short command. Never mine assistant prose or generated tool output.
    for message_id, text in reversed(list(recent_user_texts)):
        candidate = (text or "").strip()
        if len(candidate) >= 120 or (re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", candidate) and len(candidate) >= 80):
            source_id, source = message_id, candidate
            break
    if not source and (len((current_request or "").strip()) >= 120 or (re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", current_request or "") and len((current_request or "").strip()) >= 80)):
        source = current_request.strip()

    outline = recovered.get("panel_outline")
    usable_outline = (
        [str(item).strip() for item in outline if isinstance(item, str) and item.strip()]
        if isinstance(outline, list) else []
    )
    requested_count = _explicit_request_panel_count(current_request)
    if requested_count is None and expected_panel_count is not None:
        if isinstance(expected_panel_count, bool) or not isinstance(expected_panel_count, int) or not 1 <= expected_panel_count <= 24:
            return recovered, None, "The saved requested panel count must be an integer from 1 to 24. No panel plan or images were created."
        requested_count = expected_panel_count
        if expected_panel_count_is_default and source:
            source_beat_count = len(_story_sentences(source))
            if source_beat_count:
                requested_count = min(requested_count, source_beat_count)
    supplied_count = recovered.get("panel_count")
    if supplied_count is not None:
        if isinstance(supplied_count, bool) or not isinstance(supplied_count, int) or not 1 <= supplied_count <= 24:
            return recovered, None, "The supplied panel_count must be an integer from 1 to 24. No panel plan or images were created."
    discarded_stale_outline = False
    if requested_count is not None and supplied_count is not None and requested_count != supplied_count:
        # The compact outline is model-authored and can be stale when a short
        # confirmation inherits a saved story plan. Keep the creator's count,
        # discard the mismatched outline, and rebuild only from the saved source.
        # If the source cannot support the requested count, the checks below
        # still fail explicitly instead of silently reducing it.
        usable_outline = []
        discarded_stale_outline = True
    if requested_count is not None:
        panel_count = requested_count
    elif supplied_count is not None:
        panel_count = supplied_count
    elif usable_outline:
        panel_count = len(usable_outline)
    else:
        panel_count = None
    if panel_count is None and source:
        for _, text in reversed(list(recent_user_texts)):
            earlier_count = parse_panel_count(text)
            if earlier_count:
                panel_count = earlier_count
                break
    if panel_count is None and source:
        sentences = _story_sentences(source)
        if sentences:
            panel_count = min(6, len(sentences))
        else:
            panel_count = 4

    if missing_beats and panel_count is None:
        return recovered, None, "I need an explicit panel count or story text before I can turn the story into panels. No panel plan or images were created."

    if usable_outline and len(usable_outline) != panel_count:
        if requested_count is not None:
            # A generated outline with the wrong number of beats is stale just
            # like a mismatched panel_count. Regroup source story sentences to
            # the creator's requested count rather than truncate beats.
            usable_outline = []
            discarded_stale_outline = True
        else:
            return recovered, None, (
                f"The panel count is {panel_count}, but the outline contains {len(usable_outline)} usable beats. "
                "Provide exactly one outline beat per panel. No panel plan or images were created."
            )
    if missing_beats and not source:
        return recovered, None, "I need the story text or outline as well as the panel count. No panel plan or images were created."

    dialogue_by_index: Dict[int, Dict[str, str]] = {}
    raw_dialogue = recovered.get("panel_dialogue", [])
    if raw_dialogue is not None and not isinstance(raw_dialogue, list):
        return recovered, None, "Optional panel_dialogue must be a list of spoken lines with speaker IDs. No panel plan or images were created."
    authored_sources = [*authored_sources, _normalize_authored_text(source)]
    dialogue_corrections: List[str] = []
    for item in raw_dialogue or []:
        if not isinstance(item, dict):
            return recovered, None, "Each optional spoken line needs a panel index, selected speaker ID, and text. No panel plan or images were created."
        try:
            panel_index = int(item.get("panel_index"))
        except (TypeError, ValueError):
            panel_index = 0
        speaker_id = str(item.get("speaker_id") or "").strip()
        text_content = str(item.get("text_content") or "")
        if not 1 <= panel_index <= int(panel_count or 0) or not speaker_id or not text_content.strip():
            return recovered, None, (
                f"Spoken line for panel {panel_index or '?'} needs a panel index from 1 to {panel_count or 0}, "
                "a selected speaker ID, and non-empty text. No panel plan or images were created."
            )
        if speaker_id not in character_names:
            return recovered, None, (
                f"Spoken line in panel {panel_index} uses unknown speaker ID '{speaker_id}'. "
                "Choose a character ID from this project's Story Bible. No panel plan or images were created."
            )
        selected = set(selected_character_ids or [])
        if selected and speaker_id not in selected:
            return recovered, None, (
                f"Spoken line in panel {panel_index} uses '{speaker_id}', who is outside the creator-selected cast. "
                "Use a selected character as speaker. No panel plan or images were created."
            )
        if panel_index in dialogue_by_index:
            return recovered, None, f"Panel {panel_index} has more than one generated spoken line; use one concise line per panel. No panel plan or images were created."
        normalized_dialogue = _normalize_authored_text(text_content)
        is_verbatim = any(normalized_dialogue in authored for authored in authored_sources if authored)
        if _word_count(text_content) > 12:
            dialogue_corrections.append(
                f"Panel {panel_index}: preserved exact planned speech at {_word_count(text_content)} words; speech.normal allows 12. "
                "Edit or split this line before lettering; no automatic condensation was applied."
            )
        dialogue_by_index[panel_index] = {
            "speaker_id": speaker_id,
            "text_content": text_content,
        }

    if missing_scene:
        summary = str(recovered.get("scene_summary") or "").strip()
        slug = re.sub(r"[^a-z0-9]+", "_", summary.casefold()).strip("_")[:48]
        if not slug and source:
            headings = re.findall(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(.+)$", source)
            title = next((heading for heading in headings if "part" in heading.casefold()), headings[0] if headings else "")
            slug = re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")[:48]
        recovered["scene_id"] = slug or (f"scene_{source_id[-12:]}" if source_id else "scene_from_brief")

    if missing_beats:
        use_outline = len(usable_outline) == panel_count
        sentences = _story_sentences(source)
        if not use_outline and len(sentences) < panel_count:
            return recovered, None, (
                f"The request needs {panel_count} panels, but the source has only {len(sentences)} usable story beats. "
                "Add a visual outline beat for every requested panel; the panel count will not be reduced silently. "
                "No panel plan or images were created."
            )
        if any(panel_index > panel_count for panel_index in dialogue_by_index):
            return recovered, None, "A spoken line points beyond the recovered panel count. No panel plan or images were created."
        beats: List[Dict[str, Any]] = []
        for index in range(panel_count):
            if use_outline:
                event = usable_outline[index][:1900]
                takeaway = event
            else:
                start = index * len(sentences) // panel_count
                end = (index + 1) * len(sentences) // panel_count
                chunk = sentences[start:end]
                event = " ".join(chunk[:2]).strip()[:1900]
                takeaway = chunk[0].strip()[:900]
            named_characters = [
                character_id for character_id, name in character_names.items()
                if name and re.search(rf"(?<!\w){re.escape(name)}(?!\w)", event, flags=re.IGNORECASE)
            ]
            text_plan: Dict[str, Any] = {
                "content_kind": "none",
                "carrier": "none",
                "reserve_space": False,
            }
            dialogue = dialogue_by_index.get(index + 1)
            if dialogue:
                if dialogue["speaker_id"] not in named_characters:
                    named_characters.append(dialogue["speaker_id"])
                text_plan = {
                    "content_kind": "spoken_dialogue",
                    "carrier": "speech_bubble",
                    "speaker_id": dialogue["speaker_id"],
                    "text_content": dialogue["text_content"],
                    "reserve_space": True,
                }
            beats.append({
                "beat_id": f"beat_{index + 1:02d}",
                "panel_id": f"panel_{index + 1:02d}",
                "page_number": int(recovered.get("page_number") or 1),
                "narrative_function": _narrative_function(index, panel_count, event),
                "story_event": event,
                "reader_takeaway": takeaway,
                "character_ids": named_characters,
                "visual_focus": event[:450],
                "emotional_intent": "Follow only the emotion stated in the source excerpt; do not add an unstated emotion.",
                "text": text_plan,
            })
        recovered["beats"] = beats

    if not recovered.get("scene_summary"):
        recovered["scene_summary"] = " ".join(_story_sentences(source)[:2])[:1800]
    recovered.setdefault("reading_direction", "rtl")
    warning = {
        "resolution": (
            "Discarded a stale outline whose panel count did not match the creator's request and rebuilt the requested number of visual beats from the saved story. No narration or dialogue was added unless an optional spoken line was explicitly supplied."
            if discarded_stale_outline else
            "Expanded the concise story outline into visual panel beats. No narration or dialogue was added unless an optional spoken line was explicitly supplied."
            if len(usable_outline) == panel_count else
            "Built the missing panel beats from the user's story text. Actions remain visual story events; no narration or dialogue was added unless an optional spoken line was explicitly supplied."
        ),
        "source_message_id": source_id or None,
        "panel_count": panel_count,
    }
    if dialogue_corrections:
        warning["dialogue_corrections"] = dialogue_corrections
    recovered.pop("panel_count", None)
    recovered.pop("panel_outline", None)
    recovered.pop("panel_dialogue", None)
    return recovered, warning, None
