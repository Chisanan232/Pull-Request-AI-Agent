"""
Integration tests for the PR generation workflow.

These tests simulate real-world scenarios of PR generation, focusing on
the integration between git commits, task tickets, and AI-generated content.
"""

import re
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pull_request_ai_agent.ai_bot import AiModuleClient
from pull_request_ai_agent.bot import PullRequestAIAgent
from pull_request_ai_agent.project_management_tool._base.model import BaseImmutableModel


class MockTicketData(BaseImmutableModel):
    """Mock ticket data for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def serialize(self):
        """Implement required abstract method."""
        return {k: v for k, v in self.__dict__.items()}


@pytest.fixture
def mock_git_handler():
    """Create a mock git handler for PR generation tests."""
    handler = MagicMock()

    # Sample commits for different branches
    feature_commits = [
        {
            "hash": "abcdef123456",
            "short_hash": "abcdef1",
            "author": {"name": "Developer", "email": "dev@example.com"},
            "message": "feat(api): Add new endpoint for user data\n\nImplemented a new API endpoint for retrieving user data.",
            "committed_date": 1654321098,
            "authored_date": 1654321098,
        },
        {
            "hash": "fedcba654321",
            "short_hash": "fedcba6",
            "author": {"name": "Developer", "email": "dev@example.com"},
            "message": "refactor(api): Clean up error handling\n\nImproved error handling in the API endpoints.",
            "committed_date": 1654321099,
            "authored_date": 1654321099,
        },
    ]

    bug_commits = [
        {
            "hash": "123456abcdef",
            "short_hash": "123456a",
            "author": {"name": "Developer", "email": "dev@example.com"},
            "message": "fix(auth): Correct JWT validation\n\nFixed an issue with JWT token validation that caused premature token expiration.",
            "committed_date": 1654321100,
            "authored_date": 1654321100,
        }
    ]

    # Setup branch detection and commit retrieval
    handler._get_current_branch.return_value = "feature/JIRA-123-add-user-endpoint"
    handler.repo.refs = []

    def iter_commits(ref):
        if "feature" in ref or "JIRA-123" in ref:
            return feature_commits
        elif "bug" in ref or "JIRA-456" in ref:
            return bug_commits
        return []

    handler.repo.iter_commits.side_effect = iter_commits
    handler.repo.merge_base.return_value = [MagicMock(hexsha="base_commit_hash")]

    return handler


@pytest.fixture
def mock_project_management_client():
    """Create a mock project management client for PR generation tests."""
    client = MagicMock()

    # Sample ticket data
    feature_ticket = MockTicketData(
        id="JIRA-123",
        name="Add API endpoint for user data",
        description="Create a new RESTful API endpoint for retrieving user profile data with proper authentication.",
        status="In Progress",
        type="feature",
    )

    bug_ticket = MockTicketData(
        id="JIRA-456",
        name="Fix JWT token validation",
        description="The JWT tokens are expiring earlier than expected due to incorrect validation logic.",
        status="In Progress",
        type="bug",
    )

    # Configure mock to return appropriate tickets
    def get_ticket(ticket_id):
        if ticket_id == "JIRA-123" or ticket_id == "123":
            return feature_ticket
        elif ticket_id == "JIRA-456" or ticket_id == "456":
            return bug_ticket
        return None

    client.get_ticket.side_effect = get_ticket
    return client


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client for PR generation tests."""
    ai_client = MagicMock()

    # Configure the mock AI client to return appropriate responses
    def get_content(prompt):
        if "JIRA-123" in prompt or "Add API endpoint" in prompt:
            return """
TITLE: Add API endpoint for user data retrieval

Here's a suggested PR description:

```markdown
## _Target_

* ### Task summary:
    Add a new RESTful API endpoint for retrieving user profile data.

* ### Task tickets:
    * Task ID: JIRA-123
    * Relative task IDs: N/A

* ### Key point change:
    - Implemented new API route
    - Added data validation
    - Created documentation

## _Effecting Scope_
* API module
* Authentication module

## _Description_
* Created new endpoint for retrieving user profile data
* Added JWT validation to ensure proper authentication
```
"""
        elif "JIRA-456" in prompt or "Fix JWT" in prompt:
            return """
TITLE: Fix JWT token validation expiration issue

Here's a suggested PR description:

```markdown
## _Target_

* ### Task summary:
    Fix the JWT token validation logic to correct premature token expiration.

* ### Task tickets:
    * Task ID: JIRA-456
    * Relative task IDs: N/A

* ### Key point change:
    - Fixed token expiration calculation
    - Added comprehensive tests

## _Effecting Scope_
* Authentication module
* Security layer

## _Description_
* Corrected the token validation logic to properly handle expiration timestamps
* Added unit tests to verify correct expiration behavior
* Updated documentation
```
"""
        else:
            # Default response for unknown tickets
            return """
TITLE: Default PR for unknown ticket

Here's a suggested PR description:

```markdown
## _Target_

* ### Task summary:
    This is a default PR for an unknown ticket.

* ### Task tickets:
    * Task ID: UNKNOWN
    * Relative task IDs: N/A

## _Effecting Scope_
* Unknown

## _Description_
* This is a placeholder PR
```
"""
    ai_client.get_content.side_effect = get_content
    return ai_client


class TestPRGenerationWorkflow:
    """Test the entire PR generation workflow."""

    @pytest.fixture
    def pr_bot(self, mock_git_handler, mock_project_management_client, mock_ai_client):
        """Create a PR bot with mock dependencies for testing."""
        with (
            patch("pull_request_ai_agent.bot.GitHandler") as MockGitHandler,
            patch("pull_request_ai_agent.bot.GPTClient") as MockGPTClient,
        ):

            MockGitHandler.return_value = mock_git_handler
            MockGPTClient.return_value = mock_ai_client

            bot = PullRequestAIAgent(
                repo_path=".",
                base_branch="main",
                project_management_tool_type=PullRequestAIAgent.PM_TOOL_JIRA,
                project_management_tool_config=MagicMock(api_key="fake_jira_key", url="https://fake-jira.com"),
                ai_client_type=AiModuleClient.GPT,
                ai_client_api_key="fake_openai_key",
            )

            # Replace clients with mocks
            bot.project_management_client = mock_project_management_client

            return bot

    def test_feature_branch_workflow(self, pr_bot, mock_git_handler):
        """Test the PR generation workflow for a feature branch."""
        # Set up the feature branch
        branch_name = "feature/JIRA-123-add-user-endpoint"
        mock_git_handler._get_current_branch.return_value = branch_name

        # Mock PR template
        pr_template = """
## _Target_

* ### Task summary:
    N/A.

* ### Task tickets:
    * Task ID: N/A.
    * Relative task IDs: N/A.

* ### Key point change (optional):
    N/A.

## _Effecting Scope_
* N/A.

## _Description_
* N/A.
"""

        # Create sample prompt with ticket information
        sample_prompt = """
Please create a GitHub pull request title and body based on the following information:

## Ticket Details
- Ticket ID: JIRA-123
- Title: Add API endpoint for user data
- Description: Create a new RESTful API endpoint for retrieving user profile data with proper authentication.
- Status: In Progress
- Type: feature

## Commit Details
- feat(api): Add new endpoint for user data (abcdef1)

## Pull Request Template
## _Target_

* ### Task summary:
    N/A.

* ### Task tickets:
    * Task ID: N/A.
    * Relative task IDs: N/A.

* ### Key point change (optional):
    N/A.

## _Effecting Scope_
* N/A.

## _Description_
* N/A.
"""

        # Mock reading PR template
        with (
            patch("builtins.open", mock_open(read_data=pr_template)),
            patch.object(pr_bot, "prepare_ai_prompt", return_value=sample_prompt),
        ):

            # Test ticket ID extraction
            ticket_id = pr_bot.extract_ticket_id(branch_name)
            assert ticket_id == "JIRA-123"

            # Test ticket fetching
            ticket_details = pr_bot.get_ticket_details([ticket_id])
            assert len(ticket_details) == 1
            assert ticket_details[0].id == "JIRA-123"
            assert "Add API endpoint" in ticket_details[0].name

            # Mock get_branch_commits
            with patch.object(pr_bot, "get_branch_commits") as mock_get_commits:
                mock_get_commits.return_value = [
                    {
                        "hash": "abcdef123456",
                        "short_hash": "abcdef1",
                        "author": {"name": "Developer", "email": "dev@example.com"},
                        "message": "feat(api): Add new endpoint for user data",
                    }
                ]

                # Test AI prompt preparation
                prompt = pr_bot.prepare_ai_prompt(mock_get_commits.return_value, ticket_details)
                assert "JIRA-123" in prompt
                assert "Add API endpoint" in prompt

                # Test AI response and parsing
                ai_response = pr_bot.ai_client.get_content(prompt)
                assert "Add API endpoint" in ai_response

                title = pr_bot._parse_ai_response_title(ai_response)
                body = pr_bot._parse_ai_response_body(ai_response)
                assert "Add API endpoint" in title
                assert "## _Target_" in body
                assert "JIRA-123" in body

                # Verify PR content complies with template
                required_sections = [
                    r"## _Target_",
                    r"\* ### Task summary:",
                    r"\* ### Task tickets:",
                    r"## _Effecting Scope_",
                    r"## _Description_",
                ]

                for section in required_sections:
                    assert re.search(section, body), f"Missing required section: {section}"

    def test_bugfix_branch_workflow(self, pr_bot, mock_git_handler):
        """Test the PR generation workflow for a bugfix branch."""
        # Set up the bugfix branch
        branch_name = "bugfix/JIRA-456-fix-jwt-validation"
        mock_git_handler._get_current_branch.return_value = branch_name

        # Mock PR template
        pr_template = """
## _Target_

* ### Task summary:
    N/A.

* ### Task tickets:
    * Task ID: N/A.
    * Relative task IDs: N/A.

* ### Key point change (optional):
    N/A.

## _Effecting Scope_
* N/A.

## _Description_
* N/A.
"""

        # Create sample prompt with ticket information
        sample_prompt = """
Please create a GitHub pull request title and body based on the following information:

## Ticket Details
- Ticket ID: JIRA-456
- Title: Fix JWT token validation
- Description: The JWT tokens are expiring earlier than expected due to incorrect validation logic.
- Status: In Progress
- Type: bug

## Commit Details
- fix(auth): Correct JWT validation (123456a)

## Pull Request Template
## _Target_

* ### Task summary:
    N/A.

* ### Task tickets:
    * Task ID: N/A.
    * Relative task IDs: N/A.

* ### Key point change (optional):
    N/A.

## _Effecting Scope_
* N/A.

## _Description_
* N/A.
"""

        # Mock reading PR template
        with (
            patch("builtins.open", mock_open(read_data=pr_template)),
            patch.object(pr_bot, "prepare_ai_prompt", return_value=sample_prompt),
        ):

            # Test ticket ID extraction
            ticket_id = pr_bot.extract_ticket_id(branch_name)
            assert ticket_id == "JIRA-456"

            # Test ticket fetching
            ticket_details = pr_bot.get_ticket_details([ticket_id])
            assert len(ticket_details) == 1
            assert ticket_details[0].id == "JIRA-456"
            assert "Fix JWT token validation" in ticket_details[0].name

            # Mock get_branch_commits
            with patch.object(pr_bot, "get_branch_commits") as mock_get_commits:
                mock_get_commits.return_value = [
                    {
                        "hash": "123456abcdef",
                        "short_hash": "123456a",
                        "author": {"name": "Developer", "email": "dev@example.com"},
                        "message": "fix(auth): Correct JWT validation",
                    }
                ]

                # Test AI prompt preparation
                prompt = pr_bot.prepare_ai_prompt(mock_get_commits.return_value, ticket_details)
                assert "JIRA-456" in prompt
                assert "Fix JWT token validation" in prompt

                # Test AI response and parsing
                ai_response = pr_bot.ai_client.get_content(prompt)
                assert "Fix JWT token validation" in ai_response

                title = pr_bot._parse_ai_response_title(ai_response)
                body = pr_bot._parse_ai_response_body(ai_response)
                assert "Fix JWT token validation" in title
                assert "## _Target_" in body
                assert "JIRA-456" in body

                # Verify specific bugfix content
                assert "token validation" in body.lower()
                assert "expiration" in body.lower()

    def test_end_to_end_workflow(self, pr_bot, mock_git_handler):
        """Test the end-to-end PR generation workflow."""
        # Set up a feature branch
        branch_name = "feature/JIRA-123-add-user-endpoint"
        mock_git_handler._get_current_branch.return_value = branch_name

        # Mock GitHub operations
        mock_github_ops = MagicMock()
        mock_github_ops.get_pull_request_by_branch.return_value = None
        mock_github_ops.create_pull_request.return_value = MagicMock(
            number=101, html_url="https://github.com/example/repo/pull/101"
        )

        # Mock PR template
        pr_template = """
## _Target_

* ### Task summary:
    N/A.

* ### Task tickets:
    * Task ID: N/A.
    * Relative task IDs: N/A.

* ### Key point change (optional):
    N/A.

## _Effecting Scope_
* N/A.

## _Description_
* N/A.
"""

        # Create sample prompt with ticket information
        sample_prompt = """
Please create a GitHub pull request title and body based on the following information:

## Ticket Details
- Ticket ID: JIRA-123
- Title: Add API endpoint for user data
- Description: Create a new RESTful API endpoint for retrieving user profile data with proper authentication.
- Status: In Progress
- Type: feature

## Commit Details
- feat(api): Add new endpoint for user data (abcdef1)

## Pull Request Template
## _Target_

* ### Task summary:
    N/A.

* ### Task tickets:
    * Task ID: N/A.
    * Relative task IDs: N/A.

* ### Key point change (optional):
    N/A.

## _Effecting Scope_
* N/A.

## _Description_
* N/A.
"""

        # Mock reading PR template and commits
        with (
            patch("builtins.open", mock_open(read_data=pr_template)),
            patch.object(pr_bot, "get_branch_commits") as mock_get_commits,
            patch.object(pr_bot, "prepare_ai_prompt", return_value=sample_prompt),
        ):

            # Mock commits
            commits = [
                {
                    "hash": "abcdef123456",
                    "short_hash": "abcdef1",
                    "author": {"name": "Developer", "email": "dev@example.com"},
                    "message": "feat(api): Add new endpoint for user data",
                    "committed_date": 1654321098,
                    "authored_date": 1654321098,
                }
            ]
            mock_get_commits.return_value = commits

            # Test the PR generation steps
            # 1. Extract ticket ID
            ticket_id = pr_bot.extract_ticket_id(branch_name)
            assert ticket_id == "JIRA-123"

            # 2. Get ticket details
            ticket_details = pr_bot.get_ticket_details([ticket_id])
            assert len(ticket_details) == 1
            assert ticket_details[0].id == "JIRA-123"

            # 3. Prepare AI prompt
            prompt = pr_bot.prepare_ai_prompt(commits, ticket_details)
            assert "JIRA-123" in prompt
            assert "Add API endpoint" in prompt

            # 4. Get AI response
            ai_response = pr_bot.ai_client.get_content(prompt)
            assert "Add API endpoint" in ai_response

            # 5. Parse AI response
            title = pr_bot._parse_ai_response_title(ai_response)
            body = pr_bot._parse_ai_response_body(ai_response)
            assert "Add API endpoint" in title
            assert "## _Target_" in body
            assert "JIRA-123" in body

            # 6. Test GitHub PR creation (mocked)
            with patch.object(pr_bot, "github_operations", mock_github_ops):
                pr_info = pr_bot.create_pull_request(title, body)

                # Verify GitHub PR creation was called
                mock_github_ops.create_pull_request.assert_called_once()
                assert pr_info.number == 101
                assert pr_info.html_url == "https://github.com/example/repo/pull/101"
