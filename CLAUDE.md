# Todoist Blade MCP — Developer Context

Todoist MCP server following the Sidereal blade pattern. Token-efficient, write-gated, dual REST+Sync API.

## Project Structure

```
src/todoist_blade_mcp/
├── server.py      — FastMCP server, 28 @mcp.tool definitions
├── client.py      — TodoistClient (httpx, REST v2 + Sync v9), lazy singleton
├── formatters.py  — Token-efficient output (pipe-delimited, null omission)
├── models.py      — Constants, exceptions, write gate
└── auth.py        — Bearer token middleware for HTTP transport
```

## Key Commands

- `make install-dev` — Install with dev+test deps
- `make test` — Run unit tests (excludes e2e)
- `make test-cov` — Tests with coverage
- `make test-e2e` — Live API tests (needs TODOIST_E2E=1 + TODOIST_API_TOKEN)
- `make lint` — Ruff linter
- `make check` — All quality checks (lint + format + type-check)

## Code Conventions

- Python 3.12+ (PEP 604 unions, walrus operator)
- Type hints everywhere, mypy strict
- FastMCP 2.0+ tool definitions with Annotated[..., Field(description=...)]
- All client methods synchronous, wrapped with asyncio.to_thread() in server
- httpx for HTTP (no SDK dependency)
- Conventional commits

## Testing

- `tests/conftest.py` — Shared fixtures, mock httpx
- `tests/test_client.py` — Client method tests (mocked HTTP)
- `tests/test_formatters.py` — Pure formatter tests
- `tests/test_server.py` — Async tool tests (mocked client)
- `tests/e2e/` — Live API tests (gated by TODOIST_E2E=1)

## Dual API Strategy

- **REST v2** (`api.todoist.com/rest/v2`): CRUD, filter queries, individual resources
- **Sync v9** (`api.todoist.com/sync/v9`): delta sync, batch commands, stats, completed tasks
