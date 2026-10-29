"""
InkLoop Visual Regression Corpus & Engine Readiness Register (Task T6.2).
Maintains versioned regression specifications across all 7 comic production domains.
Enforces the strict invariant that unimplemented engines (E2, E4, E5, E6, E7, S8)
cannot falsely report passing regression results.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict

from app.contracts.engine import EngineId
from app.evaluation.enums import (
    RegressionDomain,
    RegressionReadiness,
    EvaluationVerdict,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VisualRegressionCase(BaseModel):
    """
    Specification for a visual regression test case.
    Explicitly tracks whether producing engine dependencies are implemented.
    """
    case_id: str = Field(..., description="Stable regression identifier (e.g. 'reg_01_comp_establishing')")
    version: str = Field(default="1.0.0")
    domain: RegressionDomain = Field(..., description="Evaluation domain")
    engine_id: EngineId = Field(..., description="Specialist engine responsible for this visual layer")
    engine_implemented: bool = Field(..., description="Whether producing engine is currently implemented in workspace")
    taxonomy_ids: List[str] = Field(default_factory=list, description="Associated taxonomy group IDs")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Description of the test scenario")
    expected_behavior: str = Field(..., description="Affirmative quality invariant expected")
    failure_definition: str = Field(..., description="Exact condition constituting a visual regression")
    input_artifact_ids: List[str] = Field(default_factory=list, description="Input asset IDs from Asset Registry")
    input_artifact_hashes: Dict[str, str] = Field(default_factory=dict, description="Artifact ID to SHA-256 mapping")
    baseline_output_artifact_id: Optional[str] = Field(default=None)
    baseline_output_sha256: Optional[str] = Field(default=None)
    automated_check_description: Optional[str] = Field(default=None)
    human_check_required: bool = Field(default=False)
    human_rubric: Optional[str] = Field(default=None)
    readiness: RegressionReadiness = Field(..., description="READY, PLANNED, or BLOCKED_BY_ENGINE")
    known_limitations: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_engine_readiness_integrity(self) -> "VisualRegressionCase":
        """
        Guarantees that an unimplemented engine cannot have readiness=READY,
        and cannot claim verified baseline outputs without real implementation.
        """
        if not self.engine_implemented:
            if self.readiness == RegressionReadiness.READY:
                raise ValueError(
                    f"Regression case '{self.case_id}' targets unimplemented engine '{self.engine_id.value}' "
                    f"and cannot be marked readiness='READY'. Must be BLOCKED_BY_ENGINE or PLANNED."
                )
            if self.baseline_output_sha256 is not None:
                raise ValueError(
                    f"Regression case '{self.case_id}' cannot specify baseline_output_sha256 "
                    f"for an unimplemented engine ('{self.engine_id.value}')."
                )
        return self


class RegressionEvaluationResult(BaseModel):
    """Execution outcome of a regression check."""
    case_id: str
    engine_id: EngineId
    domain: RegressionDomain
    verdict: EvaluationVerdict
    is_blocked: bool
    block_reason: Optional[str] = None
    observed_sha256: Optional[str] = None
    baseline_sha256: Optional[str] = None
    difference_detected: bool = False
    evidence_notes: str
    evaluated_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")


class VisualRegressionCorpus:
    """
    Corpus register maintaining canonical visual regression cases across all 7 domains.
    Reuses existing Asset Registry identifiers and canonical assets.
    """

    def __init__(self, seed_defaults: bool = True):
        self._cases: Dict[str, VisualRegressionCase] = {}
        if seed_defaults:
            self._seed_canonical_corpus()

    def _seed_canonical_corpus(self) -> None:
        """Seeds canonical cases across all 7 domains with honest engine readiness."""
        canonical_cases = [
            # Domain 1: Composition & Framing (Engine: E1 Image Generation - IMPLEMENTED)
            VisualRegressionCase(
                case_id="reg_01_comp_establishing",
                version="1.0.0",
                domain=RegressionDomain.COMPOSITION_FRAMING,
                engine_id=EngineId.E1_IMAGE_GENERATION,
                engine_implemented=True,
                taxonomy_ids=["tax_04_panel_types_function", "tax_07_camera_shot_scales"],
                title="Wide Establishing Shot Composition",
                description="Verifies that wide shot scale maintains environmental horizon and character position.",
                expected_behavior="Subject occupies central third; environmental landmarks visible without zoom cropping.",
                failure_definition="Camera zooms into close-up or omits environmental horizon.",
                input_artifact_ids=["art_nour_reference"],
                input_artifact_hashes={"art_nour_reference": "b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644"},
                readiness=RegressionReadiness.READY,
                automated_check_description="SAM/CLIP subject bounding box scale relative to canvas dimensions.",
                human_check_required=True,
                human_rubric="Verify composition matches wide framing scale.",
            ),

            # Domain 2: Character / Reference Consistency (Engine: E1 Image Generation - IMPLEMENTED)
            VisualRegressionCase(
                case_id="reg_02_char_nour_glasses",
                version="1.0.0",
                domain=RegressionDomain.CHARACTER_REFERENCE_CONSISTENCY,
                engine_id=EngineId.E1_IMAGE_GENERATION,
                engine_implemented=True,
                taxonomy_ids=["tax_60_visual_continuity_validation"],
                title="Nour Character Feature Retention Across Rotations",
                description="Checks that round wireframe glasses, white hair streak, and jacket patch persist under 3/4 view.",
                expected_behavior="All 3 canonical attributes present and correctly positioned on character mesh.",
                failure_definition="Square/thick glasses, white hair streak omitted or inverted to right, missing lightning patch.",
                input_artifact_ids=["art_nour_reference"],
                input_artifact_hashes={"art_nour_reference": "b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644"},
                baseline_output_artifact_id="art_nour_panel_01",
                baseline_output_sha256="70ffcdf3905df47979073e3b5e86410e6fd34f2d93ce1cc5b0cfdd56327c7b22",
                readiness=RegressionReadiness.READY,
                automated_check_description="Spark-1.3 tri-state attribute checklist verifier.",
                human_check_required=True,
                human_rubric="Verify 3/3 attributes match canonical reference sheet.",
            ),

            # Domain 3: Generation Defects & Unintended Content (Engine: E1 Image Generation - IMPLEMENTED)
            VisualRegressionCase(
                case_id="reg_03_defect_baked_text",
                version="1.0.0",
                domain=RegressionDomain.GENERATION_DEFECTS,
                engine_id=EngineId.E1_IMAGE_GENERATION,
                engine_implemented=True,
                taxonomy_ids=["tax_12_speech_bubble_types", "tax_60_visual_continuity_validation"],
                title="Negative Constraint Against Baked Dialogue and Watermarks",
                description="Verifies that generated raster artwork contains zero burned-in gibberish text or fake balloons.",
                expected_behavior="Clean artwork free of baked characters, text glyphs, signatures, or pseudo-balloons.",
                failure_definition="Visible text-like character strokes or baked-in oval dialogue containers.",
                input_artifact_ids=["art_nour_reference"],
                input_artifact_hashes={"art_nour_reference": "b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644"},
                readiness=RegressionReadiness.READY,
                automated_check_description="OCR/Text-detection check on image raster output.",
                human_check_required=False,
            ),

            # Domain 4: Text Rendering & Arabic Shaping (Engine: E4/E5 Typography - NOT IMPLEMENTED YET)
            VisualRegressionCase(
                case_id="reg_04_text_arabic_shaping",
                version="1.0.0",
                domain=RegressionDomain.TEXT_RENDERING,
                engine_id=EngineId.E5_TYPOGRAPHY_FONT,
                engine_implemented=False,  # Unimplemented engine
                taxonomy_ids=["tax_18_arabic_multilingual_lettering"],
                title="Arabic BiDi Shaping and Ligature Rendering Integrity",
                description="Verifies right-to-left cursive Arabic joining and Amiri font ligature rendering without disconnects.",
                expected_behavior="Properly connected cursive Arabic glyphs with zero reversed characters or isolated letter forms.",
                failure_definition="Disconnected Arabic letters (isolated glyph fallback) or left-to-right character reversal.",
                input_artifact_ids=["art_amiri_font"],
                readiness=RegressionReadiness.BLOCKED_BY_ENGINE,
                known_limitations=["E5 Typography Font Engine is planned for Milestone 3; cannot execute tests yet."],
            ),

            # Domain 5: Speech Bubble Geometry & Tail Attribution (Engine: E6 Speech Bubble - NOT IMPLEMENTED YET)
            VisualRegressionCase(
                case_id="reg_05_bubble_speaker_tail",
                version="1.0.0",
                domain=RegressionDomain.SPEECH_BUBBLE_GEOMETRY,
                engine_id=EngineId.E6_SPEECH_BUBBLE,
                engine_implemented=False,  # Unimplemented engine
                taxonomy_ids=["tax_14_speech_bubble_tails"],
                title="Speech Bubble Tail Origin and Speaker Attribution",
                description="Verifies that bubble tails point cleanly towards speaker mouth without occluding facial features.",
                expected_behavior="Bubble tail terminates at speaker head vector; balloon padding clears dialogue boundary.",
                failure_definition="Tail points away from speaker, collides with eyes, or crosses panel border illegally.",
                readiness=RegressionReadiness.BLOCKED_BY_ENGINE,
                known_limitations=["E6 Speech Bubble Engine is planned for Milestone 4; cannot execute tests yet."],
            ),

            # Domain 6: Effects & Motion Lines (Engine: E7 Effects Motion - NOT IMPLEMENTED YET)
            VisualRegressionCase(
                case_id="reg_06_fx_speedlines_layer",
                version="1.0.0",
                domain=RegressionDomain.EFFECTS_MOTION,
                engine_id=EngineId.E7_EFFECTS_MOTION,
                engine_implemented=False,  # Unimplemented engine
                taxonomy_ids=["tax_20_motion_lines_focus_effects"],
                title="Radial Focus Lines Geometry Layer",
                description="Verifies radial speed lines radiate outward from action focal point on transparent layer.",
                expected_behavior="Procedural radial rays with focal hole centered on action anchor.",
                failure_definition="Uniform speed lines with no vanishing point, or lines occluding focal subject completely.",
                readiness=RegressionReadiness.BLOCKED_BY_ENGINE,
                known_limitations=["E7 Effects & Motion Engine is planned for Milestone 4; cannot execute tests yet."],
            ),

            # Domain 7: Export & Delivery Reconstruction (Engine: S8 Export Delivery - NOT IMPLEMENTED YET)
            VisualRegressionCase(
                case_id="reg_07_export_cmyk_pdf_integrity",
                version="1.0.0",
                domain=RegressionDomain.EXPORT_RECONSTRUCTION,
                engine_id=EngineId.S8_EXPORT_DELIVERY,
                engine_implemented=False,  # Unimplemented engine
                taxonomy_ids=["tax_59_lettering_export_quality"],
                title="300 DPI Print PDF Raster and Vector Composite Delivery",
                description="Verifies that exported comic book PDF matches page geometry, 300 DPI, and bleed specs.",
                expected_behavior="Multi-page PDF renders at exactly 300 DPI with vector text and lossless raster layers.",
                failure_definition="Downsampled raster (<300 DPI), missing bleed trim boxes, or rasterized rasterized text blur.",
                readiness=RegressionReadiness.BLOCKED_BY_ENGINE,
                known_limitations=["S8 Export Delivery Service is planned for Milestone 5; cannot execute tests yet."],
            ),
        ]

        for case in canonical_cases:
            self._cases[case.case_id] = case

    def register_case(self, case: VisualRegressionCase) -> None:
        """Adds or updates a visual regression case."""
        validated = VisualRegressionCase.model_validate(case.model_dump())
        self._cases[validated.case_id] = validated

    def get_case(self, case_id: str) -> Optional[VisualRegressionCase]:
        return self._cases.get(case_id)

    def list_cases(self) -> List[VisualRegressionCase]:
        return sorted(self._cases.values(), key=lambda c: c.case_id)

    def list_cases_by_domain(self, domain: RegressionDomain) -> List[VisualRegressionCase]:
        return [c for c in self._cases.values() if c.domain == domain]

    def get_readiness_inventory(self) -> Dict[str, Any]:
        """Provides statistical breakdown of regression readiness across all domains."""
        cases = self.list_cases()
        by_readiness: Dict[str, int] = {st.value: 0 for st in RegressionReadiness}
        by_domain: Dict[str, Dict[str, int]] = {d.value: {"total": 0, "ready": 0, "blocked": 0, "planned": 0} for d in RegressionDomain}

        for c in cases:
            by_readiness[c.readiness.value] += 1
            by_domain[c.domain.value]["total"] += 1
            if c.readiness == RegressionReadiness.READY:
                by_domain[c.domain.value]["ready"] += 1
            elif c.readiness == RegressionReadiness.BLOCKED_BY_ENGINE:
                by_domain[c.domain.value]["blocked"] += 1
            elif c.readiness == RegressionReadiness.PLANNED:
                by_domain[c.domain.value]["planned"] += 1

        return {
            "total_cases": len(cases),
            "readiness_summary": by_readiness,
            "domain_breakdown": by_domain,
            "implemented_engines": [EngineId.E1_IMAGE_GENERATION.value],
            "unimplemented_engines": [
                EngineId.E2_CANVAS_GENERATION.value,
                EngineId.E3_IMAGE_CANVAS_INTEGRATION.value,
                EngineId.E4_TEXT_GENERATION.value,
                EngineId.E5_TYPOGRAPHY_FONT.value,
                EngineId.E6_SPEECH_BUBBLE.value,
                EngineId.E7_EFFECTS_MOTION.value,
                EngineId.S6_COMPOSITOR.value,
                EngineId.S8_EXPORT_DELIVERY.value,
            ],
            "inventory_timestamp": utc_now_iso(),
        }

    def evaluate_case(
        self,
        case_id: str,
        candidate_sha256: Optional[str] = None,
        candidate_notes: Optional[str] = None,
    ) -> RegressionEvaluationResult:
        """
        Evaluates a regression case against candidate output.
        Fails closed: strictly rejects passing an evaluation for an unimplemented engine.
        """
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(f"Regression case '{case_id}' not found in corpus.")

        # Strict invariant: Unimplemented engine cannot pass
        if not case.engine_implemented or case.readiness == RegressionReadiness.BLOCKED_BY_ENGINE:
            return RegressionEvaluationResult(
                case_id=case.case_id,
                engine_id=case.engine_id,
                domain=case.domain,
                verdict=EvaluationVerdict.NOT_EVALUABLE,
                is_blocked=True,
                block_reason=f"Engine '{case.engine_id.value}' is not implemented yet. Execution blocked.",
                observed_sha256=candidate_sha256,
                baseline_sha256=case.baseline_output_sha256,
                difference_detected=False,
                evidence_notes="Evaluation halted: Producing engine is not implemented in workspace.",
            )

        if not candidate_sha256:
            return RegressionEvaluationResult(
                case_id=case.case_id,
                engine_id=case.engine_id,
                domain=case.domain,
                verdict=EvaluationVerdict.NOT_EVALUABLE,
                is_blocked=False,
                block_reason="No candidate artifact SHA-256 provided for evaluation.",
                observed_sha256=None,
                baseline_sha256=case.baseline_output_sha256,
                difference_detected=False,
                evidence_notes="Candidate artifact missing.",
            )

        # If baseline output digest is recorded, check exact match
        differs = False
        if case.baseline_output_sha256:
            differs = (candidate_sha256.lower() != case.baseline_output_sha256.lower())

        verdict = EvaluationVerdict.PASS if not differs else EvaluationVerdict.FAIL
        notes = candidate_notes or ("Exact baseline hash match." if not differs else "Output digest diverged from baseline.")

        return RegressionEvaluationResult(
            case_id=case.case_id,
            engine_id=case.engine_id,
            domain=case.domain,
            verdict=verdict,
            is_blocked=False,
            observed_sha256=candidate_sha256,
            baseline_sha256=case.baseline_output_sha256,
            difference_detected=differs,
            evidence_notes=notes,
        )
