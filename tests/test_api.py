"""Tests for things.http API endpoints."""

import os
import sys
from pathlib import Path

# Set required env before importing main
os.environ["THINGS_PASSWORD"] = "test-secret"

# Ensure main.py is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Mock things.py before importing main
mock_things = MagicMock()
sys.modules["things"] = mock_things

# Now we can import main (it will use our mock)
import main  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)

AUTH = ("things", "test-secret")


def _auth():
    return {"Authorization": "Basic dGhpbmdzOnRlc3Qtc2VjcmV0"}


@pytest.fixture(autouse=True)
def reset_mock():
    mock_things.reset_mock()
    yield
    mock_things.reset_mock()


# --- Auth tests ---


def test_unauthorized():
    """All endpoints should return 401 without auth."""
    resp = client.get("/today")
    assert resp.status_code == 401


def test_wrong_password():
    """Wrong password should return 401."""
    resp = client.get("/today", headers={"Authorization": "Basic dGhpbmdzOndyb25n"})
    assert resp.status_code == 401


# --- Read endpoint tests ---


@patch("main.things.today")
def test_today(today_fn):
    today_fn.return_value = [{"uuid": "abc", "title": "Task 1"}]
    resp = client.get("/today", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == [{"uuid": "abc", "title": "Task 1"}]


@patch("main.things.inbox")
def test_inbox(inbox_fn):
    inbox_fn.return_value = []
    resp = client.get("/inbox", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == []


@patch("main.things.projects")
def test_projects(projects_fn):
    projects_fn.return_value = [{"uuid": "p1", "title": "Project A"}]
    resp = client.get("/projects", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.areas")
def test_areas(areas_fn):
    areas_fn.return_value = [{"uuid": "a1", "title": "Health"}]
    resp = client.get("/areas", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.tags")
def test_tags(tags_fn):
    tags_fn.return_value = [{"uuid": "t1", "title": "work"}]
    resp = client.get("/tags", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.logbook")
def test_logbook(logbook_fn):
    logbook_fn.return_value = []
    resp = client.get("/logbook", headers=_auth())
    assert resp.status_code == 200


# --- New endpoints ---


@patch("main.things.search")
def test_search_no_query(search_fn):
    """Empty query returns empty list without calling search."""
    resp = client.get("/search", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == []
    search_fn.assert_not_called()


@patch("main.things.search")
def test_search_with_query(search_fn):
    """Search with a query calls things.search."""
    search_fn.return_value = [
        {"uuid": "s1", "title": "Meeting notes", "type": "to-do"}
    ]
    resp = client.get("/search?q=meeting", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == [
        {"uuid": "s1", "title": "Meeting notes", "type": "to-do"}
    ]
    search_fn.assert_called_once_with("meeting")


@patch("main.things.search")
def test_search_special_chars(search_fn):
    """Search should handle special characters."""
    search_fn.return_value = []
    resp = client.get("/search?q=todo%20%23urgent", headers=_auth())
    assert resp.status_code == 200
    search_fn.assert_called_once_with("todo #urgent")


@patch("main.things.deadlines")
def test_deadlines(deadlines_fn):
    """Deadlines endpoint returns tasks with deadlines."""
    deadlines_fn.return_value = [
        {"uuid": "d1", "title": "Report", "deadline": "2026-06-01"},
    ]
    resp = client.get("/deadlines", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == [
        {"uuid": "d1", "title": "Report", "deadline": "2026-06-01"}
    ]
    deadlines_fn.assert_called_once()


@patch("main.things.trash")
def test_trash(trash_fn):
    """Trash endpoint returns deleted items."""
    trash_fn.return_value = [
        {"uuid": "t1", "title": "Old task", "type": "to-do"},
    ]
    resp = client.get("/trash", headers=_auth())
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@patch("main.things.canceled")
def test_canceled(canceled_fn):
    """Canceled endpoint returns canceled tasks."""
    canceled_fn.return_value = [
        {"uuid": "c1", "title": "Cancelled item", "type": "to-do"},
    ]
    resp = client.get("/canceled", headers=_auth())
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- Single task endpoint ---


@patch("main.things.get")
def test_get_task_exists(get_fn):
    get_fn.return_value = {"uuid": "abc", "title": "Task 1"}
    resp = client.get("/tasks/abc", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.get")
def test_get_task_not_found(get_fn):
    get_fn.return_value = None
    resp = client.get("/tasks/nonexistent", headers=_auth())
    assert resp.status_code == 404


# --- Write endpoint tests (sanity checks) ---


@patch("main.things.url")
@patch("main._open")
def test_create_task(mock_open, mock_url):
    mock_url.return_value = "things:///add?title=test"
    resp = client.post(
        "/tasks",
        headers=_auth(),
        json={"title": "Test task", "when": "today"},
    )
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted"}


@patch("main.things.complete")
def test_complete_task(mock_complete):
    resp = client.post("/tasks/abc/complete", headers=_auth())
    assert resp.status_code == 202


@patch("main.things.url")
@patch("main._open")
def test_cancel_task(mock_open, mock_url):
    mock_url.return_value = "things:///update?uuid=abc&canceled=true"
    resp = client.post("/tasks/abc/cancel", headers=_auth())
    assert resp.status_code == 202


@patch("main.things.url")
@patch("main._open")
def test_update_task(mock_open, mock_url):
    mock_url.return_value = "things:///update?uuid=abc&title=new"
    resp = client.patch(
        "/tasks/abc",
        headers=_auth(),
        json={"title": "new title"},
    )
    assert resp.status_code == 202


# --- Project write endpoint tests ---


@patch("main.things.complete")
def test_complete_project(mock_complete):
    resp = client.post("/projects/p1/complete", headers=_auth())
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted"}
    mock_complete.assert_called_once_with("p1")


@patch("main.things.url")
@patch("main._open")
def test_cancel_project(mock_open, mock_url):
    mock_url.return_value = "things:///update-project?uuid=p1&canceled=true"
    resp = client.post("/projects/p1/cancel", headers=_auth())
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted"}
    mock_url.assert_called_once_with(uuid="p1", command="update-project", canceled="true")


@patch("main.things.url")
@patch("main._open")
def test_complete_project_requires_auth(mock_open, mock_url):
    resp = client.post("/projects/p1/complete")
    assert resp.status_code == 401


@patch("main.things.url")
@patch("main._open")
def test_cancel_project_requires_auth(mock_open, mock_url):
    resp = client.post("/projects/p1/cancel")
    assert resp.status_code == 401
