"""What the method page shows, read from the files the product was built from: the dataset and
how the demo was drawn from it, the labels and the exact instructions the annotators received,
the documents of the probe campaign, the prompt of the LLM review, and the labelled posts
themselves, so that every number of the page can be traced back to what produced it.

Nothing here is typed by hand for the page: a part whose file is missing is null or empty, and
the page says it is not published yet.
"""

from pydantic import BaseModel

# What an annotator answered on a label: `yes`, `no` or `unclear`; for the labels that have
# answers of their own (language, theme, political side), one of those; and, in a reading,
# `invalid` for a yes that quoted words the post does not hold, which counts as no reading.
Answer = str


class BuildFacts(BaseModel):
    name: str
    points: int
    zones: int
    built_at: str
    embedding_key: str
    dims: int


class Provenance(BaseModel):
    """Where the posts of the demo come from, and how they were drawn."""

    dataset: str | None
    source_url: str | None
    revision: str | None
    files: list[str]
    licence: str | None
    # How the sample was drawn (`pipelines/sample`): seed, unit, what it was drawn from.
    sample: dict[str, object] | None


class Document(BaseModel):
    """A file of the repository shown as it is: an annotation guide, the report, the journal."""

    name: str
    title: str
    # Path in the repository, for the link to the source.
    path: str
    markdown: str


class LabelDoc(BaseModel):
    name: str
    family: str
    # What the label is for: probe, descriptor, llm_test, auxiliary.
    use: str
    values: list[str]
    # The closed question the annotators answered, from the guide of its family.
    question: str | None
    # What became of it: shown, review-only, dropped; null while it has no evaluation.
    state: str | None


class TechniqueDoc(BaseModel):
    key: str
    name: str
    question: str | None


class ReviewDoc(BaseModel):
    """The LLM review as it runs: nothing is paraphrased, the prompt is the one sent."""

    model: str | None
    prompt_version: str
    system: str
    # The techniques the review screens every reviewed item for.
    techniques: list[TechniqueDoc]
    # The review of a group of items: a selection of the map, a zone.
    selection_prompt_version: str
    selection_system: str
    # The context the review of one item reads: its nearest items, other items of its actor.
    neighbours: int
    actor_items: int
    # How a selection is read: posts sampled at most, of one actor at most, characters of each.
    selection_posts: int
    selection_posts_per_actor: int
    selection_post_chars: int


class LabelledSummary(BaseModel):
    """The posts the annotators read, as shipped beside the demo build. A post read in two
    rounds counts once for each."""

    posts: int
    # The labels that have a settled answer on at least one post.
    labels: list[str]
    splits: dict[str, int]
    # The rounds in the order they were drawn.
    rounds: list[str]
    # What each round is: `annotation`, or `second reader` when it holds posts of other rounds
    # read again by another model. A second reading settles nothing: its posts have no answer.
    round_kinds: dict[str, str]
    # Posts per kind of round.
    kinds: dict[str, int]


class Method(BaseModel):
    commit: str
    repository: str
    build: BuildFacts | None
    provenance: Provenance | None
    labels: list[LabelDoc]
    guides: list[Document]
    documents: list[Document]
    # Names of the figures of the report, served at `method/figures/{name}`.
    figures: list[str]
    # The other files of the probe evaluation (`reports/probes/*.json` but `metrics.json`,
    # which `GET /metrics` serves), as written, under the name of the file without `.json`.
    probe_files: dict[str, object]
    review: ReviewDoc | None
    labelled: LabelledSummary | None


class Reading(BaseModel):
    """What one annotator answered on one post, with the span it quoted for each yes."""

    # The batch the annotator read (round, family, reading, number): one fresh agent per batch.
    # A post is read twice, `a` and `b`, and a third time, `c`, where the two disagreed.
    reader: str
    answers: dict[str, Answer]
    quotes: dict[str, str]


class LabelledPost(BaseModel):
    """One post as it was read in one round. A post read in two rounds appears once for each."""

    # The name the campaign gives the post: "<build>:<row in the build>".
    id: str
    text: str
    split: str
    round: str
    # The kind of its round: `annotation` or `second reader`.
    kind: str
    # Why the post was drawn: `random`, `enrich:<label>:<source>`, `band:<label>:<n>` (several
    # joined by `|`) or `audit:<label>`. Only the random ones are a sample of the corpus.
    stratum: str
    # The settled answer per label, after the readings were compared. Empty for a second
    # reading, which is never mixed with the answers of the annotators.
    answers: dict[str, Answer]
    readings: list[Reading]
    # The score of each probe shown, computed now from the vector of the post.
    scores: dict[str, float]


class LabelledPage(BaseModel):
    total: int
    posts: list[LabelledPost]
