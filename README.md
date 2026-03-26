# things.http

A lightweight HTTP wrapper around [Things 3](https://culturedcode.com/things/) for Mac. Exposes your tasks, projects, and areas as a password-protected JSON API — useful for automations, integrations, or querying your todos from other devices on your network.

## Features

- Read all Things collections: inbox, today, upcoming, anytime, someday, logbook, projects, areas, tags
- Create and update tasks and projects
- Complete or cancel tasks
- HTTP Basic Auth on every endpoint
- Runs as a system service (available after boot, before login)
- Auto-docs at `/docs`

## Requirements

- macOS with [Things 3](https://culturedcode.com/things/) installed
- [uv](https://docs.astral.sh/uv/) for dependency management

## First-time Things setup

Two one-time prompts from macOS/Things are required before everything works:

1. **Full Disk Access for Python** — macOS will prompt when the server first reads the Things database. To avoid this blocking headless runs, grant it permanently: System Settings → Privacy & Security → Full Disk Access → add `.venv/bin/python` from the project directory.

2. **Enable Things URLs** — Things will prompt the first time a write endpoint is called. Accept it, or enable it manually in Things → Settings → General → "Enable Things URLs". Without this, write calls will fail silently.

## Setup

```bash
git clone https://github.com/ehippy/things.http
cd things.http
uv sync
```

## Running

```bash
THINGS_PASSWORD=secret uv run python main.py
```

The server starts on `http://127.0.0.1:8000`. Browse to `/docs` for the interactive API reference.

Optional environment variables:

| Variable | Default | Description |
|---|---|---|
| `THINGS_PASSWORD` | *(required)* | Basic Auth password |
| `THINGS_USERNAME` | `things` | Basic Auth username |
| `THINGS_HOST` | `127.0.0.1` | Bind address |
| `THINGS_PORT` | `8000` | Port |

## API

All endpoints require Basic Auth (`Authorization: Basic ...`).

### Read

| Method | Path | Description |
|---|---|---|
| GET | `/today` | Today's tasks |
| GET | `/inbox` | Inbox |
| GET | `/upcoming` | Upcoming |
| GET | `/anytime` | Anytime |
| GET | `/someday` | Someday |
| GET | `/logbook` | Completed tasks |
| GET | `/projects` | All projects |
| GET | `/areas` | All areas |
| GET | `/tags` | All tags |
| GET | `/tasks/{uuid}` | Single task by UUID |

### Write

Writes go through the Things [URL scheme](https://culturedcode.com/things/support/articles/2803573/) and return `202 Accepted`. Things.app is launched automatically if not already running. Write endpoints return `503` when no GUI session is available (e.g. before login).

| Method | Path | Description |
|---|---|---|
| POST | `/tasks` | Create a task |
| PATCH | `/tasks/{uuid}` | Update a task |
| POST | `/tasks/{uuid}/complete` | Complete a task |
| POST | `/tasks/{uuid}/cancel` | Cancel a task |
| POST | `/projects` | Create a project |
| PATCH | `/projects/{uuid}` | Update a project |

**Task fields:** `title`, `notes`, `when` (today/tomorrow/evening/someday/date), `deadline`, `tags`, `list_id`, `area_id`, `checklist_items`

**Note:** Things has no delete API — use complete or cancel instead.

### Example

```bash
# Get today's tasks
curl -u things:secret http://localhost:8000/today

# Create a task due today
curl -u things:secret -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title": "Buy groceries", "when": "today", "tags": ["errands"]}'

# Complete a task
curl -u things:secret -X POST http://localhost:8000/tasks/SOME-UUID/complete
```

## Running as a system service

`com.things.http.plist.template` is a LaunchDaemon template that starts things.http automatically after every boot — reads work immediately, writes work once you're logged in.

1. Copy the template and fill in your details:
```bash
cp com.things.http.plist.template com.things.http.plist
```
2. Edit `com.things.http.plist` — set `THINGS_PASSWORD`, `UserName`, and the paths to match your username
3. Install:

```bash
sudo cp com.things.http.plist /Library/LaunchDaemons/
sudo launchctl load /Library/LaunchDaemons/com.things.http.plist
```

```bash
# Check it's running (look for a PID in the first column)
sudo launchctl list | grep things.http

# View logs
tail -f ~/Library/Logs/things.http.log
```

## License

MIT
