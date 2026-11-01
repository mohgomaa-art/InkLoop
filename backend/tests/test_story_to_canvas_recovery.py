from types import SimpleNamespace

from app.agent.production import PanelProduction
from app.agent.story_to_canvas import StoryToCanvasWorkflow


class _AssetRegistry:
    def resolve_asset(self, asset_id, verify_integrity=False):
        assert asset_id == "art_panel_01"
        assert verify_integrity is True
        return SimpleNamespace(metadata=SimpleNamespace(project_id="story_recovery_test"))


def _workflow(selected_character_ids):
    workflow = object.__new__(StoryToCanvasWorkflow)
    workflow.project_id = "story_recovery_test"
    workflow.selected_character_ids = selected_character_ids
    workflow.selected_style_profile = {"profile_id": "style_test", "version": 3}
    workflow.selected_location = None
    workflow.canonical_characters = {
        "char_a": SimpleNamespace(canon_version=2, reference_assets=[SimpleNamespace(asset_id="ref_a")]),
        "char_b": SimpleNamespace(canon_version=4, reference_assets=[SimpleNamespace(asset_id="ref_b")]),
    }
    return workflow


def test_prior_selected_cast_superset_can_be_reused_only_with_exact_receipt_provenance(monkeypatch):
    from app.api.routers import assets

    monkeypatch.setattr(assets, "get_registry", lambda: _AssetRegistry())
    workflow = _workflow(["char_a", "char_b"])
    panel = PanelProduction(
        panel_id="panel_01",
        page_number=1,
        character_ids=["char_a"],
        character_versions={"char_a": 2},
        style_profile_id="style_test",
        style_profile_version=3,
    )
    output = {
        "panel_id": "panel_01",
        "asset_id": "art_panel_01",
        "character_ids": ["char_a", "char_b"],
        "character_versions": {"char_a": 2, "char_b": 4},
        "style_profile_id": "style_test",
        "style_profile_version": 3,
        "character_reference_asset_ids": ["ref_a", "ref_b"],
        "reference_image_roles": [
            {"asset_id": "ref_a", "role": "character_reference", "character_id": "char_a"},
            {"asset_id": "ref_b", "role": "character_reference", "character_id": "char_b"},
        ],
        "style_reference_asset_ids": [],
        "is_simulated": False,
    }

    assert workflow._asset_matches_panel(output, panel, allow_selected_cast_superset=True)
    assert not workflow._asset_matches_panel({**output, "reference_image_roles": []}, panel, allow_selected_cast_superset=True)
    assert not workflow._asset_matches_panel(output, panel)
    assert not _workflow(["char_a"])._asset_matches_panel(output, panel, allow_selected_cast_superset=True)

    changed_version = {**output, "character_versions": {"char_a": 2, "char_b": 3}}
    assert not workflow._asset_matches_panel(changed_version, panel, allow_selected_cast_superset=True)


def test_resume_recovers_only_unambiguous_profile_and_cast_from_successful_receipts():
    from app.agent.schemas import ToolCall, ToolResult

    calls = [ToolCall(call_id="gen1", tool_id="generation.generate_image", arguments={"character_ids": ["char_a", "char_b"]})]
    results = [ToolResult(
        call_id="gen1", tool_id="generation.generate_image", status="success",
        output={"style_profile_id": "style_test", "style_profile_version": 3,
                "location_id": "clinic", "location_version": 2},
    )]

    assert StoryToCanvasWorkflow._recover_selected_cast(results, calls) == ["char_a", "char_b"]
    assert StoryToCanvasWorkflow._recover_profile_snapshot(results, "style_profile_id", "style_profile_version", "profile_id") == {
        "profile_id": "style_test", "version": 3,
    }
    assert StoryToCanvasWorkflow._recover_profile_snapshot(results, "location_id", "location_version", "location_id") == {
        "location_id": "clinic", "version": 2,
    }

    conflicting = results + [ToolResult(
        call_id="gen2", tool_id="generation.generate_image", status="success",
        output={"style_profile_id": "another_style", "style_profile_version": 1},
    )]
    assert StoryToCanvasWorkflow._recover_profile_snapshot(conflicting, "style_profile_id", "style_profile_version", "profile_id") is None


def test_resume_restores_saved_job_cast_and_profile_versions_when_chat_selection_is_empty():
    workflow = _workflow([])
    workflow.selected_style_profile = None
    job = SimpleNamespace(
        selected_character_ids=["char_a", "char_b"],
        style_snapshot={"profile_id": "style_test", "version": 3},
        location_snapshot={"location_id": "clinic", "version": 2},
    )

    workflow._restore_job_context(job)

    assert workflow.selected_character_ids == ["char_a", "char_b"]
    assert workflow.selected_style_profile == {"profile_id": "style_test", "version": 3}
    assert workflow.selected_location == {"location_id": "clinic", "version": 2}


def test_legacy_panel_plans_inherit_selected_cast_unless_marked_characterless():
    plans = [
        {"panel_id": "panel_01", "character_ids": [], "image_brief": "A character reacts."},
        {"panel_id": "panel_02", "character_ids": [], "characterless": True, "image_brief": "An empty room."},
    ]

    inherited = StoryToCanvasWorkflow._apply_selected_cast_defaults(
        plans,
        ["char_a", "char_b"],
        {"char_a": SimpleNamespace(name="Gomaa"), "char_b": SimpleNamespace(name="Muse")},
    )

    assert inherited == ["panel_01"]
    assert plans[0]["character_ids"] == ["char_a", "char_b"]
    assert plans[0]["character_selection_source"] == "creator_selected_default"
    assert "Gomaa, Muse" in plans[0]["image_brief"]
    assert plans[1]["character_ids"] == []


def test_completed_job_reports_panels_generated_without_the_saved_selected_cast():
    from app.agent.production import PageProduction, StoryProductionJob

    plans = [{"panel_id": f"panel_{index:02d}", "character_ids": []} for index in range(1, 7)]
    panels = {
        plan["panel_id"]: PanelProduction(
            panel_id=plan["panel_id"],
            page_number=1,
            status="placed",
            character_ids=["char_gomaa", "char_muse"] if plan["panel_id"] == "panel_01" else [],
            asset_id=f"art_{plan['panel_id']}",
            provenance={
                "character_ids": ["char_gomaa", "char_muse"] if plan["panel_id"] == "panel_01" else [],
            },
        )
        for plan in plans
    }
    job = StoryProductionJob(
        job_id="job",
        run_id="job",
        project_id="project",
        source_request_message_id="request",
        source_plan_call_id="plan",
        status="completed",
        plan={"plans": plans},
        selected_character_ids=["char_gomaa", "char_muse"],
        pages=[PageProduction(page_number=1, page_id="page", panel_ids=[p["panel_id"] for p in plans])],
        panels=panels,
    )

    assert StoryToCanvasWorkflow._saved_cast_mismatches(job) == [
        "panel_02", "panel_03", "panel_04", "panel_05", "panel_06"
    ]


def test_reopened_completed_job_tells_creator_which_saved_panels_missed_selected_cast():
    from app.agent.production import PageProduction, StoryProductionJob, stable_job_id
    from app.agent.schemas import AgentSession, ToolResult

    project_id = "story_recovery_test"
    session_id = "saved_cast_mismatch"
    plan_call_id = "saved_plan"
    job_id = stable_job_id(project_id, session_id, plan_call_id)
    plans = [{"panel_id": f"panel_{index:02d}", "character_ids": []} for index in range(1, 3)]
    job = StoryProductionJob(
        job_id=job_id,
        run_id=job_id,
        project_id=project_id,
        source_request_message_id="request",
        source_plan_call_id=plan_call_id,
        status="completed",
        plan={"plans": plans},
        selected_character_ids=["char_gomaa", "char_muse"],
        pages=[PageProduction(
            page_number=1, page_id="page_story_saved",
            panel_ids=["panel_01", "panel_02"], revision=3,
            status="assembled", verification={"passed": True},
        )],
        panels={
            panel_id: PanelProduction(
                panel_id=panel_id, page_number=1, status="placed", asset_id=f"art_{panel_id}",
                character_ids=["char_gomaa", "char_muse"] if panel_id == "panel_01" else [],
                provenance={"character_ids": ["char_gomaa", "char_muse"] if panel_id == "panel_01" else []},
            )
            for panel_id in ("panel_01", "panel_02")
        },
    )
    session = AgentSession(
        project_id=project_id,
        session_id=session_id,
        metadata={"story_production_jobs": {job_id: job.model_dump(mode="json")}},
    )
    workflow = StoryToCanvasWorkflow(
        registry=object(), session_store=None, session=session, project_id=project_id,
        plan_result=ToolResult(
            call_id=plan_call_id, tool_id="planning.plan_panels", status="success",
            output={"plans": plans},
        ),
        plan_call_id=plan_call_id, source_request_message_id="request", request_texts=["MAKE PANELS"],
        selected_character_ids=[], selected_style_profile=None, selected_location=None,
        canonical_characters={}, execution_manager=None, effective_budget_usd=0.0, offline_mode=False,
    )

    resumed, summary = workflow.run([], [])

    assert resumed.status == "needs_attention"
    assert "selected characters were omitted from panel_02" in summary
    assert "left the existing artwork untouched" in summary
    assert session.metadata["story_production_jobs"][job_id]["status"] == "needs_attention"


def test_selected_cast_repair_prepares_only_verified_mismatched_panel_layers_for_replacement():
    from app.agent.production import PageProduction, StoryProductionJob
    from app.agent.schemas import AgentSession
    from app.editor.models import LayerKind

    class _PageStore:
        def save_session(self, _session):
            return None

    page = SimpleNamespace(
        page_id="page_saved",
        project_id="story_recovery_test",
        revision=13,
        layout=SimpleNamespace(get_panel=lambda _panel_id: object()),
        layers=[
            SimpleNamespace(layer_id=f"image_old_{index}", kind=LayerKind.IMAGE,
                            panel_id=f"panel_{index:02d}", source_asset_id=f"art_old_{index}")
            for index in range(1, 3)
        ],
    )
    registry = SimpleNamespace(_editor_page=lambda _page_id, _ctx: (None, page))
    workflow = object.__new__(StoryToCanvasWorkflow)
    workflow.project_id = "story_recovery_test"
    workflow.registry = registry
    workflow.session = AgentSession(project_id="story_recovery_test", session_id="repair")
    workflow.session_store = _PageStore()
    workflow.activity_callback = None
    workflow.execution_manager = None
    workflow.canonical_characters = {
        "char_a": SimpleNamespace(name="Gomaa", canon_version=2),
        "char_b": SimpleNamespace(name="Muse", canon_version=4),
    }
    plans = [
        {"panel_id": f"panel_{index:02d}", "character_ids": [], "image_brief": f"Beat {index}."}
        for index in range(1, 3)
    ]
    job = StoryProductionJob(
        job_id="job_repair",
        run_id="job_repair",
        project_id="story_recovery_test",
        source_request_message_id="request",
        source_plan_call_id="plan",
        status="completed",
        plan={"plans": plans},
        selected_character_ids=["char_a", "char_b"],
        pages=[PageProduction(
            page_number=1, page_id="page_saved", panel_ids=["panel_01", "panel_02"],
            revision=13, status="assembled", verification={"passed": True},
        )],
        panels={
            f"panel_{index:02d}": PanelProduction(
                panel_id=f"panel_{index:02d}", page_number=1, status="placed",
                character_ids=[], asset_id=f"art_old_{index}",
                image_layer_id=f"image_old_{index}", provenance={"character_ids": []},
            )
            for index in range(1, 3)
        },
    )

    workflow._prepare_selected_cast_repair(job, plans, ["panel_02"])

    assert job.status == "preflight"
    assert job.run_id.startswith("job_repair_castrepair_")
    assert job.panels["panel_01"].asset_id == "art_old_1"
    assert job.panels["panel_02"].asset_id is None
    assert job.panels["panel_02"].replacement_expected_asset_id == "art_old_2"
    assert job.panels["panel_02"].image_layer_id == "image_old_2"
    assert job.panels["panel_02"].character_ids == ["char_a", "char_b"]
    assert plans[1]["character_ids"] == ["char_a", "char_b"]
    assert "Gomaa, Muse" in plans[1]["image_brief"]


def test_canvas_repair_replaces_only_the_exact_recorded_old_artwork_asset():
    from app.agent.production import PageProduction, StoryProductionJob
    from app.agent.schemas import AgentSession, ToolResult
    from app.editor.models import LayerKind

    old_layer = SimpleNamespace(
        layer_id="image_old_panel_02", kind=LayerKind.IMAGE, panel_id="panel_02",
        source_asset_id="art_old_panel_02",
    )
    page = SimpleNamespace(
        page_id="page_saved", project_id="story_recovery_test", revision=13,
        layout=SimpleNamespace(get_panel=lambda _panel_id: object()), layers=[old_layer],
    )

    class _Registry:
        def __init__(self):
            self.calls = []

        def _editor_page(self, _page_id, _ctx):
            return None, page

        def dispatch(self, call, _ctx):
            self.calls.append(call)
            args = call.arguments
            assert args["replace_existing"] is True
            assert page.revision == args["expected_revision"]
            assert old_layer.source_asset_id == "art_old_panel_02"
            page.layers = [layer for layer in page.layers if layer is not old_layer]
            page.layers.append(SimpleNamespace(
                layer_id="image_new_panel_02", kind=LayerKind.IMAGE,
                panel_id="panel_02", source_asset_id="art_new_panel_02",
            ))
            page.revision += 1
            return ToolResult(call_id=call.call_id, tool_id=call.tool_id, status="success", output={
                "page_id": page.page_id, "panel_id": "panel_02", "layer_id": "image_new_panel_02",
                "asset_id": "art_new_panel_02", "revision": page.revision,
            })

    workflow = object.__new__(StoryToCanvasWorkflow)
    workflow.project_id = "story_recovery_test"
    workflow.registry = _Registry()
    workflow.session = AgentSession(project_id="story_recovery_test", session_id="repair")
    workflow.session_store = SimpleNamespace(save_session=lambda _session: None)
    workflow.execution_manager = None
    workflow.activity_callback = None
    workflow.dispatch_context = {"project_id": "story_recovery_test", "_agent_chat": True}
    workflow.calls = []
    workflow.results = []
    job = StoryProductionJob(
        job_id="job_repair", run_id="job_repair", project_id="story_recovery_test",
        source_request_message_id="request", source_plan_call_id="plan", plan={"plans": []},
        pages=[PageProduction(page_number=1, page_id="page_saved", panel_ids=["panel_02"], status="created")],
        panels={"panel_02": PanelProduction(
            panel_id="panel_02", page_number=1, status="generated", asset_id="art_new_panel_02",
            character_ids=["char_a"], replacement_expected_asset_id="art_old_panel_02",
            image_layer_id="image_old_panel_02",
        )},
    )

    workflow._place_assets(job, {"panel_02": {"panel_id": "panel_02"}})

    assert len(workflow.registry.calls) == 1
    assert workflow.registry.calls[0].tool_id == "canvas.place_panel_artwork"
    assert job.panels["panel_02"].status == "placed"
    assert job.panels["panel_02"].replacement_expected_asset_id is None
    assert [(layer.layer_id, layer.source_asset_id) for layer in page.layers] == [
        ("image_new_panel_02", "art_new_panel_02")
    ]


def test_summary_explains_unlettered_plan_without_inventing_copy():
    from app.agent.production import PageProduction

    job = SimpleNamespace(
        status="needs_attention",
        pages=[PageProduction(page_number=1, page_id="page_test", revision=5, status="assembled")],
        panels={"panel_01": SimpleNamespace(status="placed", panel_id="panel_01", error=None)},
        plan={"plans": [{"panel_id": "panel_01", "text": {"carrier": "speech_bubble", "text_content": ""}}]},
        errors=["The approved panel plan reserved lettering carriers but contains no exact text. No dialogue or captions were invented; add the wording in Canvas to finish lettering."],
    )

    summary = StoryToCanvasWorkflow._summary(job)

    assert "No lettering was added because the approved panel plan did not include exact wording" in summary
    assert "no exact text" in summary


def test_repeating_make_panels_reuses_verified_saved_page_without_tool_calls():
    from app.agent.production import PageProduction, StoryProductionJob, stable_job_id
    from app.agent.schemas import AgentSession, ToolResult

    project_id = "story_recovery_test"
    session_id = "saved_story_repeat"
    plan_call_id = "saved_panel_plan"
    job_id = stable_job_id(project_id, session_id, plan_call_id)
    plan = {"plans": [{"panel_id": "panel_01", "page_number": 1, "character_ids": ["char_a"]}]}
    job = StoryProductionJob(
        job_id=job_id,
        run_id=job_id,
        project_id=project_id,
        source_request_message_id="story_request",
        source_plan_call_id=plan_call_id,
        status="needs_attention",
        plan=plan,
        page_panel_count=1,
        pages=[PageProduction(
            page_number=1,
            page_id="page_story_saved",
            panel_ids=["panel_01"],
            revision=5,
            status="assembled",
            verification={"passed": True, "page_id": "page_story_saved", "revision": 5},
        )],
        panels={"panel_01": PanelProduction(
            panel_id="panel_01",
            page_number=1,
            status="placed",
            character_ids=["char_a"],
            asset_id="art_panel_01",
            image_layer_id="layer_panel_01",
            provenance={"character_ids": ["char_a"]},
        )},
        selected_character_ids=["char_a"],
        errors=["Lettering still needs creator attention."],
    )
    session = AgentSession(
        project_id=project_id,
        session_id=session_id,
        metadata={"story_production_jobs": {job_id: job.model_dump(mode="json")}},
    )
    workflow = StoryToCanvasWorkflow(
        registry=object(),
        session_store=None,
        session=session,
        project_id=project_id,
        plan_result=ToolResult(
            call_id=plan_call_id,
            tool_id="planning.plan_panels",
            status="success",
            output=plan,
        ),
        plan_call_id=plan_call_id,
        source_request_message_id="story_request",
        request_texts=["MAKE PANELS"],
        selected_character_ids=[],
        selected_style_profile=None,
        selected_location=None,
        canonical_characters={},
        execution_manager=None,
        effective_budget_usd=0.0,
        offline_mode=False,
    )

    resumed, summary = workflow.run([], [])

    assert resumed.job_id == job_id
    assert resumed.status == "needs_attention"
    assert workflow.calls == []
    assert "saved 1-panel story and Canvas page" in summary
    assert "without making duplicates" in summary
    assert "#/editor?page=page_story_saved" in summary
