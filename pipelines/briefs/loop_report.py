"""Test 3, the numbers: what the loop recovered, measured on the hidden half only.

Two spaces are measured. In the space of posts: how close the posts written from a recovered
instruction land to the hidden posts. In the space of prompts: how close the recovered
instruction is to the true one. A loop can gain in the first and lose in the second.

Run: uv run --group pipelines python -m pipelines.briefs.loop_report
"""

import json
import logging
from collections import Counter

import numpy as np

from pipelines.briefs.bench import SEED, write_result
from pipelines.briefs.fields import LEVELS, operator_prompt
from pipelines.briefs.loop import ROUNDS, energy_distance
from pipelines.briefs.loop_prompts import POSTS_PER_ROUND, PROMPT_VERSION
from pipelines.briefs.loop_run import LOOP_FILE, targets
from pipelines.briefs.ncurve import RESAMPLES, interval, rounded
from pipelines.briefs.vectors import embed

log = logging.getLogger("briefs.loop_report")

EXAMPLES = 3
Run = dict[str, object]


def pooled_fit(runs: list[Run], distances: np.ndarray, rng: np.random.Generator) -> list[float]:
    """Share of the way from the floor (subject alone) to the ceiling (true instruction).

    Summed over briefs before dividing: one brief whose floor and ceiling nearly coincide
    cannot blow the ratio up. Above 1 means closer to the hidden posts than the true
    instruction got.
    """
    floor = np.array([run["floor"]["hidden_distance"] for run in runs])
    ceiling = np.array([run["ceiling"]["hidden_distance"] for run in runs])
    picks = rng.integers(0, len(runs), size=(RESAMPLES, len(runs)))
    gained, span = (floor - distances)[picks].sum(axis=1), (floor - ceiling)[picks].sum(axis=1)
    low, high = np.quantile(gained / span, [0.025, 0.975])
    point = (floor - distances).sum() / (floor - ceiling).sum()
    return [round(float(v), 3) for v in (point, low, high)]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    runs: list[Run] = json.loads(LOOP_FILE.read_text(encoding="utf-8"))["runs"]
    runs = [run for run in runs if len(run["rounds"]) == ROUNDS + 1]
    all_targets = targets()
    real_gap = {t.brief.id: energy_distance(t.seen, t.hidden) for t in all_targets}
    hidden = {t.brief.id: t.hidden for t in all_targets}
    true_prompt = {t.brief.id: operator_prompt(t.brief) for t in all_targets}
    same_topic = {
        t.brief.id: [o.brief.id for o in all_targets if o.brief.topic == t.brief.topic]
        for t in all_targets
    }
    picked = [run["rounds"][run["chosen"]] for run in runs]
    first = [run["rounds"][0] for run in runs]
    stages = {
        "floor_subject_alone": [run["floor"] for run in runs],
        "round_0": first,
        "chosen_round": picked,
        # The chosen instruction run once more: posts the search never saw.
        "chosen_round_fresh_posts": [run["fresh"] for run in runs],
        "ceiling_true_instruction": [run["ceiling"] for run in runs],
    }
    # One embedding call for every text the report compares.
    texts = sorted(
        {post for stage in stages.values() for entry in stage for post in entry["posts"]}
        | {entry["prompt"] for stage in stages.values() for entry in stage}
        | set(true_prompt.values())
    )
    vector = dict(zip(texts, embed(texts)[0], strict=True))
    rng = np.random.default_rng(SEED)

    def summary(values: list[float]) -> list[float]:
        return rounded(interval(np.array(values, dtype=float), rng))

    def first_by_posts(run: Run, entry: Run) -> bool:
        """Are the hidden posts of the true brief the closest, among its topic's briefs?"""
        written = np.stack([vector[post] for post in entry["posts"]])
        return run["brief"] == min(
            same_topic[run["brief"]], key=lambda b: energy_distance(written, hidden[b])
        )

    def first_by_prompt(run: Run, entry: Run) -> bool:
        """Is the true instruction the closest to the recovered one, among its topic's?"""
        return run["brief"] == max(
            same_topic[run["brief"]], key=lambda b: vector[entry["prompt"]] @ vector[true_prompt[b]]
        )

    def distance(stage: list[Run]) -> np.ndarray:
        return np.array([entry["hidden_distance"] for entry in stage])

    fresh = stages["chosen_round_fresh_posts"]
    gain = distance(first) - distance(fresh)
    # Does what the search sees (seen half) say what it cannot see (hidden half)?
    seen_gain = [
        f["seen_distance"] - p["seen_distance"] for f, p in zip(first, picked, strict=True)
    ]
    hidden_gain = distance(first) - distance(picked)
    payload = {
        "model": "gemini-3.8-flash",
        "prompt_version": PROMPT_VERSION,
        "writer_temperature": 1.0,
        "rounds": ROUNDS,
        "posts_per_round": POSTS_PER_ROUND,
        "briefs": len(runs),
        "briefs_per_topic": round(float(np.mean([len(v) for v in same_topic.values()])), 1),
        "interval": "95%, bootstrap over briefs",
        "posts_space": {
            "distance_to_hidden_half": {
                "seen_half_of_the_same_brief": summary([real_gap[run["brief"]] for run in runs]),
                **{name: summary(list(distance(stage))) for name, stage in stages.items()},
                **{
                    f"round_{r}": summary([run["rounds"][r]["hidden_distance"] for run in runs])
                    for r in range(1, ROUNDS + 1)
                },
            },
            "fit": {
                "round_0": pooled_fit(runs, distance(first), rng),
                "chosen_round": pooled_fit(runs, distance(picked), rng),
                "chosen_round_fresh_posts": pooled_fit(runs, distance(fresh), rng),
            },
            "distance_gained_by_the_loop": summary(list(gain)),
            "share_of_briefs_the_loop_brought_closer": round(float((gain > 0).mean()), 3),
            "correlation_of_gain_on_seen_and_on_hidden": round(
                float(np.corrcoef(seen_gain, hidden_gain)[0, 1]), 2
            ),
            "true_brief_ranked_first_in_its_topic": {
                name: summary(
                    [first_by_posts(run, entry) for run, entry in zip(runs, stage, strict=True)]
                )
                for name, stage in stages.items()
            },
        },
        "prompt_space": {
            "cosine_to_true_instruction": {
                name: summary(
                    [
                        float(vector[entry["prompt"]] @ vector[true_prompt[run["brief"]]])
                        for run, entry in zip(runs, stage, strict=True)
                    ]
                )
                for name, stage in stages.items()
                if name != "ceiling_true_instruction"
            },
            "true_instruction_ranked_first_in_its_topic": {
                name: summary(
                    [first_by_prompt(run, entry) for run, entry in zip(runs, stage, strict=True)]
                )
                for name, stage in stages.items()
                if name != "ceiling_true_instruction"
            },
            "words": {
                "true_instruction": summary([len(true_prompt[r["brief"]].split()) for r in runs]),
                "round_0": summary([len(entry["prompt"].split()) for entry in first]),
                "chosen_round": summary([len(entry["prompt"].split()) for entry in picked]),
            },
        },
        "fields_exact_match": {
            name: {
                stage_name: summary(
                    [
                        entry["fields"].get(name) == run["truth"][name]
                        for run, entry in zip(runs, s, strict=True)
                    ]
                )
                for stage_name, s in (("round_0", first), ("chosen_round", picked))
            }
            for name in LEVELS
        },
        "chosen_round_counts": dict(sorted(Counter(run["chosen"] for run in runs).items())),
        "examples": [
            {
                "brief": run["brief"],
                "true_instruction": run["true_prompt"],
                "round_0": run["rounds"][0]["prompt"],
                "chosen_round": run["chosen"],
                "chosen": run["rounds"][run["chosen"]]["prompt"],
                "differences_named_by_the_editor": run["rounds"][run["chosen"]]["differences"],
            }
            for run in runs[:EXAMPLES]
        ],
    }
    log.info("posts space: %s", payload["posts_space"]["fit"])
    log.info("written: %s", write_result("prompt-loop", payload))


if __name__ == "__main__":
    main()
