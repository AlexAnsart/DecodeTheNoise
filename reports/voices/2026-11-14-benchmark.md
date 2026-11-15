# One voice or several: evaluation 2026-11-14

## What is decided

- **Unit:** a group of actors with several posts each, read from a selection on the map.
- **Positive means:** the actors are interchangeable: any post could have come from any of them.
- **Detector:** gap between posts of one actor and posts of different actors, in standard deviations of 999 shuffles of who wrote what, averaged over 20 draws. Rule: flag under the value 5% of the most alike real groups fall under, on the calibration half of the real pools. Embedding: `embeddinggemma:300m-qat-q8_0@e84a7acc2394|prefix='task: classification | query: '|dims=256`.
- **Commit:** f23416b

## Data

| Split | Source | Groups |
| --- | --- | --- |
| Calibration | Real pools of the 2026 sample of X posts (one word, one month), the half a hash of the pool name selects | see each size |
| Test, negatives | The other half of the real pools: actors drawn at random, and the most alike actors | see each size |
| Test, positives | Synthetic groups written by Claude Haiku from one brief, three ways of running the actors | see each size |
| Off-distribution | Internet Research Agency tweets, 2015 to 2017 | see each size |

Split rule: by pool, never by post. How the groups were made: `docs/brief-recovery/benchmark.md`.

## Results on test

### 6 actors of 6 posts

Threshold: score under 3.09, set on 94 real pools. Negatives below are the hardest real groups (the most alike actors of each held-out pool).

| | Flagged | Not flagged |
| --- | --- | --- |
| Written from one brief | TP = 50 | FN = 3 |
| Real, most alike actors | FP = 1 | TN = 72 |

| Measure | Value | 95% interval | n |
| --- | --- | --- | --- |
| Recall | 94% | 85% to 98% | 53 |
| False-positive rate, most alike real actors | 1% | 0% to 7% | 73 |
| False-positive rate, real actors drawn at random | 0% | 0% to 5% | 73 |
| Precision on this test mix | 98% | | 51 |
| F1 on this test mix | 0.96 | | |

By way of running the actors:

| Mode | Flagged |
| --- | --- |
| `shared`: one context wrote all the posts, dealt to the actors | 21 of 21 (84% to 100%) |
| `solo`: one context per actor, the same brief | 18 of 18 (82% to 100%) |
| `persona`: one context per actor, plus an age, a place and a writing habit each | 11 of 14 (52% to 92%) |

A real operation (Internet Research Agency, groups of one team in one zone and month):

| Team | Flagged |
| --- | --- |
| NewsFeed | 9 of 69 (7% to 23%) |
| RightTroll | 9 of 17 (31% to 74%) |

Precision when coordinated groups are rare (measured rates; worst case of both intervals in brackets):

| Share of groups that are coordinated | 1% | 5% | 20% |
| --- | --- | --- | --- |
| Precision | 40% (10%) | 78% (38%) | 94% (74%) |

### 4 actors of 4 posts

Threshold: score under 1.67, set on 98 real pools. Negatives below are the hardest real groups (the most alike actors of each held-out pool).

| | Flagged | Not flagged |
| --- | --- | --- |
| Written from one brief | TP = 60 | FN = 5 |
| Real, most alike actors | FP = 2 | TN = 81 |

| Measure | Value | 95% interval | n |
| --- | --- | --- | --- |
| Recall | 92% | 83% to 97% | 65 |
| False-positive rate, most alike real actors | 2% | 1% to 8% | 83 |
| False-positive rate, real actors drawn at random | 0% | 0% to 4% | 83 |
| Precision on this test mix | 97% | | 62 |
| F1 on this test mix | 0.94 | | |

By way of running the actors:

| Mode | Flagged |
| --- | --- |
| `shared`: one context wrote all the posts, dealt to the actors | 21 of 21 (84% to 100%) |
| `solo`: one context per actor, the same brief | 23 of 23 (86% to 100%) |
| `persona`: one context per actor, plus an age, a place and a writing habit each | 16 of 21 (55% to 89%) |

A real operation (Internet Research Agency, groups of one team in one zone and month):

| Team | Flagged |
| --- | --- |
| NewsFeed | 10 of 69 (8% to 25%) |
| RightTroll | 9 of 17 (31% to 74%) |

Precision when coordinated groups are rare (measured rates; worst case of both intervals in brackets):

| Share of groups that are coordinated | 1% | 5% | 20% |
| --- | --- | --- | --- |
| Precision | 28% (9%) | 67% (34%) | 91% (71%) |

## Baseline

A near-duplicate rule (two actors posted texts sharing 50% of their character 5-grams) on the same groups:

| Detector | Groups from one brief flagged | Real groups flagged |
| --- | --- | --- |
| Near-duplicate rule | 1 of 67 (0% to 8%) | 13 of 88 (9% to 24%) |
| This check, 6 x 6 | 50 of 53 (85% to 98%) | 0 of 73 (0% to 5%) |

## False-positive audit

Real groups flagged on the held-out half, at any measured size:

| Pool | What it is | What the product does |
| --- | --- | --- |
| fremantle-2026-04 | News coverage of one event. Sports outlets and club accounts report the same matches of one football club: independent newsrooms, the same facts. Flagged at 4 x 4 only | Says that news feeds read the same, and shows the closest posts so the reader sees headlines. This is the false alarm to expect on event-tight groups |
| unneeded-2026-04 | Declared campaign. Police departments and agencies relay one kit for a national drug take-back day: the same announcements, lightly reworded. One voice indeed, and an open one | Keeps the level at `possible` and says that a campaign kit reads the same. Whether a coordination is announced is not measured yet |

## On real posts, outside the benchmark

### Build `tweets-2026-100k` (100,000 posts)

The check was run on every selection one gesture makes on the map: word: every post, reposts left out, that holds one word of 4 letters or more; word in a month: the same, within one calendar month; zone in a month: every post of one zone of the map within one calendar month; kept: selections of 16 to 5000 posts that the check can read: at least 4 actors with 4 posts each.

13,407 selections tried, 2,864 read, **19 flagged** (11 campaign, 8 false alarm).

| Kind of selection | Read | Flagged |
| --- | --- | --- |
| word | 1,876 | 6 |
| word in a month | 836 | 12 |
| zone in a month | 152 | 1 |

Every flagged selection, read by hand:

| Selection | Posts | Read at | Score | Limit | What it is |
| --- | --- | --- | --- | --- | --- |
| jensspahn, 2026-03 | 36 | 4x4 | 0.14 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| verfahren, 2026-03 | 43 | 4x4 | 0.15 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| täglich, 2026-03 | 48 | 4x4 | 0.24 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| ermittlungen, 2026-03 | 42 | 4x4 | 0.31 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| eingestellt, 2026-03 | 40 | 4x4 | 0.31 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| werde, 2026-03 | 60 | 4x4 | 0.33 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| aufnahme, 2026-03 | 35 | 4x4 | 0.34 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| strafrechtlich, 2026-03 | 38 | 4x4 | 0.41 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| spahnrücktritt, 2026-03 | 34 | 4x4 | 0.46 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| poste, 2026-03 | 38 | 4x4 | 0.47 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| fordern, 2026-03 | 45 | 4x4 | 0.59 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| befürchte | 149 | 6x6 | 2.16 | 3.09 | false alarm. A common word or phrase used in unrelated posts by unrelated actors: no shared subject. |
| knoblauch, 2026-03 | 68 | 4x4 | 0.75 | 1.67 | false alarm. Independent people and outlets reacting to one event or one show. |
| literarisch | 78 | 4x4 | 0.83 | 1.67 | false alarm. A common word or phrase used in unrelated posts by unrelated actors: no shared subject. |
| dschungel | 94 | 4x4 | 0.88 | 1.67 | false alarm. Independent people and outlets reacting to one event or one show. |
| passiert | 226 | 4x4 | 1.12 | 1.67 | false alarm. A common word or phrase used in unrelated posts by unrelated actors: no shared subject. |
| kater | 136 | 4x4 | 1.22 | 1.67 | false alarm. A common word or phrase used in unrelated posts by unrelated actors: no shared subject. |
| zone 13, 2026-01 | 360 | 4x4 | 1.28 | 1.67 | false alarm. A broad zone of general commentary in one month: no shared subject. |
| komplett | 247 | 4x4 | 1.59 | 1.67 | false alarm. A common word or phrase used in unrelated posts by unrelated actors: no shared subject. |

Nothing is labelled: this is how often the check fires on real posts, an upper bound on its false alarms there, not a measure of coordination.

### Build `tweets-2026-500k` (500,000 posts)

The check was run on every selection one gesture makes on the map: word: every post, reposts left out, that holds one word of 4 letters or more; word in a month: the same, within one calendar month; zone in a month: every post of one zone of the map within one calendar month; kept: selections of 16 to 5000 posts that the check can read: at least 4 actors with 4 posts each.

61,192 selections tried, 15,427 read, **13 flagged** (9 campaign, 4 false alarm).

| Kind of selection | Read | Flagged |
| --- | --- | --- |
| word | 8,302 | 1 |
| word in a month | 6,808 | 12 |
| zone in a month | 317 | 0 |

Every flagged selection, read by hand:

| Selection | Posts | Read at | Score | Limit | What it is |
| --- | --- | --- | --- | --- | --- |
| jensspahn, 2026-03 | 43 | 4x4 | 0.14 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| verfahren, 2026-03 | 71 | 4x4 | 0.15 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| täglich, 2026-03 | 104 | 4x4 | 0.24 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| eingestellt, 2026-03 | 54 | 4x4 | 0.31 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| ermittlungen, 2026-03 | 57 | 4x4 | 0.31 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| aufnahme, 2026-03 | 45 | 4x4 | 0.34 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| spahnrücktritt, 2026-03 | 34 | 4x4 | 0.46 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| poste, 2026-03 | 47 | 4x4 | 0.47 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| fordern, 2026-03 | 80 | 4x4 | 0.59 | 1.67 | campaign. Five actors repost the same dated demand every day. The word belongs to its template, and the four actors with enough posts are the same in every such selection. |
| literarisch, 2026-01 | 115 | 4x4 | 0.73 | 1.67 | false alarm. A common word or phrase used in unrelated posts by unrelated actors: no shared subject. |
| befürchte | 517 | 6x6 | 2.16 | 3.09 | false alarm. A common word or phrase used in unrelated posts by unrelated actors: no shared subject. |
| russische, 2026-05 | 123 | 4x4 | 1.36 | 1.67 | false alarm. One broad subject, written about by actors with opposite views. |
| kris, 2026-05 | 113 | 4x4 | 1.64 | 1.67 | false alarm. Independent people and outlets reacting to one event or one show. |

Nothing is labelled: this is how often the check fires on real posts, an upper bound on its false alarms there, not a measure of coordination.

## Abstention

The check answers `not enough evidence` when the selection holds fewer than 4 actors with 4 posts each, reposts left out. Most selections of a sparse corpus abstain.

## Off-distribution

The Internet Research Agency rows above: other years, posts of 140 characters, groups cut by map zone. A second writer model for the synthetic groups: untested.

## Limits

- The real groups are actors who posted on one word in one month: looser than many people reacting to one event in one hour. Not tested on such groups.
- The groups written from one brief are synthetic: one writer model, fictional subjects.
- An operator who gives each actor its own subject passes the check.
- A fan campaign, a news feed or a posting tool is one voice too: the check says that actors are interchangeable, not why.
- Measured on English posts and on one embedding model.
- The real actors are not labelled: some may be scripted, so false alarms are an upper bound.
