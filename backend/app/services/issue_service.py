from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.issue_repository import IssueRepository
from app.core.exceptions import IssueNotFoundException, InvalidStatusTransitionException
from app.models.issue import Issue, IssueStatus
from app.schemas.issue import IssueCreate, IssueUpdate

VALID_TRANSITIONS: dict[IssueStatus, set[IssueStatus]] = {
    IssueStatus.OPEN: {IssueStatus.IN_PROGRESS},
    IssueStatus.IN_PROGRESS: {IssueStatus.CLOSED, IssueStatus.OPEN},
    IssueStatus.CLOSED: set(),  # terminal — no exit
}

class IssueService:
    def __init__(self, db: AsyncSession):
        self.repo = IssueRepository(db)

    async def get_all_issues(self, page: int, page_size: int) -> tuple[list[Issue], int]:
        return await self.repo.get_all(page=page, page_size=page_size)

    async def get_issue_or_raise(self, issue_id: int) -> Issue:
        issue = await self.repo.get_by_id(issue_id)
        if issue is None:
            raise IssueNotFoundException(issue_id)
        return issue

    async def create_issue(self, data: IssueCreate) -> Issue:
        return await self.repo.create(data)

    async def update_issue(self, issue_id: int, data: IssueUpdate) -> Issue:
        issue = await self.get_issue_or_raise(issue_id)
        if data.status is not None and data.status != issue.status:
            allowed = VALID_TRANSITIONS.get(issue.status, set())
            if data.status not in allowed:
                raise InvalidStatusTransitionException(
                    issue.status.value, data.status.value
                )
        return await self.repo.update(issue, data)

    async def delete_issue(self, issue_id: int) -> None:
        issue = await self.get_issue_or_raise(issue_id)
        await self.repo.delete(issue)