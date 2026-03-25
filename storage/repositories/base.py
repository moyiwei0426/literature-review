from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    @abstractmethod
    def save_json(self, category: str, name: str, payload: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def read_json(self, category: str, name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def list_json(self, category: str) -> list[str]:
        raise NotImplementedError
