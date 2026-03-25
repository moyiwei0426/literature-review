from __future__ import annotations

import logging
from typing import Optional

from .settings import get_settings


LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "project=%(project_id)s task=%(task_id)s | %(message)s"
)


class ContextAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("project_id", self.extra.get("project_id", "-"))
        extra.setdefault("task_id", self.extra.get("task_id", "-"))
        return msg, kwargs


_configured = False


def configure_logging(level: Optional[str] = None) -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    logging.basicConfig(
        level=(level or settings.log_level).upper(),
        format=LOG_FORMAT,
    )
    _configured = True


def get_logger(name: str, *, project_id: str = "-", task_id: str = "-") -> ContextAdapter:
    configure_logging()
    logger = logging.getLogger(name)
    return ContextAdapter(logger, {"project_id": project_id, "task_id": task_id})
