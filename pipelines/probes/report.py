"""Builds `docs/probes/report.md` from its template: hand-written text, generated tables.

A `{{table:name}}` mark is replaced by the table of that name, built from the files of the
campaign. `{{run}}` and `{{model_key}}` are filled from the run. A mark left unfilled is an
error: the report never ships with a hole.

Run: uv run --group pipelines python -m pipelines.probes.report --run v1 --round m1
"""

import argparse
import json
import logging
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from pipelines.probes import report_notes as notes
from pipelines.probes import report_results as results
from pipelines.probes import report_tables as tables
from pipelines.probes.pool import SPLITS
from pipelines.probes.sample import round_dir
from pipelines.probes.train import RUNS

log = logging.getLogger("probes.report")

DOCS = Path("docs") / "probes"
TEMPLATE = DOCS / "report.template.md"
REPORT = DOCS / "report.md"
PILOT = "p1"
AUDIT = "a1"
_MARK = re.compile(r"\{\{([a-z_:]+)\}\}")


def builders(run: str, round_name: str) -> dict[str, Callable[[], str]]:
    return {
        "table:pool": tables.pool_table,
        "table:rounds": tables.rounds_table,
        "table:agreement": lambda: tables.agreement_table(round_name),
        "table:prevalence": lambda: tables.prevalence_table(round_name, SPLITS),
        "table:training": lambda: tables.training_table(run),
        "table:thresholds": lambda: results.thresholds_table(run),
        "table:states": results.states_table,
        "table:results_shown": lambda: results.levels_table(("shown",)),
        "table:withdrawn": lambda: results.levels_table(("shown",), "withdrawn"),
        "table:results_other": lambda: results.levels_table(("review-only", "dropped")),
        "table:heads": results.heads_table,
        "table:audit": results.audit_table,
        "table:demo": results.demo_table,
        "note:demo": results.demo_note,
        "table:languages": results.language_table,
        "note:language_probe": results.language_note,
        "table:ranking": results.ranking_table,
        "table:pilot_effect": lambda: notes.pilot_effect(PILOT, round_name),
        "table:enrichment": lambda: notes.enrichment_table(notes.rounds_of((round_name, "e"))),
        "note:agreement": lambda: notes.agreement_summary(round_name),
        "note:states": notes.states_note,
        "note:audit": lambda: notes.audit_note(run, AUDIT),
        "note:campaign": notes.campaign_note,
        "note:errors": lambda: notes.errors_note(run),
        "table:errors": lambda: notes.errors_table(run),
        "table:error_examples": lambda: notes.error_examples_table(run),
        "note:position": lambda: notes.position_note(round_name),
        "note:noise": lambda: notes.single_reading_noise(round_name),
        "note:readers": lambda: notes.readers_note(run),
        "note:dims": lambda: notes.dims_note(run),
        "note:learning": lambda: notes.learning_note(run),
        "run": lambda: run,
        "model_key": lambda: (
            f"`{tables.read_json(RUNS / run / 'train.json')['config']['model_key']}`"
        ),
    }


def render(template: str, fill: dict[str, Callable[[], str]]) -> str:
    missing = sorted({m for m in _MARK.findall(template) if m not in fill})
    if missing:
        raise KeyError(f"marks with nothing to fill them: {missing}")
    return _MARK.sub(lambda match: fill[match[1]](), template)


def publish(run: str, round_name: str) -> None:
    """Puts the files behind the tables next to the metrics. Counts and rates only: no post."""
    out = Path("reports") / "probes"
    sources = {
        "agreement.json": round_dir(round_name) / "agreement.json",
        "thresholds.json": RUNS / run / "thresholds.json",
        "diagnostics.json": RUNS / run / "diagnostics.json",
        "train.json": RUNS / run / "train.json",
        "audit.json": RUNS / run / f"audit-{AUDIT}.json",
    }
    for name, source in sources.items():
        if source.exists():
            shutil.copyfile(source, out / name)
    rates = tables.prevalence(round_name, SPLITS)
    (out / "prevalence.json").write_text(json.dumps(rates, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--round", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    text = render(TEMPLATE.read_text(encoding="utf-8"), builders(args.run, args.round))
    REPORT.write_text(text, encoding="utf-8")
    publish(args.run, args.round)
    log.info("%s written, %d lines", REPORT, text.count("\n"))


if __name__ == "__main__":
    main()
