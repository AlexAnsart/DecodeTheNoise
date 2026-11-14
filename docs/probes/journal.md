# Probe campaign: journal

What was run, in order, with what it gave and what was decided from it. Times are UTC. The method and the results are written up in [`report.md`](report.md); this file is the trail behind it.

## 14 Nov 2026

### 19:55. Scope

- Decided with the project owner: annotate the whole taxonomy ([`taxonomy.md`](taxonomy.md)), with Haiku annotators run as independent agents; train linear probes; iterate on the guides and the data from measured results.
- Not validated: a single merged `feed_text` class ("too specific"). The three format labels of family 5 stay as separate labels, as in the validated tables; no merged class is built.

### 20:00. State of the data

| Fact | Value |
| --- | --- |
| Shards with corpus and vectors on the laptop | 00, 54, 72 |
| Posts | 2,392,413 |
| Vectors | EmbeddingGemma `300m-qat-q8_0`, prefix `task: classification \| query: `, 256 dimensions, float16 |
| Shards 18 and 36 | Not on the laptop yet: not used |

### 20:10. Pool and split (`pipelines/probes/pool.py`)

- Split by actor: `sha1("probes-split-v1|" + actor_id)`, 60% train, 20% calibration, 20% test. The same actor is on one side in every shard.
- A text is normalised (lower case; links, mentions and numbers masked) and kept once per split. A text found in several splits is kept in one of them, picked by its own hash.
- Posts over 1,500 characters are left out of the labelled samples.

| | Posts |
| --- | --- |
| Read | 2,392,413 |
| Distinct normalised texts | 2,322,691 |
| Texts found in several splits (kept in one) | 7,436 |
| Over 1,500 characters (left out) | 68,212 |
| Kept: train | 1,355,504 |
| Kept: calibration | 449,592 |
| Kept: test | 452,310 |

Consequence to state in the report: every rate is measured over distinct texts of 1,500 characters at most.

### 20:10. Guides v1 and pilot round `p1`

- Ten guide files written ([`guides/`](guides/)): common rules, then one guide per annotation pass. Rhetorical techniques are split in two passes (`rhetoric`, `fallacies`) to keep each guide short: nine passes for 63 labels.
- `authority_appeal` "named or not" became a second yes/no label, `unnamed_authority`: every label stays a closed question.
- Round `p1`: 240 posts drawn at random from the **train** split only (seed 1). Guides are developed on train posts; calibration and test posts are never read while a guide can still change.
- Batches: 40 posts, shuffled on a seed of their own for each pass and each reading, so two readings of a post share neither its neighbours nor its position.

### 20:11. How annotators are run

A workflow starts one fresh Claude Haiku 5.5 agent per batch. The agent reads three files (the common rules, its family guide, its batch) and returns its answers through a typed output: one value per label and per post, plus the quoted evidence. It has no other input.

Smoke test, one batch of 40 posts, three settings:

| Setting | Project instructions in context | `calls` batch | `subject` batch |
| --- | --- | --- | --- |
| Read-only agent, low effort | No | 33 s | 56 s |
| Read-only agent, medium effort | No | 34 s | 85 s |
| Default agent, medium effort | Yes | 30 s | 59 s |

- The three settings gave identical answers on `calls` (no yes at all in that batch). On `subject` they differed on `theme` for 1 to 5 posts of 40 and on one or two other answers.
- Kept: the read-only agent at low effort. It does not receive the project's instruction files, so an annotator does not know what the labels are for; it cannot write anything; it is the fastest. A sample of 40 posts cannot tell low from medium effort apart: untested beyond that.
- Checked in the transcripts: every agent ran on `claude-haiku-5-5`, with three file reads and one typed answer.

### 20:13. Pilot `p1`: 240 train posts, two readings, guides v1

108 agents (9 passes, 6 batches, 2 readings), all returned complete batches in 8 min 10 s.

Agreement between the two readings, labels with at least 3 yes in one reading (kappa on posts where both readings decided):

| Label | Yes (reading a / b) | Kappa |
| --- | --- | --- |
| `political` | 73 / 69 | 0.94 |
| `political_side` | three values | 0.92 |
| `attack_identity_group` | 6 / 7 | 0.92 |
| `profanity` | 5 / 6 | 0.91 |
| `fear` | 5 / 4 | 0.89 |
| `checkable_claim` | 83 / 88 | 0.88 |
| `news_headline` | 15 / 12 | 0.88 |
| `theme` | fourteen values | 0.86 |
| `slogan` | 4 / 3 | 0.86 |
| `enthusiasm` | 23 / 22 | 0.83 |
| `attack_political_group` | 9 / 8 | 0.82 |
| `attack_addressee` | 5 / 5 | 0.80 |
| `contempt` | 47 / 48 | 0.80 |
| `conspiracy_narrative` | 6 / 4 | 0.80 |
| `endorsement` | 8 / 7 | 0.79 |
| `loaded_language` | 37 / 37 | 0.78 |
| `anger` | 28 / 32 | 0.77 |
| `reported_speech` | 18 / 15 | 0.77 |
| `exaggeration` | 33 / 35 | 0.73 |
| `unsourced_statistic` | 11 / 8 | 0.73 |
| `doubt` | 13 / 13 | 0.67 |
| `dehumanisation` | 5 / 4 | 0.66 |
| `us_vs_them` | 6 / 7 | 0.60 |
| `attack_person` | 3 / 4 | 0.57 |
| `fear_appeal` | 5 / 5 | 0.39 |
| `irony` | 3 / 2 | 0.39 |
| `lang` | fifteen values | 1.00 |

What the pilot cannot say: 35 labels had fewer than 3 yes in 240 random posts (every call, most of solicitation, threats, most fallacies). Their agreement can only be measured on enriched posts, later.

Read by hand: every disagreement of the weaker labels. Systematic causes found, and the correction made in guides v2:

| Cause | Correction (v2) |
| --- | --- |
| `unclear` used as a softer `no` (up to 2.7% of answers on `checkable_claim`, `political`, `doubt`) | Common rule: when a condition needs something named or shown and the post does not show it, the answer is `no` |
| Some agents answered `yes` on `profanity` with no quote (2.3% of answers thrown away) | Common rule: a `yes` without its span is thrown away; offensive words are copied exactly |
| `fear_appeal`: harm already happening read as a warning | The harm must be to come: a future, a condition, or a question that puts the reader in the victim's place |
| `attack_person`: character judgements and "his dementia" read either way; unidentified person answered `unclear` | Demeaning content now lists character judgements and illness used as a put-down; the test "who the target is, or what it did"; unidentified means `no` |
| `dehumanisation`: set phrases ("lapdog", "bird-brained") read either way | The post must say what kind of being the target is; set phrases about one trait are `no` |
| `doubt`: no shared test of what an insinuation is | A closed list of forms; none present means `no` |
| `us_vs_them`: "I" against "they" read either way | The first camp must be a collective |
| `identity_appeal`: a list of national achievements read as an appeal | Pride that argues for nothing is `no` |
| `exaggeration`: casual absolutes read either way | Judge the wording literally; longer list of absolute terms |
| `unsourced_statistic`: thresholds and figures of speech read as statistics | The number must be asserted as a measurement or a count |
| `endorsement`: "public person" needs outside knowledge | A named person counts unless the post shows a private tie |
| `call_amplify`: a campaign hashtag read as a request to share | A campaign hashtag alone is not a request |

### 20:25. Guides frozen at v2; main round `m1`

- No second pilot: the agreement of v2 is measured at scale on the calibration and test posts of `m1`, which are read twice.
- From here on, a guide may only change from disagreements seen on **train** posts, and a change means reading every post again. Calibration and test disagreements are never read to tune a guide.
- `m1`: 3,600 posts drawn at random (seed 2): 1,600 train, 800 calibration, 1,200 test.
- Readings: every post once (reading a); calibration and test posts a second time (reading b), then a third time where the two differ. The `fallacies` pass runs on calibration and test only: its labels are kept to test an LLM later, not to train probes.
- 1,220 agents in two workflows run side by side (770 and 450).

### 20:35. Enrichment round `e1`, by seeds (train split only)

- Why: on random posts most labels are too rare to train on. The pilot found fewer than 3 yes in 240 posts for 35 labels.
- How (`pipelines/probes/enrich.py`): 500,000 train posts are searched. For each of 34 rare labels, a post is scored by its cosine to the closest YES example of the label's guide, embedded with the same model and prefix as the corpus. 70 posts are drawn at random among the 300 highest scores, and 30 among ranks 300 to 3,000 (near misses).
- 3,400 posts, one round per family (`e1_calls`, `e1_hostility`, ...), each read by its own family's pass only, twice.
- What this does to the numbers: train is now biased toward each label on purpose. Nothing measured on these posts is a rate of the corpus. Calibration and test stay random or sampled by score band with known weights.
- The guide examples are in English, so the posts found are mostly English: the rare labels will be learnt mostly from English. To measure per language.

### 20:59. Main round `m1` read; agreement under the frozen guides

- 1,244 batches taken, none incomplete. Five workflows ran side by side; the whole fleet returned about 56 batches a minute, whatever the number of workflows. No agent failed.
- Agreement on the 2,000 calibration and test posts read twice (full table in the report): kappa is 0.8 or more for 38 labels, between 0.6 and 0.8 for 15, under 0.6 for 9.
- Effect of the guide corrections, measured on posts the pilot never saw: `fear_appeal` 0.39 to 0.72, `attack_person` 0.57 to 0.85, `dehumanisation` 0.66 to 0.85, `identity_appeal` 0.00 to 0.71, `us_vs_them` 0.60 to 0.76, `irony` 0.39 to 0.64. `doubt` did not move (0.67 to 0.61). `unclear` answers fell to under 1% on every label; answers thrown away for a missing quote fell to 0.2% at most.
- Under 0.6: `whataboutism` (0.22), `thought_terminating_cliche` (0.28), `bandwagon` (0.36), `causal_oversimplification` (0.40), and five labels with 6 yes or fewer per reading (`call_pressure`, `gain_promise`, `engagement_bait`, `templated_post`, `doxxing`), where a kappa says little. The first four are fallacies kept for testing an LLM later: as annotated today they are not a usable reference.
- Position in the batch: the share of yes rises from 3.37% over the first ten posts of a batch to 3.72% over the last ten (slope +0.014 points per position, standard error 0.003, 321,316 answers). Annotators grow slightly more willing to say yes along a batch. Positions are shuffled and differ between readings, so this adds noise, not a bias tied to content. Not corrected in this campaign.

### 20:59. What the first enrichment found; search probes `s1`

- Agreement on the enriched posts is high: kappa 0.80 to 1.00 on every call, 0.91 on `threat`, 0.86 to 1.00 on solicitation labels. The rare labels can be annotated consistently when positives exist.
- Yield of the seed search was low for calls: 3 to 17 positives per label among 800 posts. Two guide examples are too thin a seed.
- `s1`: search probes fitted on the train posts of `m1` and `e1`, down to 5 positives. They are used to find posts, never measured and never shown.

### 21:00. Enrichment rounds `e2` and `e3` (train split only)

For the 32 labels with fewer than 80 train positives, two more searches over two different draws of 500,000 train posts:

- `e2`: by the search probe of the label (70 posts among the 300 highest scores, 30 among ranks 300 to 3,000);
- `e3`: by cosine to the closest known positive or guide example.

6,400 posts, read twice. The third readings of `m1` run at the same time (1,513 posts where two readings differ on at least one label of a pass).

### 21:48. Enrichment after three searches; a fourth, targeted round `e4`

- `m1` is settled: every post where two readings differed was read a third time (1,513 posts over the nine passes).
- Lesson on throughput: batches of enriched posts take about two minutes each, three times a random batch, because they hold many yes answers and their quotes. With two workflows the fleet fell to 12 batches a minute; work is now always split over five workflows or more.
- Train positives per label after `e1`, `e2` and `e3` (13,400 posts in all): every call except three now has 47 or more (`call_boycott` 82, `call_violence` 51, `call_amplify` 48, `call_pressure` 47, `call_vote` 47); `threat` 51, `violence_endorsement` 61, `engagement_bait` 33, `anti_pluralism` 43.
- Still too few to fit a probe: `call_protest` 18, `call_join` 19, `call_overthrow` 4. `doxxing` has none.
- `e4`: search probes `s2` (fitted down to 4 positives) look for the 13 labels still under 60 train positives. 1,300 posts, read twice.

### 22:06. Run `v1`: the probes that are measured

- Train set: the 1,600 random train posts of `m1` and the enriched posts of `e1` to `e4`: 12,700 train posts, each read by the pass of the label it was drawn for (enriched posts) or by all eight probe passes (random posts).
- 71 targets fitted of 92. Not fitted, under 25 train positives: `call_overthrow` (7 found after four searches), `doxxing` (none), ten languages with fewer than 20 posts each. The nine fallacy labels are not trained by design.
- Out-of-fold average precision on train (enriched, so not comparable between labels nor with test): from 1.00 (`lang:en`, `lang:de`) and 0.96 (`political`, `urgency_framing`) down to 0.11 (`irony`) and 0.04 (`hearsay`).
- Train positives after `e4`: `call_protest` 30, `call_join` 36, `call_amplify` 86, `call_vote` 86, `call_boycott` 85, `call_pressure` 82, `call_violence` 78, `threat` 76.

### 22:08. Calibration read by score band, round `c1`

- 42 labels: every fitted yes/no probe or descriptor with fewer than 150 positives in the random calibration sample (800 posts). The others (`political`, `checkable_claim`, `contempt`) and the targets derived from `lang`, `theme` and `political_side` are calibrated on the random sample alone.
- For each label the 449,592 calibration posts are ranked by its score and cut at ranks 100, 300, 1,000, 3,000, 10,000 and 30,000; 25 posts are drawn uniformly in each of the six bands.
- A post may be drawn for two labels of one family: each draw stays uniform in its band, the post is read once.
- 6,249 posts, read twice, in five workflows.

### 22:30. Thresholds of `v1`; what the diagnostics say

- Calibration `c1` is settled (third readings done). Thresholds are placed for 29 of the 42 labels read by band, and for `political`, `checkable_claim`, `contempt` and ten targets derived from `lang`, `theme` and `political_side`.
- No level for 13 labels read by band. In the 100 highest-scored calibration posts (0.02% of the split) the measured precision is 35% to 68%: `call_pressure` 35%, `threat` 38%, `violence_endorsement` 40%, `call_violence` 45%, `call_protest` 48%, `call_join` 50%, `anti_pluralism` 52%, `engagement_bait` 56%, `testimonial` 58%, `call_amplify` 61%, `slogan` 62%, `money_request` 67%, `adult_promo` 68%, `fear_appeal` 68%. For labels this rare (0.05% to 0.3% of posts) that is a ranking hundreds of times above chance, but under the 65% a level needs, or over it with too few posts read to be sure.
- Diagnostics on train, out of fold (`diagnostics.json`):
  - The linear probe matches or beats the MLP and k-NN on every target: the signal is linear, a heavier reader of the same vector buys nothing.
  - Cosine to the mean positive is far behind everywhere (for example 0.28 against 0.57 on `call_amplify`): similarity to examples is not a detector.
  - 256 dimensions beat 128, which beat 64, on nearly every target, sometimes by a wide margin (`call_vote` 0.49, 0.54, 0.67): the curve is still rising at the served size. The full 768 dimensions are untested.
  - Learning curves still rise for the rare labels (`call_join` 0.20, 0.31, 0.33 at 25%, 50%, 100% of train; `violence_endorsement` 0.15, 0.23, 0.30) and are flat for `doubt` (0.20, 0.22, 0.22) and `anti_pluralism`: more posts would help the former, not the latter.
- Decided here, from calibration, before any test post is read:
  1. Eight labels within reach of the bar get more calibration reads where their level is decided: 50 more posts in each of the two top bands (round `c2`). The rule that places a level does not change.
  2. Test is read now for the 29 labels whose thresholds are frozen (round `t1`); the labels that gain a level from `c2` follow in a second draw.
  3. Labels that still have no level are reported with their ranking on the random test sample and stay `review-only` or `dropped`. Mining more hard negatives for them and fitting a second run is the next iteration, not done here.

### 22:33. Test read by band, round `t1`

- For each of the 29 labels: 100 posts drawn in the `probable` band, 100 in the band between the two thresholds, 60 just under the lower threshold (a band three times the size of what is flagged). A label with one level gets 100 and 60.
- 6,050 posts, read twice, in five workflows; the 800 extra calibration posts of `c2` run beside them.

### 22:40. Extra calibration reads `c2`; four labels gain a level

- 800 more calibration posts read in the two top bands of eight labels near the bar. After the recalibration only those labels moved, checked against the thresholds saved before: `call_amplify`, `fear_appeal`, `money_request` and `adult_promo` gained a `possible` level; `slogan`, `testimonial`, `engagement_bait` and `identity_appeal` did not.
- Their test posts were drawn in a second round, `t2`.

### 23:00. First reading of test, and three rules it led to

The first evaluation ran with every test reading settled. Three things were wrong with what it would have shown, each fixed by a rule and not by moving a threshold:

1. **A level under the bar was still listed.** `conspiracy_narrative` had a `possible` level at 44% precision beside a `probable` level at 88%. Rule: a level is kept when its test precision is at least 60% on at least 30 posts read (the bar already written in `evaluate.py` for a probe); a level under it is withdrawn when the probe has another that passes.
2. **Probes with no level had no test number at all.** Five call probes came out as dropped only because the random test sample holds fewer than five of their positives. Round `t3`: 50 posts read among the 100 highest-scored test posts of each of 12 probes without a level. Rule: such a probe is review-only when the 95% interval of its precision there starts at 25% or more.
3. **The language probes had a poor operating point.** The general rule (deepest edge with 85% precision) put `lang:en` at 87% precision when the probe separates languages almost perfectly. Stricter targets for `lang:*` (98% and 95%), recalibrated on calibration; only the language thresholds moved. This is a second look at the random test posts for the language targets, and it is said so in the report.

### 23:15. Final evaluation of `v1`

- Test posts read: 1,200 random, 6,050 by band (`t1`), 609 (`t2`), 600 at the head of scores (`t3`). Every round read twice, then a third time where two readings differed.
- Before the second opinion: 38 shown, 30 review-only, 3 dropped.

### 23:17. Second opinion on the test labels, round `a1`

- 883 test posts, drawn among those read in the flagged bands of each shown probe (up to 15 settled yes and 15 settled no per probe), read again by Claude Opus 5.5 with the same guides, the same batches format and the same blind protocol. Checked in a transcript: the agents ran on `claude-opus-5-5`.
- Over every label of the passes concerned: 827 of 965 settled yes confirmed (86%), 120 of 4,811 settled no overturned (2.5%).
- Lowest confirmation: `dehumanisation` 10 of 27, `news_headline` 14 of 24. The Haiku annotators say yes to these two more readily than a stricter reader.
- Rule added after reading the audit: a shown probe is withdrawn to review-only when the second reader confirms fewer than 70% of at least 10 of its yes answers. Final states: 36 shown, 32 review-only, 3 dropped.

### 23:20. Export, and a check on the demo build

- `pipelines/probes/export.py` (written by the session that owns the product side) packs the run into `probes/probes.json` and `probes/probes.npz`: 42 probes, 36 shown.
- The 500,000 posts of the demo build, all from test actors, were scored with the pack as the server will: the share flagged at each level matches the share measured on test for every probe (`data/probes/runs/v1/demo-flags.json`). Largest gaps are on rare labels (`money_request` 0.060% against 0.021%).

### 23:45. False positives read

- 736 false positives of 30 shown probes on test, read and sorted by a second model (Claude Opus 5.5): near miss 70%, topic 13%, label error 12%, too short or no context 4%, language 1%.
- A slow point found and fixed along the way: the loader of labels built a new array for every answer it read, which made training take ten minutes; it now takes about one.

### What this campaign did not do

- No person has read the test posts. The audit module writes the sheets.
- No second run with hard negatives mined for the review-only probes.
- No test on another corpus, and none on the full 768 dimensions.
