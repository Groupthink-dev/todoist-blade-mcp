"""Shared fixtures for Todoist Blade MCP tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------


def _make_task(
    task_id: str = "1001",
    content: str = "Buy milk",
    description: str = "",
    project_id: str = "2001",
    section_id: str | None = None,
    parent_id: str | None = None,
    priority: int = 1,
    due: dict | None = None,
    labels: list[str] | None = None,
    url: str | None = None,
    created_at: str = "2026-03-15T10:30:00Z",
) -> dict:
    task = {
        "id": task_id,
        "content": content,
        "description": description,
        "project_id": project_id,
        "priority": priority,
        "labels": labels or [],
        "created_at": created_at,
        "url": url or f"https://app.todoist.com/app/task/{task_id}",
    }
    if section_id:
        task["section_id"] = section_id
    if parent_id:
        task["parent_id"] = parent_id
    if due:
        task["due"] = due
    return task


def _make_project(
    project_id: str = "2001",
    name: str = "Work",
    color: str = "berry",
    is_inbox_project: bool = False,
    is_favorite: bool = False,
    is_shared: bool = False,
    view_style: str = "list",
    url: str | None = None,
) -> dict:
    return {
        "id": project_id,
        "name": name,
        "color": color,
        "is_inbox_project": is_inbox_project,
        "is_favorite": is_favorite,
        "is_shared": is_shared,
        "view_style": view_style,
        "url": url or f"https://app.todoist.com/app/project/{project_id}",
    }


def _make_section(
    section_id: str = "3001",
    name: str = "To Do",
    project_id: str = "2001",
) -> dict:
    return {
        "id": section_id,
        "name": name,
        "project_id": project_id,
    }


def _make_comment(
    comment_id: str = "4001",
    content: str = "This is a comment",
    task_id: str | None = "1001",
    project_id: str | None = None,
    posted_at: str = "2026-03-15T10:30:00Z",
) -> dict:
    comment: dict = {
        "id": comment_id,
        "content": content,
        "posted_at": posted_at,
    }
    if task_id:
        comment["task_id"] = task_id
    if project_id:
        comment["project_id"] = project_id
    return comment


def _make_label(
    label_id: str = "5001",
    name: str = "urgent",
    color: str = "red",
    is_favorite: bool = False,
) -> dict:
    return {
        "id": label_id,
        "name": name,
        "color": color,
        "is_favorite": is_favorite,
    }


# ---------------------------------------------------------------------------
# Fixtures — sample data
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_tasks() -> list[dict]:
    return [
        _make_task(
            task_id="1001",
            content="Buy milk",
            priority=1,
            due={"date": "2026-04-01", "is_recurring": False, "string": "Apr 1"},
            labels=["errands"],
        ),
        _make_task(
            task_id="1002",
            content="Finish project report",
            priority=4,
            due={"date": "2026-03-31", "is_recurring": False, "string": "Mar 31"},
            labels=["work", "urgent"],
        ),
        _make_task(
            task_id="1003",
            content="Call dentist",
            priority=2,
            labels=["personal"],
        ),
    ]


@pytest.fixture
def sample_task_detail() -> dict:
    return _make_task(
        task_id="1001",
        content="Buy milk",
        description="Whole milk, 2 litres",
        project_id="2001",
        section_id="3001",
        priority=3,
        due={"date": "2026-04-01", "is_recurring": True, "string": "every week"},
        labels=["errands", "grocery"],
    )


@pytest.fixture
def sample_projects() -> list[dict]:
    return [
        _make_project(project_id="2000", name="Inbox", is_inbox_project=True, color="charcoal"),
        _make_project(project_id="2001", name="Work", color="berry", is_favorite=True),
        _make_project(project_id="2002", name="Personal", color="blue"),
        _make_project(project_id="2003", name="Shared Project", color="green", is_shared=True),
    ]


@pytest.fixture
def sample_sections() -> list[dict]:
    return [
        _make_section(section_id="3001", name="To Do", project_id="2001"),
        _make_section(section_id="3002", name="In Progress", project_id="2001"),
        _make_section(section_id="3003", name="Done", project_id="2001"),
    ]


@pytest.fixture
def sample_comments() -> list[dict]:
    return [
        _make_comment(comment_id="4001", content="This needs to be done by Friday", task_id="1001"),
        _make_comment(comment_id="4002", content="Updated the deadline", task_id="1001"),
    ]


@pytest.fixture
def sample_labels() -> list[dict]:
    return [
        _make_label(label_id="5001", name="urgent", color="red", is_favorite=True),
        _make_label(label_id="5002", name="work", color="berry"),
        _make_label(label_id="5003", name="errands", color="charcoal"),
    ]


@pytest.fixture
def sample_collaborators() -> list[dict]:
    return [
        {"id": "6001", "name": "Alice", "email": "alice@example.com"},
        {"id": "6002", "name": "Bob", "email": "bob@example.com"},
    ]


@pytest.fixture
def sample_sync_result() -> dict:
    return {
        "sync_token": "abc123def456",
        "full_sync": False,
        "items": [
            {"id": "1001", "content": "Buy milk", "checked": False},
            {"id": "1002", "content": "Finish report", "checked": True},
        ],
        "projects": [
            {"id": "2001", "name": "Work"},
        ],
        "sections": [],
        "labels": [
            {"id": "5001", "name": "urgent"},
        ],
    }


@pytest.fixture
def sample_batch_result() -> dict:
    return {
        "sync_status": {
            "uuid-001": "ok",
            "uuid-002": "ok",
            "uuid-003": {"error": "Invalid project_id"},
        },
        "temp_id_mapping": {
            "tmp-1": "12345",
            "tmp-2": "67890",
        },
    }


@pytest.fixture
def sample_stats() -> dict:
    return {
        "karma": 12345,
        "karma_trend": "up",
        "goals": {
            "daily_goal": 5,
            "daily_streak": 12,
            "weekly_goal": 25,
            "weekly_streak": 4,
        },
        "days_items": [
            {"date": "2026-03-31", "total_completed": 3},
            {"date": "2026-03-30", "total_completed": 5},
            {"date": "2026-03-29", "total_completed": 4},
            {"date": "2026-03-28", "total_completed": 2},
            {"date": "2026-03-27", "total_completed": 3},
            {"date": "2026-03-26", "total_completed": 2},
            {"date": "2026-03-25", "total_completed": 2},
        ],
    }


@pytest.fixture
def sample_completed_tasks() -> dict:
    return {
        "items": [
            {"task_id": "1010", "content": "Old task 1", "completed_at": "2026-03-30T15:00:00Z"},
            {"task_id": "1011", "content": "Old task 2", "completed_at": "2026-03-29T10:00:00Z"},
        ],
    }


# ---------------------------------------------------------------------------
# Fixtures — mock HTTP
# ---------------------------------------------------------------------------


def _mock_response(status_code: int = 200, json_data: Any = None) -> httpx.Response:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = ""
    return resp


@pytest.fixture
def mock_rest_client():
    """Patch httpx.Client for REST API."""
    with patch("todoist_blade_mcp.client.httpx.Client") as mock_cls:
        mock_rest = MagicMock()
        mock_sync = MagicMock()
        # First call = REST client, second = Sync client
        mock_cls.side_effect = [mock_rest, mock_sync]
        yield mock_rest, mock_sync


@pytest.fixture
def client(mock_rest_client):
    """Create a TodoistClient with mocked httpx."""
    mock_rest, mock_sync = mock_rest_client
    with (
        patch.dict("os.environ", {"TODOIST_API_TOKEN": "test-token-12345"}),
        patch("todoist_blade_mcp.client._CACHE_DIR", MagicMock()),
    ):
        # Patch _load_sync_token to return None
        with patch.object(
            __import__("todoist_blade_mcp.client", fromlist=["TodoistClient"]).TodoistClient,
            "_load_sync_token",
            return_value=None,
        ):
            from todoist_blade_mcp.client import TodoistClient

            c = TodoistClient(api_token="test-token-12345")
            # Replace the clients with our mocks
            c._rest = mock_rest
            c._sync_client = mock_sync
            return c


# Provide mock_response as a callable fixture
@pytest.fixture
def mock_response():
    """Return the _mock_response factory for building httpx.Response mocks."""
    return _mock_response
