"""Token-efficient output formatters for Todoist data.

Design principles:
- Concise by default (one line per item)
- Null fields omitted
- Lists capped and annotated with total count
- Priority rendered as p1–p4 labels
- Due dates rendered in relative terms where useful
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from todoist_blade_mcp.models import DEFAULT_LIMIT, MAX_DESCRIPTION_CHARS, PRIORITY_DISPLAY

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def format_task_list(tasks: list[dict[str, Any]], limit: int = DEFAULT_LIMIT) -> str:
    """Format task list concisely: priority | due | labels | content | id.

    Example::

        p1 | 2026-04-01 | @work @urgent | Finish project report | id=123
        p4 | today | | Call dentist | id=456
        … 18 more (use limit= to see more)
    """
    if not tasks:
        return "No tasks found."

    total = len(tasks)
    shown = tasks[:limit]
    lines: list[str] = []

    for task in shown:
        parts: list[str] = []

        # Priority
        priority = task.get("priority", 1)
        parts.append(PRIORITY_DISPLAY.get(priority, "p4"))

        # Due date
        due = task.get("due")
        if due:
            due_date = due.get("date", "")
            is_recurring = due.get("is_recurring", False)
            display = _format_due_date(due_date)
            if is_recurring:
                display = f"↻ {display}"
            parts.append(display)

        # Labels
        labels = task.get("labels", [])
        if labels:
            parts.append(" ".join(f"@{lbl}" for lbl in labels[:5]))

        # Content
        parts.append(task.get("content", "?"))

        # ID
        if tid := task.get("id"):
            parts.append(f"id={tid}")

        lines.append(" | ".join(parts))

    if total > len(shown):
        lines.append(f"… {total - len(shown)} more (use limit= to see more)")

    return "\n".join(lines)


def format_task_detail(task: dict[str, Any]) -> str:
    """Format a full task for reading: all fields.

    Example::

        Content: Finish project report
        Description: Need to include Q3 metrics and charts
        Project: 123 (Work)
        Section: 456
        Priority: p1 (urgent)
        Due: 2026-04-01 (recurring)
        Labels: @work @urgent
        Created: 2026-03-15T10:30:00Z
        ID: 789
        URL: https://app.todoist.com/app/task/789
    """
    lines: list[str] = []

    if content := task.get("content"):
        lines.append(f"Content: {content}")
    if desc := task.get("description"):
        lines.append(f"Description: {desc}")
    if project_id := task.get("project_id"):
        lines.append(f"Project: {project_id}")
    if section_id := task.get("section_id"):
        lines.append(f"Section: {section_id}")
    if parent_id := task.get("parent_id"):
        lines.append(f"Parent: {parent_id}")

    priority = task.get("priority", 1)
    p_label = PRIORITY_DISPLAY.get(priority, "p4")
    from todoist_blade_mcp.models import PRIORITY_LABELS

    p_name = PRIORITY_LABELS.get(priority, "normal")
    lines.append(f"Priority: {p_label} ({p_name})")

    if due := task.get("due"):
        due_parts = [due.get("date", "?")]
        if due.get("is_recurring"):
            due_parts.append("(recurring)")
        if due_str := due.get("string"):
            due_parts.append(f'"{due_str}"')
        lines.append(f"Due: {' '.join(due_parts)}")

    labels = task.get("labels", [])
    if labels:
        lines.append(f"Labels: {' '.join(f'@{lbl}' for lbl in labels)}")

    if assignee := task.get("assignee_id"):
        lines.append(f"Assignee: {assignee}")
    if duration := task.get("duration"):
        amount = duration.get("amount", "?")
        unit = duration.get("unit", "minute")
        lines.append(f"Duration: {amount} {unit}(s)")
    if created := task.get("created_at"):
        lines.append(f"Created: {created}")
    if tid := task.get("id"):
        lines.append(f"ID: {tid}")
    if url := task.get("url"):
        lines.append(f"URL: {url}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def format_project_list(projects: list[dict[str, Any]]) -> str:
    """Format project list: name | color | favorite | id.

    Example::

        Inbox [inbox] | id=123
        Work | berry | ★ | id=456
        Personal | id=789
    """
    if not projects:
        return "No projects found."

    lines: list[str] = []
    for p in projects:
        parts: list[str] = [p.get("name", "?")]

        if p.get("is_inbox_project"):
            parts.append("[inbox]")
        if color := p.get("color"):
            if color != "charcoal":
                parts.append(color)
        if p.get("is_favorite"):
            parts.append("★")
        if p.get("is_shared"):
            parts.append("shared")
        if pid := p.get("id"):
            parts.append(f"id={pid}")

        lines.append(" | ".join(parts))

    return "\n".join(lines)


def format_project_detail(project: dict[str, Any]) -> str:
    """Format a full project for reading."""
    lines: list[str] = []

    if name := project.get("name"):
        lines.append(f"Name: {name}")
    if project.get("is_inbox_project"):
        lines.append("Type: Inbox")
    if color := project.get("color"):
        lines.append(f"Color: {color}")
    if parent_id := project.get("parent_id"):
        lines.append(f"Parent: {parent_id}")
    if project.get("is_shared"):
        lines.append("Shared: yes")
    if project.get("is_favorite"):
        lines.append("Favorite: yes")
    if view := project.get("view_style"):
        lines.append(f"View: {view}")
    if pid := project.get("id"):
        lines.append(f"ID: {pid}")
    if url := project.get("url"):
        lines.append(f"URL: {url}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def format_section_list(sections: list[dict[str, Any]]) -> str:
    """Format section list: name | project_id | id.

    Example::

        To Do | project=123 | id=456
        In Progress | project=123 | id=789
    """
    if not sections:
        return "No sections found."

    lines: list[str] = []
    for s in sections:
        parts: list[str] = [s.get("name", "?")]
        if pid := s.get("project_id"):
            parts.append(f"project={pid}")
        if sid := s.get("id"):
            parts.append(f"id={sid}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def format_comment_list(comments: list[dict[str, Any]], limit: int = DEFAULT_LIMIT) -> str:
    """Format comment list: date | content (truncated) | id.

    Example::

        2026-03-15 10:30 | This is a comment about the task | id=123
        2026-03-14 09:00 | Another comment here | id=456
    """
    if not comments:
        return "No comments found."

    total = len(comments)
    shown = comments[:limit]
    lines: list[str] = []

    for c in shown:
        parts: list[str] = []

        if posted := c.get("posted_at"):
            parts.append(posted[:16])

        content = c.get("content", "?")
        if len(content) > MAX_DESCRIPTION_CHARS:
            content = content[:MAX_DESCRIPTION_CHARS] + "…"
        parts.append(content)

        if cid := c.get("id"):
            parts.append(f"id={cid}")

        lines.append(" | ".join(parts))

    if total > len(shown):
        lines.append(f"… {total - len(shown)} more")

    return "\n".join(lines)


def format_comment_detail(comment: dict[str, Any]) -> str:
    """Format a full comment for reading."""
    lines: list[str] = []
    if posted := comment.get("posted_at"):
        lines.append(f"Date: {posted}")
    if content := comment.get("content"):
        lines.append(f"Content: {content}")
    if task_id := comment.get("task_id"):
        lines.append(f"Task: {task_id}")
    if project_id := comment.get("project_id"):
        lines.append(f"Project: {project_id}")
    if cid := comment.get("id"):
        lines.append(f"ID: {cid}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def format_label_list(labels: list[dict[str, Any]]) -> str:
    """Format label list: @name | color | id.

    Example::

        @work | berry | ★ | id=123
        @urgent | red | id=456
    """
    if not labels:
        return "No labels found."

    lines: list[str] = []
    for lb in labels:
        parts: list[str] = [f"@{lb.get('name', '?')}"]
        if color := lb.get("color"):
            if color != "charcoal":
                parts.append(color)
        if lb.get("is_favorite"):
            parts.append("★")
        if lid := lb.get("id"):
            parts.append(f"id={lid}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


def format_shared_labels(labels: list[str]) -> str:
    """Format shared label names."""
    if not labels:
        return "No shared labels."
    return "\n".join(f"@{lbl}" for lbl in labels)


# ---------------------------------------------------------------------------
# Collaborators
# ---------------------------------------------------------------------------


def format_collaborator_list(collabs: list[dict[str, Any]]) -> str:
    """Format collaborator list: name | email | id."""
    if not collabs:
        return "No collaborators."

    lines: list[str] = []
    for c in collabs:
        parts: list[str] = [c.get("name", "?")]
        if email := c.get("email"):
            parts.append(email)
        if cid := c.get("id"):
            parts.append(f"id={cid}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def format_sync_result(data: dict[str, Any]) -> str:
    """Format sync API result compactly.

    Example::

        Sync token: abc123
        Full sync: false
        Items: 5 changed
        Projects: 2 changed
        Sections: 0 changed
        Labels: 1 changed
    """
    lines: list[str] = []
    if token := data.get("sync_token"):
        lines.append(f"Sync token: {token[:20]}…" if len(token) > 20 else f"Sync token: {token}")
    lines.append(f"Full sync: {str(data.get('full_sync', False)).lower()}")

    for resource in ["items", "projects", "sections", "labels", "filters", "reminders"]:
        items = data.get(resource, [])
        if isinstance(items, list) and items:
            lines.append(f"{resource.capitalize()}: {len(items)} changed")
        elif isinstance(items, list):
            lines.append(f"{resource.capitalize()}: 0 changed")

    return "\n".join(lines)


def format_sync_items(items: list[dict[str, Any]], resource_type: str, limit: int = DEFAULT_LIMIT) -> str:
    """Format synced items (tasks/projects/etc.) in compact form."""
    if not items:
        return f"No {resource_type} in sync result."

    shown = items[:limit]
    lines: list[str] = []

    for item in shown:
        if resource_type == "items":
            content = item.get("content", "?")
            checked = "✓" if item.get("checked") or item.get("is_completed") else "○"
            tid = item.get("id", "?")
            lines.append(f"{checked} {content} | id={tid}")
        elif resource_type == "projects":
            lines.append(f"{item.get('name', '?')} | id={item.get('id', '?')}")
        else:
            lines.append(f"{item.get('name', item.get('content', '?'))} | id={item.get('id', '?')}")

    if len(items) > len(shown):
        lines.append(f"… {len(items) - len(shown)} more")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


def format_batch_result(data: dict[str, Any]) -> str:
    """Format batch command results.

    Example::

        Sync status:
          cmd-uuid-1: ok
          cmd-uuid-2: ok
          cmd-uuid-3: error: "Invalid project_id"
        Temp ID mapping:
          tmp-1 → 12345
    """
    lines: list[str] = []

    sync_status = data.get("sync_status", {})
    if sync_status:
        lines.append("Sync status:")
        for cmd_uuid, status in sync_status.items():
            short_uuid = cmd_uuid[:8]
            if status == "ok":
                lines.append(f"  {short_uuid}: ok")
            else:
                lines.append(f"  {short_uuid}: error: {status}")

    temp_id_mapping = data.get("temp_id_mapping", {})
    if temp_id_mapping:
        lines.append("Temp ID mapping:")
        for temp_id, real_id in temp_id_mapping.items():
            lines.append(f"  {temp_id} → {real_id}")

    if not lines:
        return "Batch completed (no status details)."

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def format_stats(stats: dict[str, Any]) -> str:
    """Format productivity stats compactly.

    Example::

        Karma: 12345 (Enlightened)
        Daily goal: 5 tasks (streak: 12 days)
        Weekly goal: 25 tasks (streak: 4 weeks)
        Tasks completed: today 3, last 7 days 21
    """
    lines: list[str] = []

    if karma := stats.get("karma"):
        trend = stats.get("karma_trend", "")
        lines.append(f"Karma: {karma}" + (f" ({trend})" if trend else ""))

    goals = stats.get("goals", {})
    if daily := goals.get("daily_goal"):
        streak = goals.get("daily_streak", 0)
        lines.append(f"Daily goal: {daily} tasks (streak: {streak} days)")
    if weekly := goals.get("weekly_goal"):
        streak = goals.get("weekly_streak", 0)
        lines.append(f"Weekly goal: {weekly} tasks (streak: {streak} weeks)")

    days = stats.get("days_items", [])
    if days:
        today_count = days[0].get("total_completed", 0) if days else 0
        week_count = sum(d.get("total_completed", 0) for d in days[:7])
        lines.append(f"Tasks completed: today {today_count}, last 7 days {week_count}")

    if not lines:
        # Fallback: dump top-level keys
        for k, v in stats.items():
            if not isinstance(v, (dict, list)):
                lines.append(f"{k}: {v}")

    return "\n".join(lines) if lines else "No stats available."


# ---------------------------------------------------------------------------
# Completed Tasks
# ---------------------------------------------------------------------------


def format_completed_tasks(data: dict[str, Any], limit: int = DEFAULT_LIMIT) -> str:
    """Format completed tasks list."""
    items = data.get("items", [])
    if not items:
        return "No completed tasks found."

    shown = items[:limit]
    lines: list[str] = []

    for item in shown:
        parts: list[str] = []
        if completed := item.get("completed_at"):
            parts.append(completed[:10])
        parts.append(item.get("content", "?"))
        if tid := item.get("task_id"):
            parts.append(f"id={tid}")
        lines.append(" | ".join(parts))

    total = len(items)
    if total > len(shown):
        lines.append(f"… {total - len(shown)} more")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quick Add
# ---------------------------------------------------------------------------


def format_quick_add_result(task: dict[str, Any]) -> str:
    """Format quick add result."""
    content = task.get("content", "?")
    tid = task.get("id", "?")
    due = task.get("due")
    parts = [f"Created: {content}"]
    if due:
        parts.append(f"due={due.get('date', '?')}")
    parts.append(f"id={tid}")
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_due_date(due_str: str) -> str:
    """Render a due date with relative labels for today/tomorrow/overdue."""
    if not due_str:
        return ""
    try:
        # Handle datetime strings (has T)
        if "T" in due_str:
            dt = datetime.fromisoformat(due_str)
            due_date = dt.date()
        else:
            due_date = date.fromisoformat(due_str)

        today = date.today()
        delta = (due_date - today).days

        if delta < 0:
            return f"overdue ({due_str[:10]})"
        elif delta == 0:
            return "today"
        elif delta == 1:
            return "tomorrow"
        elif delta <= 7:
            return due_date.strftime("%A")  # Day name
        else:
            return due_str[:10]
    except (ValueError, TypeError):
        return due_str[:10] if due_str else ""
