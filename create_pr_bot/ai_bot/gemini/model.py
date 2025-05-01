from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass(frozen=True)
class GeminiContent:
    """Represents a part in the Gemini content."""
    text: str
    role: Optional[str] = None


@dataclass(frozen=True)
class GeminiCandidate:
    """Represents a response candidate from the Gemini model."""
    content: GeminiContent
    finish_reason: str
    index: int
    safety_ratings: List[Dict[str, Any]]


@dataclass(frozen=True)
class GeminiPromptFeedback:
    """Represents feedback on the prompt."""
    safety_ratings: List[Dict[str, Any]]


@dataclass(frozen=True)
class GeminiUsage:
    """Represents token usage information from the Gemini response."""
    prompt_token_count: int
    candidates_token_count: int
    total_token_count: int


@dataclass(frozen=True)
class GeminiResponse:
    """Represents a complete response from the Gemini API."""
    candidates: List[GeminiCandidate]
    prompt_feedback: GeminiPromptFeedback
    usage: GeminiUsage
