"""
Module for prompt data models in the AI bot component.
This module provides dataclasses for different types of prompts used by the AI bot,
along with utility functions to load and create these models from prompt files.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Dict, List, Type, TypeVar, Optional, Any


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


@dataclass(frozen=True)
class PRPromptData:
    """Data model for processed PR prompt data."""
    
    title: str
    description: str


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
    prompt_file = prompts_dir / f"{prompt_name.value}.prompt"

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


def process_prompt_template(
    prompt_content: str,
    task_tickets_details: List[Dict[str, Any]],
    commits: List[Dict[str, str]]
) -> str:
    """
    Process a prompt template by replacing variables with actual values.

    Args:
        prompt_content: The content of the prompt template.
        task_tickets_details: List of task ticket details.
        commits: List of commit details.

    Returns:
        The processed prompt with variables replaced.
    """
    # Replace task tickets details
    if "{{ task_tickets_details }}" in prompt_content:
        # Convert task tickets to JSON string
        import json
        task_tickets_json = json.dumps(task_tickets_details, indent=2)
        prompt_content = prompt_content.replace("{{ task_tickets_details }}", task_tickets_json)
    
    # Replace commits
    if "{{ all_commits }}" in prompt_content:
        # Format commits as a list of short_hash and message
        formatted_commits = []
        for commit in commits:
            if "short_hash" in commit and "message" in commit:
                formatted_commits.append(f"{commit['short_hash']}: {commit['message']}")
        
        commits_text = "\n".join(formatted_commits)
        prompt_content = prompt_content.replace("{{ all_commits }}", commits_text)
    
    return prompt_content


def prepare_pr_prompt_data(
    task_tickets_details: List[Dict[str, Any]],
    commits: List[Dict[str, str]]
) -> PRPromptData:
    """
    Prepare PR prompt data by processing prompt templates.

    Args:
        task_tickets_details: List of task ticket details.
        commits: List of commit details with short_hash and message.

    Returns:
        PRPromptData object with processed title and description prompts.

    Raises:
        FileNotFoundError: If any prompt file is not found.
    """
    # Get prompt models
    title_prompt_model = get_prompt_model(PromptName.SUMMARIZE_AS_CLEAR_TITLE)
    description_prompt_model = get_prompt_model(PromptName.SUMMARIZE_CHANGE_CONTENT)
    
    # Process prompt templates
    title_prompt = process_prompt_template(
        title_prompt_model.content,
        task_tickets_details,
        commits
    )
    
    description_prompt = process_prompt_template(
        description_prompt_model.content,
        task_tickets_details,
        commits
    )
    
    # Return processed prompts
    return PRPromptData(
        title=title_prompt,
        description=description_prompt
    )
