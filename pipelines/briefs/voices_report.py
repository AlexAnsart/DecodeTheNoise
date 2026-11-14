"""Measures the one-voice check the server runs, and writes `reports/voices/metrics.json`.

The server flags a selection whose actors are interchangeable (`backend/voices/`). This script
runs the same score on groups whose truth is known: real actors of 2026 (negatives), groups
written from one brief (positives), and a real troll operation (where do they fall?).

One threshold per measured group size, set on half of the real pools as the value 5% of the
hardest real groups fall under. Every rate is then counted on the other half and on arms the
threshold never saw.

Run: uv run --group pipelines python -m pipelines.briefs.voices_report
"""

import json
import logging
import re

import numpy as np

from backend.voices.score import DRAWS, PERMUTATIONS, SIZES, read_voices
from pipelines.briefs.bench import SEED
from pipelines.briefs.interchange_detector import BASE_RATES, is_calibration, precision
from pipelines.briefs.interchange_groups import (
    Group,
    ira_groups,
    most_alike,
    organic_groups,
    twin_groups,
)
from pipelines.briefs.vectors import served_key
from pipelines.briefs.voices_report_text import FOLDER, write_report

log = logging.getLogger("briefs.voices_report")

FLAG_QUANTILE = 0.05
ONE_BRIEF = ("shared", "solo", "persona")
REAL, HARD = "organic", "organic-alike"
NEAR_COPY = 0.5
_NOISE = re.compile(r"https?://\S+|[@#]\w+")


def wilson(flagged: int, groups: int) -> dict[str, float | int]:
    """A count as a rate with its 95% Wilson interval."""
    if groups == 0:
        return {"groups": 0, "flagged": 0, "rate": 0.0, "low": 0.0, "high": 1.0}
    z, rate = 1.96, flagged / groups
    centre = (rate + z * z / (2 * groups)) / (1 + z * z / groups)
    half = z * np.sqrt(rate * (1 - rate) / groups + z * z / (4 * groups**2)) / (1 + z * z / groups)
    return {
        "groups": groups,
        "flagged": flagged,
        "rate": round(rate, 3),
        "low": round(max(0.0, float(centre - half)), 3),
        "high": round(min(1.0, float(centre + half)), 3),
    }


def has_near_copy(group: Group) -> bool:
    """The baseline: two actors of the group posted almost the same text."""

    def grams(text: str) -> set[str]:
        clean = " ".join(_NOISE.sub(" ", text.lower()).split())
        return {clean[i : i + 5] for i in range(max(len(clean) - 4, 1))}

    sets = [grams(text) for text in group.texts]
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            if group.actors[i] != group.actors[j]:
                shared = len(sets[i] & sets[j])
                if shared >= NEAR_COPY * (len(sets[i]) + len(sets[j]) - shared):
                    return True
    return False


def held_out(arm: str, name: str) -> bool:
    return not (arm in (REAL, HARD) and is_calibration(name))


def measure(size: tuple[int, int], groups: list[Group], rng: np.random.Generator) -> dict:
    scores: dict[str, dict[str, float]] = {}
    for group in groups:
        voices = read_voices(group.vectors, group.actors, size, rng)
        if voices is not None:
            scores.setdefault(group.arm, {})[group.name] = voices.score
    calibration = [s for name, s in scores[HARD].items() if is_calibration(name)]
    threshold = float(np.quantile(calibration, FLAG_QUANTILE))

    def counted(arms: tuple[str, ...]) -> dict[str, float | int]:
        kept = [s for arm in arms for name, s in scores.get(arm, {}).items() if held_out(arm, name)]
        return wilson(sum(s < threshold for s in kept), len(kept))

    def spread(arms: tuple[str, ...]) -> list[float]:
        values = [s for arm in arms for s in scores.get(arm, {}).values()]
        return [round(float(v), 2) for v in np.quantile(values, [0.05, 0.95])]

    one_brief, hard = counted(ONE_BRIEF), counted((HARD,))
    return {
        "actors": size[0],
        "posts_each": size[1],
        "draws": DRAWS,
        "threshold": round(threshold, 2),
        "calibration_groups": len(calibration),
        "reference": {
            "independent": spread((REAL,)),
            "independent_alike": spread((HARD,)),
            "one_brief": spread(ONE_BRIEF),
        },
        "real": counted((REAL,)),
        "real_alike": hard,
        "one_brief": {**one_brief, "by_mode": {mode: counted((mode,)) for mode in ONE_BRIEF}},
        "ira": {arm: counted((arm,)) for arm in sorted(scores) if arm.startswith("ira")},
        "precision_at_base_rate": {
            str(rate): {
                "measured": round(precision(one_brief["rate"], hard["rate"], rate), 3),
                "worst_case": round(precision(one_brief["low"], hard["high"], rate), 3),
            }
            for rate in BASE_RATES
        },
        "flagged_real_groups": sorted(
            name
            for arm in (REAL, HARD)
            for name, s in scores[arm].items()
            if held_out(arm, name) and s < threshold
        ),
    }


def baseline(groups: list[Group]) -> dict[str, object]:
    """What a near-duplicate rule sees in the same groups."""

    def counted(arms: tuple[str, ...]) -> dict[str, float | int]:
        kept = [g for g in groups if g.arm in arms and held_out(g.arm, g.name)]
        return wilson(sum(has_near_copy(g) for g in kept), len(kept))

    return {
        "rule": f"two actors posted texts sharing {NEAR_COPY:.0%} of their character 5-grams",
        "real": counted((REAL,)),
        "one_brief": counted(ONE_BRIEF),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    organic = organic_groups()
    twins = [g for g in twin_groups() if g.arm in ONE_BRIEF]
    ira = [g for g in ira_groups() if not g.arm.endswith("untagged")]
    groups = [*organic, *map(most_alike, organic), *twins, *ira]
    rng = np.random.default_rng(SEED)
    metrics = {
        "title": "One voice or several",
        "evaluated": "2026-11-14",
        "embedding_key": str(served_key()),
        "unit": "a group of actors with several posts each",
        "positive": "the actors are interchangeable: any post could have come from any of them",
        "score": f"gap between posts of one actor and posts of different actors, in standard "
        f"deviations of {PERMUTATIONS} shuffles of who wrote what, averaged over {DRAWS} draws",
        "rule": f"flag under the value {FLAG_QUANTILE:.0%} of the most alike real groups fall "
        "under, on the calibration half of the real pools",
        "seed": SEED,
        "sizes": [measure(size, groups, rng) for size in SIZES],
        "baseline": baseline(groups),
        "limits": [
            "The real groups are actors who posted on one word in one month: looser than many "
            "people reacting to one event in one hour. Not tested on such groups.",
            "The groups written from one brief are synthetic: one writer model, fictional "
            "subjects.",
            "An operator who gives each actor its own subject passes the check.",
            "A fan campaign, a news feed or a posting tool is one voice too: the check says "
            "that actors are interchangeable, not why.",
            "Measured on English posts and on one embedding model.",
            "The real actors are not labelled: some may be scripted, so false alarms are an "
            "upper bound.",
        ],
        "report": "2026-11-14-benchmark.md",
    }
    FOLDER.mkdir(parents=True, exist_ok=True)
    (FOLDER / "metrics.json").write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")
    write_report(FOLDER / metrics["report"], metrics)
    for size in metrics["sizes"]:
        log.info(
            "%d x %d: threshold %s, real %s, most alike %s, one brief %s",
            size["actors"],
            size["posts_each"],
            size["threshold"],
            size["real"],
            size["real_alike"],
            {k: v for k, v in size["one_brief"].items() if k != "by_mode"},
        )
    log.info("written: %s", FOLDER / "metrics.json")


if __name__ == "__main__":
    main()
