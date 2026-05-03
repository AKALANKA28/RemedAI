from __future__ import annotations

import logging
import os

DEFAULT_LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'


def configure_logging(level: str | None = None) -> None:
    resolved_level = (level or DEFAULT_LOG_LEVEL).upper()
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(resolved_level)
        return
    logging.basicConfig(level=resolved_level, format=LOG_FORMAT)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or 'backend')
