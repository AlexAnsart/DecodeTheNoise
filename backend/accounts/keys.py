"""API keys and workspace ids. The server keeps the hash of a key, never the key."""

import hashlib
import secrets

KEY_PREFIX = "nm_"


def new_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(24)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def new_workspace_id() -> str:
    return "ws_" + secrets.token_hex(6)
