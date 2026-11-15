"""Exports the posts the annotators of the probe campaign read, as the one file the method
page explores and offers for download: `data/method/labelled.sqlite`.

One row per post and per round that read it: its text, its split, why it was drawn, the settled
answers, every reading with the spans it quoted, and the vector of the post. The pilot round is
left out: it was read with the first version of the guides. The rounds of the audit hold posts
of other rounds read again by another model: they are rows of their own, of kind
`second reader`, and settle no answer.

The campaign is read through its own loaders (`pipelines.probes`). The file is written anew at
each run: run it again when rounds were added.

Run: uv run --group pipelines python -m pipelines.method.labelled
"""

import json
import logging
from pathlib import Path

from backend.method.labelled import ANNOTATION, SECOND_READER, LabelledRecord, write_labelled
from backend.method.schema import LabelledSummary, Reading
from pipelines import runlog
from pipelines.paths import DATA

log = logging.getLogger("method.labelled")

LABELLED = DATA / "method" / "labelled.sqlite"
SETTLED_FILE = "settled.json"


def round_names() -> list[str]:
    """The rounds to publish, in the order they were drawn: every round but the pilot."""
    from pipelines.probes.report import PILOT
    from pipelines.probes.sample import ITEMS_FILE, ROUNDS

    drawn = [(path.stat().st_mtime_ns, path.parent.name) for path in ROUNDS.glob(f"*/{ITEMS_FILE}")]
    return [name for _, name in sorted(drawn) if name != PILOT]


def kind_of(round_name: str) -> str:
    """The audit named `a1` reads posts again in the rounds `a1_<family>`."""
    from pipelines.probes.report import AUDIT

    return SECOND_READER if round_name.startswith(f"{AUDIT}_") else ANNOTATION


def records_of(round_name: str, kind: str) -> list[LabelledRecord]:
    """The posts of a round that were read, in the order of the round."""
    from pipelines.probes.merge import READINGS, load_reading
    from pipelines.probes.sample import read_items, round_dir
    from pipelines.probes.taxonomy import FAMILIES

    readings: dict[str, list[Reading]] = {}
    settled: dict[str, dict[str, str]] = {}
    for family in FAMILIES:
        for letter in READINGS:
            for key, row in load_reading(round_name, family, letter).items():
                reading = Reading(
                    reader=row["batch_id"], answers=row["labels"], quotes=row["evidence"]
                )
                readings.setdefault(key, []).append(reading)
        path = round_dir(round_name) / "labels" / family / SETTLED_FILE
        # A second reading is never taken for the answer of the annotators.
        if kind == ANNOTATION and path.exists():
            for key, answers in json.loads(path.read_text(encoding="utf-8")).items():
                settled.setdefault(key, {}).update(answers)
    return [
        LabelledRecord(
            id=item.key,
            text=item.text,
            split=item.split,
            round=round_name,
            kind=kind,
            stratum=item.stratum,
            answers=settled.get(item.key, {}),
            readings=readings[item.key],
        )
        for item in read_items(round_name)
        if item.key in readings
    ]


def export(out: Path) -> LabelledSummary:
    from pipelines.probes.dataset import vectors_for

    records = [record for name in round_names() for record in records_of(name, kind_of(name))]
    if not records:
        raise SystemExit("no round has been read yet: nothing to export")
    vectors, model_key = vectors_for([record.id for record in records])
    return write_labelled(out, records, vectors, model_key)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    with runlog.timed() as elapsed:
        summary = export(LABELLED)
    kinds = ", ".join(f"{posts} {kind}" for kind, posts in summary.kinds.items())
    note = f"{len(summary.rounds)} rounds of the probe campaign: {kinds}"
    runlog.record("labelled", "method", summary.posts, elapsed[0], note=note)
    log.info("%d posts in %s (%s) in %.1fs", summary.posts, LABELLED, note, elapsed[0])


if __name__ == "__main__":
    main()
