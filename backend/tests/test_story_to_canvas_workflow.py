from __future__ import annotations

from types import SimpleNamespace
import pytest

from app.agent.production import (
    PanelProduction, StoryProductionJob, corrected_character_ids, group_panels,
    production_action_requested, selected_cast_repair_requested,
)
from app.agent.schemas import AgentSession, ToolCall, ToolResult
from app.agent.story_to_canvas import StoryToCanvasWorkflow
from app.editor.models import LayerKind


class _SessionStore:
    def save_session(self, _session):
        return None


class _ExecutionManager:
    class _DB:
        @staticmethod
        def get_run(_run_id):
            return None

    db = _DB()

    @staticmethod
    def create_run(**_kwargs):
        return None

    @staticmethod
    def complete_run(_run_id):
        return None

    @staticmethod
    def mark_run_needs_review(*_args, **_kwargs):
        return None


class _AssetRegistry:
    def resolve_asset(self, _asset_id, verify_integrity=True):
        assert verify_integrity is True
        return SimpleNamespace(metadata=SimpleNamespace(project_id="real_one_6675e532"))


def _char(name, ref_id):
    return SimpleNamespace(
        name=name,
        canon_version=1,
        version=1,
        reference_assets=[SimpleNamespace(asset_id=ref_id)],
    )


def _approved_plan():
    protagonist_old_id = "char_mvuehfe4"  # Incorrect role ID in the traced plan.
    muse_old_id = "char_mvued66u"  # Incorrect role ID in the traced plan.
    plans = []
    for index in range(1, 13):
        if index <= 9:
            cast = [protagonist_old_id]
        elif index <= 11:
            cast = [protagonist_old_id, muse_old_id]
        else:
            cast = []
        text = {"carrier": "none", "text_content": "", "speaker_id": None}
        if index == 2:
            text = {"carrier": "speech_bubble", "text_content": "I found the hackathon.", "speaker_id": protagonist_old_id}
        elif index == 10:
            text = {"carrier": "speech_bubble", "text_content": "Shortlisted is not winning.", "speaker_id": muse_old_id}
        elif index == 12:
            text = {
                "carrier": "caption",
                "text_content": "You didn't win $150. You got $150 worth of opportunity. Now prove what you can build with it.",
                "speaker_id": None,
            }
        plans.append({
            "panel_id": f"p{index}",
            "scene_id": "ch1_part_one_12panel",
            "reading_order_index": index,
            "story_event": f"Approved beat {index}",
            "image_brief": f"Approved visual beat {index}",
            "character_ids": cast,
            "text": text,
        })
    return plans


def _valid_output(panel_id, character_ids, style, location, characters):
    reference_ids = [
        ref.asset_id
        for character_id in character_ids
        for ref in characters[character_id].reference_assets
    ]
    return {
        "panel_id": panel_id,
        "asset_id": f"art_{panel_id}",
        "content_sha256": f"hash_{panel_id}",
        "character_ids": list(character_ids),
        "character_versions": {character_id: 1 for character_id in character_ids},
        "character_reference_asset_ids": reference_ids,
        "reference_image_roles": [
            {"asset_id": ref_id, "role": "character_reference", "character_id": character_id}
            for character_id in character_ids
            for ref_id in [next(ref.asset_id for ref in characters[character_id].reference_assets)]
        ],
        "style_profile_id": style["profile_id"],
        "style_profile_version": style["version"],
        "style_reference_asset_ids": style["reference_asset_ids"],
        "location_id": location["location_id"],
        "location_version": location["version"],
        "is_simulated": False,
    }


def test_traced_twelve_panel_story_resumes_into_two_real_pages_with_text_and_retry(monkeypatch):
    monkeypatch.setattr("app.api.routers.assets.get_registry", lambda: _AssetRegistry())

    canon = {
        "char_mvued66u": _char("Gomaa", "gomaa_ref"),
        "char_mvuehfe4": _char("Muse", "muse_ref"),
    }
    style = {"profile_id": "style_approved", "version": 3, "reference_asset_ids": ["style_ref"]}
    location = {"location_id": "workshop", "version": 2}
    old_role_text = "- `char_mvuehfe4` — Protagonist\n- `char_mvued66u` — Muse\n\nCaption:\n\nYou didn't win $150. You got $150 worth of opportunity. Now prove what you can build with it."
    raw_plans = _approved_plan()
    corrected, corrections = corrected_character_ids(raw_plans, [old_role_text], canon)
    assert corrections == {"char_mvuehfe4": "char_mvued66u", "char_mvued66u": "char_mvuehfe4"}
    assert corrected[0]["character_ids"] == ["char_mvued66u"]
    assert corrected[9]["character_ids"] == ["char_mvued66u", "char_mvuehfe4"]
    assert corrected[9]["text"]["speaker_id"] == "char_mvuehfe4"
    assert len(group_panels(corrected, ["2 pages, 6 panels per page"])) == 2

    # The prior run had 11 successful compatible outputs. The only remaining
    # panel then hits one transient provider error during resume.
    prior_calls = []
    prior_results = []
    for index in [*range(1, 10), 11, 12]:
        plan = corrected[index - 1]
        output = _valid_output(plan["panel_id"], plan["character_ids"], style, location, canon)
        call_id = f"old_gen_{plan['panel_id']}"
        prior_calls.append(ToolCall(call_id=call_id, tool_id="generation.generate_image", arguments={"panel_id": plan["panel_id"]}))
        prior_results.append(ToolResult(call_id=call_id, tool_id="generation.generate_image", status="success", output=output))
    class _CanvasAndGenerationRegistry:
        def __init__(self):
            self.calls = []
            self.pages = {}
            self.revision = 1
            self.p10_attempts = 0
            self.tools = [SimpleNamespace(tool_id=tool_id) for tool_id in (
                "generation.generate_image", "canvas.create_page_from_template", "canvas.create_custom_page",
                "canvas.place_panel_artwork", "canvas.add_speech_bubble",
                "editor.add_text_layer", "canvas.verify_page", "canvas.inspect_page_spacing",
            )]

        def list_tools(self, callable_only=False):
            assert callable_only is True
            return self.tools

        def get_tool(self, tool_id):
            assert tool_id == "generation.generate_image"
            return SimpleNamespace(estimated_cost_usd=0.01)

        def _editor_page(self, page_id, _context):
            return None, self.pages[page_id]

        def dispatch(self, call, context):
            self.calls.append(call)
            args = call.arguments
            if call.tool_id in {"canvas.create_page_from_template", "canvas.create_custom_page"}:
                panel_ids = (
                    [item["panel_id"] for item in args["panel_geometry"]]
                    if call.tool_id == "canvas.create_custom_page"
                    else args["template_parameters"]["panel_ids"]
                )
                assert [plan["reading_order_index"] for plan in args["panel_plans"]] == list(range(1, 7))
                assert [plan["panel_id"] for plan in args["panel_plans"]] == panel_ids
                if call.tool_id == "canvas.create_custom_page":
                    assert len(args["panel_geometry"]) == 6
                    assert all(item.get("rect") or item.get("polygon") for item in args["panel_geometry"])
                # Workflow consumers only need stable slots, reading order and
                # revision here; the real adapter/editor are covered elsewhere.
                slots = {
                    panel_id: SimpleNamespace(rect=SimpleNamespace(x=10, y=10, width=300, height=240))
                    for panel_id in panel_ids
                }
                layout = SimpleNamespace(
                    get_panel=lambda panel_id: slots.get(panel_id),
                    reading_order_panel_ids=panel_ids,
                )
                page = SimpleNamespace(
                    page_id=args["page_id"], project_id="real_one_6675e532", revision=self.revision,
                    layout=layout, layers=[],
                )
                self.pages[page.page_id] = page
                output = {"page_id": page.page_id, "revision": page.revision, "panel_ids": panel_ids}
            elif call.tool_id == "canvas.inspect_page_spacing":
                page = self.pages[args["page_id"]]
                panel_ids = page.layout.reading_order_panel_ids
                output = {
                    "page_id": page.page_id,
                    "minimum_edge_gap_px": 18.0,
                    "overlapping_panel_pairs": [],
                    "margin_clearance_valid": True,
                    "panels": [
                        {"panel_id": panel_id, "measured_margins_px": {"top": 45, "right": 45, "bottom": 45, "left": 45}, "margin_clearance_valid": True}
                        for panel_id in panel_ids
                    ],
                }
            elif call.tool_id == "generation.generate_image":
                panel_id = args["panel_id"]
                if panel_id == "p10":
                    self.p10_attempts += 1
                    if self.p10_attempts == 1:
                        return ToolResult(
                            call_id=call.call_id, tool_id=call.tool_id, status="failed",
                            error="The image generation service is temporarily unavailable. Please try again.",
                            error_code="ERR_IMAGE_GENERATION_FAILED",
                        )
                character_ids = list(args["character_ids"])
                output = _valid_output(panel_id, character_ids, style, location, canon)
            elif call.tool_id == "canvas.place_panel_artwork":
                page = self.pages[args["page_id"]]
                self.revision += 1
                page.revision = self.revision
                page.layers.append(SimpleNamespace(
                    layer_id=f"image_{args['panel_id']}", kind=LayerKind.IMAGE,
                    panel_id=args["panel_id"], source_asset_id=args["asset_id"], metadata={},
                ))
                output = {"page_id": page.page_id, "panel_id": args["panel_id"], "layer_id": f"image_{args['panel_id']}", "revision": page.revision}
            elif call.tool_id in {"canvas.add_speech_bubble", "editor.add_text_layer"}:
                page = self.pages[args["page_id"]]
                self.revision += 1
                page.revision = self.revision
                page.layers.append(SimpleNamespace(
                    layer_id=args["layer_id"], kind=LayerKind.TEXT, panel_id=args["panel_id"],
                    source_asset_id=None,
                    metadata={"text": args["text"], "speaker_character_id": args.get("speaker_character_id")},
                ))
                output = {"page_id": page.page_id, "layer_id": args["layer_id"], "revision": page.revision}
            elif call.tool_id == "canvas.verify_page":
                page = self.pages[args["page_id"]]
                actual_texts = {(layer.panel_id, layer.metadata.get("text"), layer.metadata.get("speaker_character_id")) for layer in page.layers if layer.kind == LayerKind.TEXT}
                expected_texts = args["expected_texts"]
                assert all((item["panel_id"], item["text"], item.get("speaker_character_id")) in actual_texts for item in expected_texts)
                output = {
                    "page_id": page.page_id, "revision": page.revision, "passed": True,
                    "failures": [], "visual_verification": "not_run",
                    "reading_order_panel_ids": page.layout.reading_order_panel_ids,
                }
            else:
                raise AssertionError(f"Unexpected workflow tool {call.tool_id}")
            return ToolResult(call_id=call.call_id, tool_id=call.tool_id, status="success", output=output)

    registry = _CanvasAndGenerationRegistry()
    session = AgentSession(project_id="real_one_6675e532", session_id="trace_run")
    workflow = StoryToCanvasWorkflow(
        registry=registry, session_store=_SessionStore(), session=session,
        project_id="real_one_6675e532",
        plan_result=ToolResult(
            call_id="approved_12_panel_plan", tool_id="planning.plan_panels", status="success",
            output={"plans": raw_plans, "reading_direction": "ltr"},
        ),
        plan_call_id="approved_12_panel_plan", source_request_message_id="approved_request",
        request_texts=[old_role_text, "2 pages, 6 panels per page"],
        selected_character_ids=["char_mvuehfe4"], selected_style_profile=style,
        selected_location=location, canonical_characters=canon,
        execution_manager=_ExecutionManager(), effective_budget_usd=1.0,
        offline_mode=False,
    )

    job, _summary = workflow.run(prior_results, prior_calls)

    assert job.status == "completed", f"errors={job.errors}; panels={[(key, panel.status, panel.error) for key, panel in job.panels.items()]}; pages={[(page.status, page.verification) for page in job.pages]}; text={[(plan['panel_id'], plan.get('text')) for plan in job.plan['plans'] if plan.get('text', {}).get('carrier') not in ('none', '')]}"
    assert job.target_page_count == 2
    assert job.page_panel_counts == {"1": 6, "2": 6}
    assert "verify each saved page" in job.goal
    assert len(job.pages) == 2
    assert all(page.verification["spacing_valid"] for page in job.pages)
    assert sum(call.tool_id == "canvas.inspect_page_spacing" for call in registry.calls) == 2
    assert [len(page.panel_ids) for page in job.pages] == [6, 6]
    assert all(page.status == "assembled" and page.revision for page in job.pages)
    assert all(panel.status == "placed" for panel in job.panels.values())
    generation_calls = [call for call in registry.calls if call.tool_id == "generation.generate_image"]
    # p12's older receipt omitted the creator-selected cast, so it must not be
    # reused after the planner began inheriting selected characters by default.
    assert [call.arguments["panel_id"] for call in generation_calls] == ["p10", "p10", "p12"]
    assert generation_calls[0].arguments["character_ids"] == ["char_mvued66u", "char_mvuehfe4"]
    assert registry.p10_attempts == 2
    assert sum(result.status == "success" for result in prior_results) == 11
    assert job.panels["p2"].character_ids == ["char_mvued66u"]
    assert job.panels["p10"].character_ids == ["char_mvued66u", "char_mvuehfe4"]
    assert job.plan["plans"][9]["text"]["speaker_id"] == "char_mvuehfe4"
    assert any(call.arguments.get("text") == "You didn't win $150. You got $150 worth of opportunity. Now prove what you can build with it." for call in registry.calls if call.tool_id == "editor.add_text_layer")
    assert any(call.tool_id == "canvas.verify_page" for call in registry.calls)

    calls_after_completion = len(registry.calls)
    restarted_workflow = StoryToCanvasWorkflow(
        registry=registry, session_store=_SessionStore(), session=session,
        project_id="real_one_6675e532",
        plan_result=workflow.plan_result, plan_call_id="approved_12_panel_plan",
        source_request_message_id="approved_request", request_texts=[old_role_text],
        selected_character_ids=[], selected_style_profile=None, selected_location=None,
        canonical_characters=canon, execution_manager=_ExecutionManager(),
        effective_budget_usd=1.0, offline_mode=False,
    )
    resumed, _ = restarted_workflow.run([], [])
    assert resumed.status == "completed"
    assert len(registry.calls) == calls_after_completion


def test_story_action_routes_retry_and_canonical_id_corrections_include_inline_code():
    assert production_action_requested("add to canvas")
    assert production_action_requested("Retry panel p10")
    assert production_action_requested("Retry panel_01_02")
    assert production_action_requested("Regenerate panels missing selected character references")
    assert selected_cast_repair_requested("Fix the saved selected-character mismatch by regenerating panels")
    assert not selected_cast_repair_requested("Make panels")
    canon = {"char_gomaa": {"name": "Gomaa"}, "char_muse": {"name": "Muse"}}
    plans, corrections = corrected_character_ids(
        [{"panel_id": "p1", "character_ids": ["char_wrong"], "text": {"speaker_id": "char_wrong"}}],
        ["`char_wrong` — Protagonist"], canon,
    )
    assert corrections == {"char_wrong": "char_gomaa"}
    assert plans[0]["character_ids"] == ["char_gomaa"]
    assert plans[0]["text"]["speaker_id"] == "char_gomaa"


def test_unselected_panel_cast_stops_before_canvas_page_or_generation_mutation():
    class _NoMutationRegistry:
        def __init__(self):
            self.calls = []

        def dispatch(self, call, _context):
            self.calls.append(call)
            raise AssertionError("Cast scope must be checked before any Canvas or image tool dispatch.")

    registry = _NoMutationRegistry()
    session = AgentSession(project_id="real_one_6675e532", session_id="unselected_cast")
    workflow = StoryToCanvasWorkflow(
        registry=registry,
        session_store=_SessionStore(),
        session=session,
        project_id="real_one_6675e532",
        plan_result=ToolResult(
            call_id="plan_unselected_cast",
            tool_id="planning.plan_panels",
            status="success",
            output={"project_id": "real_one_6675e532", "scene_id": "clinic", "plans": [{
                "panel_id": "panel_01",
                "scene_id": "clinic",
                "reading_order_index": 1,
                "story_event": "Nour arrives at the clinic.",
                "image_brief": "Nour arrives at the clinic.",
                "character_ids": ["nour"],
            }]},
        ),
        plan_call_id="plan_unselected_cast",
        source_request_message_id="story_request",
        request_texts=["A clinic story about Gomaa and Nour."],
        selected_character_ids=["char_gomaa"],
        selected_style_profile=None,
        selected_location=None,
        canonical_characters={
            "char_gomaa": _char("Gomaa", "gomaa_ref"),
            "nour": _char("Nour", "nour_ref"),
        },
        execution_manager=_ExecutionManager(),
        effective_budget_usd=1.0,
        offline_mode=False,
    )

    job, summary = workflow.run([], [])

    assert job.status == "needs_attention"
    assert job.pages[0].revision is None
    assert job.panels["panel_01"].status == "needs_attention"
    assert "Nour" in summary
    assert "Select those characters or revise the plan's cast" in summary
    assert registry.calls == []


def test_resumed_job_accepts_refreshed_selection_only_when_it_covers_saved_plan_cast():
    job = StoryProductionJob(
        job_id="cast_resume_job",
        run_id="cast_resume_job",
        project_id="real_one_6675e532",
        source_request_message_id="source",
        source_plan_call_id="plan",
        plan={"plans": [
            {"panel_id": "panel_01", "character_ids": ["char_gomaa", "char_nour"]},
            {"panel_id": "panel_02", "character_ids": ["char_gomaa", "char_muse"]},
        ]},
        panels={
            "panel_01": PanelProduction(
                panel_id="panel_01", page_number=1,
                character_ids=["char_gomaa", "char_nour"], asset_id="existing_art_01",
            ),
            "panel_02": PanelProduction(
                panel_id="panel_02", page_number=1,
                character_ids=["char_gomaa", "char_muse"],
                status="needs_attention",
                error="The approved panel cast contains characters outside the current selected/reference allow-list: char_muse",
            ),
        },
        selected_character_ids=["char_gomaa"],
        errors=["Panel panel_02 character scope needs attention."],
    )

    assert not StoryToCanvasWorkflow._sync_resumed_selection_allowlist(
        job, ["char_gomaa", "char_muse"]
    )
    assert StoryToCanvasWorkflow._selected_cast_scope_errors(job)
    assert StoryToCanvasWorkflow._sync_resumed_selection_allowlist(
        job, ["char_gomaa", "char_muse", "char_nour"]
    )
    assert not StoryToCanvasWorkflow._selected_cast_scope_errors(job)
    StoryToCanvasWorkflow._clear_resolved_selected_cast_failures(job)
    assert job.panels["panel_01"].asset_id == "existing_art_01"
    assert job.panels["panel_01"].character_ids == ["char_gomaa", "char_nour"]
    assert job.panels["panel_02"].status == "pending"
    assert job.panels["panel_02"].error is None
    assert job.errors == []


def test_old_generated_asset_with_incompatible_all_cast_is_not_reused(monkeypatch):
    monkeypatch.setattr("app.api.routers.assets.get_registry", lambda: _AssetRegistry())
    canon = {
        "char_gomaa": _char("Gomaa", "gomaa_ref"),
        "char_muse": _char("Muse", "muse_ref"),
    }
    style = {"profile_id": "style_approved", "version": 3, "reference_asset_ids": ["style_ref"]}
    location = {"location_id": "workshop", "version": 2}
    workflow = StoryToCanvasWorkflow(
        registry=SimpleNamespace(), session_store=_SessionStore(),
        session=AgentSession(project_id="real_one_6675e532", session_id="provenance"),
        project_id="real_one_6675e532",
        plan_result=ToolResult(call_id="plan", tool_id="planning.plan_panels", status="success", output={"plans": []}),
        plan_call_id="plan", source_request_message_id="request", request_texts=[],
        selected_character_ids=["char_gomaa"], selected_style_profile=style,
        selected_location=location, canonical_characters=canon,
        execution_manager=_ExecutionManager(), effective_budget_usd=1.0,
        offline_mode=False,
    )
    panel = PanelProduction(
        panel_id="p1", page_number=1, character_ids=["char_gomaa"],
        character_versions={"char_gomaa": 1}, style_profile_id=style["profile_id"],
        style_profile_version=style["version"],
        provenance={"location_id": "workshop", "location_version": 2},
    )
    old_output = _valid_output("p1", ["char_gomaa", "char_muse"], style, location, canon)
    assert workflow._asset_matches_panel(old_output, panel) is False


def test_live_activity_keeps_panel_job_progress_separate_from_real_tool_events():
    from app.agent.live_activity import begin_activity, get_activity, record_tool_activity

    activity_id = "story-progress-regression"
    begin_activity(activity_id)
    record_tool_activity(activity_id, {"call_id": "gen_p1", "tool_id": "generation.generate_image", "status": "success"})
    record_tool_activity(activity_id, {
        "production_job": {
            "job_id": "storyjob_test", "status": "generating",
            "pages": [], "panels": {"p1": {"panel_id": "p1", "page_number": 1, "status": "generated"}},
        },
        "stage": "panel_p1_generated",
    })
    activity = get_activity(activity_id)
    assert [tool["call_id"] for tool in activity["tools"]] == ["gen_p1"]
    assert activity["production_job"]["panels"]["p1"]["status"] == "generated"


def test_agent_lettering_routes_by_meaning_uses_selected_speaker_and_24px_without_rewriting_text():
    dispatched = []
    page = SimpleNamespace(page_number=1, page_id="page_1", revision=1)
    doc = SimpleNamespace(
        revision=1,
        layers=[],
        layout=SimpleNamespace(get_panel=lambda _panel_id: object()),
    )
    workflow = object.__new__(StoryToCanvasWorkflow)
    workflow.calls = []
    workflow.results = []
    workflow._page_document = lambda _page_id: doc
    workflow._checkpoint = lambda _job, _stage: None

    long_exact_dialogue = "You did not win the prize; the credits are for building a project before November fourth."

    def dispatch(call, _context=None):
        dispatched.append(call)
        if call.tool_id == "canvas.add_speech_bubble":
            return ToolResult(
                call_id=call.call_id,
                tool_id=call.tool_id,
                status="failed",
                error="Canvas bubble text overflow: shorten or split the text.",
                error_code="ERR_BUBBLE_TEXT_OVERFLOW",
            )
        return ToolResult(
            call_id=call.call_id,
            tool_id=call.tool_id,
            status="success",
            output={"layer_id": f"layer_{call.arguments['panel_id']}", "revision": 2},
        )

    workflow._dispatch = dispatch
    panels = {
        panel_id: SimpleNamespace(
            page_number=1,
            character_ids=cast,
            text_layer_ids=[],
            status="generated",
            error=None,
        )
        for panel_id, cast in {
            "p_narration": ["char_muse"],
            "p_dialogue": ["char_muse"],
            "p_wrong_speaker": ["char_muse"],
        }.items()
    }
    job = SimpleNamespace(
        job_id="speech_rules_job",
        pages=[page],
        panels=panels,
        errors=[],
        assumptions=[],
    )

    workflow._place_text(job, {
        "p_narration": {"text": {
            "content_kind": "narration",
            "carrier": "speech_bubble",
            "text_content": "Muse arrives at the clinic carrying a satchel.",
        }},
        "p_dialogue": {"emotional_intent": "curious wonder", "narrative_function": "dialogue", "story_event": "Muse notices a strange light", "text": {
            "content_kind": "spoken_dialogue",
            "carrier": "speech_bubble",
            "speaker_id": "char_muse",
            "text_content": long_exact_dialogue,
        }},
        "p_wrong_speaker": {"text": {
            "content_kind": "spoken_dialogue",
            "carrier": "speech_bubble",
            "speaker_id": "char_nour",
            "text_content": "I found the notice.",
        }},
    })

    assert [call.tool_id for call in dispatched] == ["editor.add_text_layer", "canvas.add_speech_bubble"]
    assert dispatched[0].arguments["text"] == "Muse arrives at the clinic carrying a satchel."
    bubble_args = dispatched[1].arguments
    assert bubble_args["speaker_character_id"] == "char_muse"
    assert bubble_args["text"] == long_exact_dialogue
    assert bubble_args["font_size"] == 24
    assert bubble_args["emotional_intent"] == "curious wonder"
    assert bubble_args["bubble_shape"] == "scalloped_flower"
    assert bubble_args["story_event"] == "Muse notices a strange light"
    assert bubble_args["dialogue_text"] == long_exact_dialogue
    assert panels["p_dialogue"].status == "needs_attention"
    assert "overflow" in panels["p_dialogue"].error.casefold()
    assert "char_nour" in panels["p_wrong_speaker"].error
    assert panels["p_wrong_speaker"].status == "needs_attention"
    assert any("routed narration to caption" in item for item in job.assumptions)


def test_story_local_dialogue_uses_trusted_job_speaker_identity_for_editable_bubble():
    local_id = "story_local_8d4f9232ac168d3a"
    workflow = object.__new__(StoryToCanvasWorkflow)
    doc = SimpleNamespace(
        revision=3,
        layers=[],
        layout=SimpleNamespace(get_panel=lambda _panel_id: object()),
    )
    workflow._page_document = lambda _page_id: doc
    workflow._saved_character_anchor = lambda *_args: None
    workflow._checkpoint = lambda _job, _stage: None
    dispatched = []

    def dispatch(call, context=None):
        dispatched.append((call, context))
        return ToolResult(
            call_id=call.call_id,
            tool_id=call.tool_id,
            status="success",
            output={"layer_id": "bubble_local_1", "revision": 4},
        )

    workflow._dispatch = dispatch
    page = SimpleNamespace(page_number=1, page_id="page_local", revision=3, verification={})
    panel = SimpleNamespace(
        page_number=1,
        character_ids=[],
        text_layer_ids=[],
        status="generated",
        error=None,
    )
    job = SimpleNamespace(
        job_id="story_local_job",
        plan={"story_local_cast": [{"speaker_id": local_id, "name": "Pip"}]},
        pages=[page],
        panels={"p1": panel},
        errors=[],
        assumptions=[],
    )

    workflow._place_text(job, {
        "p1": {
            "story_local_character_names": ["Pip"],
            "story_event": "Pip invites a friend closer.",
            "emotional_intent": "warm and curious",
            "text": {
                "content_kind": "spoken_dialogue",
                "carrier": "speech_bubble",
                "text_content": "Come closer.",
                "speaker_id": local_id,
                "speaker_name": "Pip",
            },
        },
    })

    assert len(dispatched) == 1
    call, context = dispatched[0]
    assert call.tool_id == "canvas.add_speech_bubble"
    assert call.arguments["text"] == "Come closer."
    assert call.arguments["speaker_character_id"] == local_id
    assert call.arguments["speaker"] == "Pip"
    assert call.arguments["font_size"] == 24
    assert context["selected_character_ids"] == []
    assert context["_story_local_speakers"] == {local_id: "Pip"}
    assert panel.text_layer_ids == ["bubble_local_1"]

    resolved = workflow._resolve_agent_text_carrier(
        {"content_kind": "spoken_dialogue", "carrier": "speech_bubble", "speaker_id": local_id},
        [],
        {local_id: "Pip"},
    )
    assert resolved == ("speech_bubble", local_id, None, None)


def test_bubble_adapter_accepts_only_job_scoped_story_local_speakers(monkeypatch):
    from app.agent.registry import CapabilityRegistry, ToolError
    from app.contracts.geometry import Rect
    from app.canvas import character_locator

    registry = object.__new__(CapabilityRegistry)
    slot = SimpleNamespace(rect=Rect(x=0, y=0, width=320, height=320))
    document = SimpleNamespace(
        layout=SimpleNamespace(
            get_panel=lambda _panel_id: slot,
            trim_box=Rect(x=0, y=0, width=320, height=320),
            reading_direction="ltr",
        ),
        layers=[],
    )
    registry._editor_page = lambda _args, _ctx: (object(), document)
    monkeypatch.setattr(character_locator, "locate_character_in_panel", lambda *_args, **_kwargs: None)
    arguments = {
        "page_id": "page_local",
        "panel_id": "p1",
        "text": "Come closer.",
        "speaker": "Pip",
        "speaker_character_id": "story_local_forged",
    }
    context = {
        "project_id": "story_project",
        "_agent_chat": True,
        "selected_character_ids": [],
        "_story_local_speakers": {"story_local_trusted": "Pip"},
    }

    with pytest.raises(ToolError, match="not in the Agent's selected character cast"):
        registry._canvas_add_speech_bubble_adapter(arguments, context)

    arguments["speaker_character_id"] = "story_local_trusted"
    with pytest.raises(ToolError, match="could not locate a visible subject"):
        registry._canvas_add_speech_bubble_adapter(arguments, context)


def test_story_shape_preferences_compile_to_custom_panel_geometry():
    from app.agent.story_to_canvas import _scratch_geometry_from_plans

    plans = [
        {"panel_id": "p1", "reading_order_index": 1, "shape_preference": "panoramic", "narrative_function": "establishing"},
        {"panel_id": "p2", "reading_order_index": 2, "shape_preference": "trapezoid", "narrative_function": "action_continuation"},
        {"panel_id": "p3", "reading_order_index": 3, "shape_preference": "vertical_rectangle", "narrative_function": "reaction"},
        {"panel_id": "p4", "reading_order_index": 4, "shape_preference": "square", "narrative_function": "dialogue"},
    ]
    geometry = _scratch_geometry_from_plans(plans, "rtl")
    assert [item["panel_id"] for item in geometry] == ["p1", "p2", "p3", "p4"]
    assert "rect" in geometry[0]
    assert "polygon" in geometry[1]
    assert "rect" in geometry[2]
    assert len({(tuple(item["rect"].values()) if "rect" in item else tuple((point["x"], point["y"]) for point in item["polygon"])) for item in geometry}) == 4


def test_eighteen_panel_custom_layout_clamps_last_row_to_usable_page_edge():
    from app.agent.story_to_canvas import _scratch_geometry_from_plans
    from app.canvas.models import CanvasSpec, PageSpec, ReadingDirection
    from app.canvas.templates.custom import CustomLayoutTemplate

    plans = []
    for index in range(1, 19):
        plan = {"panel_id": f"panel_{index:02d}", "reading_order_index": index}
        if index == 1:
            plan["narrative_function"] = "establishing"
        if index == 7:
            plan["narrative_function"] = "action_continuation"
        if index == 18:
            plan["shape_preference"] = "panoramic"
        plans.append(plan)

    geometry = _scratch_geometry_from_plans(plans, "ltr")
    assert len(geometry) == 18
    assert all(
        item["rect"]["x"] + item["rect"]["width"] <= 1.0
        and item["rect"]["y"] + item["rect"]["height"] <= 1.0
        for item in geometry
    )
    layout = CustomLayoutTemplate().generate(
        CanvasSpec(width_px=900.0, height_px=1200.0),
        PageSpec(page_id="page_custom_18", reading_direction=ReadingDirection.LTR),
        panel_geometry=geometry,
    )
    assert len(layout.panel_slots) == 18
    assert layout.panel_slots[-1].rect.bottom <= layout.usable_box.bottom


def test_creator_explicit_caption_is_kept_as_one_narration_layer_not_spread_across_panels():
    workflow = object.__new__(StoryToCanvasWorkflow)
    plans = [
        {"panel_id": "p1", "text": {"content_kind": "none", "carrier": "none"}},
        {"panel_id": "p2", "text": {"content_kind": "none", "carrier": "none"}},
    ]

    workflow._recover_explicit_caption(plans, ["Caption:\nAt dawn, the clinic opens."])

    assert plans[0]["text"] == {
        "content_kind": "narration",
        "carrier": "caption",
        "text_content": "At dawn, the clinic opens.",
        "reserve_space": True,
    }
    assert plans[1]["text"]["content_kind"] == "none"


def test_non_custom_layout_fallback_uses_story_rhythm_instead_of_static_grid():
    from app.agent.story_to_canvas import _fallback_layout_template

    six_action = [{"panel_id": f"p{i}", "shape_preference": "trapezoid", "narrative_function": "action"} for i in range(1, 7)]
    four_action = [{"panel_id": f"p{i}", "story_event": f"Hero strike action beat {i}"} for i in range(1, 5)]
    four_comedy = [{"panel_id": f"p{i}"} for i in range(1, 5)]

    assert _fallback_layout_template(six_action, ["battle sequence"])[0] == "diagonal_slash_battle"
    assert _fallback_layout_template(four_action, ["dynamic action scene"])[0] == "three_tier_action_slant"
    assert _fallback_layout_template(four_comedy, ["four-koma setup and punchline"])[0] == "four_koma"
    assert _fallback_layout_template(four_comedy, ["scratch a custom page"])[2] is True


def test_spacing_failure_marks_page_and_panels_before_artwork_generation():
    workflow = object.__new__(StoryToCanvasWorkflow)
    workflow._dispatch = lambda call: ToolResult(
        call_id=call.call_id,
        tool_id=call.tool_id,
        status="failed",
        error="Page spacing service unavailable.",
    )
    page = SimpleNamespace(page_number=1, page_id="page_1", panel_ids=["p1", "p2"], status="created", verification={})
    panels = {
        panel_id: SimpleNamespace(status="pending", asset_id=None, error=None)
        for panel_id in page.panel_ids
    }
    job = SimpleNamespace(job_id="spacing_failure", errors=[], assumptions=[], panels=panels)

    workflow._inspect_page_spacing(job, page)

    assert page.status == "needs_attention"
    assert page.verification["spacing_valid"] is False
    assert "Page spacing service unavailable." in job.errors[0]
    assert all(panel.status == "needs_attention" for panel in panels.values())


def test_spacing_failure_blocks_even_an_explicit_generation_retry():
    workflow = object.__new__(StoryToCanvasWorkflow)
    workflow.request_texts = ["retry panel p1"]
    workflow._checkpoint = lambda _job, _stage: None
    dispatched = []
    workflow._dispatch = lambda call: dispatched.append(call)
    page = SimpleNamespace(page_number=1, verification={"spacing_valid": False})
    panel = SimpleNamespace(
        asset_id=None, status="needs_attention", page_number=1,
        error=None, manual_retries=0, automatic_retries=0,
    )
    job = SimpleNamespace(
        status="needs_attention", panels={"p1": panel}, pages=[page], errors=[],
    )

    workflow._generate_missing(job, {"p1": {}}, [], [], unit_cost=0.01)

    assert dispatched == []
    assert panel.status == "needs_attention"
    assert "spacing" in panel.error.casefold()
