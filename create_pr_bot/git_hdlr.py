import ast
import logging
import os

from git import Repo, Remote, Head, GitCommandError
from typing import List, Optional, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class GitHandler:
    """Handler for Git repository operations."""
    
    def __init__(self, repo_path: str | Path):
        """
        Initialize GitHandler with repository path.
        
        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = Path(repo_path)
        self.repo = Repo(self.repo_path)

    @property
    def is_in_ci_env(self) -> bool:
        """
        Determine if the code is running in a Continuous Integration (CI) environment.

        This method evaluates environment variables to determine if the script is
        running in a CI environment such as GitHub Actions.

        :return: A boolean indicating whether the script is running in a CI environment.
        :rtype: bool
        """
        return ast.literal_eval(str(os.getenv("GITHUB_ACTIONS", "false")).capitalize())

    @property
    def _current_git_branch(self) -> str:
        """
        Get the name of the current active Git branch.

        This method attempts to retrieve the name of the current active branch
        from the Git repository associated with the object. If the repository
        is in a detached HEAD state and running in a CI environment, it falls
        back to an environment variable to determine the branch name.

        :raises TypeError: If an exception is raised and the issue cannot be handled
            (other than the detached HEAD state in CI environments).

        :return: Name of the current active Git branch, or an environment variable
            value if in CI with detached HEAD state.
        :rtype: str
        """
        try:
            current_git_branch = self.repo.active_branch.name
        except TypeError as e:
            # NOTE: Only for CI runtime environment
            logger.error("Occur something wrong when trying to get git branch.")
            if "HEAD" in str(e) and "detached" in str(e) and self.is_in_ci_env:
                current_git_branch = os.getenv("GITHUB_REF", "")
            else:
                raise e
        return current_git_branch

    def has_changes_between_branches(
        self,
        current_branch: str = "",
        default_branch: str = "master",
        remote_name: str = "remote"
    ) -> Tuple[bool, int, int]:
        """
        Check if there are differences between current branch and remote default branch.
        
        Args:
            current_branch: Name of the current branch to compare
            default_branch: Name of the default branch in remote
            remote_name: Name of the remote repository (default: "origin")
            
        Returns:
            Tuple of (has_changes: bool, ahead_count: int, behind_count: int)
            - has_changes: True if there are differences
            - ahead_count: Number of commits current branch is ahead
            - behind_count: Number of commits current branch is behind
            
        Raises:
            GitCommandError: If Git operations fail
            ValueError: If specified branches don't exist
        """
        if not current_branch:
            current_branch = self._current_git_branch
        try:
            # Fetch the latest changes from remote
            remote: Remote = self.repo.remote(remote_name)
            remote.fetch()

            # Validate current branch exists
            if current_branch not in self.repo.heads:
                raise ValueError(f"Current branch '{current_branch}' not found in local repository")

            # Get remote reference for default branch
            remote_ref = f"{remote_name}/{default_branch}"
            if remote_ref in [r.name for r in self.repo.refs]:
                raise ValueError(f"Default branch '{default_branch}' not found in remote repository")

            # Get branch references
            local_branch = self.repo.heads[current_branch]
            remote_branch = self.repo.refs[remote_ref]

            # Count commits in both directions
            behind_count = sum(1 for _ in self.repo.iter_commits(f'{local_branch}..{remote_branch}'))
            ahead_count = sum(1 for _ in self.repo.iter_commits(f'{remote_branch}..{local_branch}'))

            return bool(ahead_count or behind_count), ahead_count, behind_count

        except GitCommandError as e:
            raise GitCommandError(f"Failed to check branch differences: {e}")

    def get_head_commits(self) -> List[str]:
        """
        Get all head commit hashes from the local repository.
        
        Returns:
            List of commit hashes for all branch heads
            
        Raises:
            GitCommandError: If Git operations fail
        """
        try:
            return [head.commit.hexsha for head in self.repo.heads]
        except GitCommandError as e:
            raise GitCommandError(f"Failed to get head commits: {e}")

    def get_branch_head_commit(self, branch_name: str) -> Optional[str]:
        """
        Get the head commit hash for a specific branch.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            Commit hash if branch exists, None otherwise
            
        Raises:
            GitCommandError: If Git operations fail
        """
        try:
            if branch_name in self.repo.heads:
                return self.repo.heads[branch_name].commit.hexsha
            return None
        except GitCommandError as e:
            raise GitCommandError(f"Failed to get branch head commit: {e}")

    def get_remote_branch_head_commit(
        self,
        branch_name: str,
        remote_name: str = "remote"
    ) -> Optional[str]:
        """
        Get the head commit hash for a specific branch in the remote repository.
        
        Args:
            branch_name: Name of the branch
            remote_name: Name of the remote repository (default: "origin")
            
        Returns:
            Commit hash if remote branch exists, None otherwise
            
        Raises:
            GitCommandError: If Git operations fail
        """
        try:
            remote: Remote = self.repo.remote(remote_name)
            remote.fetch()
            
            remote_ref = f"{remote_name}/{branch_name}"
            if remote_ref in [r.name for r in self.repo.refs]:
                return self.repo.refs[remote_ref].commit.hexsha
            return None
        except GitCommandError as e:
            raise GitCommandError(f"Failed to get remote head commit: {e}")

    def get_common_ancestor(
        self,
        current_branch: str,
        default_branch: str,
        remote_name: str = "remote"
    ) -> Optional[str]:
        """
        Find the common ancestor commit between current branch and remote default branch.
        
        Args:
            current_branch: Name of the current branch
            default_branch: Name of the default branch in remote
            remote_name: Name of the remote repository (default: "origin")
            
        Returns:
            Common ancestor commit hash if found, None otherwise
            
        Raises:
            GitCommandError: If Git operations fail
            ValueError: If specified branches don't exist
        """
        try:
            if current_branch not in self.repo.heads:
                raise ValueError(f"Current branch '{current_branch}' not found in local repository")

            remote_ref = f"{remote_name}/{default_branch}"
            if remote_ref not in [r.name for r in self.repo.refs]:
                raise ValueError(f"Default branch '{default_branch}' not found in remote repository")

            merge_base = self.repo.merge_base(
                self.repo.heads[current_branch],
                self.repo.refs[remote_ref]
            )
            return merge_base[0].hexsha if merge_base else None
            
        except GitCommandError as e:
            raise GitCommandError(f"Failed to find common ancestor: {e}")
