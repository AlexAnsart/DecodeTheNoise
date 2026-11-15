"""Writes the report of the cascade measured by score band. Pure: text from the numbers."""

from collections.abc import Mapping

from pipelines.review.band_estimate import MIN_BAND_READ

Rate = Mapping[str, float] | None


def _rate(rate: Rate) -> str:
    if rate is None:
        return "no estimate: a band was not read"
    return f"{rate['value']:.1%} ({rate['low']:.1%} to {rate['high']:.1%})"


def _table(header: list[str], rows: list[list[object]]) -> str:
    lines = [header, ["---"] * len(header), *rows]
    return "\n".join("| " + " | ".join(str(cell) for cell in line) + " |" for line in lines)


def render_bands(block: Mapping[str, object], random_sample: object) -> str:
    probes: Mapping[str, Mapping[str, object]] = block["probes"]  # type: ignore[assignment]
    rows = [
        [
            f"`{name}`" + ("" if probe["scope"] == "flagged" else ", highest scores only"),
            f"{probe['flagged_in_split']:,}",
            probe["read"],
            probe["read_yes"],
            _rate(probe["after_probe"]),  # type: ignore[arg-type]
            probe["kept"],
            probe["kept_yes"],
            _rate(probe["after_review"]),  # type: ignore[arg-type]
            _rate(probe["true_positives_kept"]),  # type: ignore[arg-type]
        ]
        for name, probe in probes.items()
    ]
    header = [
        "Probe",
        "Test posts measured",
        "Of them, read",
        "Annotated yes",
        "Precision after the probe",
        "Kept by the review",
        "Of them, a yes",
        "Precision after the review",
        "True positives kept",
    ]
    rounds = ", ".join(f"`{name}`" for name in block["rounds"])  # type: ignore[union-attr]
    parts = [
        "# A probe, then the review: measured by score band",
        "## What is decided",
        "\n".join(
            [
                "- **Unit:** one post of the test split that a technique probe flags at its lowest "
                "level (`possible`, `probable` when it has no other, or the review cut of a probe "
                "that is not shown).",
                "- **Positive means:** the settled answer of the annotation on the post is `yes` "
                "for the label of the probe.",
                f"- **Detector:** the probes of run `{block['pack_run']}`, then "
                f"`backend.review.reader.review_item` with `{block['model']}` and prompt "
                f"`{block['prompt_version']}`, asked as the product asks: the technique probes "
                'that flag the post are listed, text alone. "Kept" means the review answered '
                "`supported` for the probe.",
                "- **Reference:** the annotation of the probe campaign, an LLM annotation and not "
                "human gold (`reports/review/2026-11-15-review-v2.md`).",
            ]
        ),
        "## Why by score band",
        "The random test sample holds about a hundred posts a technique probe flags, so the "
        "cascade measured on it has wide intervals. The probe campaign also read, for each "
        "probe, posts drawn uniformly inside bands of its scores on the test split, to measure "
        "its levels. Inside a band those posts and the random ones are a uniform sample of the "
        "band. Each band is therefore counted for the number of test posts it holds: the shares "
        "below are those of all the test posts the probe flags, not of the posts read. The "
        "intervals come from the Jeffreys posterior of the four outcomes of each band (kept or "
        "not, yes or not), propagated by simulation: the method of `pipelines/probes/estimate.py`, "
        "with four outcomes instead of two.",
        "## Results on test",
        f"{block['posts_read']:,} posts read by the review, of {block['posts_flagged']:,} flagged "
        f"posts with a settled answer, from the rounds {rounds}.",
        _table(header, rows),
        'A probe marked "highest scores only" has no level: it sends a post to the review from '
        "its review cut, but the campaign read its highest scores only. Under them fewer than "
        f"{MIN_BAND_READ} posts were read in a band that holds thousands, so nothing narrow can "
        "be said there: the figures of that row are those of its highest scores, the number in "
        "the second column. Every band, its size and its counts are in "
        "`reports/review/metrics.json` under `cascade_bands.probes.<probe>.bands`.",
    ]
    if isinstance(random_sample, Mapping):
        parts += [
            "## The same on the random sample alone",
            "The first measure of the cascade, kept as it was: the flagged posts among the 1,200 "
            "random test posts, with Wilson intervals. It is in the main report and under "
            "`cascade` in `metrics.json`. Both are measures of the same thing; this one rests on "
            "more posts.",
        ]
    parts += [
        "## Limits",
        "\n".join(
            [
                "- The posts drawn by band were drawn on the scores of the probe they are counted "
                "for; a post is counted for a probe only when it was drawn for it or at random.",
                "- A band is weighted by its size in the test split of the campaign: three shards "
                "of the corpus, distinct texts of 1,500 characters at most.",
                "- The review read each post alone, without its neighbours or the other posts of "
                "its account, which the product adds.",
                "- Untested off-distribution, per language, and for the probes that are not "
                "technique probes.",
            ]
        ),
    ]
    return "\n\n".join(parts) + "\n"
