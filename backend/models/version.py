"""Response body for GET /version."""

from __future__ import annotations

from pydantic import BaseModel


class VersionResponse(BaseModel):
    commit: str
    short: str
    # Where the commit came from (env var name, "git", or "unavailable") — the
    # difference between "deployed build" and "someone's laptop" is worth seeing.
    source: str
