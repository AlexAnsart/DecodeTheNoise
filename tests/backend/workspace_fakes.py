"""The whole API on a temp folder with stand-ins for the embedding model and the LLM: no test
calls a model or the network."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import numpy as np
from analyze_fakes import FakeEmbedder
from conftest import DIMS, EMBEDDING_KEY, write_tiny_build
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analyze.coordinates import load_coordinates
from backend.main import mount, set_limiters
from backend.map.store import MapBuild, load_build
from backend.probes.pack import Probes, load_probes
from backend.refresh.layout import on_axes
from backend.services import Services, start_services


def unit(values: list[float]) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


@dataclass
class FakeModel:
    """A fixed vector per text: the one registered for it, else one drawn from its hash."""

    key: str = EMBEDDING_KEY
    by_text: dict[str, np.ndarray] = field(default_factory=dict)
    calls: list[list[str]] = field(default_factory=list)
    # How many of the next calls fail, as when the model is down.
    failing: int = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        if self.failing:
            self.failing -= 1
            raise httpx.ConnectError("the model is down")
        self.calls.append(list(texts))
        return np.stack([self.by_text.get(text, self._drawn(text)) for text in texts])

    def _drawn(self, text: str) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
        return unit(np.random.default_rng(seed).normal(size=DIMS).tolist())


@dataclass
class FakeChat:
    """Names every zone the same way and supports every probe it is asked about."""

    asked: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        self.asked.append((system, user))
        if "findings" not in system:
            return json.dumps({"name": f"Zone number {len(self.asked)}"})
        keys = [line.split("key: ")[1] for line in user.splitlines() if line.startswith("- key: ")]
        findings = [
            {"probe": key, "reading": "supported", "explanation": "It does.", "quote": None}
            for key in keys
        ]
        return json.dumps({"findings": findings})


class FakeComputing:
    """Stands in for the computing process: no second process, and no UMAP, which compiles
    for a long time. Whatever layout is asked, the points are laid on their axes."""

    def run(self, function: object, vectors: np.ndarray, components: int, *rest: object) -> object:
        return on_axes(vectors, components)

    def start(self, function: object, *args: object) -> None:
        return None

    def close(self) -> None:
        return None


@dataclass
class Platform:
    client: TestClient
    app: FastAPI
    services: Services
    model: FakeModel
    chat: FakeChat
    build: MapBuild
    root: Path

    def new_workspace(self) -> dict[str, str]:
        """Creates a workspace; returns the headers that carry its key."""
        created = self.client.post("/api/workspaces")
        assert created.status_code == 200
        return {"Authorization": f"Bearer {created.json()['api_key']}"}

    def settle(self, delayed: bool = True) -> None:
        """Waits for the background jobs; with `delayed` false, not for the ones set to be
        tried again later."""
        assert self.services.jobs is not None
        self.services.jobs.join(delayed)


def make_app(root: Path, model: FakeModel, chat: FakeChat | None, probes: Probes) -> Platform:
    build_folder = root / "build"
    if not build_folder.exists():
        build_folder.mkdir(parents=True)
        write_tiny_build(build_folder)
    build = load_build(build_folder)
    assert build is not None
    services = start_services(
        root / "workspaces", model, DIMS, probes, chat, "test-llm", FakeComputing()
    )
    app = FastAPI()
    mount(app)
    set_limiters(app)
    app.state.build = build
    app.state.embedder = FakeEmbedder(key=EMBEDDING_KEY, default=build.vectors[3])
    app.state.coordinates = load_coordinates(build)
    app.state.page_reader = None
    app.state.probes = probes
    app.state.reports_dir = root / "reports"
    app.state.score_cache = {}
    app.state.sample_cache = {}
    app.state.services = services
    return Platform(TestClient(app), app, services, model, chat or FakeChat(), build, root)


def probes_in(folder: Path) -> Probes:
    return load_probes(folder, EMBEDDING_KEY)
