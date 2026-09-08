"""GET /version — which commit this instance is actually running.

The frontend and backend deploy independently (Pages and Render), so they can
drift from each other as easily as from local. Without this, confirming a fix is
live means guessing from behaviour.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

from models.version import VersionResponse

router = APIRouter(tags=["meta"])

# Render sets RENDER_GIT_COMMIT on every deploy with no configuration needed;
# the others are the equivalents on common alternatives, checked in order.
_COMMIT_ENV_VARS = ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_COMMIT")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        timeout=2,
        check=True,
    )
    return result.stdout.strip()


@lru_cache(maxsize=1)
def _resolve_commit() -> tuple[str, str]:
    """Return (commit, source). Cached: it cannot change while the process runs."""
    for var in _COMMIT_ENV_VARS:
        commit = os.environ.get(var)
        if commit:
            return commit, var

    # Local dev has no such env var but does have a working tree. A deployed
    # image usually has neither, which is why this is the fallback and not the
    # primary path.
    try:
        commit = _git("rev-parse", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return "unknown", "unavailable"

    # Uncommitted edits are the normal local state, and without this marker the
    # endpoint reports a commit whose code isn't actually what's running.
    # Deploys build from a clean checkout, so they never carry the suffix.
    # Deliberately not `git describe --dirty`: once the milestone tags in
    # BACKLOG.md exist, describe would return a tag name instead of a SHA.
    try:
        if _git("status", "--porcelain"):
            commit += "-dirty"
    except (OSError, subprocess.SubprocessError):
        pass  # Couldn't tell; report the plain commit rather than guessing.

    return commit, "git"


_DIRTY = "-dirty"


def _shorten(commit: str) -> str:
    """Abbreviate without losing the dirty marker — the marker is the point."""
    if commit.endswith(_DIRTY):
        return commit[: -len(_DIRTY)][:7] + _DIRTY
    return commit[:7]


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    commit, source = _resolve_commit()
    return VersionResponse(commit=commit, short=_shorten(commit), source=source)
