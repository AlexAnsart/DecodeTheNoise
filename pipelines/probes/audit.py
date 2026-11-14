"""A second opinion on the labels the test numbers rest on.

The annotators that settle a label are also what a probe is measured against. To see how far
their answers can be trusted, some test posts are read again, blind, by a stronger reader with
the same guide: a larger model, or a person. For each probe, the posts are drawn among those
read in its flagged bands, half settled as yes and half as no.

`--make` writes one round per family (`<name>_<family>`). After they are read, `--score`
compares the second opinion with the settled answers and writes `audit-<name>.json` in the run.

Run: uv run --group pipelines python -m pipelines.probes.audit --name a1 --run v1 --make \
       --rounds t1_calls t1_hostility
"""

import argparse
import json
import logging

import numpy as np

from pipelines.probes.dataset import load_labelled
from pipelines.probes.estimate import wilson
from pipelines.probes.merge import load_reading
from pipelines.probes.sample import RoundItem, fetch_texts, write_items
from pipelines.probes.taxonomy import BY_NAME, FAMILIES, YES
from pipelines.probes.train import RUNS, SEED

log = logging.getLogger("probes.audit")

PER_ANSWER = 15  # posts drawn per probe among the settled yes, and as many among the settled no


def make(name: str, rounds: tuple[str, ...], targets: list[str]) -> None:
    rng = np.random.default_rng(SEED)
    labelled = load_labelled(rounds)
    drawn: dict[str, dict[str, str]] = {}  # family -> post key -> the probe it is audited for
    for target in targets:
        label = BY_NAME[target]
        flagged = [f"band:{target}:{band}" in s for s in labelled.stratum for band in (0, 1)]
        in_band = np.array(flagged).reshape(-1, 2).any(axis=1)
        rows = np.intersect1d(labelled.rows(label), np.flatnonzero(in_band))
        answers = labelled.answers[target][rows]
        family = drawn.setdefault(label.family, {})
        for wanted in (True, False):
            group = rows[(answers == YES) == wanted]
            for row in rng.choice(group, size=min(PER_ANSWER, len(group)), replace=False):
                family.setdefault(labelled.keys[row], f"audit:{target}")
    for family, posts in drawn.items():
        texts = fetch_texts(list(posts))
        items = [RoundItem(key, "test", stratum, texts[key]) for key, stratum in posts.items()]
        write_items(f"{name}_{family}", items)
        log.info("round %s_%s: %d posts", name, family, len(items))


def score(name: str, rounds: tuple[str, ...]) -> dict[str, dict[str, object]]:
    """Per probe: how often the second opinion says yes where the settled answer is yes, or no."""
    labelled = load_labelled(rounds)
    settled = {key: i for i, key in enumerate(labelled.keys)}
    out: dict[str, dict[str, object]] = {}
    for family in FAMILIES:
        for key, row in load_reading(f"{name}_{family}", family, "a").items():
            for target, second in row["labels"].items():
                first = labelled.answers[target][settled[key]] if key in settled else ""
                if first not in ("yes", "no") or second not in ("yes", "no"):
                    continue
                cell = out.setdefault(target, {"yes": [0, 0], "no": [0, 0]})
                cell[first][0] += second == YES
                cell[first][1] += 1
    for cell in out.values():
        confirmed, total_yes = cell["yes"]
        overturned, total_no = cell["no"]
        cell["yes_confirmed"] = confirmed / total_yes if total_yes else None
        cell["yes_confirmed_interval"] = list(wilson(confirmed, total_yes))
        cell["no_overturned"] = overturned / total_no if total_no else None
        agree = confirmed + (total_no - overturned)
        cell["agreement"] = agree / max(total_yes + total_no, 1)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--rounds", nargs="+", required=True, help="rounds with the settled labels")
    parser.add_argument("--targets", nargs="*", help="probes to audit (default: those shown)")
    parser.add_argument("--make", action="store_true")
    parser.add_argument("--score", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    folder = RUNS / args.run
    if args.make:
        metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))["targets"]
        shown = [n for n, row in metrics.items() if row["state"] == "shown" and n in BY_NAME]
        make(args.name, tuple(args.rounds), args.targets or shown)
    if args.score:
        result = score(args.name, tuple(args.rounds))
        (folder / f"audit-{args.name}.json").write_text(json.dumps(result, indent=1), "utf-8")
        for target, cell in result.items():
            log.info("%-28s yes confirmed %s, no overturned %s", target, cell["yes"], cell["no"])


if __name__ == "__main__":
    main()
