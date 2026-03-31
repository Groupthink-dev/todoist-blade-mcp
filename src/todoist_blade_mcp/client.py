"""Todoist API client wrapper.

Wraps ``httpx`` with typed exceptions, pattern-based error classification,
and convenience methods for REST v2 and Sync v9 APIs. All methods are
synchronous — the server wraps them with ``asyncio.to_thread()``.

Dual-API strategy:
- REST v2: simple CRUD on individual resources, filter queries
- Sync v9: incremental sync (delta tokens), batch commands, stats
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import httpx

from todoist_blade_mcp.models import (
    DEFAULT_LIMIT,
    MAX_BATCH_SIZE,
    REST_BASE_URL,
    SYNC_BASE_URL,
    AuthError,
    NotFoundError,
    TodoistError,
    classify_error,
    scrub_token,
)

logger = logging.getLogger(__name__)

# Sync token cache directory
_CACHE_DIR = Path.home() / ".todoist-blade-mcp"


class TodoistClient:
    """Todoist API client with dual REST + Sync support.

    Wraps ``httpx.Client`` for REST v2 and Sync v9 APIs. All methods are
    synchronous — the MCP server's ``_run()`` helper wraps them in
    ``asyncio.to_thread()`` to avoid blocking the event loop.

    Args:
        api_token: Todoist API token. Defaults to ``TODOIST_API_TOKEN`` env var.
    """

    def __init__(self, api_token: str | None = None) -> None:
        token = api_token or os.environ.get("TODOIST_API_TOKEN", "")
        if not token:
            raise AuthError("TODOIST_API_TOKEN is not set")
        self._token = token
        self._rest = httpx.Client(
            base_url=REST_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        self._sync_client = httpx.Client(
            base_url=SYNC_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        self._sync_token: str | None = self._load_sync_token()
        logger.info("TodoistClient initialised")

    def close(self) -> None:
        """Close underlying HTTP clients."""
        self._rest.close()
        self._sync_client.close()

    # -------------------------------------------------------------------
    # HTTP helpers
    # -------------------------------------------------------------------

    def _rest_request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Execute a REST API request with error handling."""
        try:
            response = self._rest.request(method, path, **kwargs)
            if response.status_code >= 400:
                msg = scrub_token(response.text)
                raise classify_error(msg, response.status_code)
            return response
        except TodoistError:
            raise
        except httpx.HTTPError as e:
            msg = scrub_token(str(e))
            raise classify_error(msg) from e

    def _sync_request(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a Sync API request with error handling."""
        try:
            response = self._sync_client.post("/sync", json=kwargs)
            if response.status_code >= 400:
                msg = scrub_token(response.text)
                raise classify_error(msg, response.status_code)
            data: dict[str, Any] = response.json()
            # Update sync token if present
            if "sync_token" in data:
                self._sync_token = data["sync_token"]
                self._save_sync_token(data["sync_token"])
            return data
        except TodoistError:
            raise
        except httpx.HTTPError as e:
            msg = scrub_token(str(e))
            raise classify_error(msg) from e

    # -------------------------------------------------------------------
    # Sync token persistence
    # -------------------------------------------------------------------

    def _load_sync_token(self) -> str | None:
        """Load cached sync token from disk."""
        token_file = _CACHE_DIR / "sync_token"
        if token_file.exists():
            token = token_file.read_text().strip()
            if token:
                return token
        return None

    def _save_sync_token(self, token: str) -> None:
        """Persist sync token to disk."""
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / "sync_token").write_text(token)

    # -------------------------------------------------------------------
    # Projects (REST)
    # -------------------------------------------------------------------

    def list_projects(self) -> list[dict[str, Any]]:
        """Get all projects."""
        response = self._rest_request("GET", "/projects")
        projects: list[dict[str, Any]] = response.json()
        return projects

    def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a single project by ID."""
        response = self._rest_request("GET", f"/projects/{project_id}")
        project: dict[str, Any] = response.json()
        return project

    def create_project(
        self,
        name: str,
        parent_id: str | None = None,
        color: str | None = None,
        is_favorite: bool = False,
        view_style: str | None = None,
    ) -> dict[str, Any]:
        """Create a new project."""
        payload: dict[str, Any] = {"name": name}
        if parent_id:
            payload["parent_id"] = parent_id
        if color:
            payload["color"] = color
        if is_favorite:
            payload["is_favorite"] = True
        if view_style:
            payload["view_style"] = view_style
        response = self._rest_request("POST", "/projects", json=payload)
        project: dict[str, Any] = response.json()
        return project

    def update_project(self, project_id: str, **fields: Any) -> dict[str, Any]:
        """Update a project. Pass fields to update as kwargs."""
        payload = {k: v for k, v in fields.items() if v is not None}
        if not payload:
            raise TodoistError("No fields to update")
        response = self._rest_request("POST", f"/projects/{project_id}", json=payload)
        project: dict[str, Any] = response.json()
        return project

    def delete_project(self, project_id: str) -> None:
        """Delete a project."""
        self._rest_request("DELETE", f"/projects/{project_id}")

    def get_collaborators(self, project_id: str) -> list[dict[str, Any]]:
        """Get collaborators for a shared project."""
        response = self._rest_request("GET", f"/projects/{project_id}/collaborators")
        collabs: list[dict[str, Any]] = response.json()
        return collabs

    # -------------------------------------------------------------------
    # Sections (REST)
    # -------------------------------------------------------------------

    def list_sections(self, project_id: str | None = None) -> list[dict[str, Any]]:
        """Get sections, optionally filtered by project."""
        params: dict[str, str] = {}
        if project_id:
            params["project_id"] = project_id
        response = self._rest_request("GET", "/sections", params=params)
        sections: list[dict[str, Any]] = response.json()
        return sections

    def create_section(self, name: str, project_id: str, order: int | None = None) -> dict[str, Any]:
        """Create a new section in a project."""
        payload: dict[str, Any] = {"name": name, "project_id": project_id}
        if order is not None:
            payload["order"] = order
        response = self._rest_request("POST", "/sections", json=payload)
        section: dict[str, Any] = response.json()
        return section

    def update_section(self, section_id: str, name: str) -> dict[str, Any]:
        """Update a section name."""
        response = self._rest_request("POST", f"/sections/{section_id}", json={"name": name})
        section: dict[str, Any] = response.json()
        return section

    def delete_section(self, section_id: str) -> None:
        """Delete a section."""
        self._rest_request("DELETE", f"/sections/{section_id}")

    # -------------------------------------------------------------------
    # Tasks (REST)
    # -------------------------------------------------------------------

    def list_tasks(
        self,
        project_id: str | None = None,
        section_id: str | None = None,
        label: str | None = None,
        filter_query: str | None = None,
        ids: list[str] | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """List active tasks with optional filters.

        Uses the ``filter`` parameter for Todoist's filter query syntax
        (e.g. ``today & #Work``, ``overdue | p1``, ``@errands``).
        """
        params: dict[str, Any] = {}
        if project_id:
            params["project_id"] = project_id
        if section_id:
            params["section_id"] = section_id
        if label:
            params["label"] = label
        if filter_query:
            params["filter"] = filter_query
        if ids:
            params["ids"] = ",".join(ids)
        response = self._rest_request("GET", "/tasks", params=params)
        tasks: list[dict[str, Any]] = response.json()
        return tasks[:limit]

    def get_task(self, task_id: str) -> dict[str, Any]:
        """Get a single task by ID."""
        response = self._rest_request("GET", f"/tasks/{task_id}")
        task: dict[str, Any] = response.json()
        return task

    def create_task(
        self,
        content: str,
        description: str | None = None,
        project_id: str | None = None,
        section_id: str | None = None,
        parent_id: str | None = None,
        order: int | None = None,
        labels: list[str] | None = None,
        priority: int = 1,
        due_string: str | None = None,
        due_date: str | None = None,
        due_datetime: str | None = None,
        assignee_id: str | None = None,
        duration: int | None = None,
        duration_unit: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task.

        Priority: 1 (normal) to 4 (urgent).
        due_string: natural language (e.g. "tomorrow at 2pm").
        due_date: YYYY-MM-DD (all-day).
        due_datetime: RFC 3339 (e.g. "2026-04-01T14:00:00Z").
        """
        payload: dict[str, Any] = {"content": content, "priority": priority}
        if description:
            payload["description"] = description
        if project_id:
            payload["project_id"] = project_id
        if section_id:
            payload["section_id"] = section_id
        if parent_id:
            payload["parent_id"] = parent_id
        if order is not None:
            payload["order"] = order
        if labels:
            payload["labels"] = labels
        if due_string:
            payload["due_string"] = due_string
        elif due_date:
            payload["due_date"] = due_date
        elif due_datetime:
            payload["due_datetime"] = due_datetime
        if assignee_id:
            payload["assignee_id"] = assignee_id
        if duration is not None:
            payload["duration"] = duration
            payload["duration_unit"] = duration_unit or "minute"
        response = self._rest_request("POST", "/tasks", json=payload)
        task: dict[str, Any] = response.json()
        return task

    def update_task(self, task_id: str, **fields: Any) -> dict[str, Any]:
        """Update a task. Pass fields to update as kwargs."""
        payload = {k: v for k, v in fields.items() if v is not None}
        if not payload:
            raise TodoistError("No fields to update")
        response = self._rest_request("POST", f"/tasks/{task_id}", json=payload)
        task: dict[str, Any] = response.json()
        return task

    def close_task(self, task_id: str) -> None:
        """Complete/close a task."""
        self._rest_request("POST", f"/tasks/{task_id}/close")

    def reopen_task(self, task_id: str) -> None:
        """Reopen a completed task."""
        self._rest_request("POST", f"/tasks/{task_id}/reopen")

    def delete_task(self, task_id: str) -> None:
        """Delete a task permanently."""
        self._rest_request("DELETE", f"/tasks/{task_id}")

    def quick_add(self, text: str) -> dict[str, Any]:
        """Quick add a task using natural language parsing.

        Todoist parses project (#), label (@), priority (p1-p4), and date from text.
        """
        response = self._sync_client.post(
            "/quick/add",
            json={"text": text},
        )
        if response.status_code >= 400:
            raise classify_error(scrub_token(response.text), response.status_code)
        task: dict[str, Any] = response.json()
        return task

    # -------------------------------------------------------------------
    # Comments (REST)
    # -------------------------------------------------------------------

    def list_comments(
        self,
        task_id: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get comments for a task or project."""
        params: dict[str, str] = {}
        if task_id:
            params["task_id"] = task_id
        elif project_id:
            params["project_id"] = project_id
        else:
            raise TodoistError("Either task_id or project_id is required")
        response = self._rest_request("GET", "/comments", params=params)
        comments: list[dict[str, Any]] = response.json()
        return comments

    def create_comment(
        self,
        content: str,
        task_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a comment to a task or project."""
        payload: dict[str, Any] = {"content": content}
        if task_id:
            payload["task_id"] = task_id
        elif project_id:
            payload["project_id"] = project_id
        else:
            raise TodoistError("Either task_id or project_id is required")
        response = self._rest_request("POST", "/comments", json=payload)
        comment: dict[str, Any] = response.json()
        return comment

    def update_comment(self, comment_id: str, content: str) -> dict[str, Any]:
        """Update a comment's content."""
        response = self._rest_request("POST", f"/comments/{comment_id}", json={"content": content})
        comment: dict[str, Any] = response.json()
        return comment

    def delete_comment(self, comment_id: str) -> None:
        """Delete a comment."""
        self._rest_request("DELETE", f"/comments/{comment_id}")

    # -------------------------------------------------------------------
    # Labels (REST)
    # -------------------------------------------------------------------

    def list_labels(self) -> list[dict[str, Any]]:
        """Get all personal labels."""
        response = self._rest_request("GET", "/labels")
        labels: list[dict[str, Any]] = response.json()
        return labels

    def create_label(
        self,
        name: str,
        color: str | None = None,
        order: int | None = None,
        is_favorite: bool = False,
    ) -> dict[str, Any]:
        """Create a new personal label."""
        payload: dict[str, Any] = {"name": name}
        if color:
            payload["color"] = color
        if order is not None:
            payload["order"] = order
        if is_favorite:
            payload["is_favorite"] = True
        response = self._rest_request("POST", "/labels", json=payload)
        label: dict[str, Any] = response.json()
        return label

    def delete_label(self, label_id: str) -> None:
        """Delete a personal label."""
        self._rest_request("DELETE", f"/labels/{label_id}")

    def list_shared_labels(self) -> list[str]:
        """Get all shared labels (names only)."""
        response = self._rest_request("GET", "/labels/shared")
        shared: list[str] = response.json()
        return shared

    # -------------------------------------------------------------------
    # Sync API — Incremental Sync
    # -------------------------------------------------------------------

    def sync(
        self,
        resource_types: list[str] | None = None,
        sync_token: str | None = None,
    ) -> dict[str, Any]:
        """Perform incremental sync. Returns only items changed since last sync.

        resource_types: list of resource types to sync (e.g. ["items", "projects"]).
            Default: ["items", "projects", "sections", "labels"].
        sync_token: override sync token. Use "*" for full sync.
        """
        token = sync_token or self._sync_token or "*"
        types = resource_types or ["items", "projects", "sections", "labels"]
        data = self._sync_request(
            sync_token=token,
            resource_types=json.dumps(types),
        )
        return data

    def reset_sync_token(self) -> None:
        """Reset sync token to force a full sync on next call."""
        self._sync_token = None
        token_file = _CACHE_DIR / "sync_token"
        if token_file.exists():
            token_file.unlink()

    # -------------------------------------------------------------------
    # Sync API — Batch Commands
    # -------------------------------------------------------------------

    def batch(self, commands: list[dict[str, Any]]) -> dict[str, Any]:
        """Execute batch commands via the Sync API.

        Each command is a dict with:
        - type: command type (e.g. "item_add", "item_update", "item_close")
        - uuid: unique ID (auto-generated if missing)
        - args: command arguments
        - temp_id: (optional) temporary ID for referencing in subsequent commands

        Up to 100 commands per request. Returns sync_status with per-command results.
        """
        if len(commands) > MAX_BATCH_SIZE:
            raise TodoistError(f"Maximum {MAX_BATCH_SIZE} commands per batch. Got {len(commands)}.")

        # Auto-generate UUIDs if missing
        for cmd in commands:
            if "uuid" not in cmd:
                cmd["uuid"] = str(uuid.uuid4())

        data = self._sync_request(commands=json.dumps(commands))
        return data

    # -------------------------------------------------------------------
    # Productivity Stats
    # -------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get personal productivity stats (karma, daily/weekly goals)."""
        try:
            response = self._sync_client.get(
                "/completed/get_stats",
            )
            if response.status_code >= 400:
                raise classify_error(scrub_token(response.text), response.status_code)
            stats: dict[str, Any] = response.json()
            return stats
        except TodoistError:
            raise
        except httpx.HTTPError as e:
            msg = scrub_token(str(e))
            raise classify_error(msg) from e

    # -------------------------------------------------------------------
    # Completed Tasks
    # -------------------------------------------------------------------

    def get_completed_tasks(
        self,
        project_id: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get completed tasks (requires Todoist Pro)."""
        params: dict[str, Any] = {"limit": min(limit, 200), "offset": offset}
        if project_id:
            params["project_id"] = project_id
        try:
            response = self._sync_client.get("/completed/get_all", params=params)
            if response.status_code >= 400:
                raise classify_error(scrub_token(response.text), response.status_code)
            data: dict[str, Any] = response.json()
            return data
        except TodoistError:
            raise
        except httpx.HTTPError as e:
            msg = scrub_token(str(e))
            raise classify_error(msg) from e

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _find_project_by_name(self, name: str) -> dict[str, Any] | None:
        """Find a project by name (case-insensitive)."""
        projects = self.list_projects()
        lower = name.lower()
        for p in projects:
            if p.get("name", "").lower() == lower:
                return p
        return None

    def get_inbox_project_id(self) -> str:
        """Get the Inbox project ID."""
        projects = self.list_projects()
        for p in projects:
            if p.get("is_inbox_project"):
                return str(p["id"])
        raise NotFoundError("Inbox project not found")
