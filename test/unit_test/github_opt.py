"""Unit tests for GitHubOperations class."""

import unittest
from unittest.mock import MagicMock, patch

from github import GithubException
from github.PullRequest import PullRequest

from pull_request_ai_agent.github_opt import GitHubOperations


class TestGitHubOperations(unittest.TestCase):
    """Test cases for GitHubOperations class."""

    def setUp(self):
        """Set up test fixtures."""
        self.patcher = patch("pull_request_ai_agent.github_opt.Github")
        self.mock_github = self.patcher.start()
        self.mock_repo = MagicMock()
        self.mock_github.return_value.get_repo.return_value = self.mock_repo

        self.github_ops = GitHubOperations("fake_token", "owner/repo")

    def tearDown(self):
        """Tear down test fixtures."""
        self.patcher.stop()

    def test_init(self):
        """Test initialization of GitHubOperations."""
        self.mock_github.assert_called_once_with("fake_token")
        self.mock_github.return_value.get_repo.assert_called_once_with("owner/repo")
        self.assertEqual(self.github_ops.repo_name, "owner/repo")
        self.assertEqual(self.github_ops.repo, self.mock_repo)

    def test_get_pull_requests(self):
        """Test _get_pull_requests method."""
        # Mock the return value
        mock_pr1 = MagicMock(spec=PullRequest)
        mock_pr2 = MagicMock(spec=PullRequest)
        mock_prs = [mock_pr1, mock_pr2]

        # Set up the mock to return a list that acts like a PaginatedList
        self.mock_repo.get_pulls.return_value = mock_prs

        # Call the method
        result = self.github_ops._get_pull_requests()

        # Assertions
        self.mock_repo.get_pulls.assert_called_once_with(state="open")
        self.assertEqual(result, mock_prs)

    def test_get_pull_requests_exception(self):
        """Test _get_pull_requests method with exception."""
        # Set up the mock to raise an exception
        self.mock_repo.get_pulls.side_effect = GithubException(status=404, data={"message": "Not Found"})

        # Call the method and verify exception
        with self.assertRaises(GithubException) as context:
            self.github_ops._get_pull_requests()

        self.assertEqual(context.exception.status, 404)
        self.assertIn("Failed to get pull requests", str(context.exception))

    def test_get_pull_request_by_branch(self):
        """Test get_pull_request_by_branch method."""
        # Mock PRs
        mock_pr1 = MagicMock(spec=PullRequest)
        mock_pr1.head.ref = "feature-branch"

        mock_pr2 = MagicMock(spec=PullRequest)
        mock_pr2.head.ref = "another-branch"

        # Set up the _get_pull_requests method
        with patch.object(self.github_ops, "_get_pull_requests", return_value=[mock_pr1, mock_pr2]) as mock_get_prs:
            # Call the method
            result = self.github_ops.get_pull_request_by_branch("feature-branch")

            # Assertions
            mock_get_prs.assert_called_once()
            self.assertEqual(result, mock_pr1)

            # Test with non-existent branch
            result = self.github_ops.get_pull_request_by_branch("non-existent")
            self.assertIsNone(result)

    def test_get_pull_request_by_branch_exception(self):
        """Test get_pull_request_by_branch method with exception."""
        # Set up the mock to raise an exception
        with patch.object(
            self.github_ops,
            "_get_pull_requests",
            side_effect=GithubException(status=401, data={"message": "Unauthorized"}),
        ):
            # Call the method and verify exception
            with self.assertRaises(GithubException) as context:
                self.github_ops.get_pull_request_by_branch("feature-branch")

            self.assertEqual(context.exception.status, 401)
            self.assertIn("Failed to find PR for branch", str(context.exception))

    def test_create_pull_request(self):
        """Test create_pull_request method."""
        # Mock the return value
        mock_pr = MagicMock(spec=PullRequest)
        self.mock_repo.create_pull.return_value = mock_pr

        # Call the method
        result = self.github_ops.create_pull_request(
            title="Test PR", body="Description", base_branch="main", head_branch="feature", draft=True
        )

        # Assertions
        self.mock_repo.create_pull.assert_called_once_with(
            title="Test PR", body="Description", base="main", head="feature", draft=True
        )
        self.assertEqual(result, mock_pr)

    def test_create_pull_request_exception(self):
        """Test create_pull_request method with exception."""
        # Set up the mock to raise an exception
        self.mock_repo.create_pull.side_effect = GithubException(status=422, data={"message": "Validation Failed"})

        # Call the method and verify exception
        with self.assertRaises(GithubException) as context:
            self.github_ops.create_pull_request(
                title="Test PR", body="Description", base_branch="main", head_branch="feature"
            )

        self.assertEqual(context.exception.status, 422)
        self.assertIn("Failed to create PR", str(context.exception))

    def test_add_labels_to_pull_request(self):
        """Test add_labels_to_pull_request method with PR object."""
        # Mock PR and files
        mock_pr = MagicMock(spec=PullRequest)

        # Mock files in PR
        mock_file1 = MagicMock()
        mock_file1.filename = "src/main.py"

        mock_file2 = MagicMock()
        mock_file2.filename = "docs/README.md"

        mock_pr.get_files.return_value = [mock_file1, mock_file2]

        # Labels config
        labels_config = {"*.py": ["python", "code"], "docs/*": ["documentation"]}

        # Call the method
        result = self.github_ops.add_labels_to_pull_request(mock_pr, labels_config)

        # Assertions
        mock_pr.add_to_labels.assert_called_once()
        self.assertCountEqual(result, ["python", "code", "documentation"])

    def test_add_labels_to_pull_request_with_pr_number(self):
        """Test add_labels_to_pull_request method with PR number."""
        # Mock PR and files
        mock_pr = MagicMock(spec=PullRequest)

        # Mock files in PR
        mock_file = MagicMock()
        mock_file.filename = "src/main.py"

        mock_pr.get_files.return_value = [mock_file]
        self.mock_repo.get_pull.return_value = mock_pr

        # Labels config
        labels_config = {"*.py": ["python"]}

        # Call the method
        result = self.github_ops.add_labels_to_pull_request(123, labels_config)

        # Assertions
        self.mock_repo.get_pull.assert_called_once_with(123)
        mock_pr.add_to_labels.assert_called_once_with("python")
        self.assertEqual(result, ["python"])

    def test_add_labels_to_pull_request_exception(self):
        """Test add_labels_to_pull_request method with exception."""
        # Mock PR
        mock_pr = MagicMock(spec=PullRequest)

        # Set up the mock to raise an exception
        self.mock_repo.get_pull.side_effect = GithubException(status=404, data={"message": "Not Found"})

        # Labels config
        labels_config = {"*.py": ["python"]}

        # Call the method and verify exception
        with self.assertRaises(GithubException) as context:
            self.github_ops.add_labels_to_pull_request(123, labels_config)

        self.assertEqual(context.exception.status, 404)
        self.assertIn("Failed to add labels to PR", str(context.exception))
