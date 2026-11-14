"""Makes a subject fictional: the same kind of debate, with invented proper names.

A synthetic post must not be usable in a real debate, and no real person is the target of one.
One LLM call per subject, pinned and cached.
"""

import logging

from pydantic import BaseModel, ValidationError

from pipelines.briefs.llm import CachedChat

log = logging.getLogger("briefs.fiction")

PROMPT_VERSION = "brief-fiction-v2"
FICTION_SYSTEM = (
    "You rewrite debate subjects for a research benchmark so that no synthetic post can be "
    "dropped into a real debate. Answer with one JSON object and nothing else."
)
FICTION_USER = """Subject: {subject}
Opinion for: {position_for}
Opinion against: {position_against}

Rewrite the three lines by changing proper names only. The setting stays the present day and
every ordinary word stays as it is (football, crypto, inflation, the government, a tennis
tournament). Replace each real person, team, club, company, product, show, place, institution,
law or event with an invented, plausible modern name that belongs to no real one. If you need a
town, region or country, call it {place}. If the subject names nothing real, tie it to {place}
or to one invented company, so that it is fictional too.

Return a JSON object with the keys "subject", "position_for" and "position_against"."""
# One invented place per topic, so that two topics do not end up in the same town.
PLACES = (
    "Marlow Ridge",
    "Kestrel Bay",
    "Dunmore Falls",
    "Ashby Vale",
    "Port Hallam",
    "Linden Cross",
    "Harrow Creek",
    "Welby Heights",
    "Thornbury Lake",
    "Carrow Point",
    "Eskdale Springs",
    "Calder Wells",
    "Fenwick Shore",
    "Tolland Green",
    "Larkfield Junction",
    "Pennholt",
    "Greyling Harbour",
    "Norbury Sands",
    "Halvern",
    "Ostrava Bay",
    "Merrowdale",
    "Quillon",
    "Brightwater Gap",
    "Sandover",
)


class Topic(BaseModel):
    """One subject of the benchmark: fictional, in the mould of the pool named by `id`."""

    id: str
    pool_subject: str
    subject: str
    position_for: str
    position_against: str


def fictional(
    chat: CachedChat, pool: str, subject: str, position_for: str, position_against: str, place: str
) -> Topic | None:
    asked = FICTION_USER.format(
        subject=subject, position_for=position_for, position_against=position_against, place=place
    )
    reply = chat.ask(FICTION_SYSTEM, asked, max_tokens=1200)
    try:
        return Topic(id=pool, pool_subject=subject, **reply.data)
    except (ValidationError, TypeError):
        log.warning("pool %s: unusable fiction %s", pool, reply.data)
        return None
