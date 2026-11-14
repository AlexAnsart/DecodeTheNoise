"""Item content, fetched by point index for tooltips, cards and lists."""

from pydantic import BaseModel, Field

MAX_ITEMS_PER_REQUEST = 200

AttrValue = str | int | float | bool | None


class Item(BaseModel):
    index: int
    item_id: str
    actor_id: str
    text: str
    created_at: int | None  # milliseconds since the epoch
    lang: str | None
    repost_of: str | None
    urls: list[str]
    attrs: dict[str, AttrValue]


class ItemsRequest(BaseModel):
    indices: list[int] = Field(max_length=MAX_ITEMS_PER_REQUEST)


class ItemsResponse(BaseModel):
    items: list[Item]
