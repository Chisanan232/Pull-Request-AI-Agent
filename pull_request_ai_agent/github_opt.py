"""
GitHub operations module for handling GitHub repository interactions.
This module uses PyGithub to interact with GitHub repositories.
"""

import logging
from typing import Dict, List, Optional, Union

from github import Github, GithubException
from github.PullRequest import PullRequest

logger = logging.getLogger(__name__)


class GitHubOperations:
    """Class for handling GitHub repository operations."""

    def __init__(self, access_token: str, repo_name: str):
        """
        Initialize GitHub operations with an access token and repository name.

        Args:
            access_token: GitHub access token
            repo_name: Repository name in format 'owner/repo'
        """
        logger.debug(f"Initializing GitHub operations for repository: {repo_name}")
        try:
            self.github = Github(access_token)
            self.repo_name = repo_name
            self.repo = self.github.get_repo(repo_name)
            logger.info(f"Successfully connected to GitHub repository: {repo_name}")
        except GithubException as e:
            logger.error(f"Failed to initialize GitHub operations for {repo_name}: {e.data.get('message', '')}")
            raise

    def _get_pull_requests(self, state: str = "open") -> List[PullRequest]:
        """
        Get a list of pull requests from the repository.

        Args:
            state: State of PRs to retrieve (open, closed, all)

        Returns:
            List of pull request objects

        Raises:
            GithubException: If GitHub API request fails
        """
        logger.debug(f"Fetching {state} pull requests from repository {self.repo_name}")
        try:
            pulls = list(self.repo.get_pulls(state=state))
            logger.debug(f"Found {len(pulls)} {state} pull requests")
            return pulls
        except GithubException as e:
            error_msg = f"Failed to get pull requests: {e.data.get('message', '')}"
            logger.error(error_msg)
            raise GithubException(e.status, error_msg)

    def get_pull_request_by_branch(self, head_branch: str) -> Optional[PullRequest]:
        """
        Get a specific pull request by its head branch name.

        Args:
            head_branch: The head branch name of the pull request

        Returns:
            Pull request object if found, None otherwise

        Raises:
            GithubException: If GitHub API request fails
        """
        logger.debug(f"Looking for pull request with head branch: {head_branch}")
        try:
            pulls = self._get_pull_requests()
            for pr in pulls:
                if pr.head.ref == head_branch:
                    logger.info(f"Found existing PR #{pr.number} for branch '{head_branch}'")
                    logger.debug(f"PR details: Title='{pr.title}', State={pr.state}, URL={pr.html_url}")
                    return pr

            logger.info(f"No existing pull request found for branch '{head_branch}'")
            return None
        except GithubException as e:
            error_msg = f"Failed to find PR for branch '{head_branch}': {e.data.get('message', '')}"
            logger.error(error_msg)
            raise GithubException(e.status, error_msg)

    def create_pull_request(
        self,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
        draft: bool = False,
    ) -> PullRequest:
        """
        Create a new pull request in the repository.

        Args:
            title: Title of the pull request
            body: Description body of the pull request
            base_branch: The branch to merge into (destination)
            head_branch: The branch containing changes (source)
            draft: Whether to create as a draft PR (default: False)

        Returns:
            Created pull request object

        Raises:
            GithubException: If GitHub API request fails
        """
        logger.info(f"Creating new pull request from '{head_branch}' to '{base_branch}'")
        logger.debug(f"PR details: Title='{title}', Draft={draft}")

        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=head_branch,
                draft=draft,
            )
            logger.info(f"Successfully created PR #{pr.number}: {pr.html_url}")
            return pr
        except GithubException as e:
            error_msg = f"Failed to create PR from '{head_branch}' to '{base_branch}': {e.data.get('message', '')}"
            logger.error(error_msg)
            raise GithubException(e.status, error_msg)

    def add_labels_to_pull_request(
        self, pull_request: Union[PullRequest, int], labels_config: Dict[str, List[str]]
    ) -> List[str]:
        """
        Add GitHub labels to a specific pull request based on changed files.

        Args:
            pull_request: Pull request object or PR number
            labels_config: Dictionary mapping file patterns to label names
                Example: {"*.py": ["python"], "docs/*": ["documentation"]}

        Returns:
            List of labels that were added

        Raises:
            GithubException: If GitHub API request fails
            ValueError: If the pull request is not found
        """
        logger.debug(f"Adding labels to PR based on changed files")
        pr_id = pull_request if isinstance(pull_request, int) else pull_request.number
        logger.debug(f"Processing PR #{pr_id} with labels config: {labels_config}")

        try:
            # Get PR object if number is provided
            if isinstance(pull_request, int):
                logger.debug(f"Getting PR object for PR #{pull_request}")
                pr = self.repo.get_pull(pull_request)
            else:
                pr = pull_request

            # Get changed files in the PR
            logger.debug(f"Fetching changed files for PR #{pr.number}")
            changed_files = [file.filename for file in pr.get_files()]
            logger.debug(f"Files changed in PR #{pr.number}: {changed_files}")

            # Determine which labels to add based on changed files
            labels_to_add = set()
            for file_path in changed_files:
                for pattern, labels in labels_config.items():
                    # Simple wildcard matching (can be enhanced with regex)
                    if pattern.endswith("*"):
                        prefix = pattern[:-1]
                        if file_path.startswith(prefix):
                            logger.debug(f"File '{file_path}' matches pattern '{pattern}', adding labels: {labels}")
                            labels_to_add.update(labels)
                    # Exact match
                    elif pattern == file_path:
                        logger.debug(f"File '{file_path}' exactly matches pattern '{pattern}', adding labels: {labels}")
                        labels_to_add.update(labels)
                    # Extension match
                    elif pattern.startswith("*.") and file_path.endswith(pattern[1:]):
                        logger.debug(
                            f"File '{file_path}' matches extension pattern '{pattern}', adding labels: {labels}"
                        )
                        labels_to_add.update(labels)

            # Add labels to PR
            if labels_to_add:
                logger.info(f"Adding labels to PR #{pr.number}: {list(labels_to_add)}")
                pr.add_to_labels(*labels_to_add)
            else:
                logger.info(f"No labels matched for PR #{pr.number}")

            return list(labels_to_add)

        except GithubException as e:
            error_msg = f"Failed to add labels to PR #{pr_id}: {e.data.get('message', '')}"
            logger.error(error_msg)
            raise GithubException(e.status, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while adding labels to PR #{pr_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
