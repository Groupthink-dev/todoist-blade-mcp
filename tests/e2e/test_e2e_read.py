"""E2E read-only tests against live Todoist API."""

from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestE2EProjects:
    def test_list_projects(self, live_client):
        projects = live_client.list_projects()
        assert len(projects) > 0
        # At least Inbox should exist
        inbox = [p for p in projects if p.get("is_inbox_project")]
        assert len(inbox) == 1

    def test_get_project(self, live_client):
        projects = live_client.list_projects()
        project = live_client.get_project(str(projects[0]["id"]))
        assert "name" in project


@pytest.mark.e2e
class TestE2ETasks:
    def test_list_tasks(self, live_client):
        tasks = live_client.list_tasks(limit=5)
        assert isinstance(tasks, list)

    def test_list_with_filter(self, live_client):
        tasks = live_client.list_tasks(filter_query="all", limit=5)
        assert isinstance(tasks, list)


@pytest.mark.e2e
class TestE2ELabels:
    def test_list_labels(self, live_client):
        labels = live_client.list_labels()
        assert isinstance(labels, list)


@pytest.mark.e2e
class TestE2ESync:
    def test_full_sync(self, live_client):
        data = live_client.sync(sync_token="*")
        assert "sync_token" in data
        assert data.get("full_sync") is True

    def test_incremental_sync(self, live_client):
        # First: full sync to get token
        data1 = live_client.sync(sync_token="*")
        token = data1["sync_token"]
        # Second: incremental
        data2 = live_client.sync(sync_token=token)
        assert "sync_token" in data2
        assert data2.get("full_sync") is False
