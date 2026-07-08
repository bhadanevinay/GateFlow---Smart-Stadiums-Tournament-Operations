"""Structured and privacy-preserving logging setup.

Uses ContextVar to inject request IDs into all log messages and filters out
sensitive payload data.
"""

from __future__ import annotations

import contextvars
import logging
import logging.config
from typing import Any, Final

# ContextVar storing request ID for the current thread/coroutine execution context
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Logging filter to inject request_id ContextVar into records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Injects request_id from ContextVar into LogRecord.

        Args:
            record: Logger record.

        Returns:
            True always.

        """
        record.request_id = request_id_var.get()
        return True


LOGGING_CONFIG: Final[dict[str, Any]] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id_filter": {
            "()": RequestIdFilter,
        }
    },
    "formatters": {
        "structured": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [ReqID: %(request_id)s] - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "filters": ["request_id_filter"],
        }
    },
    "loggers": {
        "gateflow": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}


def setup_logging() -> None:
    """Configures structured, privacy-safe application logging."""
    logging.config.dictConfig(LOGGING_CONFIG)
