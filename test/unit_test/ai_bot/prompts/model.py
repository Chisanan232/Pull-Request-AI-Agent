"""Unit tests for prompt data models."""

from typing import List, Type
from unittest.mock import Mock
import json
import os
from enum import Enum
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from create_pr_bot.ai_bot.prompts.model import (
    PROMPT_MODEL_MAPPING,
    BasePrompt,
    PromptName,
    load_prompt_from_file,
    create_prompt_model,
    get_prompt_model,
    process_prompt_template,
    prepare_pr_prompt_data,
    SummarizeAsPullRequestTitle,
    SummarizeChangeContentPrompt,
    PRPromptData
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
            mock_file.assert_called_once_with(Path(mock_path), "r", encoding="utf-8")

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
    prompt_name = Mock()
    prompt_name.value = "test-prompt"
    with patch("create_pr_bot.ai_bot.prompts.model.load_prompt_from_file", return_value=mock_prompt_content):
        # Test with each model class
        for model_class in [SummarizeChangeContentPrompt, SummarizeAsPullRequestTitle]:
            prompt = create_prompt_model(model_class, prompt_name)

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
        return_value=SummarizeChangeContentPrompt(content=mock_prompt_content),
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


class TestPromptModel:
    """Tests for the prompt model module."""

    def test_load_prompt_from_file(self):
        """Test loading prompt content from a file."""
        # Mock the open function
        mock_content = "This is a test prompt"
        with patch("builtins.open", mock_open(read_data=mock_content)) as mock_file:
            # Mock Path.exists to return True
            with patch("pathlib.Path.exists", return_value=True):
                content = load_prompt_from_file("test_prompt.prompt")
                assert content == mock_content
                mock_file.assert_called_once_with(Path("test_prompt.prompt"), "r", encoding="utf-8")

    def test_load_prompt_from_file_not_found(self):
        """Test loading prompt content from a non-existent file."""
        # Mock Path.exists to return False
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                load_prompt_from_file("non_existent_prompt.prompt")

    def test_create_prompt_model(self):
        """Test creating a prompt model."""
        # Mock load_prompt_from_file
        with patch("create_pr_bot.ai_bot.prompts.model.load_prompt_from_file", return_value="Test content"):
            # Create a prompt model
            model = create_prompt_model(SummarizeAsPullRequestTitle, PromptName.SUMMARIZE_AS_CLEAR_TITLE)

            # Verify the model
            assert isinstance(model, SummarizeAsPullRequestTitle)
            assert model.content == "Test content"

    def test_get_prompt_model(self):
        """Test getting a prompt model by name."""
        # Mock create_prompt_model
        with patch("create_pr_bot.ai_bot.prompts.model.create_prompt_model") as mock_create:
            mock_create.return_value = SummarizeAsPullRequestTitle(content="Test content")

            # Get a prompt model
            model = get_prompt_model(PromptName.SUMMARIZE_AS_CLEAR_TITLE)

            # Verify the model
            assert isinstance(model, SummarizeAsPullRequestTitle)
            assert model.content == "Test content"
            mock_create.assert_called_once_with(SummarizeAsPullRequestTitle, PromptName.SUMMARIZE_AS_CLEAR_TITLE)

    def test_get_prompt_model_unknown(self):
        """Test getting a prompt model with an unknown name."""

        # Create a mock enum value that's not in the mapping
        class MockPromptName(Enum):
            UNKNOWN = "unknown"

        # Try to get a prompt model with an unknown name
        with pytest.raises(KeyError):
            get_prompt_model(MockPromptName.UNKNOWN)

    def test_process_prompt_template(self):
        """Test processing a prompt template."""
        # Create a test prompt template
        template = """
        Task tickets:
        ```json
        {{ task_tickets_details }}
        ```

        Commits:
        ```shell
        {{ all_commits }}
        ```
        """

        # Create test data
        task_tickets = [
            {"id": "PROJ-123", "title": "Fix bug", "description": "Fix the login bug", "status": "In Progress"},
            {"id": "PROJ-456", "title": "Add feature", "description": "Add a new feature", "status": "Done"}
        ]

        commits = [
            {"short_hash": "abc123", "message": "Fix login bug"},
            {"short_hash": "def456", "message": "Add new feature"}
        ]

        # Process the template
        result = process_prompt_template(template, task_tickets, commits)

        # Verify the result
        assert "Task tickets:" in result
        assert json.dumps(task_tickets, indent=2) in result
        assert "Commits:" in result
        assert "abc123: Fix login bug" in result
        assert "def456: Add new feature" in result

    def test_process_prompt_template_empty_data(self):
        """Test processing a prompt template with empty data."""
        # Create a test prompt template
        template = """
        Task tickets:
        ```json
        {{ task_tickets_details }}
        ```

        Commits:
        ```shell
        {{ all_commits }}
        ```
        """

        # Process the template with empty data
        result = process_prompt_template(template, [], [])

        # Verify the result
        assert "Task tickets:" in result
        assert "[]" in result
        assert "Commits:" in result
        assert "{{ all_commits }}" not in result

    def test_prepare_pr_prompt_data(self):
        """Test preparing PR prompt data."""
        # Mock get_prompt_model
        with patch("create_pr_bot.ai_bot.prompts.model.get_prompt_model") as mock_get_prompt:
            # Mock the prompt models
            title_prompt = SummarizeAsPullRequestTitle(
                content="Title template: {{ task_tickets_details }} {{ all_commits }}")
            description_prompt = SummarizeChangeContentPrompt(
                content="Description template: {{ task_tickets_details }} {{ all_commits }}")
            mock_get_prompt.side_effect = [title_prompt, description_prompt]

            # Create test data
            task_tickets = [{"id": "PROJ-123", "title": "Fix bug"}]
            commits = [{"short_hash": "abc123", "message": "Fix login bug"}]

            # Prepare PR prompt data
            result = prepare_pr_prompt_data(task_tickets, commits)

            # Verify the result
            assert isinstance(result, PRPromptData)
            assert "Title template:" in result.title
            assert "Description template:" in result.description
            assert json.dumps(task_tickets, indent=2) in result.title
            assert json.dumps(task_tickets, indent=2) in result.description
            assert "abc123: Fix login bug" in result.title
            assert "abc123: Fix login bug" in result.description

    def test_prepare_pr_prompt_data_file_not_found(self):
        """Test preparing PR prompt data with a missing file."""
        # Mock get_prompt_model to raise FileNotFoundError
        with patch("create_pr_bot.ai_bot.prompts.model.get_prompt_model", side_effect=FileNotFoundError("Test error")):
            # Create test data
            task_tickets = [{"id": "PROJ-123", "title": "Fix bug"}]
            commits = [{"short_hash": "abc123", "message": "Fix login bug"}]

            # Try to prepare PR prompt data
            with pytest.raises(FileNotFoundError):
                prepare_pr_prompt_data(task_tickets, commits)
