"""The demo check in the probe report: what the probes flag on the build the site shows."""

from pipelines.probes.evaluate import LEVELS, REPORT
from pipelines.probes.report_tables import pct, read_json, table


def demo_table() -> str:
    """Share of the demo build flagged at each level, beside the share measured on test."""
    report = read_json(REPORT.with_name("demo.json"))
    rows = []
    for name, row in report["probes"].items():
        for level in LEVELS:
            got = row.get(level)
            if got:
                zone = got["top_zones"][0]
                where = f"{zone['zone']} ({pct(zone['share'])})"
                cells = [got["flagged"], pct(got["share"], 2), pct(got["share_on_test"], 2), where]
                rows.append([f"`{name}`", row["state"], level, *cells])
    header = ["Target", "State", "Level", "Posts flagged", "Share of the build", "Share on test"]
    return table([*header, "Zone where it fires most (share of the zone)"], rows)


def demo_note() -> str:
    """The build, who wrote it, and how it was drawn."""
    report = read_json(REPORT.with_name("demo.json"))
    by_split = report["actors_by_split"].items()
    splits = ", ".join(f"{n:,} of the {name} split" for name, n in by_split)
    size = f"{report['posts']:,} posts by {report['actors']:,} actors"
    note = f"`{report['build']}`, {size} ({splits})"
    if report["kept_actors"]:
        note += (
            f". It is a seeded draw of whole actors, plus {report['kept_actors']} accounts "
            f"({report['kept_posts']:,} posts) kept by hand for the demonstration"
        )
    return note


def demo_gaps_note() -> str:
    """How far the shares on the demo build are from the shares on test, widest gaps named."""
    report = read_json(REPORT.with_name("demo.json"))
    cuts: dict[tuple[str, int], tuple[str, dict]] = {}
    for name, row in report["probes"].items():
        for level in LEVELS:
            got = row.get(level)
            if got and got["share_on_test"]:
                # Two levels placed on the same threshold are one cut.
                cuts.setdefault((name, got["flagged"]), (level, got))
    ratios = sorted(
        (got["share"] / got["share_on_test"], name, level, got)
        for (name, _), (level, got) in cuts.items()
    )

    def gap(entry: tuple[float, str, str, dict]) -> str:
        ratio, name, level, got = entry
        expected = round(got["share_on_test"] * report["posts"])
        counts = f"{got['flagged']:,} posts where {expected:,} were expected"
        return f"`{name}` at `{level}` flags {ratio:.2f} times its test share ({counts})"

    near = sum(0.8 <= ratio <= 1.25 for ratio, *_ in ratios)
    note = (
        f"Of the {len(ratios)} cuts, {near} flag between 0.8 and 1.25 times their test share. "
        f"The widest gaps: {gap(ratios[-1])}; {gap(ratios[0])}."
    )
    _, name, level, got = max(ratios, key=lambda r: r[3]["flagged_in_kept"] / r[3]["flagged"])
    if got["flagged_in_kept"]:
        note += (
            f" The accounts kept by hand weigh most on `{name}` at `{level}`: "
            f"{got['flagged_in_kept']} of its {got['flagged']} flagged posts are theirs."
        )
    return note
