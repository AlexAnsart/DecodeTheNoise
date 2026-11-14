"""Test 1 on real data: can a probe read which IRA team an account belongs to, and from how
many posts?

The teams of the Internet Research Agency (labels of Linvill and Warren) are briefs that people
carried out before language models. Accounts are split, never posts: a test account is new.

Run: uv run --group pipelines python -m pipelines.briefs.ira_teams
"""

import hashlib
import logging
import sqlite3

import numpy as np

from pipelines.briefs.bench import SEED, write_result
from pipelines.briefs.field_probes import SIZES, fit_probe
from pipelines.briefs.ncurve import interval, pooled_accuracy, rounded
from pipelines.paths import CORPUS_FILE, work_dir
from pipelines.vectors import read_vectors

log = logging.getLogger("briefs.ira_teams")

BUILD = "ira-120k"
TEAMS = ("RightTroll", "LeftTroll", "NewsFeed", "HashtagGamer")
MIN_POSTS = 8
TEST_TENTHS = 3


def is_test(actor: str) -> bool:
    """A hash of the actor decides its side, so the split is the same on every run."""
    return int(hashlib.sha256(actor.encode("utf-8")).hexdigest()[:8], 16) % 10 < TEST_TENTHS


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work = work_dir(BUILD)
    vectors, key = read_vectors(work)
    con = sqlite3.connect(f"file:{(work / CORPUS_FILE).as_posix()}?mode=ro", uri=True)
    query = (
        "select idx, actor_id, category from items where post_type != 'repost' and lang = 'English'"
    )
    rows = [row for row in con.execute(query) if row[2] in TEAMS]
    con.close()
    actors = np.array([row[1] for row in rows])
    names, counts = np.unique(actors, return_counts=True)
    enough = np.isin(actors, names[counts >= MIN_POSTS])
    actors = actors[enough]
    x = vectors[[row[0] for row, keep in zip(rows, enough, strict=True) if keep]]
    y = np.array([TEAMS.index(row[2]) for row, keep in zip(rows, enough, strict=True) if keep])
    test = np.array([is_test(actor) for actor in actors])

    model, strength = fit_probe(x[~test], y[~test], actors[~test])
    log_proba = model.predict_log_proba(x[test])
    rng = np.random.default_rng(SEED)
    curve = {}
    for size in SIZES:
        shares = pooled_accuracy(log_proba, actors[test], y[test], size, rng)
        curve[size] = {"actors": len(shares), "accuracy": rounded(interval(shares, rng))}
    team_of = {actor: team for actor, team in zip(actors[test], y[test], strict=True)}
    share = np.bincount(list(team_of.values()), minlength=len(TEAMS)) / len(team_of)
    payload = {
        "build": BUILD,
        "embedding_key": key,
        "seed": SEED,
        "teams": list(TEAMS),
        "split": "by account, 30% of accounts held out by hash",
        "train": {"accounts": len(set(actors[~test])), "posts": int((~test).sum())},
        "test": {"accounts": len(team_of), "posts": int(test.sum())},
        "test_accounts_per_team": dict(
            zip(TEAMS, np.bincount(list(team_of.values())).tolist(), strict=False)
        ),
        "majority_baseline": round(float(share.max()), 3),
        "regularisation": strength,
        "interval": "95%, bootstrap over test accounts",
        "curve": curve,
    }
    log.info(
        "majority %.3f; accuracy at 1 / 8 / 32 posts: %s / %s / %s",
        share.max(),
        curve[1]["accuracy"][0],
        curve[8]["accuracy"][0],
        curve[32]["accuracy"][0],
    )
    log.info("written: %s", write_result("ira-teams", payload))


if __name__ == "__main__":
    main()
