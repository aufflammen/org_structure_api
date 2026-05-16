"""Structured logging setup using structlog."""

import logging
import sys
from typing import Any

import structlog


def _reorder_keys(desired_order: list[str]):
    def processor(logger, method_name, event_dict):
        new_dict = {}
        for key in desired_order:
            if key in event_dict:
                new_dict[key] = event_dict.pop(key)
        new_dict.update(event_dict)
        return new_dict

    return processor


def setup_logger(log_level: str = "INFO") -> None:
    """Configure stdlib logging and structlog for JSON-friendly output."""
    level: int = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            _reorder_keys(["level", "timestamp", "event"]),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger."""
    return structlog.get_logger(name)
