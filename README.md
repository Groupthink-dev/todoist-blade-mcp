# todoist-blade-mcp

A high-performance [Model Context Protocol](https://modelcontextprotocol.io) server for Todoist. Dual API strategy (REST v2 + Sync v9), token-efficient output, and a write-gated safety model.

## Why this over the official Todoist MCP?

| Capability | Official | todoist-blade-mcp |
|---|---|---|
| **API coverage** | REST v2 only | REST v2 + Sync v9 |
| **Batch commands** | One op per call | Up to 100 ops in a single `todoist_batch` call via Sync API |
| **Incremental sync** | Not supported | Delta tokens — only fetch what changed since last sync |
| **Output format** | JSON blobs | Pipe-delimited, null-omitted — 40-60% fewer tokens |
| **Write safety** | Open | Write-gated: mutations require explicit `TODOIST_WRITE=true` |
| **Filter queries** | Basic | Full Todoist filter syntax (`#Work & due before: tomorrow`) |
| **Productivity stats** | Not exposed | Karma, streaks, daily/weekly goals |
| **Completed tasks** | Not exposed | Full completion history (Pro accounts) |
| **Quick add** | Not exposed | Natural language parsing (`Buy milk tomorrow p1 #Shopping`) |
| **Tool count** | ~15 | 30 |

**The key differentiator is the Sync v9 integration.** No other Todoist MCP server uses it. This unlocks batch commands (bulk-create 50 tasks in one call), incremental sync (delta tokens eliminate redundant fetches), and access to endpoints REST v2 simply doesn't expose.

## Features

- **30 tools** across 7 categories — projects, sections, tasks, comments, labels, sync, productivity
- **Dual API client** — REST v2 for simple CRUD, Sync v9 for batch operations and incremental sync
- **Token-efficient formatters** — pipe-delimited output with null omission, not verbose JSON
- **Write-gated safety** — all mutations disabled by default; enable with `TODOIST_WRITE=true`
- **Destructive confirmation** — delete operations require explicit `confirm=true` parameter
- **Filter query support** — full Todoist filter syntax in `tasks_list` and `tasks_search`
- **Natural language quick-add** — dates, priorities, labels, and projects parsed from plain text
- **HTTP transport with auth** — Bearer token middleware for remote deployments

## Quick Start

```bash
# Clone
git clone https://github.com/groupthink-dev/todoist-blade-mcp.git
cd todoist-blade-mcp

# Install
pip install -e .

# Run (read-only by default)
export TODOIST_API_TOKEN="your-api-token"
todoist-blade-mcp
```

To enable write operations:

```bash
export TODOIST_WRITE=true
```

## Tools

### Projects (6)

| Tool | Description | Gated |
|---|---|---|
| `projects_list` | List all projects with hierarchy | |
| `projects_read` | Get project details by ID | |
| `projects_create` | Create a new project | write |
| `projects_update` | Update project name, colour, etc. | write |
| `projects_delete` | Delete a project | write + confirm |
| `projects_collaborators` | List project collaborators | |

### Sections (4)

| Tool | Description | Gated |
|---|---|---|
| `sections_list` | List sections in a project | |
| `sections_create` | Create a section | write |
| `sections_update` | Rename a section | write |
| `sections_delete` | Delete a section | write + confirm |

### Tasks (9)

| Tool | Description | Gated |
|---|---|---|
| `tasks_list` | List tasks with filter query support | |
| `tasks_read` | Get task details by ID | |
| `tasks_search` | Search with advanced Todoist filter syntax | |
| `tasks_create` | Create a task with full metadata | write |
| `tasks_update` | Update task fields | write |
| `tasks_complete` | Mark a task complete | write |
| `tasks_reopen` | Reopen a completed task | write |
| `tasks_delete` | Delete a task | write + confirm |
| `tasks_quick_add` | Natural language task creation | write |

### Comments (4)

| Tool | Description | Gated |
|---|---|---|
| `comments_list` | List comments on a task or project | |
| `comments_create` | Add a comment | write |
| `comments_update` | Edit a comment | write |
| `comments_delete` | Delete a comment | write |

### Labels (3)

| Tool | Description | Gated |
|---|---|---|
| `labels_list` | List personal and shared labels | |
| `labels_create` | Create a label | write |
| `labels_delete` | Delete a label | write |

### Sync (2)

| Tool | Description | Gated |
|---|---|---|
| `todoist_sync` | Incremental sync with delta tokens — only returns changes since last sync | |
| `todoist_batch` | Execute up to 100 commands in a single Sync API call | write |

### Productivity (2)

| Tool | Description | Gated |
|---|---|---|
| `todoist_stats` | Karma score, streaks, daily/weekly goals | |
| `todoist_completed` | Completion history with date ranges (Pro) | |

## Filter Query Examples

`tasks_list` and `tasks_search` accept [Todoist filter syntax](https://todoist.com/help/articles/introduction-to-filters-702348ff):

```
today                          # Due today
overdue | today                # Overdue or due today
#Work & due before: tomorrow   # Work project, due before tomorrow
p1 & no date                   # Priority 1 with no due date
@waiting & !subtask            # Label "waiting", exclude subtasks
assigned to: me & due: week    # Assigned to me, due this week
created before: -30 days       # Created in the last 30 days
```

## Security Model

| Layer | Behaviour |
|---|---|
| **Read-only default** | `TODOIST_WRITE=false` — all mutations return an error |
| **Write gate** | Set `TODOIST_WRITE=true` to enable create/update/delete/complete tools |
| **Delete confirmation** | `projects_delete`, `sections_delete`, `tasks_delete` require `confirm=true` |
| **Token scoping** | Server uses only the permissions granted to your Todoist API token |
| **HTTP auth** | Bearer token middleware for remote/HTTP transport deployments |

## Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "todoist-blade-mcp",
      "env": {
        "TODOIST_API_TOKEN": "your-api-token",
        "TODOIST_WRITE": "true"
      }
    }
  }
}
```

### Claude Code

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "todoist-blade-mcp",
      "env": {
        "TODOIST_API_TOKEN": "your-api-token",
        "TODOIST_WRITE": "true"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TODOIST_API_TOKEN` | Yes | — | Todoist API token ([Settings > Integrations > Developer](https://todoist.com/app/settings/integrations/developer)) |
| `TODOIST_WRITE` | No | `false` | Enable write operations (create, update, delete, complete) |
| `TODOIST_BATCH_LIMIT` | No | `100` | Max commands per `todoist_batch` call |
| `TODOIST_TRANSPORT` | No | `stdio` | Transport mode: `stdio` or `http` |
| `TODOIST_HTTP_PORT` | No | `8080` | Port for HTTP transport |
| `TODOIST_HTTP_TOKEN` | No | — | Bearer token for HTTP transport auth |

## Architecture

```
src/todoist_blade_mcp/
├── server.py       — FastMCP server, 30 @mcp.tool decorators
├── client.py       — Dual API client (REST v2 + Sync v9), delta tokens
├── formatters.py   — Token-efficient output (pipe-delimited, null omission)
├── models.py       — Config, write-gate, batch limits
└── auth.py         — Bearer token middleware for HTTP transport
```

**REST v2** handles individual CRUD — get a task, create a project, post a comment. Straightforward request/response.

**Sync v9** handles everything REST can't. Incremental sync uses a `sync_token` (delta token) so subsequent calls only return what changed. Batch mode packs up to 100 heterogeneous commands (create tasks, move sections, complete items) into a single API call and returns per-command results.

**Formatters** convert API responses to pipe-delimited text with null fields omitted. A task that would be 800 tokens as formatted JSON becomes ~300 tokens. Over a multi-turn conversation this compounds significantly.

## Development

```bash
# Install in development mode
make install-dev

# Run tests
make test

# Lint
make lint

# Type check
make typecheck

# Format
make fmt
```

## License

MIT
