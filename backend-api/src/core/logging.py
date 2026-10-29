"""
Logging configuration for Masjid Connect application.

Provides structured JSON logging with correlation IDs for distributed tracing
across microservices. Supports different log levels per environment.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that injects correlation_id into log records.

    The correlation_id is thread-local and enables request tracking
    across microservices in distributed systems.
    """

    _correlation_id: Dict[int, str] = {}

    @classmethod
    def set_correlation_id(cls, correlation_id: str) -> None:
        """
        Set correlation ID for current thread.

        Args:
            correlation_id: Unique identifier for request tracing
        """
        import threading

        cls._correlation_id[threading.get_ident()] = correlation_id

    @classmethod
    def get_correlation_id(cls) -> Optional[str]:
        """
        Get correlation ID for current thread.

        Returns:
            Current correlation ID or None
        """
        import threading

        return cls._correlation_id.get(threading.get_ident())

    @classmethod
    def clear_correlation_id(cls) -> None:
        """Clear correlation ID for current thread."""
        import threading

        cls._correlation_id.pop(threading.get_ident(), None)

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Inject correlation_id into log record.

        Args:
            record: Log record to filter

        Returns:
            True to process the record
        """
        record.correlation_id = self.get_correlation_id() or "unknown"
        record.timestamp = datetime.utcnow().isoformat() + "Z"
        return True


class StructuredFormatter(jsonlogger.JsonFormatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON with standardized fields for easier parsing
    in centralized logging systems (ELK, Datadog, etc).
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """
        Add custom fields to log record.

        Args:
            log_record: Dictionary to add fields to
            record: Python log record
            message_dict: Dictionary with message and args
        """
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["correlation_id"] = getattr(record, "correlation_id", "unknown")
        log_record["level"] = record.levelname
        log_record["logger"] = record.name


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Get configured logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    logger.addFilter(correlation_filter)

    # Configure handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s %(correlation_id)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
