"""
InkLoop Visual Verification Service - Multi-Tier Pipeline Coordinator.
Orchestrates L0 (Deterministic Code) -> L1 (Subject / SAM) -> L2 (Vision Judge)
with early rejection, closed-failure enforcement, and seamless BatchOrchestrator integration.
"""
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple, Callable
import io

from app.config import InkLoopConfig
from app.schemas import (
    VerificationResult,
    AttributeVerdict,
    AttributeCheck,
    CharacterSpec,
    ReferenceAsset,
    Tolerances,
)
from app.verification.schemas import (
    VerificationMode,
    L0CheckResult,
    L1SubjectResult,
    L2JudgeResult,
)
from app.verification.l0_code import L0CodeChecker
from app.verification.l1_subject import L1SubjectChecker
from app.verification.l2_judge import L2VisionJudge

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class VisualVerificationService:
    """
    Production Multi-Tier Verification Service.
    Enforces ADR-002: strictly remove-only, multi-tier verification:
    - Tier 0: L0CodeChecker (decodability, aspect ratio, blank frame, sheet bleed)
    - Tier 1: L1SubjectChecker (subject count, framing scale, face resolution)
    - Tier 2: L2VisionJudge (multimodal character reference vs candidate checklist)
    """

    def __init__(
        self,
        config: Optional[InkLoopConfig] = None,
        l0_checker: Optional[L0CodeChecker] = None,
        l1_checker: Optional[L1SubjectChecker] = None,
        l2_judge: Optional[L2VisionJudge] = None,
        mode: VerificationMode = VerificationMode.AUTO,
    ):
        self.config = config or InkLoopConfig.load()
        self.l0_checker = l0_checker or L0CodeChecker()
        self.l1_checker = l1_checker or L1SubjectChecker(config=self.config)
        self.l2_judge = l2_judge or L2VisionJudge(config=self.config)
        self.mode = mode

    @property
    def is_simulated(self) -> bool:
        """Indicates whether verification is running in simulated/mock mode."""
        if self.mode == VerificationMode.SIMULATED:
            return True
        if self.mode == VerificationMode.LIVE:
            return False
        # AUTO mode: simulated if credentials missing
        return not self.config.has_credentials

    def _resolve_reference_bytes(
        self,
        ref: Optional[Union[ReferenceAsset, Path, str, bytes, Any]],
    ) -> Optional[bytes]:
        """Extracts raw bytes from various reference asset representations."""
        if ref is None:
            return None
        if isinstance(ref, bytes):
            return ref

        # Check for ReferenceAsset or AssetRef schemas
        path_str = getattr(ref, "file_path", None) or getattr(ref, "path", None)
        if path_str is not None:
            p = Path(path_str)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            if p.exists() and p.is_file():
                try:
                    return p.read_bytes()
                except Exception:
                    return None

        # String or Path
        if isinstance(ref, (str, Path)):
            p = Path(ref)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            if p.exists() and p.is_file():
                try:
                    return p.read_bytes()
                except Exception:
                    return None

        return None

    def _extract_character_info(
        self,
        char_obj: Optional[Union[CharacterSpec, Any, Dict[str, Any]]],
        include_invariants: bool = False,
    ) -> Tuple[str, List[AttributeCheck], Optional[Tolerances]]:
        """Normalizes character spec or canon definition into consistent fields."""
        if char_obj is None:
            return ("unknown", [], None)

        char_id = "character"
        attributes: List[AttributeCheck] = []
        tolerances: Optional[Tolerances] = None

        if isinstance(char_obj, dict):
            char_id = char_obj.get("id") or char_obj.get("character_id", "character")
            raw_attrs = char_obj.get("attributes", [])
            for a in raw_attrs:
                if isinstance(a, AttributeCheck):
                    attributes.append(a)
                elif isinstance(a, dict):
                    attributes.append(AttributeCheck(**a))
            if include_invariants:
                raw_invs = char_obj.get("visual_invariants", [])
                for idx, inv in enumerate(raw_invs):
                    attributes.append(AttributeCheck(id=f"invariant_{idx+1}", text=inv, required=True))
            raw_tol = char_obj.get("tolerances")
            if isinstance(raw_tol, Tolerances):
                tolerances = raw_tol
            elif isinstance(raw_tol, dict):
                tolerances = Tolerances(**raw_tol)
            return (char_id, attributes, tolerances)

        # Object (CharacterSpec or CharacterDefinition)
        char_id = getattr(char_obj, "id", None) or getattr(char_obj, "character_id", "character")
        raw_attrs = getattr(char_obj, "attributes", [])
        for a in raw_attrs:
            if isinstance(a, AttributeCheck):
                attributes.append(a)
            elif isinstance(a, dict):
                attributes.append(AttributeCheck(**a))
        if include_invariants:
            raw_invs = getattr(char_obj, "visual_invariants", [])
            for idx, inv in enumerate(raw_invs):
                attributes.append(AttributeCheck(id=f"invariant_{idx+1}", text=inv, required=True))
        tolerances = getattr(char_obj, "tolerances", None)

        return (char_id, attributes, tolerances)

    def verify_panel(
        self,
        reference_asset: Optional[Union[ReferenceAsset, Path, str, bytes, Any]],
        candidate_bytes: bytes,
        character_spec: Optional[Union[CharacterSpec, Any, Dict[str, Any]]] = None,
        *,
        target_dimensions: Optional[Tuple[int, int]] = None,
        target_aspect_ratio: Optional[str] = None,
        check_sheet_bleed: bool = True,
        asset_profile: str = "panel",
        skip_l1: bool = False,
        skip_l2: bool = False,
        expected_subject_count: int = 1,
        include_invariants: bool = False,
    ) -> VerificationResult:
        """
        Executes hierarchical verification:
        1. L0 Code Checks (early exit if failed)
        2. L1 Subject & Structure Checks (early exit if failed)
        3. L2 Vision Judge (enforces closed failure)
        """
        simulated = self.is_simulated

        # =========================================================================
        # 1. Tier 0: L0 Code Checks
        # =========================================================================
        l0_res = self.l0_checker.check(
            candidate_bytes=candidate_bytes,
            target_dimensions=target_dimensions,
            target_aspect_ratio=target_aspect_ratio,
            check_sheet_bleed=check_sheet_bleed,
            asset_profile=asset_profile,
        )

        if not l0_res.passed:
            # Early rejection: abort immediately before incurring downstream costs
            return VerificationResult(
                passed=False,
                verdicts=[
                    AttributeVerdict(
                        attr_id="l0_code",
                        verdict="fail",
                        evidence=l0_res.reason or "L0 structural check failed",
                    )
                ],
                rejection_reason=f"L0 Code check failed: {l0_res.reason}",
                l0_passed=False,
                l1_passed=None,
                l2_passed=None,
                is_simulated=simulated,
                details={"l0": l0_res.model_dump()},
            )

        char_id, attributes, tolerances = self._extract_character_info(character_spec, include_invariants=include_invariants)

        # =========================================================================
        # 2. Tier 1: L1 Subject & Structure Checks
        # =========================================================================
        l1_res: Optional[L1SubjectResult] = None
        if not skip_l1:
            if isinstance(character_spec, dict):
                entity_kind = character_spec.get("entity_kind", "visual subject")
                morphology = character_spec.get("morphology", "")
            else:
                entity_kind = getattr(character_spec, "entity_kind", "visual subject")
                morphology = getattr(character_spec, "morphology", "")
            l1_res = self.l1_checker.check(
                candidate_bytes=candidate_bytes,
                concept=" ".join(part for part in [entity_kind, morphology] if part),
                expected_subject_count=expected_subject_count,
                tolerances=tolerances,
                is_simulated=simulated,
            )

            if not l1_res.passed:
                # Early rejection: subject missing or malformed; abort before L2 vision call
                return VerificationResult(
                    passed=False,
                    verdicts=[
                        AttributeVerdict(
                            attr_id="l1_structure",
                            verdict="fail",
                            evidence=l1_res.reason or "L1 subject check failed",
                        )
                    ],
                    rejection_reason=f"L1 Subject check failed: {l1_res.reason}",
                    l0_passed=True,
                    l1_passed=False,
                    l2_passed=None,
                    is_simulated=simulated or l1_res.is_simulated,
                    details={
                        "l0": l0_res.model_dump(),
                        "l1": l1_res.model_dump(),
                    },
                )

        # =========================================================================
        # 3. Tier 2: L2 Vision Judge
        # =========================================================================
        l2_res: Optional[L2JudgeResult] = None
        if not skip_l2 and attributes:
            ref_bytes = self._resolve_reference_bytes(reference_asset)
            l2_res = self.l2_judge.evaluate(
                reference_bytes=ref_bytes,
                candidate_bytes=candidate_bytes,
                character_id=char_id,
                attributes=attributes,
                is_simulated=simulated,
            )

            return VerificationResult(
                passed=l2_res.passed,
                verdicts=l2_res.verdicts,
                rejection_reason=l2_res.rejection_reason,
                l0_passed=True,
                l1_passed=l1_res.passed if l1_res else None,
                l2_passed=l2_res.passed,
                is_simulated=simulated or (l2_res.is_simulated if l2_res else False),
                details={
                    "l0": l0_res.model_dump(),
                    "l1": l1_res.model_dump() if l1_res else None,
                    "l2": l2_res.model_dump(),
                },
            )

        # If no L2 attributes were required, L0 and L1 passing is sufficient
        return VerificationResult(
            passed=True,
            verdicts=[
                AttributeVerdict(
                    attr_id="structural_invariants",
                    verdict="pass",
                    evidence="L0 and L1 structural checks verified; no character attributes declared",
                )
            ],
            rejection_reason=None,
            l0_passed=True,
            l1_passed=l1_res.passed if l1_res else None,
            l2_passed=True,
            is_simulated=simulated,
            details={
                "l0": l0_res.model_dump(),
                "l1": l1_res.model_dump() if l1_res else None,
            },
        )

    def __call__(
        self,
        reference_asset: Optional[Union[ReferenceAsset, Path, str, bytes, Any]],
        candidate_bytes: bytes,
        character_spec: Optional[Union[CharacterSpec, Any, Dict[str, Any]]] = None,
    ) -> VerificationResult:
        """Allows VisualVerificationService to be passed directly as a callable verifier."""
        return self.verify_panel(reference_asset, candidate_bytes, character_spec)


class SimulatedVisualVerificationService(VisualVerificationService):
    """
    Guaranteed Offline Deterministic Visual Verification Service.
    Always runs in SIMULATED mode; never makes external network calls.
    Truthfully identifies all outputs as simulated.
    """

    def __init__(
        self,
        config: Optional[InkLoopConfig] = None,
        mock_verdicts: Optional[List[AttributeVerdict]] = None,
    ):
        cfg = config or InkLoopConfig.load()
        super().__init__(
            config=cfg,
            l2_judge=L2VisionJudge(config=cfg, mock_verdicts=mock_verdicts),
            mode=VerificationMode.SIMULATED,
        )
        self.mock_verdicts = mock_verdicts
