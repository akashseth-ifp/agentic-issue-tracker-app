from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.issue import IssueStatus
from app.repositories.issue_repository import IssueRepository
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services.issue_service import IssueService
from app.core.exceptions import AppException

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "count_issues",
            "description": (
                "Count issues matching filters WITHOUT fetching them. Use this for any question "
                "about quantities, totals, or summaries. Much cheaper than list_issues for large "
                "datasets — always prefer this when you only need a number."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "Filter by status. Omit to count all statuses.",
                    },
                    "created_after": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only count issues created after this date.",
                    },
                    "created_before": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only count issues created before this date.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": (
                "Fetch a page of issues with optional filters. Returns at most 20 results per call. "
                "Use id to look up a specific issue by its numeric ID. "
                "If has_more is true, there are additional results — do NOT call this again to paginate; "
                "instead inform the user and offer to continue if they ask."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "Filter by exact issue ID. Use this when the user asks about a specific issue by number.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "Filter by status. Omit to return all statuses.",
                    },
                    "created_after": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only return issues created after this date.",
                    },
                    "created_before": {
                        "type": "string",
                        "description": "ISO 8601 date (YYYY-MM-DD). Only return issues created before this date.",
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Opaque cursor from a previous list_issues response. Pass this to fetch the next page of results.",
                    },
                },
                "required": [],
            },
        },
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
                        "description": "Short, descriptive title for the issue.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional longer description.",
                    },
                },
                "required": ["title"],
            },
        },
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
                        "description": "The numeric ID of the issue to update.",
                    },
                    "new_status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "The new status value.",
                    },
                },
                "required": ["issue_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bulk_update_status",
            "description": (
                "Update the status of ALL issues currently matching from_status. This affects multiple records. "
                "Only call this after you know how many issues will be affected "
                "(use count_issues first — it returns the exact total without fetching rows). "
                "You MUST set confirm=true to proceed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "Filter: only issues with this status will be updated.",
                    },
                    "to_status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Closed"],
                        "description": "The new status to apply to all matched issues.",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true. Explicit acknowledgement that this will affect multiple records.",
                    },
                },
                "required": ["from_status", "to_status", "confirm"],
            },
        },
    },
]


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
    issue_id = args.get("id")
    status = IssueStatus(args["status"]) if "status" in args else None
    created_after = datetime.fromisoformat(args["created_after"]) if "created_after" in args else None
    created_before = datetime.fromisoformat(args["created_before"]) if "created_before" in args else None
    cursor = args.get("cursor")

    items, has_more, next_cursor = await repo.get_cursor_page(
        page_size=20,
        cursor=cursor,
        issue_id=issue_id,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )
    return {
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status.value,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ],
        "has_more": has_more,
        "next_cursor": next_cursor,
        "is_mutation": False,
    }


async def _create_issue(args: dict, db: AsyncSession) -> dict:
    service = IssueService(db)
    issue = await service.create_issue(IssueCreate(title=args["title"], description=args.get("description")))
    return {"id": issue.id, "title": issue.title, "status": issue.status.value, "is_mutation": True}


async def _update_issue_status(args: dict, db: AsyncSession) -> dict:
    service = IssueService(db)
    issue = await service.update_issue(args["issue_id"], IssueUpdate(status=IssueStatus(args["new_status"])))
    return {"id": issue.id, "title": issue.title, "status": issue.status.value, "is_mutation": True}


async def _bulk_update_status(args: dict, db: AsyncSession) -> dict:
    if not args.get("confirm"):
        return {
            "error": "confirm must be true to execute a bulk update. Call count_issues first to see how many will be affected."
        }
    from_status = IssueStatus(args["from_status"])
    to_status = IssueStatus(args["to_status"])
    VALID = {
        IssueStatus.OPEN: {IssueStatus.IN_PROGRESS},
        IssueStatus.IN_PROGRESS: {IssueStatus.CLOSED, IssueStatus.OPEN},
        IssueStatus.CLOSED: set(),
    }
    if to_status not in VALID[from_status]:
        return {"error": f"Bulk transition from '{from_status.value}' to '{to_status.value}' is not allowed."}
    count = await IssueRepository(db).bulk_update_status(from_status, to_status)
    return {"updated_count": count, "is_mutation": True}
