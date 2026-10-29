"""
InkLoop Statistical Uncertainty, Agreement & Denominator Policy (Task T6.2).
Provides mathematical foundations for binomial confidence intervals,
inter-rater agreement (Cohen's Kappa), and strict sample denominator accounting.
"""
import math
from typing import List, Dict, Any, Tuple, Optional


def wilson_score_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """
    Computes the Wilson score interval for a binomial proportion.
    Unlike normal approximation (Wald interval), the Wilson interval performs well
    with small sample sizes and extreme probabilities (e.g. 0/6 or 6/6 in M0).
    Returns (lower_bound, upper_bound) bounded in [0.0, 1.0].
    """
    if total <= 0:
        return 0.0, 0.0

    if successes < 0 or successes > total:
        raise ValueError(f"Successes ({successes}) cannot be negative or exceed total ({total}).")

    # z-score lookup for common confidence levels
    z_table = {
        0.90: 1.64485,
        0.95: 1.95996,
        0.98: 2.32635,
        0.99: 2.57583,
    }
    z = z_table.get(round(confidence, 2), 1.95996)

    p_hat = successes / total
    z2 = z * z
    denominator = 1.0 + (z2 / total)
    center = (p_hat + (z2 / (2.0 * total))) / denominator
    margin = (z * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))) / denominator

    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return round(low, 4), round(high, 4)


def cohens_kappa(
    rater1: List[str],
    rater2: List[str],
    categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes Cohen's Kappa coefficient of inter-rater agreement for categorical items.
    Formula: kappa = (Po - Pe) / (1 - Pe)
    where Po is observed agreement and Pe is chance-expected agreement.
    """
    if len(rater1) != len(rater2):
        raise ValueError(f"Rater lists must have identical lengths: got {len(rater1)} vs {len(rater2)}.")

    n = len(rater1)
    if n == 0:
        return {
            "n_items": 0,
            "observed_agreement": 0.0,
            "expected_agreement": 0.0,
            "kappa": 0.0,
            "interpretation": "no_data",
            "limitations": ["No items evaluated."],
        }

    # Determine unique categories
    if categories is None:
        cats = sorted(list(set(rater1) | set(rater2)))
    else:
        cats = sorted(list(set(categories)))

    if not cats:
        return {
            "n_items": n,
            "observed_agreement": 0.0,
            "expected_agreement": 0.0,
            "kappa": 0.0,
            "interpretation": "no_categories",
            "limitations": ["No category labels found."],
        }

    # Confusion matrix
    matrix = {c1: {c2: 0 for c2 in cats} for c1 in cats}
    agreed_count = 0
    for r1, r2 in zip(rater1, rater2):
        if r1 in matrix and r2 in matrix[r1]:
            matrix[r1][r2] += 1
            if r1 == r2:
                agreed_count += 1

    po = agreed_count / n

    # Expected agreement by chance
    pe = 0.0
    for c in cats:
        r1_count = sum(matrix[c][c2] for c2 in cats)
        r2_count = sum(matrix[c1][c] for c1 in cats)
        pe += (r1_count / n) * (r2_count / n)

    if pe >= 1.0:
        kappa = 1.0 if po >= 1.0 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    # Landis & Koch interpretation benchmarks
    if kappa < 0:
        interpretation = "poor_less_than_chance"
    elif kappa <= 0.20:
        interpretation = "slight_agreement"
    elif kappa <= 0.40:
        interpretation = "fair_agreement"
    elif kappa <= 0.60:
        interpretation = "moderate_agreement"
    elif kappa <= 0.80:
        interpretation = "substantial_agreement"
    else:
        interpretation = "almost_perfect_agreement"

    return {
        "n_items": n,
        "categories": cats,
        "observed_agreement": round(po, 4),
        "expected_agreement": round(pe, 4),
        "kappa": round(kappa, 4),
        "interpretation": interpretation,
        "what_it_establishes": "Quantifies the degree of agreement above chance between two independent raters.",
        "what_it_does_not_establish": "Does not prove ground truth or objective correctness; raters can agree on shared bias.",
    }


def reconcile_sample_denominator(
    planned: int,
    completed: int,
    failed: int,
    filtered: int,
    unresolved: int,
    unfinished: int = 0,
) -> Dict[str, Any]:
    """
    Strict accounting check ensuring every sample is preserved in reporting denominators.
    Prevents selective omission of failed, filtered, or incomplete cases.
    """
    total_accounted = completed + failed + filtered + unresolved + unfinished
    if total_accounted != planned:
        raise ValueError(
            f"Denominator accounting mismatch: planned={planned} but "
            f"completed({completed}) + failed({failed}) + filtered({filtered}) + "
            f"unresolved({unresolved}) + unfinished({unfinished}) = {total_accounted}."
        )

    dispatched = completed + failed + filtered + unresolved
    completion_rate = (completed / planned) if planned > 0 else 0.0
    failure_rate = (failed / planned) if planned > 0 else 0.0
    filter_rate = (filtered / planned) if planned > 0 else 0.0
    unresolved_rate = (unresolved / planned) if planned > 0 else 0.0

    return {
        "planned_samples": planned,
        "dispatched_samples": dispatched,
        "completed_samples": completed,
        "failed_samples": failed,
        "filtered_samples": filtered,
        "unresolved_samples": unresolved,
        "unfinished_samples": unfinished,
        "completion_rate": round(completion_rate, 4),
        "failure_rate": round(failure_rate, 4),
        "filter_rate": round(filter_rate, 4),
        "unresolved_rate": round(unresolved_rate, 4),
        "is_reconciled": True,
    }
