"""Draws calibration or test posts by score band, for labels too rare for a random sample.

For each probe, the posts of the split are cut into bands by score, and a fixed number is drawn
uniformly inside each band. The positive rate of a band is then measured on a uniform sample of
it, and the band weighs its true size in the split. Annotators never see a score or a band.

Calibration cuts by rank, to place the thresholds. Test cuts at the thresholds already frozen.
One round per family is written (`<name>_<family>`), and the bands go to `bands-<split>.json`.

Run: uv run --group pipelines python -m pipelines.probes.bands --name c1 --run v1 \
       --split calibration
"""

import argparse
import json
import logging

import numpy as np

from pipelines.probes.pool import load_pool
from pipelines.probes.sample import RoundItem, drawn_keys, fetch_texts, keys_of, write_items
from pipelines.probes.score import load_probes, score_rows, split_rows
from pipelines.probes.taxonomy import BY_NAME
from pipelines.probes.train import RUNS, SEED

log = logging.getLogger("probes.bands")

# Calibration: ranks of the split's posts by decreasing score, and posts drawn per band.
RANK_EDGES = (0, 100, 300, 1000, 3000, 10_000, 30_000)
PER_RANK_BAND = 25
# Test: the two flagged bands, then the band just under the lower threshold.
PER_TEST_BAND = (100, 100, 60)
NEAR_FACTOR = 3  # the near-miss band holds this many times the flagged posts
HEAD_DRAWN = 50  # posts drawn in the head of the scores of a probe without a level


def rank_bands(scores: np.ndarray) -> list[tuple[float, float]]:
    """Score intervals [low, high) that hold the ranks between consecutive edges."""
    ordered = np.sort(scores)[::-1]
    cuts = [float("inf")] + [float(ordered[min(e, len(ordered)) - 1]) for e in RANK_EDGES[1:]]
    return [(cuts[i + 1], cuts[i]) for i in range(len(cuts) - 1)]


def threshold_bands(scores: np.ndarray, levels: dict[str, float | None]) -> list[tuple]:
    """The flagged bands a probe has, highest first, then the band just under its lowest level."""
    cuts = [levels[name] for name in ("probable", "possible") if levels[name] is not None]
    flagged = int((scores >= cuts[-1]).sum())
    ordered = np.sort(scores)[::-1]
    near = float(ordered[min(flagged * (NEAR_FACTOR + 1), len(ordered) - 1)])
    edges = [float("inf"), *cuts, near]
    return list(zip(edges[1:], edges[:-1], strict=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--split", required=True, choices=("calibration", "test"))
    parser.add_argument("--labels", nargs="+", required=True, help="probes to read by band")
    parser.add_argument(
        "--top", type=int, help="read the head of the scores instead: one band of this many posts"
    )
    parser.add_argument(
        "--per-band",
        type=int,
        nargs="+",
        help="posts to draw in each band, to add reads where a level is decided",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    rng = np.random.default_rng(SEED + (args.split == "test"))
    pool = load_pool()
    probes = load_probes(args.run)
    rows = split_rows(pool, args.split)
    keys = np.array(keys_of(pool, rows))
    taken = drawn_keys()
    free = np.array([key not in taken for key in keys])
    logits = score_rows(probes, pool, rows)
    folder = RUNS / args.run
    thresholds = {}
    if args.split == "test" and not args.top:
        thresholds = json.loads((folder / "thresholds.json").read_text(encoding="utf-8"))
    record: dict[str, list[dict[str, object]]] = {}
    drawn: dict[str, dict[str, str]] = {}  # family -> post key -> stratum
    for name in args.labels:
        scores = logits[:, probes.names.index(name)]
        if args.top:
            # A probe without a level: its highest scores are read, to measure its ranking.
            bands = [(float(np.sort(scores)[::-1][args.top - 1]), float("inf"))]
            sizes = tuple(args.per_band or (HEAD_DRAWN,))
        elif args.split == "test":
            bands = threshold_bands(scores, thresholds[name])
            sizes = PER_TEST_BAND[-len(bands) :]
        else:
            bands = rank_bands(scores)
            sizes = tuple(args.per_band or (PER_RANK_BAND,) * len(bands))
        record[name] = []
        for number, ((low, high), size) in enumerate(zip(bands, sizes, strict=True)):
            inside = np.flatnonzero((scores >= low) & (scores < high))
            open_rows = inside[free[inside]]
            picked = rng.choice(open_rows, size=min(size, len(open_rows)), replace=False)
            # A post may be drawn for two labels of a family: each draw stays uniform in its
            # band, and the post is read once. Its stratum then names both bands.
            family = drawn.setdefault(BY_NAME[name.split(":")[0]].family, {})
            for key in keys[picked]:
                mark = f"band:{name}:{number}"
                family[key] = f"{family[key]}|{mark}" if key in family else mark
            band = {"low": low, "high": high, "size": len(inside), "drawn": keys[picked].tolist()}
            record[name].append(band)
        log.info("%-26s bands %s", name, [(b["size"], len(b["drawn"])) for b in record[name]])
    # A later draw adds its labels to the record; it never erases an earlier one.
    path = folder / f"bands-{args.split}.json"
    earlier = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for name, bands_drawn in record.items():
        for old, new in zip(earlier.get(name, []), bands_drawn, strict=False):
            new["drawn"] = old["drawn"] + new["drawn"]
    path.write_text(json.dumps({**earlier, **record}), encoding="utf-8")
    for family, posts in drawn.items():
        texts = fetch_texts(list(posts))
        items = [RoundItem(key, args.split, s, texts[key]) for key, s in posts.items()]
        write_items(f"{args.name}_{family}", items)
        log.info("round %s_%s: %d posts", args.name, family, len(items))


if __name__ == "__main__":
    main()
