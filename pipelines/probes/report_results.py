"""The result tables of the probe report: thresholds, measures on test, final state."""

from collections import Counter

from pipelines.probes.evaluate import LEVELS, REPORT
from pipelines.probes.languages import GROUPS
from pipelines.probes.report_tables import num, pct, read_json, span, table, use_of
from pipelines.probes.train import RUNS

MEASURES = ["Precision", "Recall", "False-positive rate", "Prevalence"]


def thresholds_table(run: str) -> str:
    """What calibration read and where each level was placed."""
    rows = []
    for name, row in read_json(RUNS / run / "thresholds.json").items():
        cells = [f"`{name}`", row["read"], row["positives"]]
        for level in ("probable", "possible"):
            edge = next((e for e in row["edges"] if e["threshold"] == row[level]), None)
            if edge is None:
                cells += ["none", ""]
            else:
                cells += [pct(edge["flag_rate"], 2), span(edge["precision"])]
        rows.append(cells)
    header = ["Target", "Calibration posts read", "Positives"]
    for level in ("Probable", "Possible"):
        header += [f"{level}: flagged", f"{level}: precision on calibration"]
    return table(header, rows)


def level_row(name: str, level: str, got: dict) -> list[object]:
    at_one = (got.get("precision_at_base_rate") or {}).get("0.01")
    return [
        f"`{name}`", level, pct(got["flag_rate"], 2),
        f"{got['positive_flagged']} / {got['read_flagged']}",
        span(got["precision"]), span(got["recall"]), span(got["fpr"], 2),
        span(got["prevalence"], 2), pct(at_one, 0),
    ]  # fmt: skip


def levels_table(states: tuple[str, ...], field: str = "levels") -> str:
    """Measures on test, one line per level: the levels kept, or those withdrawn."""
    rows = [
        level_row(name, level, row[field][level])
        for name, row in read_json(REPORT)["targets"].items()
        if row["state"] in states
        for level in LEVELS
        if level in row[field]
    ]
    header = ["Target", "Level", "Posts flagged", "Yes / read among flagged", *MEASURES]
    return table([*header, "Precision if 1% were positive"], rows)


def heads_table() -> str:
    """Probes without a level: what the 100 highest-scored test posts hold."""
    rows = []
    for name, row in read_json(REPORT)["targets"].items():
        head = row["head"]
        if head:
            low, high = head["wilson"]
            share = head["positive_flagged"] / max(head["read_flagged"], 1)
            rows.append([
                f"`{name}`", row["state"], f"{head['positive_flagged']} / {head['read_flagged']}",
                f"{pct(share, 0)} ({pct(low, 0)} to {pct(high, 0)})",
                f"{row['ranking']['positives']} / {row['ranking']['n']}",
            ])  # fmt: skip
    header = ["Target", "State", "Yes / read in the 100 highest scores", "Precision there",
              "Yes / posts in the random test sample"]  # fmt: skip
    return table(header, rows)


def ranking_table() -> str:
    """Average precision on the random test sample, for every fitted probe."""
    rows = []
    for name, row in read_json(REPORT)["targets"].items():
        rank = row["ranking"]
        lift = rank["average_precision"] / rank["chance"] if "chance" in rank else None
        rows.append([
            f"`{name}`", use_of(name), row["state"], rank["n"], rank["positives"],
            num(rank.get("average_precision")), num(rank.get("chance"), 3), num(lift, 1),
        ])  # fmt: skip
    header = ["Target", "Use", "State", "Random test posts", "Positives", "Average precision",
              "Chance", "Lift"]  # fmt: skip
    return table(header, rows)


def states_table() -> str:
    targets = read_json(REPORT)["targets"]
    counts = Counter(row["state"] for row in targets.values())
    rows = []
    for state in ("shown", "review-only", "dropped"):
        names = ", ".join(f"`{n}`" for n, row in targets.items() if row["state"] == state)
        rows.append([state, counts[state], names])
    return table(["State", "Probes", "Which"], rows)


def language_table() -> str:
    """Yes / read per language in the band of each kept level, for the shown probes."""
    rows = []
    for name, row in read_json(REPORT)["targets"].items():
        if row["state"] != "shown" or name.startswith("lang:"):
            continue
        for level in LEVELS:
            cells = row.get("by_language", {}).get(level)
            if cells and level in row["levels"]:
                shares = [f"{cells[g][0]} / {cells[g][1]}" for g in GROUPS]
                rows.append([f"`{name}`", level, *shares])
    header = ["Target", "Band of the level", "English: yes / read", "German: yes / read",
              "Other: yes / read"]  # fmt: skip
    return table(header, rows)


def language_note() -> str:
    probe = read_json(REPORT).get("language_probe", {})
    parts = []
    for group in GROUPS:
        row = probe[group]
        scores = f"recall {pct(row['recall'])}, precision {pct(row['precision'])}"
        parts.append(f"{group}: {scores} ({row['n']} posts)")
    return f"{pct(probe['accuracy'])} of {probe['n']} random test posts. " + "; ".join(parts) + "."


def audit_table() -> str:
    """What the second reader said of the settled answers, for the probes it re-read."""
    rows = []
    for name, row in read_json(REPORT)["targets"].items():
        audit = row.get("audit")
        if not audit or not row["levels"]:
            continue
        (confirmed, yes), (overturned, no) = audit["yes"], audit["no"]
        shares = [pct(confirmed / yes if yes else None, 0), pct(overturned / no if no else None, 0)]
        cells = [f"{confirmed} / {yes}", shares[0], f"{overturned} / {no}", shares[1]]
        rows.append([f"`{name}`", row["state"], *cells])
    header = ["Target", "State", "Yes confirmed", "Share", "No overturned", "Share"]
    return table(header, rows)
