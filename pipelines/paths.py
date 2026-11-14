"""Where each pipeline step reads and writes under `data/` (git-ignored)."""

from pathlib import Path

DATA = Path("data")
RAW = DATA / "raw"
DATASET_MANIFEST = DATA / "MANIFEST.json"
EMBEDDINGS = DATA / "embeddings"
RUN_LOG = Path("reports") / "pipeline-runs.jsonl"

# Files of a build's working folder, each written by the step named after it.
CORPUS_FILE = "corpus.sqlite"
VECTORS_FILE = "vectors.f16"
VECTORS_META = "vectors.json"
LAYOUT_FILE = "layout.npz"
NEIGHBOURS_FILE = "neighbours.npy"
ZONES_FILE = "zones.json"
ZONE_OF_POINT_FILE = "zone.npy"


def work_dir(name: str) -> Path:
    """Intermediate files of one build: corpus, vectors, layout, neighbours, zones."""
    return DATA / "work" / name


def build_dir(name: str) -> Path:
    """The folder the server loads (contract: backend/map/schema.py)."""
    return DATA / "build" / name
