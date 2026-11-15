"""The audit of the test labels by a person: a sheet to fill, and its score.

`--write` turns the audit rounds (`audit --make`) into one CSV: a row per post, with the probe it
is audited for, the question of the guide, the text, and an empty `answer` column. The settled
answer is not in the sheet: the reading is blind. The reader opens the guide of the label when in
doubt and writes `yes` or `no`.

`--score` compares the filled sheet with the settled answers and writes
`audit-<name>-human.json` in the run. `evaluate` reads every audit of the run, and this file
comes after the model's audit: a person's reading replaces it for the probes it covers.

Run: uv run --group pipelines python -m pipelines.probes.audit_sheet --name a1 --write
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from pipelines.probes.batches import GUIDES
from pipelines.probes.dataset import load_labelled
from pipelines.probes.pool import PROBES
from pipelines.probes.sample import ROUNDS, read_items
from pipelines.probes.taxonomy import BY_NAME, NO, YES
from pipelines.probes.train import RUNS

log = logging.getLogger("probes.audit_sheet")

SHEETS = PROBES / "audit"
COLUMNS = ("row", "probe", "question", "post", "answer")


def question_of(label: str) -> str:
    """The question the guide asks for a label."""
    guide = (GUIDES / f"{BY_NAME[label].family}.md").read_text(encoding="utf-8")
    section = guide.split(f"## `{label}`", 1)[1]
    line = next(line for line in section.splitlines() if line.startswith("**Question.**"))
    return line.removeprefix("**Question.**").strip()


def write_sheet(name: str) -> Path:
    rows = []
    for folder in sorted(ROUNDS.glob(f"{name}_*")):
        for item in read_items(folder.name):
            probe = item.stratum.removeprefix("audit:")
            rows.append([f"{item.key}|{probe}", probe, question_of(probe), item.text, ""])
    SHEETS.mkdir(parents=True, exist_ok=True)
    path = SHEETS / f"{name}.csv"
    # utf-8-sig: a spreadsheet opens the file with the right encoding.
    with path.open("w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    log.info("%s: %d rows", path, len(rows))
    return path


def score_sheet(name: str, rounds: tuple[str, ...]) -> dict[str, dict[str, list[int]]]:
    """Per probe: settled yes the reader confirms, settled no the reader overturns."""
    labelled = load_labelled(rounds)
    position = {key: i for i, key in enumerate(labelled.keys)}
    out: dict[str, dict[str, list[int]]] = {}
    with (SHEETS / f"{name}.csv").open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            answer = row["answer"].strip().lower()
            key, probe = row["row"].rsplit("|", 1)
            settled = labelled.answers[probe][position[key]] if key in position else ""
            if answer not in (YES, NO) or settled not in (YES, NO):
                continue
            cell = out.setdefault(probe, {YES: [0, 0], NO: [0, 0]})
            cell[settled][0] += answer == YES
            cell[settled][1] += 1
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--run", help="with --score: the run the audit belongs to")
    parser.add_argument("--rounds", nargs="*", default=[], help="with --score: settled rounds")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if args.write:
        write_sheet(args.name)
    if args.score:
        result = score_sheet(args.name, tuple(args.rounds))
        path = RUNS / args.run / f"audit-{args.name}-human.json"
        path.write_text(json.dumps(result, indent=1), encoding="utf-8")
        for probe, cell in result.items():
            log.info("%-28s yes confirmed %s, no overturned %s", probe, cell[YES], cell[NO])


if __name__ == "__main__":
    main()
