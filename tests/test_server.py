"""Tests for MCP server tool functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from todoist_blade_mcp.models import TodoistError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Patch _get_client to return a mock TodoistClient."""
    with patch("todoist_blade_mcp.server._get_client") as mock_get:
        mock_todoist = MagicMock()
        mock_get.return_value = mock_todoist
        yield mock_todoist


@pytest.fixture
def write_enabled():
    """Enable write operations."""
    with patch.dict("os.environ", {"TODOIST_WRITE_ENABLED": "true"}):
        yield


@pytest.fixture
def write_disabled():
    """Disable write operations (default)."""
    with patch.dict("os.environ", {"TODOIST_WRITE_ENABLED": "false"}):
        yield


# ===========================================================================
# Project tools
# ===========================================================================


class TestProjectsList:
    async def test_success(self, mock_client, sample_projects):
        from todoist_blade_mcp.server import projects_list

        mock_client.list_projects.return_value = sample_projects
        result = await projects_list()
        assert "Work" in result
        assert "Inbox" in result
        assert "id=2001" in result

    async def test_error(self, mock_client):
        from todoist_blade_mcp.server import projects_list

        mock_client.list_projects.side_effect = TodoistError("API error")
        result = await projects_list()
        assert "Error" in result


class TestProjectsRead:
    async def test_success(self, mock_client, sample_projects):
        from todoist_blade_mcp.server import projects_read

        mock_client.get_project.return_value = sample_projects[1]
        result = await projects_read(id="2001")
        assert "Name: Work" in result


class TestProjectsCreate:
    async def test_write_gate(self, mock_client, write_disabled):
        from todoist_blade_mcp.server import projects_create

        result = await projects_create(name="Test")
        assert "Write operations are disabled" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import projects_create

        mock_client.create_project.return_value = {"id": "2099", "name": "Test"}
        result = await projects_create(name="Test")
        assert "Created: Test" in result


class TestProjectsDelete:
    async def test_requires_confirm(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import projects_delete

        result = await projects_delete(id="2001")
        assert "confirm=true" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import projects_delete

        mock_client.delete_project.return_value = None
        result = await projects_delete(id="2001", confirm=True)
        assert "Deleted" in result


# ===========================================================================
# Task tools
# ===========================================================================


class TestTasksList:
    async def test_success(self, mock_client, sample_tasks):
        from todoist_blade_mcp.server import tasks_list

        mock_client.list_tasks.return_value = sample_tasks
        result = await tasks_list()
        assert "Buy milk" in result
        assert "Finish project report" in result

    async def test_with_filter(self, mock_client, sample_tasks):
        from todoist_blade_mcp.server import tasks_list

        mock_client.list_tasks.return_value = sample_tasks[:1]
        result = await tasks_list(filter="today")
        assert "Buy milk" in result


class TestTasksRead:
    async def test_success(self, mock_client, sample_task_detail):
        from todoist_blade_mcp.server import tasks_read

        mock_client.get_task.return_value = sample_task_detail
        result = await tasks_read(id="1001")
        assert "Content: Buy milk" in result
        assert "Description: Whole milk" in result


class TestTasksSearch:
    async def test_success(self, mock_client, sample_tasks):
        from todoist_blade_mcp.server import tasks_search

        mock_client.list_tasks.return_value = sample_tasks
        result = await tasks_search(query="today & #Work")
        assert "Buy milk" in result


class TestTasksCreate:
    async def test_write_gate(self, mock_client, write_disabled):
        from todoist_blade_mcp.server import tasks_create

        result = await tasks_create(content="Test")
        assert "Write operations are disabled" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_create

        mock_client.create_task.return_value = {"id": "1099", "content": "New task"}
        result = await tasks_create(content="New task", priority=4, due_string="tomorrow")
        assert "Created: New task" in result

    async def test_with_labels(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_create

        mock_client.create_task.return_value = {"id": "1099", "content": "Labeled task"}
        result = await tasks_create(content="Labeled task", labels="work,urgent")
        assert "Created: Labeled task" in result
        call_args = mock_client.create_task.call_args
        assert call_args[1]["labels"] == ["work", "urgent"]


class TestTasksUpdate:
    async def test_write_gate(self, mock_client, write_disabled):
        from todoist_blade_mcp.server import tasks_update

        result = await tasks_update(id="1001", content="Updated")
        assert "Write operations are disabled" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_update

        mock_client.update_task.return_value = {"id": "1001", "content": "Updated"}
        result = await tasks_update(id="1001", content="Updated")
        assert "Updated: Updated" in result

    async def test_no_fields(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_update

        result = await tasks_update(id="1001")
        assert "No fields" in result


class TestTasksComplete:
    async def test_write_gate(self, mock_client, write_disabled):
        from todoist_blade_mcp.server import tasks_complete

        result = await tasks_complete(id="1001")
        assert "Write operations are disabled" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_complete

        mock_client.close_task.return_value = None
        result = await tasks_complete(id="1001")
        assert "Completed" in result


class TestTasksReopen:
    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_reopen

        mock_client.reopen_task.return_value = None
        result = await tasks_reopen(id="1001")
        assert "Reopened" in result


class TestTasksDelete:
    async def test_requires_confirm(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_delete

        result = await tasks_delete(id="1001")
        assert "confirm=true" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_delete

        mock_client.delete_task.return_value = None
        result = await tasks_delete(id="1001", confirm=True)
        assert "Deleted" in result


class TestTasksQuickAdd:
    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import tasks_quick_add

        mock_client.quick_add.return_value = {"id": "1099", "content": "Buy milk", "due": {"date": "2026-04-01"}}
        result = await tasks_quick_add(text="Buy milk tomorrow")
        assert "Created: Buy milk" in result


# ===========================================================================
# Comment tools
# ===========================================================================


class TestCommentsList:
    async def test_success(self, mock_client, sample_comments):
        from todoist_blade_mcp.server import comments_list

        mock_client.list_comments.return_value = sample_comments
        result = await comments_list(task_id="1001")
        assert "This needs to be done by Friday" in result


class TestCommentsCreate:
    async def test_write_gate(self, mock_client, write_disabled):
        from todoist_blade_mcp.server import comments_create

        result = await comments_create(content="Test", task_id="1001")
        assert "Write operations are disabled" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import comments_create

        mock_client.create_comment.return_value = {"id": "4099", "content": "New comment"}
        result = await comments_create(content="New comment", task_id="1001")
        assert "Comment added" in result


# ===========================================================================
# Label tools
# ===========================================================================


class TestLabelsList:
    async def test_success(self, mock_client, sample_labels):
        from todoist_blade_mcp.server import labels_list

        mock_client.list_labels.return_value = sample_labels
        mock_client.list_shared_labels.return_value = ["shared-label"]
        result = await labels_list()
        assert "@urgent" in result
        assert "Shared labels:" in result
        assert "@shared-label" in result


class TestLabelsCreate:
    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import labels_create

        mock_client.create_label.return_value = {"id": "5099", "name": "new-label"}
        result = await labels_create(name="new-label")
        assert "Created: @new-label" in result


# ===========================================================================
# Sync tools
# ===========================================================================


class TestTodoistSync:
    async def test_incremental(self, mock_client, sample_sync_result):
        from todoist_blade_mcp.server import todoist_sync

        mock_client.sync.return_value = sample_sync_result
        result = await todoist_sync()
        assert "Sync token:" in result
        assert "Items: 2 changed" in result

    async def test_full_sync(self, mock_client, sample_sync_result):
        from todoist_blade_mcp.server import todoist_sync

        full_result = {**sample_sync_result, "full_sync": True}
        mock_client.sync.return_value = full_result
        mock_client.reset_sync_token.return_value = None
        await todoist_sync(full_sync=True)
        mock_client.reset_sync_token.assert_called_once()


class TestTodoistBatch:
    async def test_write_gate(self, mock_client, write_disabled):
        from todoist_blade_mcp.server import todoist_batch

        result = await todoist_batch(commands='[{"type":"item_add","args":{"content":"Test"}}]')
        assert "Write operations are disabled" in result

    async def test_success(self, mock_client, write_enabled, sample_batch_result):
        from todoist_blade_mcp.server import todoist_batch

        mock_client.batch.return_value = sample_batch_result
        result = await todoist_batch(commands='[{"type":"item_add","args":{"content":"Test"}}]')
        assert "Sync status:" in result

    async def test_invalid_json(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import todoist_batch

        result = await todoist_batch(commands="not json")
        assert "Invalid JSON" in result

    async def test_not_array(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import todoist_batch

        result = await todoist_batch(commands='{"type":"item_add"}')
        assert "must be a JSON array" in result


# ===========================================================================
# Productivity tools
# ===========================================================================


class TestTodoistStats:
    async def test_success(self, mock_client, sample_stats):
        from todoist_blade_mcp.server import todoist_stats

        mock_client.get_stats.return_value = sample_stats
        result = await todoist_stats()
        assert "Karma: 12345" in result


class TestTodoistCompleted:
    async def test_success(self, mock_client, sample_completed_tasks):
        from todoist_blade_mcp.server import todoist_completed

        mock_client.get_completed_tasks.return_value = sample_completed_tasks
        result = await todoist_completed()
        assert "Old task 1" in result


# ===========================================================================
# Section tools
# ===========================================================================


class TestSectionsList:
    async def test_success(self, mock_client, sample_sections):
        from todoist_blade_mcp.server import sections_list

        mock_client.list_sections.return_value = sample_sections
        result = await sections_list(project_id="2001")
        assert "To Do" in result
        assert "In Progress" in result


class TestSectionsCreate:
    async def test_write_gate(self, mock_client, write_disabled):
        from todoist_blade_mcp.server import sections_create

        result = await sections_create(name="Test", project_id="2001")
        assert "Write operations are disabled" in result

    async def test_success(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import sections_create

        mock_client.create_section.return_value = {"id": "3099", "name": "New"}
        result = await sections_create(name="New", project_id="2001")
        assert "Created: New" in result


class TestSectionsDelete:
    async def test_requires_confirm(self, mock_client, write_enabled):
        from todoist_blade_mcp.server import sections_delete

        result = await sections_delete(id="3001")
        assert "confirm=true" in result
