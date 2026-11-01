"""
InkLoop Visual Verification Service - L0 Deterministic Code Checker.
Provides zero-cost, deterministic preflight validation of candidate panel images:
- File decodability and structural integrity (PNG/JPEG/WebP)
- Non-blank / solid color detection (variance & entropy)
- Dimension and aspect ratio conformance
- Sheet-bleed & artificial border ring detection
"""
import io
from typing import Optional, Tuple, Dict, Any
from PIL import Image
import numpy as np

from app.verification.schemas import L0CheckResult

VALID_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}


class L0CodeChecker:
    """
    Tier-0 Deterministic Image Validator.
    Rejects malformed, blank, distorted, or artifact-bordered panels
    before incurring expensive downstream API costs.
    """

    def __init__(
        self,
        min_pixel_std: float = 2.0,
        aspect_ratio_tolerance: float = 0.05,
        border_thickness: int = 4,
        max_border_uniformity: float = 0.98,
        min_inner_variance_for_bleed: float = 12.0,
    ):
        self.min_pixel_std = min_pixel_std
        self.aspect_ratio_tolerance = aspect_ratio_tolerance
        self.border_thickness = border_thickness
        self.max_border_uniformity = max_border_uniformity
        self.min_inner_variance_for_bleed = min_inner_variance_for_bleed

    def check(
        self,
        candidate_bytes: bytes,
        *,
        target_dimensions: Optional[Tuple[int, int]] = None,
        target_aspect_ratio: Optional[str] = None,
        check_sheet_bleed: bool = True,
        asset_profile: str = "panel",
    ) -> L0CheckResult:
        """
        Executes all L0 deterministic checks on raw image bytes.
        Returns L0CheckResult with passed=True only if all checks succeed.
        """
        checks: Dict[str, bool] = {
            "decodable": False,
            "format_valid": False,
            "dimensions_positive": False,
            "non_blank": False,
            "aspect_ratio_match": True,
            "dimensions_match": True,
            "no_sheet_bleed": True,
        }

        if not candidate_bytes or len(candidate_bytes) == 0:
            return L0CheckResult(
                passed=False,
                checks=checks,
                reason="Candidate image bytes are empty",
            )

        # 1. Structural Verification with PIL
        try:
            # First pass: verify file format integrity
            bio_verify = io.BytesIO(candidate_bytes)
            img_verify = Image.open(bio_verify)
            fmt = (img_verify.format or "").upper()
            img_verify.verify()

            if fmt not in VALID_IMAGE_FORMATS:
                return L0CheckResult(
                    passed=False,
                    checks=checks,
                    reason=f"Invalid image format '{fmt}'. Expected one of {sorted(VALID_IMAGE_FORMATS)}",
                )
            checks["format_valid"] = True
            checks["decodable"] = True

            # Second pass: load pixel buffer for raster analysis
            bio_load = io.BytesIO(candidate_bytes)
            img = Image.open(bio_load)
            img.load()
            w, h = img.size
        except Exception as e:
            return L0CheckResult(
                passed=False,
                checks=checks,
                reason=f"Failed to decode image bytes: {str(e)}",
            )

        # 2. Positive Dimensions
        if w <= 0 or h <= 0:
            return L0CheckResult(
                passed=False,
                checks=checks,
                reason=f"Non-positive image dimensions: {w}x{h}",
                dimensions=(w, h),
            )
        checks["dimensions_positive"] = True
        actual_aspect_ratio = round(float(w) / float(h), 4)

        # 3. Target Dimensions Matching (if specified)
        if target_dimensions is not None:
            tw, th = target_dimensions
            if w != tw or h != th:
                checks["dimensions_match"] = False
                return L0CheckResult(
                    passed=False,
                    checks=checks,
                    reason=f"Dimension mismatch: expected {tw}x{th}, found {w}x{h}",
                    dimensions=(w, h),
                    aspect_ratio=actual_aspect_ratio,
                )

        # 4. Target Aspect Ratio Matching (if specified)
        if target_aspect_ratio is not None:
            try:
                parts = target_aspect_ratio.split(":")
                if len(parts) == 2:
                    expected_ratio = float(parts[0]) / float(parts[1])
                    diff_pct = abs(actual_aspect_ratio - expected_ratio) / expected_ratio
                    if diff_pct > self.aspect_ratio_tolerance:
                        checks["aspect_ratio_match"] = False
                        return L0CheckResult(
                            passed=False,
                            checks=checks,
                            reason=(
                                f"Aspect ratio mismatch: expected {target_aspect_ratio} "
                                f"({expected_ratio:.3f}), found {actual_aspect_ratio:.3f} "
                                f"(deviation {diff_pct*100:.1f}% > {self.aspect_ratio_tolerance*100:.1f}%)"
                            ),
                            dimensions=(w, h),
                            aspect_ratio=actual_aspect_ratio,
                        )
            except Exception:
                # Malformed aspect ratio spec string; skip check
                pass

        # 5. Non-Blank / Variance Analysis
        rgb_img = img.convert("RGB")
        arr = np.array(rgb_img, dtype=np.float32)
        pixel_std = float(np.std(arr))

        if pixel_std < self.min_pixel_std:
            checks["non_blank"] = False
            return L0CheckResult(
                passed=False,
                checks=checks,
                reason=f"Candidate image is blank or solid color (pixel std={pixel_std:.2f} < {self.min_pixel_std})",
                dimensions=(w, h),
                aspect_ratio=actual_aspect_ratio,
                pixel_std=pixel_std,
            )
        checks["non_blank"] = True

        # 6. Sheet Bleed & Artificial Border Ring Detection
        border_uniformity = 0.0
        if check_sheet_bleed and w > (self.border_thickness * 2 + 10) and h > (self.border_thickness * 2 + 10):
            bt = self.border_thickness
            top_border = arr[:bt, :, :]
            bottom_border = arr[-bt:, :, :]
            left_border = arr[bt:-bt, :bt, :]
            right_border = arr[bt:-bt, -bt:, :]

            border_pixels = np.concatenate([
                top_border.reshape(-1, 3),
                bottom_border.reshape(-1, 3),
                left_border.reshape(-1, 3),
                right_border.reshape(-1, 3),
            ], axis=0)

            inner_pixels = arr[bt:-bt, bt:-bt, :].reshape(-1, 3)
            inner_std = float(np.std(inner_pixels))
            border_std = float(np.std(border_pixels))

            # If inner image is textured and complex, but the perimeter border is completely flat
            # (e.g. artificial solid white/black margin produced by anchor bleed)
            if inner_std > self.min_inner_variance_for_bleed:
                # Check how close the border pixels are to pure white (255) or pure black (0)
                mean_border_val = float(np.mean(border_pixels))
                is_solid_white_border = (mean_border_val > 250.0 and border_std < 1.5)
                is_solid_black_border = (mean_border_val < 5.0 and border_std < 1.5)

                if is_solid_white_border or is_solid_black_border:
                    border_uniformity = 1.0 - min(border_std / 10.0, 1.0)
                    checks["no_sheet_bleed"] = False
                    return L0CheckResult(
                        passed=False,
                        checks=checks,
                        reason=(
                            f"Sheet bleed detected: candidate contains an artificial solid border ring "
                            f"(border_std={border_std:.2f}, inner_std={inner_std:.2f})"
                        ),
                        dimensions=(w, h),
                        aspect_ratio=actual_aspect_ratio,
                        pixel_std=pixel_std,
                        border_uniformity=border_uniformity,
                    )

        # All L0 checks passed
        return L0CheckResult(
            passed=True,
            checks=checks,
            reason=None,
            dimensions=(w, h),
            aspect_ratio=actual_aspect_ratio,
            pixel_std=pixel_std,
            border_uniformity=border_uniformity,
        )
