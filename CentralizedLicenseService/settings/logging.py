"""
Logging configuration for structured logging to Loki.

This module configures JSON logging that works well with Loki.
"""

import json
import logging
import sys
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds trace context."""

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add trace context if available
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                trace_context = span.get_span_context()
                log_record['trace_id'] = format(trace_context.trace_id, '032x')
                log_record['span_id'] = format(trace_context.span_id, '016x')
        except Exception:
            pass


def get_logging_config(environment: str = "development") -> dict:
    """
    Get logging configuration for the application.
    
    Args:
        environment: Environment name (development, production, test)
    
    Returns:
        Django logging configuration dictionary
    """
    log_level = "DEBUG" if environment == "development" else "INFO"
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": CustomJsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            },
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {message}",
                "style": "{",
            },
        },
        "filters": {},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": "/var/log/license-service/application.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "core": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "api": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "licenses": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "brands": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "products": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "activations": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
        },
    }

