"""Attach a request_id to logs for the lifetime of an HTTP request."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_context import new_request_id, set_request_id, set_run_id, set_user_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = new_request_id()
        # Do not reset in finally — BackgroundTasks still run after call_next
        # returns and must keep uid from get_current_user.
        set_request_id(rid)
        set_user_id("-")
        set_run_id("-")
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response
