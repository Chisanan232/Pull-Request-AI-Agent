"""Unit tests for prompt data models."""
import os
from pathlib import Path
from typing import List, Type
from unittest.mock import patch, mock_open

import pytest

from create_pr_bot.ai_bot.prompts.model import (
    BasePrompt,
    SummarizeChangeContentPrompt,
    SummarizeAsPullRequestTitle,
    load_prompt_from_file,
    create_prompt_model,
    get_prompt_model,
    PROMPT_MODEL_MAPPING, PromptName
)


@pytest.fixture
def mock_prompt_content() -> str:
    """Mock prompt content for testing."""
    return "This is a test prompt content."


@pytest.fixture
def sample_prompt_models() -> List[Type[BasePrompt]]:
    """List of sample prompt model classes for testing."""
    return [
        SummarizeChangeContentPrompt,
        SummarizeAsPullRequestTitle,
    ]


def test_base_prompt_dataclass():
    """Test that BasePrompt is a frozen dataclass with a content field."""
    prompt = BasePrompt(content="Test content")
    assert prompt.content == "Test content"

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        prompt.content = "New content"


def test_prompt_models_inherit_from_base(sample_prompt_models):
    """Test that all prompt models inherit from BasePrompt."""
    for model_class in sample_prompt_models:
        assert issubclass(model_class, BasePrompt)

        # Create an instance to ensure it works
        prompt = model_class(content="Test content")
        assert prompt.content == "Test content"

        # Test immutability
        with pytest.raises(AttributeError):
            prompt.content = "New content"


def test_load_prompt_from_file(mock_prompt_content):
    """Test loading prompt content from a file."""
    mock_path = "path/to/prompt.prompt"

    # Mock open to return our test content
    with patch("builtins.open", mock_open(read_data=mock_prompt_content)) as mock_file:
        with patch("pathlib.Path.exists", return_value=True):
            content = load_prompt_from_file(mock_path)

            # Verify the correct file was opened
            mock_file.assert_called_once_with(Path(mock_path), 'r', encoding='utf-8')

            # Verify the content matches
            assert content == mock_prompt_content


def test_load_prompt_from_file_not_found():
    """Test that load_prompt_from_file raises FileNotFoundError for missing files."""
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            load_prompt_from_file("nonexistent_file.prompt")


def test_create_prompt_model(mock_prompt_content):
    """Test creating a prompt model instance."""
    # Mock the load_prompt_from_file function
    with patch(
            "create_pr_bot.ai_bot.prompts.model.load_prompt_from_file",
            return_value=mock_prompt_content
    ):
        # Test with each model class
        for model_class in [SummarizeChangeContentPrompt, SummarizeAsPullRequestTitle]:
            prompt = create_prompt_model(model_class, "test-prompt")

            # Verify the instance has the correct type and content
            assert isinstance(prompt, model_class)
            assert prompt.content == mock_prompt_content


def test_prompt_model_mapping():
    """Test that PROMPT_MODEL_MAPPING contains the expected mappings."""
    expected_mappings = {
        PromptName.SUMMARIZE_CHANGE_CONTENT: SummarizeChangeContentPrompt,
        PromptName.SUMMARIZE_AS_CLEAR_TITLE: SummarizeAsPullRequestTitle,
    }

    for prompt_name, expected_class in expected_mappings.items():
        assert prompt_name in PROMPT_MODEL_MAPPING
        assert PROMPT_MODEL_MAPPING[prompt_name] == expected_class


def test_get_prompt_model(mock_prompt_content):
    """Test getting a prompt model by name."""
    # Mock create_prompt_model to avoid file system access
    with patch(
            "create_pr_bot.ai_bot.prompts.model.create_prompt_model",
            return_value=SummarizeChangeContentPrompt(content=mock_prompt_content)
    ):
        # Test with a valid prompt name
        prompt = get_prompt_model(PromptName.SUMMARIZE_CHANGE_CONTENT)

        # Verify the correct model was returned
        assert isinstance(prompt, SummarizeChangeContentPrompt)
        assert prompt.content == mock_prompt_content


def test_get_prompt_model_unknown_prompt():
    """Test that get_prompt_model raises KeyError for unknown prompt names."""
    with pytest.raises(KeyError):
        get_prompt_model("nonexistent-prompt-name")


def test_real_prompt_file_exists():
    """Test that the actual prompt files exist in the expected location."""
    # This test helps ensure the code will work with the actual project structure
    for prompt_name in PROMPT_MODEL_MAPPING.keys():
        prompts_dir = Path(__file__).parent.parent.parent.parent.parent / "create_pr_bot" / "ai_bot" / "prompts"
        prompt_file = prompts_dir / f"{prompt_name.value}.prompt"

        # Skip this assertion if we're in a CI environment without the actual files
        if not os.environ.get("CI"):
            assert prompt_file.exists(), f"Expected prompt file not found: {prompt_file}"
