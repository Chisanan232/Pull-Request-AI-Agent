"""Unit tests for prompt data models."""

import json
import os
from pathlib import Path
from typing import List, Type
from unittest.mock import Mock, mock_open, patch

import pytest

from pull_request_ai_agent.ai_bot.prompts.model import (
    PROMPT_MODEL_MAPPING,
    BasePrompt,
    PromptName,
    PRPromptData,
    SummarizeAsPullRequestTitle,
    SummarizeChangeContentPrompt,
    create_prompt_model,
    get_prompt_model,
    load_prompt_from_file,
    prepare_pr_prompt_data,
    process_prompt_template,
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
    with patch("pull_request_ai_agent.ai_bot.prompts.model.load_prompt_from_file", return_value=mock_prompt_content):
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
        "pull_request_ai_agent.ai_bot.prompts.model.create_prompt_model",
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
        with patch.dict(PROMPT_MODEL_MAPPING, {}, clear=True):
            get_prompt_model(PromptName.SUMMARIZE_AS_CLEAR_TITLE)


def test_real_prompt_file_exists():
    """Test that the actual prompt files exist in the expected location."""
    # This test helps ensure the code will work with the actual project structure
    for prompt_name in PROMPT_MODEL_MAPPING.keys():
        prompts_dir = Path(__file__).parent.parent.parent.parent.parent / "pull_request_ai_agent" / "ai_bot" / "prompts"
        prompt_file = prompts_dir / f"{prompt_name.value}.prompt"

        # Skip this assertion if we're in a CI environment without the actual files
        if not os.environ.get("CI"):
            assert prompt_file.exists(), f"Expected prompt file not found: {prompt_file}"


class TestPromptModel:
    """Tests for the prompt model module."""

    def test_load_prompt_from_file(self, mock_prompt_content: str) -> None:
        """Test loading prompt content from a file."""
        # Mock the open function
        mock_path = "path/to/prompt.prompt"
        with patch("builtins.open", mock_open(read_data=mock_prompt_content)) as mock_file:
            # Mock Path.exists to return True
            with patch("pathlib.Path.exists", return_value=True):
                content = load_prompt_from_file(mock_path)

                # Verify the correct file was opened
                mock_file.assert_called_once_with(Path(mock_path), "r", encoding="utf-8")

                # Verify the content matches
                assert content == mock_prompt_content

    def test_load_prompt_from_file_not_found(self) -> None:
        """Test loading prompt content from a non-existent file."""
        # Mock Path.exists to return False
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                load_prompt_from_file("non_existent_prompt.prompt")

    def test_create_prompt_model(self, mock_prompt_content: str) -> None:
        """Test creating a prompt model."""
        # Mock load_prompt_from_file
        prompt_name = Mock()
        prompt_name.value = "test-prompt"
        with patch(
            "pull_request_ai_agent.ai_bot.prompts.model.load_prompt_from_file", return_value=mock_prompt_content
        ):
            # Create a prompt model
            model = create_prompt_model(SummarizeAsPullRequestTitle, prompt_name)

            # Verify the model
            assert isinstance(model, SummarizeAsPullRequestTitle)
            assert model.content == mock_prompt_content

    def test_get_prompt_model(self, mock_prompt_content: str) -> None:
        """Test getting a prompt model by name."""
        # Mock create_prompt_model
        with patch("pull_request_ai_agent.ai_bot.prompts.model.create_prompt_model") as mock_create:
            mock_create.return_value = SummarizeAsPullRequestTitle(content=mock_prompt_content)

            # Get a prompt model
            model = get_prompt_model(PromptName.SUMMARIZE_AS_CLEAR_TITLE)

            # Verify the model
            assert isinstance(model, SummarizeAsPullRequestTitle)
            assert model.content == mock_prompt_content
            mock_create.assert_called_once_with(SummarizeAsPullRequestTitle, PromptName.SUMMARIZE_AS_CLEAR_TITLE)

    def test_get_prompt_model_unknown(self) -> None:
        """Test getting a prompt model with an unknown name."""

        # Create a mock enum value that's not in the mapping
        unknown_prompt_name = PromptName.SUMMARIZE_AS_CLEAR_TITLE

        # Try to get a prompt model with an unknown name
        with patch.dict(PROMPT_MODEL_MAPPING, {}, clear=True):
            with pytest.raises(KeyError):
                get_prompt_model(unknown_prompt_name)

    def test_process_prompt_template(self, mock_prompt_content: str) -> None:
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
            {"id": "PROJ-456", "title": "Add feature", "description": "Add a new feature", "status": "Done"},
        ]

        commits = [
            {"short_hash": "abc123", "message": "Fix login bug"},
            {"short_hash": "def456", "message": "Add new feature"},
        ]

        # Process the template
        result = process_prompt_template(template, task_tickets, commits)

        # Verify the result
        assert "Task tickets:" in result
        assert json.dumps(task_tickets, indent=2) in result
        assert "Commits:" in result
        assert "abc123: Fix login bug" in result
        assert "def456: Add new feature" in result

    def test_process_prompt_template_empty_data(self) -> None:
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

    def test_process_prompt_template_with_pr_template(self, mock_prompt_content: str) -> None:
        """Test processing a prompt template with PR template."""
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

        PR Template:
        ```
        {{ pull_request_template }}
        ```
        """

        # Create test data
        task_tickets = [{"id": "PROJ-123", "title": "Fix bug"}]
        commits = [{"short_hash": "abc123", "message": "Fix login bug"}]

        # Mock project root and PR template file
        mock_pr_template = "## PR Template\n* Task ID: \n* Description: "

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_pr_template)):
                # Process the template
                result = process_prompt_template(template, task_tickets, commits, project_root="/fake/path")

                # Verify the result
                assert "Task tickets:" in result
                assert "Commits:" in result
                assert "PR Template:" in result
                assert mock_pr_template in result

    def test_process_prompt_template_without_pr_template_file(self) -> None:
        """Test processing a prompt template when PR template file doesn't exist."""
        # Create a test prompt template
        template = """
        PR Template:
        ```
        {{ pull_request_template }}
        ```
        """

        # Mock project root but PR template file doesn't exist
        with patch("pathlib.Path.exists", return_value=False):
            # Process the template
            result = process_prompt_template(template, [], [], project_root="/fake/path")

            # Verify the result
            assert "PR Template:" in result
            assert "{{ pull_request_template }}" not in result
            filtered_result = result.replace("PR Template:", "").replace("{{ pull_request_template }}", "")
            empty_result = filtered_result.replace("\n", "").replace(" ", "").replace("```", "")
            assert empty_result == ""

    def test_prepare_pr_prompt_data(self, mock_prompt_content: str) -> PRPromptData:
        """Test preparing PR prompt data."""
        # Mock get_prompt_model
        with patch("pull_request_ai_agent.ai_bot.prompts.model.get_prompt_model") as mock_get_prompt:
            # Mock the prompt models
            title_prompt = SummarizeAsPullRequestTitle(
                content="Title template: {{ task_tickets_details }} {{ all_commits }}"
            )
            description_prompt = SummarizeChangeContentPrompt(
                content="Description template: {{ task_tickets_details }} {{ all_commits }}"
            )
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
            return result

    def test_prepare_pr_prompt_data_with_project_root(self, mock_prompt_content: str) -> PRPromptData:
        """Test preparing PR prompt data with project root."""
        # Mock get_prompt_model
        with patch("pull_request_ai_agent.ai_bot.prompts.model.get_prompt_model") as mock_get_prompt:
            # Mock the prompt models
            title_prompt = SummarizeAsPullRequestTitle(content="Title: {{ pull_request_template }}")
            description_prompt = SummarizeChangeContentPrompt(content="Description: {{ pull_request_template }}")
            mock_get_prompt.side_effect = [title_prompt, description_prompt]

            # Mock PR template file
            mock_pr_template = "## PR Template\n* Task ID: \n* Description: "

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=mock_pr_template)):
                    # Prepare PR prompt data
                    result = prepare_pr_prompt_data([], [], project_root="/fake/path")

                    # Verify the result
                    assert isinstance(result, PRPromptData)
                    assert "Title: " in result.title
                    assert "Description: " in result.description
                    assert mock_pr_template in result.title
                    assert mock_pr_template in result.description
                    return result

    def test_prepare_pr_prompt_data_file_not_found(self) -> None:
        """Test preparing PR prompt data with a missing file."""
        # Mock get_prompt_model to raise FileNotFoundError
        with patch(
            "pull_request_ai_agent.ai_bot.prompts.model.get_prompt_model", side_effect=FileNotFoundError("Test error")
        ):
            # Create test data
            task_tickets = [{"id": "PROJ-123", "title": "Fix bug"}]
            commits = [{"short_hash": "abc123", "message": "Fix login bug"}]

            # Try to prepare PR prompt data
            with pytest.raises(FileNotFoundError):
                prepare_pr_prompt_data(task_tickets, commits)
