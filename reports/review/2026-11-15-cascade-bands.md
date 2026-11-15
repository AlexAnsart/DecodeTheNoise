# A probe, then the review: measured by score band

## What is decided

- **Unit:** one post of the test split that a technique probe flags at its lowest level (`possible`, `probable` when it has no other, or the review cut of a probe that is not shown).
- **Positive means:** the settled answer of the annotation on the post is `yes` for the label of the probe.
- **Detector:** the probes of run `v1`, then `backend.review.reader.review_item` with `gemini-3.8-flash` and prompt `review-v2`, asked as the product asks: the technique probes that flag the post are listed, text alone. "Kept" means the review answered `supported` for the probe.
- **Reference:** the annotation of the probe campaign, an LLM annotation and not human gold (`reports/review/2026-11-15-review-v2.md`).

## Why by score band

The random test sample holds about a hundred posts a technique probe flags, so the cascade measured on it has wide intervals. The probe campaign also read, for each probe, posts drawn uniformly inside bands of its scores on the test split, to measure its levels. Inside a band those posts and the random ones are a uniform sample of the band. Each band is therefore counted for the number of test posts it holds: the shares below are those of all the test posts the probe flags, not of the posts read. The intervals come from the Jeffreys posterior of the four outcomes of each band (kept or not, yes or not), propagated by simulation: the method of `pipelines/probes/estimate.py`, with four outcomes instead of two.

## Results on test

913 posts read by the review, of 924 flagged posts with a settled answer, from the rounds `m1`, `t1_calls`, `t1_claims`, `t1_emotion`, `t1_format`, `t1_hostility`, `t1_rhetoric`, `t1_solicitation`, `t1_subject`, `t2_calls`, `t2_rhetoric`, `t2_solicitation`, `t3_calls`, `t3_hostility`, `t3_rhetoric`, `t3_solicitation`, `t3_subject`.

| Probe | Test posts measured | Of them, read | Annotated yes | Precision after the probe | Kept by the review | Of them, a yes | Precision after the review | True positives kept |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `loaded_language` | 29,646 | 265 | 211 | 73.8% (67.0% to 79.3%) | 201 | 190 | 93.2% (87.8% to 96.5%) | 87.3% (81.0% to 92.2%) |
| `exaggeration` | 9,900 | 220 | 176 | 72.7% (64.9% to 79.1%) | 161 | 153 | 93.1% (86.5% to 96.9%) | 85.4% (77.7% to 91.1%) |
| `fear_appeal` | 108 | 92 | 55 | 59.8% (49.9% to 69.2%) | 41 | 38 | 92.7% (81.4% to 97.8%) | 69.1% (56.2% to 80.2%) |
| `doubt`, highest scores only | 100 | 47 | 24 | 51.1% (36.9% to 64.8%) | 13 | 11 | 84.6% (58.3% to 96.7%) | 45.8% (27.6% to 65.2%) |
| `identity_appeal`, highest scores only | 100 | 48 | 27 | 56.2% (42.4% to 69.0%) | 19 | 16 | 84.2% (63.6% to 95.3%) | 59.3% (40.6% to 76.6%) |
| `us_vs_them` | 951 | 194 | 145 | 71.3% (64.0% to 77.6%) | 93 | 92 | 98.4% (92.4% to 99.7%) | 60.3% (51.6% to 68.1%) |
| `slogan`, highest scores only | 100 | 49 | 31 | 63.3% (48.8% to 74.9%) | 26 | 25 | 96.2% (82.8% to 99.6%) | 80.6% (64.1% to 91.3%) |

A probe marked "highest scores only" has no level: it sends a post to the review from its review cut, but the campaign read its highest scores only. Under them fewer than 20 posts were read in a band that holds thousands, so nothing narrow can be said there: the figures of that row are those of its highest scores, the number in the second column. Every band, its size and its counts are in `reports/review/metrics.json` under `cascade_bands.probes.<probe>.bands`.

## The same on the random sample alone

The first measure of the cascade, kept as it was: the flagged posts among the 1,200 random test posts, with Wilson intervals. It is in the main report and under `cascade` in `metrics.json`. Both are measures of the same thing; this one rests on more posts.

## Limits

- The posts drawn by band were drawn on the scores of the probe they are counted for; a post is counted for a probe only when it was drawn for it or at random.
- A band is weighted by its size in the test split of the campaign: three shards of the corpus, distinct texts of 1,500 characters at most.
- The review read each post alone, without its neighbours or the other posts of its account, which the product adds.
- Untested off-distribution, per language, and for the probes that are not technique probes.
