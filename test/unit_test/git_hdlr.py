"""
Unit tests for the GitHandler class.
"""
import os
import pytest
from unittest.mock import Mock, patch, PropertyMock, MagicMock
from datetime import datetime
import git
from git.exc import GitCommandError

from create_pr_bot.git_hdlr import GitHandler, GitCodeConflictError


class TestGitHandler:
    """Test cases for GitHandler class."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock git repo for testing."""
        mock_repo = Mock(spec=git.Repo)

        # Setup active branch
        mock_active_branch = Mock()
        mock_active_branch.name = "feature-branch"
        mock_repo.active_branch = mock_active_branch

        # Setup heads
        mock_branch = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "1234567890abcdef1234567890abcdef12345678"
        mock_commit.message = "Test commit message\n"
        mock_author = Mock()
        mock_author.name = "Test Author"
        mock_author.email = "test@example.com"
        mock_commit.author = mock_author
        mock_commit.committer = mock_author
        mock_commit.committed_date = 1620000000
        mock_commit.authored_date = 1620000000
        mock_branch.commit = mock_commit
        mock_branch.name = "feature-branch"

        mock_base_branch_commit = Mock()
        mock_base_branch_commit.commit = mock_commit
        mock_base_branch_commit.name = "main"

        mock_heads = []
        mock_heads.append(mock_branch)
        mock_heads.append(mock_base_branch_commit)

        type(mock_repo).heads = PropertyMock(return_value=mock_heads)

        # Setup remotes
        mock_remote = Mock()
        mock_fetch = Mock()
        mock_remote.fetch = mock_fetch

        mock_remotes = {"origin": mock_remote}
        type(mock_repo).remotes = PropertyMock(return_value=mock_remotes)

        # Setup refs
        mock_ref = Mock()
        mock_ref.commit = mock_commit

        mock_refs = {"origin/main": mock_ref, "origin/feature-branch": mock_ref}
        type(mock_repo).refs = PropertyMock(return_value=mock_refs)

        # Setup git
        mock_git = Mock()
        mock_repo.git = mock_git

        # Setup merge_base
        mock_repo.merge_base = Mock(return_value=[mock_commit])

        return mock_repo

    @pytest.fixture
    def git_handler(self, mock_repo):
        """Create a GitHandler instance with a mock repo."""
        with patch("create_pr_bot.git_hdlr.git.Repo", return_value=mock_repo):
            handler = GitHandler("/mock/repo/path")
            return handler

    def test_init(self, mock_repo):
        """Test GitHandler initialization."""
        with patch("git.Repo", return_value=mock_repo) as mock_git_repo:
            handler = GitHandler("/path/to/repo")
            mock_git_repo.assert_called_once_with("/path/to/repo")
            assert handler.repo == mock_repo

    def test_get_current_branch(self, git_handler, mock_repo):
        """Test _get_current_branch method."""
        branch_name = git_handler._get_current_branch()
        assert branch_name == "feature-branch"

    def test_get_branch_head_commit_details_current_branch(self, git_handler):
        """Test get_branch_head_commit_details with current branch."""
        commit_details = git_handler.get_branch_head_commit_details()

        assert commit_details["hash"] == "1234567890abcdef1234567890abcdef12345678"
        assert commit_details["short_hash"] == "1234567"
        assert commit_details["message"] == "Test commit message"
        assert commit_details["author"]["name"] == "Test Author"
        assert commit_details["author"]["email"] == "test@example.com"

    def test_get_branch_head_commit_details_specific_branch(self, git_handler):
        """Test get_branch_head_commit_details with a specific branch."""
        commit_details = git_handler.get_branch_head_commit_details("main")

        assert commit_details["hash"] == "1234567890abcdef1234567890abcdef12345678"
        assert commit_details["author"]["name"] == "Test Author"

    def test_get_branch_head_commit_details_nonexistent_branch(self, git_handler):
        """Test get_branch_head_commit_details with a nonexistent branch."""
        with pytest.raises(ValueError, match="Branch 'nonexistent-branch' not found"):
            git_handler.get_branch_head_commit_details("nonexistent-branch")

    def test_get_remote_branch_head_commit_details(self, git_handler):
        """Test get_remote_branch_head_commit_details."""
        commit_details = git_handler.get_remote_branch_head_commit_details("main")

        assert commit_details["hash"] == "1234567890abcdef1234567890abcdef12345678"
        assert commit_details["short_hash"] == "1234567"
        assert commit_details["author"]["name"] == "Test Author"
        assert commit_details["message"] == "Test commit message"

    def test_get_remote_branch_head_commit_details_nonexistent_remote(self, git_handler, mock_repo):
        """Test get_remote_branch_head_commit_details with nonexistent remote."""
        type(mock_repo).remotes = PropertyMock(return_value={})

        with pytest.raises(ValueError, match="Remote 'origin' not found"):
            git_handler.get_remote_branch_head_commit_details("main")

    def test_get_remote_branch_head_commit_details_nonexistent_branch(self, git_handler, mock_repo):
        """Test get_remote_branch_head_commit_details with nonexistent branch."""
        type(mock_repo).refs = PropertyMock(return_value={})

        with pytest.raises(ValueError, match="Remote branch 'origin/main' not found"):
            git_handler.get_remote_branch_head_commit_details("main")

    def test_is_branch_outdated_not_outdated(self, git_handler, mock_repo):
        """Test is_branch_outdated when branch is not outdated."""
        # Mock merge_base to return a commit with a different hash than the local commit
        mock_base_commit = Mock()
        mock_base_commit.hexsha = "0000000000000000000000000000000000000000"
        mock_repo.merge_base.return_value = [mock_base_commit]

        assert not git_handler.is_branch_outdated("feature-branch", "main")

    def test_is_branch_outdated_is_outdated(self, git_handler, mock_repo):
        """Test is_branch_outdated when branch is outdated."""
        # Mock merge_base to return a commit with the same hash as the local commit
        # This simulates that local branch is behind remote
        target_branches = list(filter(lambda head: head.name == "feature-branch", mock_repo.heads))
        assert target_branches and len(target_branches) == 1, f"Unexpected branches: {target_branches}"
        local_commit = target_branches[0].commit
        mock_repo.merge_base.return_value = [local_commit]

        assert git_handler.is_branch_outdated("feature-branch", "main")

    def test_is_branch_outdated_no_common_ancestor(self, git_handler, mock_repo):
        """Test is_branch_outdated when there's no common ancestor."""
        # Mock merge_base to return empty list (no common ancestor)
        mock_repo.merge_base.return_value = []

        # If no common ancestor, we consider the branch outdated
        assert git_handler.is_branch_outdated("feature-branch", "main")

    def test_fetch_and_merge_remote_branch_success(self, git_handler, mock_repo):
        """Test fetch_and_merge_remote_branch successful merge."""
        result = git_handler.fetch_and_merge_remote_branch("feature-branch")

        # Verify fetch was called
        mock_repo.remotes["origin"].fetch.assert_called_once()

        # Verify merge was attempted
        mock_repo.git.merge.assert_called_once_with("origin/feature-branch", ff_only=True)

        assert result is True

    def test_fetch_and_merge_remote_branch_needs_checkout(self, git_handler, mock_repo):
        """Test fetch_and_merge_remote_branch when we need to checkout the branch first."""
        # Change current branch
        mock_active_branch = Mock()
        mock_active_branch.name = "another-branch"
        mock_repo.active_branch = mock_active_branch

        result = git_handler.fetch_and_merge_remote_branch("feature-branch")

        # Verify checkout was called
        mock_repo.git.checkout.assert_called_once_with("feature-branch")

        # Verify merge was attempted
        mock_repo.git.merge.assert_called_once_with("origin/feature-branch", ff_only=True)

        assert result is True

    def test_fetch_and_merge_remote_branch_conflict(self, git_handler, mock_repo):
        """Test fetch_and_merge_remote_branch with merge conflict."""
        # Mock git.merge to raise a GitCommandError with conflict
        merge_error = GitCommandError("git merge", 1, "CONFLICT (content): Merge conflict in file.txt")
        mock_repo.git.merge.side_effect = merge_error

        with pytest.raises(GitCodeConflictError, match="Merge conflicts detected"):
            git_handler.fetch_and_merge_remote_branch("feature-branch")

        # Verify merge abort was called
        # Please refer to the note in source code.
        # mock_repo.git.merge.assert_called_once_with("--abort")

    def test_fetch_and_merge_remote_branch_other_error(self, git_handler, mock_repo):
        """Test fetch_and_merge_remote_branch with other git error."""
        # Mock git.merge to raise a GitCommandError without conflict
        merge_error = GitCommandError("git merge", 1, "Some other error")
        mock_repo.git.merge.side_effect = merge_error

        with pytest.raises(GitCommandError, match="Some other error"):
            git_handler.fetch_and_merge_remote_branch("feature-branch")

    def test_fetch_and_merge_remote_branch_nonexistent_branch(self, git_handler, mock_repo):
        """Test fetch_and_merge_remote_branch with nonexistent branch."""
        # Mock heads to not contain the branch
        mock_heads = []
        type(mock_repo).heads = PropertyMock(return_value=mock_heads)

        with pytest.raises(ValueError,
                           match="Branch 'feature-branch' or remote branch 'origin/feature-branch' not found"):
            git_handler.fetch_and_merge_remote_branch("feature-branch")

    def test_push_branch_to_remote_success(self, git_handler, mock_repo):
        """Test push_branch_to_remote success."""
        result = git_handler.push_branch_to_remote("feature-branch")

        # Verify push was called
        mock_repo.git.push.assert_called_once_with("origin", "feature-branch")

        assert result is True

    def test_push_branch_to_remote_force(self, git_handler, mock_repo):
        """Test push_branch_to_remote with force option."""
        result = git_handler.push_branch_to_remote("feature-branch", force=True)

        # Verify force push was called
        mock_repo.git.push.assert_called_once_with("origin", "feature-branch", force=True)

        assert result is True

    def test_push_branch_to_remote_nonexistent_branch(self, git_handler, mock_repo):
        """Test push_branch_to_remote with nonexistent branch."""
        # Mock heads to not contain the branch
        head = Mock()
        head.name = "main"
        mock_heads = [head]
        type(mock_repo).heads = PropertyMock(return_value=mock_heads)

        with pytest.raises(ValueError, match="Branch 'feature-branch' not found"):
            git_handler.push_branch_to_remote("feature-branch")

    def test_push_branch_to_remote_rejected(self, git_handler, mock_repo):
        """Test push_branch_to_remote when push is rejected."""
        # Mock git.push to raise a GitCommandError with rejection message
        push_error = GitCommandError("git push", 1, "rejected non-fast-forward")
        mock_repo.git.push.side_effect = push_error

        with pytest.raises(GitCommandError, match="Push rejected: Remote has changes"):
            git_handler.push_branch_to_remote("feature-branch")

    def test_push_branch_to_remote_other_error(self, git_handler, mock_repo):
        """Test push_branch_to_remote with other git error."""
        # Mock git.push to raise a GitCommandError without rejection message
        push_error = GitCommandError("git push", 1, "Some other error")
        mock_repo.git.push.side_effect = push_error

        with pytest.raises(GitCommandError, match="Some other error"):
            git_handler.push_branch_to_remote("feature-branch")
