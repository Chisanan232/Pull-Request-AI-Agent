"""
Module for prompt data models in the AI bot component.
This module provides dataclasses for different types of prompts used by the AI bot,
along with utility functions to load and create these models from prompt files.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Type, TypeVar


class PromptName(Enum):
    SUMMARIZE_AS_CLEAR_TITLE = "summarize-as-clear-title"
    SUMMARIZE_CHANGE_CONTENT = "summarize-change-content"


# Define a generic type for our prompt models
T = TypeVar("T", bound="BasePrompt")


@dataclass(frozen=True)
class BasePrompt:
    """Base class for all prompt models."""

    content: str


@dataclass(frozen=True)
class SummarizeChangeContentPrompt(BasePrompt):
    """Prompt model for summarizing changes in pull requests."""


@dataclass(frozen=True)
class SummarizeAsPullRequestTitle(BasePrompt):
    """Prompt model for generating pull request titles."""


@dataclass(frozen=True)
class GeneratePRDescriptionPrompt(BasePrompt):
    """Prompt model for generating pull request descriptions."""


# Add other prompt models as needed


def load_prompt_from_file(file_path: str | Path) -> str:
    """
    Load prompt content from a file.

    Args:
        file_path: Path to the prompt file.

    Returns:
        The content of the prompt file as a string.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def create_prompt_model(model_class: Type[T], prompt_name: PromptName) -> T:
    """
    Factory function to create a prompt model instance.

    Args:
        model_class: The dataclass type to instantiate.
        prompt_name: Name of the prompt file (without extension).

    Returns:
        An instance of the specified prompt model class.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
    """
    # Determine the prompt directory
    prompts_dir = Path(__file__).parent
    prompt_file = prompts_dir / f"{prompt_name}.prompt"

    # Load the prompt content
    content = load_prompt_from_file(prompt_file)

    # Create and return the model instance
    return model_class(content=content)


# Mapping from prompt names to model classes for easier access
PROMPT_MODEL_MAPPING: Dict[PromptName, Type[BasePrompt]] = {
    PromptName.SUMMARIZE_CHANGE_CONTENT: SummarizeChangeContentPrompt,
    PromptName.SUMMARIZE_AS_CLEAR_TITLE: SummarizeAsPullRequestTitle,
}


def get_prompt_model(prompt_name: PromptName) -> BasePrompt:
    """
    Get a prompt model instance by name.

    Args:
        prompt_name: Name of the prompt file (without extension).

    Returns:
        An instance of the appropriate prompt model class.

    Raises:
        KeyError: If the prompt name is not in the mapping.
        FileNotFoundError: If the prompt file doesn't exist.
    """
    if prompt_name not in PROMPT_MODEL_MAPPING:
        raise KeyError(f"Unknown prompt name: {prompt_name}")

    model_class = PROMPT_MODEL_MAPPING[prompt_name]
    return create_prompt_model(model_class, prompt_name)
