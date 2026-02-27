"""
Structlog configuration for the Rental Management Suite.

Uses ConsoleRenderer (human-readable) — appropriate for a self-hosted tool
where logs are read directly by the operator, not consumed by a log aggregator.
"""

import logging

import structlog


def configure_logging() -> None:
    """Configure structlog for human-readable console output.

    Integrates with stdlib logging so that uvicorn and SQLAlchemy log
    messages flow through the same formatted output.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Configure stdlib logging so uvicorn/SQLAlchemy logs are formatted consistently
    logging.basicConfig(format="%(message)s", level=logging.INFO)
