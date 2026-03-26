# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`things-http` is a FastAPI HTTP server that exposes Things 3 todo app data over HTTP with Basic Auth. It uses the `things.py` library for reads and the Things URL scheme (`things:///`) via `subprocess.run(['open', url])` for writes.

## Commands

```bash
# Install dependencies
uv sync

# Run the server (THINGS_PASSWORD is required)
THINGS_PASSWORD=secret uv run python main.py

# Optional env vars
THINGS_USERNAME=things   # default: "things"
THINGS_HOST=127.0.0.1    # default: "127.0.0.1"
THINGS_PORT=8000         # default: 8000
```

## Running as a system service (LaunchDaemon)

`com.things.http.plist` is a LaunchDaemon template. It runs as your user so the Things SQLite DB is accessible immediately after boot, before login. Writes auto-launch Things.app once you're logged in; they return 503 pre-login when no GUI session exists.

**Setup:**
1. Edit `com.things.http.plist` — set `THINGS_PASSWORD` to your actual password
2. Install:
```bash
sudo cp com.things.http.plist /Library/LaunchDaemons/
sudo launchctl load /Library/LaunchDaemons/com.things.http.plist
```

```bash
# Check status (look for PID in first column)
sudo launchctl list | grep things.http

# Reload after editing the plist
sudo launchctl unload /Library/LaunchDaemons/com.things.http.plist
sudo launchctl load /Library/LaunchDaemons/com.things.http.plist

# Uninstall
sudo launchctl unload /Library/LaunchDaemons/com.things.http.plist
sudo rm /Library/LaunchDaemons/com.things.http.plist

# Logs
tail -f ~/Library/Logs/things.http.log
```

## Architecture

Everything lives in `main.py` — a single-file FastAPI app:

- **Auth:** HTTP Basic Auth via `fastapi.security.HTTPBasic` + `secrets.compare_digest`. All endpoints share the `verify` dependency.
- **Reads:** Thin wrappers over `things.*` functions (e.g. `things.today()`, `things.get(uuid)`).
- **Writes:** Fire-and-forget via the Things URL scheme. `things.url()` builds the URL; `_open()` calls `subprocess.run(['open', url])`. Returns `202 Accepted`. Things has no delete command — use complete or cancel instead.
- **Auto-docs:** FastAPI serves OpenAPI docs at `/docs` (Basic Auth prompted in browser).

## Write operation notes

Write endpoints return `202 Accepted` immediately — there is no confirmation that Things processed the action. The Things app must be running (or will be launched) to handle URL scheme calls. The `things.token()` call (used internally by `things.url()` for update commands) reads the auth token from the Things database.
