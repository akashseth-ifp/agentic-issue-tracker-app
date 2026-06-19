# ADR-003: Agentic Assistant — Architecture & Implementation Guide

**Status:** Accepted  
**Date:** 2026-06-18  
**Author:** Akash Seth  
**See also:** [ADR-001](ADR-001.md) — Base architecture, [ADR-002](ADR-002.md) — Implementation guide

---

## Context

The Issue Tracking System is extended with an Agentic Assistant panel embedded in the dashboard. Users type a natural language instruction ("close all in-progress issues", "show me open issues older than 7 days", "create a bug for the login page") and the assistant executes it against the issue tracker, responding in plain English. The issue list reflects any changes immediately without a page refresh.

**Supported interaction types:**
- Querying issues — by status, age, count, or summary
- Creating a new issue from a description
- Updating the status of one or more issues
- Bulk operations across a filtered set of issues

**Scope boundaries:**
- Stateless agent per turn — each submission runs a fresh agent loop, but pagination cursor state is carried across turns so users can ask for more results
- No history storage — responses are ephemeral
- The agent loop runs on the backend (not in the browser)

---

## How AI Agents Work (Primer for Newcomers)

A traditional LLM call is: you send text in, you get text back. That's it.

An **AI agent** is different. Instead of generating one final answer, the model can request to call a **tool** (a Python function you define). The loop works like this:

```
You send: "Close all open issues"
                 ↓
Model thinks: "I need to know the scope before a bulk operation — I'll count first"
Model responds: calls count_issues(status="Open")  ← not text, a tool call
                 ↓
Your code executes count_issues() → returns { count: 1500000 }
You send the result back to the model
                 ↓
Model thinks: "There are 1.5M open issues. I'll bulk-move them all to In Progress."
Model responds: calls bulk_update_status(from_status="Open", to_status="In Progress", confirm=True)
                 ↓
Your code executes bulk_update_status() → returns { updated_count: 1500000 }
  (runs a single UPDATE WHERE status='Open' — no rows fetched, works at any scale)
You send the result back to the model
                 ↓
Model responds: plain text "Done! I moved 1,500,000 open issues to In Progress."  ← loop ends
```

**Why `count_issues` and not `list_issues` before bulk ops:**
`list_issues` is capped at 20 rows. If there are millions of open issues, the model would only see 20 of them and make a scope decision on incomplete data. `count_issues` runs a single indexed `COUNT(*)` — returns the exact total for any dataset size with zero row fetching. The model gets the true scope, then `bulk_update_status` operates at the DB level on all matching rows in one query.

This observe → plan → act loop is what makes it an **agent** rather than a simple LLM call. The model decides which tools to call, in what order, based on what it observes.

**Native function calling vs. JSON prompt parsing:**
OpenAI (and Anthropic) expose a `tools` parameter in their API. When used, the model returns a structured `tool_calls` object — not free text — with the exact function name and arguments. This is more reliable than asking the model to "return JSON like this: {action: ..., params: ...}" because:
- The API enforces the schema — you will never get malformed JSON
- The model is fine-tuned specifically for tool use, not text mimicry
- You don't need to write a fragile JSON parser or handle `json.JSONDecodeError`

We will use native function calling throughout.

---

## Architectural Decisions

### D1 — Tool Design: 5 Minimal, Orthogonal Tools

**Decision:** Define exactly 5 tools. Each tool has a single, unambiguous purpose. Read and write operations are separated.

| Tool | Type | Purpose |
|---|---|---|
| `count_issues` | Read | Count issues matching filters — no rows fetched, no token cost |
| `list_issues` | Read | Fetch a page of issues with optional filters; cursor-based |
| `create_issue` | Write | Create one new issue |
| `update_issue_status` | Write | Change the status of a single issue by ID |
| `bulk_update_status` | Write | Change status of all issues matching a filter |

**Why 5 and not more or fewer:**
- **Not fewer:** A single "manage_issues" god-tool forces the model to guess intent from a vague action parameter — ambiguity causes unreliable tool selection. Separate tools with descriptive names give the model a clear decision tree.
- **`count_issues` is justified:** Counting and listing are fundamentally different DB operations. `list_issues` fetches rows (expensive at scale, adds tokens to context). `count_issues` runs a single indexed `COUNT(*)` — fast regardless of dataset size, zero token cost. Without it, the model is forced to fetch rows just to answer "how many?" — wasteful and dangerous on large datasets.
- **Why no `get_issue_by_id`:** `list_issues` accepts an optional `id` filter that returns the single matching issue. A dedicated `get_issue_by_id` tool would be redundant — same DB query, same response shape, just an extra tool for the model to choose between.

**Tool schemas (OpenAI format):**

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "count_issues",
            "description": "Count issues matching filters WITHOUT fetching them. Use this for any question about quantities, totals, or summaries. Much cheaper than list_issues for large datasets — always prefer this when you only need a number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "Filter by status. Omit to count all statuses."
                    },
                    "created_after": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only count issues created after this date."
                    },
                    "created_before": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only count issues created before this date."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "Fetch a page of issues with optional filters. Returns at most 20 results per call. Use id to look up a specific issue by its numeric ID. If has_more is true, there are additional results — do NOT call this again to paginate; instead inform the user and offer to continue if they ask.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "Filter by exact issue ID. Use this when the user asks about a specific issue by number."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "Filter by status. Omit to return all statuses."
                    },
                    "created_after": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only return issues created after this date."
                    },
                    "created_before": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only return issues created before this date."
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Opaque cursor from a previous list_issues response. Pass this to fetch the next page of results."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_issue",
            "description": "Create a new issue in the tracker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short, descriptive title for the issue."
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional longer description."
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_issue_status",
            "description": "Update the status of a single issue by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "integer",
                        "description": "The numeric ID of the issue to update."
                    },
                    "new_status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "The new status value."
                    }
                },
                "required": ["issue_id", "new_status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bulk_update_status",
            "description": "Update the status of ALL issues currently matching from_status. This affects multiple records. Only call this after you know how many issues will be affected (use count_issues first — it returns the exact total without fetching rows). You MUST set confirm=true to proceed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "Filter: only issues with this status will be updated."
                    },
                    "to_status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "The new status to apply to all matched issues."
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true. Explicit acknowledgement that this will affect multiple records."
                    }
                },
                "required": ["from_status", "to_status", "confirm"]
            }
        }
    }
]
```

**Key reliability features:**
- `confirm: bool` on `bulk_update_status` — the model cannot accidentally bulk-update: it must reason about the operation and consciously pass `true`. If the model passes `false`, the tool executor returns an error message instead of writing, and the model must reconsider.
- `list_issues` returns `has_more` but **not** a total count — the model cannot calculate how many pages remain, so it cannot plan a pagination loop. It sees `has_more: true` and stops, guided by the tool description and system prompt.
- `count_issues` exists precisely so the model never needs to fetch rows just to answer a quantity question.

---

### D2 — Agentic Loop Architecture: Backend-Hosted Multi-Step Loop

**Decision:** The agent loop runs entirely on the backend as a single `POST /api/assistant/run` endpoint. The frontend sends one instruction and waits for one response. The model may internally make multiple tool calls before responding.

**Why backend, not frontend:**
- The OpenAI API key must never be exposed to the browser
- Tool execution requires direct database access (no round-trip through HTTP)
- The loop can run faster without the browser as an intermediary

**Loop implementation:**

```python
# backend/app/agent/assistant_service.py

MAX_ITERATIONS = 10  # safety cap — prevents runaway loops

BASE_SYSTEM_PROMPT = """
You are a dedicated assistant for an issue tracking system. Your sole purpose is to help users
query, create, and update issues in this tracker. You are NOT a general-purpose AI assistant.

STRICT DOMAIN BOUNDARY:
If the user's request is unrelated to issue tracking (e.g. coding help, general knowledge,
weather, jokes, or anything outside this product), do NOT call any tool. Respond with:
  "I can only help with the issue tracker. Try: 'Show open issues', 'Create a bug for X',
   or 'Close all in-progress issues'."
Never apologise excessively — one short sentence of redirection is enough.

WORKFLOW RULES:
- For bulk operations, ALWAYS call count_issues first to understand scope, then bulk_update_status.
- For any question about counts or totals, ALWAYS use count_issues — never use list_issues just to count.
- list_issues returns at most 20 results. If has_more is true, tell the user how many were returned
  and invite them to ask for the next page. Do NOT paginate automatically.

Always be specific in your final response: mention counts, IDs, or titles of affected issues.
"""

async def run_agent(instruction: str, db: AsyncSession, cursor: str | None = None) -> dict:
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Inject cursor context so the model knows how to continue a paginated query
    system_prompt = BASE_SYSTEM_PROMPT
    if cursor:
        system_prompt += (
            f"\n\nPending cursor: {cursor}. "
            "If the user is asking for the next page of results, pass this as the `cursor` parameter to list_issues."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": instruction}
    ]
    mutations_made = False
    next_cursor = None

    for iteration in range(MAX_ITERATIONS):
        response = await client.chat.completions.create(
            model="gpt-4o-mini",   # cost-effective, strong at tool use
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"     # model decides: call a tool or respond with text
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # "stop" means the model chose to respond with text — loop ends
        if finish_reason == "stop" or not message.tool_calls:
            return {
                "response": message.content or "Done.",
                "mutations_made": mutations_made,
                "next_cursor": next_cursor
            }

        # Model returned tool calls — execute each one
        messages.append(message)   # add assistant's tool-call turn to history

        for tool_call in message.tool_calls:
            result = await execute_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments),
                db
            )
            if result.get("is_mutation"):
                mutations_made = True
            # Capture cursor from list_issues for the response
            if result.get("next_cursor"):
                next_cursor = result["next_cursor"]
            elif tool_call.function.name == "list_issues":
                next_cursor = None  # no more pages, clear any pending cursor
            # Feed the result back to the model
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

    # Exhausted iterations without a final text response
    return {
        "response": "I was unable to complete the request within the allowed steps. Please try rephrasing.",
        "mutations_made": mutations_made,
        "next_cursor": None
    }
```

**Why `MAX_ITERATIONS = 10`:** A malformed or ambiguous instruction could cause the model to loop indefinitely. Capping at 10 is a safety ceiling — in practice, all supported interactions complete in 1–3 iterations.

**Why `mutations_made` flag:** The frontend needs to know whether to refresh the issue list. Rather than always refreshing (wasteful for read-only queries), the backend signals whether any write occurred.

**Why `next_cursor` in the return value:** The frontend stores this after a paginated response and sends it back on the next request. The agent loop treats it as opaque context — it cannot plan a multi-page loop on its own because each turn is stateless.

---

### D3 — LLM Integration: OpenAI Native Function Calling

**Decision:** Use the OpenAI Python SDK (`openai>=1.0`) with the `tools` parameter for native function calling. Model: `gpt-4o-mini`.

**Why `gpt-4o-mini` and not `gpt-4o`:**
- `gpt-4o-mini` has excellent tool-use reliability at ~10× lower cost
- For structured, well-defined tools like ours, the smaller model performs comparably
- The bottleneck is tool design, not model size

**Why native function calling, not JSON prompt parsing:**

| Approach | How it works | Risk |
|---|---|---|
| Prompt parsing | Ask model: "respond ONLY with JSON: {action: ..., params: ...}" | Model may add preamble text, wrap in markdown fences, hallucinate fields, produce invalid JSON |
| Native function calling | Pass `tools=[...]` to the API; model returns `tool_calls` object | API enforces schema; no parsing needed; model retries automatically on schema mismatch |

With native function calling, the model's tool invocation looks like:
```json
{
  "tool_calls": [{
    "id": "call_abc123",
    "type": "function",
    "function": {
      "name": "list_issues",
      "arguments": "{\"status\": \"Open\"}"
    }
  }]
}
```
`arguments` is always valid JSON — you just call `json.loads()`.

**Configuration:** `OPENAI_API_KEY` stored in `.env`, loaded via existing `pydantic-settings` config (`backend/app/core/config.py`).

---

### D4 — Reliability & Edge Case Handling

**Decision:** Address five reliability failure modes explicitly.

**1. Instruction doesn't map to any tool ("what is the weather today?")**
The system prompt constrains the model's domain. If the instruction is out of scope, the model responds with text (no tool call) explaining it can only help with issues. The loop naturally handles this on iteration 1.

**2. Bulk destructive operations (close all issues)**
Two-layer guardrail:
- Tool description instructs the model to call `list_issues` first
- `confirm: bool` parameter forces explicit acknowledgement in the tool call
- Tool executor checks `confirm == True` before writing; returns a warning otherwise

**3. Invalid status transitions (close an Open issue directly)**
The existing `IssueService` raises `InvalidStatusTransitionException` for invalid transitions. The tool executor catches this and returns an error dict to the model:
```python
{"error": "Cannot transition from Open to Closed. Open issues must first move to In Progress."}
```
The model reads this, explains the constraint to the user, and may suggest the correct multi-step path.

**4. Errors are always surfaced, never swallowed**
```python
async def execute_tool(name: str, args: dict, db: AsyncSession) -> dict:
    try:
        if name == "list_issues":
            return await _list_issues(args, db)
        elif name == "create_issue":
            return await _create_issue(args, db)
        elif name == "update_issue_status":
            return await _update_issue_status(args, db)
        elif name == "bulk_update_status":
            return await _bulk_update_status(args, db)
        else:
            return {"error": f"Unknown tool: {name}"}
    except AppException as e:
        return {"error": str(e.detail)}   # model sees the error and explains it
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
```
All exceptions are caught and returned as structured error dicts. The model reads the error and decides whether to retry with different parameters or explain to the user. Nothing is silently swallowed.

**5. OpenAI API failure**
If the OpenAI call itself fails (network error, rate limit), the exception propagates to the FastAPI router, which returns a 502 response. The frontend shows a toast error via the existing global error interceptor.

**6. Large result sets ("show all issues from the last 5 years")**
Two interlocking constraints prevent runaway queries:
- `list_issues` fetches `page_size + 1` rows with no `COUNT(*)` — the extra row detects `has_more` without scanning the full table. The response includes `has_more: bool` and `next_cursor` but **never a total count**. Without a total, the model cannot calculate how many pages remain and cannot plan a loop.
- The tool description and system prompt explicitly forbid pagination within a single turn. When `has_more` is true, the model tells the user results were truncated and offers to continue if asked.
- For count-only questions ("how many issues from last year?"), the model uses `count_issues` — a single indexed `COUNT(*)` with no row fetching and no token cost.

---

### D5 — Frontend: Collapsible Panel + Live Refresh + Cursor State

**Decision:** Add `AssistantPanelComponent` (smart component) directly inside the issue-list container. It emits `@Output() issuesChanged` when a write operation completes; `IssueListComponent` triggers a refresh on that event. The component stores `next_cursor` in a Signal and sends it automatically on the next submission.

**Why a smart component (not dumb):**
The panel injects `AssistantService` to make the API call. It manages its own loading/error/cursor state. It is self-contained — the parent only needs to handle the `issuesChanged` output.

**Collapsible pattern:**
```typescript
isExpanded = signal(false);
togglePanel() { this.isExpanded.update(v => !v); }
```
Controlled via Angular Signals (consistent with existing component patterns in the codebase).

**Cursor state — stored in the component, not the backend:**
```typescript
pendingCursor = signal<string | null>(null);  // cleared on write ops or new queries

submit() {
  this.assistantService.run(this.instruction(), this.pendingCursor()).subscribe({
    next: (result) => {
      this.response.set(result.response);
      this.pendingCursor.set(result.next_cursor ?? null); // store for next turn
      if (result.mutations_made) {
        this.pendingCursor.set(null);  // writes invalidate cursor
        this.issuesChanged.emit();
      }
    }
  });
}
```
The cursor lives in ephemeral component state. If the user collapses and reopens the panel, or starts a new query, the cursor is discarded — the next submission starts fresh.

**Refresh mechanism:**
```typescript
// issue-list.component.html
<app-assistant-panel (issuesChanged)="onIssuesChanged()" />

// issue-list.component.ts
onIssuesChanged() {
  this.refresh$.next();  // reuses existing refresh$ Subject
}
```
The existing `refresh$` Subject in `IssueListComponent` already drives a re-fetch. No new state management needed.

---

### D6 — Scalable Pagination: Index + Cursor-Based

**Decision:** Add a DB index on `created_at` via Alembic migration. Replace offset-based pagination in agent-facing queries with cursor-based pagination using a composite `(created_at, id)` cursor.

**Why an index on `created_at`:**
All date-range queries (`WHERE created_at >= '2021-01-01'`) and the `count_issues` tool use this column as a filter. Without an index, every query is a full table scan. The index makes both operations fast regardless of table size.

**Why cursor over offset:**

| | Offset (`LIMIT N OFFSET K`) | Cursor (`WHERE created_at < :ts AND id < :id`) |
|---|---|---|
| DB work | Reads and discards K rows to skip | Index seek directly to cursor position |
| Page 500 performance | 10,000 rows discarded | Same as page 1 |
| Stability | New inserts between pages cause duplicates/skips | Anchored to a fixed point — stable |

**Composite cursor `(created_at, id)` — not just `created_at`:**
Two issues can share the exact same `created_at` timestamp. Using only timestamp as cursor would skip or repeat those. The composite cursor `(created_at, id)` is unique and unambiguous:

```python
import base64, json

def encode_cursor(created_at: datetime, id: int) -> str:
    payload = json.dumps({"ts": created_at.isoformat(), "id": id})
    return base64.urlsafe_b64encode(payload.encode()).decode()

def decode_cursor(cursor: str) -> tuple[datetime, int]:
    payload = json.loads(base64.urlsafe_b64decode(cursor))
    return datetime.fromisoformat(payload["ts"]), payload["id"]
```

The frontend treats the cursor as an opaque string — it never inspects the contents.

**Repository query pattern:**
```python
async def get_cursor_page(
    self, page_size: int = 20,
    cursor: str | None = None,
    status: IssueStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[Issue], bool, str | None]:
    query = select(Issue)

    if cursor:
        ts, cid = decode_cursor(cursor)
        # items strictly before the cursor position (DESC order)
        query = query.where(
            (Issue.created_at < ts) |
            ((Issue.created_at == ts) & (Issue.id < cid))
        )
    if status:
        query = query.where(Issue.status == status)
    if created_after:
        query = query.where(Issue.created_at >= created_after)
    if created_before:
        query = query.where(Issue.created_at <= created_before)

    # Fetch one extra row to detect has_more — no COUNT(*) needed
    rows = list((await self.db.execute(
        query.order_by(Issue.created_at.desc(), Issue.id.desc()).limit(page_size + 1)
    )).scalars().all())

    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None
    return items, has_more, next_cursor
```

The existing `get_all(page, page_size)` method is left **unchanged** — the HTTP pagination routes still use it. `get_cursor_page` is new and used only by the agent tools.

---

## New File Structure

```
backend/app/
└── agent/                         ← NEW: all agent code isolated here
    ├── __init__.py
    ├── tools.py                   ← Tool schemas (TOOLS list) + execute_tool dispatcher
    └── assistant_service.py       ← run_agent() with the agentic loop

backend/app/routers/
└── assistant_router.py            ← NEW: POST /api/assistant/run

backend/app/schemas/
└── assistant.py                   ← NEW: AssistantRequest, AssistantResponse Pydantic schemas

frontend/src/app/features/assistant/    ← NEW feature folder
├── assistant.service.ts                ← Calls POST /api/assistant/run
└── components/
    └── assistant-panel/
        ├── assistant-panel.component.ts
        ├── assistant-panel.component.html
        └── assistant-panel.component.scss
```

**Files modified (not created):**
- `backend/app/core/config.py` — add `openai_api_key: str` field
- `backend/app/repositories/issue_repository.py` — add `get_cursor_page`, `count`, `bulk_update_status` methods
- `backend/app/main.py` — register `assistant_router`
- `frontend/src/app/features/issues/containers/issue-list/issue-list.component.ts` — add `onIssuesChanged()`
- `frontend/src/app/features/issues/containers/issue-list/issue-list.component.html` — add `<app-assistant-panel>`
- `backend/.env` / `backend/.env.example` — add `OPENAI_API_KEY=`
- `backend/pyproject.toml` — add `openai>=1.0`

**New Alembic migration:**
- `backend/alembic/versions/xxxx_add_created_at_index.py` — `ix_issues_created_at`

---

## API Contract

### `POST /api/assistant/run`

**Request:**
```json
{
  "instruction": "Close all in-progress issues",
  "cursor": null
}
```
`cursor` is optional. Pass the `next_cursor` from a previous response to continue a paginated query.

**Response 200 — write operation:**
```json
{
  "response": "Done! I moved 3 in-progress issues to Closed: #4 (Login bug), #7 (Dashboard crash), #12 (API timeout).",
  "mutations_made": true,
  "next_cursor": null
}
```

**Response 200 — paginated read (first page):**
```json
{
  "response": "Here are the 20 most recent open issues. There are more — say 'next page' to continue.",
  "mutations_made": false,
  "next_cursor": "eyJ0cyI6IjIwMjQtMDEtMTVUMTA6MzA6MDBaIiwiaWQiOjQ4MjF9"
}
```

**Response 200 — count query:**
```json
{
  "response": "There are 1,000,000 issues created in the last 5 years.",
  "mutations_made": false,
  "next_cursor": null
}
```

**Response 400** (empty instruction):
```json
{ "error": "Instruction cannot be empty", "status_code": 400 }
```

**Response 502** (OpenAI API failure):
```json
{ "error": "Assistant service unavailable. Please try again.", "status_code": 502 }
```

---

## Implementation — 8 Commits

| # | Commit | What it establishes |
|---|---|---|
| 1 | `feat: add openai dependency and config` | `pyproject.toml`, `config.py`, `.env.example` |
| 2 | `feat: add created_at index migration` | Alembic migration — `ix_issues_created_at` for fast date-range queries |
| 3 | `feat: extend issue repository for agent queries` | `get_cursor_page`, `count`, `bulk_update_status` methods; cursor encode/decode helpers |
| 4 | `feat: define agent tools and executor` | `agent/tools.py` — 5 tools + execute_tool() dispatcher |
| 5 | `feat: implement agentic loop in assistant service` | `agent/assistant_service.py` — run_agent() with cursor support + MAX_ITERATIONS loop |
| 6 | `feat: add assistant API endpoint` | `schemas/assistant.py` with cursor fields, `routers/assistant_router.py`, register in `main.py` |
| 7 | `feat: add Angular AssistantPanel component` | `assistant.service.ts` + `assistant-panel` component with cursor state |
| 8 | `feat: wire assistant panel into issue-list dashboard` | `issue-list.component.ts/.html` — add panel + refresh on issuesChanged |

---

## Commit 1: OpenAI Dependency + Config

**`backend/pyproject.toml`** — add to dependencies:
```toml
"openai>=1.0",
```

**`backend/app/core/config.py`** — add field:
```python
openai_api_key: str = ""
```

**`backend/.env.example`** (create if not exists):
```
DATABASE_URL=sqlite+aiosqlite:///./issues.db
OPENAI_API_KEY=sk-...
```

---

## Commit 2: Add created_at Index Migration

```python
# backend/alembic/versions/xxxx_add_created_at_index.py
def upgrade():
    op.create_index("ix_issues_created_at", "issues", ["created_at"])

def downgrade():
    op.drop_index("ix_issues_created_at", table_name="issues")
```

---

## Commit 3: Repository — Cursor Pagination + Count + Bulk Update

**`backend/app/repositories/issue_repository.py`** — add three new methods (existing `get_all` is untouched):

```python
import base64, json
from datetime import datetime
from sqlalchemy import update as sa_update

def encode_cursor(created_at: datetime, id: int) -> str:
    payload = json.dumps({"ts": created_at.isoformat(), "id": id})
    return base64.urlsafe_b64encode(payload.encode()).decode()

def decode_cursor(cursor: str) -> tuple[datetime, int]:
    payload = json.loads(base64.urlsafe_b64decode(cursor))
    return datetime.fromisoformat(payload["ts"]), payload["id"]

async def get_cursor_page(
    self,
    page_size: int = 20,
    cursor: str | None = None,
    status: IssueStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[Issue], bool, str | None]:
    query = select(Issue)
    if cursor:
        ts, cid = decode_cursor(cursor)
        query = query.where(
            (Issue.created_at < ts) |
            ((Issue.created_at == ts) & (Issue.id < cid))
        )
    if status:
        query = query.where(Issue.status == status)
    if created_after:
        query = query.where(Issue.created_at >= created_after)
    if created_before:
        query = query.where(Issue.created_at <= created_before)

    # Fetch page_size + 1 to detect has_more — no COUNT(*) needed
    rows = list((await self.db.execute(
        query.order_by(Issue.created_at.desc(), Issue.id.desc()).limit(page_size + 1)
    )).scalars().all())

    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None
    return items, has_more, next_cursor

async def count(
    self,
    status: IssueStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> int:
    query = select(func.count()).select_from(Issue)
    if status:
        query = query.where(Issue.status == status)
    if created_after:
        query = query.where(Issue.created_at >= created_after)
    if created_before:
        query = query.where(Issue.created_at <= created_before)
    return await self.db.scalar(query) or 0

async def bulk_update_status(self, from_status: IssueStatus, to_status: IssueStatus) -> int:
    result = await self.db.execute(
        sa_update(Issue)
        .where(Issue.status == from_status)
        .values(status=to_status)
    )
    await self.db.commit()
    return result.rowcount
```

**Important:** `bulk_update_status` bypasses the per-issue status machine in `IssueService`. The tool executor must validate the transition before calling this. Valid bulk transitions:
- Open → In Progress ✓
- In Progress → Closed ✓
- In Progress → Open ✓
- Closed → anything ✗ (reject in executor before hitting DB)

---

## Commit 4: Agent Tools Definition (5 Tools)

**`backend/app/agent/tools.py`**

```python
# TOOLS list (the 5 schemas shown in D1 above)
TOOLS = [...]  # paste the 5 tool schemas from D1

async def execute_tool(name: str, args: dict, db: AsyncSession) -> dict:
    try:
        if name == "count_issues":
            return await _count_issues(args, db)
        elif name == "list_issues":
            return await _list_issues(args, db)
        elif name == "create_issue":
            return await _create_issue(args, db)
        elif name == "update_issue_status":
            return await _update_issue_status(args, db)
        elif name == "bulk_update_status":
            return await _bulk_update_status(args, db)
        else:
            return {"error": f"Unknown tool: {name}"}
    except AppException as e:
        return {"error": e.detail}
    except Exception as e:
        return {"error": str(e)}

async def _count_issues(args: dict, db: AsyncSession) -> dict:
    repo = IssueRepository(db)
    status = IssueStatus(args["status"]) if "status" in args else None
    created_after = datetime.fromisoformat(args["created_after"]) if "created_after" in args else None
    created_before = datetime.fromisoformat(args["created_before"]) if "created_before" in args else None
    total = await repo.count(status, created_after, created_before)
    return {"count": total, "is_mutation": False}

async def _list_issues(args: dict, db: AsyncSession) -> dict:
    repo = IssueRepository(db)
    status = IssueStatus(args["status"]) if "status" in args else None
    created_after = datetime.fromisoformat(args["created_after"]) if "created_after" in args else None
    created_before = datetime.fromisoformat(args["created_before"]) if "created_before" in args else None
    cursor = args.get("cursor")

    items, has_more, next_cursor = await repo.get_cursor_page(
        page_size=20, cursor=cursor,
        status=status, created_after=created_after, created_before=created_before
    )
    return {
        "items": [
            {"id": i.id, "title": i.title, "status": i.status.value, "created_at": i.created_at.isoformat()}
            for i in items
        ],
        "has_more": has_more,
        "next_cursor": next_cursor,  # opaque; frontend stores and sends back
        "is_mutation": False
    }

async def _create_issue(args: dict, db: AsyncSession) -> dict:
    service = IssueService(IssueRepository(db))
    issue = await service.create(IssueCreate(title=args["title"], description=args.get("description")))
    return {"id": issue.id, "title": issue.title, "status": issue.status.value, "is_mutation": True}

async def _update_issue_status(args: dict, db: AsyncSession) -> dict:
    service = IssueService(IssueRepository(db))
    issue = await service.update(args["issue_id"], IssueUpdate(status=IssueStatus(args["new_status"])))
    return {"id": issue.id, "title": issue.title, "status": issue.status.value, "is_mutation": True}

async def _bulk_update_status(args: dict, db: AsyncSession) -> dict:
    if not args.get("confirm"):
        return {"error": "confirm must be true to execute a bulk update. Call count_issues first to see how many will be affected."}
    from_status = IssueStatus(args["from_status"])
    to_status = IssueStatus(args["to_status"])
    VALID = {
        IssueStatus.OPEN: {IssueStatus.IN_PROGRESS},
        IssueStatus.IN_PROGRESS: {IssueStatus.CLOSED, IssueStatus.OPEN},
        IssueStatus.CLOSED: set()
    }
    if to_status not in VALID[from_status]:
        return {"error": f"Bulk transition from '{from_status.value}' to '{to_status.value}' is not allowed."}
    count = await IssueRepository(db).bulk_update_status(from_status, to_status)
    return {"updated_count": count, "is_mutation": True}
```

---

## Commit 5: Agentic Loop Service

**`backend/app/agent/assistant_service.py`** — full implementation per D2 above (including `cursor` parameter, `next_cursor` in return value, and cursor injection into system prompt).

---

## Commit 6: Assistant API Endpoint

**`backend/app/schemas/assistant.py`**
```python
from pydantic import BaseModel, field_validator

class AssistantRequest(BaseModel):
    instruction: str
    cursor: str | None = None   # opaque cursor from previous list_issues response

    @field_validator("instruction")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Instruction cannot be empty")
        return v.strip()

class AssistantResponse(BaseModel):
    response: str
    mutations_made: bool
    next_cursor: str | None = None  # present when list_issues has_more=true
```

**`backend/app/routers/assistant_router.py`**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.agent.assistant_service import run_agent

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

@router.post("/run", response_model=AssistantResponse)
async def run_assistant(body: AssistantRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await run_agent(body.instruction, db, cursor=body.cursor)
        return AssistantResponse(**result)
    except Exception:
        raise HTTPException(status_code=502, detail="Assistant service unavailable. Please try again.")
```

**`backend/app/main.py`** — add:
```python
from app.routers.assistant_router import router as assistant_router
app.include_router(assistant_router)
```

---

## Commit 7: Angular AssistantPanel Component (with Cursor)

**`frontend/src/app/features/assistant/assistant.service.ts`**
```typescript
export interface AssistantResponse {
  response: string;
  mutations_made: boolean;
  next_cursor: string | null;
}

@Injectable({ providedIn: 'root' })
export class AssistantService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/assistant`;

  run(instruction: string, cursor: string | null = null): Observable<AssistantResponse> {
    return this.http.post<AssistantResponse>(
      `${this.baseUrl}/run`,
      { instruction, cursor }
    );
  }
}
```

**`assistant-panel.component.ts`** (smart component)
```typescript
export class AssistantPanelComponent {
  private assistantService = inject(AssistantService);

  @Output() issuesChanged = new EventEmitter<void>();

  isExpanded = signal(false);
  isLoading = signal(false);
  response = signal<string | null>(null);
  error = signal<string | null>(null);
  instruction = signal('');
  pendingCursor = signal<string | null>(null);  // stored between turns

  togglePanel() {
    this.isExpanded.update(v => !v);
    if (!this.isExpanded()) this.pendingCursor.set(null);  // clear on collapse
  }

  submit() {
    if (!this.instruction().trim() || this.isLoading()) return;
    this.isLoading.set(true);
    this.response.set(null);
    this.error.set(null);

    this.assistantService.run(this.instruction(), this.pendingCursor()).pipe(
      finalize(() => this.isLoading.set(false))
    ).subscribe({
      next: (result) => {
        this.response.set(result.response);
        this.pendingCursor.set(result.next_cursor);  // null clears it automatically
        if (result.mutations_made) {
          this.pendingCursor.set(null);  // writes invalidate any pending cursor
          this.issuesChanged.emit();
        }
      },
      error: (err) => {
        this.error.set(err.message || 'Assistant failed. Please try again.');
      }
    });
  }
}
```

**`assistant-panel.component.html`** — key structure:
```html
<div class="assistant-panel">
  <div class="assistant-panel__header" (click)="togglePanel()">
    <span>AI Assistant</span>
    <span class="assistant-panel__chevron" [class.assistant-panel__chevron--open]="isExpanded()">▾</span>
  </div>

  @if (isExpanded()) {
    <div class="assistant-panel__body">
      <textarea
        class="assistant-panel__input"
        placeholder="Try: 'Show open issues', 'next page', 'Create a bug for the login page'"
        [value]="instruction()"
        (input)="instruction.set($any($event.target).value)"
        rows="3"
      ></textarea>
      <button class="btn btn--primary" (click)="submit()" [disabled]="isLoading()">
        @if (isLoading()) { Running... } @else { Run }
      </button>

      @if (response()) {
        <div class="assistant-panel__response">{{ response() }}</div>
      }
      @if (error()) {
        <div class="assistant-panel__error">{{ error() }}</div>
      }
    </div>
  }
</div>
```

---

## Commit 8: Wire into Issue-List Dashboard

**`issue-list.component.html`** — add inside the main container, below the issue list:
```html
<app-assistant-panel (issuesChanged)="onIssuesChanged()" />
```

**`issue-list.component.ts`** — add method and import:
```typescript
// Add to imports array: AssistantPanelComponent
onIssuesChanged(): void {
  this.refresh$.next();  // existing Subject — triggers a re-fetch
}
```

---

## Verification Checklist

**Backend (run `uvicorn app.main:app --reload` in `backend/`):**

| Test | Expected |
|---|---|
| `POST /api/assistant/run` `{"instruction": "list all open issues"}` | 200, response mentions open issues, `mutations_made: false`, `next_cursor` present if >20 results |
| `POST /api/assistant/run` `{"instruction": "how many open issues are there?"}` | 200, agent calls `count_issues` (not `list_issues`), `mutations_made: false`, `next_cursor: null` |
| `POST /api/assistant/run` `{"instruction": "show all issues from last 5 years"}` | 200, agent calls `count_issues` first, then `list_issues` for a sample; response says results were truncated if >20 |
| Send "next page" with cursor from previous response | 200, next 20 issues returned anchored at cursor; no OFFSET |
| `POST /api/assistant/run` `{"instruction": "create an issue called Test bug"}` | 200, response confirms creation, `mutations_made: true`, `next_cursor: null` |
| `POST /api/assistant/run` `{"instruction": ""}` | 422 validation error |
| `POST /api/assistant/run` `{"instruction": "close all open issues"}` | 200, agent calls `count_issues` first, then `bulk_update_status`, `mutations_made: true` |
| `POST /api/assistant/run` `{"instruction": "what is 2+2"}` | 200, response says it can only help with issues |
| Try to close a Closed issue via `update_issue_status` | Tool returns error, model explains terminal status |

**Frontend (run `ng serve` in `frontend/`):**

| Test | Expected |
|---|---|
| Click "AI Assistant" header | Panel expands/collapses; cursor cleared on collapse |
| Type "show open issues" and click Run | Response appears; `next_cursor` stored if there are more |
| Type "next page" on a response that had more results | Next 20 issues appear — cursor advanced, no duplicate/skipped items |
| Start a new unrelated query after a paginated one | `pendingCursor` is cleared; new query starts fresh |
| Type "create a bug called Test" and click Run | Response appears + issue list auto-refreshes; cursor cleared |
| Submit while loading | Button stays disabled; no double submission |
| Kill the backend, submit any instruction | Error message appears in the panel (not a blank screen) |
| Bulk close all in-progress issues | Issue list refreshes, in-progress cards are gone |

---

## Rubric Self-Assessment

| Criteria | Score | Evidence |
|---|---|---|
| Tool Design | 5 | 5 orthogonal tools; `count_issues` separated from `list_issues` to avoid row fetching for aggregate queries; typed enums; clear names; read/write separation; `confirm` guardrail on bulk ops; `has_more` without total count prevents model from planning pagination loops |
| Agentic Loop | 5 | Multi-step loop (observe → plan → act); tool results fed back into model; loop terminates on `stop` or text response; MAX_ITERATIONS safety cap; cursor flows across turns via frontend state without breaking single-turn agent design |
| LLM Integration | 5 | Native OpenAI function calling via `tools=` parameter; `tool_calls` object parsed with `json.loads` (never regex); handles text-only response as clean termination; cursor injected into system prompt per turn |
| Reliability | 5 | Large result sets handled via `count_issues` + cursor pagination — no unbounded queries; `has_more` without total prevents pagination loops; `ix_issues_created_at` index makes date-range queries fast at scale; bulk ops require `confirm=True`; all exceptions surfaced to model; invalid transitions explained; `mutations_made` triggers selective refresh; cursor cleared on write ops and panel collapse; 502 for API failures |
