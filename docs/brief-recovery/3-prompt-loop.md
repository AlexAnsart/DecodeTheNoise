# Test 3: recovering the instruction with a loop

**Question.** Posts were written from a hidden instruction. Does a loop that proposes an instruction, runs it, compares the result with the real posts and corrects itself recover that instruction better than a single reading?

**Answer.** One reading already recovers what the instruction asked for. The loop then makes the regenerated posts resemble the real ones more, beyond what the true instruction itself achieves, but the instruction it writes is no closer to the true one. The loop learns to imitate the writer; it does not learn more about the prompt.

## Method

This is "gradient descent on a prompt" in the only form open to us: no access to the writer model, only calls to another one.

| | |
| --- | --- |
| Data | 40 held-out briefs of the [benchmark](benchmark.md), 8 per topic on 5 topics, written by Claude Haiku. 32 posts each, split once: **16 seen** by the loop, **16 hidden** |
| Model | `gemini-3.8-flash` plays every role. A different family from the writer: the realistic case |
| Round 0 | A reader sees the 16 posts and writes the four closed fields and an instruction of at most 120 words |
| Rounds 1 to 3 | A writer runs the best instruction so far (24 posts, one call, temperature 1). An editor sees those posts next to the 16 real ones, names what differs, and rewrites the instruction |
| Distance | Energy distance between two sets of post vectors: 0 when the sets come from one distribution |
| Chosen round | The round closest to the **seen** half. The hidden half never steers anything |
| Honest score | The chosen instruction is run once more. Those fresh posts are the ones measured: the round was picked on its own posts, which flatters it |
| Interval | 95%, bootstrap over briefs |

Two anchors frame every distance. **Floor**: the subject alone ("Write posts about …"). **Ceiling**: the true instruction, run by the same model. The fit is the share of the way from floor to ceiling, summed over briefs.

## Results

**In the space of posts**: how far the regenerated posts land from the 16 hidden posts.

| Posts written from | Distance to the hidden half | True brief ranked first among the 9 or 10 of its topic |
| --- | --- | --- |
| *(the 16 seen posts themselves)* | 0.002 | |
| The loop's chosen instruction | **0.071** (0.061 to 0.083) | 97% |
| The true instruction (ceiling) | 0.097 (0.082 to 0.114) | 90% |
| Round 0, one reading | 0.124 (0.099 to 0.149) | 90% |
| The subject alone (floor) | 0.271 (0.233 to 0.311) | 10% (chance) |

- Fit: 0.85 after one reading (0.71 to 0.96), **1.15** after the loop (1.06 to 1.27). Above 1 means closer than the true instruction got.
- The loop brought the posts closer for 80% of the briefs. Mean gain in distance: 0.053 (0.033 to 0.075).
- Picking the round on its own posts flattered it by 0.009 (0.062 before the fresh run).
- The chosen round was round 0 for 10 briefs, round 1 for 13, round 2 for 12, round 3 for 5.

**In the space of prompts**: how close the recovered instruction is to the true one.

| | Round 0 | Chosen round |
| --- | --- | --- |
| Stance, persona recovered exactly | 100%, 100% | 100%, 100% |
| Tone recovered exactly | 100% | 97% |
| Format recovered exactly | 97% | 100% |
| True instruction ranked first among its topic's, by cosine | 97% | 95% |
| Cosine to the true instruction | 0.870 | 0.863 |
| Length in words (true instruction: 89) | 66 | 86 |

All figures: [`results/prompt-loop.json`](results/prompt-loop.json), with three briefs written out.

## What the results mean

1. **The brief is recovered at round 0.** From 16 posts, one LLM call gets the four fields right for 39 or 40 briefs of 40, and its posts point to the right brief among its topic's 9 or 10 as often as the true instruction's own posts do (90%). The fear that a model "can only describe an intention" is half right: it cannot give the wording, but the intention it describes is the right one, and it is checkable.

2. **The loop works as an optimiser.** The gain holds on posts it never saw, and on fresh posts, for 4 briefs in 5. The check that matters, hidden half and fresh run, was passed.

3. **But it optimises resemblance to the posts, not to the prompt.** The instruction gets longer and no closer to the truth: cosine 0.870 to 0.863, rank 97% to 95%, tone 100% to 97%. The fit above 1 is the tell: nothing can be closer to the prompt than the prompt itself, so what the loop gained is not in the prompt.

4. **What it gained is the writer's habits.** Reading the editor's notes, the corrections are doses and recurring details: "the target names the coach in a third of the posts, not in all", "the military background stays implicit", lists of the hashtags and emoji seen. None of this was in the true instruction. It is how one model, in one context, carried it out.

5. **Cosine to the true prompt is a poor score.** The floor instruction, which holds the subject and nothing else, has the highest cosine to the true one (0.93) because it shares its opening words. It ranks the right brief at chance (10%). Published work on prompt recovery reports this cosine; here it rewards shared wording over recovered content. Ranking the true instruction among close alternatives is the score that separates them.

6. **Why 20 posts did not drown the loop in noise.** The worry was that the distance, measured on so few posts, would be too noisy to steer by. It was not: the gain on the seen half predicts the gain on the hidden half (correlation 0.92 across briefs). Both halves came from one context, so they agree with each other more than two samples of a real campaign would.

## Limits

- **One context wrote both halves.** The hidden half is held out from the loop, not from the writer. With posts from several sessions, or edited by hand, a habit learned on one half may not hold on the other. Untested.
- **Fields that match the reader's list.** The reader is given the same closed lists the briefs were drawn from. A real brief has fields nobody listed.
- **One model family reconstructs.** The same-family case (Haiku reading Haiku) was not run: on the one call tried, Haiku declined to write the posts through the API.
- **No organic control.** The loop was run on groups that do have a brief. On an organic group it will also return an instruction; nothing here says how to tell. That is the job of [test 2](2-interchangeable-actors.md).
- **Cost.** 8 LLM calls and about 100 embeddings per group, against 1 call for a reading.

## Decision

- **A brief card needs one reading, not a loop.** The reading gives the fields and an instruction; quote posts for each field as evidence.
- **Keep the loop for another job**: producing look-alike posts of a known swarm, as test material for a detector. It is a generator of imitations, and should be named so.
- **Score recovery by ranking** the true brief among close alternatives, in the space of posts. Not by cosine between prompts.

## Reproduce

```
uv run --group pipelines python -m pipelines.briefs.loop_run      # the loop (AI Router, cached)
uv run --group pipelines python -m pipelines.briefs.loop_report   # the numbers
```
