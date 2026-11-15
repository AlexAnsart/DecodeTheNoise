import json
from pathlib import Path

import pytest
from method_fakes import FLAGGED, NOT_FLAGGED, MethodApi, method_api, post, write_posts

from backend.method.labelled import SECOND_READER

LABELLED = "/api/method/labelled"
# For each post: what `call_vote` and `theme:sport` output on it.
POSTS = [
    (post("tiny:0", "Vote for her on Sunday", {"call_vote": "yes"}), [FLAGGED, NOT_FLAGGED]),
    (post("tiny:1", "Vote early, vote often", {"call_vote": "yes"}), [NOT_FLAGGED, NOT_FLAGGED]),
    (post("tiny:2", "What a match", {"call_vote": "no", "theme": "sport"}), [4.0, FLAGGED]),
    (
        post("tiny:3", "Rain again", {"call_vote": "unclear", "theme": "other"}, split="test"),
        [FLAGGED, FLAGGED],
    ),
    (
        post("tiny:4", "50% off today", {"theme": "other"}, round_name="e1_subject"),
        [NOT_FLAGGED, NOT_FLAGGED],
    ),
    (
        post("tiny:0", "Vote for her on Sunday", {}, round_name="a1_calls", kind=SECOND_READER),
        [FLAGGED, NOT_FLAGGED],
    ),
]


@pytest.fixture
def api(tmp_path: Path) -> MethodApi:
    served = method_api(tmp_path)
    write_posts(served, POSTS)
    return served


def _ids(api: MethodApi, **params: str | int) -> list[str]:
    response = api.client.get(LABELLED, params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= len(body["posts"])
    return [f"{found['id']}@{found['round']}" for found in body["posts"]]


def test_a_page_holds_the_posts_in_file_order_with_their_readings_and_scores(
    api: MethodApi,
) -> None:
    body = api.client.get(LABELLED, params={"limit": 2, "offset": 1}).json()

    assert body["total"] == 6
    assert [found["id"] for found in body["posts"]] == ["tiny:1", "tiny:2"]
    second = body["posts"][1]
    assert second["answers"] == {"call_vote": "no", "theme": "sport"}
    assert second["readings"][0]["reader"] == "m1-calls-a-001"
    assert second["kind"] == "annotation"
    assert second["stratum"] == "random"
    assert second["scores"]["call_vote"] >= 0.8
    assert second["scores"]["theme:sport"] >= 0.8
    assert body["posts"][0]["scores"]["call_vote"] < 0.5


def test_plain_filters_keep_their_posts(api: MethodApi) -> None:
    assert _ids(api, label="call_vote", answer="yes") == ["tiny:0@m1", "tiny:1@m1"]
    # A label alone keeps the posts that have an answer on it.
    assert _ids(api, label="theme") == ["tiny:2@m1", "tiny:3@m1", "tiny:4@e1_subject"]
    assert _ids(api, label="theme", answer="other", split="test") == ["tiny:3@m1"]
    assert _ids(api, round="e1_subject") == ["tiny:4@e1_subject"]
    assert _ids(api, kind="second reader") == ["tiny:0@a1_calls"]
    assert _ids(api, q="vote sunday", kind="annotation") == ["tiny:0@m1"]
    # `%` is a character of the text here, not a wildcard.
    assert _ids(api, q="50%") == ["tiny:4@e1_subject"]
    assert _ids(api, q="5%f") == []
    assert _ids(api, label="no_such_label") == []


def test_a_probe_is_compared_with_the_settled_answer_on_its_own_label(api: MethodApi) -> None:
    # The second reading of tiny:0 settles nothing: no level counts it.
    assert _ids(api, probe="call_vote", level="flagged") == ["tiny:2@m1", "tiny:0@m1"]
    assert _ids(api, probe="call_vote", level="agreed") == ["tiny:0@m1"]
    assert _ids(api, probe="call_vote", level="false alarm") == ["tiny:2@m1"]
    assert _ids(api, probe="call_vote", level="missed") == ["tiny:1@m1"]
    # The probe of one answer of a label is right when that answer was settled.
    assert _ids(api, probe="theme:sport", level="agreed") == ["tiny:2@m1"]
    assert _ids(api, probe="theme:sport", level="false alarm") == ["tiny:3@m1"]
    assert _ids(api, probe="theme:sport", level="missed") == []
    # Without a level, every post kept by the other filters, the highest score first.
    assert _ids(api, probe="call_vote", split="train", kind="annotation")[0] == "tiny:2@m1"
    assert len(_ids(api, probe="call_vote")) == 6


def test_what_cannot_be_asked_is_refused(api: MethodApi) -> None:
    assert api.client.get(LABELLED, params={"probe": "nope"}).status_code == 404
    assert api.client.get(LABELLED, params={"limit": 101}).status_code == 422
    assert (
        api.client.get(LABELLED, params={"level": "wrong", "probe": "call_vote"}).status_code == 422
    )
    # A level without a probe compares nothing: it is not applied.
    assert len(_ids(api, level="missed")) == 6


def test_probes_do_not_read_vectors_of_another_model(tmp_path: Path) -> None:
    api = method_api(tmp_path)
    write_posts(api, POSTS, embedding_key="another-model@1|prefix=''|dims=4")

    listed = api.client.get(LABELLED).json()
    refused = api.client.get(LABELLED, params={"probe": "call_vote"})

    assert listed["total"] == 6
    assert all(found["scores"] == {} for found in listed["posts"])
    assert refused.status_code == 409


def test_the_download_is_every_post_as_json_lines(api: MethodApi) -> None:
    response = api.client.get("/api/method/labelled.jsonl")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="labelled.jsonl"'
    lines = [json.loads(line) for line in response.text.split("\n") if line]
    assert [line["id"] for line in lines] == [record.id for record, _ in POSTS]
    assert lines[2] == {
        "id": "tiny:2",
        "text": "What a match",
        "split": "train",
        "round": "m1",
        "kind": "annotation",
        "stratum": "random",
        "answers": {"call_vote": "no", "theme": "sport"},
        "readings": [
            {
                "reader": "m1-calls-a-001",
                "answers": {"call_vote": "no", "theme": "sport"},
                "quotes": {},
            }
        ],
    }
    assert lines[5]["kind"] == "second reader"
    assert lines[5]["answers"] == {}


def test_without_the_file_there_is_no_post_and_nothing_to_download(tmp_path: Path) -> None:
    api = method_api(tmp_path)

    assert api.client.get(LABELLED, params={"probe": "call_vote"}).json() == {
        "total": 0,
        "posts": [],
    }
    assert api.client.get("/api/method/labelled.jsonl").status_code == 404


def test_the_file_can_be_replaced_while_the_server_runs(api: MethodApi) -> None:
    assert api.client.get(LABELLED).json()["total"] == 6

    write_posts(api, POSTS[:2])

    assert api.client.get(LABELLED).json()["total"] == 2
    assert _ids(api, probe="call_vote", level="agreed") == ["tiny:0@m1"]
    assert api.client.get("/api/method").json()["labelled"]["posts"] == 2
