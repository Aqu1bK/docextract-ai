"""FastAPI application assembly: lifespan, middleware, handlers, routers.

The full ASGI stack for an incoming HTTP request, top to bottom:

1. ``ServerErrorMiddleware`` (Starlette built-in, outermost) — turns any
   exception that escapes the app into a 500 response.
2. ``CORSMiddleware`` — adds CORS headers to responses and answers preflight
   requests before they reach business code.
3. ``RequestIDMiddleware`` — binds ``request_id`` to the logging context and
   appends ``X-Request-ID`` to the response.
4. ``ExceptionMiddleware`` (Starlette built-in) — converts raised
   ``HTTPException`` and registered application exceptions into responses.
5. Router — matches the path and calls the endpoint function.

Known limitation: a response produced by ``ServerErrorMiddleware`` for an
unhandled exception is emitted by the outermost layer after the inner
middlewares have unwound, so it may lack the ``X-Request-ID`` header.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.config import get_settings
from app.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    request_validation_handler,
    unhandled_exception_handler,
)
from app.logging_config import setup_logging
from app.middleware import RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup and shutdown logic around the application's lifetime.

    Logging is configured at startup so the very first events
    ("api_started" included) already flow through structlog.
    """
    setup_logging(get_settings())
    logger = structlog.get_logger(__name__)
    logger.info("api_started")
    yield
    logger.info("api_stopped")


app = FastAPI(
    title="DocExtract AI API",
    version=get_settings().APP_VERSION,
    description=(
        "Backend API for DocExtract AI, a document extraction and human "
        "review platform: clients upload PDF documents, a queue-driven "
        "pipeline extracts structured fields with confidence scores, and "
        "reviewers approve or reject the results before export."
    ),
    lifespan=lifespan,
)

# Starlette's add_exception_handler stub requires Callable[[Request, Exception]],
# but at runtime it dispatches the caught exception of the registered type, so
# narrower handler parameters are the documented pattern and are safe here.
app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, request_validation_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

# Middleware order: Starlette runs the LAST added middleware OUTERMOST, so
# adding RequestIDMiddleware first and CORSMiddleware second leaves CORS
# outermost. That lets CORS answer preflight requests without them reaching
# request-id binding, while normal requests still pass through both.
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.include_router(api_v1_router)
