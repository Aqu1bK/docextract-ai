# docextract-ai/apps/api/app/middleware.py

"""Request-id middleware built as pure ASGI.

``contextvars.ContextVar`` stores per-request values without passing them
through every function signature, and asyncio keeps one context per request
task — two concurrent requests never see each other's id. A module-level
global variable would be shared by all requests and race under concurrency.

The middleware is written as pure ASGI (``__call__(scope, receive, send)``)
rather than subclassing ``BaseHTTPMiddleware``. ``BaseHTTPMiddleware`` wraps
the app in a task and a streaming response, which historically adds overhead
and interacts badly with background tasks and early disconnects; pure ASGI
middlewares are what Starlette's own ``CORSMiddleware`` and
``ExceptionMiddleware`` use.
"""

import uuid
from contextvars import ContextVar

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "x-request-id"

REQUEST_ID_VAR: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware:
    """Bind a request id to the context and echo it on the response.

    Reads an incoming ``x-request-id`` header so a caller (or an upstream
    proxy) can correlate its own logs with ours; generates a uuid4 hex value
    when the header is absent.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the next ASGI application in the middleware stack."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI request: set the id, delegate, append the header."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = REQUEST_ID_VAR.set(request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            structlog.contextvars.clear_contextvars()
            REQUEST_ID_VAR.reset(token)


def get_request_id() -> str:
    """Return the current request id, or "unknown" outside a request scope."""
    return REQUEST_ID_VAR.get() or "unknown"
