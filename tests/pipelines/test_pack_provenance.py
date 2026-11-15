import json
from pathlib import Path

from backend.map.schema import PROVENANCE_FILE
from backend.method.schema import Provenance
from pipelines.corpus import write_corpus
from pipelines.pack.provenance import provenance_of, write_provenance
from pipelines.paths import CORPUS_FILE

URL = "https://huggingface.co/datasets/SinclairSchneider/tweets_sample_2026"
SAMPLE = {"sources": ["shard-a", "shard-b", "shard-gone"], "seed": "demo-sample-v1", "items": 2}


def _corpus(work: Path, meta: dict[str, str]) -> Path:
    write_corpus(work / CORPUS_FILE, [], meta)
    return work


def _manifest(root: Path) -> Path:
    datasets = [
        {"name": "other", "source": "https://example.org/other", "licence": "CC-BY-4.0"},
        {"name": "tweets-sample-2026", "source": URL, "licence": "not stated", "files": []},
    ]
    path = root / "MANIFEST.json"
    path.write_text(json.dumps({"datasets": datasets}), encoding="utf-8")
    return path


def _shard(root: Path, name: str, file: str) -> None:
    meta = {"dataset": "tweets-sample-2026", "revision": "254bbe4", "files": file}
    _corpus(root / name, {**meta, "min_text_chars": "20"})


def test_a_sample_takes_its_dataset_from_the_builds_it_was_drawn_from(tmp_path: Path) -> None:
    _shard(tmp_path, "shard-a", "train-00000.parquet")
    _shard(tmp_path, "shard-b", "train-00018.parquet,train-00019.parquet")
    work = _corpus(tmp_path / "demo", {"sample": json.dumps(SAMPLE)})
    out = tmp_path / "build"
    out.mkdir()

    written = write_provenance(work, out, _manifest(tmp_path))

    assert written == Provenance(
        dataset="tweets-sample-2026",
        source_url=URL,
        revision="254bbe4",
        files=["train-00000.parquet", "train-00018.parquet", "train-00019.parquet"],
        # Said as the manifest says it: nobody stated a licence.
        licence="not stated",
        sample=SAMPLE,
    )
    stored = (out / PROVENANCE_FILE).read_text(encoding="utf-8")
    assert Provenance.model_validate_json(stored) == written


def test_a_build_read_from_a_dataset_says_so_itself(tmp_path: Path) -> None:
    _shard(tmp_path, "shard-a", "train-00000.parquet")

    found = provenance_of(tmp_path / "shard-a", _manifest(tmp_path))

    assert found.dataset == "tweets-sample-2026"
    assert found.files == ["train-00000.parquet"]
    assert found.sample is None


def test_what_is_not_recorded_is_left_empty(tmp_path: Path) -> None:
    # The sources of the sample are not on this machine, and there is no manifest.
    work = _corpus(tmp_path / "demo", {"sample": json.dumps(SAMPLE)})
    unknown = _corpus(tmp_path / "unknown", {"dataset": "never-fetched"})

    lone = provenance_of(work, tmp_path / "absent.json")
    unlisted = provenance_of(unknown, _manifest(tmp_path))

    assert lone == Provenance(
        dataset=None, source_url=None, revision=None, files=[], licence=None, sample=SAMPLE
    )
    assert (unlisted.dataset, unlisted.source_url, unlisted.licence) == (
        "never-fetched",
        None,
        None,
    )
