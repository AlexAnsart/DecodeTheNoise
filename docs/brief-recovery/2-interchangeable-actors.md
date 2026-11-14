# Test 2: are the actors of a group interchangeable?

**Question.** Several actors post about the same thing. Does each of them have a voice of its own? Real actors should. Actors fed from one brief should not: any post could have come from any of them.

**Answer.** Real actors are told apart almost always, even from two posts each. Actors run from one brief are interchangeable in what they say, under every way of running them we tried. Giving each actor a persona fakes a different style, not different things to say. One threshold on a single score flags 100% of the synthetic groups without a persona and 62% of those with one, for 0% to 2% of real groups. A real operation shows the same pattern.

## Method

| | |
| --- | --- |
| Score | Take a group of posts. Compare two posts by the same actor with two posts by different actors. The **gap** is how much closer the first pair is. Shuffle who wrote what 999 times: the score **z** is the gap, in standard deviations of its shuffled values. z near 0: actors are interchangeable |
| Two readings | **Meaning**: cosine between the post vectors. **Style**: 16 surface features of a post (length, capitals, punctuation, hashtags, emoji, how it ends), standardised |
| Told apart | The permutation test at the 5% level: fewer than 5% of shuffles give a gap as large |
| Group size | 6 actors of 6 posts each, drawn 20 times per group. Other sizes in the size table |
| Detector | Flag a group when its meaning z is under a threshold. The threshold is the value that 5% of the hardest real draws fall under, on half of the real pools. Every rate is measured on the other half |
| Interval | 95%, bootstrap over groups |

The arms, from the [benchmark](benchmark.md):

| Arm | Groups at 6 × 6 | What it is |
| --- | --- | --- |
| `organic` | 167 | Real actors of 2026 who posted on one word in one month; 6 of them drawn at random |
| `organic-alike` | 167 | The same pools, keeping the 6 actors that resemble each other most: the hardest real groups |
| `shared` | 21 | One context wrote all the posts; they were dealt to the actors |
| `solo` | 18 | One context per actor, the same brief |
| `persona` | 14 | One context per actor, the same brief, plus an age, a place and a writing habit per actor |
| `ira-RightTroll`, `ira-NewsFeed` | 17, 69 | Actors of one Internet Research Agency team, in one zone of the map, in one month |

## Results

**The score, per arm.**

| Arm | z, meaning | z, style | Told apart by meaning | Told apart by style | Post given back to its actor (chance 0.17) |
| --- | --- | --- | --- | --- | --- |
| `organic` | **15.0** (14.5 to 15.4) | 11.9 | 100% | 100% | 0.80 |
| `organic-alike` | **11.8** (11.1 to 12.5) | 10.1 | 97% | 99% | 0.68 |
| `shared` | 0.0 (-0.3 to 0.3) | -0.3 | 6% | 3% | 0.18 |
| `solo` | -0.9 (-1.3 to -0.5) | 1.7 | 1% | 42% | 0.15 |
| `persona` | 2.3 (1.5 to 3.3) | **12.4** | 57% | 100% | 0.31 |
| `ira-NewsFeed` | 5.7 (5.1 to 6.3) | 2.9 | 95% | 46% | 0.47 |
| `ira-RightTroll` | 4.9 (2.5 to 7.4) | 2.3 | 54% | 46% | 0.39 |

**The detector.** Threshold: meaning z under 2.54, set on 94 real pools. Rates on the 73 other real pools and on the arms the threshold never saw:

| Arm | Flagged |
| --- | --- |
| `organic` (73 held-out pools) | 0% of 1,460 draws |
| `organic-alike` (73 held-out pools) | 1.8% (0.1% to 4.9%) |
| `shared` | 100% |
| `solo` | 100% |
| `persona` | 62% (44% to 78%) |
| `ira-NewsFeed` | 13% (9% to 17%) |
| `ira-RightTroll` | 52% (30% to 74%) |

What a flag is worth depends on how rare coordinated groups are. With the false-positive rate of the hardest real groups (1.8%), and the worst case its interval allows (4.9%) in brackets:

| Share of groups that are coordinated | Precision, `shared` or `solo` | Precision, `persona` |
| --- | --- | --- |
| 1% | 36% (17%) | 26% (11%) |
| 5% | 75% (52%) | 64% (40%) |
| 20% | 93% (84%) | 90% (76%) |

Without any threshold, the meaning score ranks a real group above a synthetic one with probability 1.00 (`shared`), 1.00 (`solo`), 1.00 (`persona`); against the hardest real groups, 0.99, 0.99 and 0.96.

**Group size.** Share of draws where actors are told apart by meaning:

| Arm | 6 actors × 2 posts | 6 × 3 | 6 × 6 | 3 × 6 |
| --- | --- | --- | --- | --- |
| `organic` | 97% | 99% | 100% | 99% |
| `organic-alike` | 84% | 92% | 97% | 94% |
| `persona` | 17% | 22% | 57% | 44% |
| `shared` | 7% | 6% | 6% | 5% |

**A real operation.** The 17 `ira-RightTroll` groups split by month, with no overlap:

| Months of 2017 | Groups | z, meaning |
| --- | --- | --- |
| June, September, October | 9 | -0.6 to 1.5 |
| July, August | 8 | 5.1 to 15.2 |

In the posts we read, all these actors relay headlines with a link. In July and August each actor also opens its posts with a hashtag of its own (`#jud`, `#cha`, `#vvmar`). Read again without hashtags and links, the mean score of the 17 groups falls from 4.9 to 1.7 and the share flagged rises from 52% to 76%.

All figures, per group: [`results/interchangeable-actors.json`](results/interchangeable-actors.json).

## What the results mean

1. **Real actors have a voice, and it shows at once.** With 6 posts each they are told apart in 999 draws out of 1,000, with 2 posts each in 97%. A post goes back to its author 4 times in 5. The test is not blind: this was the result the idea needed first.

2. **One brief leaves no voice.** Dealt from one context, the posts score 0: the test finds exactly nothing, as it should. Everything that follows is a way an operator might hide that.

3. **A session per actor does not help, and leaves its own trace.** The meaning score goes below zero (-0.9): a context avoids repeating itself, so its own posts are *further apart* than posts of two contexts. Real actors never do that. Style differs a little between sessions (told apart 42% of the time): each context settles into habits.

4. **A persona changes how an actor writes, not what it has to say.** With an age, a place and a writing habit per actor, the style score reaches the level of real actors (12.4 against 11.9) and the style test is fooled every time. The meaning score barely moves: 2.3, against 11.8 for the most alike real actors. Real actors differ by what they care about, and a brief gives every actor the same thing to care about.

5. **So the detector must read meaning and use a threshold.** "Told apart or not" breaks on personas (57% are told apart by meaning). The size of the gap does not: the threshold flags 62% of persona groups, and the ranking against real groups is near perfect (0.96 to 1.00).

6. **A real operation used the same trick, and it fails the same way.** For 9 of 17 IRA groups the actors are as interchangeable as our `shared` arm: one feed of headlines, dealt out. In the other 8 each actor carries a hashtag of its own, the 2017 form of a persona, and that tag is most of what tells them apart: without it the score drops by two thirds. This is real data, written by people, years before language models.

7. **What defeats the signal is giving each actor its own subject.** `ira-NewsFeed` actors are told apart by meaning 95% of the time. Linvill and Warren describe them as local news aggregators; if each covers its own place, the brief itself assigns a different subject per actor. An operator who does the same with a model would pass this test.

## Limits

- **The real groups are loose.** "One word, one month" is wider than the false alarm that matters: many people reacting to one event in one hour. `organic-alike` narrows it, not all the way. Untested on event-tight groups.
- **The threshold belongs to one group size.** z grows with the number of posts (real groups: 4.2 at 6 × 2, 15.0 at 6 × 6). Each size needs its own threshold, set the same way.
- **Few synthetic groups.** 14 to 21 per mode, one writer model, fictional subjects. The persona arm lost the most groups to writers who declined, and not at random.
- **Personas we wrote.** They set style. An operator could give each actor its own angle, biography or memory, which is what point 7 warns about. Untested.
- **IRA is not a matched control.** Other years, posts of 140 characters, groups cut by map zone from a 4% sample, style features standardised on 2026 posts. The IRA meaning scores are comparable in kind; the IRA style scores are not.
- **The real actors of 2026 are unlabelled.** Some may be scripted: the false-positive rates are upper bounds.
- **It abstains often.** It needs several actors with at least 2 or 3 posts each in one group. Most actors of a corpus do not qualify.
- **No hand audit** of flagged real groups yet.

## As served in the product

Built the same evening as the **"One voice, or several?"** check on a lasso selection of the map: `POST {base}/voices` (`backend/voices/`), shown in the selection list (`frontend/src/voices/`).

The served rule is slightly different from the detector above, and was measured on its own (`reports/voices/`, written by `pipelines/briefs/voices_report.py`):

| | Above | Served |
| --- | --- | --- |
| What is compared to the threshold | Each draw of 6 actors × 6 posts | The mean of 20 draws: one answer per selection |
| Sizes | 6 × 6 | 6 × 6, and 4 × 4 when the selection is too small |
| Threshold | 2.54 | 3.09 at 6 × 6, 1.67 at 4 × 4 |

| Served check, held-out groups | 6 × 6 | 4 × 4 |
| --- | --- | --- |
| Groups written from one brief, flagged | 50 of 53 | 60 of 65 |
| With a persona per actor, flagged | 11 of 14 | 16 of 21 |
| Real groups, actors drawn at random, flagged | 0 of 73 | 0 of 83 |
| Real groups, the most alike actors, flagged | 1 of 73 | 2 of 83 |
| `ira-RightTroll` groups, flagged | 9 of 17 | 9 of 17 |
| A near-duplicate rule on the same groups | 1 of 67 one-brief groups, 13 of 88 real groups | |

The three real groups flagged were read. Two are one pool: police departments relaying the kit of a national drug take-back day, an open campaign and truly one voice. The third is sports outlets reporting the same matches of one club: the false alarm to expect on event-tight groups.

## Decision


- **Built as a check on a selection** (above), level `possible` only. Still worth adding as one trace of a swarm card once swarms exist: "the actors of this swarm are interchangeable in what they say", with the score, where real groups score, and the two rates above. It explains a swarm that other traces flagged; alone, at a 1% base rate, a flag is right about one time in three.
- **Use the meaning score.** Keep the style score as evidence shown to the reader, not as a detector.
- **Read posts without hashtags and links** before scoring: it removes the cheapest per-actor marker.
- **Before shipping**: an event-tight organic control, a threshold per group size, and a hand reading of the first flagged real groups.

## Reproduce

```
uv run --group pipelines python -m pipelines.briefs.interchange_run
```
