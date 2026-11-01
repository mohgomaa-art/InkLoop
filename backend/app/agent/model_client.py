"""
InkLoop S9 Model Client & Tool-Use Planner.
Handles model-driven tool selection, parameter extraction, and multi-turn iterative reasoning
supporting live Meta Responses API and deterministic offline execution.
"""
import json
import re
import hashlib
import logging
import os
import time
import base64
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

from app.config import PROJECT_ROOT, InkLoopConfig
from app.agent.schemas import ToolCall, ToolResult, ToolDefinition
from app.agent.image_inspector import resolve_attachment_path, detect_mime_from_bytes, ImageInspectionError, MAX_FILE_BYTES
from app.agent.file_inspector import resolve_document_path, extract_stored_document, ALLOWED_DOCUMENT_MIMES

# Conversational intents
INTENT_GREETING = "GREETING"
INTENT_ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
INTENT_CANON_QUERY = "CANON_QUERY"
INTENT_PLAN_DRAFT = "PLAN_DRAFT"
INTENT_PANEL_PLANNING = "PANEL_PLANNING"
INTENT_EXECUTION = "EXECUTION"
INTENT_IMAGE_INSPECTION = "IMAGE_INSPECTION"
INTENT_BUDGET_QUERY = "BUDGET_QUERY"
INTENT_CANVAS_QUERY = "CANVAS_QUERY"
INTENT_CANVAS_CONTROL = "CANVAS_CONTROL"
INTENT_CATALOGUE_QUERY = "CATALOGUE_QUERY"
INTENT_ASSETS_QUERY = "ASSETS_QUERY"
INTENT_DIAGNOSTICS_QUERY = "DIAGNOSTICS_QUERY"
INTENT_TEXT_GENERATION = "TEXT_GENERATION"
INTENT_UNIMPLEMENTED_ENGINE = "UNIMPLEMENTED_ENGINE"
INTENT_EDITOR = "EDITOR"
INTENT_EXPORT = "EXPORT"
INTENT_GENERAL = "GENERAL"

GREETING_WORDS = {
    "hi", "hello", "hey", "greetings", "good morning", "good afternoon",
    "good evening", "how are you", "yo", "sup",
    "اه", "أه", "تمام", "هلا", "مرحبا", "أهلا", "اهلا", "صباح الخير", "مساء الخير", "السلام عليكم",
}

ACKNOWLEDGEMENT_WORDS = {
    "ok", "okay", "got it", "understood", "thanks", "thank you", "cool",
    "great", "sure", "done", "alright", "fine",
    "حسنا", "ماشي", "فهمت", "شكرا", "تسلم", "ممتاز",
}


def _clean_query(text: str) -> str:
    clean = re.sub(r"[^\w\s\$\.]", " ", text).strip().lower()
    return " ".join(clean.split())


def _classify_intent(query: str, history: List[Dict[str, Any]], has_attachments: bool) -> str:
    cleaned = _clean_query(query)
    tokens = set(cleaned.split())

    # 1. Image inspection when attachments present
    if has_attachments:
        if any(w in cleaned for w in ["visual", "compare", "consistency", "anchor", "match"]):
            return INTENT_IMAGE_INSPECTION
        return INTENT_IMAGE_INSPECTION

    # 2. Greetings & Chitchat
    if cleaned in GREETING_WORDS or (len(tokens) <= 2 and tokens.intersection(GREETING_WORDS)):
        return INTENT_GREETING

    # 3. Acknowledgements
    if cleaned in ACKNOWLEDGEMENT_WORDS or (len(tokens) <= 2 and tokens.intersection(ACKNOWLEDGEMENT_WORDS)):
        # Check if previous assistant turn was gated or requested approval
        return INTENT_ACKNOWLEDGEMENT

    # 4. E4 semantic text requests (the deterministic adapter is offline-only).
    text_action = any(w in cleaned for w in ["generate", "write", "draft", "create", "compose"])
    text_subject = any(w in cleaned for w in ["dialogue", "speech text", "narration", "script text", "e4"])
    if text_action and text_subject:
        return INTENT_TEXT_GENERATION

    # 5. Unimplemented / Future Engines
    if any(w in cleaned for w in ["typography", "font shaping", "kerning", "e5"]):
        return INTENT_UNIMPLEMENTED_ENGINE
    # Canvas and Speech Bubble Director
    canvas_terms = (
        "create page", "new page", "أنشئ صفحة", "صفحة جديدة",
        "switch template", "غير القالب", "layout template", "قالب التخطيط", "template",
        "grid", "شبكة", "قوالب", "templates",
        "speech bubble", "bubble", "balloon", "bubble tail", "فقاعة كلام", "فقاعة", "e6",
        "assemble page", "تجميع الصفحة", "رتب الصفحة",
        "compositor", "final composite", "render page", "composite panels", "composite page",
        "diagonal_slash", "three_tier", "shonen_climax", "four_panel_cinematic", "nine_panel",
        "place artwork", "ضع الصورة في اللوحة",
    )
    if any(term in cleaned for term in canvas_terms):
        return INTENT_CANVAS_CONTROL
    if any(w in cleaned for w in ["effects", "vfx", "speed lines", "motion blur", "e7"]):
        return INTENT_UNIMPLEMENTED_ENGINE
    if any(w in cleaned for w in ["export", "package delivery", "pdf bundle", "print-ready", "تصدير", "طباعة"]):
        return INTENT_EXPORT

    # Editor commands
    editor_terms = (
        "editor", "page editor", "محرر", "محرر الصفحة", "محرر الصفحات",
        "move image", "حرك الصورة", "إزاحة الصورة", "adjust image", "shift image", "fit mode",
        "add text to panel", "أضف نص", "ضيف نص", "add text layer",
        "reshape panel", "غير شكل اللوحة", "عدل شكل اللوحة",
        "add line", "أضف خط", "ضيف خط",
        "remove layer", "delete layer", "احذف الطبقة", "احذف الصورة",
    )
    if any(term in cleaned for term in editor_terms):
        return INTENT_EDITOR

    # 5. Planning requests
    panel_plan_terms = (
        "plan panels", "panel planning", "panel-by-panel", "panel by panel",
        "panel breakdown", "shot sequence", "shots per panel", "composition per panel",
        "narrative panel", "تخطيط اللوحات", "خطة اللوحات", "توزيع اللقطات",
        "لقطة لكل لوحة", "تكوين كل لوحة",
    )
    if any(term in cleaned for term in panel_plan_terms):
        return INTENT_PANEL_PLANNING
    if any(w in cleaned for w in [
        "draft a", "create a plan", "generation plan", "sequential plan", "plan for chapter",
        "أنشئ الفصل", "انشئ الفصل", "تخطيط الفصل", "فصل مانجا", "خطة إنتاج", "خطة انتاج",
        "chapter plan", "full pipeline",
    ]) or (any(w in cleaned for w in ["أنشئ", "انشئ", "create", "generate"]) and any(w in cleaned for w in ["فصل", "chapter", "مشاهد", "scenes"])):
        return INTENT_PLAN_DRAFT
    if "plan" in tokens and any(w in cleaned for w in ["draft", "create", "sequence", "scene", "budget", "ceiling"]):
        return INTENT_PLAN_DRAFT

    # 6. Execution requests
    image_gen_terms = (
        "generate", "draw", "render", "dispatch", "execute",
        "create image", "make an image", "make image", "generate image", "draw image",
        "picture of", "image of",
        "ولّد", "ولد", "توليد صورة", "توليد", "انشئ صورة", "أنشئ صورة", "ارسم", "صورة لنور", "صورة جديدة",
    )
    if any(cleaned.startswith(w) for w in ["generate", "draw", "render", "dispatch", "execute"]) or any(term in cleaned for term in image_gen_terms):
        return INTENT_EXECUTION

    # 7. Image inspection from text
    if any(w in cleaned for w in ["inspect metadata", "metadata inspection", "file integrity", "magic bytes", "sha 256", "reference image", "anchor image"]):
        return INTENT_IMAGE_INSPECTION

    # 8. Canon & Character queries
    if any(w in cleaned for w in ["canon anchor", "mandatory attributes", "character", "lore", "story bible", "invariants", "protagonist", "anchor", "cast"]):
        return INTENT_CANON_QUERY

    # 9. Budget queries
    if any(w in cleaned for w in ["budget", "allowance", "headroom", "spend", "cost", "funds", "how much balance"]):
        return INTENT_BUDGET_QUERY

    # 10. Canvas & Layout queries
    if any(w in cleaned for w in ["canvas", "template", "layout", "grid", "gutter", "margins"]):
        return INTENT_CANVAS_QUERY

    # 11. Knowledge Catalogue queries
    if any(w in cleaned for w in ["catalogue", "taxonomy", "recipes", "elements", "research governance"]):
        return INTENT_CATALOGUE_QUERY

    # 12. Asset library queries
    if any(w in cleaned for w in ["asset", "artifact", "manifest", "lineage"]):
        return INTENT_ASSETS_QUERY

    # 13. Diagnostics queries
    if any(w in cleaned for w in ["health", "status", "readiness", "diagnostics"]):
        return INTENT_DIAGNOSTICS_QUERY

    return INTENT_GENERAL


def _is_ambiguous_multi_image_request(query: str) -> bool:
    """True when the request supplies a count and character but no panel/story brief or variant intent."""
    count_words = r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten|٢|٣|٤|٥|٦|٧|٨|٩|١٠)"
    simple_request = re.compile(
        rf"^\s*(?:please\s+)?(?:make|create|generate|draw)\s+{count_words}\s+"
        r"(?:images?|pictures?|panels?)\s+(?:for|of)\s+(?:the\s+)?(?:character\s+)?[\w'-]+"
        r"(?:\s+in\s+(?:manga|anime|comic|black and white|monochrome)\s+style)?\s*[.!?]*\s*$",
        re.IGNORECASE,
    )
    arabic_simple_request = re.compile(
        r"^\s*(?:اعمل|أنشئ|انشئ|ولّد|ولد|ارسم)\s+(?:٢|٣|٤|٥|٦|٧|٨|٩|١٠|\d+)\s+"
        r"(?:صور|لوحات)\s+(?:ل|عن)\s*[\w'-]+\s*[.!؟?]*\s*$",
        re.IGNORECASE,
    )
    if not (simple_request.match(query or "") or arabic_simple_request.match(query or "")):
        return False

    # Extra scene/variation instructions make this a different, explicit mode;
    # the anchored patterns above deliberately match only count + target.
    return True


class AgentModelClient:
    """Manages conversational reasoning, tool selection, and grounded response synthesis."""

    def __init__(self, config: Optional[InkLoopConfig] = None):
        self.config = config or InkLoopConfig.load()
        self.last_usage: Optional[Dict[str, int]] = None

    def plan_next_action(
        self,
        messages: List[Dict[str, Any]],
        available_tools: List[ToolDefinition],
        project_context: Dict[str, Any],
        iteration: int = 1,
    ) -> Tuple[Optional[List[ToolCall]], Optional[str], Optional[str]]:
        """
        Evaluates conversation history and available tools to decide the next action.
        In live production with configured credentials, the real Meta Responses API model
        (muse-spark-1.3) is authoritative for reasoning, structured tool selection, and text.
        In explicit offline test mode (INKLOOP_OFFLINE_MODE or offline_mode=True), uses deterministic execution with $0.00 spend.
        """
        self.last_usage = None
        is_offline = (
            project_context.get("offline_mode") is True
            or os.getenv("INKLOOP_OFFLINE_MODE", "0").lower() in ("1", "true")
        )
        if iteration == 1:
            latest_user_text = next(
                (m.get("content") or m.get("text") or "" for m in reversed(messages) if m.get("role") == "user"),
                "",
            )
            if _is_ambiguous_multi_image_request(latest_user_text):
                is_arabic = any("\u0600" <= char <= "\u06ff" for char in latest_user_text)
                if is_arabic:
                    return (
                        None,
                        "هل تقصد (1) Variants بصرية للتصميم نفسه، أم (2) Panels متتابعة لمشهد قصصي؟ "
                        "للوحات القصصية أرسل أحداث المشهد. لن أختلق مشاهد من العدد واسم الشخصية فقط، "
                        "وسأستخدم مرجع نور المعتمد أو الصورة التي تختارها.",
                        None,
                    )
                return (
                    None,
                    "Do you mean (1) visual variants of the same approved design, or (2) story panels from one scene? "
                    "For story panels, send the scene/events. I won't invent scenes from a count and character name alone; "
                    "variants will reuse the canonical or creator-selected reference image.",
                    None,
                )
        if is_offline:
            return self._plan_offline_action(messages, available_tools, project_context, iteration)
        if not self.config.has_credentials:
            return (
                None,
                "**Model provider unavailable.** Configure `MODEL_API_KEY` to use natural-language Agent chat. "
                "The deterministic offline planner is available only when `INKLOOP_OFFLINE_MODE=1` is explicitly set.",
                None,
            )
        return self._plan_live_action(messages, available_tools, project_context, iteration)

    def _plan_live_action(
        self,
        messages: List[Dict[str, Any]],
        available_tools: List[ToolDefinition],
        project_context: Dict[str, Any],
        iteration: int = 1,
    ) -> Tuple[Optional[List[ToolCall]], Optional[str], Optional[str]]:
        """Executes live model reasoning with real structured tool calling via Meta Responses API."""
        import httpx

        api_key = (
            self.config.model_api_key.get_secret_value()
            if hasattr(self.config.model_api_key, "get_secret_value")
            else (self.config.model_api_key or "")
        )
        if not api_key:
            return None, "⚠️ **Configuration Error**: Meta Model API key is not configured. Please set MODEL_API_KEY.", None

        project_id = project_context.get("project_id", "default_project")
        tool_by_id = {tool.tool_id: tool for tool in available_tools}
        canon_hash = project_context.get("canon_hash", "")
        avail_budget = project_context.get("available_budget_usd", 10.0)
        effective_cap = project_context.get("effective_run_budget_cap_usd", avail_budget)
        latest_query = next((str(m.get("content") or m.get("text") or "") for m in reversed(messages) if m.get("role") == "user"), "")
        needs_art_context = bool(re.search(r"\b(generate|draw|image|artwork|illustrat|style|location|panel|page|canvas)\b", latest_query.lower()))
        needs_canvas_context = bool(re.search(r"\b(panel|page|canvas|editor|bubble|dialogue|speech|tail)\b", latest_query.lower()))
        style_snapshot = project_context.get("selected_style_profile") if needs_art_context else None
        location_snapshot = project_context.get("selected_location") if needs_art_context else None
        canvas_snapshot = project_context.get("canvas_page_context") if needs_canvas_context else None

        # Build tool declarations for Meta Responses API
        tools_decl = []
        for t in available_tools:
            tools_decl.append({
                "type": "function",
                "name": t.tool_id,
                "description": t.purpose,
                "parameters": t.parameters_schema or {"type": "object"},
            })

        # Build system instructions
        inst = (
            f"You are the S9 Autonomous Production Studio Coordinator for comic project '{project_id}'.\n"
            f"Active project: {project_id}\n"
            f"Canon anchor hash: {canon_hash[:12] if canon_hash else 'none'}\n"
            f"Creator-selected canonical characters: {', '.join(project_context.get('selected_character_ids', [])) or 'none selected'}\n"
            f"Active project object library (stable IDs, versions, identity traits, states, and reference asset IDs): {json.dumps(project_context.get('available_object_profiles', []), ensure_ascii=False)}\n"
            f"Creator-selected style profile snapshot: {json.dumps(style_snapshot, ensure_ascii=False) if style_snapshot else 'not needed for this request'}\n"
            f"Creator-selected location snapshot: {json.dumps(location_snapshot, ensure_ascii=False) if location_snapshot else 'not needed for this request'}\n"
            f"Active Canvas target: {json.dumps(project_context.get('canvas_target'), ensure_ascii=False) if project_context.get('canvas_target') else 'none selected'}\n"
            f"Active Canvas page state: {json.dumps(canvas_snapshot, ensure_ascii=False) if canvas_snapshot else 'not needed for this request'}\n"
            f"Available project budget: ${avail_budget:.2f} USD\n"
            f"Governing run budget ceiling: ${effective_cap:.2f} USD\n\n"
            "CORE OPERATIONAL DIRECTIVES (CREATOR CONTROL & CONCISENESS):\n"
            "- Ground every action in the creator's explicit request and the active project context. Use reasonable creative judgment within the requested scope; ask one concise question when missing information would change the requested output materially.\n"
            "- Do not retry failed, blocked, costly, canon-changing, publishing, or otherwise mutating actions unless the runtime marks a safe retry or the creator approves the retry. Never rewrite/sanitize the creator's brief and claim it was the requested action.\n"
            "- Keep explanations concise. Report only results returned by executed tools; state plainly when no action occurred or when verification is unavailable.\n\n"
            "CRITICAL INSTRUCTIONS FOR TOOL USE:\n"
            "1. For ordinary greetings ('hi', 'hello', 'مرحبا') without any story, narrative, or creative goal, answer naturally and concisely in 1-2 sentences. Do NOT call tools.\n"
            "2. For explicit image requests, invoke 'generation.generate_image' with the requested action and actual project character IDs. The tool compiles canonical context and uses a registered reference when available; never claim a reference or style was used unless the tool confirms it.\n"
            "2a. For a recurring physical object, reuse its exact prop_id from the active project object library. Do not create a second ID for the same lamp, key, phone, or other physical item. Put only scene state (for example lit, carried, or damaged) in prop_states. For a genuinely new recurring design, include one recurring_objects draft in the typed story blueprint and use that same prop_id on every planned panel where it appears. The runtime saves it as a project draft, attaches the first real registered artwork only as an unverified provisional reference, and sends verified reference bytes with the object role on later panels. Never claim exact visual continuity or visual verification unless an actual verification result says so.\n"
            "3. If a request gives only a count plus a character name with zero action (for example, 'make 4 images of the protagonist'), ask whether the creator wants visual variants or story panels. If they explicitly request variants or say 'more of image/character #N', reuse the creator-selected registered asset through reference_asset_id, keep canonical identity invariants, and vary only the requested aspects.\n"
            "4. When the creator shares a story, script, narrative, or confirms ('start', 'yes', 'yes pls', 'proceed', 'go ahead', 'do it', 'make it'), act as an autonomous production agent! Do NOT stall by asking passive chatbot questions. Call 'planning.plan_panels' using its compact Agent-facing schema: provide panel_count (default 6 for a standard comic page if not explicitly stated, or 4 if very short), and exactly one concise panel_outline beat per panel grounded in the supplied story. The coordinator expands that outline and automatically executes the plan through real image generation, canvas assembly, lettering, and print-ready delivery. Never stop after merely inspecting characters or budget when an actionable story or 'start' command was given.\n"
            "4a. Keep panel_outline entries as visual story events, not dialogue or captions. A speech balloon is only audible words spoken by one named character in that panel's creator-selected cast. Never put narration, plot summaries, actions, or visual descriptions in a speech balloon. Use narration only as a brief caption when needed; omit it when the art communicates the event. Internal thought belongs in a thought bubble. Leave panels without lettering when no line adds value.\n"
            "4b. Use optional panel_dialogue only for a plausible audible line. Aim for 8 words or fewer and never exceed 12 words for newly drafted dialogue; use the exact selected speaker_id. Preserve exact creator-authored dialogue unchanged even if longer. Never truncate or rewrite exact text. New Agent speech bubbles use 24px text; rely on Canvas measurement and report overflow instead of shrinking the font.\n"
            "4c. Select each new bubble treatment from that panel's emotional_intent, delivery, and meaningful action context. Pass those values to canvas.add_speech_bubble; do not reuse one generic shape for every line. Keep narration in caption/text layers and thoughts in thought bubbles. Let the Canvas tool position bubbles automatically; do not invent fixed page coordinates. If it reports no safe space or an unavailable speaker anchor, report that and do not force an overlap.\n"
            "5. When the user asks to inspect canon or characters, call 'canon.inspect_characters' or 'canon.inspect_reference_anchor'.\n"
            "6. When the user asks about available budget, call 'execution.get_budget_allowance'.\n"
            "7. When the user asks whether image generation is configured or ready, call 'generation.check_readiness'; report its returned state without exposing secrets.\n"
            "8. When creating or proposing new characters, call 'canon.propose_character_mutation'.\n"
            "9. After a tool executes, report its returned status and evidence. Embed an image and state the registered asset ID only when the successful tool result contains them. If visual verification was not run, say so.\n"
            "10. If an image is attached, describe or analyze visible features accurately and distinguish visible visual evidence from metadata.\n"
            "11. LIVE IMAGE PREVIEW IN CHAT: When 'generation.generate_image' executes successfully, its output contains 'url' and 'asset_id'. You MUST embed the image in your final markdown response and state the registered asset ID. Use a selected image's asset_id as reference_asset_id for continuations; never pass a filesystem path.\n"
            "12. Artwork is a clean image layer. Do not ask E1 to draw text, labels, headings, captions, logos, or speech bubbles; use the appropriate registered text or Canvas tool when available.\n"
            "12. For edits to an existing page, use registered canvas.* and editor.* tools and the exact page, panel, and revision from Active Canvas page state; if that edit target is missing, ask the creator to select it instead of inventing IDs. To zoom, scale, or reposition an image in a panel, use 'editor.update_image_placement' with 'panel_id' and 'zoom' or 'transform'. To zoom or scale a speech bubble, use 'canvas.update_speech_bubble' with 'scale'. For a new-page story request, create a new page from the actual plan and place generated artwork with returned asset IDs.\n"
            "13. For layout changes, choose registered Canvas layout and panel tools that match the request; preserve the existing story and reading order unless the creator asked to change them. Use the newest returned page revision for each follow-up mutation. If the creator asks to scratch/custom-draw a new page, use 'canvas.create_custom_page' with normalized rect or polygon geometry so the result is the same editable page the manual Canvas opens; do not substitute a square grid. For an existing page, use 'canvas.reshape_panel'. Use 'canvas.inspect_page_spacing' to measure real saved panel gaps, and do not guess gutters or spacing from a screenshot description.\n"
            "14. Add only planned exact lettering as editable Canvas layers, not inside generated artwork. Keep audible character speech in a speech balloon, internal thought in a thought bubble, and narration in a caption/narration box. Use expressive bubble presets only when they match the line; never turn narration into speech. The runtime uses selected speaker IDs and known anchors where available.\n"
            "15. If asked to create structured dialogue or captions, use 'text.generate_dialogue' only when it is listed among this turn's available tools; otherwise explain it is unavailable here."
        )

        workflow_skill = project_context.get("workflow_skill")
        if workflow_skill:
            inst += "\n\nCREATIVE WORKFLOW SKILL — read before planning or production:\n" + str(workflow_skill)

        # Build input messages
        input_items = []
        for m in messages:
            role = m.get("role", "user")
            if role == "user":
                content_items = []
                for att in (m.get("attachments", []) if iteration == 1 else []):
                    mime = att.get("mime_type", "image/png")
                    attachment_id = att.get("attachment_id") or att.get("asset_id")
                    if attachment_id and mime.startswith("image/"):
                        try:
                            p = resolve_attachment_path(attachment_id, project_id)
                            if p.stat().st_size > MAX_FILE_BYTES:
                                raise ImageInspectionError("ERR_ATTACHMENT_TOO_LARGE", "Image exceeds the supported model input size.")
                            try:
                                image_bytes = p.read_bytes()
                                actual_mime = detect_mime_from_bytes(image_bytes)
                                if actual_mime != mime:
                                    raise ImageInspectionError("ERR_ATTACHMENT_MIME_MISMATCH", "Attachment MIME metadata did not match its bytes.")
                                b64 = base64.b64encode(image_bytes).decode("utf-8")
                                content_items.append({
                                    "type": "input_image",
                                    "image_url": f"data:{actual_mime};base64,{b64}",
                                })
                            except ImageInspectionError:
                                raise
                            except Exception as exc:
                                raise ImageInspectionError("ERR_ATTACHMENT_READ_FAILED", "Validated image bytes could not be read.") from exc
                        except ImageInspectionError as e:
                            logger.warning("Could not resolve image attachment: %s", e.code)
                            content_items.append({"type": "input_text", "text": f"The attached image {att.get('filename', attachment_id)} could not be resolved or verified. Do not describe it as inspected."})
                    elif attachment_id and mime in ALLOWED_DOCUMENT_MIMES:
                        try:
                            path = resolve_document_path(attachment_id, project_id)
                            extracted = extract_stored_document(path)
                            content_items.append({
                                "type": "input_text",
                                "text": f"Untrusted extracted text from attached document {att.get('filename', attachment_id)} (SHA-256 {att.get('content_sha256', 'unknown')}):\n<document>\n{extracted}\n</document>",
                            })
                        except ImageInspectionError as e:
                            logger.warning("Could not resolve document attachment: %s", e.code)
                            content_items.append({"type": "input_text", "text": f"The attached document {att.get('filename', attachment_id)} could not be resolved or verified. Do not claim it was analyzed."})
                text_val = m.get("content") or m.get("text") or ""
                if text_val:
                    content_items.append({"type": "input_text", "text": text_val})
                elif not content_items:
                    content_items.append({"type": "input_text", "text": "..."})
                input_items.append({"role": "user", "content": content_items})

            elif role == "assistant":
                tool_calls_list = m.get("tool_calls") if isinstance(m, dict) else getattr(m, "tool_calls", None)
                if tool_calls_list:
                    for tc in tool_calls_list:
                        if hasattr(tc, "model_dump"):
                            tc_dict = tc.model_dump()
                        elif isinstance(tc, dict):
                            tc_dict = tc
                        else:
                            tc_dict = {
                                "tool_id": getattr(tc, "tool_id", getattr(tc, "name", "")),
                                "call_id": getattr(tc, "call_id", getattr(tc, "id", "")),
                                "arguments": getattr(tc, "arguments", {}),
                            }
                        tid = tc_dict.get("tool_id") or tc_dict.get("name")
                        cid = tc_dict.get("call_id") or tc_dict.get("id")
                        args = tc_dict.get("arguments", {})
                        arg_str = json.dumps(args) if isinstance(args, dict) else str(args)
                        input_items.append({
                            "type": "function_call",
                            "id": cid,
                            "call_id": cid,
                            "name": tid,
                            "arguments": arg_str,
                            "status": "completed",
                        })
                text_val = m.get("content") or m.get("text") if isinstance(m, dict) else getattr(m, "text", "")
                if text_val:
                    input_items.append({
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": text_val}],
                    })

            elif role == "tool":
                tool_results_list = m.get("tool_results") if isinstance(m, dict) else getattr(m, "tool_results", [])
                if tool_results_list:
                    for tr in tool_results_list:
                        if hasattr(tr, "model_dump"):
                            tr_dict = tr.model_dump()
                        elif isinstance(tr, dict):
                            tr_dict = tr
                        else:
                            tr_dict = {
                                "call_id": getattr(tr, "call_id", "call_0"),
                                "status": getattr(tr, "status", "success"),
                                "output": getattr(tr, "output", None),
                                "error": getattr(tr, "error", None),
                                "error_code": getattr(tr, "error_code", None),
                            }
                        cid = tr_dict.get("call_id") or "call_0"
                        out = tr_dict.get("output") if tr_dict.get("status") == "success" else {
                            "error": tr_dict.get("error"),
                            "error_code": tr_dict.get("error_code"),
                            "status": tr_dict.get("status"),
                        }
                        out_str = json.dumps(out) if isinstance(out, (dict, list)) else str(out)
                        input_items.append({
                            "type": "function_call_output",
                            "call_id": cid,
                            "output": out_str,
                        })

        if not input_items:
            return None, "Hello! How can I assist you with InkLoop today?", None

        payload = {
            "model": self.config.muse_spark_model,
            "instructions": inst,
            "tools": tools_decl,
            "input": input_items,
        }

        resp = None
        for attempt in range(2):
            try:
                resp = httpx.post(
                    f"{self.config.meta_base_url.rstrip('/')}/responses",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=45.0,
                )
            except httpx.TimeoutException:
                if attempt == 0:
                    time.sleep(0.25)
                    continue
                return None, "The model provider timed out after one retry. No action was taken; please retry.", None
            except httpx.RequestError as exc:
                if attempt == 0:
                    time.sleep(0.25)
                    continue
                logger.warning("Live model request failed after retry: %s", type(exc).__name__)
                return None, "The model provider could not be reached after one retry. No action was taken.", None

            if resp.status_code == 200:
                break
            if attempt == 0 and resp.status_code in {429, 500, 502, 503, 504}:
                time.sleep(0.25)
                continue
            logger.warning("Meta Responses API returned HTTP %s", resp.status_code)
            return None, f"The model provider returned HTTP {resp.status_code}. No action was taken.", None

        data = resp.json()
        usage = data.get("usage") if isinstance(data, dict) else None
        if isinstance(usage, dict):
            reported = {}
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                value = usage.get(key)
                if isinstance(value, int) and value >= 0:
                    reported[key] = value
            self.last_usage = reported or None
        raw_output = data.get("output", [])

        # Check for function calls
        function_calls = [o for o in raw_output if o.get("type") == "function_call"]
        assistant_messages = [o for o in raw_output if o.get("type") == "message" and o.get("role") == "assistant"]

        if function_calls:
            parsed_calls = []
            for fc in function_calls:
                call_id = fc.get("call_id") or fc.get("id") or f"call_{int(time.time()*1000)}"
                tool_name = fc.get("name", "")
                raw_args = fc.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except Exception:
                    args = {}
                tool_definition = tool_by_id.get(tool_name)
                declared_properties = (
                    (tool_definition.parameters_schema or {}).get("properties", {})
                    if tool_definition else {}
                )
                if "project_id" in declared_properties and "project_id" not in args:
                    args["project_id"] = project_id
                parsed_calls.append(ToolCall(call_id=call_id, tool_id=tool_name, arguments=args))

            step_label = f"Executing {parsed_calls[0].tool_id}..." if parsed_calls else "Executing tools..."
            return parsed_calls, None, step_label

        if assistant_messages:
            text_content = ""
            for c in assistant_messages[0].get("content", []):
                if c.get("type") == "output_text":
                    text_content += c.get("text", "")
            if text_content.strip():
                return None, text_content.strip(), None
            return None, "The model returned an empty response. No action was taken; please retry.", None

        return None, "The model returned no usable response. No action was taken; please retry.", None

    def _plan_offline_action(
        self,
        messages: List[Dict[str, Any]],
        available_tools: List[ToolDefinition],
        project_context: Dict[str, Any],
        iteration: int = 1,
    ) -> Tuple[Optional[List[ToolCall]], Optional[str], Optional[str]]:
        """
        Evaluates the latest user turn and prior tool results to dynamically select tools
        or formulate a grounded final response.
        """
        last_msg = messages[-1] if messages else {"role": "user", "content": ""}
        user_query = ""
        user_attachments = []
        for m in reversed(messages):
            if m.get("role") == "user":
                user_query = m.get("content", "")
                user_attachments = m.get("attachments", [])
                break

        document_mimes = {"text/plain", "text/markdown", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        if any(att.get("mime_type") in document_mimes for att in user_attachments):
            return (
                None,
                "The document is stored and available to live Agent mode, but explicit offline mode cannot interpret document contents. No summary or document-based action was produced.",
                None,
            )

        # Check if the last turn was a tool result
        tool_results: List[ToolResult] = last_msg.get("tool_results", [])

        # If we have tool results from iteration >= 1, synthesize response or decide next tool
        if tool_results:
            first_tr = tool_results[0]
            first_tr_tool_id = first_tr.get("tool_id") if isinstance(first_tr, dict) else getattr(first_tr, "tool_id", "")
            # Multi-step mutation flow if user explicitly requested character creation or mutation
            if (
                first_tr_tool_id == "canon.inspect_characters"
                and any(w in user_query.lower() for w in ["propose", "create", "add", "new character"])
                and iteration < 3
            ):
                q_lower = user_query.lower()
                m_name = re.search(r"named\s+([A-Za-z0-9_\-]+)", user_query, re.IGNORECASE)
                if m_name:
                    target_name = m_name.group(1).lower()
                elif "mira" in q_lower:
                    target_name = "mira"
                elif "rival" in q_lower:
                    target_name = "rival"
                else:
                    target_name = "character_02"

                # Extract traits
                traits = []
                for phrase in ["silver hair", "blue eyes", "cybernetic arm", "mechanical arm", "engineer", "red coat", "leather jacket"]:
                    if phrase in q_lower:
                        traits.append(phrase)
                if not traits:
                    traits = ["distinctive design", "sequential continuity"]

                call = ToolCall(
                    call_id=f"call_{abs(hash(user_query + str(iteration))) % 100000}",
                    tool_id="canon.propose_character_mutation",
                    arguments={
                        "project_id": project_context.get("project_id", "default_project"),
                        "target_type": "character",
                        "target_id": target_name,
                        "change_description": f"Proposed character {target_name.capitalize()} from user brief: {user_query}",
                        "proposed_changes": {
                            "action": "add",
                            "name": target_name.capitalize(),
                            "role": "Supporting Character" if "engineer" in q_lower else "Character",
                            "visual_invariants": traits,
                            "attributes": [
                                {"id": f"{target_name}_attr_{i+1}", "text": t, "required": True}
                                for i, t in enumerate(traits)
                            ],
                        },
                    },
                )
                return [call], None, f"Drafting structured character proposal for {target_name.capitalize()}..."

            # Synthesize final answer grounded in actual tool outputs
            return None, self._synthesize_grounded_response(user_query, tool_results, project_context), None

        # Iteration 1: Semantic Intent Classification
        has_image_attachments = any(str(att.get("mime_type", "")).startswith("image/") for att in user_attachments)
        intent = _classify_intent(user_query, messages[:-1], has_attachments=has_image_attachments)
        project_id = project_context.get("project_id", "default_project")
        tools_by_id = {t.tool_id: t for t in available_tools}

        # Intent: GREETING
        if intent == INTENT_GREETING:
            is_arabic = any(w in user_query for w in ["اه", "أه", "تمام", "هلا", "مرحبا", "أهلا", "اهلا", "صباح", "مساء", "سلام"])
            if is_arabic:
                reply = (
                    "أهلاً بك! أنا وكيل InkLoop للإنتاج. يمكنني مساعدتك في فحص Story Bible، "
                    "وتدقيق سمات الشخصيات، وتخطيط الكانفاس، وصياغة خطط التوليد، "
                    "وفحص الصور، وإدارة الميزانية. كيف يمكنني مساعدتك اليوم؟"
                )
            else:
                reply = (
                    "Hello! I am your InkLoop Production Studio Agent. I can help you inspect Story Bible specifications, "
                    "verify character invariants, generate canvas layouts, draft sequential plans within budgets, "
                    "and inspect image attachments. How can I assist with your comic production today?"
                )
            return None, reply, None

        # Intent: ACKNOWLEDGEMENT
        if intent == INTENT_ACKNOWLEDGEMENT:
            # Check context for prior gated approvals or plans
            approval_id = project_context.get("approval_id")
            if approval_id:
                reply = (
                    f"Understood. The action remains paused at Approval Gate `{approval_id}`. "
                    "To proceed with execution, please submit an approval decision in the Approval Queue or specify 'APPROVE'."
                )
            else:
                is_arabic = any(w in user_query for w in ["تمام", "ماشي", "فهمت", "شكرا"])
                if is_arabic:
                    reply = "تمام، أنا جاهز لأي خطوة قادمة في المشروع. ماذا تود أن نفعل الآن؟"
                else:
                    reply = "Understood. I am ready for the next step in your project workflow. What would you like to work on next?"
            return None, reply, None

        # Offline panel planning is structured-input only; do not substitute
        # the unrelated sequential execution planner or invent story semantics.
        if intent == INTENT_PANEL_PLANNING:
            return (
                None,
                "Offline panel planning requires structured scene beats (narrative function, story event, reader takeaway, visual focus, emotion, and explicit text carrier). Submit them to POST /api/v1/planning/panels or use live Agent mode for model-assisted beat structuring. No generation or execution plan was started.",
                None,
            )

        # Intent: TEXT_GENERATION (explicit offline mode only)
        if intent == INTENT_TEXT_GENERATION:
            q_lower = user_query.lower()
            scene_match = re.search(r"\bscene[_-][a-z0-9_-]+", q_lower)
            panel_match = re.search(r"\bpanel[_-][a-z0-9_-]+", q_lower)
            kind = "dialogue"
            for kind_name, words in (
                ("narration", ("narration",)),
                ("caption", ("caption",)),
                ("monologue", ("monologue", "inner thought")),
                ("sfx", ("sfx", "sound effect")),
            ):
                if any(word in q_lower for word in words):
                    kind = kind_name
                    break
            is_arabic = any("\u0600" <= char <= "\u06ff" for char in user_query)
            matched_char_ids = []
            try:
                from app.agent.registry import _get_project_bible
                b_proj = _get_project_bible(project_id)
                for cid, cdef in getattr(b_proj, "characters", {}).items():
                    if cid.lower() in q_lower or getattr(cdef, "name", "").lower() in q_lower:
                        matched_char_ids.append(cid)
            except Exception:
                pass
            args = {
                "scene_id": scene_match.group(0) if scene_match else "scene_01",
                "panel_id": panel_match.group(0) if panel_match else "panel_01",
                "scene_action": user_query,
                "character_ids": matched_char_ids,
                "block_kinds_requested": [kind],
                "target_language": "ar" if is_arabic else "en",
                "target_direction": "rtl" if is_arabic else "ltr",
            }
            call = ToolCall(call_id="call_text_generate_01", tool_id="text.generate_dialogue", arguments=args)
            return [call], None, "Generating structured E4 text in explicit offline simulation mode..."

        # Intent: UNIMPLEMENTED_ENGINE
        if intent == INTENT_UNIMPLEMENTED_ENGINE:
            q_lower = user_query.lower()
            if any(w in q_lower for w in ["typography", "font", "e5"]):
                tid = "typography.shape_text"
            elif any(w in q_lower for w in ["speech bubble", "balloon", "e6"]):
                tid = "speech_bubble.place_bubbles"
            elif any(w in q_lower for w in ["effects", "vfx", "speed lines", "e7"]):
                tid = "effects.apply_fx"
            elif any(w in q_lower for w in ["compositor", "final composite"]):
                tid = "compositor.render_page"
            else:
                tid = "export.package_delivery"

            if tid in tools_by_id:
                call = ToolCall(call_id=f"call_{tid.replace('.', '_')}", tool_id=tid, arguments={})
                return [call], None, f"Querying {tools_by_id[tid].name}..."

        # Intent: PLAN_DRAFT
        if intent == INTENT_PLAN_DRAFT:
            # Parse budget cap and panel count
            cap = None
            m = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", user_query)
            if m:
                cap = float(m.group(1))

            p_count = 6
            m_p = re.search(r"(\d+)\s*(?:[ -]?panel|لوح)", user_query, re.IGNORECASE)
            if m_p:
                p_count = int(m_p.group(1))
            elif "six" in user_query.lower() or "ست" in user_query:
                p_count = 6

            call = ToolCall(
                call_id=f"call_plan_draft_{int(hashlib.sha256(user_query.encode()).hexdigest()[:8], 16)}",
                tool_id="plan.draft_plan",
                arguments={
                    "project_id": project_id,
                    "goal": user_query,
                    "panel_count": p_count,
                    "requested_run_budget_cap_usd": cap,
                },
            )
            return [call], None, f"Drafting {p_count}-panel sequential execution plan..."

        # Intent: EDITOR
        if intent == INTENT_EDITOR:
            from app.api.routers.editor import get_page_store
            store = get_page_store()
            pages = store.list_pages(project_id)
            target_page_id = pages[0]["page_id"] if pages else None
            m_pg = re.search(r"page_[a-zA-Z0-9_\-]+", user_query)
            if m_pg:
                target_page_id = m_pg.group(0)

            if target_page_id is None:
                return None, "There is no saved page in this project yet. Create a page before editing it; no edit was made.", None
            try:
                page_doc = store.get(target_page_id)
            except Exception:
                return None, f"I could not load page {target_page_id} in the active project; no edit was made.", None
            if page_doc.project_id != project_id:
                return None, f"Page {target_page_id} is outside the active project; no edit was made.", None
            ordered_panels = sorted(page_doc.layout.panel_slots, key=lambda item: item.reading_order)
            panel_match = re.search(r"panel_[a-zA-Z0-9_\-]+", user_query)
            target_panel_id = panel_match.group(0) if panel_match else (ordered_panels[0].panel_id if ordered_panels else None)
            expected_revision = page_doc.revision

            q_lower = user_query.lower()
            if any(w in q_lower for w in ["move image", "حرك الصورة", "إزاحة الصورة", "adjust image", "shift image"]):
                dx = 25
                dy = 0
                if "right" in q_lower or "يمين" in q_lower:
                    dx = 25
                elif "left" in q_lower or "يسار" in q_lower:
                    dx = -25
                elif "up" in q_lower or "فوق" in q_lower or "أعلى" in q_lower:
                    dy = -25
                    dx = 0
                elif "down" in q_lower or "تحت" in q_lower or "أسفل" in q_lower:
                    dy = 25
                    dx = 0
                image_layer = next((layer for layer in page_doc.layers if layer.kind.value == "image" and (not target_panel_id or layer.panel_id == target_panel_id)), None)
                if image_layer is None:
                    return None, f"Page {target_page_id} has no image in the selected panel to move; no edit was made.", None
                transform = image_layer.transform.model_dump(mode="json") if image_layer.transform else {}
                transform["translate_x"] = float(transform.get("translate_x", 0)) + dx
                transform["translate_y"] = float(transform.get("translate_y", 0)) + dy
                call = ToolCall(
                    call_id="call_editor_placement",
                    tool_id="editor.update_image_placement",
                    arguments={
                        "page_id": target_page_id,
                        "expected_revision": expected_revision,
                        "layer_id": image_layer.layer_id,
                        "transform": transform,
                    },
                )
                return [call], None, f"Updating image placement within panel mask on {target_page_id}..."

            if any(w in q_lower for w in ["add text", "أضف نص", "ضيف نص", "text layer"]):
                m_txt = re.search(r"['\"]([^'\"]+)['\"]", user_query)
                text_content = m_txt.group(1) if m_txt else None
                if not text_content:
                    return None, "Please provide the exact wording to add; I will not insert placeholder dialogue.", None
                call = ToolCall(
                    call_id="call_editor_text",
                    tool_id="editor.add_text_layer",
                    arguments={
                        "page_id": target_page_id,
                        "expected_revision": expected_revision,
                        "panel_id": target_panel_id,
                        "text": text_content,
                    },
                )
                return [call], None, f"Adding text layer to {target_page_id}..."

            if any(w in q_lower for w in ["reshape", "غير شكل", "عدل شكل", "polygon", "مضلع"]):
                return None, "Tell me which panel and the new size or corner positions. I need those values to reshape it accurately; no geometry was changed.", None

            if any(w in q_lower for w in ["add line", "أضف خط", "ضيف خط"]):
                return None, "Give me the line’s start and end coordinates (or describe what it should connect) before I add it.", None

            # Default: list pages
            call = ToolCall(
                call_id="call_editor_list",
                tool_id="editor.list_pages",
                arguments={"project_id": project_id},
            )
            return [call], None, "Querying saved editable pages..."

        if intent == INTENT_EXPORT:
            from app.api.routers.editor import get_page_store
            saved_pages = get_page_store().list_pages(project_id)
            explicit_page = re.search(r"page_[a-zA-Z0-9_\-]+", user_query)
            if explicit_page:
                page_ids = [explicit_page.group(0)]
            elif len(saved_pages) == 1:
                page_ids = [saved_pages[0]["page_id"]]
            elif not saved_pages:
                return None, "There are no saved pages to export in this project; no export was created.", None
            else:
                return None, "Several pages are saved. Select the page IDs or use the story production export so their reading order is preserved.", None
            target_format = "png" if "png" in user_query.lower() else "pdf"
            call = ToolCall(
                call_id="call_export_comic",
                tool_id="export.generate_comic_book",
                arguments={"page_id": page_ids[0], "project_id": project_id, "target_format": target_format},
            )
            return [call], None, f"Exporting saved page {page_ids[0]} as {target_format.upper()}..."

        # Intent: CANVAS_CONTROL
        if intent == INTENT_CANVAS_CONTROL:
            q_lower = user_query.lower()
            target_page_id = None
            try:
                from app.api.routers.editor import get_page_store
                pages = get_page_store().list_pages(project_id)
                if pages:
                    target_page_id = pages[0]["page_id"]
                    page_doc = get_page_store().get(target_page_id)
                    if page_doc.project_id != project_id:
                        target_page_id = None
                    else:
                        expected_revision = page_doc.revision
                        ordered_panels = sorted(page_doc.layout.panel_slots, key=lambda item: item.reading_order)
                        panel_match = re.search(r"panel_[a-zA-Z0-9_\-]+", user_query)
                        target_panel_id = panel_match.group(0) if panel_match else (ordered_panels[0].panel_id if ordered_panels else None)
            except Exception:
                pass

            if any(w in q_lower for w in ["bubble", "speech bubble", "balloon", "فقاعة"]):
                if not target_page_id:
                    return None, "There is no saved page to edit yet. Create or select a page first; no canvas action was taken.", None
                m_txt = re.search(r"['\"]([^'\"]+)['\"]", user_query)
                text_content = m_txt.group(1) if m_txt else None
                if not text_content:
                    return None, "Please provide the exact speech-bubble text before editing the page.", None
                if not target_panel_id:
                    return None, f"Page {target_page_id} has no panels to attach this bubble to; no edit was made.", None
                if not target_panel_id:
                    return None, f"Page {target_page_id} has no panels to attach this bubble to; no edit was made.", None
                shape = "shout_burst" if any(w in q_lower for w in ["shout", "burst", "scream", "صراخ"]) else "thought_cloud" if any(w in q_lower for w in ["thought", "think", "فكرة"]) else "oval"
                tail = "lightning_bolt" if shape == "shout_burst" else "bubble_chain" if shape == "thought_cloud" else "smooth_pointer"
                call = ToolCall(
                    call_id="call_canvas_bubble",
                    tool_id="canvas.add_speech_bubble",
                    arguments={
                        "page_id": target_page_id,
                        "expected_revision": expected_revision,
                        "panel_id": target_panel_id,
                        "text": text_content,
                        "bubble_shape": shape,
                        "tail_type": tail,
                    },
                )
                return [call], None, f"Directing expressive {shape} speech bubble on {target_page_id}..."

            if any(w in q_lower for w in ["compositor", "final composite", "render page", "composite panels", "composite page"]):
                if not target_page_id:
                    return None, "There is no saved page to render in this project; no composite was created.", None
                call = ToolCall(
                    call_id="call_canvas_composite_page",
                    tool_id="canvas.composite_page",
                    arguments={"page_id": target_page_id, "project_id": project_id},
                )
                return [call], None, f"Rendering the saved Canvas page {target_page_id}..."

            if any(w in q_lower for w in ["switch", "change template", "غير القالب"]):
                if not target_page_id:
                    return None, "There is no saved page to edit yet. Create or select a page first; no canvas action was taken.", None
                call = ToolCall(
                    call_id="call_canvas_switch",
                    tool_id="canvas.switch_page_template",
                    arguments={
                        "page_id": target_page_id,
                        "expected_revision": expected_revision,
                        "layout_template": "diagonal_slash_battle",
                        "preserve_layers": True,
                    },
                )
                return [call], None, f"Switching layout template on {target_page_id}..."

            if any(w in q_lower for w in ["assemble", "رتب الصفحة", "تجميع"]):
                return None, "I need the approved panel beats or a saved story plan to assemble the page. I will not invent scenes or dialogue.", None

            # Default canvas creation
            chosen_tpl = "diagonal_slash_battle" if "slash" in q_lower else "three_tier_action_slant" if "tier" in q_lower or "slant" in q_lower else "dynamic_shonen"
            call = ToolCall(
                call_id="call_canvas_create",
                tool_id="canvas.create_page_from_template",
                arguments={
                    "layout_template": chosen_tpl,
                    "project_id": project_id,
                    "reading_direction": "ltr",
                },
            )
            return [call], None, f"Creating new comic page using {chosen_tpl} template..."

        # Intent: EXECUTION
        if intent == INTENT_EXECUTION:
            q_lower = user_query.lower()
            is_gen = any(w in q_lower for w in ["generate", "draw", "render", "create", "make", "ولّد", "ولد", "توليد", "انشئ", "أنشئ", "ارسم"]) or any(w in q_lower for w in ["image", "panel", "صورة", "لوحة"])
            if is_gen or ("dispatch" not in q_lower and "execute plan" not in q_lower):
                gen_args: Dict[str, Any] = {"prompt": user_query, "panel_id": "panel_01", "width": 1024, "height": 1536}
                if any(w in q_lower for w in ["initial", "portrait", "anchor", "concept"]):
                    gen_args["is_anchor_generation"] = True
                exec_char_ids = []
                try:
                    from app.agent.registry import _get_project_bible
                    b_proj = _get_project_bible(project_id)
                    for cid, cdef in getattr(b_proj, "characters", {}).items():
                        if cid.lower() in q_lower or getattr(cdef, "name", "").lower() in q_lower:
                            exec_char_ids.append(cid)
                except Exception:
                    pass
                if not exec_char_ids and project_context.get("selected_character_ids"):
                    exec_char_ids = [str(x) for x in project_context.get("selected_character_ids")]
                if exec_char_ids:
                    gen_args["character_ids"] = exec_char_ids
                call = ToolCall(
                    call_id="call_gen_01",
                    tool_id="generation.generate_image",
                    arguments=gen_args,
                )
                return [call], None, "Dispatching panel image generation..."
            if "dispatch" in q_lower or "execute plan" in q_lower:
                m_plan = re.search(r"plan_[a-f0-9]+", user_query)
                plan_id = m_plan.group(0) if m_plan else "plan_active"
                call = ToolCall(
                    call_id="call_dispatch_01",
                    tool_id="plan.dispatch_plan",
                    arguments={"project_id": project_id, "plan_id": plan_id},
                )
                return [call], None, f"Validating and dispatching execution plan {plan_id}..."

        # Intent: IMAGE_INSPECTION
        if intent == INTENT_IMAGE_INSPECTION:
            q_lower = user_query.lower()
            target_char_id = None
            try:
                from app.agent.registry import _get_project_bible
                b_proj = _get_project_bible(project_id)
                b_chars = getattr(b_proj, "characters", {})
                for cid, cdef in b_chars.items():
                    if cid.lower() in q_lower or getattr(cdef, "name", "").lower() in q_lower:
                        target_char_id = cid
                        break
                if not target_char_id and len(b_chars) == 1:
                    target_char_id = next(iter(b_chars.keys()))
            except Exception:
                pass

            if user_attachments:
                att = user_attachments[0]
                if any(w in q_lower for w in ["visual", "compare", "consistency", "anchor", "match"]):
                    verify_args = {"attachment_id": att.get("attachment_id")}
                    if target_char_id:
                        verify_args["character_id"] = target_char_id
                    call = ToolCall(
                        call_id=f"call_verify_{att.get('attachment_id', 'att_1')}",
                        tool_id="image.verify_visual_consistency",
                        arguments=verify_args,
                    )
                    char_label = f"{target_char_id} anchor" if target_char_id else "canonical reference"
                    return [call], None, f"Verifying visual consistency of {att.get('filename', 'attachment')} against {char_label}..."
                else:
                    call = ToolCall(
                        call_id=f"call_inspect_{att.get('attachment_id', 'att_1')}",
                        tool_id="image.inspect_file_metadata",
                        arguments={"attachment_id": att.get("attachment_id")},
                    )
                    return [call], None, f"Inspecting image {att.get('filename', 'attachment')}..."

            # Text mention of canonical reference anchor image
            if "anchor" in q_lower or "reference image" in q_lower:
                anchor_args = {}
                if target_char_id:
                    anchor_args["character_id"] = target_char_id
                call = ToolCall(
                    call_id="call_inspect_anchor",
                    tool_id="canon.inspect_reference_anchor",
                    arguments=anchor_args,
                )
                char_label = f"{target_char_id} " if target_char_id else ""
                return [call], None, f"Inspecting verified {char_label}canonical reference image..."

        # Intent: CANON_QUERY
        if intent == INTENT_CANON_QUERY:
            call = ToolCall(
                call_id="call_canon_01",
                tool_id="canon.inspect_characters",
                arguments={"project_id": project_id},
            )
            return [call], None, "Inspecting active Story Bible characters and canon invariants..."

        # Intent: BUDGET_QUERY
        if intent == INTENT_BUDGET_QUERY:
            call = ToolCall(
                call_id="call_budget_01",
                tool_id="execution.get_budget_allowance",
                arguments={"project_id": project_id},
            )
            return [call], None, "Checking SQLite execution budget headroom..."

        # Intent: CANVAS_QUERY
        if intent == INTENT_CANVAS_QUERY:
            call = ToolCall(
                call_id="call_canvas_01",
                tool_id="canvas.list_templates",
                arguments={},
            )
            return [call], None, "Listing deterministic canvas layout templates..."

        # Intent: CATALOGUE_QUERY
        if intent == INTENT_CATALOGUE_QUERY:
            q_lower = user_query.lower()
            if any(w in q_lower for w in ["rule", "recipe", "retrieve", "scene"]):
                call = ToolCall(
                    call_id="call_cat_rules",
                    tool_id="catalogue.retrieve_knowledge",
                    arguments={"action": user_query},
                )
                return [call], None, "Querying 60-group image knowledge catalogue..."
            call = ToolCall(
                call_id="call_cat_01",
                tool_id="catalogue.get_summary",
                arguments={},
            )
            return [call], None, "Auditing 60-group image knowledge catalogue..."

        # Intent: ASSETS_QUERY
        if intent == INTENT_ASSETS_QUERY:
            call = ToolCall(
                call_id="call_asset_01",
                tool_id="assets.list_assets",
                arguments={"project_id": project_id},
            )
            return [call], None, "Querying registered assets from AssetRegistry..."

        # Intent: DIAGNOSTICS_QUERY
        if intent == INTENT_DIAGNOSTICS_QUERY:
            call = ToolCall(
                call_id="call_diag_01",
                tool_id="diagnostics.get_engine_readiness",
                arguments={},
            )
            return [call], None, "Evaluating specialist engine readiness inventory..."

        # Intent: GENERAL / Default
        if self.config.has_credentials and not project_context.get("offline_mode"):
            live_reply = self._call_live_model(messages, project_context)
            if live_reply:
                return None, live_reply, None

        # Contextual fallback for general queries
        clean_q = _clean_query(user_query)
        if clean_q in ("?", "help", "menu", "commands", "options"):
            reply = (
                f"I have reviewed your request for **{project_id}**. "
                "Here are the core operations you can perform:\n\n"
                "- **Inspect Canon:** 'Inspect canon anchor and mandatory attributes'\n"
                "- **Draft Sequential Plan:** 'Draft a 6-panel plan for Chapter 1 within $0.50 budget'\n"
                "- **Inspect Images:** Upload an image attachment to verify dimensions and SHA-256 integrity\n"
                "- **Generate Artwork:** 'Generate one image of character using current scene brief'\n"
                "- **Budget & Engine Health:** 'Check available budget allowance' or 'Engine readiness'"
            )
        else:
            reply = (
                f"I received your message for **{project_id}**: *\"{user_query}\"*.\n\n"
                "I am ready to help you inspect Story Bible specifications, verify character invariants against canon, "
                "draft sequential plans, generate canvas layouts, or inspect image attachments. How would you like to proceed?"
            )
        return None, reply, None

    def _synthesize_grounded_response(
        self,
        user_query: str,
        tool_results: List[ToolResult],
        project_context: Dict[str, Any],
    ) -> str:
        """Constructs an evidence-backed Markdown response from actual tool execution results."""
        sections = []

        for tr in tool_results:
            tr_status = tr.get("status") if isinstance(tr, dict) else getattr(tr, "status", "")
            tr_tool_id = tr.get("tool_id") if isinstance(tr, dict) else getattr(tr, "tool_id", "")
            tr_error = tr.get("error") if isinstance(tr, dict) else getattr(tr, "error", None)
            tr_error_code = tr.get("error_code") if isinstance(tr, dict) else getattr(tr, "error_code", None)
            tr_approval_id = tr.get("approval_id") if isinstance(tr, dict) else getattr(tr, "approval_id", None)
            tr_cost_usd = tr.get("cost_usd") if isinstance(tr, dict) else getattr(tr, "cost_usd", None)
            out = tr.get("output") if isinstance(tr, dict) else getattr(tr, "output", None)

            if tr_status == "blocked":
                sections.append(
                    f"### Tool Gate Intercepted: `{tr_tool_id}`\n"
                    f"- **Status:** `BLOCKED` ({tr_error_code or 'ERR_CAPABILITY_UNAVAILABLE'})\n"
                    f"- **Reason:** {tr_error}\n\n"
                    f"> **Roadmap Notice:** This capability is deferred in strict compliance with project invariants. "
                    f"No fake execution will be simulated. You can review approved contracts in `docs/`."
                )
            elif tr_status == "gated":
                sections.append(
                    f"### Approval Gate Intercepted: `{tr_tool_id}`\n"
                    f"- **Status:** `AWAITING HUMAN APPROVAL`\n"
                    f"- **Approval ID:** `{tr_approval_id}`\n"
                    f"- **Cost Exposure:** ${tr_cost_usd or 0.0:.4f} USD\n\n"
                    f"{tr_error}\n\n"
                    f"> Execution is held until an explicit sign-off record is approved."
                )
            elif tr_status == "failed":
                sections.append(
                    f"### Tool Execution Failure: `{tr_tool_id}`\n"
                    f"- **Error Code:** `{tr_error_code}`\n"
                    f"- **Diagnostic:** {tr_error}"
                )
            elif tr_status == "success" and out:
                if tr_tool_id == "canon.inspect_characters":
                    chars = out.get("characters", {})
                    sections.append(
                        f"### Canonical Being Profiles & Invariants (Project: `{out.get('project_id')}`)\n"
                        f"- **Cryptographic Canon Hash:** `{(out.get('canon_hash') or '')[:16]}...`\n"
                        f"- **Declared Characters:** {', '.join(chars.keys()) if chars else 'None'}"
                    )
                    for cid, cdata in chars.items():
                        invariants_str = "\n".join([f"  * {inv}" for inv in cdata.get("visual_invariants", [])])
                        attrs_str = "\n".join([
                            f"  * **{a.get('id', 'attr')}**: {a.get('text', '')} ({'Mandatory' if a.get('required') else 'Optional'})"
                            if isinstance(a, dict) else f"  * {a}"
                            for a in cdata.get("attributes", [])
                        ])
                        sections.append(
                            f"#### Being: `{cdata.get('name', cid)}` (`{cid}`)\n"
                            f"- **Declared kind and form:** {cdata.get('entity_kind') or 'unspecified'}; {cdata.get('morphology') or 'not specified'}\n"
                            f"- **Declared surface:** {cdata.get('surface_description') or 'not specified'}\n"
                            f"- **Mandatory Attributes Checklist:**\n{attrs_str or '  * None'}\n"
                            f"- **Visual Invariants:**\n{invariants_str or '  * None'}\n"
                            f"- **Declared clothing or coverings:** {', '.join(cdata.get('clothing_attributes', [])) or 'None declared'}\n"
                            f"- **Face-specific check:** {'Enabled' if cdata.get('face_check_applicable') else 'Not applicable / not enabled'}"
                        )

                elif tr_tool_id == "canon.inspect_reference_anchor":
                    sections.append(
                        f"### Verified Canonical Reference Anchor (`{out.get('character_id')}`)\n"
                        f"- **Filename:** `{out.get('filename')}`\n"
                        f"- **Geometry:** {out.get('dimensions', {}).get('width')} × {out.get('dimensions', {}).get('height')} px ({out.get('format')})\n"
                        f"- **File Size:** {out.get('byte_size')} bytes\n"
                        f"- **Cryptographic SHA-256 Digest:** `{out.get('content_sha256')}`\n"
                        f"- **Status:** Registered canonical reference anchor\n"
                        f"- **Key Invariants:**\n"
                        + "\n".join([f"  * {inv}" for inv in out.get("mandatory_invariants", [])])
                    )

                elif tr_tool_id == "plan.draft_plan":
                    steps = out.get("steps", [])
                    total_cost = sum(s.get("estimated_cost_usd", 0.0) or 0.0 for s in steps)
                    cap_val = out.get("requested_run_budget_cap_usd")
                    cap_str = f"${cap_val:.4f} USD" if cap_val is not None else "None (Uncapped)"
                    sections.append(
                        f"### Sequential Execution Plan Drafted (`{out.get('plan_id')}`)\n\n"
                        f"- **Goal:** {out.get('goal')}\n"
                        f"- **Plan Status:** `{out.get('status')}` (Draft Only — Not Dispatched)\n"
                        f"- **Total Sequential Steps:** {len(steps)} steps\n\n"
                        f"#### Authoritative Budget Bounds:\n"
                        f"- **Available Project Budget:** `${out.get('project_available_budget_usd', 0.0):.4f} USD`\n"
                        f"- **Requested Run Budget Cap:** {cap_str}\n"
                        f"- **Effective Governing Ceiling:** `${out.get('effective_run_budget_cap_usd', 0.0):.4f} USD`\n"
                        f"- **Total Plan Estimated Cost:** `${total_cost:.4f} USD`\n\n"
                        f"#### Planned Steps Breakdown:\n"
                        + "\n".join([
                            f"{idx+1}. **{s.get('title')}** (`{s.get('engine_id')}`) — Cost: ${s.get('estimated_cost_usd', 0.0) or 0.0:.2f} USD [{s.get('status')}]"
                            for idx, s in enumerate(steps)
                        ])
                        + "\n\n> **Dispatch Notice:** This plan is held in draft state. Execution requires operator confirmation."
                    )

                elif tr_tool_id == "plan.dispatch_plan":
                    sections.append(
                        f"### Plan Dispatched for Execution\n"
                        f"- **Plan ID:** `{out.get('plan_id')}`\n"
                        f"- **Status:** `{out.get('status')}`\n"
                        f"- **Steps Dispatched:** {out.get('steps_count')}\n"
                        f"- **Effective Ceiling:** `${out.get('effective_budget_cap_usd', 0.0):.4f} USD`"
                    )

                elif tr_tool_id == "image.inspect_file_metadata":
                    inspect_sec = (
                        f"### Image File Inspection Findings\n"
                        f"- **Filename:** `{out.get('filename')}`\n"
                        f"- **Geometry:** {out.get('width')} × {out.get('height')} px\n"
                        f"- **Format & Size:** `{out.get('mime_type')}` ({out.get('byte_size')} bytes)\n"
                        f"- **SHA-256 Digest:** `{out.get('content_sha256')}`\n"
                        f"- **Decompression Guard:** Passed (safe pixel limit verified)\n\n"
                        f"> *Note: This check reports deterministic structural file metadata and does not imply semantic visual understanding.*"
                    )
                    sections.append(inspect_sec)
                    if any(w in user_query.lower() for w in ["layout", "panel", "what kind", "detect", "extract", "contain", "sheet"]):
                        sections.append(
                            "#### Semantic Layout Analysis Capability Notice\n"
                            "The runtime evaluated the attached image via deterministic structural metadata inspection.\n\n"
                            "- **Format, Geometry & Hash Integrity:** Confirmed valid on-disk image bytes.\n"
                            "- **Semantic Panel Understanding:** Currently `NOT_IMPLEMENTED`. The image inspector validates physical dimensions, decompression limits, and SHA-256 integrity, but cannot infer panel geometry, panel count, or comic layout types from metadata alone.\n"
                            "- **Truthfulness Guarantee:** In strict adherence to InkLoop safety invariants, no panel layout classification or polygon geometry is fabricated."
                        )

                elif tr_tool_id == "image.verify_visual_consistency":
                    sections.append(
                        f"### Visual Verification Result (Against Canonical Anchor)\n"
                        f"- **Overall Verdict:** `{out.get('verdict')}` (Score: {out.get('overall_score', 0.0):.2f})\n"
                        f"- **Evaluation Mode:** {'Simulated/Offline' if out.get('is_simulated') else 'Live Provider'}\n"
                        f"- **L0 Structural Code:** {'PASSED' if out.get('l0_passed') else 'FAILED'}\n"
                        f"- **L1 Subject Geometry:** {'PASSED' if out.get('l1_passed') else 'FAILED'}\n"
                        f"- **Checked Attributes:** {', '.join(out.get('checked_attributes', [])) or 'None'}\n"
                        f"- **Failures:** {', '.join(out.get('failures', [])) or 'None'}"
                    )

                elif tr_tool_id == "generation.generate_image":
                    url = out.get("url") or out.get("preview_url")
                    p_id = out.get("panel_id", "Panel")
                    provider_cost = out.get("cost_usd")
                    if provider_cost is not None:
                        cost_line = f"- **Provider-reported cost:** `${provider_cost:.4f} USD`\n"
                    elif tr_cost_usd is not None:
                        cost_line = (
                            f"- **Estimated cost:** `${tr_cost_usd:.4f} USD` "
                            "(provider billing details were not returned)\n"
                        )
                    else:
                        cost_line = "- **Provider-reported cost:** Not returned\n"
                    sec = (
                        f"### Image Generation Result\n"
                        f"- **Panel ID:** `{p_id}`\n"
                        f"- **Provider Mode:** {'Simulated (Offline)' if out.get('is_simulated') else 'Live Meta Model API'}\n"
                        f"- **Duration:** {out.get('duration_seconds')}s\n"
                        f"{cost_line}"
                    )
                    if out.get("asset_id"):
                        sec += (
                            f"- **Registered Asset ID:** `{out.get('asset_id')}`\n"
                            f"- **File Path:** `{out.get('file_path')}`\n"
                            f"- **Content SHA-256:** `{(out.get('content_sha256') or '')[:16]}...`\n"
                        )
                    if url:
                        sec += f"\n![{p_id}]({url})\n"
                    style_refs = out.get("style_reference_asset_ids") or []
                    if style_refs and out.get("style_reference_image_conditioning") == "not_supported_by_configured_provider":
                        sec += (
                            "\n- **Style reference handling:** The selected style profile text was applied. "
                            "Its source pictures were not sent because this provider treats every input image "
                            "as scene content and cannot separate style from subject/layout conditioning.\n"
                        )
                    sections.append(sec)

                elif tr_tool_id == "execution.get_budget_allowance":
                    sections.append(
                        f"### Execution Budget Headroom\n"
                        f"- **Available Budget:** `${out.get('available_global_usd', 0.0):.4f} USD`\n"
                        f"- **Global Spend Cap:** `${out.get('global_cap_usd', 0.0):.4f} USD`\n"
                        f"- **Accounting Mode:** `{out.get('accounting_mode')}`"
                    )

                elif tr_tool_id == "canvas.list_templates":
                    tmpls = out.get("templates", [])
                    sections.append(
                        f"### Available Canvas Templates ({len(tmpls)} supported)\n"
                        + "\n".join([f"- `{t}`" for t in tmpls])
                    )

                elif tr_tool_id == "catalogue.retrieve_knowledge":
                    sections.append(
                        f"### Knowledge Catalogue Retrieval (T6.3)\n"
                        f"- **Selected Rules:** {out.get('selected_rules_count')} rules\n"
                        f"- **Selected Recipes:** {out.get('selected_recipes_count')} recipes\n"
                        f"- **Selection Hash:** `{out.get('knowledge_selection_hash')}`\n"
                        f"- **Catalogue Version:** `{out.get('catalogue_version')}`\n"
                        f"- **Injected Directives:**\n"
                        + "\n".join([f"  * {c}" for c in out.get("prompt_clauses", [])])
                    )

                elif tr.tool_id == "catalogue.get_summary":
                    sections.append(
                        f"### Knowledge Catalogue Summary\n"
                        f"- **Taxonomy Groups:** {out.get('total_groups')}\n"
                        f"- **Canonical Elements:** {out.get('total_canonical_elements')}\n"
                        f"- **Researched Elements:** {out.get('total_researched_elements')}"
                    )

                elif tr.tool_id == "assets.list_assets":
                    assets = out.get("assets", [])
                    sections.append(
                        f"### Registered Project Assets ({len(assets)} items)\n"
                        + "\n".join([f"- **{a.get('logical_filename', 'asset')}** (`{(a.get('content_sha256') or '')[:12]}...`)" for a in assets[:5]])
                    )

                elif tr.tool_id == "diagnostics.get_engine_readiness":
                    sections.append(
                        f"### Engine Readiness Inventory\n"
                        f"- **Implemented Engines:** {', '.join(out.get('implemented_engines', []))}\n"
                        f"- **Unimplemented Engines:** {', '.join(out.get('unimplemented_engines', []))}"
                    )

                elif tr_tool_id.startswith("editor.") or tr.tool_id.startswith("editor."):
                    t_id = tr_tool_id or tr.tool_id
                    action_name = t_id.split(".")[-1].replace("_", " ").title()
                    p_id = out.get("page_id", "Page")
                    rev = out.get("revision", out.get("new_revision", ""))
                    sec = (
                        f"### Page Editor Action: {action_name}\n"
                        f"- **Page Target:** `{p_id}`\n"
                    )
                    if rev:
                        sec += f"- **Current Immutable Revision:** `rev {rev}`\n"
                    if out.get("panel_id"):
                        sec += f"- **Panel ID:** `{out.get('panel_id')}`\n"
                    if out.get("layer_id"):
                        sec += f"- **Layer ID:** `{out.get('layer_id')}`\n"
                    if out.get("fit_mode"):
                        sec += f"- **Fit Mode:** `{out.get('fit_mode')}` (Aspect ratio preserved)\n"
                    if out.get("pages"):
                        sec += f"- **Pages Found:** {len(out['pages'])} saved pages\n" + "\n".join([f"  * `{p.get('page_id')}` (rev {p.get('revision')})" for p in out["pages"][:5]])
                    sections.append(sec)

                elif tr_tool_id == "canvas.place_panel_artwork":
                    sections.append(
                        "### Added to Canvas\n"
                        f"- **Page:** `{out.get('page_id', 'unknown')}`\n"
                        f"- **Panel:** `{out.get('panel_id', 'unknown')}`\n"
                        f"- **Saved page revision:** `rev {out.get('revision', 'unknown')}`\n"
                        f"- **Artwork asset:** `{out.get('asset_id', 'unknown')}`\n"
                    )

                else:
                    sections.append(
                        f"### Tool Result: `{tr.tool_id}`\n"
                        f"```json\n{json.dumps(out, indent=2)}\n```"
                    )

        if not sections:
            return "No tool result was produced. The requested action may not have completed; check the run trace before continuing."

        return "\n\n".join(sections)
