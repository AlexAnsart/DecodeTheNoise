"""From a score to a detector: one threshold on the meaning z-score, set on real groups.

The z-score says how much more two posts by one actor resemble each other than two posts by
different actors. Real actors score high. The threshold is the value under which only 5% of
the hardest real groups fall, on one half of the real pools; every rate is then measured on
the other half and on the arms the threshold never saw.
"""

import hashlib

import numpy as np

from pipelines.briefs.ncurve import interval, rounded

FLAG_QUANTILE = 0.05
CALIBRATION_ARM = "organic-alike"
BASE_RATES = (0.01, 0.05, 0.2)
Draws = dict[str, dict[str, np.ndarray]]  # arm -> group -> z-score of each draw


def is_calibration(group: str) -> bool:
    """A hash of the pool's name puts it on one side, the same on every run."""
    return int(hashlib.sha256(group.encode("utf-8")).hexdigest()[:8], 16) % 2 == 0


def precision(recall: float, false_positive_rate: float, base_rate: float) -> float:
    flagged = recall * base_rate + false_positive_rate * (1 - base_rate)
    return recall * base_rate / flagged if flagged else float("nan")


def detector(draws: Draws, rng: np.random.Generator) -> dict[str, object]:
    calibration = [z for name, z in draws[CALIBRATION_ARM].items() if is_calibration(name)]
    threshold = float(np.quantile(np.concatenate(calibration), FLAG_QUANTILE))
    flagged: dict[str, dict[str, object]] = {}
    for arm, groups in draws.items():
        # Real pools used to set the threshold are not scored again.
        held_out = {
            name: z
            for name, z in groups.items()
            if not (arm.startswith("organic") and is_calibration(name))
        }
        shares = np.array([float((z < threshold).mean()) for z in held_out.values()])
        flagged[arm] = {"groups": len(shares), "rate": rounded(interval(shares, rng))}
    real = flagged[CALIBRATION_ARM]
    # With no false positive seen in n groups, the rate can still be about 3 / n.
    ceiling = max(real["rate"][2], 3 / real["groups"])
    return {
        "score": "z_meaning",
        "rule": f"flag a group whose score is below the {FLAG_QUANTILE:.0%} quantile of the "
        f"calibration draws of `{CALIBRATION_ARM}`",
        "threshold": round(threshold, 3),
        "calibration_groups": len(calibration),
        "flagged": flagged,
        "false_positive_rate": {"measured": real["rate"][0], "upper_bound": round(ceiling, 3)},
        "precision_at_base_rate": {
            arm: {
                str(rate): {
                    "measured": round(precision(values["rate"][0], real["rate"][0], rate), 3),
                    "worst_case": round(precision(values["rate"][0], ceiling, rate), 3),
                }
                for rate in BASE_RATES
            }
            for arm, values in flagged.items()
            if not arm.startswith(("organic", "ira"))
        },
    }
