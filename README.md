# Issue Tracker App

A full-stack Issue Tracking System built with **Angular** (frontend) and **FastAPI + SQLAlchemy + SQLite** (backend), with an **Agentic AI Assistant** powered by OpenAI.

## Overview

Supports creating, viewing, editing, and deleting issues with status lifecycle management (Open → In Progress → Closed). The backend exposes a paginated REST API; the frontend consumes it with a reactive Angular UI using RxJS. A built-in AI Assistant panel lets users query and manage issues using natural language.

## Architecture

```
agentic-issue-tracker-app/
├── backend/      — FastAPI + SQLAlchemy + SQLite + OpenAI agent loop
├── frontend/     — Angular 17+ standalone components
└── adr/          — Architecture Decision Records
```

The backend follows a 3-layer architecture: **Router → Service → Repository**. The AI Assistant adds an **Agent** layer that runs an OpenAI function-calling loop on top of the existing service/repository layer. The frontend uses a **Smart/Dumb component** split with RxJS pipelines for async data flow.

## Quick Start

Start the backend first, then the frontend.

```bash
# Backend
cd backend
uv venv && source .venv/bin/activate
uv sync
cp .env.example .env          # then add your OPENAI_API_KEY to .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
pnpm install
ng serve
```

- Backend API: `http://localhost:8000`
- API docs (Swagger): `http://localhost:8000/docs`
- Frontend: `http://localhost:4200`

## Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 17+, TypeScript, RxJS, Angular Signals, SCSS |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| AI Agent | OpenAI `gpt-4o-mini`, native function calling |
| Database | SQLite + aiosqlite |
| Migrations | Alembic |
| Package managers | uv (backend), pnpm (frontend) |

## AI Assistant

A floating panel (bottom-right of the issue list) accepts natural language instructions and executes them against the issue tracker. Examples:

- `"Show all open issues"` — lists issues with pagination
- `"Create a bug for the login page"` — creates a new issue
- `"Close all in-progress issues"` — bulk status update
- `"How many open issues are older than 7 days?"` — count query

The agent loop runs entirely on the backend (`POST /api/assistant/run`). The model may call multiple tools internally before returning a plain-English response. If any write occurs, the issue list refreshes automatically.

## Documentation

- [Backend README](backend/README.md) — setup, project structure, API reference
- [Frontend README](frontend/README.md) — setup, component architecture, dev commands
- [ADR-003](adr/ADR-003-Agentic%20Assistant.md) — Agentic Assistant architecture decisions
