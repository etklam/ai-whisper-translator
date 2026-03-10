"""Logger utilities for ASR module."""

import logging

_logger = None


def get_logger(name: str = "asr") -> logging.Logger:
    """Get or create a logger instance."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
    return logging.getLogger(name)
