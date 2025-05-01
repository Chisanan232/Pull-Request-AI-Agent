"""
GitHub operations module for handling GitHub repository interactions.
This module uses PyGithub to interact with GitHub repositories.
"""

from typing import Dict, List, Optional, Union

from github import Github, GithubException
from github.PullRequest import PullRequest


class GitHubOperations:
    """Class for handling GitHub repository operations."""

    def __init__(self, access_token: str, repo_name: str):
        """
        Initialize GitHub operations with an access token and repository name.

        Args:
            access_token: GitHub access token
            repo_name: Repository name in format 'owner/repo'
        """
        self.github = Github(access_token)
        self.repo_name = repo_name
        self.repo = self.github.get_repo(repo_name)

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
        try:
            return list(self.repo.get_pulls(state=state))
        except GithubException as e:
            raise GithubException(e.status, f"Failed to get pull requests: {e.data.get('message', '')}")

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
        try:
            pulls = self._get_pull_requests()
            for pr in pulls:
                if pr.head.ref == head_branch:
                    return pr
            return None
        except GithubException as e:
            raise GithubException(
                e.status, f"Failed to find PR for branch '{head_branch}': {e.data.get('message', '')}"
            )

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
        try:
            return self.repo.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=head_branch,
                draft=draft,
            )
        except GithubException as e:
            raise GithubException(
                e.status, f"Failed to create PR from '{head_branch}' to '{base_branch}': {e.data.get('message', '')}"
            )

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
        try:
            # Get PR object if number is provided
            if isinstance(pull_request, int):
                pr = self.repo.get_pull(pull_request)
            else:
                pr = pull_request

            # Get changed files in the PR
            changed_files = [file.filename for file in pr.get_files()]

            # Determine which labels to add based on changed files
            labels_to_add = set()
            for file_path in changed_files:
                for pattern, labels in labels_config.items():
                    # Simple wildcard matching (can be enhanced with regex)
                    if pattern.endswith("*"):
                        prefix = pattern[:-1]
                        if file_path.startswith(prefix):
                            labels_to_add.update(labels)
                    # Exact match
                    elif pattern == file_path:
                        labels_to_add.update(labels)
                    # Extension match
                    elif pattern.startswith("*.") and file_path.endswith(pattern[1:]):
                        labels_to_add.update(labels)

            # Add labels to PR
            if labels_to_add:
                pr.add_to_labels(*labels_to_add)

            return list(labels_to_add)

        except GithubException as e:
            raise GithubException(e.status, f"Failed to add labels to PR: {e.data.get('message', '')}")
