"""Todoist Blade MCP Server — tasks, projects, sections, labels, comments, sync, batch.

Wraps the Todoist REST v2 and Sync v9 APIs via ``httpx`` as MCP tools.
Token-efficient by default: concise output, capped lists, null-field omission.

Dual-API strategy:
- REST v2 for simple CRUD, filter queries, and individual resource access
- Sync v9 for incremental sync (delta tokens), batch commands, and stats
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from todoist_blade_mcp.client import TodoistClient, TodoistError
from todoist_blade_mcp.formatters import (
    format_batch_result,
    format_collaborator_list,
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
from todoist_blade_mcp.models import DEFAULT_LIMIT, MAX_BATCH_SIZE, require_write

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transport configuration
# ---------------------------------------------------------------------------

TRANSPORT = os.environ.get("TODOIST_MCP_TRANSPORT", "stdio")
HTTP_HOST = os.environ.get("TODOIST_MCP_HOST", "127.0.0.1")
HTTP_PORT = int(os.environ.get("TODOIST_MCP_PORT", "8768"))

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "TodoistBlade",
    instructions=(
        "Todoist task management via REST v2 and Sync v9 APIs. "
        "Create, read, update, delete tasks, projects, sections, labels, and comments. "
        "Incremental sync with delta tokens. Batch commands (up to 100 per request). "
        "Filter queries using Todoist syntax (e.g. 'today & #Work', 'overdue | p1'). "
        "Write operations require TODOIST_WRITE_ENABLED=true."
    ),
)

# Lazy-initialized client
_client: TodoistClient | None = None


def _get_client() -> TodoistClient:
    """Get or create the TodoistClient singleton."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = TodoistClient()
        logger.info("TodoistClient initialised")
    return _client


def _error_response(e: TodoistError) -> str:
    """Format a client error as a user-friendly string."""
    return f"Error: {e}"


async def _run(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking client method in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)


# ===========================================================================
# PROJECT TOOLS
# ===========================================================================


@mcp.tool
async def projects_list() -> str:
    """List all projects with name, color, favorite status, and ID.

    Returns Inbox and all user projects. Use project IDs for task filtering.
    """
    try:
        projects = await _run(_get_client().list_projects)
        return format_project_list(projects)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def projects_read(
    id: Annotated[str, Field(description="Project ID")],
) -> str:
    """Get full details for a project: name, color, shared status, view style, URL."""
    try:
        project = await _run(_get_client().get_project, id)
        return format_project_detail(project)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def projects_create(
    name: Annotated[str, Field(description="Project name")],
    parent_id: Annotated[str | None, Field(description="Parent project ID for nesting")] = None,
    color: Annotated[str | None, Field(description="Color name (e.g. 'berry', 'red', 'blue')")] = None,
    is_favorite: Annotated[bool, Field(description="Pin as favorite")] = False,
    view_style: Annotated[str | None, Field(description="View: 'list' or 'board'")] = None,
) -> str:
    """Create a new project. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        project = await _run(
            _get_client().create_project,
            name=name,
            parent_id=parent_id,
            color=color,
            is_favorite=is_favorite,
            view_style=view_style,
        )
        return f"Created: {project.get('name', '?')} (id={project.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def projects_update(
    id: Annotated[str, Field(description="Project ID to update")],
    name: Annotated[str | None, Field(description="New name")] = None,
    color: Annotated[str | None, Field(description="New color")] = None,
    is_favorite: Annotated[bool | None, Field(description="Pin/unpin favorite")] = None,
    view_style: Annotated[str | None, Field(description="View: 'list' or 'board'")] = None,
) -> str:
    """Update a project. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        project = await _run(
            _get_client().update_project,
            id,
            name=name,
            color=color,
            is_favorite=is_favorite,
            view_style=view_style,
        )
        return f"Updated: {project.get('name', '?')} (id={project.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def projects_delete(
    id: Annotated[str, Field(description="Project ID to delete")],
    confirm: Annotated[bool, Field(description="Must be true to confirm deletion")] = False,
) -> str:
    """Delete a project and all its tasks. Requires TODOIST_WRITE_ENABLED=true and confirm=true."""
    if err := require_write():
        return err
    if not confirm:
        return "Error: Pass confirm=true to confirm project deletion. This deletes all tasks in the project."
    try:
        await _run(_get_client().delete_project, id)
        return f"Deleted project {id}."
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def projects_collaborators(
    id: Annotated[str, Field(description="Project ID")],
) -> str:
    """Get collaborators for a shared project: name, email, ID."""
    try:
        collabs = await _run(_get_client().get_collaborators, id)
        return format_collaborator_list(collabs)
    except TodoistError as e:
        return _error_response(e)


# ===========================================================================
# SECTION TOOLS
# ===========================================================================


@mcp.tool
async def sections_list(
    project_id: Annotated[str | None, Field(description="Filter by project ID")] = None,
) -> str:
    """List sections, optionally filtered by project. Returns name, project, ID."""
    try:
        sections = await _run(_get_client().list_sections, project_id=project_id)
        return format_section_list(sections)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def sections_create(
    name: Annotated[str, Field(description="Section name")],
    project_id: Annotated[str, Field(description="Project ID to add section to")],
    order: Annotated[int | None, Field(description="Position order")] = None,
) -> str:
    """Create a section in a project. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        section = await _run(_get_client().create_section, name=name, project_id=project_id, order=order)
        return f"Created: {section.get('name', '?')} (id={section.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def sections_update(
    id: Annotated[str, Field(description="Section ID to update")],
    name: Annotated[str, Field(description="New section name")],
) -> str:
    """Rename a section. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        section = await _run(_get_client().update_section, id, name=name)
        return f"Updated: {section.get('name', '?')} (id={section.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def sections_delete(
    id: Annotated[str, Field(description="Section ID to delete")],
    confirm: Annotated[bool, Field(description="Must be true to confirm deletion")] = False,
) -> str:
    """Delete a section. Tasks in it move to the project root. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    if not confirm:
        return "Error: Pass confirm=true to confirm section deletion."
    try:
        await _run(_get_client().delete_section, id)
        return f"Deleted section {id}."
    except TodoistError as e:
        return _error_response(e)


# ===========================================================================
# TASK TOOLS
# ===========================================================================


@mcp.tool
async def tasks_list(
    project_id: Annotated[str | None, Field(description="Filter by project ID")] = None,
    section_id: Annotated[str | None, Field(description="Filter by section ID")] = None,
    label: Annotated[str | None, Field(description="Filter by label name")] = None,
    filter: Annotated[
        str | None,
        Field(description="Todoist filter query (e.g. 'today', 'overdue', 'today & #Work', 'p1', '@errands')"),
    ] = None,
    limit: Annotated[int, Field(description="Max results (default: 20)")] = DEFAULT_LIMIT,
) -> str:
    """List active tasks with filters. Returns priority, due, labels, content, ID.

    Supports Todoist's filter query syntax for powerful searches:
    ``today``, ``overdue``, ``p1``, ``#ProjectName``, ``@label``,
    ``today & #Work``, ``overdue | p1``, ``due before: next Monday``.
    """
    try:
        tasks = await _run(
            _get_client().list_tasks,
            project_id=project_id,
            section_id=section_id,
            label=label,
            filter_query=filter,
            limit=limit,
        )
        return format_task_list(tasks, limit=limit)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_read(
    id: Annotated[str, Field(description="Task ID")],
) -> str:
    """Get full task details: content, description, project, priority, due, labels, URL."""
    try:
        task = await _run(_get_client().get_task, id)
        return format_task_detail(task)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_search(
    query: Annotated[
        str, Field(description="Todoist filter query (e.g. 'today & #Work', '@urgent', 'search: meeting')")
    ],
    limit: Annotated[int, Field(description="Max results (default: 20)")] = DEFAULT_LIMIT,
) -> str:
    """Search tasks using Todoist filter syntax. More expressive than tasks_list filters.

    Examples: ``today``, ``overdue``, ``#Work & p1``, ``@errands & due before: friday``,
    ``search: quarterly report``, ``assigned to: me & !subtask``.
    """
    try:
        tasks = await _run(_get_client().list_tasks, filter_query=query, limit=limit)
        return format_task_list(tasks, limit=limit)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_create(
    content: Annotated[str, Field(description="Task content/title")],
    description: Annotated[str | None, Field(description="Task description/notes")] = None,
    project_id: Annotated[str | None, Field(description="Project ID (default: Inbox)")] = None,
    section_id: Annotated[str | None, Field(description="Section ID within project")] = None,
    parent_id: Annotated[str | None, Field(description="Parent task ID (creates subtask)")] = None,
    labels: Annotated[str | None, Field(description="Comma-separated label names")] = None,
    priority: Annotated[int, Field(description="Priority 1 (normal) to 4 (urgent)")] = 1,
    due_string: Annotated[str | None, Field(description="Natural language due date (e.g. 'tomorrow 2pm')")] = None,
    due_date: Annotated[str | None, Field(description="Due date YYYY-MM-DD (all-day)")] = None,
    assignee_id: Annotated[str | None, Field(description="Assignee user ID (shared projects)")] = None,
) -> str:
    """Create a new task. Requires TODOIST_WRITE_ENABLED=true.

    Priority: 1=normal, 2=medium, 3=high, 4=urgent.
    Use ``due_string`` for natural language ("tomorrow", "every Monday", "Jan 15 at 3pm").
    """
    if err := require_write():
        return err
    try:
        label_list = [lb.strip() for lb in labels.split(",") if lb.strip()] if labels else None
        task = await _run(
            _get_client().create_task,
            content=content,
            description=description,
            project_id=project_id,
            section_id=section_id,
            parent_id=parent_id,
            labels=label_list,
            priority=priority,
            due_string=due_string,
            due_date=due_date,
            assignee_id=assignee_id,
        )
        return f"Created: {task.get('content', '?')} (id={task.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_update(
    id: Annotated[str, Field(description="Task ID to update")],
    content: Annotated[str | None, Field(description="New content/title")] = None,
    description: Annotated[str | None, Field(description="New description")] = None,
    labels: Annotated[str | None, Field(description="New comma-separated label names (replaces existing)")] = None,
    priority: Annotated[int | None, Field(description="New priority 1-4")] = None,
    due_string: Annotated[str | None, Field(description="New due date (natural language)")] = None,
    due_date: Annotated[str | None, Field(description="New due date YYYY-MM-DD")] = None,
    assignee_id: Annotated[str | None, Field(description="New assignee user ID")] = None,
) -> str:
    """Update a task's fields. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        fields: dict[str, Any] = {}
        if content is not None:
            fields["content"] = content
        if description is not None:
            fields["description"] = description
        if labels is not None:
            fields["labels"] = [lb.strip() for lb in labels.split(",") if lb.strip()]
        if priority is not None:
            fields["priority"] = priority
        if due_string is not None:
            fields["due_string"] = due_string
        elif due_date is not None:
            fields["due_date"] = due_date
        if assignee_id is not None:
            fields["assignee_id"] = assignee_id
        if not fields:
            return "Error: No fields to update."
        task = await _run(_get_client().update_task, id, **fields)
        return f"Updated: {task.get('content', '?')} (id={task.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_complete(
    id: Annotated[str, Field(description="Task ID to complete")],
) -> str:
    """Mark a task as complete. Requires TODOIST_WRITE_ENABLED=true.

    Recurring tasks advance to the next occurrence instead of closing.
    """
    if err := require_write():
        return err
    try:
        await _run(_get_client().close_task, id)
        return f"Completed task {id}."
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_reopen(
    id: Annotated[str, Field(description="Task ID to reopen")],
) -> str:
    """Reopen a completed task. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        await _run(_get_client().reopen_task, id)
        return f"Reopened task {id}."
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_delete(
    id: Annotated[str, Field(description="Task ID to delete")],
    confirm: Annotated[bool, Field(description="Must be true to confirm deletion")] = False,
) -> str:
    """Permanently delete a task. Requires TODOIST_WRITE_ENABLED=true and confirm=true."""
    if err := require_write():
        return err
    if not confirm:
        return "Error: Pass confirm=true to confirm task deletion. This cannot be undone."
    try:
        await _run(_get_client().delete_task, id)
        return f"Deleted task {id}."
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def tasks_quick_add(
    text: Annotated[
        str, Field(description="Natural language task text (e.g. 'Buy milk #Shopping @errands tomorrow p2')")
    ],
) -> str:
    """Quick add a task with natural language parsing. Requires TODOIST_WRITE_ENABLED=true.

    Todoist parses: ``#Project``, ``@label``, ``p1``-``p4``, and date expressions from the text.
    Example: ``Buy milk #Shopping @errands tomorrow p2``
    """
    if err := require_write():
        return err
    try:
        task = await _run(_get_client().quick_add, text)
        return format_quick_add_result(task)
    except TodoistError as e:
        return _error_response(e)


# ===========================================================================
# COMMENT TOOLS
# ===========================================================================


@mcp.tool
async def comments_list(
    task_id: Annotated[str | None, Field(description="Task ID to get comments for")] = None,
    project_id: Annotated[str | None, Field(description="Project ID to get comments for")] = None,
    limit: Annotated[int, Field(description="Max results (default: 20)")] = DEFAULT_LIMIT,
) -> str:
    """List comments on a task or project. Provide either task_id or project_id."""
    try:
        comments = await _run(_get_client().list_comments, task_id=task_id, project_id=project_id)
        return format_comment_list(comments, limit=limit)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def comments_create(
    content: Annotated[str, Field(description="Comment text (supports Markdown)")],
    task_id: Annotated[str | None, Field(description="Task ID to comment on")] = None,
    project_id: Annotated[str | None, Field(description="Project ID to comment on")] = None,
) -> str:
    """Add a comment to a task or project. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        comment = await _run(
            _get_client().create_comment,
            content=content,
            task_id=task_id,
            project_id=project_id,
        )
        return f"Comment added (id={comment.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def comments_update(
    id: Annotated[str, Field(description="Comment ID to update")],
    content: Annotated[str, Field(description="New comment text")],
) -> str:
    """Update a comment's content. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        comment = await _run(_get_client().update_comment, id, content=content)
        return f"Updated comment {comment.get('id', '?')}."
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def comments_delete(
    id: Annotated[str, Field(description="Comment ID to delete")],
) -> str:
    """Delete a comment. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        await _run(_get_client().delete_comment, id)
        return f"Deleted comment {id}."
    except TodoistError as e:
        return _error_response(e)


# ===========================================================================
# LABEL TOOLS
# ===========================================================================


@mcp.tool
async def labels_list() -> str:
    """List all personal labels with name, color, and ID.

    Also shows shared labels from collaborative projects.
    """
    try:
        personal = await _run(_get_client().list_labels)
        result = format_label_list(personal)
        try:
            shared = await _run(_get_client().list_shared_labels)
            if shared:
                result += "\n\nShared labels:\n" + format_shared_labels(shared)
        except TodoistError:
            pass  # Shared labels may fail on free plans
        return result
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def labels_create(
    name: Annotated[str, Field(description="Label name (without @)")],
    color: Annotated[str | None, Field(description="Color name")] = None,
    is_favorite: Annotated[bool, Field(description="Pin as favorite")] = False,
) -> str:
    """Create a personal label. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        label = await _run(
            _get_client().create_label,
            name=name,
            color=color,
            is_favorite=is_favorite,
        )
        return f"Created: @{label.get('name', '?')} (id={label.get('id', '?')})"
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def labels_delete(
    id: Annotated[str, Field(description="Label ID to delete")],
) -> str:
    """Delete a personal label. Removes from all tasks. Requires TODOIST_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        await _run(_get_client().delete_label, id)
        return f"Deleted label {id}."
    except TodoistError as e:
        return _error_response(e)


# ===========================================================================
# SYNC TOOLS
# ===========================================================================


@mcp.tool
async def todoist_sync(
    resource_types: Annotated[
        str | None,
        Field(description="Comma-separated resource types (default: 'items,projects,sections,labels')"),
    ] = None,
    full_sync: Annotated[bool, Field(description="Force full sync instead of incremental")] = False,
) -> str:
    """Incremental sync — returns only items changed since last sync.

    First call returns all data. Subsequent calls return only deltas.
    Use ``full_sync=true`` to reset and fetch everything.

    Resource types: items, projects, sections, labels, filters, reminders.
    """
    try:
        types = [t.strip() for t in resource_types.split(",") if t.strip()] if resource_types else None
        token = "*" if full_sync else None
        if full_sync:
            await _run(_get_client().reset_sync_token)
        data = await _run(_get_client().sync, resource_types=types, sync_token=token)
        result = format_sync_result(data)

        # Show first few items of each changed resource
        for rtype in ["items", "projects", "sections", "labels"]:
            items = data.get(rtype, [])
            if items:
                result += f"\n\n{rtype.capitalize()} ({len(items)}):\n"
                result += format_sync_items(items, rtype, limit=10)

        return result
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def todoist_batch(
    commands: Annotated[
        str,
        Field(
            description=(
                'JSON array of sync commands. Each: {"type": "item_add", "args": {...}}. '
                "Types: item_add, item_update, item_move, item_close, item_delete, "
                "project_add, project_update, project_delete, section_add, section_update, "
                "section_delete, label_add, label_update, label_delete. "
                "Use temp_id for referencing items created in the same batch."
            )
        ),
    ],
) -> str:
    """Execute batch commands via Sync API (up to 100 per request). Requires TODOIST_WRITE_ENABLED=true.

    Each command is executed atomically. Use ``temp_id`` to reference items
    created within the same batch (e.g. create project, then add tasks to it).

    Example: ``[{"type": "item_add", "temp_id": "t1", "args": {"content": "Task 1", "project_id": "123"}}]``
    """
    if err := require_write():
        return err
    try:
        cmd_list = json.loads(commands)
        if not isinstance(cmd_list, list):
            return "Error: Commands must be a JSON array."
        if len(cmd_list) > MAX_BATCH_SIZE:
            return f"Error: Maximum {MAX_BATCH_SIZE} commands per batch. Got {len(cmd_list)}."
        data = await _run(_get_client().batch, cmd_list)
        return format_batch_result(data)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON — {e}"
    except TodoistError as e:
        return _error_response(e)


# ===========================================================================
# PRODUCTIVITY TOOLS
# ===========================================================================


@mcp.tool
async def todoist_stats() -> str:
    """Get personal productivity stats: karma, daily/weekly goals, streaks, completion counts."""
    try:
        stats = await _run(_get_client().get_stats)
        return format_stats(stats)
    except TodoistError as e:
        return _error_response(e)


@mcp.tool
async def todoist_completed(
    project_id: Annotated[str | None, Field(description="Filter by project ID")] = None,
    limit: Annotated[int, Field(description="Max results (default: 20, max: 200)")] = DEFAULT_LIMIT,
) -> str:
    """Get completed task history (requires Todoist Pro). Returns completion date, content, ID."""
    try:
        data = await _run(_get_client().get_completed_tasks, project_id=project_id, limit=limit)
        return format_completed_tasks(data, limit=limit)
    except TodoistError as e:
        return _error_response(e)


# ===========================================================================
# Entry point
# ===========================================================================


def main() -> None:
    """Main entry point for the Todoist Blade MCP server."""
    if TRANSPORT == "http":
        from starlette.middleware import Middleware

        from todoist_blade_mcp.auth import BearerAuthMiddleware, get_bearer_token

        bearer = get_bearer_token()
        logger.info("Starting HTTP transport on %s:%s", HTTP_HOST, HTTP_PORT)
        if bearer:
            logger.info("Bearer token auth enabled (TODOIST_MCP_API_TOKEN is set)")
        else:
            logger.info("Bearer token auth disabled (no TODOIST_MCP_API_TOKEN)")
        mcp.run(
            transport="http",
            host=HTTP_HOST,
            port=HTTP_PORT,
            middleware=[Middleware(BearerAuthMiddleware)],
        )
    else:
        mcp.run()
