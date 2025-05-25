"""
Git Handler module for PR creation bot.
This module provides functionality for common git operations.
"""

import logging
import re
import sys
from typing import Any, Dict, Optional

import git
from git.exc import GitCommandError

logger = logging.getLogger(__name__)


class GitCodeConflictError(Exception):
    """Custom exception raised when a git merge operation results in code conflicts."""


class GitHandler:
    """Class to handle Git operations."""

    def __init__(self, repo_path: str = "."):
        """
        Initialize the GitHandler with the path to the git repository.

        Args:
            repo_path: Path to the git repository. Defaults to current directory.
        """
        logger.debug(f"Initializing GitHandler with repo path: {repo_path}")
        try:
            self.repo = git.Repo(repo_path)
            logger.info(f"Successfully initialized git repository at {repo_path}")

            # Safely log remote names
            try:
                remote_names = [r.name for r in self.repo.remotes] if hasattr(self.repo, "remotes") else []
                logger.debug(f"Repository remotes: {remote_names}")
            except AttributeError:
                logger.debug("Could not determine repository remotes")
        except Exception as e:
            logger.error(f"Failed to initialize git repository at {repo_path}: {str(e)}")
            raise

    def _get_current_branch(self) -> str:
        """
        Get the name of the current git branch.

        Returns:
            The name of the current branch as a string.
        """
        try:
            branch_name = self.repo.active_branch.name
            logger.debug(f"Current branch: {branch_name}")
            return branch_name
        except Exception as e:
            logger.error(f"Failed to get current branch: {str(e)}")
            raise

    def get_branch_head_commit_details(self, branch_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details of the head commit for a specific branch.

        Args:
            branch_name: Name of the branch. If None, uses the current branch.

        Returns:
            Dictionary containing commit details like hash, author, message, etc.
        """
        if branch_name is None:
            branch_name = self._get_current_branch()

        logger.debug(f"Getting head commit details for branch: {branch_name}")

        try:
            branches = list(filter(lambda head: head.name == branch_name, self.repo.heads))
            if not branches:
                available_branches = [h.name for h in self.repo.heads]
                error_msg = (
                    f"Cannot get the git branch '{branch_name}' from repository head list '{available_branches}'."
                )
                logger.error(error_msg)
                raise KeyError(error_msg)

            branch = branches[0]
            logger.debug(f"Found branch: {branch.name}")
            commit = branch.commit
            logger.debug(f"Head commit hash: {commit.hexsha}")

            commit_details = {
                "hash": commit.hexsha,
                "short_hash": commit.hexsha[:7],
                "author": {"name": commit.author.name, "email": commit.author.email},
                "committer": {"name": commit.committer.name, "email": commit.committer.email},
                "message": commit.message.strip(),
                "committed_date": commit.committed_date,
                "authored_date": commit.authored_date,
            }

            logger.debug(
                f"Commit details retrieved for branch '{branch_name}', short hash: {commit_details['short_hash']}"
            )
            return commit_details
        except (IndexError, KeyError) as e:
            logger.error(f"Branch '{branch_name}' not found: {str(e)}")
            raise ValueError(f"Branch '{branch_name}' not found")
        except Exception as e:
            logger.error(f"Unexpected error getting branch head commit details: {str(e)}")
            raise

    def get_remote_branch_head_commit_details(self, branch_name: str, remote_name: str = "origin") -> Dict[str, Any]:
        """
        Get details of the head commit for a remote branch.

        Args:
            branch_name: Name of the remote branch.
            remote_name: Name of the remote. Defaults to "origin".

        Returns:
            Dictionary containing commit details of the remote branch head.

        Raises:
            ValueError: If the remote or branch is not found.
        """
        logger.debug(f"Getting remote branch head commit details for {remote_name}/{branch_name}")

        try:
            # Safely log available remotes
            remote_names = []
            try:
                if hasattr(self.repo, "remotes"):
                    remote_names = [r.name for r in self.repo.remotes]
                    logger.debug(f"Available remotes: {remote_names}")
                else:
                    logger.debug("No remotes available in repository")
            except AttributeError:
                logger.debug("Could not access repository remotes")

            # Check for nonexistent remote
            remote = None
            if not hasattr(self.repo, "remotes") or not remote_names or remote_name not in remote_names:
                logger.error(f"Remote '{remote_name}' not found")
                raise ValueError(f"Remote '{remote_name}' not found")

            # Attempt to get the remote if it exists
            try:
                remote = getattr(self.repo.remotes, remote_name)
                logger.info(f"Fetching latest from remote '{remote_name}'")
                remote.fetch()
            except (AttributeError, TypeError) as e:
                logger.warning(f"Could not fetch from remote '{remote_name}': {str(e)}")

            # Get the remote reference
            remote_ref = f"{remote_name}/{branch_name}"
            logger.debug(f"Looking for remote reference: {remote_ref}")

            if not hasattr(self.repo, "refs") or remote_ref not in self.repo.refs:
                logger.error(f"Remote branch '{remote_name}/{branch_name}' not found")
                raise ValueError(f"Remote branch '{remote_name}/{branch_name}' not found")

            # Get the commit
            commit = self.repo.refs[remote_ref].commit
            logger.debug(f"Found commit {commit.hexsha[:7]} on {remote_name}/{branch_name}")

            # Format the commit details
            commit_details = {
                "hash": commit.hexsha,
                "short_hash": commit.hexsha[:7],
                "author": {"name": commit.author.name, "email": commit.author.email},
                "committer": {"name": commit.committer.name, "email": commit.committer.email},
                "message": commit.message.strip(),
                "committed_date": commit.committed_date,
                "authored_date": commit.authored_date,
            }

            logger.debug(f"Formatted commit details for {commit.hexsha[:7]}")
            return commit_details

        except (git.GitCommandError, ValueError) as e:
            logger.error(f"Error getting remote branch head commit: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting remote branch head commit: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get commit details: {str(e)}")

    def is_branch_outdated(
        self, branch_name: Optional[str] = None, base_branch: str = "main", remote_name: str = "origin"
    ) -> bool:
        """
        Check if the local branch is outdated compared to the remote base branch.

        Args:
            branch_name: Name of the local branch to check. If None, uses the current branch.
            base_branch: Name of the base branch to compare against. Defaults to "main".
            remote_name: Name of the remote. Defaults to "origin".

        Returns:
            True if the local branch is outdated, False otherwise.
        """
        if branch_name is None:
            branch_name = self._get_current_branch()

        logger.info(f"Checking if branch '{branch_name}' is outdated compared to '{remote_name}/{base_branch}'")

        try:
            # Get the local branch head commit
            local_commit_details = self.get_branch_head_commit_details(branch_name)
            local_commit_hash = local_commit_details["hash"]
            logger.debug(f"Local commit hash: {local_commit_hash[:7]}")

            # Get the remote base branch head commit
            remote_commit_details = self.get_remote_branch_head_commit_details(base_branch, remote_name)
            remote_commit_hash = remote_commit_details["hash"]
            logger.debug(f"Remote commit hash: {remote_commit_hash[:7]}")

            # Find the merge base (common ancestor)
            merge_base = self.repo.merge_base(local_commit_hash, remote_commit_hash)

            # If the merge base is the same as the remote commit, then remote is behind (not outdated)
            # If the merge base is the same as the local commit, then local is behind (outdated)
            # Otherwise, they have diverged from a common point

            if not merge_base:
                # No common ancestor, consider outdated
                logger.warning(f"No common ancestor found between '{branch_name}' and '{remote_name}/{base_branch}'")
                return True

            merge_base_hash = merge_base[0].hexsha
            logger.debug(f"Merge base commit hash: {merge_base_hash[:7]}")

            if merge_base_hash == local_commit_hash:
                # Local branch is behind remote
                logger.info(f"Branch '{branch_name}' is outdated (behind '{remote_name}/{base_branch}')")
                return True

            if merge_base_hash == remote_commit_hash:
                logger.info(f"Branch '{branch_name}' is ahead of '{remote_name}/{base_branch}'")
            else:
                logger.info(f"Branch '{branch_name}' has diverged from '{remote_name}/{base_branch}'")

            return False
        except Exception as e:
            logger.error(f"Error checking if branch is outdated: {str(e)}", exc_info=True)
            # In case of error, consider it outdated to be safe
            return True

    def fetch_and_merge_remote_branch(
        self, branch_name: Optional[str] = None, remote_branch: Optional[str] = None, remote_name: str = "origin"
    ) -> bool:
        """
        Fetch and merge the remote branch into the local branch.

        Args:
            branch_name: Name of the local branch to merge into. If None, uses the current branch.
            remote_branch: Name of the remote branch to fetch and merge from. If None, uses the same name as local branch.
            remote_name: Name of the remote. Defaults to "origin".

        Returns:
            True if the merge was successful, False if no merge was needed.

        Raises:
            GitCodeConflictError: If there is a conflict during the merge operation.
            ValueError: If the branch is not found.
        """
        if branch_name is None:
            branch_name = self._get_current_branch()

        if remote_branch is None:
            remote_branch = branch_name

        logger.info(f"Fetching and merging '{remote_name}/{remote_branch}' into local branch '{branch_name}'")

        # Ensure we're on the correct branch
        current_branch = self._get_current_branch()
        if current_branch != branch_name:
            logger.info(f"Switching from branch '{current_branch}' to '{branch_name}'")
            self.repo.git.checkout(branch_name)
            logger.debug(f"Successfully switched to branch '{branch_name}'")

        # Fetch the latest from remote
        logger.info(f"Fetching latest from remote '{remote_name}'")
        self.repo.remotes[remote_name].fetch()
        logger.debug(f"Fetch from '{remote_name}' completed")

        remote_ref = f"{remote_name}/{remote_branch}"
        logger.debug(f"Using remote reference: {remote_ref}")

        try:
            # Check if merge is necessary
            logger.debug("Checking if merge is necessary")
            merge_base = self.repo.merge_base(f"refs/heads/{branch_name}", f"refs/remotes/{remote_ref}")
            logger.debug(f"Found merge base: {merge_base[0].hexsha if merge_base else 'None'}")

            # Get the specific branch
            branches = list(filter(lambda head: head.name == branch_name, self.repo.heads))
            if not branches:
                available_branches = [h.name for h in self.repo.heads]
                error_msg = (
                    f"Cannot get the git branch '{branch_name}' from repository head list '{available_branches}'."
                )
                logger.error(error_msg)
                raise KeyError(error_msg)
            branch = branches[0]

            if merge_base and merge_base[0].hexsha == branch.commit.hexsha:
                # Local branch is directly behind remote, we can fast-forward
                logger.info(f"Local branch '{branch_name}' is behind remote, attempting fast-forward merge")
                try:
                    logger.debug("Attempting fast-forward merge")
                    self.repo.git.merge(remote_ref, ff_only=True)
                    logger.info(f"Successfully fast-forwarded '{branch_name}' to '{remote_ref}'")
                    return True
                except GitCommandError as e:
                    # Cannot fast-forward, need to do a real merge
                    logger.warning(f"Cannot fast-forward merge: {str(e)}")
                    logger.debug("Will attempt regular merge")

            # Try to merge
            try:
                logger.info(f"Merging '{remote_ref}' into '{branch_name}'")
                self.repo.git.merge(remote_ref)
                logger.info(f"Successfully merged '{remote_ref}' into '{branch_name}'")
                return True
            except GitCommandError as e:
                # Check if the error is due to conflicts
                error_msg = str(e)
                search_conflict = re.search(r"CONFLICT", error_msg, re.IGNORECASE)
                search_merge_fail = re.search(r"Automatic merge failed", error_msg, re.IGNORECASE)
                if search_conflict or search_merge_fail:
                    # Merge conflict detected
                    logger.error(f"Merge conflicts detected between '{branch_name}' and '{remote_ref}'")
                    logger.debug(f"Git merge error: {error_msg}")
                    # NOTE: It seems like doesn't need to do the step of command line "git merge --abort" when facing
                    # git code conflict with git Python SDK. Just note it and observe the usage state.
                    # Abort the merge
                    # self.repo.git.merge("--abort")
                    raise GitCodeConflictError(f"Merge conflicts detected between {branch_name} and {remote_ref}")

                # Other error
                logger.error(f"Error during merge operation: {error_msg}")
                raise  # Re-raise the original exception if not a conflict error

        except (IndexError, KeyError) as e:
            error_msg = f"Branch '{branch_name}' or remote branch '{remote_ref}' not found: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except GitCodeConflictError:
            # Re-raise conflict errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during fetch and merge: {str(e)}", exc_info=True)
            raise

        logger.info(f"No merge was needed between '{branch_name}' and '{remote_ref}' (already up to date)")
        return False  # No merge was needed

    def push_branch_to_remote(
        self, branch_name: Optional[str] = None, remote_name: str = "origin", force: bool = False
    ) -> bool:
        """
        Push the local branch to the remote repository.

        Args:
            branch_name: Name of the local branch to push. If None, uses the current branch.
            remote_name: Name of the remote. Defaults to "origin".
            force: If True, force push the branch. Use with caution. Defaults to False.

        Returns:
            True if the push was successful.

        Raises:
            GitCommandError: If there's an error during the push operation.
            ValueError: If the branch is not found.
        """
        if branch_name is None:
            branch_name = self._get_current_branch()

        logger.info(f"Pushing branch '{branch_name}' to remote '{remote_name}'" + (" (force)" if force else ""))

        try:
            # Ensure the branch exists
            available_branches = [b.name for b in self.repo.heads]
            logger.debug(f"Available branches: {available_branches}")

            if branch_name not in available_branches:
                error_msg = f"Branch '{branch_name}' not found in available branches: {available_branches}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Push to remote
            if force:
                logger.warning(f"Force pushing branch '{branch_name}' to '{remote_name}'")
                self.repo.git.push(remote_name, branch_name, force=True)
            else:
                logger.info(f"Pushing branch '{branch_name}' to '{remote_name}'")
                self.repo.git.push(remote_name, branch_name)

            logger.info(f"Successfully pushed branch '{branch_name}' to '{remote_name}'")
            return True

        except GitCommandError as e:
            error_msg = str(e)
            if "rejected" in error_msg and "non-fast-forward" in error_msg:
                error_details = "Push rejected: Remote has changes you don't have locally. Use force=True to override or fetch and merge first."
                logger.error(f"{error_details} Original error: {error_msg}")
                raise GitCommandError(error_details)
            logger.error(f"Error pushing branch '{branch_name}' to '{remote_name}': {error_msg}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during push operation: {str(e)}", exc_info=True)
            raise
