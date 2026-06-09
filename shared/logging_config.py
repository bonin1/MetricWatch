"""
Structured logging configuration for all MetricWatch services.
"""
import logging
import os
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(service_name: str) -> logging.Logger:
    """Configure root logger with text or JSON output."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json").lower()

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    logger = logging.getLogger(service_name)
    logger.info("Logging initialized", extra={"service": service_name, "format": log_format})
    return logger
