from __future__ import annotations

import logging


def get_app_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f'remedai.{name}')
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
