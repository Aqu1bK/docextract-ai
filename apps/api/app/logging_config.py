# docextract-ai/apps/api/app/logging_config.py

"""Structured logging setup with structlog.

``print`` output cannot be searched, filtered, or correlated: it is free text
for humans only. Structured logging emits an event name plus key/value pairs,
so a log line such as ``api_started`` can carry ``request_id`` and be queried
by machine in production. That is the difference between reading logs and
using them.

The renderer differs by environment: ``ConsoleRenderer`` prints colorized,
human-readable lines for local development where a person reads the terminal;
``JSONRenderer`` emits one JSON object per line for production, where log
shippers such as Render's log stream ingest and index them. The event data is
identical in both cases.
"""

import logging

import structlog
from structlog.typing import Processor

from app.config import Settings

_LOG_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(settings: Settings) -> None:
    """Configure process-wide structlog for the given settings.

    Raises:
        KeyError: If LOG_LEVEL is not a known level name; startup fails fast
            on a misconfigured environment instead of silently logging
            everything.
    """
    level = _LOG_LEVELS[settings.LOG_LEVEL.upper()]
    renderer: Processor = (
        structlog.dev.ConsoleRenderer()
        if settings.ENVIRONMENT == "development"
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
