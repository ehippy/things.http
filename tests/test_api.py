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

AUTH="dGhpbmdzOnRlc3Qtc2VjcmV0"  # base64("things:test-secret")


def _auth():
    return {"Authorization": f"Basic {AUTH}"}


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


@patch("main.things.upcoming")
def test_upcoming(upcoming_fn):
    upcoming_fn.return_value = []
    resp = client.get("/upcoming", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.anytime")
def test_anytime(anytime_fn):
    anytime_fn.return_value = []
    resp = client.get("/anytime", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.someday")
def test_someday(someday_fn):
    someday_fn.return_value = []
    resp = client.get("/someday", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.logbook")
def test_logbook(logbook_fn):
    logbook_fn.return_value = []
    resp = client.get("/logbook", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.projects")
def test_projects(projects_fn):
    projects_fn.return_value = []
    resp = client.get("/projects", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.areas")
def test_areas(areas_fn):
    areas_fn.return_value = []
    resp = client.get("/areas", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.tags")
def test_tags(tags_fn):
    tags_fn.return_value = []
    resp = client.get("/tags", headers=_auth())
    assert resp.status_code == 200


@patch("main.things.get")
def test_get_task(get_fn):
    get_fn.return_value = {"uuid": "abc", "title": "Task 1"}
    resp = client.get("/tasks/abc", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == {"uuid": "abc", "title": "Task 1"}


@patch("main.things.get")
def test_get_task_not_found(get_fn):
    get_fn.return_value = None
    resp = client.get("/tasks/nonexistent", headers=_auth())
    assert resp.status_code == 404


# --- Write endpoint tests ---


@patch("main.things.url")
@patch("main._open")
def test_create_task(open_fn, url_fn):
    url_fn.return_value = "things://test"
    open_fn.return_value = None
    resp = client.post(
        "/tasks",
        headers=_auth(),
        json={"title": "New task", "when": "today"},
    )
    assert resp.status_code == 202
    url_fn.assert_called_once()
    # Check that the URL was built with add command
    call_kwargs = url_fn.call_args[1]
    assert call_kwargs.get("command") == "add"


@patch("main.things.url")
@patch("main._open")
def test_update_task(open_fn, url_fn):
    url_fn.return_value = "things://test"
    open_fn.return_value = None
    resp = client.patch(
        "/tasks/abc",
        headers=_auth(),
        json={"title": "Updated title"},
    )
    assert resp.status_code == 202
    url_fn.assert_called_once()
    call_kwargs = url_fn.call_args[1]
    assert call_kwargs.get("command") == "update"
    assert call_kwargs.get("uuid") == "abc"


@patch("main.things.complete")
def test_complete_task(complete_fn):
    resp = client.post(
        "/tasks/abc/complete",
        headers=_auth(),
    )
    assert resp.status_code == 202
    complete_fn.assert_called_once_with("abc")


@patch("main.things.url")
@patch("main._open")
def test_cancel_task(open_fn, url_fn):
    url_fn.return_value = "things://test"
    open_fn.return_value = None
    resp = client.post(
        "/tasks/abc/cancel",
        headers=_auth(),
    )
    assert resp.status_code == 202
    url_fn.assert_called_once()
    call_kwargs = url_fn.call_args[1]
    assert call_kwargs.get("command") == "update"
    assert call_kwargs.get("uuid") == "abc"
    assert call_kwargs.get("canceled") == "true"


# --- Move endpoint tests ---


@patch("main.things.url")
@patch("main._open")
def test_move_task_to_today(open_fn, url_fn):
    """Move a task to the 'today' collection."""
    url_fn.return_value = "things://test"
    open_fn.return_value = None
    resp = client.post(
        "/tasks/abc/move",
        headers=_auth(),
        json={"collection": "today"},
    )
    assert resp.status_code == 202
    url_fn.assert_called_once()
    call_kwargs = url_fn.call_args[1]
    assert call_kwargs.get("command") == "move-to-collection"
    assert call_kwargs.get("uuid") == "abc"
    assert call_kwargs.get("collection") == "today"


@patch("main.things.url")
@patch("main._open")
def test_move_task_to_inbox(open_fn, url_fn):
    """Move a task to the inbox."""
    url_fn.return_value = "things://test"
    open_fn.return_value = None
    resp = client.post(
        "/tasks/abc/move",
        headers=_auth(),
        json={"collection": "inbox"},
    )
    assert resp.status_code == 202
    call_kwargs = url_fn.call_args[1]
    assert call_kwargs.get("command") == "move-to-collection"
    assert call_kwargs.get("collection") == "inbox"


@patch("main.things.url")
@patch("main._open")
def test_move_task_to_project(open_fn, url_fn):
    """Move a task to a specific project."""
    url_fn.return_value = "things://test"
    open_fn.return_value = None
    resp = client.post(
        "/tasks/abc/move",
        headers=_auth(),
        json={"collection": "project-uuid-123"},
    )
    assert resp.status_code == 202
    call_kwargs = url_fn.call_args[1]
    assert call_kwargs.get("command") == "move-to-collection"
    assert call_kwargs.get("collection") == "project-uuid-123"


@patch("main._open")
def test_move_task_unauthorized(open_fn):
    """Move endpoint should require auth."""
    resp = client.post(
        "/tasks/abc/move",
        json={"collection": "today"},
    )
    assert resp.status_code == 401
