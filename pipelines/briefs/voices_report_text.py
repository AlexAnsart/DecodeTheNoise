"""Writes the evaluation report of the one-voice check from its metrics. No number is typed.

Run alone to write the report again from the metrics on disk, after the audit below changes:
uv run --group pipelines python -m pipelines.briefs.voices_report_text
"""

import json
import subprocess
from pathlib import Path

FOLDER = Path("reports") / "voices"
_COMMIT_LINE = "- **Commit:** "

# Real groups the check flagged on the held-out half, read by hand: what they turned out to be.
# Keyed by pool; a pool not listed here is reported as not read yet.
AUDIT: dict[str, tuple[str, str]] = {
    "unneeded-2026-04": (
        "Declared campaign. Police departments and agencies relay one kit for a national "
        "drug take-back day: the same announcements, lightly reworded. One voice indeed, and "
        "an open one",
        "Keeps the level at `possible` and says that a campaign kit reads the same. Whether a "
        "coordination is announced is not measured yet",
    ),
    "fremantle-2026-04": (
        "News coverage of one event. Sports outlets and club accounts report the same matches "
        "of one football club: independent newsrooms, the same facts. Flagged at 4 x 4 only",
        "Says that news feeds read the same, and shows the closest posts so the reader sees "
        "headlines. This is the false alarm to expect on event-tight groups",
    ),
}

MODES = {
    "shared": "one context wrote all the posts, dealt to the actors",
    "solo": "one context per actor, the same brief",
    "persona": "one context per actor, plus an age, a place and a writing habit each",
}


def _commit() -> str:
    done = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    )
    return done.stdout.strip() or "unknown"


def _rate(count: dict) -> str:
    return f"{count['flagged']} of {count['groups']} ({count['low']:.0%} to {count['high']:.0%})"


def _size_section(size: dict) -> list[str]:
    positives, negatives = size["one_brief"], size["real_alike"]
    tp, fn = positives["flagged"], positives["groups"] - positives["flagged"]
    fp, tn = negatives["flagged"], negatives["groups"] - negatives["flagged"]
    found = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * found * recall / (found + recall) if found + recall else float("nan")
    lines = [
        f"### {size['actors']} actors of {size['posts_each']} posts",
        "",
        f"Threshold: score under {size['threshold']}, set on {size['calibration_groups']} real "
        "pools. Negatives below are the hardest real groups (the most alike actors of each "
        "held-out pool).",
        "",
        "| | Flagged | Not flagged |",
        "| --- | --- | --- |",
        f"| Written from one brief | TP = {tp} | FN = {fn} |",
        f"| Real, most alike actors | FP = {fp} | TN = {tn} |",
        "",
        "| Measure | Value | 95% interval | n |",
        "| --- | --- | --- | --- |",
        f"| Recall | {positives['rate']:.0%} | {positives['low']:.0%} to {positives['high']:.0%} "
        f"| {positives['groups']} |",
        f"| False-positive rate, most alike real actors | {negatives['rate']:.0%} | "
        f"{negatives['low']:.0%} to {negatives['high']:.0%} | {negatives['groups']} |",
        f"| False-positive rate, real actors drawn at random | {size['real']['rate']:.0%} | "
        f"{size['real']['low']:.0%} to {size['real']['high']:.0%} | {size['real']['groups']} |",
        f"| Precision on this test mix | {found:.0%} | | {tp + fp} |",
        f"| F1 on this test mix | {f1:.2f} | | |",
        "",
        "By way of running the actors:",
        "",
        "| Mode | Flagged |",
        "| --- | --- |",
        *[
            f"| `{mode}`: {MODES[mode]} | {_rate(size['one_brief']['by_mode'][mode])} |"
            for mode in MODES
        ],
        "",
        "A real operation (Internet Research Agency, groups of one team in one zone and month):",
        "",
        "| Team | Flagged |",
        "| --- | --- |",
        *[f"| {arm.removeprefix('ira-')} | {_rate(count)} |" for arm, count in size["ira"].items()],
        "",
        "Precision when coordinated groups are rare (measured rates; worst case of both "
        "intervals in brackets):",
        "",
        "| Share of groups that are coordinated | 1% | 5% | 20% |",
        "| --- | --- | --- | --- |",
        "| Precision | "
        + " | ".join(
            f"{size['precision_at_base_rate'][key]['measured']:.0%} "
            f"({size['precision_at_base_rate'][key]['worst_case']:.0%})"
            for key in ("0.01", "0.05", "0.2")
        )
        + " |",
        "",
    ]
    return lines


def _census_section() -> list[str]:
    """What `voices_census.py` counted on real builds, when it ran: one block per build."""
    lines: list[str] = []
    for file in sorted(FOLDER.glob("census-*.json")):
        census = json.loads(file.read_text(encoding="utf-8"))
        natures = ", ".join(f"{n} {nature}" for nature, n in census["flagged_by_nature"].items())
        lines += [
            f"### Build `{census['build']}` ({census['points']:,} posts)",
            "",
            "The check was run on every selection one gesture makes on the map: "
            + "; ".join(f"{kind}: {text}" for kind, text in census["definition"].items())
            + ".",
            "",
            f"{census['selections_tried']:,} selections tried, {census['selections_read']:,} "
            f"read, **{census['flagged']} flagged**" + (f" ({natures})." if natures else "."),
            "",
            "| Kind of selection | Read | Flagged |",
            "| --- | --- | --- |",
            *[
                f"| {kind} | {c['read']:,} | {c['flagged']} |"
                for kind, c in census["by_kind"].items()
            ],
            "",
        ]
        if census["flagged_selections"]:
            lines += [
                "Every flagged selection, read by hand:",
                "",
                "| Selection | Posts | Read at | Score | Limit | What it is |",
                "| --- | --- | --- | --- | --- | --- |",
                *[
                    f"| {e['name']} | {e['posts']} | {e['size']} | {e['score']} | {e['threshold']} "
                    f"| {e['nature']}. {e['reason']} |"
                    for e in census["flagged_selections"]
                ],
                "",
            ]
        lines += [census["note"], ""]
    return lines


def write_report(path: Path, metrics: dict, commit: str | None = None) -> None:
    flagged = sorted({name for size in metrics["sizes"] for name in size["flagged_real_groups"]})
    audit = [
        f"| {name} | {AUDIT[name][0]} | {AUDIT[name][1]} |"
        if name in AUDIT
        else f"| {name} | not read yet | |"
        for name in flagged
    ]
    base = metrics["baseline"]
    census = _census_section()
    lines = [
        f"# One voice or several: evaluation {metrics['evaluated']}",
        "",
        "## What is decided",
        "",
        f"- **Unit:** {metrics['unit']}, read from a selection on the map.",
        f"- **Positive means:** {metrics['positive']}.",
        f"- **Detector:** {metrics['score']}. Rule: {metrics['rule']}. Embedding: "
        f"`{metrics['embedding_key']}`.",
        f"{_COMMIT_LINE}{commit or _commit()}",
        "",
        "## Data",
        "",
        "| Split | Source | Groups |",
        "| --- | --- | --- |",
        "| Calibration | Real pools of the 2026 sample of X posts (one word, one month), the "
        "half a hash of the pool name selects | see each size |",
        "| Test, negatives | The other half of the real pools: actors drawn at random, and the "
        "most alike actors | see each size |",
        "| Test, positives | Synthetic groups written by Claude Haiku from one brief, three "
        "ways of running the actors | see each size |",
        "| Off-distribution | Internet Research Agency tweets, 2015 to 2017 | see each size |",
        "",
        "Split rule: by pool, never by post. How the groups were made: "
        "`docs/brief-recovery/benchmark.md`.",
        "",
        "## Results on test",
        "",
        *[line for size in metrics["sizes"] for line in _size_section(size)],
        "## Baseline",
        "",
        f"A near-duplicate rule ({base['rule']}) on the same groups:",
        "",
        "| Detector | Groups from one brief flagged | Real groups flagged |",
        "| --- | --- | --- |",
        f"| Near-duplicate rule | {_rate(base['one_brief'])} | {_rate(base['real'])} |",
        f"| This check, {metrics['sizes'][0]['actors']} x {metrics['sizes'][0]['posts_each']} | "
        f"{_rate(metrics['sizes'][0]['one_brief'])} | {_rate(metrics['sizes'][0]['real'])} |",
        "",
        "## False-positive audit",
        "",
        "Real groups flagged on the held-out half, at any measured size:",
        "",
        "| Pool | What it is | What the product does |",
        "| --- | --- | --- |",
        *(audit or ["| none | | |"]),
        "",
        *(["## On real posts, outside the benchmark", "", *census] if census else []),
        "## Abstention",
        "",
        "The check answers `not enough evidence` when the selection holds fewer than "
        f"{metrics['sizes'][-1]['actors']} actors with {metrics['sizes'][-1]['posts_each']} posts "
        "each, reposts left out. Most selections of a sparse corpus abstain.",
        "",
        "## Off-distribution",
        "",
        "The Internet Research Agency rows above: other years, posts of 140 characters, groups "
        "cut by map zone. A second writer model for the synthetic groups: untested.",
        "",
        "## Limits",
        "",
        *[f"- {limit}" for limit in metrics["limits"]],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    saved = json.loads((FOLDER / "metrics.json").read_text(encoding="utf-8"))
    report = FOLDER / saved["report"]
    # Writing the report again keeps the commit its metrics were measured at.
    measured = next(
        line.removeprefix(_COMMIT_LINE)
        for line in report.read_text(encoding="utf-8").splitlines()
        if line.startswith(_COMMIT_LINE)
    )
    write_report(report, saved, measured)
