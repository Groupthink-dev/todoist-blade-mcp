"""Tests for token-efficient formatters."""

from __future__ import annotations

from todoist_blade_mcp.formatters import (
    format_batch_result,
    format_collaborator_list,
    format_comment_detail,
    format_comment_list,
    format_completed_tasks,
    format_label_list,
    format_project_detail,
    format_project_list,
    format_quick_add_result,
    format_section_list,
    format_shared_labels,
    format_stats,
    format_sync_items,
    format_sync_result,
    format_task_detail,
    format_task_list,
)

# ---------------------------------------------------------------------------
# Task formatters
# ---------------------------------------------------------------------------


class TestFormatTaskList:
    def test_empty(self):
        assert format_task_list([]) == "No tasks found."

    def test_basic_tasks(self, sample_tasks):
        result = format_task_list(sample_tasks)
        assert "Buy milk" in result
        assert "Finish project report" in result
        assert "id=1001" in result
        assert "p4" in result  # priority 1 = p4 (normal)
        assert "p1" in result  # priority 4 = p1 (urgent)

    def test_labels_shown(self, sample_tasks):
        result = format_task_list(sample_tasks)
        assert "@errands" in result
        assert "@work" in result

    def test_due_dates(self, sample_tasks):
        result = format_task_list(sample_tasks)
        # At least one task should have a date
        assert "2026" in result or "today" in result or "tomorrow" in result or "overdue" in result

    def test_limit_truncation(self, sample_tasks):
        result = format_task_list(sample_tasks, limit=1)
        assert "Buy milk" in result
        assert "… 2 more" in result

    def test_no_truncation_when_all_shown(self, sample_tasks):
        result = format_task_list(sample_tasks, limit=10)
        assert "more" not in result


class TestFormatTaskDetail:
    def test_full_detail(self, sample_task_detail):
        result = format_task_detail(sample_task_detail)
        assert "Content: Buy milk" in result
        assert "Description: Whole milk, 2 litres" in result
        assert "Project: 2001" in result
        assert "Section: 3001" in result
        assert "p2" in result  # priority 3 = p2
        assert "high" in result
        assert "(recurring)" in result
        assert "@errands" in result
        assert "@grocery" in result
        assert "ID: 1001" in result

    def test_minimal_task(self):
        result = format_task_detail({"content": "Simple task", "id": "99", "priority": 1})
        assert "Content: Simple task" in result
        assert "p4" in result  # normal priority


# ---------------------------------------------------------------------------
# Project formatters
# ---------------------------------------------------------------------------


class TestFormatProjectList:
    def test_empty(self):
        assert format_project_list([]) == "No projects found."

    def test_projects(self, sample_projects):
        result = format_project_list(sample_projects)
        assert "Inbox" in result
        assert "[inbox]" in result
        assert "Work" in result
        assert "berry" in result
        assert "★" in result  # favorite
        assert "shared" in result
        assert "id=2001" in result

    def test_charcoal_color_omitted(self, sample_projects):
        result = format_project_list(sample_projects)
        # Inbox has charcoal — should not show "charcoal"
        lines = result.split("\n")
        inbox_line = [ln for ln in lines if "Inbox" in ln][0]
        assert "charcoal" not in inbox_line


class TestFormatProjectDetail:
    def test_full_detail(self, sample_projects):
        result = format_project_detail(sample_projects[1])  # Work
        assert "Name: Work" in result
        assert "Color: berry" in result
        assert "Favorite: yes" in result
        assert "ID: 2001" in result


# ---------------------------------------------------------------------------
# Section formatters
# ---------------------------------------------------------------------------


class TestFormatSectionList:
    def test_empty(self):
        assert format_section_list([]) == "No sections found."

    def test_sections(self, sample_sections):
        result = format_section_list(sample_sections)
        assert "To Do" in result
        assert "In Progress" in result
        assert "Done" in result
        assert "project=2001" in result
        assert "id=3001" in result


# ---------------------------------------------------------------------------
# Comment formatters
# ---------------------------------------------------------------------------


class TestFormatCommentList:
    def test_empty(self):
        assert format_comment_list([]) == "No comments found."

    def test_comments(self, sample_comments):
        result = format_comment_list(sample_comments)
        assert "This needs to be done by Friday" in result
        assert "Updated the deadline" in result
        assert "id=4001" in result

    def test_limit(self, sample_comments):
        result = format_comment_list(sample_comments, limit=1)
        assert "… 1 more" in result


class TestFormatCommentDetail:
    def test_detail(self, sample_comments):
        result = format_comment_detail(sample_comments[0])
        assert "This needs to be done by Friday" in result
        assert "Task: 1001" in result


# ---------------------------------------------------------------------------
# Label formatters
# ---------------------------------------------------------------------------


class TestFormatLabelList:
    def test_empty(self):
        assert format_label_list([]) == "No labels found."

    def test_labels(self, sample_labels):
        result = format_label_list(sample_labels)
        assert "@urgent" in result
        assert "red" in result
        assert "★" in result
        assert "@work" in result
        assert "id=5001" in result

    def test_charcoal_omitted(self, sample_labels):
        result = format_label_list(sample_labels)
        lines = result.split("\n")
        errands_line = [ln for ln in lines if "errands" in ln][0]
        assert "charcoal" not in errands_line


class TestFormatSharedLabels:
    def test_empty(self):
        assert format_shared_labels([]) == "No shared labels."

    def test_labels(self):
        result = format_shared_labels(["team", "review"])
        assert "@team" in result
        assert "@review" in result


# ---------------------------------------------------------------------------
# Collaborator formatters
# ---------------------------------------------------------------------------


class TestFormatCollaboratorList:
    def test_empty(self):
        assert format_collaborator_list([]) == "No collaborators."

    def test_collaborators(self, sample_collaborators):
        result = format_collaborator_list(sample_collaborators)
        assert "Alice" in result
        assert "alice@example.com" in result
        assert "id=6001" in result


# ---------------------------------------------------------------------------
# Sync formatters
# ---------------------------------------------------------------------------


class TestFormatSyncResult:
    def test_result(self, sample_sync_result):
        result = format_sync_result(sample_sync_result)
        assert "Sync token:" in result
        assert "Full sync: false" in result
        assert "Items: 2 changed" in result
        assert "Projects: 1 changed" in result
        assert "Sections: 0 changed" in result
        assert "Labels: 1 changed" in result


class TestFormatSyncItems:
    def test_items(self, sample_sync_result):
        result = format_sync_items(sample_sync_result["items"], "items")
        assert "Buy milk" in result
        assert "✓" in result  # checked=True
        assert "○" in result  # checked=False

    def test_empty(self):
        assert "No items" in format_sync_items([], "items")


# ---------------------------------------------------------------------------
# Batch formatters
# ---------------------------------------------------------------------------


class TestFormatBatchResult:
    def test_result(self, sample_batch_result):
        result = format_batch_result(sample_batch_result)
        assert "Sync status:" in result
        assert "ok" in result
        assert "error" in result
        assert "Temp ID mapping:" in result
        assert "tmp-1 → 12345" in result

    def test_empty(self):
        assert "Batch completed" in format_batch_result({})


# ---------------------------------------------------------------------------
# Stats formatters
# ---------------------------------------------------------------------------


class TestFormatStats:
    def test_stats(self, sample_stats):
        result = format_stats(sample_stats)
        assert "Karma: 12345" in result
        assert "(up)" in result
        assert "Daily goal: 5" in result
        assert "streak: 12 days" in result
        assert "Weekly goal: 25" in result
        assert "streak: 4 weeks" in result
        assert "today 3" in result
        assert "last 7 days 21" in result

    def test_empty(self):
        assert "No stats" in format_stats({})


# ---------------------------------------------------------------------------
# Completed task formatters
# ---------------------------------------------------------------------------


class TestFormatCompletedTasks:
    def test_tasks(self, sample_completed_tasks):
        result = format_completed_tasks(sample_completed_tasks)
        assert "Old task 1" in result
        assert "2026-03-30" in result
        assert "id=1010" in result

    def test_empty(self):
        assert "No completed tasks" in format_completed_tasks({"items": []})


# ---------------------------------------------------------------------------
# Quick add formatter
# ---------------------------------------------------------------------------


class TestFormatQuickAddResult:
    def test_result(self):
        task = {"id": "1234", "content": "Buy milk", "due": {"date": "2026-04-01"}}
        result = format_quick_add_result(task)
        assert "Created: Buy milk" in result
        assert "due=2026-04-01" in result
        assert "id=1234" in result
