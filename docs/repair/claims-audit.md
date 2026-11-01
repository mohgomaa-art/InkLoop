# Earlier Claims Audit (M0)

None of these earlier claims is promoted to verified solely because a report or comment said it was fixed. The full current backend suite passed on an isolated snapshot; the focused editor test passed against mocked API routes. M0 did not capture a before-failure for these historical claims and did not validate a live provider response. Status is therefore conservative.

| Earlier claim | M0 status | Evidence / limit |
|---|---|---|
| E1 canonical character context and actual reference bytes reach provider | CLAIMED-UNVERIFIED | Existing regression source: `backend/tests/test_agent_generation_context.py`; no live provider call. |
| Cover/contain masked image fit preserves source proportions | CLAIMED-UNVERIFIED | Browser fixture exercised cover fit only and mocked storage; `test_character_bounds_follow_contain_fit_and_image_rotation` is in the baseline suite. |
| Non-uniform image scaling is rejected | CLAIMED-UNVERIFIED | `backend/tests/test_editable_page_store.py` ran in the baseline suite; no pre-fix failure or live editor/backend round trip recorded. |
| Revisioned page-editing tools are registered and exposed | CLAIMED-UNVERIFIED | 66 registry definitions inspected, 57 available/callable with adapters; tests mention many tool IDs. Per-tool real UI effects not verified. |
| Font upload validation exists | CLAIMED-UNVERIFIED | API tests ran in the backend suite; font selection/shaping/export not visually verified. |
| Agent routing fixes and count-only clarification | CLAIMED-UNVERIFIED | Routing and behavioral tests ran; no production conversation was submitted in a live UI. |
| Character-scoped exclusions prevent cross-character suppression | CLAIMED-UNVERIFIED | `test_character_specific_restrictions_do_not_cancel_another_selected_characters_traits` ran in the suite; no provider image comparison. |
| Quick-style previews are display-only and not sent as generation references | CLAIMED-UNVERIFIED | `backend/tests/test_quick_styles.py` ran in the suite; the M0 tool/provider request was not observed live. |
| Lettering continuation on completed jobs | CLAIMED-UNVERIFIED | `backend/tests/test_agent_lettering_continuation.py` ran; no real chat-to-Canvas journey was captured. |
| Speech bubbles measure text and default to 24px | CLAIMED-UNVERIFIED | Relevant tests ran but the Agent-to-Canvas live production journey was not driven in M0. |
| Project-scoped transcript cache and restore behavior | CLAIMED-UNVERIFIED | Session tests ran; no browser refresh/project-switch test was captured. |
| Object Studio drafts reuse existing object IDs and references | CLAIMED-UNVERIFIED | Object Studio tests ran; no provider request or visual continuity verification. |

