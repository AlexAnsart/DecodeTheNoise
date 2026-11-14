"""Request dependencies of the workspace routes: who is asking, and with what."""

from fastapi import HTTPException, Request

from backend.accounts.limits import BATCHES_PER_MINUTE, MAX_BATCH_BYTES
from backend.analyze.rate_limit import RateLimiter
from backend.services import Services
from backend.workspace.state import Workspace

_SCHEME = "bearer "
UNAUTHORISED = (
    "This route needs a workspace key: send the header 'Authorization: Bearer <your key>'."
)


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


def require_workspace(request: Request) -> None:
    """Finds the workspace of the key in the request, and keeps it for the routes."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith(_SCHEME):
        raise HTTPException(status_code=401, detail=UNAUTHORISED)
    services = get_services(request)
    account = services.accounts.by_key(header[len(_SCHEME) :].strip())
    if account is None:
        raise HTTPException(status_code=401, detail="This workspace key is not known.")
    request.state.workspace = services.workspaces.of(account)


def get_workspace(request: Request) -> Workspace:
    workspace: Workspace = request.state.workspace
    return workspace


def _too_many(limit: int, what: str) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=f"Too many {what}: at most {limit} a minute for this workspace. Try again shortly.",
        headers={"Retry-After": "10"},
    )


def limit_items(request: Request) -> None:
    """The per-minute limit of the workspace on posts sent one by one."""
    limiter: RateLimiter = request.app.state.item_limiter
    if not limiter.allow(get_workspace(request).id):
        raise _too_many(limiter.limit, "posts")


def limit_batches(request: Request) -> None:
    length = request.headers.get("content-length", "")
    if not length.isdigit() or int(length) > MAX_BATCH_BYTES:
        megabytes = MAX_BATCH_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413, detail=f"A batch is at most {megabytes} MB. Send it in several parts."
        )
    limiter: RateLimiter = request.app.state.batch_limiter
    if not limiter.allow(get_workspace(request).id):
        raise _too_many(BATCHES_PER_MINUTE, "batches")
