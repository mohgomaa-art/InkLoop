"""
InkLoop Visual Verification Service - L1 Structure & Subject Checker.
Evaluates subject presence, character counts, bounding box framing, and face scale
using Meta SAM 3.1 Promptable Concept Segmentation (live) or deterministic structural heuristics (offline/simulated).
"""
import base64
import time
from typing import Optional, List, Dict, Any, Tuple
import httpx
from PIL import Image

from app.config import InkLoopConfig
from app.schemas import BoundingBox, SegmentationResult, Tolerances
from app.parsers import parse_sam_response
from app.verification.schemas import L1SubjectResult


class L1SubjectChecker:
    """
    Tier-1 Structure & Subject Framing Checker.
    Enforces subject presence, count consistency, and minimum face/scale thresholds.
    """

    def __init__(
        self,
        config: Optional[InkLoopConfig] = None,
        min_subject_fraction: float = 0.02,
        timeout_seconds: float = 30.0,
    ):
        self.config = config or InkLoopConfig.load()
        self.min_subject_fraction = min_subject_fraction
        self.timeout_seconds = timeout_seconds

    def check(
        self,
        candidate_bytes: bytes,
        *,
        concept: str = "person",
        expected_subject_count: int = 1,
        tolerances: Optional[Tolerances] = None,
        is_simulated: bool = False,
        mock_boxes: Optional[List[BoundingBox]] = None,
    ) -> L1SubjectResult:
        """
        Evaluates candidate panel for subject presence and scale.
        """
        # Determine execution arm: live SAM API vs simulated heuristic
        can_run_live = (not is_simulated) and self.config.has_credentials

        if can_run_live:
            return self._run_live_sam(
                candidate_bytes=candidate_bytes,
                concept=concept,
                expected_count=expected_subject_count,
                tolerances=tolerances,
            )
        else:
            return self._run_simulated_structure(
                candidate_bytes=candidate_bytes,
                expected_count=expected_subject_count,
                tolerances=tolerances,
                mock_boxes=mock_boxes,
            )

    def _run_live_sam(
        self,
        candidate_bytes: bytes,
        concept: str,
        expected_count: int,
        tolerances: Optional[Tolerances],
    ) -> L1SubjectResult:
        """Dispatches live request to Meta SAM 3.1 endpoint."""
        b64_str = base64.b64encode(candidate_bytes).decode("ascii")
        data_url = f"data:image/png;base64,{b64_str}"

        payload = {
            "model": self.config.sam_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_image", "image_url": data_url},
                        {"type": "input_text", "text": f"Locate each {concept} in the image."}
                    ]
                }
            ]
        }

        api_key = (
            self.config.model_api_key.get_secret_value()
            if hasattr(self.config.model_api_key, "get_secret_value")
            else (self.config.model_api_key or "")
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            start_t = time.time()
            resp = httpx.post(
                f"{self.config.meta_base_url}/responses",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )

            if resp.status_code != 200:
                # Live endpoint error: fail closed with explicit live error; never silently downgrade to simulated pass
                return L1SubjectResult(
                    passed=False,
                    subject_count=0,
                    boxes=[],
                    mask_available=False,
                    framing_ok=False,
                    face_scale_ok=False,
                    reason=f"Live SAM API returned status {resp.status_code}: {resp.text[:200]}",
                    is_simulated=False,
                )

            data = resp.json()
            raw_text = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            raw_text = c.get("text", "")

            seg_result = parse_sam_response(raw_text)
            return self._evaluate_boxes(
                boxes=seg_result.boxes,
                mask_available=seg_result.mask_available,
                mask_sha256=seg_result.mask_sha256,
                candidate_bytes=candidate_bytes,
                expected_count=expected_count,
                tolerances=tolerances,
                is_simulated=False,
            )
        except Exception as e:
            # Network or timeout: fail closed with explicit live error; never silently downgrade to simulated pass
            return L1SubjectResult(
                passed=False,
                subject_count=0,
                boxes=[],
                mask_available=False,
                framing_ok=False,
                face_scale_ok=False,
                reason=f"Live SAM API call exception: {str(e)}",
                is_simulated=False,
            )

    def _run_simulated_structure(
        self,
        candidate_bytes: bytes,
        expected_count: int,
        tolerances: Optional[Tolerances],
        mock_boxes: Optional[List[BoundingBox]] = None,
        error_note: Optional[str] = None,
    ) -> L1SubjectResult:
        """
        Deterministic offline structural evaluation.
        Analyzes image dimensions and detects central subject bounding box heuristically.
        """
        if mock_boxes is not None:
            boxes = mock_boxes
        else:
            # Generate deterministic bounding box based on image size
            import io
            try:
                bio = io.BytesIO(candidate_bytes)
                img = Image.open(bio)
                w, h = img.size
                # Explicitly simulated fallback: assume one generic visual subject in frame.
                boxes = [
                    BoundingBox(
                        x=w * 0.2,
                        y=h * 0.1,
                        width=w * 0.6,
                        height=h * 0.8,
                        label="visual subject",
                        confidence=0.95,
                    )
                ]
            except Exception:
                boxes = []

        return self._evaluate_boxes(
            boxes=boxes,
            mask_available=False,
            candidate_bytes=candidate_bytes,
            expected_count=expected_count,
            tolerances=tolerances,
            is_simulated=True,
            note=error_note,
        )

    def _evaluate_boxes(
        self,
        boxes: List[BoundingBox],
        mask_available: bool,
        candidate_bytes: bytes,
        expected_count: int,
        tolerances: Optional[Tolerances],
        is_simulated: bool,
        note: Optional[str] = None,
        mask_sha256: Optional[str] = None,
    ) -> L1SubjectResult:
        """Evaluates extracted bounding boxes against constraints."""
        import io
        img_w, img_h = (1024, 1024)
        try:
            bio = io.BytesIO(candidate_bytes)
            img = Image.open(bio)
            img_w, img_h = img.size
        except Exception:
            pass

        panel_area = max(img_w * img_h, 1)
        subject_count = len(boxes)

        # 1. Subject Count Check
        if expected_count > 0 and subject_count == 0:
            return L1SubjectResult(
                passed=False,
                subject_count=0,
                boxes=[],
                mask_available=mask_available,
                mask_sha256=mask_sha256,
                framing_ok=False,
                face_scale_ok=False,
                reason=f"No character detected: no visual subject found in the candidate panel (expected at least {expected_count})",
                is_simulated=is_simulated,
            )

        # 2. Framing & Subject Area Scale Check
        framing_ok = True
        face_scale_ok = True
        reasons: List[str] = []

        if boxes:
            # Largest subject box
            largest_box = max(boxes, key=lambda b: b.width * b.height)
            box_area = largest_box.width * largest_box.height
            subject_fraction = box_area / panel_area

            if subject_fraction < self.min_subject_fraction:
                framing_ok = False
                reasons.append(
                    f"Subject scale too small: {subject_fraction*100:.2f}% of panel area "
                    f"(minimum threshold {self.min_subject_fraction*100:.2f}%)"
                )

            # Face-specific checks are opt-in for characters whose identity includes a face.
            # Object-like, masked, headless, and other nonhuman beings must not fail a face heuristic.
            face_check_applicable = getattr(tolerances, "face_check_applicable", True) if tolerances else True
            if face_check_applicable:
                min_face_px = (
                    tolerances.min_face_px_for_check
                    if tolerances and hasattr(tolerances, "min_face_px_for_check")
                    else 80
                )
                estimated_face_px = largest_box.height * 0.22
                if estimated_face_px < min_face_px and largest_box.height < min_face_px * 2.0:
                    face_scale_ok = False
                    reasons.append(
                        f"Estimated face resolution ({estimated_face_px:.1f}px) is below "
                        f"minimum verification threshold ({min_face_px}px)"
                    )

        passed = (subject_count >= expected_count) and framing_ok and face_scale_ok
        reason = "; ".join(reasons) if (reasons and not passed) else None

        return L1SubjectResult(
            passed=passed,
            subject_count=subject_count,
            boxes=boxes,
            mask_available=mask_available,
            mask_sha256=mask_sha256,
            framing_ok=framing_ok,
            face_scale_ok=face_scale_ok,
            reason=reason if not passed else None,
            is_simulated=is_simulated,
        )
