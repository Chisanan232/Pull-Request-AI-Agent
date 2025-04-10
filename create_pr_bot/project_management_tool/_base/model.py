from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class BaseImmutableModel(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def serialize(cls, data: Dict[str, Any]) -> "BaseImmutableModel":
        pass
