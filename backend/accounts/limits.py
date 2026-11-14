"""What a workspace may use. Free, but the server is small and the LLM balance is shared."""

from backend.ingest.schema import MAX_BATCH_ITEMS, MAX_TEXT_CHARS
from backend.workspace.schema import Limits

# Posts are embedded on the two cores of the server, at about eight a second (measured on the
# server, reports/verda.md): a thousand posts are about two minutes of work.
LIMITS = Limits(
    items=1_000,
    batch_items=MAX_BATCH_ITEMS,
    requests_per_minute=300,
    reviews_per_day=1_000,
    text_chars=MAX_TEXT_CHARS,
)

# Zone names asked to the LLM, per workspace and per day.
NAMES_PER_DAY = 500
# All workspaces together, per day: the stop that protects the shared balance.
ALL_WORKSPACES = "*"
GLOBAL_REVIEWS_PER_DAY = 10_000
GLOBAL_NAMES_PER_DAY = 5_000

# Workspaces one address may create, per day. A whole venue can sit behind one address.
CREATIONS_PER_DAY = 200
BATCHES_PER_MINUTE = 30
# A thousand posts are well under a megabyte, and long texts fit too. Beyond this the request
# is refused unread.
MAX_BATCH_BYTES = 32 * 1024 * 1024

REVIEWS = "reviews"
NAMES = "names"
