"""The text of the evaluation report of the review: the sections of the template of skill
`evaluate-detector`, with a `{name}` wherever a figure or a table of the metrics goes."""

_DECIDED = (
    "## What is decided\n\n"
    "- **Unit:** one post.\n"
    "- **Positive means:** for one technique, the settled answer of the annotation on the post "
    "is `yes`. The review marks a technique when it names it with a span copied from the post.\n"
    "- **Detector:** `backend.review.reader.review_item`, prompt `{prompt_version}` (sha256 of "
    "the system prompt: `{prompt_sha}`), model `{model}` through the Hostinger AI Router, "
    "temperature {temperature}. Each post is read alone: no neighbour, no other post of the "
    "account, no probe listed. There is no threshold: a technique is named or it is not.\n"
    "- **Reference:** {reference} The review and the annotators are models of two different "
    "families applying the same guides. What is measured is how far the review agrees with "
    "that annotation, not whether it is right.\n"
    "- **Commit:** `{commit}`"
)

_DATA = (
    "## Data\n\n"
    "| Split | Source | Licence | Items | Positives | Groups |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| train | not used: nothing is fitted | | | | |\n"
    "| calibration | not used: the review has no threshold | | | | |\n"
    "| test | round `{round}` of the probe campaign, drawn at random from [tweets_sample_2026]"
    "(https://huggingface.co/datasets/SinclairSchneider/tweets_sample_2026) | not stated | "
    "{asked} | {posts_with_technique} posts with at least one technique; per technique below | "
    "{accounts} accounts |\n\n"
    "Split rule: by account. A salted hash of the account id puts 60% of the accounts in "
    "train, 20% in calibration and 20% in test (`pipelines/probes/pool.py`). There is no time "
    "cut. The test posts are a uniform draw of the test split, so the share of positives below "
    "is the share in this corpus. The campaign left out posts over 1,500 characters and "
    "repeated texts.\n\n"
    "What was tuned on what: nothing is fitted on these posts. The guides the prompt quotes "
    "were written on train posts and frozen before a test post was read "
    "(`docs/probes/journal.md`). The method text of the prompt was not tuned: its first wording "
    "was kept after a try on 5 hand-written posts and 4 posts of the demo build "
    "(`docs/review.md`, section 9). Those 4 posts are not named, so whether one of them is a "
    "test post cannot be established; nothing was changed after reading them.\n\n"
    "The campaign also holds test posts drawn by the score of a probe (rounds `t1` to `t3`). "
    "They are not used here: a rate read on them would not be a rate of the corpus."
)

_RESULTS = (
    "## Results on test\n\n"
    "Threshold: none.\n\n"
    "Coverage: {posts} of {asked} posts got a readable answer. {failed} answers could not be "
    "parsed, {failed_with_json} of them because characters surround the JSON object, which the "
    "reader does not strip. {unanswered} posts got no answer. The review never abstains on a "
    "technique: it names it or it does not.\n\n"
    "{counts_table}\n\n"
    "A technique gets rates when two annotators agree on it with a kappa of {min_kappa} or "
    "more and it has at least {min_positives} positives. Under that agreement the annotators "
    "themselves disagree, so agreeing with them means little: the counts are given, and the "
    "product shows no reliability for the technique. F1 is not a share of posts and has no "
    "Wilson interval. Average precision does not apply: the review gives no score to rank "
    "on.\n\n"
    "{rates_table}\n\n"
    "The {pooled_labels} measurable techniques together, {pooled_pairs} post-technique pairs: "
    "precision {pooled_precision}, recall {pooled_recall}, false-positive rate {pooled_fpr}. "
    "The pairs of one post are not independent, so these three intervals are a little too "
    "narrow.\n\n"
    "Quote check: {rejected_quotes} techniques were reported with a quote that is not in the "
    "post, which the reader drops (last column of the first table): {rejected_on_yes} on a "
    "post the annotation says yes for (a hit lost), {rejected_on_no} on a post it says no for "
    "(an error avoided)."
)

_BASE_RATES = (
    "## Precision at realistic base rates\n\n"
    "What precision becomes where the technique is rarer or more common than here, from the "
    "recall and the false-positive rate measured above. In brackets: the same computed from "
    "the unfavourable ends of the two intervals (low recall, high false-positive rate), then "
    "from the favourable ones. A technique marked on a handful of posts has a wide bracket: "
    "its first figure alone says little.\n\n"
    "{base_rates_table}"
)

_BASELINES = (
    "## Baselines\n\n"
    "The measurable techniques together. The first row is by construction, not measured.\n\n"
    "{baseline_table}\n\n"
    "The last column shows why it is never read alone: nearly every pair is a `no`.\n\n"
    'Ceiling: the last two columns of the rates table. "Two annotators" is the kappa between '
    "two single readings of the 2,000 calibration and test posts "
    "(`reports/probes/agreement.json`). The review is compared with the settled answer, which "
    "rests on two or three readings: the two columns are close to the same comparison, not "
    "exactly the same.\n\n"
    "No published result exists on these posts."
)

_RUNS = (
    "## Agreement between two runs\n\n"
    "{runs_asked} test posts, drawn at random with a seed, were asked a second time with the "
    "cache bypassed: same prompt, same model, temperature {temperature}. {runs_posts} of them "
    "have a readable answer in both runs.\n\n"
    "- Posts with the same list of techniques in both runs: {runs_same_posts}.\n"
    "- Post-technique pairs answered the same way: {runs_same_decisions}.\n"
    "- Posts that changed, per technique: {runs_changed}."
)

_LIMITS = (
    "## Off-distribution\n\n"
    "Untested off-distribution: no other labelled source was read. Every post comes from one "
    "dataset of X posts of 1,500 characters at most.\n\n"
    "## Limits\n\n"
    "- The reference is an LLM annotation. A disagreement can be an error of the review or of "
    "the annotation: the audit above says which it was for the cases read.\n"
    "- Counts only, no rate: {counts_only}.\n"
    "- The product gives the review more than the text: the nearest posts and other posts of "
    "the account. Whether that context changes the answers is untested.\n"
    "- The cascade is measured on the technique probes only. The answers of the review to the "
    "probes of the other families (calls, hostility, solicitation and the rest) are untested.\n"
    "- The review of a selection of posts is untested.\n"
    "- Results per language are untested.\n"
    "- These numbers hold for `{model}` and prompt `{prompt_version}` with the system prompt "
    "hashed above. A change of model, prompt or guide needs a new run."
)

TEMPLATE = "\n\n".join(
    [
        "# LLM review of one item: evaluation {date}",
        _DECIDED,
        _DATA,
        _RESULTS,
        _BASE_RATES,
        _BASELINES,
        "## Cascade: a probe flags, the review reads\n\n{cascade}",
        _RUNS,
        "## False-positive audit: the disagreements read\n\n{audit}",
        _LIMITS,
    ]
)
