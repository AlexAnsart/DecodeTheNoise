"""Measures the LLM review against the annotation of the probe campaign.

Three stages, 1,500 calls at most over every run of this script:
1. the technique screen on every post of the random test sample: text alone, no probe listed;
2. the same question asked again on 200 of them, to see whether the answer holds;
3. the cascade: posts a technique probe flags, read with the probe listed as the product does.

Answers are cached in `data/llm/review-eval.jsonl`: a second run pays for nothing it has. The
run writes `reports/review/metrics.json`; `pipelines.review.report` then writes the report.
`--limit N` reads N posts per stage to try the script, and writes nothing under `reports/`.

Run: uv run --group pipelines python -m pipelines.review.evaluate [--limit N]
"""

import argparse
import hashlib
import logging
import subprocess
from collections import Counter
from datetime import datetime
from functools import partial

from backend.model_client.llm import ChatClient
from backend.review.guides import load_guides
from backend.review.prompt import PROMPT_VERSION, ReviewRequest, system_prompt
from backend.settings import get_settings
from pipelines import runlog
from pipelines.paths import DATA
from pipelines.review.ask import Budget, holds_json, read_all
from pipelines.review.cache import Answers
from pipelines.review.cascade_stage import cascade_stage
from pipelines.review.disagreements import write_disagreements
from pipelines.review.draw import draw, seeded_order
from pipelines.review.metrics import (
    METRICS_FILE,
    REPORTS,
    Metrics,
    label_measures,
    marked_techniques,
    pool,
    runs_agreement,
)
from pipelines.review.report import render
from pipelines.review.testset import ROUND, SPLIT, count_accounts, load_posts, reference_kappas

log = logging.getLogger("review.evaluate")

SEED = 20261115
CALL_BUDGET = 1_500
REPEATS = 200
# `ChatClient.complete` asks at temperature 0.
TEMPERATURE = 0.0
ANSWERS_FILE = DATA / "llm" / "review-eval.jsonl"
REFERENCE = (
    "The settled answers of the probe campaign (guides v2): each test post was read twice by "
    "Claude Haiku 5.5 annotators, and a third time where the two differed. It is an LLM "
    "annotation, not human gold."
)


def _commit() -> str:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout

    dirty = git("status", "--porcelain", "--", "backend/review", "pipelines/review").strip()
    return git("rev-parse", "--short", "HEAD").strip() + (" + uncommitted changes" if dirty else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="posts read per stage; nothing is reported")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    settings = get_settings()
    if not (settings.llm_api_key and settings.llm_model):
        raise SystemExit("LLM_API_KEY and LLM_MODEL must be set: the review needs its model.")
    guides = load_guides(settings.guides_dir)
    kappas = reference_kappas([label.key for label in guides.screened()])
    if not kappas:
        raise SystemExit(f"No technique guide in {settings.guides_dir}: nothing to screen for.")
    posts = {post.key: post for post in load_posts(list(kappas))}
    limit = args.limit if args.limit is not None else len(posts)
    answers = Answers(ANSWERS_FILE)
    stored = len(answers)
    client = ChatClient(settings.llm_api_base, settings.llm_api_key, settings.llm_model, 120.0)
    ask = partial(
        read_all, client, settings.llm_model, guides, answers, Budget(CALL_BUDGET - stored)
    )

    def screen_of(keys: list[str]) -> dict[str, ReviewRequest]:
        return {key: ReviewRequest(text=posts[key].text, probes=()) for key in keys}

    with runlog.timed() as elapsed:
        order = seeded_order(posts, SEED)[:limit]
        screen = ask(screen_of(order), 1)
        repeats = draw(order, min(REPEATS, limit), SEED + 1)
        again = ask(screen_of(repeats), 2)
        marked = marked_techniques({post: reading.review for post, reading in screen.items()})
        cascade = cascade_stage(posts, marked, ask, limit, SEED + 2)
    client.close()

    rejected = [
        (name, posts[post].answers.get(name))
        for post, reading in screen.items()
        for name in reading.rejected
    ]
    unread = [reading.raw for post, reading in screen.items() if post not in marked]
    labels = label_measures({post: posts[post].answers for post in marked}, marked, kappas)
    metrics = Metrics(
        model=settings.llm_model,
        prompt_version=PROMPT_VERSION,
        prompt_sha256=hashlib.sha256(system_prompt(guides).encode("utf-8")).hexdigest(),
        temperature=TEMPERATURE,
        reference=REFERENCE,
        split=SPLIT,
        round=ROUND,
        seed=SEED,
        commit=_commit(),
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        asked=len(order),
        accounts=count_accounts(order),
        posts_with_technique=sum(any(posts[key].answers.values()) for key in order),
        posts=len(marked),
        unanswered=len(order) - len(screen),
        failed=len(unread),
        failed_with_json_inside=sum(holds_json(raw) for raw in unread),
        rejected_quotes=len(rejected),
        rejected_quotes_on_yes=sum(answer is True for _, answer in rejected),
        rejected_quotes_on_no=sum(answer is False for _, answer in rejected),
        rejected_quotes_by_label=dict(Counter(name for name, _ in rejected)),
        labels=labels,
        pooled=pool(labels),
        cascade=cascade,
        runs_agreement=runs_agreement(
            marked,
            marked_techniques({post: reading.review for post, reading in again.items()}),
            list(kappas),
            asked=len(repeats),
        ),
        calls=len(answers),
    )
    write_disagreements(posts, screen, labels, SEED + 3)
    log.info("%d posts read, %d answers stored\n%s", len(marked), len(answers), render(metrics))
    if args.limit is not None:
        log.info("limited run: nothing written under %s", REPORTS)
        return
    if metrics.unanswered:
        # A changed prompt asks everything again and the budget stops it: a measure on the
        # few posts answered would replace the one on all of them.
        raise SystemExit(
            f"{metrics.unanswered} posts got no answer: nothing written under {REPORTS}."
        )
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / METRICS_FILE).write_text(metrics.model_dump_json(indent=1), encoding="utf-8")
    paid = len(answers) - stored
    if paid:
        # A run that only read the cache again is not a step worth a line of the log.
        note = f"{settings.llm_model}, {PROMPT_VERSION}, {paid} calls, {len(answers)} stored"
        runlog.record("review-evaluate", ROUND, len(marked), elapsed[0], note=note)
    log.info("wrote %s", REPORTS / METRICS_FILE)


if __name__ == "__main__":
    main()
