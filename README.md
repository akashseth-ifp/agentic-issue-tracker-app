# Issue Tracker App

A full-stack Issue Tracking System built with **Angular** (frontend) and **FastAPI + SQLAlchemy + SQLite** (backend).

## Overview

Supports creating, viewing, editing, and deleting issues with status lifecycle management (Open → In Progress → Closed). The backend exposes a paginated REST API; the frontend consumes it with a reactive Angular UI using RxJS.

## Architecture

```
agentic-issue-tracker-app/
├── backend/      — FastAPI + SQLAlchemy + SQLite
└── frontend/     — Angular 17+ standalone components
```

The backend follows a 3-layer architecture: **Router → Service → Repository**. The frontend uses a **Smart/Dumb component** split with RxJS pipelines for async data flow.

## Quick Start

Start the backend first, then the frontend.

```bash
# Backend
cd backend
uv venv && source .venv/bin/activate
uv sync
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
| Frontend | Angular 17+, TypeScript, RxJS, SCSS |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | SQLite + aiosqlite |
| Migrations | Alembic |
| Package managers | uv (backend), pnpm (frontend) |

## Documentation

- [Backend README](backend/README.md) — setup, project structure, API reference
- [Frontend README](frontend/README.md) — setup, component architecture, dev commands
