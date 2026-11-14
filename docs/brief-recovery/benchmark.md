# The benchmark

The data behind the three tests: real groups of actors, and synthetic groups written from briefs we know. An actor is one account. Built on 14 Nov 2026. Everything is under `data/datasets/brief-bench/`, which is not in git.

## 1. Why build one

No real corpus comes with the prompt that produced it, so the positives have to be made. The negatives do not: they are real actors.

| Side | What | Role |
| --- | --- | --- |
| Real | Pools of actors of the 2026 sample of X posts | Negatives of test 2. The subjects of the synthetic briefs are modelled on them |
| Real | Actors of the Internet Research Agency (build `ira-120k`) | People who carried out a brief, before language models |
| Synthetic | Posts written from briefs with known fields | Positives of all three tests |

## 2. Real pools

A pool is the posts found for **one search term in one month**, by the actors who posted on it several times.

| Rule | Value |
| --- | --- |
| Source | The 5 downloaded shards of `tweets-sample-2026`, 4,542,666 rows |
| A post counts when | It is not a repost, is English by a cheap screen, and has at least 60 characters without links |
| An actor counts when | They have at least 6 such posts in the pool |
| A pool counts when | It has at least 8 such actors, and they post 30 times or fewer on average |
| Left out | Actors whose posts mostly open with the same 40 characters: they post a template |
| Kept per pool | Up to 12 actors, up to 12 posts each, drawn with a fixed seed |

Result: 187 pools qualify, one month per search term. The 60 largest are in `pools.jsonl` (6,169 posts), the other 127 in `pools-extra.jsonl` (9,179 posts). Once template actors are left out, 167 pools keep at least 6 actors. Actor names are hashed.

The 60 largest pools give the subjects of the synthetic briefs. The other 127 are only read as real groups: no synthetic post is written on them.

These actors are not labelled. Some may be scripted, so a false-positive rate measured on them is an upper bound.

## 3. Subjects

Each of the 60 pools was read by an LLM (`gemini-3.8-flash`, temperature 0, cached), which returned a subject, one opinion for, one opinion against, and two flags: coherent, sensitive.

| Step | Pools left |
| --- | --- |
| Read | 60 |
| Coherent and not sensitive, by the model | 43 |
| After a screen by hand: no real party, leader or creed, no health subject, no named financial product, no duplicate subject | 24 |

**Every subject was then made fictional.** A second call keeps the kind of debate and replaces proper names only: a real rugby coach becomes "Lachlan Fairbairn, head coach of the Quillon rugby team". Section 5 says why.

## 4. Briefs

A brief is a subject plus four closed fields. Closed lists make a recovered field scorable by exact match.

| Field | Values |
| --- | --- |
| `stance` | `for`, `against`: approves of the thing the subject names, or criticises it |
| `persona` | `parent`, `veteran`, `owner` (small business), `student`, `news` (local news outlet) |
| `tone` | `angry`, `sarcastic`, `factual`, `worried` |
| `format` | `short` (one sentence under 100 characters), `long` (two or three sentences), `tagged` (hashtags and one emoji) |

One template turns the fields into the instruction an operator would give a model (`pipelines/briefs/fields.py`). That instruction is the hidden prompt of the tests.

| Set | Briefs | Use |
| --- | --- | --- |
| Bench | 10 per topic on 16 topics. Each field is balanced inside a topic and shuffled on its own, so no field can be guessed from the topic or from another field. Topics are split: 10 for development, 6 held out (5 after one topic was dropped, §5) | Tests 1 and 3 |
| Twin | 1 per topic on 24 topics (23 after the drop), written three times (below) | Test 2 |

A twin brief is run in three ways, one per way an operator can run six actors:

| Mode | How the posts are written | What it stands for |
| --- | --- | --- |
| `shared` | One context writes 48 posts; they are dealt to 6 actors at random | "Write 48 posts", then spread them |
| `solo` | 6 contexts, one per actor, the same brief, 8 posts each | One session per actor |
| `persona` | As `solo`, plus one line per actor: an age, a place, a writing habit | An operator who wants the actors to look different |

## 5. Writers

Every synthetic post was written by a Claude Haiku 5.5 subagent in Claude Code. **One writing task is one context**: a writer sees one instruction and never another task. The writer's context also holds the Claude Code system prompt and this project's agent instructions, which a raw API call would not.

**Writers declined, and the benchmark changed because of it.**

| Run | Tasks | Declined | What followed |
| --- | --- | --- | --- |
| Pilot, real names | 16 | 5 | Their reason was sound: natural-sounding posts about a real, named person are ready-to-use astroturf. All subjects were made fictional and the pilot was discarded |
| Main run, fictional subjects | 472 | 62 (13%) | One topic (`t02`) had kept a real policy debate under an invented agency name: dropped, its 11 written tasks deleted |
| Second ask | 50 | 39 | The other 50 declined tasks were asked once more, in a new context, with the reason natural posts are needed and the stated right to decline. The 39 that declined again stay empty |

So refusals are respected, not routed around. The cost is that the missing tasks are not random. Of the tasks of the `news` persona, 14% were never written, against 4% for `student`. Subjects about a named coach, about policing, or about politicians lost the most. Tasks with a per-actor persona were declined more often than the same tasks without one (10% against 4%).

## 6. What the benchmark holds

| | Count |
| --- | --- |
| Writing tasks with posts | 410 of 472 |
| Synthetic posts | 7,286 |
| Bench briefs, 32 posts each | 132: 85 on 10 development topics, 47 on 5 held-out topics |
| Twin groups | `shared` 21, `solo` 23 (18 with all 6 actors), `persona` 23 (14 with all 6 actors) |
| Posts written on the second ask | 208, flagged `second_ask` |

**The synthetic posts are not copies of each other.** Inside a brief, the mean lexical overlap of two posts is 0.05 (Jaccard on character 5-grams) and no pair exceeds 0.5. Real pools have more near-copies: 1.5% of pairs exceed 0.5. A near-duplicate detector sees nothing in these groups.

## 7. Limits

- **One writer model, one way of calling it.** Test 3 adds posts by a second model on the held-out briefs; they are the only check on another writer.
- **Fictional subjects.** A synthetic group and its real pool share a kind of subject, not its vocabulary.
- **Briefs we wrote.** A real operator writes other prompts, edits the output, and mixes written and generated posts.
- **English only**, and one platform.

## 8. Rebuild

```
uv run --group pipelines python -m pipelines.briefs.pools      # real pools (two passes over the shards)
uv run --group pipelines python -m pipelines.briefs.topics     # subjects, through the AI Router
uv run --group pipelines python -m pipelines.briefs.design     # briefs and writing tasks
# writers: one Claude Haiku subagent per file of tasks/, each writing one file of written/
uv run --group pipelines python -m pipelines.briefs.collect    # posts.jsonl and the manifest line
```
