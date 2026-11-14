"""The label set of the probe campaign. One definition: the guides, the batch writer, the label
parser and the trainer all read it. The wording of each question is in `docs/probes/guides/`.
"""

from dataclasses import dataclass

YES, NO, UNCLEAR = "yes", "no", "unclear"
BINARY = (YES, NO, UNCLEAR)

# What a label is for. A `probe` is a candidate detector. A `descriptor` describes a group or
# stratifies a measure. An `llm_test` label is kept to test the LLM review pass later. An
# `auxiliary` label explains errors or triggers abstention.
PROBE, DESCRIPTOR, LLM_TEST, AUXILIARY = "probe", "descriptor", "llm_test", "auxiliary"

LANGS = ("en", "de", "es", "fr", "pt", "it", "nl", "tr", "ar", "ja", "ru", "hi", "id")
LANG_VALUES = (*LANGS, "other", "none")
# Order matters: when two themes fit, the annotator takes the first one in this list.
THEMES = (
    "war_geopolitics",
    "migration",
    "crime_justice",
    "health",
    "climate_energy",
    "economy_work",
    "society_identity",
    "religion",
    "media_tech",
    "politics_government",
    "sport",
    "entertainment_culture",
    "everyday_personal",
    "other",
)
SIDES = ("left", "right", "none")


@dataclass(frozen=True)
class Label:
    name: str
    family: str
    use: str
    values: tuple[str, ...] = BINARY
    # A "yes" must come with the exact span of the post that shows it.
    quoted: bool = True

    @property
    def binary(self) -> bool:
        return self.values == BINARY


def _family(family: str, *rows: tuple[str, str] | tuple[str, str, bool]) -> tuple[Label, ...]:
    return tuple(Label(row[0], family, row[1], quoted=(row[2:] or (True,))[0]) for row in rows)


LABELS: tuple[Label, ...] = (
    *_family(
        "calls",
        ("call_amplify", PROBE),
        ("call_pressure", PROBE),
        ("call_protest", PROBE),
        ("call_boycott", PROBE),
        ("call_vote", PROBE),
        ("call_join", PROBE),
        ("call_overthrow", PROBE),
        ("call_violence", PROBE),
    ),
    *_family(
        "hostility",
        ("attack_addressee", PROBE),
        ("attack_person", PROBE),
        ("attack_identity_group", PROBE),
        ("attack_political_group", PROBE),
        ("dehumanisation", PROBE),
        ("threat", PROBE),
        ("violence_endorsement", PROBE),
        ("doxxing", LLM_TEST),
        ("profanity", DESCRIPTOR),
    ),
    *_family(
        "rhetoric",
        ("loaded_language", PROBE),
        ("exaggeration", PROBE),
        ("fear_appeal", PROBE),
        ("doubt", PROBE),
        ("identity_appeal", PROBE),
        ("us_vs_them", PROBE),
        ("slogan", PROBE),
    ),
    *_family(
        "fallacies",
        ("bandwagon", LLM_TEST),
        ("authority_appeal", LLM_TEST),
        ("unnamed_authority", LLM_TEST),
        ("whataboutism", LLM_TEST),
        ("straw_man", LLM_TEST),
        ("false_dilemma", LLM_TEST),
        ("causal_oversimplification", LLM_TEST),
        ("thought_terminating_cliche", LLM_TEST),
        ("nazi_comparison", LLM_TEST),
    ),
    *_family(
        "solicitation",
        ("commercial_promo", PROBE),
        ("money_request", PROBE),
        ("gain_promise", PROBE),
        ("engagement_bait", PROBE),
        ("off_platform_redirect", PROBE),
        ("adult_promo", PROBE),
        ("testimonial", PROBE),
    ),
    *_family(
        "format",
        ("news_headline", PROBE, False),
        ("automated_alert", PROBE, False),
        ("templated_post", PROBE, False),
        ("quote_post", PROBE, False),
        ("reported_speech", AUXILIARY, False),
        ("irony", AUXILIARY, False),
        ("not_enough_text", AUXILIARY, False),
    ),
    Label("lang", "format", PROBE, LANG_VALUES, quoted=False),
    *_family(
        "subject",
        ("political", DESCRIPTOR, False),
        ("anti_pluralism", DESCRIPTOR),
        ("institution_distrust", PROBE),
        ("conspiracy_narrative", PROBE),
        ("endorsement", PROBE),
    ),
    Label("theme", "subject", DESCRIPTOR, THEMES, quoted=False),
    Label("political_side", "subject", DESCRIPTOR, SIDES, quoted=False),
    *_family(
        "claims",
        ("checkable_claim", PROBE),
        ("unsourced_statistic", PROBE),
        ("hearsay", LLM_TEST),
        ("urgency_framing", PROBE),
    ),
    *_family(
        "emotion",
        ("anger", DESCRIPTOR, False),
        ("fear", DESCRIPTOR, False),
        ("contempt", DESCRIPTOR, False),
        ("enthusiasm", DESCRIPTOR, False),
    ),
)

FAMILIES: tuple[str, ...] = tuple(dict.fromkeys(label.family for label in LABELS))
BY_NAME: dict[str, Label] = {label.name: label for label in LABELS}


def family_labels(family: str) -> tuple[Label, ...]:
    return tuple(label for label in LABELS if label.family == family)
