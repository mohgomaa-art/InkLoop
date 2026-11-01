"""Generate an evidence-oriented inventory of registered Agent tools.

Run from the repository root with ``python scripts/generate_tool_traceability.py --write``.
The live registry is the source of truth; test references are discovered from test source.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agent.registry import CapabilityRegistry, IMAGE_CHAT_TOOL_IDS  # noqa: E402


OUTPUT = ROOT / "docs" / "AGENT_TOOL_TRACEABILITY.md"


def _test_refs(tool_id: str) -> str:
    refs = []
    for path in sorted((ROOT / "backend" / "tests").glob("test_*.py")):
        try:
            if tool_id in path.read_text(encoding="utf-8"):
                refs.append(path.relative_to(ROOT).as_posix())
        except OSError:
            continue
    return ", ".join(f"`{item}`" for item in refs) or "No direct tool-ID reference found; add a focused test."


def _acceptance(tool: object) -> str:
    """Describe a meaningful, domain-specific acceptance test for one registry row."""
    domain = str(tool.domain)
    checks = {
        "assets": "verify valid bytes/hash, missing or corrupt file, and cross-project rejection; confirm no false integrity success",
        "canon": "verify stable character IDs/versions, project scope, explicit approval gates, and unchanged canon after rejection",
        "canvas": "verify persisted page mutation, stable panel/layer IDs, current revision, scope, bounds, and reload equivalence",
        "editor": "verify same saved page document, current revision, validation errors, and save/reopen preservation",
        "geometry": "verify requested panel count/reading order, bounds, overlap diagnostics, stable IDs, and deterministic repeatability",
        "generation": "verify real provider request/context/reference bytes and lineage; test credential, timeout, budget, and provider failures without fake assets",
        "inspection": "verify the inspected asset ID/project/hash and exact supported fields; reject claims beyond metadata capability",
        "verification": "verify reported checks against actual inputs; inject mismatch/provider failure and ensure unverified is never passed",
        "planning": "verify strict schema, source-grounded beats and IDs, malformed/missing fields, and no side effects before approval",
        "export": "verify selected page order/scope, decodable output format, dimensions, checksum, source lineage, and failed-export recovery",
        "lettering": "verify exact text, speaker/tail IDs, RTL/LTR/mixed shaping, overflow, persisted layer linkage, and honest font failure",
        "effects": "verify typed effect inputs, page/panel scope, saved output and compositor visibility; invalid parameters must not create assets",
        "compositor": "verify composition reads the persisted page revision and actual layer assets; compare output dimensions/hash and missing-layer failure",
        "creative": "verify source/reference provenance, draft-versus-canon separation, version lineage, and approval behavior",
        "execution": "verify budget/retry/idempotency and persisted state transitions; inject conflict/provider failure and prevent duplicate spend",
        "workspace": "verify owner/project filtering, hidden-resource rejection, and stable context resolution",
        "catalogue": "verify source-backed result provenance, license/status filters, and no unsupported claims",
        "diagnostics": "verify readiness reflects actual adapters/credentials and does not expose secret material",
        "text": "verify explicit offline/live distinction, exact source text, and no fabricated live generation",
        "future_engine": "keep unavailable until the owning engine and adapter pass a real persisted integration test; then test truthful failure and scope",
    }
    return f"For `{tool.tool_id}`: {checks.get(domain, 'verify its registered schema, actual service effect, scope/permission gate, failure path, and persisted result')}."


def render() -> str:
    registry = CapabilityRegistry()
    tools = sorted(registry.list_tools(), key=lambda tool: tool.tool_id)
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}
    chat_ids = {tool.tool_id for tool in registry.list_image_chat_tools()}
    lines = [
        "# Agent Tool Traceability Matrix",
        "",
        "Generated from the live capability registry and backend test source. Refresh with `python scripts/generate_tool_traceability.py --write` after changing tools or their exposure.",
        "",
        f"Registry snapshot: **{len(tools)} registered**, **{len(callable_ids)} callable in this environment**, **{len(chat_ids)} exposed through the image-chat catalog**. Callability can vary with explicit offline-mode configuration.",
        "",
        "A tool is not considered complete merely because a schema or adapter exists. The release gate is: correct schema, authorized scope, real service effect/result, truthful failure, and a focused regression test. The discovered test references below are evidence locations, not proof that every acceptance condition already passes.",
        "",
        "| Tool ID | Purpose / current contract | Owning service | Runtime status | Adapter / chat | Required inputs | Approval / cost / idempotency | Evidence references | Individual acceptance test / fix gate |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for tool in tools:
        status = getattr(tool.status, "value", str(tool.status))
        has_adapter = tool.tool_id in registry._adapters
        in_chat = tool.tool_id in chat_ids
        required = ", ".join(f"`{item}`" for item in tool.parameters_schema.get("required", [])) or "none declared"
        mode = "callable" if has_adapter and tool.is_callable else "no adapter"
        exposure = "chat" if in_chat else "coordinator-only/not exposed"
        refs = _test_refs(tool.tool_id)
        if status != "AVAILABLE" or not tool.is_callable or not has_adapter:
            status_note = f"{status}: currently fail-closed ({tool.status_reason or tool.purpose}); keep unavailable until real service validation passes."
        elif refs.startswith("No direct"):
            status_note = "PARTIAL: callable, but no direct tool-ID regression test was found."
        else:
            status_note = "PARTIAL: callable and referenced by tests; row-specific behavior still needs the acceptance test below before DONE_AND_VERIFIED."
        policy = f"approval={tool.requires_approval}; cost={getattr(tool.cost_semantics, 'value', tool.cost_semantics)}; idempotent={tool.is_idempotent}"
        action = _acceptance(tool)
        purpose = tool.purpose.replace("|", "\\|")
        if not in_chat and has_adapter and tool.is_callable:
            action += " Also record why this tool is internal-only or expose it only through a focused user intent."
        lines.append(
            f"| `{tool.tool_id}` | {purpose} | `{tool.owning_service}` | `{status_note}` | {mode}; {exposure} | {required} | {policy} | {refs} | {action} |"
        )
    lines += [
        "",
        "## Cross-tool release gates",
        "",
        "- Agent exposure must be derived from live callable schemas; skill documents must not advertise a tool that the active path cannot call.",
        "- Each callable row is `PARTIAL` until its individual acceptance case above passes. Missing adapters remain `NOT_IMPLEMENTED` unless an external dependency makes implementation `BLOCKED`.",
        "- Every mutation must enforce project scope, revision/concurrency, approval, and idempotency rules appropriate to its side effects.",
        "- Provider failures, missing credentials, unavailable engines, unknown usage, and incomplete verification must remain visible as such.",
        "- E4/E5/E6/E7/compositor/export transitions require deterministic unit tests plus persisted end-to-end tests. Provider-backed tests stay separate and must not use offline simulations as live evidence.",
        "- `DONE_AND_VERIFIED` is reserved for a wired implementation whose focused tests pass; code presence, a passing stub test, or an available UI control alone is insufficient.",
        "",
        "## Implementation chunk evidence (2026-10-30)",
        "",
        "- Agent discovery, skill filtering, saved-page edit, persisted lettering/composite/export pipeline, unavailable semantic analysis, and hardened legacy E5/E6/E7/compositor/export schemas: **106 passed, 1 skipped** with `python -m pytest backend/tests/test_agent_tool_discovery.py backend/tests/test_agent_downstream_tools.py backend/tests/test_agent_behavioral_acceptance.py backend/tests/test_agent_runtime.py backend/tests/test_agent_workflow_skills.py backend/tests/test_story_to_canvas_workflow.py backend/tests/test_story_to_canvas_recovery.py backend/tests/test_agent_canvas_routing.py backend/tests/test_agent_autonomous_execution.py -q`.",
        "- Dedicated legacy engine contracts: **22 passed** with `python -m pytest backend/tests/test_agent_downstream_tools.py backend/tests/test_downstream_engines.py backend/tests/test_agent_tool_discovery.py -q`.",
        "- Frontend `npm run lint`: exit 0. Frontend `npm run build`: exit 0; Vite emitted the existing >500 kB chunk-size warning.",
        "- Full backend suite (`python -m pytest backend/tests -q`): interrupted before completion after the pytest process opened outbound HTTPS. The prior session fixture set offline mode too late and did not clear inherited provider credentials. `backend/tests/conftest.py` now disables inherited model credentials before imports; the full suite was not rerun because some legacy tests mutate shared `runs/` data. The persistent-project story test is skipped unless explicitly opted into with `INKLOOP_RUN_REPO_DATA_MUTATION_TESTS=1`.",
        "- No live provider generation or live semantic vision verification is claimed. External provider integration remains separate from deterministic tests.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help=f"write {OUTPUT.relative_to(ROOT)}")
    args = parser.parse_args()
    report = render()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(report, encoding="utf-8")
        print(f"Wrote {OUTPUT}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
