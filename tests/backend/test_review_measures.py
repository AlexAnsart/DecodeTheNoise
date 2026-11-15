import json
from pathlib import Path

from backend.review.measures import NO_MEASURES, load_measures
from backend.review.schema import Finding, Review, Technique

MODEL = "test-model"
VERSION = "review-v2"


def _write_report(reports: Path, model: str = MODEL, version: str = VERSION) -> None:
    folder = reports / "review"
    folder.mkdir(parents=True)
    interval = {"value": 0.8, "low": 0.7, "high": 0.9}
    report = {
        "model": model,
        "prompt_version": version,
        "reference": "labels of the probe campaign, test split",
        "labels": {
            "whataboutism": {
                "precision": interval,
                "recall": None,
                "marked": 25,
                "positives": 30,
                "n": 400,
            },
            "theme": {
                "precision": {"value": 0.6, "low": 0.5, "high": 0.7},
                "recall": {"value": 0.4, "low": 0.3, "high": 0.5},
                "marked": 50,
                "positives": 75,
                "n": 400,
            },
            # Marked four times: a precision on four posts is not shown.
            "fear_appeal": {"precision": interval, "marked": 4, "positives": 14, "n": 400},
            # The annotators disagree on it: the evaluation gives it no rate.
            "bandwagon": {
                "precision": None,
                "marked": 30,
                "positives": 3,
                "n": 400,
                "measurable": False,
            },
        },
        "pooled": {"precision": {"value": 0.78, "low": 0.73, "high": 0.82}, "tp": 231, "fp": 65},
    }
    (folder / "metrics.json").write_text(json.dumps(report), encoding="utf-8")


def _review(model: str = MODEL, version: str = VERSION) -> Review:
    return Review(
        status="done",
        model=model,
        prompt_version=version,
        findings=[
            Finding(probe="theme:sport", reading="supported", explanation="x", quote=None),
            Finding(probe="call_amplify", reading="supported", explanation="x", quote="y"),
        ],
        techniques=[Technique(key="whataboutism", name="Whataboutism", explanation="x", quote="y")],
    )


def test_a_reading_carries_what_the_evaluation_measured_for_its_label(tmp_path: Path) -> None:
    _write_report(tmp_path)

    review = load_measures(tmp_path).attach(_review())

    assert review.measured is True
    technique = review.techniques[0].reliability
    assert technique is not None
    assert (technique.precision, technique.precision_low, technique.precision_high) == (
        0.8,
        0.7,
        0.9,
    )
    assert (technique.recall, technique.read, technique.report) == (None, 25, "review")
    # One answer of a label is measured as its label; a label the report lacks has no measure.
    theme, calls = review.findings
    assert theme.reliability is not None and (theme.reliability.recall, theme.reliability.read) == (
        0.4,
        50,
    )
    assert calls.reliability is None


def test_a_label_too_thin_to_measure_shows_no_figure_of_its_own(tmp_path: Path) -> None:
    _write_report(tmp_path)
    named = [
        Technique(key=key, name=key, explanation="x", quote="y")
        for key in ("fear_appeal", "bandwagon", "whataboutism")
    ]
    review = _review().model_copy(update={"techniques": named})

    attached = load_measures(tmp_path).attach(review)

    assert [technique.reliability is not None for technique in attached.techniques] == [
        False,
        False,
        True,
    ]
    # What the screen measured over every technique together stands in for them.
    assert attached.overall is not None
    assert (attached.overall.precision, attached.overall.read) == (0.78, 296)


def test_another_model_or_prompt_is_not_measured(tmp_path: Path) -> None:
    _write_report(tmp_path)
    measures = load_measures(tmp_path)

    for review in (_review(model="another-model"), _review(version="review-v1")):
        attached = measures.attach(review)
        assert attached.measured is False
        assert attached.techniques[0].reliability is None
        assert attached.overall is None

    failed = measures.attach(Review(status="failed", model=MODEL, prompt_version=VERSION))
    assert failed.measured is False


def test_without_a_readable_report_nothing_is_measured(tmp_path: Path) -> None:
    assert load_measures(tmp_path) is NO_MEASURES
    assert NO_MEASURES.attach(_review()).measured is False

    (tmp_path / "review").mkdir()
    (tmp_path / "review" / "metrics.json").write_text('{"model": "x"}', encoding="utf-8")
    assert load_measures(tmp_path) is NO_MEASURES


def test_a_reading_that_does_not_support_the_probe_carries_no_figure(tmp_path: Path) -> None:
    _write_report(tmp_path)
    readings = [
        Finding(probe="whataboutism", reading=reading, explanation="x", quote=None)
        for reading in ("supported", "not supported", "unclear")
    ]
    review = _review().model_copy(update={"findings": readings})

    attached = load_measures(tmp_path).attach(review)

    assert [finding.reliability is not None for finding in attached.findings] == [
        True,
        False,
        False,
    ]
