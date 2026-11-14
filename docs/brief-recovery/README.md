# Recovering the brief behind a group of posts

Three tests, run on 14 Nov 2026. Experimental: nothing here is in the product or its interface.

## The question

Before language models, a swarm copied a text. Now it can copy a prompt: every post is unique, so near-duplicate detection finds nothing. Posts written from one instruction still share something. Two questions follow:

1. **Does this group of posts come from one instruction?**
2. **If so, which one?**

The starting doubt was that neither can be answered: a model can at best describe an intention, never the prompt, and the writer model, its temperature and its sampling are unknown.

## The answer in short

The exact prompt cannot be recovered and does not need to be. What an instruction leaves in its posts is what it holds constant, and that is recoverable and checkable.

| Test | Question | Result | Verdict |
| --- | --- | --- | --- |
| [1. Field probes](1-field-probes.md) | Can a cheap probe read the stance, persona, tone and format a brief asked for? | With 16 posts: format 0.98, tone 0.90, stance 0.81, persona 0.67. One LLM call does better from fewer posts (persona 0.92). Subtracting the subject's mean vector lifts the probe to 1.00, 0.98, 0.90, 0.80 | Use an LLM reading for a brief card. Keep probes as a corpus-wide filter for format and tone |
| [2. Interchangeable actors](2-interchangeable-actors.md) | Inside a group, does each actor have a voice of its own? | Real actors of 2026 are told apart in 999 draws of 1,000 (score 15.0). Actors run from one brief are not: score 0.0, -0.9, and 2.3 with a persona per actor. One threshold flags 100%, 100% and 62% of these three modes, for 0% to 2% of held-out real groups. 9 of 17 groups of a real troll operation score like the synthetic ones | The strongest of the three. Worth building as one trace of the swarm card, on the meaning score, after a tighter organic control |
| [3. Prompt loop](3-prompt-loop.md) | Does a propose, run, compare, correct loop recover the instruction better than one reading? | One reading gets the four fields right for 39 or 40 briefs of 40. The loop brings regenerated posts closer than the true instruction does (fit 1.15), but its instruction is no closer to the true one | One reading is enough. The loop imitates the writer; it does not recover more of the prompt |

**In the product.** Test 2 is served as the "One voice, or several?" check on a lasso selection (`backend/voices/`, `frontend/src/voices/`), with its own evaluation in `reports/voices/`: at 6 actors of 6 posts it flags 50 of 53 groups written from one brief, none of 73 held-out real groups, and 1 of 73 of the hardest ones. Tests 1 and 3 stay experiments.

Question 2 ("which instruction?") is answered by tests 1 and 3. Question 1 ("is there one?") is answered by test 2, and it is the harder one: a model will write a plausible brief for any group, organic or not.

## What changed our mind

- **Non-determinism helps.** What varies from post to post is what the instruction left free; what does not vary is the instruction. With no sampling the posts would be copies.
- **The unknown model matters little for content.** Probes fitted on one model's posts read another model's posts. A different model family recovered the briefs.
- **Describing is easy, testing is the work.** Every result here rests on something held out: topics the probe never saw, a half of the posts the loop never saw, real groups the threshold never saw.
- **"Closer to the posts" is not "closer to the prompt".** Test 3 shows a loop improving the first while the second stays flat.
- **A persona changes how an actor writes, not what it has to say.** Test 2 shows it on synthetic actors and on a real operation.

## The benchmark

Real groups of actors from a 2026 sample of X posts and from the Internet Research Agency, and 7,286 synthetic posts written by Claude Haiku: 132 briefs with known fields, and 67 groups of six actors run in one of three ways. All synthetic subjects are fictional. Details, and what the writers' refusals changed: [benchmark.md](benchmark.md).

## Limits that hold for all three tests

- The positives are synthetic, written by one model from briefs we designed. A real operator writes other prompts, edits the output and mixes sources.
- English, one platform, one embedding model (`embeddinggemma:300m-qat-q8_0`, 256 values).
- Sample sizes are those of one evening: 40 to 47 held-out briefs, 14 to 21 synthetic groups per mode. Every rate comes with its interval in the result files.
- No detector here has been audited by hand on flagged real groups.

## Files

| Path | Content |
| --- | --- |
| `docs/brief-recovery/` | This write-up. [`results/`](results/) holds the figures as JSON, written by the code |
| `pipelines/briefs/` | The code: benchmark (`pools`, `topics`, `fiction`, `design`, `collect`), test 1 (`field_probes`, `field_reader`, `ira_teams`), test 2 (`interchange*`), test 3 (`loop*`) |
| `tests/pipelines/test_interchange.py`, `test_brief_bench.py` | Unit tests of the statistics |
| `data/datasets/brief-bench/` | The data. Not in git |
| [`../ai_prompt_reverse_engineering.md`](../ai_prompt_reverse_engineering.md) | The proposal these tests came from. Its "brief card" fit is replaced by the measures of test 3 |

## Cost

| | |
| --- | --- |
| Writers | 538 Claude Haiku subagent contexts (16 pilot, 472 main run, 50 second ask), plus a first main run stopped early. About 30 million tokens, most of them cached context |
| AI Router | 624 calls to `gemini-3.8-flash`: 0.47 million tokens in, 0.35 million out. At the catalogue's listed prices this is about 202 of its units; the dashboard gives the amount charged |
| Embeddings | Local model, no charge |
