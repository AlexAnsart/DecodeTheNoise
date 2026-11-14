"""Sentences and small tables of the probe report whose numbers come from the campaign files."""

from pathlib import Path

import numpy as np

from pipelines.probes.dataset import load_labelled
from pipelines.probes.merge import READINGS, load_reading
from pipelines.probes.report_tables import num, pct, read_json, table
from pipelines.probes.sample import ROUNDS, read_jsonl, round_dir
from pipelines.probes.taxonomy import FAMILIES, LABELS, YES
from pipelines.probes.train import RUNS

REPORT_FILE = Path("reports") / "probes" / "metrics.json"
STATES = ("shown", "review-only", "dropped")
ERROR_MODES = ("label_error", "near_miss", "topic", "short_or_context", "language", "other")
# Labels the pilot found weak, whose guide was corrected before the main round.
CORRECTED = ("fear_appeal", "attack_person", "dehumanisation", "identity_appeal", "us_vs_them",
             "doubt", "exaggeration", "unsourced_statistic", "endorsement")  # fmt: skip


def pilot_effect(pilot: str, main: str) -> str:
    before = read_json(round_dir(pilot) / "agreement.json")
    after = read_json(round_dir(main) / "agreement.json")

    def cells(row: dict) -> list[str]:
        return [f"{row['yes_a']} / {row['yes_b']}", num(row["kappa"])]

    rows = [[f"`{name}`", *cells(before[name]), *cells(after[name])] for name in CORRECTED]
    header = [
        "Label",
        "Pilot: yes (a / b)",
        "Pilot: kappa",
        "Main round: yes (a / b)",
        "Main round: kappa",
    ]
    return table(header, rows)


def agreement_summary(round_name: str) -> str:
    stats = read_json(round_dir(round_name) / "agreement.json")
    kappas = [row["kappa"] for row in stats.values() if row["n"] and row["kappa"] is not None]
    high = sum(k >= 0.8 for k in kappas)
    middle = sum(0.6 <= k < 0.8 for k in kappas)
    unclear = max(row["unclear"] for row in stats.values() if row["n"])
    lost = max(row["invalid"] for row in stats.values() if row["n"])
    low = len(kappas) - high - middle
    return (
        f"Of {len(kappas)} labels with a kappa, {high} are at 0.8 or more, {middle} between 0.6 "
        f"and 0.8, and {low} under 0.6. The highest share of `unclear` answers on a label is "
        f"{pct(unclear)}, and the highest share thrown away is {pct(lost)}."
    )


def position_note(round_name: str) -> str:
    yes, seen = np.zeros(41), np.zeros(41)
    for family in FAMILIES:
        for reading in READINGS[:2]:
            for row in load_reading(round_name, family, reading).values():
                answers = [v for v in row["labels"].values() if v in ("yes", "no")]
                yes[row["n"]] += answers.count(YES)
                seen[row["n"]] += len(answers)
    rate = yes[1:] / seen[1:]
    return (
        f"Over {int(seen.sum()):,} decided answers, the share of yes is "
        f"{pct(rate[:4].mean(), 2)} on the first four posts of a batch, "
        f"{pct(rate[4:20].mean(), 2)} on posts 5 to 20 and "
        f"{pct(rate[20:].mean(), 2)} on posts 21 to 40."
    )


def enrichment_table(rounds: tuple[str, ...]) -> str:
    """Train positives per label: how many came from random posts, how many from enrichment."""
    labelled = load_labelled(rounds)
    random = np.array([s == "random" for s in labelled.stratum])
    rows = []
    for label in LABELS:
        if not label.binary or label.name not in labelled.answers:
            continue
        train = labelled.rows(label, "train")
        yes = labelled.answers[label.name][train] == YES
        if not len(train):
            continue
        rows.append([f"`{label.name}`", len(train), int((yes & random[train]).sum()),
                     int((yes & ~random[train]).sum())])  # fmt: skip
    header = [
        "Label",
        "Train posts answered",
        "Positives in random posts",
        "Positives found by search",
    ]
    return table(header, rows)


def rounds_of(prefixes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(p.name for p in ROUNDS.iterdir() if p.name.startswith(prefixes)))


def readers_note(run: str) -> str:
    rows = {k: v for k, v in read_json(RUNS / run / "diagnostics.json").items() if "mlp" in v}
    ahead = sum(v["linear"] >= max(v["mlp"], v["knn"]) for v in rows.values())
    worst = max(max(v["mlp"], v["knn"]) - v["linear"] for v in rows.values())
    gap = np.mean([v["linear"] - v["centroid"] for v in rows.values()])
    return (
        f"On {ahead} of {len(rows)} targets the linear probe is at or above both other readers, "
        f"and it is never behind by more than {num(worst)}. It is {num(float(gap))} above the "
        "similarity baseline on average."
    )


def dims_note(run: str) -> str:
    rows = [v["dims"] for v in read_json(RUNS / run / "diagnostics.json").values() if "dims" in v]
    mean = {d: float(np.mean([row[d] for row in rows])) for d in ("64", "128", "256")}
    better = sum(row["256"] > row["128"] + 0.01 for row in rows)
    return (
        f"Mean average precision over {len(rows)} targets: {num(mean['64'])} with 64 dimensions, "
        f"{num(mean['128'])} with 128, {num(mean['256'])} with 256. On {better} targets 256 "
        "dimensions beat 128 by more than 0.01."
    )


def learning_note(run: str) -> str:
    rows = read_json(RUNS / run / "diagnostics.json")
    curves = {k: v["learning_curve"] for k, v in rows.items() if len(v["learning_curve"]) == 3}
    rising = sorted(k for k, c in curves.items() if c["1.0"] - c["0.5"] >= 0.04)
    flat = sum(abs(c["1.0"] - c["0.5"]) < 0.02 for c in curves.values())
    names = ", ".join(f"`{name}`" for name in rising)
    return (
        f"Between half and all of the train posts, average precision moves by less than 0.02 on "
        f"{flat} of {len(curves)} targets. It still gains 0.04 or more on {len(rising)}: {names}."
    )


def single_reading_noise(round_name: str) -> str:
    """How often one reading alone differs from the settled answer, on posts read several times."""
    differ = total = 0
    for family in FAMILIES:
        path = round_dir(round_name) / "labels" / family / "settled.json"
        first, second = (load_reading(round_name, family, r) for r in READINGS[:2])
        if not path.exists() or not second:
            continue
        settled = read_json(path)
        for key in second:
            for name, final in settled[key].items():
                if final in ("yes", "no"):
                    differ += first[key]["labels"][name] != final
                    total += 1
    return f"{pct(differ / max(total, 1), 2)} of {total:,} answers"


def states_note() -> str:
    targets = read_json(REPORT_FILE)["targets"]
    counts = {s: sum(row["state"] == s for row in targets.values()) for s in STATES}
    return (
        f"Of {len(targets)} fitted targets, {counts['shown']} are shown, {counts['review-only']} "
        f"feed the review pass only, and {counts['dropped']} are dropped."
    )


def audit_note(run: str, name: str) -> str:
    audit = read_json(RUNS / run / f"audit-{name}.json")
    posts = sum(len(read_jsonl(p / "items.jsonl")) for p in ROUNDS.glob(f"{name}_*"))
    confirmed, yes = (sum(row["yes"][i] for row in audit.values()) for i in (0, 1))
    overturned, no = (sum(row["no"][i] for row in audit.values()) for i in (0, 1))
    kept, flipped = pct(confirmed / yes, 0), pct(overturned / no)
    return (
        f"{posts} test posts were read again. Over every label of the passes concerned, the second "
        f"reader confirmed {confirmed} of {yes} settled yes answers ({kept}) and overturned "
        f"{overturned} of {no} settled no answers ({flipped})."
    )


def campaign_note() -> str:
    # The audit rounds read test posts a second time: they are not new posts.
    rounds = [p for p in ROUNDS.iterdir() if (p / "items.jsonl").exists() and p.name[0] != "a"]
    posts = sum(len(read_jsonl(p / "items.jsonl")) for p in rounds)
    batches = sum(1 for p in rounds for _ in p.glob("batches/*/*/*.txt"))
    return f"{posts:,} posts were drawn in {len(rounds)} rounds and read in {batches:,} batches"


def errors_table(run: str) -> str:
    """False positives read on test: how many fall in each failure mode, and what is confused."""
    path = RUNS / run / "error_taxonomy.json"
    if not path.exists():
        return "Not read yet."
    rows = []
    for name, row in read_json(path).items():
        modes = row["modes"]
        cells = [modes.get(mode, 0) for mode in ERROR_MODES]
        rows.append([f"`{name}`", row["read"], *cells, row["confusion"]])
    header = ["Probe", "Read", "Label error", "Near miss", "Topic", "Short or no context",
              "Language", "Other", "What it mistakes for the label"]  # fmt: skip
    return table(header, rows)


def error_examples_table(run: str) -> str:
    path = RUNS / run / "error_taxonomy.json"
    if not path.exists():
        return "Not read yet."
    rows = [
        [f"`{name}`", row["examples"][0]["mode"], row["examples"][0]["paraphrase"],
         row["examples"][0]["why"]]
        for name, row in read_json(path).items()
        if row["examples"]
    ]  # fmt: skip
    return table(["Probe", "Most frequent mode", "Example, paraphrased", "Why"], rows)


def errors_note(run: str) -> str:
    path = RUNS / run / "error_taxonomy.json"
    if not path.exists():
        return "Not read yet."
    rows = read_json(path).values()
    total = sum(row["read"] for row in rows)
    shares = {mode: sum(row["modes"].get(mode, 0) for row in rows) / total for mode in ERROR_MODES}
    parts = [f"{mode.replace('_', ' ')} {pct(share, 0)}" for mode, share in shares.items() if share]
    return f"{total} false positives read over {len(rows)} probes: " + ", ".join(parts) + "."
