# todoist-blade-mcp

Todoist MCP server for Claude Code and other MCP clients. Token-efficient, write-gated, with incremental sync and batch commands.

## Features

- **28 tools** covering tasks, projects, sections, labels, comments, sync, batch, and stats
- **Dual API**: REST v2 for CRUD + Sync v9 for incremental sync and batch commands
- **Token-efficient output**: pipe-delimited, null omission, capped lists
- **Write gating**: mutations disabled by default (`TODOIST_WRITE_ENABLED=false`)
- **Filter queries**: full Todoist filter syntax (`today & #Work`, `overdue | p1`)
- **Incremental sync**: delta tokens — only fetch what changed since last sync
- **Batch commands**: up to 100 operations in a single API call
- **Sidereal compatible**: implements `tasks-v1` service contract

## Quick Start

```bash
# Install
uv sync

# Configure
export TODOIST_API_TOKEN="your-token-here"
export TODOIST_WRITE_ENABLED=true  # optional: enable writes

# Run (stdio)
uv run todoist-blade-mcp

# Run (HTTP)
TODOIST_MCP_TRANSPORT=http uv run todoist-blade-mcp
```

### Claude Code config

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "uv",
      "args": ["--directory", "/path/to/todoist-blade-mcp", "run", "todoist-blade-mcp"],
      "env": {
        "TODOIST_API_TOKEN": "your-token-here",
        "TODOIST_WRITE_ENABLED": "false"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TODOIST_API_TOKEN` | Yes | — | Todoist API token |
| `TODOIST_WRITE_ENABLED` | No | `false` | Enable write operations |
| `TODOIST_MCP_TRANSPORT` | No | `stdio` | Transport: `stdio` or `http` |
| `TODOIST_MCP_HOST` | No | `127.0.0.1` | HTTP host |
| `TODOIST_MCP_PORT` | No | `8768` | HTTP port |
| `TODOIST_MCP_API_TOKEN` | No | — | Bearer auth for HTTP transport |

## Development

```bash
make install-dev   # Install with dev deps
make test          # Run unit tests
make test-cov      # Tests with coverage
make lint          # Ruff linter
make check         # All quality checks
```

## License

MIT
