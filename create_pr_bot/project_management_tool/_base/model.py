from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class BaseImmutableModel(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def serialize(cls, data: Dict[str, Any]) -> "BaseImmutableModel":
        pass
