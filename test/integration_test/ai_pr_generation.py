"""
Integration tests for AI PR generation functionality.

These tests verify that the AI can properly generate PR body content
based on task tickets and git commits according to the PR template.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pull_request_ai_agent.ai_bot import AiModuleClient
from pull_request_ai_agent.bot import PullRequestAIAgent
from pull_request_ai_agent.project_management_tool._base.model import BaseImmutableModel


class MockTicket(BaseImmutableModel):
    """Mock ticket for testing purposes."""

    def __init__(self, ticket_id, name, description, status="In Progress"):
        self.id = ticket_id
        self.name = name
        self.description = description
        self.status = status

    def serialize(self):
        """Implement required abstract method."""
        return {"id": self.id, "name": self.name, "description": self.description, "status": self.status}


class TestAIPRGeneration:
    """Integration tests for AI PR generation."""

    @pytest.fixture
    def mock_project_management_client(self):
        """Create a mock project management client."""
        client = MagicMock()

        # Define test tickets
        feature_ticket = MockTicket(
            "CU-abc123",
            "Add AI-powered PR generation",
            "Implement a feature that uses AI to generate PR descriptions based on commit messages and task details.",
        )

        bug_ticket = MockTicket(
            "CU-def456",
            "Fix parsing bug in ticket extraction",
            "The ticket ID extraction from branch names fails when using certain formats.",
        )

        # Configure the mock client to return different tickets based on the ID
        def get_ticket(ticket_id):
            if ticket_id == "abc123":
                return feature_ticket
            elif ticket_id == "def456":
                return bug_ticket
            return None

        client.get_ticket.side_effect = get_ticket
        return client

    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client."""
        client = MagicMock()

        # Configure the mock to return a predefined response
        feature_response = """
TITLE: Add AI-powered PR generation

BODY:
## _Target_

* ### Task summary:

    Implement AI-powered PR generation feature.

* ### Task tickets:

    * Task ID: CU-abc123
    * Relative task IDs: N/A

* ### Key point change:

    - Added AI integration for PR generation
    - Implemented prompt formatting for consistent output
    - Added template-based PR formatting

## _Effecting Scope_

* AI module
* PR generation workflow

## _Description_

* Added integration with OpenAI API for PR content generation
* Implemented structured prompt creation from commit messages
* Added parsing logic to format AI responses according to PR template
* Created robust error handling for API failures
"""

        bug_response = """
TITLE: Fix parsing bug in ticket extraction

BODY:
## _Target_

* ### Task summary:

    Fix a bug in the ticket ID extraction from branch names.

* ### Task tickets:

    * Task ID: CU-def456
    * Relative task IDs: N/A

* ### Key point change:

    - Updated regex pattern for ticket ID extraction
    - Added support for more branch naming formats
    - Improved error handling for invalid branch names

## _Effecting Scope_

* Branch handling
* Ticket extraction functionality

## _Description_

* Fixed regex pattern to correctly extract ticket IDs from branch names
* Added support for branch names with multiple format styles
* Improved error handling for cases when no ticket ID is found
* Added validation to prevent false positive ticket ID matches
"""

        # Default response that follows the template format
        default_response = """
TITLE: Default Test PR

BODY:
## _Target_

* ### Task summary:

    Test feature implementation.

* ### Task tickets:

    * Task ID: CU-test123
    * Relative task IDs: N/A

* ### Key point change:

    - Added test functionality
    - Implemented test feature

## _Effecting Scope_

* Test module

## _Description_

* Implemented test feature with proper validation
* Added test coverage
"""

        def get_content(prompt):
            # Handle PRPromptData object instead of string
            prompt_text = prompt.description if hasattr(prompt, "description") else str(prompt)

            if "Add AI-powered PR generation" in prompt_text or "CU-abc123" in prompt_text:
                return feature_response
            elif "Fix parsing bug" in prompt_text or "CU-def456" in prompt_text:
                return bug_response
            elif "Test Feature" in prompt_text or "CU-test123" in prompt_text:
                return default_response
            return default_response

        client.get_content.side_effect = get_content
        return client

    @pytest.fixture
    def mock_git_handler(self):
        """Create a mock git handler."""
        handler = MagicMock()

        # Create mock commit data
        feature_commits = [
            {
                "hash": "abcdef123456789",
                "short_hash": "abcdef1",
                "author": {"name": "John Doe", "email": "john.doe@example.com"},
                "message": "feat(ai): Implement AI PR generation\n\nImplemented AI client integration for generating PR descriptions.",
                "committed_date": 1621234567,
                "authored_date": 1621234567,
            },
            {
                "hash": "9876543210fedcba",
                "short_hash": "9876543",
                "author": {"name": "John Doe", "email": "john.doe@example.com"},
                "message": "feat(ai): Add prompt formatting\n\nCreated structured prompt formatting for AI based on commit messages.",
                "committed_date": 1621234667,
                "authored_date": 1621234667,
            },
        ]

        bug_commits = [
            {
                "hash": "1a2b3c4d5e6f7890",
                "short_hash": "1a2b3c4",
                "author": {"name": "Jane Smith", "email": "jane.smith@example.com"},
                "message": "fix(parser): Update regex pattern for ticket extraction\n\nFixed the regex pattern to correctly handle more branch name formats.",
                "committed_date": 1621235567,
                "authored_date": 1621235567,
            }
        ]

        def iter_commits(ref):
            if "feature" in ref:
                return feature_commits
            elif "bugfix" in ref:
                return bug_commits
            return []

        # Mock the necessary methods
        handler._get_current_branch.return_value = "feature/CU-abc123-ai-pr-generation"
        handler.repo.refs = []
        handler.repo.iter_commits.side_effect = iter_commits
        handler.repo.merge_base.return_value = [MagicMock(hexsha="base_commit_hash")]

        return handler

    @pytest.fixture
    def pr_bot(self, mock_project_management_client, mock_ai_client, mock_git_handler):
        """Create a PR bot with mock dependencies."""
        with (
            patch("pull_request_ai_agent.bot.GitHandler") as MockGitHandler,
            patch("pull_request_ai_agent.bot.GPTClient") as MockGPTClient,
        ):

            MockGitHandler.return_value = mock_git_handler
            MockGPTClient.return_value = mock_ai_client

            bot = PullRequestAIAgent(
                repo_path=".",
                base_branch="main",
                project_management_tool_type=PullRequestAIAgent.PM_TOOL_CLICKUP,
                project_management_tool_config=MagicMock(api_key="fake_api_key"),
                ai_client_type=AiModuleClient.GPT,
                ai_client_api_key="fake_api_key",
            )

            # Replace clients with mocks
            bot.project_management_client = mock_project_management_client

            return bot

    def test_feature_pr_generation(self, pr_bot, mock_git_handler):
        """Test generating a PR for a feature branch."""
        # Mock the branch and commits
        branch_name = "feature/CU-abc123-ai-pr-generation"
        mock_git_handler._get_current_branch.return_value = branch_name

        # Mock the get_branch_commits method to return feature commits
        with patch.object(pr_bot, "get_branch_commits") as mock_get_commits:
            mock_get_commits.return_value = [
                {
                    "hash": "abcdef123456789",
                    "short_hash": "abcdef1",
                    "author": {"name": "John Doe", "email": "john.doe@example.com"},
                    "message": "feat(ai): Implement AI PR generation\n\nImplemented AI client integration for generating PR descriptions.",
                    "committed_date": 1621234567,
                    "authored_date": 1621234567,
                },
                {
                    "hash": "9876543210fedcba",
                    "short_hash": "9876543",
                    "author": {"name": "John Doe", "email": "john.doe@example.com"},
                    "message": "feat(ai): Add prompt formatting\n\nCreated structured prompt formatting for AI based on commit messages.",
                    "committed_date": 1621234667,
                    "authored_date": 1621234667,
                },
            ]

            # Extract the ticket ID
            ticket_id = pr_bot.extract_ticket_id(branch_name)
            assert ticket_id == "CU-abc123"

            # Get ticket details
            ticket_details = pr_bot.get_ticket_details([ticket_id])
            assert len(ticket_details) == 1

            # Prepare AI prompt
            commits = pr_bot.get_branch_commits(branch_name)
            prompt = pr_bot.prepare_ai_prompt(commits, ticket_details)

            # Generate PR content
            ai_response = pr_bot.ai_client.get_content(prompt)
            title, body = pr_bot.parse_ai_response(ai_response)

            # Verify the title
            assert "Add AI-powered PR generation" in title

            # Verify the body contains required sections from the PR template
            assert "## _Target_" in body
            assert "Task summary:" in body
            assert "Task tickets:" in body
            assert "CU-abc123" in body
            assert "## _Effecting Scope_" in body
            assert "## _Description_" in body

            # Verify specific content related to this feature
            assert "AI-powered PR generation" in body
            assert "AI integration" in body or "AI module" in body

    def test_bugfix_pr_generation(self, pr_bot, mock_git_handler):
        """Test generating a PR for a bugfix branch."""
        # Mock the branch and commits
        branch_name = "bugfix/CU-def456-fix-ticket-extraction"
        mock_git_handler._get_current_branch.return_value = branch_name

        # Mock the get_branch_commits method to return bug fix commits
        with patch.object(pr_bot, "get_branch_commits") as mock_get_commits:
            mock_get_commits.return_value = [
                {
                    "hash": "1a2b3c4d5e6f7890",
                    "short_hash": "1a2b3c4",
                    "author": {"name": "Jane Smith", "email": "jane.smith@example.com"},
                    "message": "fix(parser): Update regex pattern for ticket extraction\n\nFixed the regex pattern to correctly handle more branch name formats.",
                    "committed_date": 1621235567,
                    "authored_date": 1621235567,
                }
            ]

            # Extract the ticket ID
            ticket_id = pr_bot.extract_ticket_id(branch_name)
            assert ticket_id == "CU-def456"

            # Get ticket details
            ticket_details = pr_bot.get_ticket_details([ticket_id])
            assert len(ticket_details) == 1

            # Prepare AI prompt
            commits = pr_bot.get_branch_commits(branch_name)
            prompt = pr_bot.prepare_ai_prompt(commits, ticket_details)

            # Generate PR content
            ai_response = pr_bot.ai_client.get_content(prompt)
            title, body = pr_bot.parse_ai_response(ai_response)

            # Verify the title
            assert "Fix parsing bug" in title

            # Verify the body contains required sections from the PR template
            assert "## _Target_" in body
            assert "Task summary:" in body
            assert "Task tickets:" in body
            assert "CU-def456" in body
            assert "## _Effecting Scope_" in body
            assert "## _Description_" in body

            # Verify specific content related to this bugfix
            assert "ticket extraction" in body.lower() or "parsing bug" in body.lower()
            assert "regex pattern" in body.lower()

    def test_pr_template_compliance(self, pr_bot):
        """Test that generated PR bodies comply with the PR template format."""
        # Get the actual PR template from the repository
        pr_template_path = Path(pr_bot.repo_path) / ".github" / "PULL_REQUEST_TEMPLATE.md"

        # Mock the file read operation
        with patch("builtins.open", create=True) as mock_open:
            # Set up the mock to return the PR template content
            mock_open.return_value.__enter__.return_value.read.return_value = """
[//]: # (The target why you modify something.)
## _Target_

[//]: # (The summary what you did or your target.)
* ### Task summary:

    N/A.

[//]: # (The task ID in ClickUp [project: https://app.clickup.com/9018752317/v/f/90183126979/90182605225] which maps this change.)
* ### Task tickets:

    * Task ID: N/A.
    * Relative task IDs: N/A.

[//]: # (The key changes like demonstration, as-is & to-be, etc. for reviewers could be faster understand what it changes)
* ### Key point change (optional):

    N/A.


[//]: # (What's the scope in project it would affect with your modify? For example, would it affect CI workflow? Or any feature usage? Please list all the items which may be affected.)
## _Effecting Scope_

* N/A.


[//]: # (The brief of major changes what your modify. Please list it.)
## _Description_

* N/A.
"""

            # Generate a PR body using a mock feature
            with patch.object(pr_bot, "get_branch_commits") as mock_get_commits:
                # Mock commits
                mock_get_commits.return_value = [
                    {
                        "hash": "abcdef123456789",
                        "short_hash": "abcdef1",
                        "message": "feat: Test feature",
                    }
                ]

                # Mock ticket
                ticket = MockTicket("CU-test123", "Test Feature", "This is a test feature")

                # Generate PR content
                prompt = pr_bot.prepare_ai_prompt(mock_get_commits.return_value, [ticket])
                ai_response = pr_bot.ai_client.get_content(prompt)
                _, body = pr_bot.parse_ai_response(ai_response)

                # Check for required sections from the template
                required_sections = [
                    r"## _Target_",
                    r"\* ### Task summary:",
                    r"\* ### Task tickets:",
                    r"## _Effecting Scope_",
                    r"## _Description_",
                ]

                for section in required_sections:
                    assert re.search(section, body), f"Missing required section: {section}"

                # Check task ID is included
                assert "CU-" in body, "Task ID not included in PR body"
