from pathlib import Path

import pytest

from pipelines.pack import publish


@pytest.fixture
def builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(publish, "build_dir", lambda name: tmp_path / name)
    return tmp_path


def _build(folder: Path, content: str) -> Path:
    folder.mkdir()
    (folder / "map.json").write_text(content, encoding="utf-8")
    return folder


def test_first_publish_creates_current(builds: Path) -> None:
    publish.publish_as_current(_build(builds / "a", "A"))
    assert (builds / "current" / "map.json").read_text(encoding="utf-8") == "A"


def test_publish_replaces_current_and_leaves_no_staging_folder(builds: Path) -> None:
    publish.publish_as_current(_build(builds / "a", "A"))
    publish.publish_as_current(_build(builds / "b", "B"))
    assert (builds / "current" / "map.json").read_text(encoding="utf-8") == "B"
    assert sorted(p.name for p in builds.iterdir()) == ["a", "b", "current"]
