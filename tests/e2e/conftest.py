"""E2E test configuration — requires live Todoist account."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip e2e tests unless TODOIST_E2E=1 is set."""
    if os.environ.get("TODOIST_E2E") != "1":
        skip = pytest.mark.skip(reason="TODOIST_E2E=1 not set")
        for item in items:
            if "e2e" in item.nodeid:
                item.add_marker(skip)


@pytest.fixture(scope="session")
def live_client():
    """Create a TodoistClient with a real API token."""
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        pytest.skip("TODOIST_API_TOKEN not set")

    from todoist_blade_mcp.client import TodoistClient

    client = TodoistClient(api_token=token)
    # Health check
    projects = client.list_projects()
    assert len(projects) > 0, "Health check failed — no projects found"
    return client
