"""Tests for TodoistClient methods."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from todoist_blade_mcp.models import AuthError, NotFoundError, RateLimitError, TodoistError, ValidationError

# ---------------------------------------------------------------------------
# Client instantiation
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_missing_token_raises(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("todoist_blade_mcp.client._CACHE_DIR", MagicMock()),
        ):
            from todoist_blade_mcp.client import TodoistClient

            with pytest.raises(AuthError, match="not set"):
                TodoistClient(api_token="")

    def test_token_from_env(self, mock_rest_client):
        mock_rest, mock_sync = mock_rest_client
        with (
            patch.dict("os.environ", {"TODOIST_API_TOKEN": "env-token"}),
            patch("todoist_blade_mcp.client._CACHE_DIR", MagicMock()),
            patch.object(
                __import__("todoist_blade_mcp.client", fromlist=["TodoistClient"]).TodoistClient,
                "_load_sync_token",
                return_value=None,
            ),
        ):
            from todoist_blade_mcp.client import TodoistClient

            c = TodoistClient()
            assert c._token == "env-token"


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


class TestErrorClassification:
    def test_401_returns_auth_error(self):
        from todoist_blade_mcp.models import classify_error

        err = classify_error("some message", status_code=401)
        assert isinstance(err, AuthError)

    def test_404_returns_not_found(self):
        from todoist_blade_mcp.models import classify_error

        err = classify_error("some message", status_code=404)
        assert isinstance(err, NotFoundError)

    def test_429_returns_rate_limit(self):
        from todoist_blade_mcp.models import classify_error

        err = classify_error("some message", status_code=429)
        assert isinstance(err, RateLimitError)

    def test_400_returns_validation(self):
        from todoist_blade_mcp.models import classify_error

        err = classify_error("some message", status_code=400)
        assert isinstance(err, ValidationError)

    def test_pattern_matching(self):
        from todoist_blade_mcp.models import classify_error

        assert isinstance(classify_error("unauthorized request"), AuthError)
        assert isinstance(classify_error("resource not found"), NotFoundError)
        assert isinstance(classify_error("too many requests"), RateLimitError)
        from todoist_blade_mcp.models import ConnectionError as ConnError

        assert isinstance(classify_error("connection timeout"), ConnError)

    def test_unknown_error(self):
        from todoist_blade_mcp.models import classify_error

        err = classify_error("something weird happened")
        assert type(err) is TodoistError


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class TestListProjects:
    def test_success(self, client, mock_rest_client, sample_projects, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_projects)
        projects = client.list_projects()
        assert len(projects) == 4
        assert projects[0]["name"] == "Inbox"

    def test_auth_error(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(401, None)
        mock_rest.request.return_value.text = "Unauthorized"
        with pytest.raises(AuthError):
            client.list_projects()


class TestGetProject:
    def test_success(self, client, mock_rest_client, sample_projects, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_projects[1])
        project = client.get_project("2001")
        assert project["name"] == "Work"

    def test_not_found(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(404, None)
        mock_rest.request.return_value.text = "Not found"
        with pytest.raises(NotFoundError):
            client.get_project("9999")


class TestCreateProject:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        result = {"id": "2099", "name": "New Project", "color": "blue"}
        mock_rest.request.return_value = mock_response(200, result)
        project = client.create_project(name="New Project", color="blue")
        assert project["name"] == "New Project"
        # Verify the request was made with correct payload
        call_args = mock_rest.request.call_args
        assert call_args[0] == ("POST", "/projects")
        payload = call_args[1]["json"]
        assert payload["name"] == "New Project"
        assert payload["color"] == "blue"


class TestDeleteProject:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(204)
        client.delete_project("2001")  # Should not raise


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TestListTasks:
    def test_success(self, client, mock_rest_client, sample_tasks, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_tasks)
        tasks = client.list_tasks()
        assert len(tasks) == 3

    def test_with_filter(self, client, mock_rest_client, sample_tasks, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_tasks[:1])
        tasks = client.list_tasks(filter_query="today")
        assert len(tasks) == 1
        call_args = mock_rest.request.call_args
        assert call_args[1]["params"]["filter"] == "today"

    def test_with_project(self, client, mock_rest_client, sample_tasks, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_tasks[:2])
        client.list_tasks(project_id="2001")
        call_args = mock_rest.request.call_args
        assert call_args[1]["params"]["project_id"] == "2001"

    def test_limit(self, client, mock_rest_client, sample_tasks, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_tasks)
        tasks = client.list_tasks(limit=1)
        assert len(tasks) == 1


class TestGetTask:
    def test_success(self, client, mock_rest_client, sample_task_detail, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_task_detail)
        task = client.get_task("1001")
        assert task["content"] == "Buy milk"


class TestCreateTask:
    def test_basic(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        result = {"id": "1099", "content": "New task", "priority": 1}
        mock_rest.request.return_value = mock_response(200, result)
        task = client.create_task(content="New task")
        assert task["content"] == "New task"

    def test_with_all_fields(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        result = {"id": "1099", "content": "Complex task", "priority": 4}
        mock_rest.request.return_value = mock_response(200, result)
        client.create_task(
            content="Complex task",
            description="With description",
            project_id="2001",
            section_id="3001",
            labels=["work", "urgent"],
            priority=4,
            due_string="tomorrow at 2pm",
        )
        call_args = mock_rest.request.call_args
        payload = call_args[1]["json"]
        assert payload["content"] == "Complex task"
        assert payload["description"] == "With description"
        assert payload["priority"] == 4
        assert payload["labels"] == ["work", "urgent"]
        assert payload["due_string"] == "tomorrow at 2pm"


class TestCloseTask:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(204)
        client.close_task("1001")


class TestReopenTask:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(204)
        client.reopen_task("1001")


class TestDeleteTask:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(204)
        client.delete_task("1001")


class TestQuickAdd:
    def test_success(self, client, mock_rest_client, mock_response):
        _, mock_sync = mock_rest_client
        result = {"id": "1099", "content": "Buy milk", "due": {"date": "2026-04-01"}}
        mock_sync.post.return_value = mock_response(200, result)
        task = client.quick_add("Buy milk tomorrow")
        assert task["content"] == "Buy milk"


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


class TestListSections:
    def test_success(self, client, mock_rest_client, sample_sections, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_sections)
        sections = client.list_sections(project_id="2001")
        assert len(sections) == 3


class TestCreateSection:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        result = {"id": "3099", "name": "New Section", "project_id": "2001"}
        mock_rest.request.return_value = mock_response(200, result)
        section = client.create_section(name="New Section", project_id="2001")
        assert section["name"] == "New Section"


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class TestListComments:
    def test_success(self, client, mock_rest_client, sample_comments, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_comments)
        comments = client.list_comments(task_id="1001")
        assert len(comments) == 2

    def test_requires_id(self, client):
        with pytest.raises(TodoistError, match="required"):
            client.list_comments()


class TestCreateComment:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        result = {"id": "4099", "content": "New comment", "task_id": "1001"}
        mock_rest.request.return_value = mock_response(200, result)
        comment = client.create_comment(content="New comment", task_id="1001")
        assert comment["content"] == "New comment"


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


class TestListLabels:
    def test_success(self, client, mock_rest_client, sample_labels, mock_response):
        mock_rest, _ = mock_rest_client
        mock_rest.request.return_value = mock_response(200, sample_labels)
        labels = client.list_labels()
        assert len(labels) == 3


class TestCreateLabel:
    def test_success(self, client, mock_rest_client, mock_response):
        mock_rest, _ = mock_rest_client
        result = {"id": "5099", "name": "new-label", "color": "blue"}
        mock_rest.request.return_value = mock_response(200, result)
        label = client.create_label(name="new-label", color="blue")
        assert label["name"] == "new-label"


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


class TestSync:
    def test_incremental(self, client, mock_rest_client, sample_sync_result, mock_response):
        _, mock_sync = mock_rest_client
        resp = mock_response(200, sample_sync_result)
        mock_sync.post.return_value = resp
        data = client.sync()
        assert len(data["items"]) == 2
        assert data["full_sync"] is False

    def test_full_sync(self, client, mock_rest_client, sample_sync_result, mock_response):
        _, mock_sync = mock_rest_client
        full_result = {**sample_sync_result, "full_sync": True}
        resp = mock_response(200, full_result)
        mock_sync.post.return_value = resp
        client.sync(sync_token="*")
        call_args = mock_sync.post.call_args
        assert call_args[1]["json"]["sync_token"] == "*"


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


class TestBatch:
    def test_success(self, client, mock_rest_client, sample_batch_result, mock_response):
        _, mock_sync = mock_rest_client
        resp = mock_response(200, sample_batch_result)
        mock_sync.post.return_value = resp
        commands = [
            {"type": "item_add", "args": {"content": "Task 1"}},
            {"type": "item_add", "args": {"content": "Task 2"}},
        ]
        data = client.batch(commands)
        assert "sync_status" in data

    def test_exceeds_limit(self, client):
        commands = [{"type": "item_add", "args": {"content": f"Task {i}"}} for i in range(101)]
        with pytest.raises(TodoistError, match="Maximum"):
            client.batch(commands)

    def test_auto_uuid(self, client, mock_rest_client, sample_batch_result, mock_response):
        _, mock_sync = mock_rest_client
        resp = mock_response(200, sample_batch_result)
        mock_sync.post.return_value = resp
        commands = [{"type": "item_add", "args": {"content": "No UUID"}}]
        client.batch(commands)
        assert "uuid" in commands[0]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_success(self, client, mock_rest_client, sample_stats, mock_response):
        _, mock_sync = mock_rest_client
        mock_sync.get.return_value = mock_response(200, sample_stats)
        stats = client.get_stats()
        assert stats["karma"] == 12345


# ---------------------------------------------------------------------------
# Completed Tasks
# ---------------------------------------------------------------------------


class TestCompletedTasks:
    def test_success(self, client, mock_rest_client, sample_completed_tasks, mock_response):
        _, mock_sync = mock_rest_client
        mock_sync.get.return_value = mock_response(200, sample_completed_tasks)
        data = client.get_completed_tasks()
        assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Write gate
# ---------------------------------------------------------------------------


class TestWriteGate:
    def test_disabled_by_default(self):
        from todoist_blade_mcp.models import require_write

        with patch.dict("os.environ", {}, clear=True):
            assert require_write() is not None

    def test_enabled(self):
        from todoist_blade_mcp.models import require_write

        with patch.dict("os.environ", {"TODOIST_WRITE_ENABLED": "true"}):
            assert require_write() is None

    def test_case_insensitive(self):
        from todoist_blade_mcp.models import require_write

        with patch.dict("os.environ", {"TODOIST_WRITE_ENABLED": "True"}):
            assert require_write() is None


# ---------------------------------------------------------------------------
# Token scrubbing
# ---------------------------------------------------------------------------


class TestTokenScrubbing:
    def test_scrub(self):
        from todoist_blade_mcp.models import scrub_token

        text = "Bearer 0123456789abcdef0123456789abcdef01234567 is invalid"
        scrubbed = scrub_token(text)
        assert "0123456789" not in scrubbed
        assert "****" in scrubbed

    def test_no_token(self):
        from todoist_blade_mcp.models import scrub_token

        text = "No token here"
        assert scrub_token(text) == text
