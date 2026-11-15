# The LLM review

State on 15 Nov 2026. A probe flags an item. The review reads it again with an LLM, with the annotation guide of each label and more context. This is where a technique gets named: loaded language, appeal to fear, whataboutism, an authority left unnamed. Every reading comes with the span of text that backs it.

Code: `backend/review/`. Model: `gemini-3.8-flash` through the Hostinger AI Router. Prompt versions: `review-v2` for one item, `selection-v1` for a selection.

## 1. When it runs

| Case | What starts it | Route |
| --- | --- | --- |
| A workspace item, in the background | A probe sends the item to the review, under the workspace setting `review_mode` | none: it runs when the item is placed |
| One point, on demand | Someone asks for it, on the demo or in a workspace | `POST {base}/map/review/{index}` |
| A selection of points | Someone asks for it: a lasso selection, a zone, the posts of a few actors | `POST {base}/review/selection` |

`{base}` is `/api` for the demo and `/api/v1` for a workspace.

The setting `review_mode` decides which flags send an item to the review:

| Value | A probe sends the item when |
| --- | --- |
| `off` | never |
| `probable` (default) | it reaches its `probable` level |
| `possible` | it reaches `possible` or `probable` |
| `score` | its score is at or above `review_min_score` |

Three kinds of probes, in the pack exported from run `v1`:

| Kind | Number | What it does |
| --- | --- | --- |
| Shown detector (a call, an attack, a technique, a solicitation, a claim) | 22 | Sends the item at its measured levels, as the mode says |
| Review-only detector | 14 | Never shown. 5 have measured levels and send at them. 9 have none and send from a review cut, in the modes `probable` and `possible` |
| Shown descriptor (a theme, a language, an emotion, a side) | 14 | Never sends an item: most posts carry such a flag |

The review cut of a probe is the deepest calibration edge where at least 20% of the flagged posts were real ones, on at least 20 posts read, and which flags at most 1% of the calibration posts. That 20% is a calibration estimate, not a test measure: the interface shows no reliability for it.

On demand, the point is reviewed with the probes that flag it at `possible` or above, whatever the setting.

## 2. What it reads

| Input | Bound |
| --- | --- |
| The text of the item | The first 4,000 characters |
| The probes that sent it | The 8 strongest. Each comes with the guide section of its label |
| Context: its nearest items by meaning | 8, each cut to 280 characters |
| Context: other items of the same actor | 5, each cut to 280 characters |

The context has one use: to resolve what the item refers to (who "they" are, what it answers). Nothing is quoted from it and it is never judged.

## 3. The method

The system prompt is a method in numbered steps, followed by the annotation guides of the probe campaign, word for word: the rules common to every label (`docs/probes/guides/common.md`, without the two sections about the annotators' answer format), the guides `rhetoric.md` and `fallacies.md` whole, and the condition of `calls.md` that says what a request to the readers is. A reading of the review then means what an annotation means.

1. Read the whole item.
2. Decide whose voice it is in: own, reported, ironic or unclear (rules 3 and 4 of the common rules).
3. For each probe, apply the guide section of its label: its YES conditions one by one, then its NO list. Answer `supported`, `not supported` or `unclear`, with an explanation of one or two sentences and the exact span.
4. Screen the item for the 16 techniques of the two technique guides, whether a probe flagged them or not. Report a technique only when every one of its YES conditions is met.
5. Say what the item asks its readers to do and whom it is aimed at, as spans of the item, or null.

The 16 techniques: loaded language, exaggeration, fear appeal, doubt, identity appeal, us vs them, slogan, bandwagon, authority appeal, unnamed authority, whataboutism, straw man, false dilemma, causal oversimplification, thought terminating cliche, Nazi comparison. A technique carries the same name as the probe of its label.

Without the guides folder, the review answers each probe from its description and screens for no technique.

## 4. Checks on the answer

The answer is one JSON object, parsed into typed models (`backend/review/schema.py`).

| Check | Consequence |
| --- | --- |
| A quote must be a span of the item, whitespace aside | A finding whose quote is not in the item becomes `unclear`. A technique whose quote is not in the item is removed |
| `asks` and `target` must be spans of the item | Dropped otherwise |
| A guide that asks for evidence | A `supported` reading without its span becomes `unclear` |
| A technique a flagged probe asked about | It follows the finding of that probe: the two never disagree |
| A finding for a probe nobody asked about, a technique outside the 16 | Dropped |
| An answer that is not the JSON asked for, or that answers none of the probes | The review is `failed`. Nothing is guessed |

## 5. The review of a selection

Two parts, kept apart in the answer.

- **Measured, no LLM.** The number of posts and actors, and for each shown probe how many posts of the selection it flags, that rate, the rate on the rest of the map and the ratio of the two.
- **Read by the LLM.** At most 24 posts: the nearest to the mean direction of the selection, 2 per actor at most, each cut to 280 characters and numbered. The model says what they share in one or two sentences, which techniques several posts show (same guides), what they ask their readers to do and whom they are aimed at. Each span is checked in the post it cites. A technique is kept when at least two posts show it.

The prompt states that people who agree are not a campaign. It describes what is shared, never why or by whom.

Without an LLM, or when the LLM fails, the measured part is answered alone.

## 6. Cache and limits

- **Cache.** A review is kept in `reviews.sqlite` under a hash of the model, the prompt version, the system prompt and the user prompt. The same question is never paid twice, in the background or on demand. Only a review that was read is kept: a failed one is asked again.
- **Demo.** 10 new reviews a minute per address. A cached review does not count.
- **Workspace.** 1,000 reviews a day.
- **Server.** 10,000 reviews a day, all workspaces and the demo together.
- Beyond a limit the route answers 429 with a sentence. Without an LLM configured, the item route answers 503.

## 7. What it never claims

- The intent of an author.
- That an actor is a bot, a troll or paid.
- An organisation or a campaign behind an item or a selection.
- That a statement is true or false.
- That a selection is coordinated. The one-voice check measures that (`reports/voices/`); the review only describes what the posts share.

## 8. How it is measured

The evaluation (`pipelines/review/`) compares the review with the annotated posts of the probe campaign, technique by technique, and writes `reports/review/metrics.json`. The report is `reports/review/2026-11-15-review-v2.md`. The reference is an LLM annotation (two readings, a third where they differ), not human gold: what is measured is how far the review agrees with it.

Measured on 15 Nov 2026 with `gemini-3.8-flash` and `review-v2`, on the 1,200 random posts of the test split (1,179 accounts), each read alone:

| What | Measured |
| --- | --- |
| The technique screen, the 12 measurable techniques together | Precision 78.0% (73.0 to 82.4), n=296. Recall 48.1% (43.7 to 52.6), n=480. False-positive rate 0.5% |
| `loaded_language` | Precision 79.1% (72.0 to 84.8), n=153. Recall 64.0% |
| `exaggeration` | Precision 85.5% (75.9 to 91.7), n=76. Recall 44.2% |
| A probe flags, then the review reads, on the random sample alone: `loaded_language` | Precision 75.7% after the probe, 97.2% (85.8 to 99.5), n=36, after the review, which keeps 85.4% of the true positives |
| The same on every test post read by score band (913 posts, each band counted for the test posts it holds): `loaded_language` | Precision 73.8% (67.0 to 79.3) after the probe, 93.2% (87.8 to 96.5) after the review, which keeps 87.3% (81.0 to 92.2) of the true positives; 265 posts read |
| By score band: `exaggeration`, `fear_appeal`, `us_vs_them` | After the probe 72.7%, 59.8%, 71.3%; after the review 93.1% (86.5 to 96.9), 92.7% (81.4 to 97.8), 98.4% (92.4 to 99.7) |
| By score band, highest scores only (probes without a level): `doubt`, `identity_appeal`, `slogan` | After the review 84.6% (58.3 to 96.7), 84.2% (63.6 to 95.3), 96.2% (82.8 to 99.6); under their highest scores too few posts were read to say anything narrow |
| The same 200 posts asked twice | Same list of techniques on 97.5% of the posts |
| Answers that could not be read | 4 of 1,200 |
| Quotes that were not in the post | 0 |

What the product shows beside a reading:

- A technique carries its own precision when the review marked it on at least 20 posts of the evaluation: today `loaded_language`, `exaggeration` and `doubt` (45.0%, 25.8 to 65.8, n=20).
- The other techniques carry no figure of their own. The review then shows the figure of the measurable techniques together (`overall`).
- Four techniques have counts and no rate, because two annotators agree too little on them (kappa under 0.5): `bandwagon`, `whataboutism`, `causal_oversimplification`, `thought_terminating_cliche`.
- A review made with another model or prompt version has `measured` false, and is shown as not measured.

Not measured:

- the review of a selection;
- the answers to the probes of the other families (calls, hostility, solicitation, claims);
- whether the context (nearest posts, posts of the same actor) changes an answer;
- results per language, and any text that is not a post of this corpus.

## 9. What was tried

A try, not an evaluation. On 14 and 15 Nov 2026, through the AI Router, with the real guides and the probe pack of run `v1`:

| Tried | Result |
| --- | --- |
| 5 hand-written posts (a deflection, an unnamed authority, a neutral post, a reported quote, a post in German), twice | 10 answers, all valid JSON. Second run: 18 spans given, 18 found in the item |
| 4 posts of the build served locally, through `POST /api/map/review/{index}` | All `done`. Asked again: answered from the cache |
| 2 selections of 60 posts, through `POST /api/review/selection` | Both `done`, 24 posts read each. One shares no technique; the other shows 3, each in 3 or 4 posts |
| Size of an item review | 6,868 to 7,661 tokens in, 31 to 492 out, 1.9 to 6.9 seconds |

The first wording of the prompt gave valid answers and exact spans, so it was kept. Two runs of the same post did not always give the same answer at temperature 0: the cache is what makes an answer stable.
