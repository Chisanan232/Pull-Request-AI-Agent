"""
Module for prompt data models in the AI bot component.
This module provides dataclasses for different types of prompts used by the AI bot,
along with utility functions to load and create these models from prompt files.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Type, TypeVar, Union

logger = logging.getLogger(__name__)


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


class PromptVariable(Enum):
    TASK_TICKETS_DETAILS = "{{ task_tickets_details }}"
    ALL_COMMITS = "{{ all_commits }}"
    PULL_REQUEST_TEMPLATE = "{{ pull_request_template }}"


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
    logger.debug(f"Loading prompt file from: {path}")
    
    if not path.exists():
        logger.error(f"Prompt file not found: {path}")
        raise FileNotFoundError(f"Prompt file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
        
        logger.debug(f"Successfully loaded prompt file ({len(content)} characters)")
        return content
    except Exception as e:
        logger.error(f"Error loading prompt file {path}: {str(e)}")
        raise


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
    logger.debug(f"Creating prompt model of type {model_class.__name__} for {prompt_name.value}")
    
    # Determine the prompt directory
    prompts_dir = Path(__file__).parent
    prompt_file = prompts_dir / f"{prompt_name.value}.prompt"
    logger.debug(f"Looking for prompt file at: {prompt_file}")

    try:
        # Load the prompt content
        content = load_prompt_from_file(prompt_file)

        # Create and return the model instance
        model = model_class(content=content)
        logger.debug(f"Successfully created {model_class.__name__} prompt model")
        return model
    except Exception as e:
        logger.error(f"Failed to create prompt model: {str(e)}")
        raise


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
    # Use the enum value for logging
    logger.debug(f"Getting prompt model for: {prompt_name.value}")
    
    # Check if prompt name is in mapping
    if prompt_name not in PROMPT_MODEL_MAPPING:
        logger.error(f"Unknown prompt name: {prompt_name}")
        raise KeyError(f"Unknown prompt name: {prompt_name}")

    model_class = PROMPT_MODEL_MAPPING[prompt_name]
    logger.debug(f"Using model class: {model_class.__name__}")
    
    try:
        return create_prompt_model(model_class, prompt_name)
    except Exception as e:
        logger.error(f"Failed to get prompt model for {prompt_name.value}: {str(e)}")
        raise


def process_prompt_template(
    prompt_content: str,
    task_tickets_details: List[Dict[str, Any]],
    commits: List[Dict[str, str]],
    project_root: str = ".",
) -> str:
    """
    Process a prompt template by replacing variables with actual values.

    Args:
        prompt_content: The content of the prompt template.
        task_tickets_details: List of task ticket details.
        commits: List of commit details.
        project_root: Root directory of the project. If provided, will look for PR template.

    Returns:
        The processed prompt with variables replaced.
    """
    logger.debug(f"Processing prompt template (original length: {len(prompt_content)} characters)")
    logger.debug(f"Prompt variables to replace: task_tickets={len(task_tickets_details)}, commits={len(commits)}")
    
    # Replace task tickets details
    prompt_var_task_details = PromptVariable.TASK_TICKETS_DETAILS.value
    if prompt_var_task_details in prompt_content:
        logger.debug(f"Replacing {prompt_var_task_details} variable")
        try:
            # Convert task tickets to JSON string
            task_tickets_json = json.dumps(task_tickets_details, indent=2)
            logger.debug(f"Task tickets JSON created ({len(task_tickets_json)} characters)")
            prompt_content = prompt_content.replace("%s" % prompt_var_task_details, task_tickets_json)
        except Exception as e:
            logger.error(f"Error replacing task tickets variable: {str(e)}")
            # Continue with other replacements even if this one fails

    # Replace commits
    prompt_var_all_commits = PromptVariable.ALL_COMMITS.value
    if ("%s" % prompt_var_all_commits) in prompt_content:
        logger.debug(f"Replacing {prompt_var_all_commits} variable with {len(commits)} commits")
        try:
            # Format commits as a list of short_hash and message
            formatted_commits = []
            for commit in commits:
                if "short_hash" in commit and "message" in commit:
                    formatted_commits.append(f"{commit['short_hash']}: {commit['message']}")
                else:
                    logger.warning(f"Skipping commit with missing fields: {commit}")

            commits_text = "\n".join(formatted_commits)
            logger.debug(f"Formatted commits text ({len(commits_text)} characters)")
            prompt_content = prompt_content.replace(prompt_var_all_commits, commits_text)
        except Exception as e:
            logger.error(f"Error replacing commits variable: {str(e)}")
            # Continue with other replacements even if this one fails

    # Replace pull request template
    prompt_var_pr_template = PromptVariable.PULL_REQUEST_TEMPLATE.value
    if prompt_var_pr_template in prompt_content and project_root:
        logger.debug(f"Looking for PR template to replace {prompt_var_pr_template}")
        try:
            # Look for the PR template file
            pr_template_path = Path(project_root) / ".github" / "PULL_REQUEST_TEMPLATE.md"
            logger.debug(f"Checking for PR template at: {pr_template_path}")

            if pr_template_path.exists():
                logger.info(f"Found PR template at: {pr_template_path}")
                with open(pr_template_path, "r", encoding="utf-8") as file:
                    pr_template_content = file.read()
                logger.debug(f"Loaded PR template ({len(pr_template_content)} characters)")
                prompt_content = prompt_content.replace(prompt_var_pr_template, pr_template_content)
            else:
                # If template doesn't exist, replace with empty string
                logger.warning(f"PR template not found at {pr_template_path}, using empty string")
                prompt_content = prompt_content.replace(prompt_var_pr_template, "")
        except Exception as e:
            logger.error(f"Error replacing PR template variable: {str(e)}")
            # Continue even if this replacement fails

    logger.debug(f"Prompt template processing complete (final length: {len(prompt_content)} characters)")
    return prompt_content


def prepare_pr_prompt_data(
    task_tickets_details: List[Dict[str, Any]], commits: List[Dict[str, str]], project_root: str = "."
) -> PRPromptData:
    """
    Prepare PR prompt data by processing prompt templates.

    Args:
        task_tickets_details: List of task ticket details.
        commits: List of commit details with short_hash and message.
        project_root: Root directory of the project. If provided, will look for PR template.

    Returns:
        PRPromptData containing processed title and description prompts.
    """
    logger.info("Preparing PR prompt data")
    
    try:
        # Get title prompt
        logger.debug("Getting title prompt model")
        title_prompt_model = get_prompt_model(PromptName.SUMMARIZE_AS_CLEAR_TITLE)
        title_prompt_content = title_prompt_model.content

        # Get description prompt
        logger.debug("Getting description prompt model")
        description_prompt_model = get_prompt_model(PromptName.SUMMARIZE_CHANGE_CONTENT)
        description_prompt_content = description_prompt_model.content

        # Process prompts
        logger.debug("Processing prompt templates with variable substitution")
        title_prompt = process_prompt_template(
            title_prompt_content, task_tickets_details, commits, project_root
        )
        description_prompt = process_prompt_template(
            description_prompt_content, task_tickets_details, commits, project_root
        )

        logger.info("Successfully prepared PR prompt data")
        logger.debug(f"Title prompt: {len(title_prompt)} characters")
        logger.debug(f"Title prompt: {title_prompt}")
        logger.debug(f"Description prompt: {len(description_prompt)} characters")
        logger.debug(f"Description: {description_prompt}")

        return PRPromptData(title=title_prompt, description=description_prompt)
    except Exception as e:
        logger.error(f"Error preparing PR prompt data: {str(e)}", exc_info=True)
        raise
