---
name: todoist-blade
description: Todoist task management — CRUD, sync, batch, filter queries, productivity stats
version: 0.1.0
permissions:
  read:
    - projects_list
    - projects_read
    - projects_collaborators
    - sections_list
    - tasks_list
    - tasks_read
    - tasks_search
    - comments_list
    - labels_list
    - todoist_sync
    - todoist_stats
    - todoist_completed
  write:
    - projects_create
    - projects_update
    - projects_delete
    - sections_create
    - sections_update
    - sections_delete
    - tasks_create
    - tasks_update
    - tasks_complete
    - tasks_reopen
    - tasks_delete
    - tasks_quick_add
    - comments_create
    - comments_update
    - comments_delete
    - labels_create
    - labels_delete
    - todoist_batch
---

# Todoist Blade MCP — Skill Guide

## Token Efficiency Rules (MANDATORY)

1. **Use `limit=` on list tools** — default is 20, reduce for browsing
2. **Use `tasks_search` with filter queries** — don't list all tasks then filter manually
3. **Use `projects_list` to get project IDs** — required for task filtering
4. **Use `todoist_sync` for bulk reads** — single request returns all changed items
5. **Use `todoist_batch` for bulk writes** — up to 100 commands in one request
6. **Never list all tasks** — always filter by project, label, date, or query
7. **Use `tasks_quick_add` for NLP** — parses #project, @label, p1-p4, dates from text

## Quick Start — 5 Most Common Operations

```
tasks_list limit=10                              → Recent tasks
tasks_search query="today"                       → Today's tasks
tasks_read id="123"                              → Full task details
projects_list                                    → All projects
tasks_create content="Buy milk" due_string="tomorrow"  → New task
```

## Tool Reference

### Projects (6 tools)
- **projects_list** — All projects with name, color, ID. Use IDs for task filtering.
- **projects_read** — Full project details: name, color, shared, view style, URL.
- **projects_create** ✏️ — Create project. Optional: parent_id, color, view_style.
- **projects_update** ✏️ — Update project name, color, favorite, view style.
- **projects_delete** ✏️ — Delete project + all tasks. Requires `confirm=true`.
- **projects_collaborators** — Collaborators for a shared project.

### Sections (4 tools)
- **sections_list** — Sections with name, project, ID. Filter by project_id.
- **sections_create** ✏️ — Create section in a project.
- **sections_update** ✏️ — Rename a section.
- **sections_delete** ✏️ — Delete section. Requires `confirm=true`.

### Tasks (8 tools)
- **tasks_list** — Active tasks with filters (project, section, label, query). Returns priority, due, labels, content.
- **tasks_read** — Full task: content, description, project, priority, due, labels, URL.
- **tasks_search** — Search using Todoist filter syntax. Most powerful query tool.
- **tasks_create** ✏️ — Create task with content, project, priority, due, labels.
- **tasks_update** ✏️ — Update task fields (content, priority, due, labels, etc.).
- **tasks_complete** ✏️ — Mark complete. Recurring tasks advance to next occurrence.
- **tasks_reopen** ✏️ — Reopen a completed task.
- **tasks_delete** ✏️ — Permanent delete. Requires `confirm=true`.
- **tasks_quick_add** ✏️ — Natural language: "Buy milk #Shopping @errands tomorrow p2".

### Comments (4 tools)
- **comments_list** — Comments on a task or project.
- **comments_create** ✏️ — Add comment to task or project (Markdown).
- **comments_update** ✏️ — Edit comment content.
- **comments_delete** ✏️ — Delete a comment.

### Labels (3 tools)
- **labels_list** — Personal + shared labels with name, color, ID.
- **labels_create** ✏️ — Create personal label.
- **labels_delete** ✏️ — Delete label (removes from all tasks).

### Sync (2 tools)
- **todoist_sync** — Incremental sync (delta tokens). First call = full data, subsequent = changes only.
- **todoist_batch** ✏️ — Batch up to 100 commands in one request. Supports temp_id for atomic creates.

### Productivity (2 tools)
- **todoist_stats** — Karma, daily/weekly goals, streaks, completion counts.
- **todoist_completed** — Completed task history (Pro feature).

✏️ = requires TODOIST_WRITE_ENABLED=true

## Todoist Filter Query Syntax

Used in `tasks_list filter=` and `tasks_search query=`:

| Query | Meaning |
|-------|---------|
| `today` | Tasks due today |
| `overdue` | Overdue tasks |
| `tomorrow` | Tasks due tomorrow |
| `7 days` | Tasks due in the next 7 days |
| `p1` | Priority 1 (urgent) tasks |
| `#Work` | Tasks in "Work" project |
| `@errands` | Tasks with "errands" label |
| `today & #Work` | Today's Work tasks |
| `overdue \| p1` | Overdue OR priority 1 |
| `no date` | Tasks without a due date |
| `recurring` | Recurring tasks |
| `assigned to: me` | Tasks assigned to you |
| `search: quarterly` | Full-text search |
| `due before: next Monday` | Due before a date |

## Workflow Examples

### Daily Review
```
1. tasks_search query="today"                    → Today's tasks
2. tasks_search query="overdue"                  → Overdue tasks
3. todoist_stats                                 → Productivity overview
```

### Project Planning
```
1. projects_list                                 → Find project ID
2. sections_list project_id="123"                → View sections
3. tasks_list project_id="123" limit=50          → All project tasks
4. tasks_create content="..." project_id="123" section_id="456"
```

### Batch Task Creation
```
todoist_batch commands='[
  {"type": "item_add", "temp_id": "t1", "args": {"content": "Task 1", "project_id": "123"}},
  {"type": "item_add", "temp_id": "t2", "args": {"content": "Task 2", "project_id": "123"}},
  {"type": "item_add", "temp_id": "t3", "args": {"content": "Task 3", "project_id": "123"}}
]'
```

### Incremental Sync
```
1. todoist_sync                                  → Full sync (first call)
   (sync token cached automatically)
2. todoist_sync                                  → Delta only (subsequent calls)
   (use full_sync=true to reset)
```

### Quick Capture
```
tasks_quick_add text="Review PR #123 #DevOps @urgent tomorrow p1"
```

## Common Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `id` | Resource ID | `id="123456"` |
| `project_id` | Project filter | `project_id="123"` |
| `section_id` | Section filter | `section_id="456"` |
| `label` | Label name filter | `label="urgent"` |
| `filter` / `query` | Todoist filter syntax | `filter="today & #Work"` |
| `content` | Task/comment text | `content="Buy milk"` |
| `priority` | 1 (normal) to 4 (urgent) | `priority=4` |
| `due_string` | Natural language date | `due_string="tomorrow 2pm"` |
| `due_date` | ISO date (all-day) | `due_date="2026-04-01"` |
| `labels` | Comma-separated names | `labels="work,urgent"` |
| `limit` | Max results (default: 20) | `limit=10` |
| `confirm` | Required for deletes | `confirm=true` |

## Security Notes

- Write operations blocked unless `TODOIST_WRITE_ENABLED=true`
- Destructive operations (delete) require `confirm=true`
- `todoist_batch` capped at 100 commands per request
- API token never appears in tool output
- Sync token cached locally at `~/.todoist-blade-mcp/sync_token`
