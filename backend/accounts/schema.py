"""Getting a workspace and its key. There is no account: the API key is the only credential,
and the dashboard and the API both send it as a bearer token.
"""

from pydantic import BaseModel

from backend.workspace.schema import Limits, WorkspaceInfo


class WorkspaceCreated(BaseModel):
    """The key is shown once: the server keeps only its hash."""

    api_key: str
    workspace: WorkspaceInfo


class KeyRotated(BaseModel):
    api_key: str


class PublicConfig(BaseModel):
    """What the page needs before a workspace exists."""

    limits: Limits
    # Whether an LLM is configured: without one, zones keep their words and nothing is reviewed.
    llm: bool
    possible_score: float
    probable_score: float
