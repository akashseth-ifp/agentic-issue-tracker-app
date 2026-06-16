from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

class IssueNotFoundException(AppException):
    def __init__(self, issue_id: int):
        super().__init__(404, f"Issue with id {issue_id} not found")

class InvalidStatusTransitionException(AppException):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(422, f"Cannot transition from '{from_status}' to '{to_status}'")

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )