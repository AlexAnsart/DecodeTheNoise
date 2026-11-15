"""The export of a probe run: from the run's files to the pack the server loads."""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from backend.probes.pack import load_probes
from backend.probes.schema import PACK_FILE, WEIGHTS_FILE, ProbePack
from pipelines.probes.export import (
    Cuts,
    ExportRefused,
    descriptions,
    display,
    export_pack,
    review_cut,
)
from pipelines.probes.taxonomy import BY_NAME

KEY = "test-model@0|prefix=''|dims=4"
RUN = "v1"
NAMES = [
    "call_amplify",
    "theme:sport",
    "doubt",
    "slogan",
    "threat",
    "irony",
    "made_up",
    "anger",
    "profanity",
    "call_join",
]
DOC = """
| Label | What the annotator decides | Use |
| --- | --- | --- |
| `call_amplify` | Asks to share, repost, copy-paste, tag, push a hashtag | Probe. Feeds `open` |
| `theme` | One main theme in a fixed list of fourteen | Descriptor |
| `doubt` | Questions someone's credibility without giving grounds | Probe |
"""


def _level(threshold: float, precision: float | None, read: int = 40) -> dict[str, object]:
    """One level as `pipelines.probes.evaluate` writes it; the unused keys are left out."""
    interval = None if precision is None else {"value": precision, "low": 0.6, "high": 0.95}
    return {
        "threshold": threshold,
        "flagged": 900,
        "flag_rate": 0.02,
        "read_flagged": read,
        "positive_flagged": 30,
        "precision": interval,
        "recall": {"value": 0.4, "low": 0.3, "high": 0.5},
        "fpr": None if precision is None else {"value": 0.01, "low": 0.0, "high": 0.02},
        "wilson": [0.6, 0.9],
    }


def _edge(threshold: float, precision: float | None, read: int, share: float) -> dict[str, object]:
    """One candidate cut as `pipelines.probes.calibrate` writes it."""
    interval = None if precision is None else {"value": precision, "low": 0.1, "high": 0.9}
    return {"threshold": threshold, "precision": interval, "read_flagged": read, "flag_rate": share}


# Good enough for a review cut: one real post in two, on ninety posts read, 0.5% flagged.
WORTH = [_edge(0.0, 0.5, 90, 0.005)]
NO_LEVEL = {"possible": None, "probable": None}


def _write_run(
    root: Path, metrics_run: str = RUN
) -> tuple[Path, Path, Path, dict[str, np.ndarray]]:
    rng = np.random.default_rng(1)
    arrays = {
        "names": np.array(NAMES),
        "weights": rng.normal(size=(len(NAMES), 4)).astype(np.float32),
        "bias": rng.normal(size=len(NAMES)),
        "mean": rng.normal(scale=0.05, size=4).astype(np.float32),
        "scale": rng.uniform(0.02, 0.08, size=4).astype(np.float32),
    }
    run_dir = root / "runs" / RUN
    run_dir.mkdir(parents=True)
    np.savez(run_dir / "probes.npz", **arrays)
    cuts = {
        "call_amplify": {"read": 80, "possible": 0.5, "probable": 2.0, "edges": []},
        "theme:sport": {"possible": 1.0, "probable": None},
        "doubt": {"possible": 0.2, "probable": 1.2},
        # Review-only with a measured level: the level reads it, whatever its edges.
        "slogan": {"possible": 0.0, "probable": None, "edges": WORTH},
        # Review-only without a level: the deepest edge worth a review is 0.5. Deeper, the
        # precision is unknown, then too many posts are flagged, then too few are real.
        "threat": {
            **NO_LEVEL,
            "edges": [
                _edge(2.0, 0.8, 30, 0.001),
                _edge(0.5, 0.3, 50, 0.008),
                _edge(0.2, None, 60, 0.009),
                _edge(-0.4, 0.25, 70, 0.02),
                _edge(-1.0, 0.1, 80, 0.05),
            ],
        },
        # An auxiliary label and a descriptor: never sent to the review, whatever their edges.
        "irony": {**NO_LEVEL, "edges": WORTH},
        "anger": {"possible": 0.2, "probable": None, "edges": WORTH},
        "made_up": {"possible": None, "probable": 1.5},
        "profanity": {"possible": 0.3, "probable": 0.9},
        # A detector with no edge worth a review: too few posts read, too few real ones,
        # too many flagged.
        "call_join": {
            **NO_LEVEL,
            "edges": [
                _edge(1.0, 0.9, 5, 0.001),
                _edge(0.1, 0.1, 40, 0.005),
                _edge(-0.5, 0.4, 60, 0.03),
            ],
        },
    }
    (run_dir / "thresholds.json").write_text(json.dumps(cuts), encoding="utf-8")
    unlevelled = {"state": "review-only", "levels": {}, "head": {"read": 46, "positive": 26}}
    targets = {
        "call_amplify": {
            "state": "shown",
            "levels": {"probable": _level(2.0, 0.9, read=35), "possible": _level(0.5, 0.7)},
        },
        "theme:sport": {"state": "shown", "levels": {"possible": _level(1.0, 0.8)}},
        # The probable band was not read on the test split: its precision is unknown.
        "doubt": {
            "state": "shown",
            "levels": {"probable": _level(1.2, None), "possible": _level(0.2, 0.65)},
        },
        "slogan": {"state": "review-only", "levels": {"possible": _level(0.0, 0.4)}},
        "threat": unlevelled,
        "irony": unlevelled,
        # Review-only with a measured level, but a descriptor: neither shown nor reviewed.
        "anger": {"state": "review-only", "levels": {"possible": _level(0.2, 0.7)}},
        "made_up": {"state": "shown", "levels": {"probable": _level(1.5, 0.85)}},
        "profanity": {
            "state": "dropped",
            "levels": {"probable": _level(0.9, 0.3), "possible": _level(0.3, 0.2)},
        },
        "call_join": unlevelled,
    }
    metrics_file = root / "reports" / "probes" / "metrics.json"
    metrics_file.parent.mkdir(parents=True)
    report = {"run": metrics_run, "rounds": ["m1"], "model_key": KEY, "targets": targets}
    metrics_file.write_text(json.dumps(report), encoding="utf-8")
    doc = root / "taxonomy.md"
    doc.write_text(DOC, encoding="utf-8")
    return run_dir, metrics_file, doc, arrays


def test_run_becomes_a_pack_the_server_reads(tmp_path: Path) -> None:
    run_dir, metrics_file, doc, arrays = _write_run(tmp_path)
    out = tmp_path / "probes"

    pack = export_pack(RUN, run_dir, metrics_file, doc, out)

    assert pack == ProbePack.model_validate_json((out / PACK_FILE).read_text(encoding="utf-8"))
    assert pack.embedding_key == KEY and pack.run == RUN
    by_key = {probe.info.key: probe for probe in pack.probes}
    # Dropped, not a detector, or with neither a measured level nor a review cut: not in the pack.
    assert list(by_key) == ["call_amplify", "theme:sport", "doubt", "slogan", "threat", "made_up"]

    calls = by_key["call_amplify"]
    assert (calls.possible_cut, calls.probable_cut, calls.review_cut) == (0.5, 2.0, None)
    assert calls.info.label == "Call amplify"
    assert calls.info.description == "Asks to share, repost, copy-paste, tag, push a hashtag"
    assert calls.info.family == BY_NAME["call_amplify"].family
    assert calls.info.state == "shown" and calls.info.report == "probes"
    probable = calls.info.probable
    assert probable is not None and calls.info.possible is not None
    assert (probable.precision, probable.precision_low, probable.precision_high) == (0.9, 0.6, 0.95)
    assert (probable.false_positive_rate, probable.recall) == (0.01, 0.4)
    assert (probable.read, probable.flag_rate) == (35, 0.02)

    # A detector sends its flags to the review; one answer of a descriptor never does.
    assert calls.reviewable and not by_key["theme:sport"].reviewable

    doubt = by_key["doubt"]
    assert doubt.probable_cut is None and doubt.info.probable is None
    assert doubt.possible_cut == 0.2 and doubt.info.possible is not None
    assert by_key["made_up"].info.family == "other"

    # Review-only with a level: packed with that level, and no review cut.
    slogan = by_key["slogan"]
    assert slogan.info.state == "review-only" and slogan.info.description == "Slogan"
    assert (slogan.possible_cut, slogan.probable_cut, slogan.review_cut) == (0.0, None, None)
    assert slogan.info.possible is not None and slogan.info.possible.precision == 0.4
    # Review-only without a level: packed with its review cut, and no measure to show.
    threat = by_key["threat"]
    assert threat.info.state == "review-only"
    assert (threat.possible_cut, threat.probable_cut, threat.review_cut) == (None, None, 0.5)
    assert threat.info.possible is None and threat.info.probable is None

    with np.load(out / WEIGHTS_FILE) as written:
        assert [str(name) for name in written["names"]] == list(by_key)
        assert np.array_equal(written["weights"], arrays["weights"][[0, 1, 2, 3, 4, 6]])

    probes = load_probes(out, KEY)
    assert [info.key for info in probes.infos] == list(by_key)
    assert [info.key for info in probes.shown()] == [
        "call_amplify",
        "theme:sport",
        "doubt",
        "made_up",
    ]
    # The weights of each probe followed it: the score is the one its own row gives.
    vector = np.array([0.5, -0.5, 0.5, 0.5], dtype=np.float32)
    logit = ((vector - arrays["mean"]) / arrays["scale"]) @ arrays["weights"][6] + arrays["bias"][6]
    expected = 1 / (1 + math.exp(-min(30.0, max(-30.0, logit + math.log(4) - 1.5))))
    assert probes.scores(vector)[0, probes.column("made_up")] == pytest.approx(expected, abs=1e-5)


def test_a_review_cut_is_for_a_detector_with_no_level_only(tmp_path: Path) -> None:
    run_dir, _, _, _ = _write_run(tmp_path)
    cuts = json.loads((run_dir / "thresholds.json").read_text(encoding="utf-8"))

    def cut_of(target: str) -> float | None:
        return review_cut(target, Cuts.model_validate(cuts[target]))

    assert cut_of("threat") == 0.5
    assert cut_of("call_join") is None
    # A descriptor, an auxiliary label, one answer of a label: not sent to the review.
    assert cut_of("anger") is None and cut_of("irony") is None
    assert review_cut("theme:sport", Cuts.model_validate({"edges": WORTH})) is None
    assert review_cut("lang:es", Cuts.model_validate({"edges": WORTH})) is None


def test_metrics_of_another_run_are_refused(tmp_path: Path) -> None:
    run_dir, metrics_file, doc, _ = _write_run(tmp_path, metrics_run="v0")

    with pytest.raises(ExportRefused, match="run v0"):
        export_pack(RUN, run_dir, metrics_file, doc, tmp_path / "probes")

    assert not (tmp_path / "probes").exists()


def test_a_cut_moved_since_the_evaluation_is_refused(tmp_path: Path) -> None:
    run_dir, metrics_file, doc, _ = _write_run(tmp_path)
    cuts = json.loads((run_dir / "thresholds.json").read_text(encoding="utf-8"))
    cuts["call_amplify"]["probable"] = 2.4
    (run_dir / "thresholds.json").write_text(json.dumps(cuts), encoding="utf-8")

    with pytest.raises(ExportRefused, match="call_amplify"):
        export_pack(RUN, run_dir, metrics_file, doc, tmp_path / "probes")

    assert not (tmp_path / "probes").exists()


def test_one_answer_of_a_label_is_named_after_it(tmp_path: Path) -> None:
    described = descriptions(_write_run(tmp_path)[2])

    label, description, family = display("theme:politics_government", described)

    assert label == "Theme: politics government"
    assert description == "One main theme in a fixed list of fourteen"
    assert family == BY_NAME["theme"].family
    assert descriptions(tmp_path / "absent.md") == {}
