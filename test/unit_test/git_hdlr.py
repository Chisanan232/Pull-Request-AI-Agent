import ast
import os

import pytest
from pathlib import Path
from git import Repo, GitCommandError
from unittest.mock import Mock, patch

from create_pr_bot.git_hdlr import GitHandler


class TestGitHandler:
    """Test cases for GitHandler."""

    @pytest.fixture
    def mock_repo(self):
        """Fixture for mocked Git repository."""
        mock_repo = Mock(spec=Repo)
        
        # Mock the heads dictionary-like behavior
        mock_repo.heads = {}
        
        # Mock the refs dictionary-like behavior
        mock_repo.refs = {}
        
        return mock_repo

    @pytest.fixture
    def git_handler(self, mock_repo):
        """Fixture for GitHandler with mocked repository."""
        with patch('create_pr_bot.git_hdlr.Repo') as mock_repo_class:
            mock_repo_class.return_value = mock_repo
            handler = GitHandler('./')
            return handler

    @property
    def default_branch(self) -> str:
        return "master"

    @property
    def remote_name(self) -> str:
        return "origin" if self._is_in_ci_env else "remote"

    @property
    def remote_ref(self) -> str:
        return f"{self.remote_name}/{self.default_branch}"

    @property
    def commit_hash(self) -> str:
        return "abc123"

    @property
    def _is_in_ci_env(self) -> bool:
        return ast.literal_eval(str(os.getenv("GITHUB_ACTIONS", "false")).capitalize())

    def test_has_changes_between_branches_with_differences(self, git_handler, mock_repo):
        """Test detecting changes between branches when differences exist."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        # Mock current branch
        mock_current_branch = Mock()
        mock_current_branch.name = git_handler._current_git_branch
        # Ensure commit has hexsha attribute
        mock_current_commit = Mock()
        mock_current_commit.hexsha = 'current_sha_123'
        mock_current_branch.commit = mock_current_commit
        mock_repo.heads = {git_handler._current_git_branch: mock_current_branch}
        
        # Mock remote branch
        mock_remote_branch = Mock()
        mock_remote_branch.name = self.remote_ref
        # Ensure commit has hexsha attribute
        mock_remote_commit = Mock()
        mock_remote_commit.hexsha = 'remote_sha_456'
        mock_remote_branch.commit = mock_remote_commit
        mock_repo.refs = {self.remote_ref: mock_remote_branch}
        
        # Mock commit iteration for behind and ahead counts
        def mock_iter_commits(*args, **kwargs):
            if args[0] == f'{git_handler._current_git_branch}..{self.remote_ref}':  # behind count
                mock_behind = Mock()
                mock_behind.hexsha = 'behind_sha_789'
                return [mock_behind]
            elif args[0] == f'{self.remote_ref}..{git_handler._current_git_branch}':  # ahead count
                mock_ahead1 = Mock()
                mock_ahead1.hexsha = 'ahead_sha_def'
                mock_ahead2 = Mock()
                mock_ahead2.hexsha = 'ahead_sha_ghi'
                return [mock_ahead1, mock_ahead2]
            return []
        mock_repo.iter_commits.side_effect = mock_iter_commits
        
        has_changes, ahead, behind = git_handler.has_changes_between_branches(
            git_handler._current_git_branch,
            self.default_branch,
            self.remote_name
        )
        assert has_changes is True
        assert ahead == 2
        assert behind == 1
        mock_remote.fetch.assert_called_once()

    def test_has_changes_between_branches_no_differences(self, git_handler, mock_repo):
        """Test detecting changes between branches when no differences exist."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        # Mock current branch
        mock_current_branch = Mock()
        mock_current_branch.name = git_handler._current_git_branch
        mock_repo.heads = {git_handler._current_git_branch: mock_current_branch}
        
        # Mock remote branch
        mock_remote_branch = Mock()
        mock_remote_branch.name = self.remote_ref
        mock_repo.refs = {self.remote_ref: mock_remote_branch}
        
        # Mock commit iteration with no differences
        mock_repo.iter_commits.return_value = []
        
        has_changes, ahead, behind = git_handler.has_changes_between_branches(
            git_handler._current_git_branch,
            self.default_branch,
            self.remote_name
        )
        assert has_changes is False
        assert ahead == 0
        assert behind == 0
        mock_remote.fetch.assert_called_once()

    def test_has_changes_between_branches_invalid_current(self, git_handler, mock_repo):
        """Test error handling for invalid current branch."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        # Empty heads dictionary
        mock_repo.heads = {}
        
        with pytest.raises(ValueError, match=f"Current branch '{git_handler._current_git_branch}' not found"):
            git_handler.has_changes_between_branches(
                git_handler._current_git_branch,
                self.default_branch,
                self.remote_name
            )

    def test_has_changes_between_branches_invalid_default(self, git_handler, mock_repo):
        """Test error handling for invalid default branch."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        # Mock current branch exists
        mock_current_branch = Mock()
        mock_current_branch.name = git_handler._current_git_branch
        mock_repo.heads = {git_handler._current_git_branch: mock_current_branch}
        
        # Empty refs dictionary
        mock_repo.refs = {}
        
        with pytest.raises(ValueError, match=f"Default branch '{self.default_branch}' not found"):
            git_handler.has_changes_between_branches(
                git_handler._current_git_branch,
                self.default_branch,
                self.remote_name
            )

    def test_get_branch_head_commit_existing(self, git_handler, mock_repo):
        """Test getting head commit for existing branch."""
        # Mock branch with commit
        mock_commit = Mock()
        mock_commit.hexsha = 'abc123'  # Explicitly set hexsha
        
        mock_branch = Mock()
        mock_branch.commit = mock_commit
        
        mock_repo.heads = {git_handler._current_git_branch: mock_branch}
        
        commit_hash = git_handler.get_branch_head_commit(git_handler._current_git_branch)
        assert commit_hash == 'abc123'

    def test_get_branch_head_commit_nonexistent(self, git_handler, mock_repo):
        """Test getting head commit for nonexistent branch."""
        mock_repo.heads = {}
        
        commit_hash = git_handler.get_branch_head_commit('nonexistent')
        assert commit_hash is None

    def test_get_remote_branch_head_commit_existing(self, git_handler, mock_repo):
        """Test getting remote head commit for existing branch."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        # Mock remote ref with commit
        mock_commit = Mock()
        mock_commit.hexsha = 'abc123'  # Explicitly set hexsha
        
        mock_ref = Mock()
        mock_ref.commit = mock_commit
        
        mock_repo.refs = {self.remote_ref: mock_ref}
        
        commit_hash = git_handler.get_remote_branch_head_commit(self.default_branch)
        assert commit_hash == 'abc123'
        mock_remote.fetch.assert_called_once()

    def test_get_remote_branch_head_commit_nonexistent(self, git_handler, mock_repo):
        """Test getting remote head commit for nonexistent branch."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        mock_repo.refs = {}
        
        commit_hash = git_handler.get_remote_branch_head_commit('nonexistent')
        assert commit_hash is None
        mock_remote.fetch.assert_called_once()

    def test_get_common_ancestor_success(self, git_handler, mock_repo):
        """Test finding common ancestor between branches."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        # Mock current branch
        mock_current_branch = Mock()
        mock_current_branch.name = git_handler._current_git_branch
        # Ensure commit has hexsha attribute
        mock_current_commit = Mock()
        mock_current_commit.hexsha = 'current_sha_123'
        mock_current_branch.commit = mock_current_commit
        mock_repo.heads = {git_handler._current_git_branch: mock_current_branch}
        
        # Mock remote branch
        mock_remote_branch = Mock()
        mock_remote_branch.name = self.remote_ref
        # Ensure commit has hexsha attribute
        mock_remote_commit = Mock()
        mock_remote_commit.hexsha = 'remote_sha_456'
        mock_remote_branch.commit = mock_remote_commit
        mock_repo.refs = {self.remote_ref: mock_remote_branch}
        
        # Mock merge base
        mock_commit = Mock()
        mock_commit.hexsha = 'abc123'  # Explicitly set hexsha
        mock_repo.merge_base.return_value = [mock_commit]
        
        ancestor = git_handler.get_common_ancestor(git_handler._current_git_branch, self.default_branch)
        assert ancestor == 'abc123'

    def test_get_common_ancestor_no_common(self, git_handler, mock_repo):
        """Test finding common ancestor when none exists."""
        # Mock remote
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote
        
        # Mock current branch
        mock_current_branch = Mock()
        mock_current_branch.name = git_handler._current_git_branch
        # Ensure commit has hexsha attribute
        mock_current_commit = Mock()
        mock_current_commit.hexsha = 'current_sha_123'
        mock_current_branch.commit = mock_current_commit
        mock_repo.heads = {git_handler._current_git_branch: mock_current_branch}
        
        # Mock remote branch
        mock_remote_branch = Mock()
        mock_remote_branch.name = self.remote_ref
        # Ensure commit has hexsha attribute
        mock_remote_commit = Mock()
        mock_remote_commit.hexsha = 'remote_sha_456'
        mock_remote_branch.commit = mock_remote_commit
        mock_repo.refs = {self.remote_ref: mock_remote_branch}
        
        # Mock no merge base
        mock_repo.merge_base.return_value = []
        
        ancestor = git_handler.get_common_ancestor(git_handler._current_git_branch, self.default_branch)
        assert ancestor is None
