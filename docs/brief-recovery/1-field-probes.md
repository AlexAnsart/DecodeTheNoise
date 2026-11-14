# Test 1: reading the fields of a brief

**Question.** A group of posts was written from one brief. Can a cheap linear probe say which stance, persona, tone and format that brief asked for, and how many posts does it need?

**Answer.** Yes for format and tone, partly for stance and persona, and only with several posts. One LLM call reads the same posts better, and from fewer of them. The probe closes most of the gap once the subject's own mean vector is subtracted.

## Method

| | |
| --- | --- |
| Data | Bench briefs of the [benchmark](benchmark.md): 85 briefs on 10 topics to fit, 47 briefs on 5 other topics to score. 32 posts per brief |
| Probe | One logistic regression per field on the 256-value vectors the server uses. Regularisation chosen on development topics held out in turn |
| Reading a group | Sum the probe's log-probabilities over N posts of the brief, take the best class. 200 random draws of N posts per brief |
| Two variants | `raw`: the vectors as served. `topic-centred`: each vector minus the mean vector of the posts on its subject |
| LLM reader | One call (`gemini-3.8-flash`, temperature 0) reads N posts and fills the same four fields from the same closed lists |
| Second writer | The same probes, unchanged, on 960 posts another model (`gemini-3.8-flash`) wrote from 40 of the held-out briefs |
| Interval | 95%, bootstrap over briefs |

Split by topic, never by post: a held-out topic shares no subject with the topics the probe was fitted on.

## Results

Accuracy on the 47 held-out briefs, by number of posts read. Chance is 0.50 for stance, 0.20 for persona, 0.25 for tone, 0.33 for format.

| Field | Reader | 1 post | 4 posts | 16 posts | 32 posts |
| --- | --- | --- | --- | --- | --- |
| Format | Probe, raw | 0.92 | 0.97 | 0.98 | 0.98 |
| | Probe, topic-centred | 0.95 | 0.99 | 1.00 | 1.00 |
| | LLM | 0.98 | 1.00 | 0.94 | |
| Tone | Probe, raw | 0.71 | 0.84 | 0.90 | 0.94 |
| | Probe, topic-centred | 0.73 | 0.91 | 0.98 | 1.00 |
| | LLM | 0.92 | 0.96 | 0.96 | |
| Stance | Probe, raw | 0.72 | 0.78 | 0.81 | 0.83 |
| | Probe, topic-centred | 0.77 | 0.85 | 0.90 | 0.92 |
| | LLM | 0.96 | 0.98 | 0.96 | |
| Persona | Probe, raw | 0.53 | 0.62 | 0.67 | 0.68 |
| | Probe, topic-centred | 0.54 | 0.72 | 0.80 | 0.83 |
| | LLM | 0.60 | 0.83 | 0.92 | |

Intervals are about ±0.10 at 16 posts (stance, raw: 0.71 to 0.90). The LLM gave 2 unusable answers of 141, counted as wrong: they explain its dip at 16 posts. All figures: [`results/field-probes.json`](results/field-probes.json), [`results/field-reader.json`](results/field-reader.json).

**On a second writer** (posts by `gemini-3.8-flash`, 40 briefs, 16 posts read):

| Field | Raw: Haiku posts | Raw: Gemini posts | Topic-centred: Haiku posts | Topic-centred: Gemini posts |
| --- | --- | --- | --- | --- |
| Format | 0.98 | 0.90 | 1.00 | 1.00 |
| Tone | 0.90 | 0.83 | 0.98 | 0.97 |
| Stance | 0.81 | 0.76 | 0.90 | 0.83 |
| Persona | 0.67 | 0.62 | 0.80 | 0.80 |

**On real data.** The teams of the Internet Research Agency are briefs that people carried out. A probe fitted on 323 actors reads the team of 134 actors it never saw (4 teams; the largest holds 47% of them):

| Posts read | 1 | 2 | 4 | 8 | 16 | 32 |
| --- | --- | --- | --- | --- | --- | --- |
| Team read correctly | 0.74 | 0.82 | 0.88 | 0.90 | 0.92 | 0.97 |
| Actors with that many posts | 134 | 134 | 134 | 134 | 95 | 62 |

Figures: [`results/ira-teams.json`](results/ira-teams.json).

## What the results mean

1. **One post is enough for the easy fields, not for persona.** Format, tone and stance show in a single post. Persona does not: a parent or a veteran is revealed by one post in a few, so accuracy climbs with every post read (LLM: 0.60, 0.83, 0.92). "One post does not reveal the brief, several constrain it" holds for persona and is false for the rest.

2. **More posts remove noise, not bias.** The raw probe stops improving: stance goes from 0.81 at 16 posts to 0.83 at 32. Its errors are not random post by post; whole briefs are misread, because each subject shifts the vectors in its own direction. On one held-out subject the raw stance probe is right for half of the briefs.

3. **Subtracting the subject turns that bias into noise.** After centring, accuracy on one post barely moves (stance 0.72 to 0.77) but accuracy on 32 posts jumps (0.83 to 0.92; persona 0.68 to 0.83). What is left after centring is no longer about the subject, so errors differ from post to post and the sum over posts cancels them.

4. **Anger hides the persona.** For briefs with an angry tone, the persona is read correctly about half as often as for the other tones (0.54 against 0.90 or more, topic-centred, 13 briefs). An angry post sounds the same whoever is said to write it.

5. **The probe mostly survives a change of writer when it is centred.** Fitted on Haiku posts, the centred probe reads Gemini posts as well for format, tone and persona (persona 0.80 and 0.80, tone 0.98 and 0.97); stance loses 7 points. The raw probe loses 5 to 8 points on every field.

6. **The LLM is the better reader; the probe is the cheaper one.** A probe is a dot product per post and can score a whole corpus. An LLM call reads the brief of a group that was already flagged. This is the cascade the project uses elsewhere.

## Limits

- **Centring is optimistic here.** The mean is taken over posts whose fields are balanced by design. In the product the mean would come from the posts around the group on the map, whose mix is unknown. Untested.
- **A closed list.** The probe can only answer with a persona or tone it was trained on. A real brief can ask for anything.
- **Synthetic briefs, one template.** The briefs were written by us from four fields. Real briefs are not built that way.
- **Stance is "approves or criticises".** It reads the polarity toward the subject, not what is being argued.
- **IRA teams differ in subject as well as in style**, and their labels were given by researchers who read the content. The IRA curve shows that a team is readable from few posts, not that the probe reads the brief rather than the subject.
- **Small cells.** The breakdown by tone rests on 10 to 13 briefs per tone.

## Decision

- A brief card should take its fields from one LLM reading of the group, not from probes.
- Probes are worth keeping for format and tone as a filter over a whole corpus, in the topic-centred form, and only on groups of 8 posts or more.
- Nothing here is shown in the product: a probe ships only after the centring is tested with the map's own neighbourhoods.

## Reproduce

```
uv run --group pipelines python -m pipelines.briefs.field_probes   # probes, both variants, both writers
uv run --group pipelines python -m pipelines.briefs.field_reader   # the LLM reader (AI Router, cached)
uv run --group pipelines python -m pipelines.briefs.ira_teams      # the IRA teams
```
