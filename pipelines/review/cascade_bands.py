"""The cascade (a probe flags, the review reads) measured on every test post read by score band.

The random test sample holds about a hundred posts a technique probe flags: too few for a
narrow interval. The probe campaign also read, for each probe, posts drawn uniformly inside
bands of its scores on the test split (`pipelines/probes/bands.py`). Inside a band they are a
uniform sample of it, so each band counts for the posts of the test split it holds, as
`pipelines/probes/estimate.py` does for a probe alone. Here a read post has one of four
outcomes: kept by the review or not, annotated yes or not.

Writes the block `cascade_bands` of `reports/review/metrics.json` and its own report beside it.
The cascade on the random sample alone stays as it was, in `cascade`.

Run: uv run --group pipelines python -m pipelines.review.cascade_bands
"""

import json
import logging
from pathlib import Path

from backend.model_client.llm import ChatClient
from backend.probes.pack import load_probes as load_pack
from backend.probes.schema import PACK_FILE, ProbePack
from backend.review.guides import load_guides
from backend.review.prompt import PROMPT_VERSION, ReviewRequest
from backend.settings import get_settings
from pipelines import runlog
from pipelines.probes.calibrate import uniform_in_band
from pipelines.probes.dataset import load_labelled, vectors_for
from pipelines.probes.pool import load_pool
from pipelines.probes.sample import read_items
from pipelines.probes.score import load_probes, score_rows, split_rows
from pipelines.probes.train import RUNS, targets
from pipelines.review.ask import Budget, read_all
from pipelines.review.band_estimate import BandCounts, estimate_cascade, read_enough
from pipelines.review.band_report import render_bands
from pipelines.review.cache import Answers
from pipelines.review.cascade import flagging
from pipelines.review.evaluate import ANSWERS_FILE
from pipelines.review.metrics import METRICS_FILE, REPORTS

log = logging.getLogger("review.cascade_bands")

PROBE_REPORT = Path("reports") / "probes" / "metrics.json"
BANDS_FILE = "bands-test.json"
REPORT_FILE = "2026-11-15-cascade-bands.md"
SPLIT = "test"
# New calls this stage may pay for, beyond the answers already kept.
CALL_BUDGET = 2_500


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    settings = get_settings()
    if not (settings.llm_api_key and settings.llm_model):
        raise SystemExit("LLM_API_KEY and LLM_MODEL must be set: the review needs its model.")
    guides = load_guides(settings.guides_dir)
    techniques = {label.key for label in guides.screened()}
    campaign = json.loads(PROBE_REPORT.read_text(encoding="utf-8"))
    run, rounds = campaign["run"], tuple(campaign["rounds"])
    drawn = json.loads((RUNS / run / BANDS_FILE).read_text(encoding="utf-8"))
    pack = ProbePack.model_validate_json(
        (settings.probes_dir / PACK_FILE).read_text(encoding="utf-8")
    )
    packed = {probe.info.key: probe for probe in pack.probes}

    labelled = load_labelled(rounds)
    keys = list(labelled.keys)
    vectors, model_key = vectors_for(keys)
    campaign_probes = load_probes(run)
    logits = campaign_probes.logits(vectors)
    pool = load_pool()
    split = score_rows(campaign_probes, pool, split_rows(pool, SPLIT))
    # What the product lists when it sends a post to the review: the technique probes that flag it.
    listed = flagging(load_pack(settings.probes_dir, model_key), vectors, keys, techniques)
    texts = {item.key: item.text for name in rounds for item in read_items(name)}

    plans = {}
    requests: dict[str, ReviewRequest] = {}
    for target in targets(labelled, SPLIT):
        probe = packed.get(target.name)
        if probe is None or target.name not in techniques:
            continue
        cuts = [
            cut
            for cut in (probe.probable_cut, probe.possible_cut, probe.review_cut)
            if cut is not None
        ]
        if not cuts:
            continue
        threshold = min(cuts)
        column = campaign_probes.names.index(target.name)
        used = uniform_in_band(labelled, target)
        rows, answers = target.rows[used], target.y[used]
        scores = logits[rows, column]
        lows = {band["low"] for band in drawn.get(target.name, []) if band["low"] > threshold}
        edges = sorted({threshold, *cuts, *lows}, reverse=True)
        flagged = [
            (keys[row], float(score), bool(answer))
            for row, score, answer in zip(rows, scores, answers, strict=True)
            if score >= threshold
            and any(info.key == target.name for info in listed.get(keys[row], ()))
        ]
        plans[target.name] = (edges, split[:, column], flagged)
        for key, _, _ in flagged:
            requests[key] = ReviewRequest(text=texts[key], probes=listed[key])
    log.info("%d probes, %d posts to read", len(plans), len(requests))

    stored_answers = Answers(ANSWERS_FILE)
    stored = len(stored_answers)
    client = ChatClient(settings.llm_api_base, settings.llm_api_key, settings.llm_model, 120.0)
    with runlog.timed() as elapsed:
        readings = read_all(
            client, settings.llm_model, guides, stored_answers, Budget(CALL_BUDGET), requests, 1
        )
    client.close()
    supported = {
        post: {finding.probe: finding.reading == "supported" for finding in reading.review.findings}
        for post, reading in readings.items()
        if reading.review.status == "done"
    }

    probes: dict[str, object] = {}
    for name, (edges, split_scores, flagged) in plans.items():
        bands = []
        for position, low in enumerate(edges):
            high = edges[position - 1] if position else float("inf")
            inside = [
                (supported[key][name], answer)
                for key, score, answer in flagged
                if low <= score < high and name in supported.get(key, {})
            ]
            bands.append(
                BandCounts(
                    low=low,
                    size=int(((split_scores >= low) & (split_scores < high)).sum()),
                    kept_yes=sum(kept and yes for kept, yes in inside),
                    kept_no=sum(kept and not yes for kept, yes in inside),
                    left_yes=sum(not kept and yes for kept, yes in inside),
                    left_no=sum(not kept and not yes for kept, yes in inside),
                )
            )
        measured = read_enough(bands)
        whole = len(measured) == len(bands)
        probes[name] = {
            "threshold": min(edges),
            # "flagged": every post the probe flags. "head": its highest scores only, because
            # the bands under them were hardly read.
            "scope": "flagged" if whole else "head",
            "measured_from": measured[-1].low if measured else None,
            "flagged_in_split": sum(band.size for band in measured),
            "left_out_in_split": sum(band.size for band in bands) - sum(b.size for b in measured),
            "flagged": len(flagged),
            "flagged_yes": sum(answer for _, _, answer in flagged),
            **estimate_cascade(measured),
            "bands": [band.as_dict() for band in bands],
        }
        log.info("%-18s %s", name, {k: v for k, v in probes[name].items() if k != "bands"})

    block = {
        "design": "bands",
        "pack_run": pack.run,
        "pack_exported_at": pack.exported_at,
        "model": settings.llm_model,
        "prompt_version": PROMPT_VERSION,
        "split": SPLIT,
        "rounds": list(rounds),
        "posts_flagged": len(requests),
        "posts_read": len(supported),
        "probes": probes,
    }
    path = REPORTS / METRICS_FILE
    metrics = json.loads(path.read_text(encoding="utf-8"))
    metrics["cascade_bands"] = block
    path.write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (REPORTS / REPORT_FILE).write_text(render_bands(block, metrics.get("cascade")), "utf-8")
    paid = len(stored_answers) - stored
    if paid:
        note = f"{settings.llm_model}, {PROMPT_VERSION}, {paid} calls, cascade by score band"
        runlog.record("review-cascade-bands", SPLIT, len(supported), elapsed[0], note=note)
    log.info("wrote %s and %s (%d calls paid)", path, REPORTS / REPORT_FILE, paid)


if __name__ == "__main__":
    main()
