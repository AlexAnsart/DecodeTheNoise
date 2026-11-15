"""The method of the review, as it runs: for the method page, so that what the page says is what
the model is sent."""

from pydantic import BaseModel

from backend.review.guides import Guides
from backend.review.prompt import MAX_ACTOR_ITEMS, MAX_NEIGHBOURS, PROMPT_VERSION, system_prompt
from backend.review.selection import PER_ACTOR
from backend.review.selection_prompt import (
    MAX_POSTS,
    POST_CHARS,
    SELECTION_VERSION,
    selection_system,
)


class ScreenedTechnique(BaseModel):
    key: str
    name: str
    # The closed question of the annotation guide.
    question: str
    family: str


class ReviewMethod(BaseModel):
    prompt_version: str
    # The system prompt of the item review, word for word as the model receives it.
    system_prompt: str
    selection_prompt_version: str
    selection_system_prompt: str
    # The techniques every reviewed item is screened for. Empty without the guides.
    techniques: list[ScreenedTechnique]
    # How much context an item review reads, and how a selection is sampled.
    neighbours: int
    actor_items: int
    selection_posts: int
    selection_posts_per_actor: int
    selection_post_chars: int


def describe_method(guides: Guides) -> ReviewMethod:
    return ReviewMethod(
        prompt_version=PROMPT_VERSION,
        system_prompt=system_prompt(guides),
        selection_prompt_version=SELECTION_VERSION,
        selection_system_prompt=selection_system(guides),
        techniques=[
            ScreenedTechnique(
                key=label.key, name=label.name, question=label.question, family=label.family
            )
            for label in guides.screened()
        ],
        neighbours=MAX_NEIGHBOURS,
        actor_items=MAX_ACTOR_ITEMS,
        selection_posts=MAX_POSTS,
        selection_posts_per_actor=PER_ACTOR,
        selection_post_chars=POST_CHARS,
    )
