"""The LLM review as the method page shows it: the prompts as they are sent, their versions,
the techniques every reviewed item is screened for and how much context is read.

Everything is asked to the review that runs on this server, with the guides it loaded, so the
page cannot say something else than what the model is sent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.method.schema import ReviewDoc, TechniqueDoc

if TYPE_CHECKING:
    from backend.review.engine import Reviewer


def review_of(reviewer: Reviewer | None) -> ReviewDoc | None:
    """Null on a server that runs no review, or whose review does not describe its method."""
    if reviewer is None:
        return None
    try:
        from backend.review.method import describe_method
    except ImportError:
        return None
    described = describe_method(reviewer.guides)
    return ReviewDoc(
        model=reviewer.model or None,
        prompt_version=described.prompt_version,
        system=described.system_prompt,
        techniques=[
            TechniqueDoc(key=found.key, name=found.name, question=found.question or None)
            for found in described.techniques
        ],
        selection_prompt_version=described.selection_prompt_version,
        selection_system=described.selection_system_prompt,
        neighbours=described.neighbours,
        actor_items=described.actor_items,
        selection_posts=described.selection_posts,
        selection_posts_per_actor=described.selection_posts_per_actor,
        selection_post_chars=described.selection_post_chars,
    )
