from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class BaseImmutableModel(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def serialize(cls, data: Dict[str, Any]) -> "Optional[BaseImmutableModel]":
        pass
