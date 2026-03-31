"""Shared constants, types, and write-gate for Todoist Blade MCP server."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API hosts
# ---------------------------------------------------------------------------

REST_BASE_URL = "https://api.todoist.com/rest/v2"
SYNC_BASE_URL = "https://api.todoist.com/sync/v9"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Default limit for list operations (token efficiency)
DEFAULT_LIMIT = 20

# Maximum batch size for sync commands (Todoist limit is 100)
MAX_BATCH_SIZE = 100

# Maximum description length in list views (characters)
MAX_DESCRIPTION_CHARS = 200

# Maximum body chars for full task read
MAX_BODY_CHARS = 50_000

# Sync token for initial full sync
INITIAL_SYNC_TOKEN = "*"

# ---------------------------------------------------------------------------
# Priority mapping (Todoist: 1=normal, 4=urgent; display: p1=urgent, p4=normal)
# ---------------------------------------------------------------------------

PRIORITY_DISPLAY = {
    4: "p1",  # Urgent
    3: "p2",  # High
    2: "p3",  # Medium
    1: "p4",  # Normal (default)
}

PRIORITY_LABELS = {
    4: "urgent",
    3: "high",
    2: "medium",
    1: "normal",
}

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TodoistError(Exception):
    """Base exception for Todoist client errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.details = details


class AuthError(TodoistError):
    """Authentication failed — invalid or expired token."""


class NotFoundError(TodoistError):
    """Requested resource (task, project, etc.) not found."""


class RateLimitError(TodoistError):
    """Rate limit exceeded — back off and retry."""


class ConnectionError(TodoistError):  # noqa: A001
    """Cannot connect to Todoist API."""


class WriteDisabledError(TodoistError):
    """Write operation attempted but TODOIST_WRITE_ENABLED is not true."""


class ValidationError(TodoistError):
    """Request validation failed — invalid parameters."""


class SyncError(TodoistError):
    """Sync API returned an error for one or more commands."""


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

_ERROR_PATTERNS: list[tuple[str, type[TodoistError]]] = [
    ("unauthorized", AuthError),
    ("authentication", AuthError),
    ("invalid token", AuthError),
    ("forbidden", AuthError),
    ("not found", NotFoundError),
    ("does not exist", NotFoundError),
    ("no such", NotFoundError),
    ("rate limit", RateLimitError),
    ("too many requests", RateLimitError),
    ("connection", ConnectionError),
    ("timeout", ConnectionError),
    ("unreachable", ConnectionError),
    ("timed out", ConnectionError),
    ("validation", ValidationError),
    ("invalid", ValidationError),
]


def classify_error(message: str, status_code: int | None = None) -> TodoistError:
    """Map error message and/or HTTP status to a typed exception."""
    if status_code == 401 or status_code == 403:
        return AuthError(message)
    if status_code == 404:
        return NotFoundError(message)
    if status_code == 429:
        return RateLimitError(message)
    if status_code == 400:
        return ValidationError(message)

    lower = message.lower()
    for pattern, exc_cls in _ERROR_PATTERNS:
        if pattern in lower:
            return exc_cls(message)
    return TodoistError(message)


def scrub_token(text: str) -> str:
    """Remove API tokens from text to prevent leakage in logs/output."""
    return re.sub(r"[0-9a-f]{40}", "****", text)


# ---------------------------------------------------------------------------
# Write gate
# ---------------------------------------------------------------------------


def is_write_enabled() -> bool:
    """Check if write operations are enabled via env var."""
    return os.environ.get("TODOIST_WRITE_ENABLED", "").lower() == "true"


def require_write() -> str | None:
    """Return an error message if writes are disabled, else None."""
    if not is_write_enabled():
        return "Error: Write operations are disabled. Set TODOIST_WRITE_ENABLED=true to enable."
    return None
