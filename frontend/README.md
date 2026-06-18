# Frontend — Angular Issue Tracker

Angular 17+ standalone component frontend for the Issue Tracking System.

## Setup

```bash
cd frontend
pnpm install
ng serve
```

Open `http://localhost:4200`. Requires the backend running on `http://localhost:8000`.

## Build

```bash
ng build                          # development
ng build --configuration production  # production
```

Output goes to `dist/frontend/`.

## Project Structure

```
src/app/
├── core/
│   ├── models/
│   │   └── issue.model.ts        — TypeScript interfaces + IssueStatus enum
│   ├── services/
│   │   └── issue.service.ts      — HttpClient wrapper; all methods return Observable
│   └── interceptors/
│       └── error.interceptor.ts  — Global HTTP error handler (HttpInterceptorFn)
├── features/
│   ├── issues/
│   │   ├── containers/           — Smart components (inject services, own state)
│   │   │   ├── issue-list/       — Lists issues with pagination, handles edit/delete
│   │   │   └── issue-form/       — Reactive form for create and edit
│   │   └── components/           — Dumb components (@Input/@Output only)
│   │       ├── issue-card/       — Displays one issue card
│   │       ├── status-badge/     — Colored pill badge for issue status
│   │       ├── confirm-dialog/   — Reusable delete confirmation modal
│   │       └── pagination/       — Page controls with prev/next/page buttons
│   └── assistant/
│       ├── assistant.service.ts  — Calls POST /api/assistant/run; returns Observable<AssistantResponse>
│       └── components/
│           └── assistant-panel/  — Smart component: floating FAB + modal, owns loading/response/error state
└── shared/components/
    ├── loading-spinner/          — Reusable CSS spinner
    └── error-message/            — Displays error string via @Input
```

## Key Patterns

**Smart/Dumb components** — Containers inject services and manage state. Presentational components only receive `@Input()` and emit `@Output()`.

**RxJS pipeline** — `IssueListComponent` uses `BehaviorSubject` + `distinctUntilChanged` + `switchMap` to drive pagination. `distinctUntilChanged` prevents duplicate fetches; `switchMap` cancels in-flight requests when the page changes.

**Angular Signals** — `AssistantPanelComponent` manages all local UI state (`isExpanded`, `isLoading`, `response`, `error`, `instruction`, `pendingCursor`) with Signals instead of plain class fields, enabling fine-grained reactivity without a full RxJS pipeline.

**AI Assistant panel** — A fixed floating action button (bottom-right) opens a modal overlay. The panel emits `@Output() issuesChanged` when the backend reports `mutations_made: true`; `IssueListComponent` calls `refresh$.next()` on that event to re-fetch the issue list without a full page reload.

**Cursor-based pagination in the assistant** — When the AI returns `next_cursor`, the panel stores it in `pendingCursor` signal and displays a "More results available" hint. The cursor is sent back on the next submission so the backend can continue from the same position.

**HTTP Interceptor** — All HTTP errors (404, 422, 500, network down) are caught globally in `error.interceptor.ts` and converted to readable messages.

**Lazy routing** — All routes use `loadComponent` so each page's JS bundle is only downloaded when navigated to.

## Routes

| Path | Component | Description |
|---|---|---|
| `/` | — | Redirects to `/issues` |
| `/issues` | `IssueListComponent` | Paginated issue list |
| `/issues/new` | `IssueFormComponent` | Create a new issue |
| `/issues/edit/:id` | `IssueFormComponent` | Edit an existing issue |

## Environment Config

`src/environments/environment.ts` — points `apiUrl` to `http://localhost:8000/api` in development.
`src/environments/environment.prod.ts` — use a relative `/api` path for same-origin production deploys.
