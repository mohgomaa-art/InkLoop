"""Generate real, idempotent Agent quick-style previews using InkLoop's E1 tool."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.agent.registry import CapabilityRegistry, _get_asset_registry  # noqa: E402
from app.agent.schemas import ToolCall  # noqa: E402
from app.api.routers.creative import apply_quick_style_template  # noqa: E402
from app.config import InkLoopConfig  # noqa: E402
from app.creative.quick_styles import QUICK_STYLE_SAMPLE_PROMPT, QUICK_STYLE_TEMPLATES  # noqa: E402
from app.api.routers.execution import get_execution_manager  # noqa: E402
from app.storage.models import AssetFilter  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DIR = ROOT / "frontend" / "public" / "quick-style-previews"
MANIFEST_PATH = PREVIEW_DIR / "manifest.json"
PROJECT_ID = "quick_style_preview_lab"


def read_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"schema_version": "inkloop.quick-style-preview-manifest/1.0.0", "previews": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(MANIFEST_PATH)


def register_preview(asset_id: str, template, profile, provider: str, estimated_cost: float | None) -> dict:
    from PIL import Image
    asset = _get_asset_registry().resolve_asset(asset_id, verify_integrity=True)
    if asset.metadata.extra_metadata.get("is_simulated") is not False:
        raise RuntimeError(f"Refusing to publish non-live preview asset {asset_id}.")
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    webp_path = PREVIEW_DIR / f"{template.template_id}.webp"
    im = Image.open(asset.absolute_path)
    im.save(webp_path, "WEBP", quality=90)
    suffix = asset.absolute_path.suffix.lower() or ".png"
    if suffix != ".webp":
        shutil.copyfile(asset.absolute_path, PREVIEW_DIR / f"{template.template_id}{suffix}")
    return {
        "template_id": template.template_id,
        "template_version": template.version,
        "schema_version": template.version,
        "status": "generated",
        "asset_id": asset_id,
        "preview_url": f"/quick-style-previews/{template.template_id}.webp",
        "provider": provider,
        "prompt": QUICK_STYLE_SAMPLE_PROMPT,
        "style_profile_id": profile.profile_id,
        "style_profile_version": profile.version,
        "estimated_cost_usd": estimated_cost,
        "is_simulated": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Maximum previews to generate in this run")
    parser.add_argument("--force", action="store_true", help="Force regenerate all previews using live Meta API")
    args = parser.parse_args()

    config = InkLoopConfig.load()
    if not config.has_credentials:
        print("BLOCKED: configured image provider credentials are missing; no preview was generated.")
        return 2

    registry = CapabilityRegistry.get_instance()
    definition = registry.get_tool("generation.generate_image")
    if not definition or not registry._adapters.get("generation.generate_image"):
        print("BLOCKED: generation.generate_image is unavailable or has no execution adapter.")
        return 2

    char_ref_id = "art_preview_char_muse_reference"
    uploaded_char_path = ROOT / "runs" / "artifact_store" / "objects" / "94" / "94725b3ed3c46857cbd4be2d09303e306cf6700dc902c54f12e2e91f42eaa88b.png"
    if not uploaded_char_path.exists():
        uploaded_char_path = ROOT / "runs" / "m0_visual" / "reference" / "nour_reference.png"

    asset_reg = _get_asset_registry()
    if not asset_reg.get_asset(char_ref_id):
        from app.contracts.artifacts import AssetType, LifecycleStatus
        asset_reg.register_file(
            file_path=uploaded_char_path,
            project_id=PROJECT_ID,
            asset_type=AssetType.IMAGE_REFERENCE,
            asset_id=char_ref_id,
            name="muse_character_reference",
            lifecycle_status=LifecycleStatus.APPROVED,
            extra_metadata={"is_simulated": False, "character_name": "Muse"},
        )

    manifest = read_manifest()
    registered_assets = _get_asset_registry().list_assets(AssetFilter(project_id=PROJECT_ID))
    remaining = max(0, args.limit)
    results: list[dict] = []
    for template in QUICK_STYLE_TEMPLATES:
        previous = manifest["previews"].get(template.template_id)
        image_path = PREVIEW_DIR / f"{template.template_id}.png"
        if not args.force and previous and previous.get("asset_id") and (image_path.is_file() or list(PREVIEW_DIR.glob(f"{template.template_id}.*"))):
            asset = _get_asset_registry().resolve_asset(previous["asset_id"], verify_integrity=True)
            if asset.metadata.extra_metadata.get("is_simulated") is False:
                profile = apply_quick_style_template(PROJECT_ID, template.template_id)
                previous.update({
                    "template_version": template.version,
                    "schema_version": template.version,
                    "status": "generated",
                    "is_simulated": False,
                    "provider": config.muse_image_model,
                    "prompt": QUICK_STYLE_SAMPLE_PROMPT,
                    "style_profile_id": profile.profile_id,
                    "style_profile_version": profile.version,
                    "estimated_cost_usd": float(definition.estimated_cost_usd or 0),
                })
                write_manifest(manifest)
                results.append({"template_id": template.template_id, "status": "already_generated", "asset_id": previous["asset_id"]})
                continue
            previous["status"] = "blocked_simulated_output"
            previous["error"] = "Registered asset is simulated; it cannot be shown as a real style preview."
            write_manifest(manifest)
            results.append({"template_id": template.template_id, "status": "blocked_simulated_output", "asset_id": previous["asset_id"]})
            continue
        if remaining == 0:
            results.append({"template_id": template.template_id, "status": "not_attempted_limit"})
            continue

        estimate = float(definition.estimated_cost_usd or 0)
        available = float(get_execution_manager().budget_manager.get_available_budget())
        if estimate > available:
            failure = {"template_id": template.template_id, "status": "blocked_budget", "estimated_cost_usd": estimate, "available_budget_usd": available}
            results.append(failure)
            manifest["previews"][template.template_id] = failure
            write_manifest(manifest)
            continue

        profile = apply_quick_style_template(PROJECT_ID, template.template_id)
        if not args.force:
            existing_asset = next((
                item for item in reversed(registered_assets)
                if item.extra_metadata.get("quick_style_template_id") == template.template_id
                and item.extra_metadata.get("style_profile_id") == profile.profile_id
            ), None)
            if existing_asset:
                entry = register_preview(
                    existing_asset.asset_id, template, profile, config.muse_image_model,
                    float(definition.estimated_cost_usd or 0),
                )
                results.append({"template_id": template.template_id, "status": "recovered_registered_output", "asset_id": existing_asset.asset_id})
                manifest["previews"][template.template_id] = entry
                write_manifest(manifest)
                continue
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting generation for quick style: {template.template_id} ({template.name})...", flush=True)
        call_id = f"quick-style-preview-{template.template_id}"
        result = registry.dispatch(
            ToolCall(
                call_id=call_id,
                tool_id="generation.generate_image",
                arguments={
                    "project_id": PROJECT_ID,
                    "prompt": QUICK_STYLE_SAMPLE_PROMPT,
                    "panel_id": f"preview_{template.template_id}",
                    "scene_id": "shared_quick_style_sample_scene",
                    "scene_title": "Shared quick style preview brief",
                    "shot_type": "full-body character study, centered eye-level composition",
                    "width": 768,
                    "height": 768,
                    "style_profile_id": profile.profile_id,
                    "style_profile_version": profile.version,
                    "reference_asset_id": char_ref_id,
                },
            ),
            {
                "project_id": PROJECT_ID,
                "offline_mode": False,
                "quick_style_preview_generation": True,
            },
        )
        remaining -= 1
        if (
            result.status != "success" or not result.output
            or not result.output.get("asset_id") or result.output.get("is_simulated") is not False
        ):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED for {template.template_id}: {result.error}", flush=True)
            entry = {
                "template_id": template.template_id,
                "template_version": template.version,
                "status": result.status,
                "error_code": result.error_code,
                "error": result.error or "Provider returned a simulated or incomplete result; refusing to present it as a real preview.",
                "provider": config.muse_image_model,
                "prompt": QUICK_STYLE_SAMPLE_PROMPT,
                "attempted_at": datetime.now(timezone.utc).isoformat(),
            }
            results.append(entry)
            manifest["previews"][template.template_id] = entry
            write_manifest(manifest)
            continue

        asset_id = result.output["asset_id"]
        entry = register_preview(asset_id, template, profile, config.muse_image_model, result.cost_usd)
        entry["is_simulated"] = False
        results.append(entry)
        manifest["previews"][template.template_id] = entry
        write_manifest(manifest)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS for {template.template_id}: {asset_id}", flush=True)

    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
