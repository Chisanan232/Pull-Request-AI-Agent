"""
Unit tests for the CreatePrAIBot class.
"""

import json
import os
from typing import Dict, List, Optional, Any
from unittest.mock import patch, MagicMock, PropertyMock, call

import pytest
import git
from github.PullRequest import PullRequest

from create_pr_bot.bot import CreatePrAIBot, AiModuleClient
from create_pr_bot.git_hdlr import GitHandler, GitCodeConflictError
from create_pr_bot.github_opt import GitHubOperations
from create_pr_bot.ai_bot.gpt.client import GPTClient


class SpyBot(CreatePrAIBot):
    def __init__(
            self,
            repo_path: str = ".",
            base_branch: str = "main",
            github_token: Optional[str] = None,
            github_repo: Optional[str] = None,
            project_management_client: Optional[Any] = None,
            ai_client_type: AiModuleClient = AiModuleClient,
            ai_client_api_key: Optional[str] = None,
    ):
        pass


class TestCreatePrAIBot:
    """Test cases for CreatePrAIBot class."""

    @pytest.fixture
    def mock_git_handler(self):
        """Create a mock GitHandler for testing."""
        mock = MagicMock(spec=GitHandler)

        # Setup active branch
        mock._get_current_branch.return_value = "feature-branch"

        # Setup commit details
        mock_commit = {
            "hash": "1234567890abcdef1234567890abcdef12345678",
            "short_hash": "1234567",
            "author": {"name": "Test Author", "email": "test@example.com"},
            "committer": {"name": "Test Author", "email": "test@example.com"},
            "message": "Test commit message",
            "committed_date": 1620000000,
            "authored_date": 1620000000,
        }
        mock.get_branch_head_commit_details.return_value = mock_commit

        # Setup repo
        mock_repo = MagicMock()
        type(mock).repo = PropertyMock(return_value=mock_repo)

        # Setup is_branch_outdated
        mock.is_branch_outdated.return_value = False

        return mock

    @pytest.fixture
    def mock_github_operations(self):
        """Create a mock GitHubOperations for testing."""
        mock = MagicMock(spec=GitHubOperations)

        # Setup get_pull_request_by_branch
        mock.get_pull_request_by_branch.return_value = None

        # Setup create_pull_request
        mock_pr = MagicMock(spec=PullRequest)
        mock_pr.number = 123
        mock_pr.html_url = "https://github.com/owner/repo/pull/123"
        mock.create_pull_request.return_value = mock_pr

        return mock

    @pytest.fixture
    def mock_project_management_client(self):
        """Create a mock project management client for testing."""
        mock = MagicMock()

        # Setup get_ticket
        mock_ticket = MagicMock()
        mock_ticket.id = "PROJ-123"
        mock_ticket.title = "Test ticket"
        mock_ticket.description = "Test ticket description"
        mock.get_ticket.return_value = mock_ticket

        return mock

    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client for testing."""
        mock = MagicMock(spec=GPTClient)

        # Setup get_content
        mock.get_content.return_value = """
        TITLE: Test PR title

        BODY:
        This is a test PR description.
        It includes multiple lines.
        """

        return mock

    @pytest.fixture
    def bot(self, mock_git_handler, mock_github_operations, mock_project_management_client, mock_ai_client):
        """Create a CreatePrAIBot instance with mocked dependencies."""
        with patch("create_pr_bot.bot.GitHandler", return_value=mock_git_handler), \
                patch("create_pr_bot.bot.GitHubOperations", return_value=mock_github_operations), \
                patch.object(CreatePrAIBot, "_initialize_ai_client", return_value=mock_ai_client):

            bot = CreatePrAIBot(
                repo_path="/mock/repo",
                base_branch="main",
                github_token="mock-token",
                github_repo="owner/repo",
                project_management_client=mock_project_management_client,
                ai_client_type="gpt",
                ai_client_api_key="mock-api-key"
            )

            return bot

    def test_initialize_ai_client_gpt(self):
        """Test initialization of GPT AI client."""
        with patch("create_pr_bot.bot.GPTClient") as mock_gpt_client:
            SpyBot()._initialize_ai_client(AiModuleClient.GPT, "mock-api-key")
            mock_gpt_client.assert_called_once_with(api_key="mock-api-key")

    def test_initialize_ai_client_claude(self):
        """Test initialization of Claude AI client."""
        with patch("create_pr_bot.bot.ClaudeClient") as mock_claude_client:
            SpyBot()._initialize_ai_client(AiModuleClient.CLAUDE, "mock-api-key")
            mock_claude_client.assert_called_once_with(api_key="mock-api-key")

    def test_initialize_ai_client_gemini(self):
        """Test initialization of Gemini AI client."""
        with patch("create_pr_bot.bot.GeminiClient") as mock_gemini_client:
            SpyBot()._initialize_ai_client(AiModuleClient.GEMINI, "mock-api-key")
            mock_gemini_client.assert_called_once_with(api_key="mock-api-key")

    def test_initialize_ai_client_unsupported(self):
        """Test initialization with unsupported AI client type."""
        with pytest.raises(ValueError, match="Unsupported AI client type"):
            SpyBot()._initialize_ai_client("unsupported", "mock-api-key")

    def test_get_current_branch(self, bot, mock_git_handler):
        """Test _get_current_branch method."""
        branch = bot._get_current_branch()
        mock_git_handler._get_current_branch.assert_called_once()
        assert branch == "feature-branch"

    def test_is_branch_outdated(self, bot, mock_git_handler):
        """Test is_branch_outdated method."""
        result = bot.is_branch_outdated("test-branch")
        mock_git_handler.is_branch_outdated.assert_called_once_with("test-branch", "main")
        assert not result

    def test_is_branch_outdated_current_branch(self, bot, mock_git_handler):
        """Test is_branch_outdated method with current branch."""
        result = bot.is_branch_outdated()
        mock_git_handler.is_branch_outdated.assert_called_once_with("feature-branch", "main")
        assert not result

    def test_is_pr_already_opened(self, bot, mock_github_operations):
        """Test is_pr_already_opened method."""
        result = bot.is_pr_already_opened("test-branch")
        mock_github_operations.get_pull_request_by_branch.assert_called_once_with("test-branch")
        assert not result

    def test_is_pr_already_opened_exists(self, bot, mock_github_operations):
        """Test is_pr_already_opened method when PR exists."""
        mock_pr = MagicMock(spec=PullRequest)
        mock_github_operations.get_pull_request_by_branch.return_value = mock_pr

        result = bot.is_pr_already_opened("test-branch")
        assert result

    def test_is_pr_already_opened_no_github_ops(self, bot):
        """Test is_pr_already_opened method with no GitHub operations."""
        bot.github_operations = None
        result = bot.is_pr_already_opened("test-branch")
        assert not result

    def test_is_pr_already_opened_exception(self, bot, mock_github_operations):
        """Test is_pr_already_opened method with exception."""
        mock_github_operations.get_pull_request_by_branch.side_effect = Exception("Test error")

        result = bot.is_pr_already_opened("test-branch")
        assert not result

    def test_fetch_and_merge_latest_from_base_branch(self, bot, mock_git_handler):
        """Test fetch_and_merge_latest_from_base_branch method."""
        mock_git_handler.fetch_and_merge_remote_branch.return_value = True

        result = bot.fetch_and_merge_latest_from_base_branch("test-branch")
        mock_git_handler.fetch_and_merge_remote_branch.assert_called_once_with("test-branch")
        assert result

    def test_fetch_and_merge_latest_from_base_branch_conflict(self, bot, mock_git_handler):
        """Test fetch_and_merge_latest_from_base_branch method with conflict."""
        mock_git_handler.fetch_and_merge_remote_branch.side_effect = GitCodeConflictError("Test conflict")

        with pytest.raises(GitCodeConflictError):
            bot.fetch_and_merge_latest_from_base_branch("test-branch")

    def test_get_branch_commits(self, bot, mock_git_handler):
        """Test get_branch_commits method."""
        # Setup mock repo and commits
        mock_repo = mock_git_handler.repo

        # Create mock commit objects
        mock_commit1 = MagicMock()
        mock_commit1.hexsha = "abcdef1"
        mock_commit1.author.name = "Author 1"
        mock_commit1.author.email = "author1@example.com"
        mock_commit1.committer.name = "Committer 1"
        mock_commit1.committer.email = "committer1@example.com"
        mock_commit1.message = "Commit message 1"
        mock_commit1.committed_date = 1620000001
        mock_commit1.authored_date = 1620000001

        mock_commit2 = MagicMock()
        mock_commit2.hexsha = "abcdef2"
        mock_commit2.author.name = "Author 2"
        mock_commit2.author.email = "author2@example.com"
        mock_commit2.committer.name = "Committer 2"
        mock_commit2.committer.email = "committer2@example.com"
        mock_commit2.message = "Commit message 2"
        mock_commit2.committed_date = 1620000002
        mock_commit2.authored_date = 1620000002

        # Mock base commit
        mock_base_commit = MagicMock()
        mock_base_commit.hexsha = "base123"

        # Setup merge_base
        mock_repo.merge_base.return_value = [mock_base_commit]

        # Setup iter_commits to return our mock commits
        mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2, mock_base_commit]

        # Call get_branch_commits
        commits = bot.get_branch_commits("test-branch")

        # Verify calls
        mock_repo.merge_base.assert_called_once_with("refs/heads/test-branch", "refs/heads/main")
        mock_repo.iter_commits.assert_called_once_with("test-branch")

        # Verify returned commits (should exclude base commit)
        assert len(commits) == 2
        assert commits[0]["hash"] == "abcdef1"
        assert commits[1]["hash"] == "abcdef2"

    def test_get_branch_commits_no_commits(self, bot, mock_git_handler):
        """Test get_branch_commits method with no commits."""
        mock_repo = mock_git_handler.repo
        mock_repo.merge_base.return_value = []

        commits = bot.get_branch_commits("test-branch")
        assert commits == []

    def test_extract_ticket_ids(self, bot):
        """Test extract_ticket_ids method."""
        # Create test commits with various ticket patterns
        commits = [
            {"message": "Fix bug #123"},
            {"message": "Implement feature PROJ-456"},
            {"message": "Update docs CU-abc123"},
            {"message": "Refactor code Task-789"},
            {"message": "Non-ticket commit"},
        ]

        ticket_ids = bot.extract_ticket_ids(commits)

        # Verify extracted ticket IDs
        assert sorted(ticket_ids) == sorted(["123", "PROJ-456", "abc123", "789"])

    def test_get_ticket_details(self, bot, mock_project_management_client):
        """Test get_ticket_details method."""
        ticket_ids = ["PROJ-123", "PROJ-456"]

        ticket_details = bot.get_ticket_details(ticket_ids)

        # Verify get_ticket was called for each ID
        mock_project_management_client.get_ticket.assert_has_calls([
            call("PROJ-123"),
            call("PROJ-456")
        ])

        # Verify returned ticket details
        assert len(ticket_details) == 2
        assert all(ticket.id == "PROJ-123" for ticket in ticket_details)

    def test_get_ticket_details_exception(self, bot, mock_project_management_client):
        """Test get_ticket_details method with exception."""
        mock_project_management_client.get_ticket.side_effect = [
            MagicMock(id="PROJ-123"),
            Exception("Test error")
        ]

        ticket_details = bot.get_ticket_details(["PROJ-123", "PROJ-456"])

        # Should only have one successful ticket detail
        assert len(ticket_details) == 1
        assert ticket_details[0].id == "PROJ-123"

    def test_get_ticket_details_no_client(self, bot):
        """Test get_ticket_details method with no project management client."""
        bot.project_management_client = None

        ticket_details = bot.get_ticket_details(["PROJ-123"])

        # Should return empty list
        assert ticket_details == []

    def test_prepare_ai_prompt(self, bot):
        """Test prepare_ai_prompt method."""
        # Setup test data
        commits = [
            {
                "hash": "abcdef1",
                "short_hash": "abcdef1",
                "message": "Fix bug in login flow",
                "author": {"name": "Test Author", "email": "test@example.com"},
            },
            {
                "hash": "abcdef2",
                "short_hash": "abcdef2",
                "message": "Add unit tests",
                "author": {"name": "Test Author", "email": "test@example.com"},
            }
        ]

        # Create mock tickets
        ticket1 = MagicMock()
        ticket1.id = "PROJ-123"
        ticket1.title = "Fix login bug"
        ticket1.description = "There's a bug in the login flow"

        ticket2 = MagicMock()
        ticket2.id = "PROJ-456"
        ticket2.title = "Add tests"
        ticket2.description = "Need to add tests for the login flow"

        ticket_details = [ticket1, ticket2]

        # Call prepare_ai_prompt
        prompt = bot.prepare_ai_prompt(commits, ticket_details)

        # Verify prompt content
        assert "## Commits" in prompt
        assert "abcdef1 - Fix bug in login flow" in prompt
        assert "abcdef2 - Add unit tests" in prompt
        assert "## Related Tickets" in prompt
        assert "PROJ-123: Fix login bug" in prompt
        assert "PROJ-456: Add tests" in prompt
        assert "## Instructions" in prompt
        assert "TITLE:" in prompt
        assert "BODY:" in prompt

    def test_prepare_ai_prompt_no_tickets(self, bot):
        """Test prepare_ai_prompt method with no tickets."""
        # Setup test data
        commits = [
            {
                "hash": "abcdef1",
                "short_hash": "abcdef1",
                "message": "Fix bug in login flow",
                "author": {"name": "Test Author", "email": "test@example.com"},
            }
        ]

        # Call prepare_ai_prompt
        prompt = bot.prepare_ai_prompt(commits, [])

        # Verify prompt content
        assert "## Commits" in prompt
        assert "abcdef1 - Fix bug in login flow" in prompt
        assert "## Related Tickets" not in prompt
        assert "## Instructions" in prompt

    def test_parse_ai_response(self, bot):
        """Test parse_ai_response method."""
        # Test with well-formatted response
        response = """
        TITLE: This is the PR title
        
        BODY:
        This is the PR body.
        It spans multiple lines.
        """

        title, body = bot.parse_ai_response(response)

        assert title == "This is the PR title"
        assert "This is the PR body." in body
        assert "It spans multiple lines." in body

    def test_parse_ai_response_no_title(self, bot):
        """Test parse_ai_response method with no title."""
        response = """
        This is just some text without any formatting.
        """

        title, body = bot.parse_ai_response(response)

        assert title == "Automated Pull Request"
        assert "This is just some text without any formatting." in body

    def test_parse_ai_response_no_body(self, bot):
        """Test parse_ai_response method with no body."""
        response = """
        TITLE: Just a title
        """

        title, body = bot.parse_ai_response(response)

        assert title == "Just a title"
        assert body == response

    def test_create_pull_request(self, bot, mock_github_operations):
        """Test create_pull_request method."""
        pr = bot.create_pull_request(
            title="Test PR",
            body="Test PR description",
            branch_name="feature-branch"
        )

        # Verify create_pull_request was called
        mock_github_operations.create_pull_request.assert_called_once_with(
            title="Test PR",
            body="Test PR description",
            base_branch="main",
            head_branch="feature-branch"
        )

        # Verify returned PR
        assert pr.number == 123
        assert pr.html_url == "https://github.com/owner/repo/pull/123"

    def test_create_pull_request_no_github_ops(self, bot):
        """Test create_pull_request method with no GitHub operations."""
        bot.github_operations = None

        pr = bot.create_pull_request(
            title="Test PR",
            body="Test PR description"
        )

        # Should return None
        assert pr is None

    def test_create_pull_request_exception(self, bot, mock_github_operations):
        """Test create_pull_request method with exception."""
        mock_github_operations.create_pull_request.side_effect = Exception("Test error")

        pr = bot.create_pull_request(
            title="Test PR",
            body="Test PR description"
        )

        # Should return None
        assert pr is None

    def test_run_outdated_pr_exists(self, bot):
        """Test run method when branch is outdated and PR exists."""
        # Mock is_branch_outdated and is_pr_already_opened
        with patch.object(bot, "is_branch_outdated", return_value=True), \
                patch.object(bot, "is_pr_already_opened", return_value=True):

            # Call run
            result = bot.run()

            # Verify no PR was created
            assert result is None

    def test_run_outdated_no_pr(self, bot, mock_git_handler, mock_ai_client, mock_github_operations):
        """Test run method when branch is outdated and no PR exists."""
        # Mock methods
        with patch.object(bot, "is_branch_outdated", return_value=True), \
                patch.object(bot, "is_pr_already_opened", return_value=False), \
                patch.object(bot, "fetch_and_merge_latest_from_base_branch", return_value=True), \
                patch.object(bot, "get_branch_commits", return_value=[{"message": "Test commit"}]), \
                patch.object(bot, "extract_ticket_ids", return_value=["PROJ-123"]), \
                patch.object(bot, "get_ticket_details", return_value=[MagicMock()]), \
                patch.object(bot, "prepare_ai_prompt", return_value="Test prompt"), \
                patch.object(bot, "parse_ai_response", return_value=("Test title", "Test body")):

            # Call run
            result = bot.run()

            # Verify PR was created
            assert result is not None
            mock_github_operations.create_pull_request.assert_called_once()

    def test_run_up_to_date_no_pr(self, bot, mock_github_operations):
        """Test run method when branch is up to date and no PR exists."""
        # Mock methods
        with patch.object(bot, "is_branch_outdated", return_value=False), \
                patch.object(bot, "is_pr_already_opened", return_value=False), \
                patch.object(bot, "get_branch_commits", return_value=[{"message": "Test commit"}]), \
                patch.object(bot, "extract_ticket_ids", return_value=["PROJ-123"]), \
                patch.object(bot, "get_ticket_details", return_value=[MagicMock()]), \
                patch.object(bot, "prepare_ai_prompt", return_value="Test prompt"), \
                patch.object(bot, "parse_ai_response", return_value=("Test title", "Test body")):

            # Call run
            result = bot.run()

            # Verify PR was created
            assert result is not None
            mock_github_operations.create_pull_request.assert_called_once()

    def test_run_merge_conflict(self, bot):
        """Test run method with merge conflict."""
        # Mock methods
        with patch.object(bot, "is_branch_outdated", return_value=True), \
                patch.object(bot, "is_pr_already_opened", return_value=False), \
                patch.object(bot, "fetch_and_merge_latest_from_base_branch", side_effect=GitCodeConflictError("Test conflict")):

            # Call run
            result = bot.run()

            # Verify no PR was created
            assert result is None

    def test_run_no_commits(self, bot):
        """Test run method with no commits."""
        # Mock methods
        with patch.object(bot, "is_branch_outdated", return_value=False), \
                patch.object(bot, "is_pr_already_opened", return_value=False), \
                patch.object(bot, "get_branch_commits", return_value=[]):

            # Call run
            result = bot.run()

            # Verify no PR was created
            assert result is None

    def test_run_ai_failure(self, bot, mock_ai_client, mock_github_operations):
        """Test run method with AI failure."""
        # Mock AI client to raise exception
        mock_ai_client.get_content.side_effect = Exception("AI error")

        # Mock methods
        with patch.object(bot, "is_branch_outdated", return_value=False), \
                patch.object(bot, "is_pr_already_opened", return_value=False), \
                patch.object(bot, "get_branch_commits", return_value=[{"message": "Test commit"}]), \
                patch.object(bot, "extract_ticket_ids", return_value=[]), \
                patch.object(bot, "get_ticket_details", return_value=[]), \
                patch.object(bot, "prepare_ai_prompt", return_value="Test prompt"):

            # Call run
            result = bot.run()

            # Verify PR was created with fallback content
            assert result is not None
            mock_github_operations.create_pull_request.assert_called_once()
            title, body, branch = mock_github_operations.create_pull_request.call_args[1]["title"], \
                mock_github_operations.create_pull_request.call_args[1]["body"], \
                mock_github_operations.create_pull_request.call_args[1]["head_branch"]
            assert title == f"Update {branch}"
            assert body == "Automated pull request."
