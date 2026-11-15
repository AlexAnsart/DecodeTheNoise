"""How often does the one-voice check fire on the real posts of a build?

Runs the served check on every selection a person can make on the map with one gesture: a
word typed in the search, the same word within one month, or one zone within one month. A
selection counts when the check can read it. Nothing here is labelled: the result says how
often the check fires on ordinary posts, not how much coordination they hold.

Run: uv run --group pipelines python -m pipelines.briefs.voices_census --name tweets-2026-500k
"""

import argparse
import hashlib
import json
import logging
import re
import sqlite3
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from backend.voices.calibration import load_calibration
from backend.voices.score import SIZES, measured_size, read_voices
from pipelines.paths import CORPUS_FILE, VECTORS_FILE, VECTORS_META, ZONE_OF_POINT_FILE, work_dir

log = logging.getLogger("briefs.voices_census")

REPORTS = Path("reports")
# The route reads at most this many points; the interface samples a larger selection.
MAX_POSTS = 5000
MIN_POSTS = SIZES[-1][0] * SIZES[-1][1]
WORKERS = 8
CLOSEST = 25
_WORD = re.compile(r"\w{4,40}")
Selection = tuple[str, str, list[int], list[str]]  # kind, name, points, actor of each point

# Every flagged selection of each build measured, read by hand: its nature, and why in one line.
CAMPAIGN = (
    "campaign",
    "Five actors repost the same dated demand every day. The word belongs to its template, and "
    "the four actors with enough posts are the same in every such selection.",
)
NO_SUBJECT = (
    "false alarm",
    "A common word or phrase used in unrelated posts by unrelated actors: no shared subject.",
)
ONE_EVENT = ("false alarm", "Independent people and outlets reacting to one event or one show.")
_TEMPLATE_WORDS = (
    "jensspahn", "verfahren", "täglich", "eingestellt", "ermittlungen", "aufnahme",
    "spahnrücktritt", "poste", "fordern", "werde", "strafrechtlich",
)  # fmt: skip
_CAMPAIGN_MONTH = {f"{word}, 2026-03": CAMPAIGN for word in _TEMPLATE_WORDS}
AUDIT: dict[str, dict[str, tuple[str, str]]] = {
    "tweets-2026-500k": {
        **_CAMPAIGN_MONTH,
        "literarisch, 2026-01": NO_SUBJECT,
        "befürchte": NO_SUBJECT,
        "russische, 2026-05": (
            "false alarm",
            "One broad subject, written about by actors with opposite views.",
        ),
        "kris, 2026-05": ONE_EVENT,
    },
    "tweets-2026-100k": {
        **_CAMPAIGN_MONTH,
        "befürchte": NO_SUBJECT,
        "literarisch": NO_SUBJECT,
        "passiert": NO_SUBJECT,
        "kater": NO_SUBJECT,
        "komplett": NO_SUBJECT,
        "dschungel": ONE_EVENT,
        "knoblauch, 2026-03": ONE_EVENT,
        "zone 13, 2026-01": (
            "false alarm",
            "A broad zone of general commentary in one month: no shared subject.",
        ),
    },
}
NOT_READ = ("not read yet", "")

_vectors: np.ndarray | None = None


def _score(task: tuple[str, int, Selection]) -> dict[str, object] | None:
    """One selection, read at the largest measured size. Runs in a worker process."""
    # One memory map per worker process, opened on its first selection.
    global _vectors
    work, dims, (kind, name, points, actors) = task
    if _vectors is None:
        _vectors = np.memmap(Path(work) / VECTORS_FILE, dtype=np.float16, mode="r").reshape(
            -1, dims
        )
    who = np.array(actors)
    size = measured_size(who)
    if size is None:
        return None
    # The same selection always gets the same draws.
    seed = int(hashlib.sha256(f"{kind}:{name}".encode()).hexdigest()[:16], 16)
    voices = read_voices(
        np.asarray(_vectors[points], dtype=np.float32), who, size, np.random.default_rng(seed)
    )
    if voices is None:
        return None
    return {
        "kind": kind,
        "name": name,
        "posts": len(points),
        "actors": len(set(actors)),
        "actors_with_enough_posts": voices.eligible_actors,
        "size": f"{size[0]}x{size[1]}",
        "score": round(voices.score, 2),
    }


def selections(work: Path) -> list[Selection]:
    """Every word, word in a month, and zone in a month that could be read."""
    zone = np.load(work / ZONE_OF_POINT_FILE)
    con = sqlite3.connect(f"file:{(work / CORPUS_FILE).as_posix()}?mode=ro", uri=True)
    query = "select idx, actor_id, text, created_at from items where post_type != 'repost'"
    rows = con.execute(query).fetchall()
    con.close()
    per_actor = Counter(row[1] for row in rows)
    # A word is worth trying when enough actors each use it in enough posts.
    uses: dict[str, Counter[str]] = defaultdict(Counter)
    for _idx, actor, text, _ts in rows:
        if per_actor[actor] >= SIZES[-1][1]:
            for word in set(_WORD.findall(text.lower())):
                uses[actor][word] += 1
    steady = Counter(w for words in uses.values() for w, n in words.items() if n >= SIZES[-1][1])
    words = {word for word, actors in steady.items() if actors >= SIZES[-1][0]}
    groups: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    for idx, actor, text, ts in rows:
        month = datetime.fromtimestamp(ts / 1000, UTC).strftime("%Y-%m") if ts else "undated"
        groups[("zone in a month", f"zone {int(zone[idx])}, {month}")].append((idx, actor))
        for word in set(_WORD.findall(text.lower())) & words:
            groups[("word", word)].append((idx, actor))
            groups[("word in a month", f"{word}, {month}")].append((idx, actor))
    return [
        (kind, name, [i for i, _ in members], [a for _, a in members])
        for (kind, name), members in groups.items()
        if MIN_POSTS <= len(members) <= MAX_POSTS
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work = work_dir(args.name)
    meta = json.loads((work / VECTORS_META).read_text(encoding="utf-8"))
    calibration = load_calibration(REPORTS)
    if calibration is None or calibration.embedding_key != meta["key"]:
        raise SystemExit("the check was not measured for the embedding model of this build")
    threshold = {f"{s.actors}x{s.posts_each}": s.threshold for s in calibration.sizes}

    tried = selections(work)
    log.info("%d selections to try", len(tried))
    tasks = [(work.as_posix(), int(meta["dims"]), selection) for selection in tried]
    with ProcessPoolExecutor(WORKERS) as pool:
        read = [r for r in pool.map(_score, tasks, chunksize=64) if r is not None]
    for entry in read:
        entry["threshold"] = threshold[str(entry["size"])]
        entry["flagged"] = bool(entry["score"] < entry["threshold"])
        if entry["flagged"]:
            audit = AUDIT.get(args.name, {})
            entry["nature"], entry["reason"] = audit.get(str(entry["name"]), NOT_READ)
    read.sort(key=lambda e: float(e["score"]) - float(e["threshold"]))
    kinds = sorted({str(e["kind"]) for e in read})
    payload = {
        "build": args.name,
        "embedding_key": meta["key"],
        "points": int(meta["n"]),
        "definition": {
            "word": "every post, reposts left out, that holds one word of 4 letters or more",
            "word in a month": "the same, within one calendar month",
            "zone in a month": "every post of one zone of the map within one calendar month",
            "kept": f"selections of {MIN_POSTS} to {MAX_POSTS} posts that the check can read: "
            f"at least {SIZES[-1][0]} actors with {SIZES[-1][1]} posts each",
        },
        "selections_tried": len(tried),
        "selections_read": len(read),
        "flagged": sum(bool(e["flagged"]) for e in read),
        "by_kind": {
            kind: {
                "read": sum(e["kind"] == kind for e in read),
                "flagged": sum(e["kind"] == kind and bool(e["flagged"]) for e in read),
            }
            for kind in kinds
        },
        "flagged_by_nature": dict(Counter(str(e["nature"]) for e in read if e["flagged"])),
        "flagged_selections": [e for e in read if e["flagged"]],
        "closest_to_the_threshold": read[:CLOSEST],
        "note": "Nothing is labelled: this is how often the check fires on real posts, an "
        "upper bound on its false alarms there, not a measure of coordination.",
    }
    folder = REPORTS / "voices"
    path = folder / f"census-{args.name}.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info("%d read, %d flagged; written: %s", len(read), payload["flagged"], path)


if __name__ == "__main__":
    main()
