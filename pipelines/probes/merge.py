"""Compares the readings of a round and settles one answer per post and label.

Two readings that agree give the answer. When they differ, a third reading decides by majority;
with no majority the answer is `unclear` and the post is left out for that label. An `invalid`
reading (a yes whose quote is not in the post) counts as no reading.

Run: uv run --group pipelines python -m pipelines.probes.merge --round p1
"""

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

from pipelines.probes.collect import INVALID
from pipelines.probes.sample import read_items, read_jsonl, round_dir
from pipelines.probes.taxonomy import FAMILIES, UNCLEAR, YES, Label, family_labels

log = logging.getLogger("probes.merge")

READINGS = ("a", "b", "c")
Reading = dict[str, dict[str, object]]  # post key -> its row


def load_reading(round_name: str, family: str, reading: str) -> Reading:
    path = round_dir(round_name) / "labels" / family / f"{reading}.jsonl"
    if not path.exists():
        return {}
    return {row["key"]: row for row in read_jsonl(path)}


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa over paired answers; None when chance agreement is total."""
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(left[v] * right[v] for v in left) / (n * n)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def agreement(label: Label, first: Reading, second: Reading) -> dict[str, object]:
    """How two readings of the same posts agree on one label."""
    keys = sorted(first.keys() & second.keys())
    raw = [(first[k]["labels"][label.name], second[k]["labels"][label.name]) for k in keys]
    values = [v for pair in raw for v in pair]
    out: dict[str, object] = {
        "n": len(raw),
        "unclear": values.count(UNCLEAR) / max(len(values), 1),
        "invalid": values.count(INVALID) / max(len(values), 1),
    }
    decided = [p for p in raw if not {UNCLEAR, INVALID} & set(p)]
    out["kappa"] = kappa(decided)
    out["agree"] = sum(a == b for a, b in decided) / max(len(decided), 1)
    if label.binary:
        yes_a = sum(a == YES for a, _ in decided)
        yes_b = sum(b == YES for _, b in decided)
        both = sum(a == b == YES for a, b in decided)
        out.update(yes_a=yes_a, yes_b=yes_b, both_yes=both)
        # Share of the yes answers that the other reading confirms: steadier than kappa when
        # the label is rare.
        out["positive_agreement"] = 2 * both / (yes_a + yes_b) if yes_a + yes_b else None
    return out


def settle(answers: list[str]) -> str | None:
    """The answer of a post for one label, or None when a third reading is needed.

    One reading is taken as it is. Two readings must agree. Three give the majority of the
    valid ones, and `unclear` when there is none.
    """
    valid = [a for a in answers if a != INVALID]
    if len(answers) == 1:
        return valid[0] if valid else UNCLEAR
    if len(answers) == 2:
        return valid[0] if len(valid) == 2 and valid[0] == valid[1] else None
    top, count = Counter(valid).most_common(1)[0] if valid else (UNCLEAR, 0)
    return top if len(valid) >= 2 and count * 2 > len(valid) else UNCLEAR


def settle_family(round_name: str, family: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Settled answers per post, and the posts that need one more reading."""
    readings = [load_reading(round_name, family, r) for r in READINGS]
    settled: dict[str, dict[str, str]] = {}
    pending: list[str] = []
    for key in sorted(set().union(*readings)):
        rows = [reading[key]["labels"] for reading in readings if key in reading]
        answers = {lab.name: settle([r[lab.name] for r in rows]) for lab in family_labels(family)}
        if None in answers.values():
            pending.append(key)
        settled[key] = {name: value or UNCLEAR for name, value in answers.items()}
    return settled, pending


def disagreements(round_name: str, family: str) -> list[dict[str, object]]:
    """Posts where readings a and b differ on a label, with what each one quoted."""
    first, second = (load_reading(round_name, family, r) for r in READINGS[:2])
    texts = {item.key: item.text for item in read_items(round_name)}
    rows = []
    for key in sorted(first.keys() & second.keys()):
        for label in family_labels(family):
            a, b = first[key]["labels"][label.name], second[key]["labels"][label.name]
            if a != b:
                quotes = [r[key]["evidence"].get(label.name) for r in (first, second)]
                row = {"label": label.name, "a": a, "b": b, "quotes": quotes, "text": texts[key]}
                rows.append({"key": key, **row})
    return rows


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = round_dir(args.round)
    report: dict[str, object] = {}
    differing: list[dict[str, object]] = []
    for family in FAMILIES:
        first, second = (load_reading(args.round, family, r) for r in READINGS[:2])
        if not first and not second:
            continue  # this pass has not read the round
        for label in family_labels(family):
            report[label.name] = agreement(label, first, second)
        differing += disagreements(args.round, family)
        settled, pending = settle_family(args.round, family)
        write_json(root / "labels" / family / "settled.json", settled)
        write_json(root / "labels" / family / "pending.json", pending)
        log.info(
            "%s: %d posts settled, %d need a third reading", family, len(settled), len(pending)
        )
    write_json(root / "agreement.json", report)
    write_json(root / "disagreements.json", differing)
    for name, row in report.items():
        score = "  n/a" if row["kappa"] is None else f"{row['kappa']:5.2f}"
        yes = f"{row.get('yes_a', '-')}/{row.get('yes_b', '-')}"
        rates = f"unclear={row['unclear']:.3f} invalid={row['invalid']:.3f}"
        log.info("%-28s n=%-4d kappa=%s yes=%s %s", name, row["n"], score, yes, rates)


if __name__ == "__main__":
    main()
