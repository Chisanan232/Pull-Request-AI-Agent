from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ClaudeContent:
    """Represents a content element in Claude messages."""
    type: str
    text: str


@dataclass(frozen=True)
class ClaudeMessage:
    """Represents a message in the Claude API response."""
    id: str
    type: str
    role: str
    content: List[ClaudeContent]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None


@dataclass(frozen=True)
class ClaudeUsage:
    """Represents token usage information from the Claude response."""
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ClaudeResponse:
    """Represents a complete response from the Claude API."""
    id: str
    type: str
    role: str
    content: List[ClaudeContent]
    model: str
    stop_reason: Optional[str]
    stop_sequence: Optional[str]
    usage: ClaudeUsage
