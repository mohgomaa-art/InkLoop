"""Create a resumable one-page, six-panel Muse story through registered tools."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agent.registry import CapabilityRegistry  # noqa: E402
from app.agent.schemas import ToolCall  # noqa: E402
from app.api.routers.execution import get_execution_manager  # noqa: E402
from app.api.routers.editor import get_page_store  # noqa: E402
from app.config import InkLoopConfig  # noqa: E402
from app.creative.storage import get_creative_profile_store  # noqa: E402


PROJECT_ID = "default_project"
CHARACTER_ID = "muse"
STYLE_PROFILE_ID = "quick_medical_editorial_gouache"
SCENE_ID = "muse_morning_seedling"
JOB_ID = "quick_story_muse_morning_seedling"
JOB_PATH = ROOT / "runs" / "quick_story_jobs" / f"{JOB_ID}.json"
PAGE_ID = "page_muse_morning_seedling"
TITLE = "Muse and the Morning Seedling"
ENVIRONMENT = (
    "A small sunlit hillside clinic with whitewashed rounded walls, a wooden door, "
    "a bright window and a small terracotta plant pot; keep the place coherent across panels. "
    "Only Muse is a character; no other people, animals, or creatures."
)
BEATS = [
    ("establishing", "Muse opens the hillside clinic door as the first morning sun reaches the porch.", "Muse at the clinic doorway with the quiet hillside beyond"),
    ("reaction", "Muse notices a small potted seedling drooping beside the porch; its soil is dry and its leaves curl.", "Muse looking toward the wilted seedling"),
    ("detail", "Muse gently checks the seedling's dry soil with one paw.", "Muse's paw beside the dry soil and curled leaves"),
    ("action_continuation", "Muse carefully waters the seedling with a small watering can.", "a gentle stream soaking the soil as Muse tends the pot"),
    ("reveal", "A cloud moves aside and a new leaf lifts toward a warm sunbeam.", "the first fresh leaf rising into warm light"),
    ("aftermath", "Muse sets the revived seedling by the bright clinic window and smiles softly.", "Muse and the healthy seedling in the sunlit window"),
]


def load_job() -> dict:
    if JOB_PATH.exists():
        return json.loads(JOB_PATH.read_text(encoding="utf-8"))
    return {
        "job_id": JOB_ID,
        "project_id": PROJECT_ID,
        "title": TITLE,
        "status": "planning",
        "scene_id": SCENE_ID,
        "page_id": PAGE_ID,
        "selected_character_ids": [CHARACTER_ID],
        "style_profile_id": STYLE_PROFILE_ID,
        "style_profile_version": None,
        "calls": [],
        "panels": {},
    }


def save_job(job: dict) -> None:
    JOB_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = JOB_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(JOB_PATH)


def call_tool(registry, tool_id: str, call_id: str, arguments: dict, context: dict) -> dict:
    result = registry.dispatch(
        ToolCall(call_id=call_id, tool_id=tool_id, arguments=arguments), context
    )
    event = {
        "call_id": result.call_id,
        "tool_id": result.tool_id,
        "status": result.status.value if hasattr(result.status, "value") else str(result.status),
        "error_code": result.error_code,
        "error": result.error,
        "output": result.output,
        "cost_usd": result.cost_usd,
        "duration_seconds": result.duration_seconds,
    }
    print(
        f"{event['tool_id']} - {event['status']} - {event['duration_seconds']:.2f}s"
        + (f" - {event['error_code']}: {event['error']}" if event["error"] else ""),
        flush=True,
    )
    return event


def finish_or_fail(event: dict, job: dict) -> bool:
    job["calls"].append(event)
    if event["status"] != "success":
        job["status"] = "needs_attention"
        job["error"] = {"tool_id": event["tool_id"], "code": event["error_code"], "message": event["error"]}
        save_job(job)
        print(json.dumps({"failed": job["error"]}, ensure_ascii=False))
        return False
    save_job(job)
    return True


def panel_dimensions(slot) -> tuple[int, int]:
    ratio = slot.rect.width / slot.rect.height
    if ratio > 1.25:
        return 1024, 768
    if ratio < 0.8:
        return 768, 1024
    return 768, 768


def main() -> int:
    config = InkLoopConfig.load()
    if not config.has_credentials:
        print("Provider credentials are unavailable; no image work was attempted.")
        return 2

    registry = CapabilityRegistry.get_instance()
    context = {"project_id": PROJECT_ID, "offline_mode": False, "selected_character_ids": [CHARACTER_ID]}
    job = load_job()

    if job.get("status") == "completed":
        print(json.dumps({"status": "already_completed", "job_id": JOB_ID, "page_id": job["page_id"], "revision": job["revision"], "panels": job["panels"]}, ensure_ascii=False))
        return 0

    character_call = call_tool(registry, "canon.inspect_characters", f"{JOB_ID}-inspect-character", {"project_id": PROJECT_ID}, context)
    if not finish_or_fail(character_call, job):
        return 1
    character = character_call["output"].get("characters", {}).get(CHARACTER_ID)
    if not character or not character.get("has_reference_anchor"):
        job["status"] = "needs_attention"
        job["error"] = {"code": "ERR_MUSE_REFERENCE_MISSING", "message": "Muse is not available with a canonical reference in this project."}
        save_job(job)
        print(json.dumps({"failed": job["error"]}, ensure_ascii=False))
        return 1
    job["character_anchor_asset_id"] = character.get("anchor_asset_id")

    anchor_call = call_tool(registry, "canon.inspect_reference_anchor", f"{JOB_ID}-inspect-anchor", {"project_id": PROJECT_ID, "character_id": CHARACTER_ID}, context)
    if not finish_or_fail(anchor_call, job):
        return 1
    job["character_anchor_sha256"] = anchor_call["output"]["content_sha256"]

    profile = get_creative_profile_store().get_style_profile(PROJECT_ID, STYLE_PROFILE_ID)
    if profile:
        job["style_profile_version"] = profile.version
    else:
        job["style_profile_id"] = None
        job["style_profile_version"] = None
    job["status"] = "planning"
    save_job(job)

    if not job.get("plan"):
        request = {
            "project_id": PROJECT_ID,
            "scene_id": SCENE_ID,
            "scene_summary": "A quiet clinic morning becomes a small act of care when Muse helps a wilted seedling recover.",
            "reading_direction": "ltr",
            "beats": [{
                "beat_id": f"beat_{index:02d}",
                "panel_id": f"panel_{index:02d}",
                "narrative_function": function,
                "story_event": story_event,
                "reader_takeaway": story_event,
                "character_ids": [CHARACTER_ID],
                "environment": ENVIRONMENT,
                "visual_focus": focus,
                "emotional_intent": "gentle concern turning into quiet hope",
                "text": {"content_kind": "none", "carrier": "none"},
            } for index, (function, story_event, focus) in enumerate(BEATS, 1)],
        }
        event = call_tool(registry, "planning.plan_panels", f"{JOB_ID}-plan", request, context)
        if not finish_or_fail(event, job):
            return 1
        job["plan"] = event["output"]
        job["status"] = "awaiting_review"
        save_job(job)

    page_store = get_page_store()
    try:
        page = page_store.get(job["page_id"])
    except Exception:
        page = None
    if page is None:
        event = call_tool(registry, "canvas.create_page_from_template", f"{JOB_ID}-create-page", {
            "project_id": PROJECT_ID,
            "page_id": job["page_id"],
            "layout_template": "six_panel_classic",
            "reading_direction": "ltr",
            "page_format": "custom",
            "width_px": 1200,
            "height_px": 1800,
            "panel_plans": job["plan"]["plans"],
        }, context)
        if not finish_or_fail(event, job):
            return 1
        job["revision"] = event["output"]["revision"]
        job["layout"] = event["output"]
        job["status"] = "generating"
        save_job(job)
        page = page_store.get(job["page_id"])
    else:
        job["revision"] = page.revision

    estimated_per_image = float(registry.get_tool("generation.generate_image").estimated_cost_usd or 0)
    estimated_total = estimated_per_image * sum(1 for panel in job["plan"]["plans"] if not job["panels"].get(panel["panel_id"], {}).get("asset_id"))
    available = float(get_execution_manager().budget_manager.get_available_budget())
    if estimated_total > available:
        job["status"] = "needs_attention"
        job["error"] = {"code": "ERR_BUDGET_EXCEEDED", "message": f"Estimated remaining image cost ${estimated_total:.2f} exceeds available budget ${available:.2f}."}
        save_job(job)
        print(json.dumps({"failed": job["error"]}, ensure_ascii=False))
        return 1

    job["estimated_remaining_cost_usd"] = estimated_total
    job["status"] = "generating"
    save_job(job)
    previous_summary = None
    for plan in job["plan"]["plans"]:
        panel_id = plan["panel_id"]
        panel_state = job["panels"].setdefault(panel_id, {})
        if panel_state.get("placed"):
            previous_summary = plan["story_event"]
            continue

        if not panel_state.get("asset_id"):
            slot = page.layout.get_panel(panel_id)
            width, height = panel_dimensions(slot)
            prompt = (
                f"Illustrate this as one comic panel for '{TITLE}'. {plan['story_event']} "
                f"Visual focus: {plan['visual_focus']}. Setting: {plan.get('environment')}. "
                "Use the selected Muse character reference and keep exactly Muse as the only character. "
                "The seedling is a plant, not another character. No text or extra subjects."
            )
            arguments = {
                "project_id": PROJECT_ID,
                "prompt": prompt,
                "panel_id": panel_id,
                "scene_id": SCENE_ID,
                "scene_title": TITLE,
                "scene_index": plan["reading_order_index"] - 1,
                "shot_type": plan["shot_type"],
                "character_ids": [CHARACTER_ID],
                "panel_plan": plan,
                "width": width,
                "height": height,
            }
            if previous_summary:
                arguments["previous_panel_summary"] = previous_summary
            if profile:
                arguments["style_profile_id"] = profile.profile_id
                arguments["style_profile_version"] = profile.version
            call_id = f"{JOB_ID}-generate-{panel_id}"
            event = call_tool(registry, "generation.generate_image", call_id, arguments, context)
            if not finish_or_fail(event, job):
                return 1
            output = event["output"]
            if output.get("is_simulated") is not False or not output.get("asset_id"):
                job["status"] = "needs_attention"
                job["error"] = {"code": "ERR_NOT_LIVE_GENERATION", "message": "The provider did not return a live registered image; stopping without a fake success."}
                save_job(job)
                print(json.dumps({"failed": job["error"]}, ensure_ascii=False))
                return 1
            panel_state.update({"asset_id": output["asset_id"], "generation_context_fingerprint": output.get("context_fingerprint")})
            save_job(job)

        place_event = call_tool(registry, "canvas.place_panel_artwork", f"{JOB_ID}-place-{panel_id}", {
            "page_id": job["page_id"],
            "expected_revision": job["revision"],
            "panel_id": panel_id,
            "asset_id": panel_state["asset_id"],
            "fit_mode": "cover",
        }, context)
        if not finish_or_fail(place_event, job):
            return 1
        job["revision"] = place_event["output"]["revision"]
        panel_state["placed"] = True
        panel_state["page_revision"] = job["revision"]
        previous_summary = plan["story_event"]
        save_job(job)

    job["status"] = "completed"
    job.pop("error", None)
    save_job(job)
    print(json.dumps({
        "status": job["status"],
        "job_id": JOB_ID,
        "title": TITLE,
        "project_id": PROJECT_ID,
        "page_id": job["page_id"],
        "revision": job["revision"],
        "panels": job["panels"],
        "estimated_cost_usd": round(estimated_total, 2),
        "trace_file": str(JOB_PATH.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
