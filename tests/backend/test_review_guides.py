from pathlib import Path

import pytest
from review_fakes import write_guides

from backend.review.guides import NO_GUIDES, load_guides
from backend.review.method import describe_method

REAL_GUIDES = Path("docs/probes/guides")


def test_guides_are_read_label_by_label(tmp_path: Path) -> None:
    guides = load_guides(write_guides(tmp_path))

    assert list(guides.families) == ["calls", "fallacies", "format", "rhetoric", "subject"]
    loaded = guides.labels["loaded_language"]
    assert (loaded.family, loaded.name) == ("rhetoric", "Loaded language")
    assert loaded.question.startswith("Does the post name something with a charged word")
    assert loaded.section.startswith("## `loaded_language`")
    assert loaded.section.endswith("- the word is a plain evaluation.")
    # The section is word for word: it stops where the next label starts.
    assert "fear_appeal" not in loaded.section
    assert loaded.shared and loaded.evidence
    # `unnamed_authority` leans on another label, not on the condition its family shares.
    assert not guides.labels["unnamed_authority"].shared
    assert guides.label("theme:sport") is guides.labels["theme"]
    assert guides.label("unknown") is None


def test_evidence_follows_what_each_guide_says(tmp_path: Path) -> None:
    guides = load_guides(write_guides(tmp_path))

    needs_span = {key: label.evidence for key, label in guides.labels.items()}

    assert needs_span["call_amplify"] and needs_span["whataboutism"]
    assert not needs_span["news_headline"] and not needs_span["lang"]
    assert needs_span["endorsement"]
    assert not needs_span["political"] and not needs_span["theme"]


def test_common_rules_leave_out_the_annotators_answer_format(tmp_path: Path) -> None:
    common = load_guides(write_guides(tmp_path)).common

    assert common.startswith("You annotate short posts.")
    assert "## 3. Own voice" in common
    assert "How to work" not in common and "Your answer" not in common


def test_techniques_screened_are_the_two_technique_guides(tmp_path: Path) -> None:
    guides = load_guides(write_guides(tmp_path))

    keys = [label.key for label in guides.screened()]

    assert keys == ["loaded_language", "fear_appeal", "whataboutism", "unnamed_authority"]


def test_material_gives_the_sections_of_labels_that_are_not_techniques(tmp_path: Path) -> None:
    guides = load_guides(write_guides(tmp_path))

    material = guides.material(["call_amplify", "lang:en", "loaded_language", "unknown"])

    assert material.startswith("### Guide: calls\n\nThis guide has one label.")
    assert "## Shared condition C: the post makes a request" in material
    assert "## `call_amplify`" in material
    # The notes of a guide travel with its sections; a guide without a shared condition adds none.
    assert "### Guide: format\n\nRule 3 of `common.md` (own voice) does not apply" in material
    assert "## `lang`" in material and "news_headline" not in material
    # Techniques are in the system prompt already.
    assert "loaded_language" not in material
    assert guides.material(["loaded_language"]) == ""


def test_without_the_folder_there_is_no_guide(tmp_path: Path) -> None:
    guides = load_guides(tmp_path / "absent")

    assert guides is NO_GUIDES
    assert guides.screened() == () and guides.label("loaded_language") is None
    assert describe_method(guides).techniques == []


def test_the_method_page_gets_the_prompts_as_sent(tmp_path: Path) -> None:
    method = describe_method(load_guides(write_guides(tmp_path)))

    assert (
        method.prompt_version == "review-v2" and method.selection_prompt_version == "selection-v1"
    )
    assert method.system_prompt.startswith("You review one item")
    assert method.selection_system_prompt.startswith("You read a sample of posts")
    assert [(t.key, t.name, t.family) for t in method.techniques][:2] == [
        ("loaded_language", "Loaded language", "rhetoric"),
        ("fear_appeal", "Fear appeal", "rhetoric"),
    ]
    assert method.techniques[2].question.startswith("Does the post answer a criticism")


@pytest.mark.skipif(not REAL_GUIDES.is_dir(), reason="the annotation guides are not here")
def test_the_real_guides_are_read_whole() -> None:
    guides = load_guides(REAL_GUIDES)

    assert len(guides.labels) == 63 and len(guides.families) == 9
    assert all(label.question for label in guides.labels.values())
    screened = [label.key for label in guides.screened()]
    assert len(screened) == 16
    assert {"whataboutism", "unnamed_authority", "loaded_language", "fear_appeal"} <= set(screened)
    assert guides.labels["whataboutism"].question.startswith("Does the post answer a criticism")
    assert guides.families["calls"].condition.startswith("## Shared condition C")
    assert "How to work" not in guides.common and "## 3. Own voice" in guides.common
