from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GPTMessage:
    """Represents a message in the GPT conversation."""

    role: str
    content: str


@dataclass(frozen=True)
class GPTChoice:
    """Represents a choice/response from the GPT model."""

    index: int
    message: GPTMessage
    finish_reason: str


@dataclass(frozen=True)
class GPTUsage:
    """Represents token usage information from the GPT response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class GPTResponse:
    """Represents a complete response from the GPT API."""

    id: str
    object: str
    created: int
    model: str
    choices: List[GPTChoice]
    usage: GPTUsage
