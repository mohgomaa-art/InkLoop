"""
InkLoop Visual Verification Subsystem (Workstream S7 / Milestone M2 - ADR-002).
Provides multi-tier verification:
- L0: Deterministic Code Checks (decodability, aspect ratio, non-blank, sheet bleed)
- L1: Structure & Subject Framing (SAM 3.1 Promptable Concept Segmentation & scale)
- L2: Multimodal Vision Judge (Meta Muse Spark checklist comparison against canon)
- Rule of Closed Failure: fail or unsure on any required attribute rejects candidate.
"""
from app.verification.schemas import (
    VerificationMode,
    L0CheckResult,
    L1SubjectResult,
    L2JudgeResult,
)
from app.verification.l0_code import L0CodeChecker
from app.verification.l1_subject import L1SubjectChecker
from app.verification.l2_judge import L2VisionJudge, build_judge_prompt
from app.verification.service import (
    VisualVerificationService,
    SimulatedVisualVerificationService,
)

__all__ = [
    "VerificationMode",
    "L0CheckResult",
    "L1SubjectResult",
    "L2JudgeResult",
    "L0CodeChecker",
    "L1SubjectChecker",
    "L2VisionJudge",
    "build_judge_prompt",
    "VisualVerificationService",
    "SimulatedVisualVerificationService",
]
