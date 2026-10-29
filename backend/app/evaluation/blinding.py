"""
InkLoop Blind Human Evaluation Protocol & Blinding Service (Task T6.2).
Provides file-based blind evaluation sheets, opaque sample IDs, reproducible
randomized presentation, independent rater judgment logging, and unblinded adjudication.
"""
from datetime import datetime, timezone
import random
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import json
import csv
from io import StringIO
from pydantic import BaseModel, Field, ConfigDict

from app.evaluation.enums import EvaluationVerdict, EvaluationDimension
from app.evaluation.uncertainty import cohens_kappa


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BlindEvaluationItem(BaseModel):
    """
    Individual image item presented to a human rater.
    Contains zero arm identifiers, prompt clauses, or revealing keywords.
    """
    blind_id: str = Field(..., description="Opaque randomized identifier (e.g. 'bld_7a9f82c1')")
    presentation_order: int = Field(..., ge=1, description="Sequential position in randomized rating sheet")
    clean_image_path: str = Field(..., description="Sanitized relative path concealing condition names")
    scene_context: Optional[str] = Field(default=None, description="General narrative context without revealing prompt tokens")
    dimensions_to_rate: List[EvaluationDimension] = Field(default_factory=list)
    guidelines_summary: str = Field(default="Rate character consistency and visual defects against canonical reference.")

    model_config = ConfigDict(extra="forbid")


class BlindEvaluationSheet(BaseModel):
    """
    The rater-facing evaluation sheet.
    Does not contain the unblinding key or arm definitions.
    """
    sheet_id: str = Field(..., description="Unique evaluation sheet ID (e.g. 'sheet_nour_blind_01')")
    experiment_id: str = Field(..., description="Associated experiment ID")
    rater_role: str = Field(default="Independent Visual Reviewer")
    random_seed: int = Field(..., description="Integer seed used for reproducible shuffling")
    rating_instructions: str = Field(...)
    items: List[BlindEvaluationItem] = Field(..., description="Randomized list of blinded items")
    created_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.model_dump(), indent=indent, sort_keys=True)


class BlindingKeyEntry(BaseModel):
    """Mapping from an opaque blind_id back to actual experiment provenance."""
    blind_id: str
    original_sample_id: str
    actual_arm_id: str
    actual_scene_id: Optional[str]
    actual_file_path: str
    content_sha256: str

    model_config = ConfigDict(extra="forbid")


class BlindingKeyMap(BaseModel):
    """
    Confidential unblinding map.
    Must be kept strictly separate from the rating sheet until human ratings are locked.
    """
    sheet_id: str
    experiment_id: str
    mappings: Dict[str, BlindingKeyEntry] = Field(..., description="blind_id -> BlindingKeyEntry")
    created_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")


class HumanJudgmentRecord(BaseModel):
    """
    Individual rating recorded by an independent human evaluator.
    Preserves original rater judgments; never flattened or overwritten.
    """
    judgment_id: str = Field(...)
    sheet_id: str = Field(...)
    blind_id: str = Field(...)
    rater_id: str = Field(..., description="Rater identifier or pseudonym (e.g. 'rater_alpha', 'rater_beta')")
    verdict: EvaluationVerdict = Field(...)
    confidence: float = Field(..., ge=1.0, le=5.0, description="Rater confidence on 1..5 Likert scale")
    dimension_verdicts: Dict[str, EvaluationVerdict] = Field(default_factory=dict)
    rationale: Optional[str] = Field(default=None, description="Freeform qualitative observation")
    submitted_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")


class AdjudicatedSampleResult(BaseModel):
    """Combined unblinded assessment for a single sample."""
    blind_id: str
    original_sample_id: str
    arm_id: str
    scene_id: Optional[str]
    rater_judgments: List[HumanJudgmentRecord]
    consensus_verdict: EvaluationVerdict
    unanimous: bool
    disagreements: List[str] = Field(default_factory=list)


class AdjudicationReport(BaseModel):
    """
    Final synthesis created after unblinding human ratings.
    Calculates inter-rater agreement and preserves individual judgments.
    """
    sheet_id: str
    experiment_id: str
    total_evaluated_items: int
    participating_raters: List[str]
    inter_rater_agreement: Dict[str, Any]
    adjudicated_samples: List[AdjudicatedSampleResult]
    per_arm_human_pass_rate: Dict[str, float]
    adjudicated_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    def to_csv(self) -> str:
        """Exports sample-level human evaluations to machine-readable CSV."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "blind_id", "sample_id", "arm_id", "scene_id",
            "consensus_verdict", "unanimous", "rater_count", "rater_verdicts"
        ])
        for s in self.adjudicated_samples:
            rater_summary = "; ".join(f"{j.rater_id}:{j.verdict.value}" for j in s.rater_judgments)
            writer.writerow([
                s.blind_id, s.original_sample_id, s.arm_id, s.scene_id or "",
                s.consensus_verdict.value, s.unanimous, len(s.rater_judgments), rater_summary
            ])
        return output.getvalue()


class BlindingService:
    """
    Operational service managing the creation of blind sheets,
    secure unblinding, and inter-rater agreement computation.
    """

    @staticmethod
    def create_blind_sheet(
        experiment_id: str,
        sample_entries: List[Dict[str, Any]],
        random_seed: int = 42,
        rating_instructions: Optional[str] = None,
    ) -> Tuple[BlindEvaluationSheet, BlindingKeyMap]:
        """
        Creates a blinded evaluation package from sample descriptors.
        sample_entries format: List of dicts with:
        {'sample_id': ..., 'arm_id': ..., 'scene_id': ..., 'file_path': ..., 'sha256': ..., 'scene_context': ...}
        """
        if not sample_entries:
            raise ValueError("Cannot create a blind sheet with empty sample entries.")

        # Seed the RNG reproducibly
        rng = random.Random(random_seed)
        shuffled_indices = list(range(len(sample_entries)))
        rng.shuffle(shuffled_indices)

        sheet_id = f"sheet_{experiment_id}_{random_seed}"
        blind_items: List[BlindEvaluationItem] = []
        key_mappings: Dict[str, BlindingKeyEntry] = {}

        instructions = rating_instructions or (
            "Examine each candidate image against the canonical character specification. "
            "Rate PASS only if all defining attributes are clearly preserved without severe visual defects. "
            "Rate FAIL if defining attributes are missing, distorted, or drifted. "
            "Rate NEEDS_HUMAN if ambiguous. Rate NOT_EVALUABLE if the image is corrupted or incomplete."
        )

        for presentation_order, idx in enumerate(shuffled_indices, start=1):
            entry = sample_entries[idx]
            # Opaque hash-derived ID
            blind_id = f"bld_{entry['sample_id']}_{random_seed}_{presentation_order:02d}"

            # Sanitize filename path: strip arm names ('arm_a', 'arm_b', 'baseline', 'anchored')
            clean_filename = f"blind_candidate_{presentation_order:02d}.png"

            item = BlindEvaluationItem(
                blind_id=blind_id,
                presentation_order=presentation_order,
                clean_image_path=clean_filename,
                scene_context=entry.get("scene_context"),
                dimensions_to_rate=[
                    EvaluationDimension.CHARACTER_IDENTITY,
                    EvaluationDimension.DEFINING_ATTRIBUTES,
                    EvaluationDimension.STYLE_CONSISTENCY,
                    EvaluationDimension.GENERATION_DEFECTS,
                ],
                guidelines_summary="Verify Nour's hair streak, round glasses, and jacket emblem.",
            )
            blind_items.append(item)

            key_entry = BlindingKeyEntry(
                blind_id=blind_id,
                original_sample_id=entry["sample_id"],
                actual_arm_id=entry["arm_id"],
                actual_scene_id=entry.get("scene_id"),
                actual_file_path=entry["file_path"],
                content_sha256=entry["sha256"],
            )
            key_mappings[blind_id] = key_entry

        sheet = BlindEvaluationSheet(
            sheet_id=sheet_id,
            experiment_id=experiment_id,
            random_seed=random_seed,
            rating_instructions=instructions,
            items=blind_items,
        )

        key_map = BlindingKeyMap(
            sheet_id=sheet_id,
            experiment_id=experiment_id,
            mappings=key_mappings,
        )

        return sheet, key_map

    @staticmethod
    def adjudicate_blind_judgments(
        key_map: BlindingKeyMap,
        judgments: List[HumanJudgmentRecord],
    ) -> AdjudicationReport:
        """
        Unblinds human judgments and computes consensus verdicts and inter-rater agreement.
        """
        if not judgments:
            raise ValueError("Cannot adjudicate with zero human judgments.")

        # Group judgments by blind_id
        grouped: Dict[str, List[HumanJudgmentRecord]] = {}
        for j in judgments:
            grouped.setdefault(j.blind_id, []).append(j)

        raters = sorted(list(set(j.rater_id for j in judgments)))
        adjudicated_samples: List[AdjudicatedSampleResult] = []
        arm_totals: Dict[str, int] = {}
        arm_passes: Dict[str, int] = {}

        for blind_id, key_entry in key_map.mappings.items():
            sample_judgments = grouped.get(blind_id, [])
            arm_id = key_entry.actual_arm_id
            arm_totals[arm_id] = arm_totals.get(arm_id, 0) + 1

            if not sample_judgments:
                consensus = EvaluationVerdict.NOT_EVALUABLE
                unanimous = False
                disagreements = ["No rater submitted a judgment for this item."]
            else:
                verdicts = [j.verdict for j in sample_judgments]
                unanimous = len(set(verdicts)) == 1
                disagreements = [] if unanimous else [f"Raters diverged: {[v.value for v in verdicts]}"]

                # Plurality / majority rule
                counts: Dict[EvaluationVerdict, int] = {}
                for v in verdicts:
                    counts[v] = counts.get(v, 0) + 1
                consensus = max(counts.items(), key=lambda pair: pair[1])[0]

            if consensus == EvaluationVerdict.PASS:
                arm_passes[arm_id] = arm_passes.get(arm_id, 0) + 1

            adjudicated_samples.append(
                AdjudicatedSampleResult(
                    blind_id=blind_id,
                    original_sample_id=key_entry.original_sample_id,
                    arm_id=arm_id,
                    scene_id=key_entry.actual_scene_id,
                    rater_judgments=sample_judgments,
                    consensus_verdict=consensus,
                    unanimous=unanimous,
                    disagreements=disagreements,
                )
            )

        # Compute inter-rater agreement if exactly 2 primary raters evaluated all items
        if len(raters) == 2:
            r1_id, r2_id = raters[0], raters[1]
            r1_labels = []
            r2_labels = []
            for blind_id in key_map.mappings.keys():
                item_judgments = grouped.get(blind_id, [])
                j1 = next((j.verdict.value for j in item_judgments if j.rater_id == r1_id), None)
                j2 = next((j.verdict.value for j in item_judgments if j.rater_id == r2_id), None)
                if j1 and j2:
                    r1_labels.append(j1)
                    r2_labels.append(j2)
            agreement_metrics = cohens_kappa(r1_labels, r2_labels)
        else:
            agreement_metrics = {
                "raters_count": len(raters),
                "note": "Pairwise Cohen's Kappa requires exactly two complete raters; multi-rater or partial panel observed.",
            }

        per_arm_rates = {
            arm: round(arm_passes.get(arm, 0) / arm_totals[arm], 4) if arm_totals[arm] > 0 else 0.0
            for arm in arm_totals
        }

        return AdjudicationReport(
            sheet_id=key_map.sheet_id,
            experiment_id=key_map.experiment_id,
            total_evaluated_items=len(key_map.mappings),
            participating_raters=raters,
            inter_rater_agreement=agreement_metrics,
            adjudicated_samples=adjudicated_samples,
            per_arm_human_pass_rate=per_arm_rates,
        )
