"""Test 2: are the actors of a group interchangeable? Runs the test on every arm.

Two readings of the same statistic. The permutation test says whether shuffling who wrote what
changes anything, in meaning and in style, at a level fixed at 5% before any data is read. The
detector puts one threshold on the meaning z-score, set on half of the real pools.

Run: uv run --group pipelines python -m pipelines.briefs.interchange_run
"""

import logging
from collections import defaultdict

import numpy as np

from backend.voices.score import ALPHA, PERMUTATIONS, cosine, draw, interchange_test
from pipelines.briefs.bench import SEED, write_result
from pipelines.briefs.interchange import style_similarity
from pipelines.briefs.interchange_detector import detector
from pipelines.briefs.interchange_groups import (
    Group,
    ira_groups,
    most_alike,
    organic_groups,
    twin_groups,
)
from pipelines.briefs.ncurve import interval, rounded

log = logging.getLogger("briefs.interchange")

# (actors, posts per actor). The first size is the one the headline numbers are read at.
SIZES = ((6, 6), (6, 4), (6, 3), (6, 2), (4, 6), (3, 6))
DRAWS = 20
MEASURES = (
    "interchangeable",
    "told_apart_meaning",
    "told_apart_style",
    "z_meaning",
    "z_style",
    "attribution_meaning",
    "attribution_style",
    "tightness",
)


def score(
    group: Group,
    size: tuple[int, int],
    scale: tuple[np.ndarray, np.ndarray],
    rng: np.random.Generator,
    draws: int,
) -> tuple[dict[str, float], np.ndarray] | None:
    """Means over the draws of one group at one size, and the meaning z-score of each draw."""
    totals: dict[str, list[float]] = defaultdict(list)
    for _ in range(draws):
        rows = draw(group.actors, size, rng)
        if rows is None:
            return None
        who = group.actors[rows]
        meaning_scores = cosine(group.vectors[rows])
        meaning = interchange_test(meaning_scores, who, rng)
        style = interchange_test(
            style_similarity((group.style[rows] - scale[0]) / scale[1]), who, rng
        )
        totals["interchangeable"].append(float(meaning.p >= ALPHA and style.p >= ALPHA))
        totals["told_apart_meaning"].append(float(meaning.p < ALPHA))
        totals["told_apart_style"].append(float(style.p < ALPHA))
        totals["z_meaning"].append(meaning.z)
        totals["z_style"].append(style.z)
        totals["attribution_meaning"].append(meaning.attribution)
        totals["attribution_style"].append(style.attribution)
        apart = ~np.eye(len(rows), dtype=bool)
        totals["tightness"].append(float(meaning_scores[apart].mean()))
    means = {name: float(np.mean(values)) for name, values in totals.items()}
    return means, np.array(totals["z_meaning"])


def auc(high: np.ndarray, low: np.ndarray) -> float:
    """Chance that a value of `high` exceeds a value of `low`; ties count for half."""
    wins = (high[:, None] > low[None, :]).mean() + 0.5 * (high[:, None] == low[None, :]).mean()
    return float(wins)


def separation(organic: np.ndarray, arm: np.ndarray, rng: np.random.Generator) -> list[float]:
    """AUC of organic against one arm, with a 95% interval from resampling both sides."""
    resampled = [
        auc(rng.choice(organic, len(organic)), rng.choice(arm, len(arm))) for _ in range(1000)
    ]
    low, high = np.quantile(resampled, [0.025, 0.975])
    return [round(auc(organic, arm), 3), round(float(low), 3), round(float(high), 3)]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    rng = np.random.default_rng(SEED)
    organic = organic_groups()
    groups = [*organic, *map(most_alike, organic), *twin_groups(), *ira_groups()]
    # Style features are standardised once, on the real and synthetic posts of 2026 together.
    pooled = np.concatenate([g.style for g in groups if not g.arm.startswith("ira")])
    scale = (pooled.mean(axis=0), pooled.std(axis=0) + 1e-9)

    arms: dict[str, dict[str, object]] = {}
    per_group: list[dict[str, object]] = []
    primary: dict[str, dict[str, np.ndarray]] = {}
    draws: dict[str, dict[str, np.ndarray]] = {}
    for arm in sorted({g.arm for g in groups}):
        members = [g for g in groups if g.arm == arm]
        by_size: dict[str, object] = {}
        for size in SIZES:
            draws_here = DRAWS if size == SIZES[0] else DRAWS // 2
            scored = [
                (g, s) for g in members if (s := score(g, size, scale, rng, draws_here)) is not None
            ]
            table = {m: np.array([means[m] for _, (means, _) in scored]) for m in MEASURES}
            by_size[f"{size[0]}x{size[1]}"] = {
                "groups": len(scored),
                "chance_attribution": round(1 / size[0], 3),
                **{m: rounded(interval(table[m], rng)) for m in MEASURES},
            }
            if size == SIZES[0]:
                primary[arm] = table
                draws[arm] = {g.name: z for g, (_, z) in scored}
                per_group += [{"arm": arm, "group": g.name, **means} for g, (means, _) in scored]
        arms[arm] = {"groups": len(members), "by_size": by_size}
        log.info(
            "%s: %d groups, interchangeable at %s: %s",
            arm,
            len(members),
            SIZES[0],
            by_size[f"{SIZES[0][0]}x{SIZES[0][1]}"]["interchangeable"],
        )

    # How well the z-score alone ranks real groups above each other arm, without any threshold.
    separations = {
        arm: {
            f"{real}:{name}": separation(primary[real][name], table[name], rng)
            for real in ("organic", "organic-alike")
            for name in ("z_meaning", "z_style")
        }
        for arm, table in primary.items()
        if not arm.startswith("organic")
    }
    payload = {
        "seed": SEED,
        "alpha": ALPHA,
        "permutations": PERMUTATIONS,
        "draws_per_group": {"primary_size": DRAWS, "other_sizes": DRAWS // 2},
        "sizes": [f"{a}x{p}" for a, p in SIZES],
        "interval": "95%, bootstrap over groups",
        "arms": arms,
        "organic_against_arm_auc": separations,
        "detector": detector(draws, rng),
        "groups_at_primary_size": per_group,
    }
    log.info("written: %s", write_result("interchangeable-actors", payload))


if __name__ == "__main__":
    main()
