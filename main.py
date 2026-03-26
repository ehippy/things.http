import os
import secrets
import subprocess
from typing import Optional

import things
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

USERNAME = os.environ.get("THINGS_USERNAME", "things")
PASSWORD = os.environ.get("THINGS_PASSWORD", "")
HOST = os.environ.get("THINGS_HOST", "127.0.0.1")
PORT = int(os.environ.get("THINGS_PORT", "8000"))

if not PASSWORD:
    raise RuntimeError("THINGS_PASSWORD environment variable is required")

app = FastAPI(
    title="things.http",
    description="HTTP wrapper for [Things 3](https://culturedcode.com/things/). Source: [ehippy/things.http](https://github.com/ehippy/things.http)",
    license_info={"name": "MIT", "url": "https://github.com/ehippy/things.http/blob/main/LICENSE"},
)
security = HTTPBasic()


def verify(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), USERNAME.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), PASSWORD.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )


def _open(url: str):
    try:
        subprocess.run(["open", url], check=True)
    except subprocess.CalledProcessError:
        raise HTTPException(
            status_code=503,
            detail="Write unavailable: Things.app requires an active GUI session",
        )


# --- Read endpoints ---

@app.get("/today")
def today(auth=Depends(verify)):
    return things.today()


@app.get("/inbox")
def inbox(auth=Depends(verify)):
    return things.inbox()


@app.get("/upcoming")
def upcoming(auth=Depends(verify)):
    return things.upcoming()


@app.get("/anytime")
def anytime(auth=Depends(verify)):
    return things.anytime()


@app.get("/someday")
def someday(auth=Depends(verify)):
    return things.someday()


@app.get("/logbook")
def logbook(auth=Depends(verify)):
    return things.logbook()


@app.get("/projects")
def projects(auth=Depends(verify)):
    return things.projects()


@app.get("/areas")
def areas(auth=Depends(verify)):
    return things.areas()


@app.get("/tags")
def tags(auth=Depends(verify)):
    return things.tags()


@app.get("/tasks/{uuid}")
def get_task(uuid: str, auth=Depends(verify)):
    item = things.get(uuid)
    if item is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return item


# --- Write models ---

class TaskCreate(BaseModel):
    title: str
    notes: Optional[str] = None
    when: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[list[str]] = None
    list_id: Optional[str] = None
    area_id: Optional[str] = None
    checklist_items: Optional[list[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    when: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[list[str]] = None
    list_id: Optional[str] = None


class ProjectCreate(BaseModel):
    title: str
    notes: Optional[str] = None
    when: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[list[str]] = None
    area_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    when: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[list[str]] = None
    area_id: Optional[str] = None


# --- Write endpoints ---

@app.post("/tasks", status_code=202)
def create_task(body: TaskCreate, auth=Depends(verify)):
    params = {k: v for k, v in body.model_dump().items() if v is not None}
    # Remap list_id → list-id, area_id → area-id
    if "list_id" in params:
        params["list-id"] = params.pop("list_id")
    if "area_id" in params:
        params["area-id"] = params.pop("area_id")
    if "checklist_items" in params:
        params["checklist-items"] = "\n".join(params.pop("checklist_items"))
    if "tags" in params:
        params["tags"] = ",".join(params["tags"])
    _open(things.url(command="add", **params))
    return {"status": "accepted"}


@app.patch("/tasks/{uuid}", status_code=202)
def update_task(uuid: str, body: TaskUpdate, auth=Depends(verify)):
    params = {k: v for k, v in body.model_dump().items() if v is not None}
    if "list_id" in params:
        params["list-id"] = params.pop("list_id")
    if "tags" in params:
        params["tags"] = ",".join(params["tags"])
    _open(things.url(uuid=uuid, command="update", **params))
    return {"status": "accepted"}


@app.post("/tasks/{uuid}/complete", status_code=202)
def complete_task(uuid: str, auth=Depends(verify)):
    things.complete(uuid)
    return {"status": "accepted"}


@app.post("/tasks/{uuid}/cancel", status_code=202)
def cancel_task(uuid: str, auth=Depends(verify)):
    _open(things.url(uuid=uuid, command="update", canceled="true"))
    return {"status": "accepted"}


@app.post("/projects", status_code=202)
def create_project(body: ProjectCreate, auth=Depends(verify)):
    params = {k: v for k, v in body.model_dump().items() if v is not None}
    if "area_id" in params:
        params["area-id"] = params.pop("area_id")
    if "tags" in params:
        params["tags"] = ",".join(params["tags"])
    _open(things.url(command="add-project", **params))
    return {"status": "accepted"}


@app.patch("/projects/{uuid}", status_code=202)
def update_project(uuid: str, body: ProjectUpdate, auth=Depends(verify)):
    params = {k: v for k, v in body.model_dump().items() if v is not None}
    if "area_id" in params:
        params["area-id"] = params.pop("area_id")
    if "tags" in params:
        params["tags"] = ",".join(params["tags"])
    _open(things.url(uuid=uuid, command="update-project", **params))
    return {"status": "accepted"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
