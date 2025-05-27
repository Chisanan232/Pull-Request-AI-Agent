"""
PullRequestAIAgent - A bot that helps developers create pull requests with AI-generated content.
"""

import logging
import re
import traceback
from typing import Any, Dict, List, Optional

from github.PullRequest import PullRequest

from .ai_bot import AiModuleClient
from .ai_bot._base.client import BaseAIClient
from .ai_bot.claude.client import ClaudeClient
from .ai_bot.gemini.client import GeminiClient
from .ai_bot.gpt.client import GPTClient
from .ai_bot.prompts.model import PRPromptData, prepare_pr_prompt_data
from .git_hdlr import GitCodeConflictError, GitHandler
from .github_opt import GitHubOperations
from .model import ProjectManagementToolSettings
from .project_management_tool import ProjectManagementToolType
from .project_management_tool._base.client import BaseProjectManagementAPIClient
from .project_management_tool._base.model import BaseImmutableModel
from .project_management_tool.clickup.client import ClickUpAPIClient
from .project_management_tool.jira.client import JiraAPIClient

logger = logging.getLogger(__name__)


class PullRequestAIAgent:
    """
    A bot that automates creation of pull requests with AI-generated content
    based on git commits and task tickets information.
    """

    # AI client types
    AI_CLIENT_GPT = AiModuleClient.GPT
    AI_CLIENT_CLAUDE = AiModuleClient.CLAUDE
    AI_CLIENT_GEMINI = AiModuleClient.GEMINI

    # Project management tool types
    PM_TOOL_CLICKUP = ProjectManagementToolType.CLICKUP
    PM_TOOL_JIRA = ProjectManagementToolType.JIRA

    def __init__(
        self,
        repo_path: str = ".",
        base_branch: str = "main",
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        project_management_tool_type: Optional[ProjectManagementToolType] = None,
        project_management_tool_config: Optional[ProjectManagementToolSettings] = None,
        ai_client_type: AiModuleClient = AI_CLIENT_GPT,
        ai_client_api_key: Optional[str] = None,
    ):
        """
        Initialize the PullRequestAIAgent.

        Args:
            repo_path: Path to the git repository. Defaults to current directory.
            base_branch: Name of the base branch to compare against. Defaults to "main".
            github_token: GitHub access token for API access.
            github_repo: GitHub repository name in format 'owner/repo'.
            project_management_tool_type: Type of project management tool to use.
            project_management_tool_config: Configuration for the project management tool.
            ai_client_type: Type of AI client to use (gpt, claude, gemini).
            ai_client_api_key: API key for the AI service.
        """
        logger.debug("Initializing PullRequestAIAgent")
        self.repo_path = repo_path
        self.base_branch = base_branch
        logger.debug(f"Using repository path: {repo_path}, base branch: {base_branch}")

        # Initialize Git handler
        self.git_handler = GitHandler(repo_path)
        logger.debug("Git handler initialized")

        # Initialize GitHub operations if token and repo are provided
        self.github_operations = None
        if github_token and github_repo:
            logger.debug(f"Initializing GitHub operations for repo: {github_repo}")
            self.github_operations = GitHubOperations(github_token, github_repo)
        else:
            logger.info("GitHub operations not configured - github_token or github_repo not provided")

        # Initialize project management client based on type
        self.project_management_client = None
        self.project_management_tool_type = project_management_tool_type
        if project_management_tool_type and project_management_tool_config:
            logger.debug(
                f"Initializing project management client of type: {project_management_tool_type.name if hasattr(project_management_tool_type, 'name') else project_management_tool_type}"
            )
            self.project_management_client = self._initialize_project_management_client(
                project_management_tool_type, project_management_tool_config
            )
        else:
            logger.info("Project management tool not configured - tool type or config not provided")

        # Initialize AI client based on type
        logger.debug(
            f"Initializing AI client of type: {ai_client_type.name if hasattr(ai_client_type, 'name') else ai_client_type}"
        )
        self.ai_client = self._initialize_ai_client(ai_client_type, ai_client_api_key)
        logger.info("PullRequestAIAgent initialization complete")

    def _initialize_project_management_client(
        self, tool_type: ProjectManagementToolType, config: ProjectManagementToolSettings
    ) -> Optional[BaseProjectManagementAPIClient]:
        """
        Initialize the project management client based on the specified type.

        Args:
            tool_type: Type of project management tool
            config: Configuration for the project management tool

        Returns:
            Initialized project management client or None if initialization fails

        Raises:
            ValueError: If the tool type is not supported or required config is missing
        """
        logger.debug(
            f"Initializing project management client for tool type: {tool_type.name if hasattr(tool_type, 'name') else tool_type}"
        )

        if tool_type == self.PM_TOOL_CLICKUP:
            if not config.api_key:
                logger.error("ClickUp API token is missing but required")
                raise ValueError("ClickUp API token is required")
            logger.debug("Creating ClickUp API client")
            return ClickUpAPIClient(api_token=config.api_key)
        elif tool_type == self.PM_TOOL_JIRA:
            required_keys = ["base_url", "username", "api_key"]
            missing_keys = [key for key in required_keys if getattr(config, key) is None]
            if missing_keys:
                logger.error(f"Jira configuration missing required keys: {missing_keys}")
                raise ValueError(f"Jira {missing_keys[0]} is required")
            assert config.base_url and config.username and config.api_key
            logger.debug(f"Creating Jira API client with base URL: {config.base_url}")
            return JiraAPIClient(base_url=config.base_url, email=config.username, api_token=config.api_key)
        else:
            logger.error(
                f"Unsupported project management tool type: {tool_type.name if hasattr(tool_type, 'name') else tool_type}"
            )
            raise ValueError(
                f"Unsupported project management tool type: {tool_type.name if hasattr(tool_type, 'name') else tool_type}"
            )

    def _initialize_ai_client(self, client_type: AiModuleClient, api_key: Optional[str] = None) -> BaseAIClient:
        """
        Initialize the AI client based on the specified type.

        Args:
            client_type: Type of AI client (gpt, claude, gemini)
            api_key: API key for the AI service

        Returns:
            Initialized AI client

        Raises:
            ValueError: If the client type is not supported
        """
        logger.debug(
            f"Initializing AI client of type: {client_type.name if hasattr(client_type, 'name') else client_type}"
        )

        if api_key is None:
            logger.warning(
                f"No API key provided for {client_type.name if hasattr(client_type, 'name') else client_type} AI client"
            )

        if client_type == self.AI_CLIENT_GPT:
            logger.debug("Creating GPT client")
            return GPTClient(api_key=api_key)
        elif client_type == self.AI_CLIENT_CLAUDE:
            logger.debug("Creating Claude client")
            return ClaudeClient(api_key=api_key)
        elif client_type == self.AI_CLIENT_GEMINI:
            logger.debug("Creating Gemini client")
            return GeminiClient(api_key=api_key)
        else:
            logger.error(
                f"Unsupported AI client type: {client_type.name if hasattr(client_type, 'name') else client_type}"
            )
            raise ValueError(
                f"Unsupported AI client type: {client_type.name if hasattr(client_type, 'name') else client_type}"
            )

    def _get_current_branch(self) -> str:
        """
        Get the name of the current git branch.

        Returns:
            Name of the current branch
        """
        logger.debug("Getting current git branch name")
        branch_name = self.git_handler._get_current_branch()
        logger.debug(f"Current branch name: {branch_name}")
        return branch_name

    def is_branch_outdated(self, branch_name: Optional[str] = None) -> bool:
        """
        Check if the branch is outdated compared to the base branch.

        Args:
            branch_name: Name of the branch to check. If None, uses the current branch.

        Returns:
            True if the branch is outdated, False otherwise
        """
        if not branch_name:
            branch_name = self._get_current_branch()

        logger.debug(f"Checking if branch '{branch_name}' is outdated compared to '{self.base_branch}'")
        is_outdated = self.git_handler.is_branch_outdated(branch_name, self.base_branch)
        logger.debug(f"Branch '{branch_name}' outdated status: {is_outdated}")
        return is_outdated

    def is_pr_already_opened(self, branch_name: Optional[str] = None) -> bool:
        """
        Check if a pull request is already opened for the branch.

        Args:
            branch_name: Name of the branch to check. If None, uses the current branch.

        Returns:
            True if a PR exists, False otherwise
        """
        if not branch_name:
            branch_name = self._get_current_branch()

        logger.debug(f"Checking if PR already exists for branch: {branch_name}")

        if not self.github_operations:
            logger.warning("GitHub operations not configured. Cannot check if PR exists.")
            return False

        try:
            pr = self.github_operations.get_pull_request_by_branch(branch_name)
            if pr is not None:
                logger.info(f"Found existing PR #{pr.number} for branch '{branch_name}'")
            else:
                logger.debug(f"No existing PR found for branch '{branch_name}'")
            return pr is not None
        except Exception as e:
            logger.error(f"Error checking if PR exists for branch '{branch_name}': {str(e)}", exc_info=True)
            return False

    def fetch_and_merge_latest_from_base_branch(self, branch_name: Optional[str] = None) -> bool:
        """
        Fetch and merge the latest changes from the remote base branch.

        Args:
            branch_name: Name of the branch to update. If None, uses the current branch.

        Returns:
            True if update was successful, False otherwise

        Raises:
            GitCodeConflictError: If there is a merge conflict
        """
        if not branch_name:
            branch_name = self._get_current_branch()

        logger.info(f"Fetching and merging latest changes from '{self.base_branch}' into '{branch_name}'")

        try:
            result = self.git_handler.fetch_and_merge_remote_branch(branch_name)
            if result:
                logger.info(
                    f"Successfully updated branch '{branch_name}' with latest changes from '{self.base_branch}'"
                )
            else:
                logger.warning(
                    f"No changes were applied when updating branch '{branch_name}' from '{self.base_branch}'"
                )
            return result
        except GitCodeConflictError as e:
            logger.error(
                f"Merge conflict detected when updating branch '{branch_name}' from '{self.base_branch}': {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error during fetch and merge operation: {str(e)}", exc_info=True)
            raise

    def get_branch_commits(self, branch_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all commits in the branch that are not in the base branch.

        Args:
            branch_name: Name of the branch to get commits from. If None, uses the current branch.

        Returns:
            List of commit details

        Raises:
            ValueError: If the feature branch or base branch cannot be found
        """
        if not branch_name:
            branch_name = self._get_current_branch()

        logger.info(f"Getting commits from branch '{branch_name}' that are not in '{self.base_branch}'")

        # Get the commits between the base branch and the current branch
        repo = self.git_handler.repo

        try:
            # Check if branches exist using repo.refs
            refs = {ref.name: ref for ref in repo.refs}
            logger.debug(f"Available git references: {list(refs.keys())}")

            # Try different possible reference formats
            feature_ref_options = [
                branch_name,
                f"refs/heads/{branch_name}",
                f"origin/{branch_name}",
                f"refs/remotes/origin/{branch_name}",
            ]

            base_ref_options = [
                self.base_branch,
                f"refs/heads/{self.base_branch}",
                f"origin/{self.base_branch}",
                f"refs/remotes/origin/{self.base_branch}",
            ]

            logger.debug(f"Searching for feature branch using options: {feature_ref_options}")
            logger.debug(f"Searching for base branch using options: {base_ref_options}")

            # Find valid references using filter
            feature_branch_ref = next(filter(lambda ref: ref in refs, feature_ref_options), None)
            base_branch_ref = next(filter(lambda ref: ref in refs, base_ref_options), None)

            # If we couldn't find valid references, raise an error
            if not feature_branch_ref:
                error_msg = f"Feature branch '{branch_name}' not found. Available references: {list(refs.keys())}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if not base_branch_ref:
                error_msg = f"Base branch '{self.base_branch}' not found. Available references: {list(refs.keys())}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Found feature branch reference: {feature_branch_ref}")
            logger.info(f"Found base branch reference: {base_branch_ref}")

            # Get the merge base between the branches
            merge_base = repo.merge_base(feature_branch_ref, base_branch_ref)
            if not merge_base:
                logger.warning(f"No merge base found between '{feature_branch_ref}' and '{base_branch_ref}'")
                return []

            logger.debug(f"Merge base commit: {merge_base[0].hexsha}")

            # Get all commits from merge base to head of branch
            base_commit = merge_base[0]
            commits = []

            # Iterate through commits in reverse chronological order
            for commit in repo.iter_commits(f"{branch_name}"):
                # Stop when we reach the merge base
                if commit.hexsha == base_commit.hexsha:
                    break

                commits.append(
                    {
                        "hash": commit.hexsha,
                        "short_hash": commit.hexsha[:7],
                        "author": {"name": commit.author.name, "email": commit.author.email},
                        "committer": {"name": commit.committer.name, "email": commit.committer.email},
                        "message": commit.message.strip(),
                        "committed_date": commit.committed_date,
                        "authored_date": commit.authored_date,
                    }
                )

            logger.info(f"Found {len(commits)} unique commits in branch '{branch_name}'")
            logger.debug(f"Commit short hashes: {[c['short_hash'] for c in commits]}")
            return commits
        except ValueError:
            # Re-raise ValueError exceptions (our custom errors)
            raise
        except Exception as e:
            logger.error(f"Error getting branch commits: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return []

    def extract_ticket_id(self, branch_name: str) -> str:
        """
        Extract ticket ID from the git branch name.

        Args:
            branch_name: the git branch name

        Returns:
            The unique ticket ID
        """
        logger.debug(f"Extracting ticket ID from branch name: {branch_name}")

        # Common patterns for ticket IDs in commit messages
        # Adjust patterns based on your project's conventions
        patterns = [
            r"#(\d+)",  # GitHub issue format: #123
            r"([A-Z]+-\d+)",  # Jira format: PROJ-123
            r"CU-([a-z0-9]+)",  # ClickUp format: CU-abc123
            r"Task-(\d+)",  # Generic task format: Task-123
        ]

        for pattern in patterns:
            matches = re.search(pattern, branch_name)
            if matches:
                ticket_id = matches.group(0)
                logger.info(f"Found ticket ID '{ticket_id}' in branch '{branch_name}'")
                return ticket_id

        logger.warning(f"No ticket ID pattern found in branch name: {branch_name}")
        return ""

    def get_ticket_details(self, ticket_ids: List[str]) -> List[BaseImmutableModel]:
        """
        Get details for each ticket ID from the project management system.

        Args:
            ticket_ids: List of ticket IDs to get details for

        Returns:
            List of ticket details as BaseImmutableModel objects
        """
        logger.debug(f"Getting ticket details for IDs: {ticket_ids}")

        if not self.project_management_client:
            logger.warning("Project management client not configured. Cannot get ticket details.")
            return []

        if not ticket_ids:
            logger.info("No ticket IDs provided. Skipping ticket details retrieval.")
            return []

        ticket_details = []

        for ticket_id in ticket_ids:
            formatted_ticket_id = self.format_ticket_id(ticket_id)
            if not formatted_ticket_id:
                logger.warning(f"Ticket ID '{ticket_id}' could not be formatted properly, skipping")
                continue

            try:
                logger.info(f"Getting details for ticket ID: '{ticket_id}' (formatted: '{formatted_ticket_id}')")
                ticket = self.project_management_client.get_ticket(formatted_ticket_id)

                if ticket:
                    logger.info("Successfully retrieved ticket details")
                    logger.debug(f"Ticket data: {ticket}")
                    ticket_details.append(ticket)
                else:
                    logger.warning(f"No ticket found with ID: '{formatted_ticket_id}'")
            except Exception as e:
                logger.error(f"Error getting details for ticket {ticket_id}: {str(e)}", exc_info=True)

        logger.info(f"Retrieved {len(ticket_details)} tickets out of {len(ticket_ids)} requested")
        return ticket_details

    def format_ticket_id(self, ticket_id: str) -> Optional[str]:
        """
        Format the ticket ID based on the project management tool.

        Args:
            ticket_id: Original ticket ID

        Returns:
            Formatted ticket ID
        """
        if ticket_id is None:
            logger.warning("Cannot format None ticket ID")
            return None

        # Trim whitespace from ticket ID
        ticket_id = ticket_id.strip()
        logger.debug(f"Formatting ticket ID: {ticket_id}")

        if self.project_management_tool_type:
            pm_tool_type = self.project_management_tool_type
            logger.debug(
                f"Using project management tool type: {pm_tool_type.name if hasattr(pm_tool_type, 'name') else pm_tool_type}"
            )

            if pm_tool_type == self.PM_TOOL_CLICKUP:
                # For ClickUp, remove the 'CU-' prefix if it exists
                if ticket_id.startswith("CU-"):
                    return ticket_id[3:]  # Remove the 'CU-' prefix
                else:
                    # If no prefix, return as is
                    return ticket_id
            elif pm_tool_type == self.PM_TOOL_JIRA:
                # JIRA IDs already have a proper format, return as is
                return ticket_id
            else:
                logger.warning(
                    f"Unknown project management tool type: {pm_tool_type.name if hasattr(pm_tool_type, 'name') else pm_tool_type}"
                )
                return ticket_id
        else:
            logger.debug("No project management tool configured, returning ticket ID as is")
            return ticket_id

    def _format_ticket_id(self, ticket_id: str) -> Optional[str]:
        """
        Legacy method retained for backward compatibility with tests.
        Use format_ticket_id() instead.

        Args:
            ticket_id: Raw ticket ID from commit message

        Returns:
            Formatted ticket ID or None if formatting fails
        """
        logger.debug("Using legacy _format_ticket_id method, consider updating to format_ticket_id")
        return self.format_ticket_id(ticket_id)

    def prepare_ai_prompt(
        self, commits: List[Dict[str, Any]], ticket_details: List[BaseImmutableModel]
    ) -> PRPromptData:
        """
        Prepare a prompt for the AI to generate a PR title and body.

        Args:
            commits: List of commit details
            ticket_details: List of ticket details as BaseImmutableModel objects

        Returns:
            Formatted prompt string
        """
        logger.info("Preparing AI prompt for PR generation")
        logger.debug(f"Using {len(commits)} commits and {len(ticket_details)} tickets to generate prompt")

        # Extract ticket information
        ticket_info_list = []
        for ticket in ticket_details:
            logger.debug(f"Extracting information from ticket: {getattr(ticket, 'id', 'unknown')}")
            ticket_info = self._extract_ticket_info(ticket)
            ticket_info_list.append(ticket_info)

        # Ensure commits have required fields
        formatted_commits = []
        for commit in commits:
            if "short_hash" in commit and "message" in commit:
                formatted_commits.append({"short_hash": commit["short_hash"], "message": commit["message"]})
            else:
                logger.warning(f"Skipping commit missing required fields: {commit}")

        try:
            # Process prompt templates
            logger.debug("Loading prompt template and preparing data")
            prompt_data = prepare_pr_prompt_data(
                task_tickets_details=ticket_info_list, commits=formatted_commits, project_root=self.repo_path
            )

            # For now, we'll just use the title prompt
            # In the future, we could use both title and description separately
            logger.info("Successfully prepared AI prompt")
            return prompt_data

        except FileNotFoundError as e:
            logger.error(f"Failed to load prompt template: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error preparing AI prompt: {str(e)}", exc_info=True)

            # Fallback to a simple prompt
            logger.info("Using fallback prompt template due to error")
            prompt = (
                "I need you to generate a pull request title and description based on the following information:\n\n"
            )

            # Add commit information
            prompt += "## Commits\n"
            for i, commit in enumerate(commits, 1):
                prompt += f"{i}. {commit.get('short_hash', '')} - {commit.get('message', '')}\n"

            prompt += "\n"

            # Add ticket information
            if ticket_info_list:
                prompt += "## Related Tickets\n"
                for i, ticket_info in enumerate(ticket_info_list, 1):
                    prompt += f"{i}. {ticket_info.get('id', '')}: {ticket_info.get('title', '')}\n"
                    if ticket_info.get("description"):
                        # Truncate long descriptions
                        short_desc = (
                            ticket_info["description"][:200] + "..."
                            if len(ticket_info["description"]) > 200
                            else ticket_info["description"]
                        )
                        prompt += f"   Description: {short_desc}\n"

                    # Add status if available
                    if ticket_info.get("status"):
                        prompt += f"   Status: {ticket_info['status']}\n"

                prompt += "\n"

            # Add PR template if available
            try:
                from pathlib import Path

                pr_template_path = Path(self.repo_path) / ".github" / "PULL_REQUEST_TEMPLATE.md"
                if pr_template_path.exists():
                    logger.debug(f"Loading PR template from: {pr_template_path}")
                    with open(pr_template_path, "r", encoding="utf-8") as file:
                        pr_template = file.read()
                    prompt += f"## Pull Request Template\n{pr_template}\n\n"
                else:
                    logger.debug("No PR template found")
            except Exception as e:
                # Ignore errors when trying to read PR template in fallback mode
                logger.error(f"Error setting pull request template into AI prompt: {str(e)}")

            logger.debug("Fallback prompt generated successfully")

            # Wrap the string prompt in a PRPromptData object to maintain consistent return type
            from pull_request_ai_agent.ai_bot.prompts.model import PRPromptData

            # Create a fallback title based on ticket info or a generic title
            fallback_title = "Pull Request"
            if ticket_info_list and ticket_info_list[0].get("title"):
                fallback_title = f"Fix: {ticket_info_list[0]['title']}"

            logger.debug(f"Created fallback PRPromptData with title: {fallback_title}")
            return PRPromptData(title=fallback_title, description=prompt)

    def _parse_ai_response_title(self, response: str) -> str:
        """
        Parse the AI-generated response into a PR title.

        Args:
            response: Raw response about PR title from the AI

        Returns:
            Pure value of PR title
        """
        logger.info("Parsing AI-generated response for title")
        logger.debug(f"Raw AI response length: {len(response)} characters")

        # Remove unnecessary quotes
        # example value: "Implement Test Change for PR Bot"
        pure_response = response.replace('"', "")
        return pure_response

    def _parse_ai_response_body(self, response: str) -> str:
        """
        Parse the AI-generated response into a PR body.

        Args:
            response: Raw response about PR body from the AI

        Returns:
            Pure value of PR body
        """
        logger.info("Parsing AI-generated response for body")
        logger.debug(f"Raw AI response length: {len(response)} characters")

        # Remove unnecessary quotes
        # example value:
        # Here's how you can fill up the PR description based on the provided information:
        #
        # ```markdown
        # [//]: # (The target why you modify something.)
        # ## _Target_
        #
        # [//]: # (The summary what you did or your target.)
        #
        # ...... some content
        #
        # ```
        #
        # Please note, since no task ticket was provided, the "Task ID" and "Relative task IDs" fields are marked as N/A.
        markdown_match = re.search(r"```(markdown)?\n((.|\n)*)```", response, re.DOTALL)
        if markdown_match:
            logger.info("Found Markdown content in AI response")
            markdown_content = markdown_match.group(1)
            logger.debug(f"Markdown content: {markdown_content}")
            pure_markdown_content = markdown_content.replace("```", "")
        else:
            logger.warning("Failed to find Markdown content in AI response")
            pure_markdown_content = ""
        return pure_markdown_content

    def create_pull_request(self, title: str, body: str, branch_name: Optional[str] = None) -> Optional[PullRequest]:
        """
        Create a pull request from the branch to the base branch.

        Args:
            title: Title of the pull request
            body: Body/description of the pull request
            branch_name: Name of the branch to create PR from. If None, uses the current branch.

        Returns:
            Created PullRequest object or None if creation failed
        """
        if not branch_name:
            branch_name = self._get_current_branch()

        logger.info(f"Creating pull request from '{branch_name}' to '{self.base_branch}'")
        logger.debug(f"PR Title: {title}")
        logger.debug(f"PR Body length: {len(body)} characters")

        if not self.github_operations:
            logger.error("GitHub operations not configured. Cannot create PR.")
            return None

        try:
            # Create the pull request
            logger.info("Submitting PR creation request to GitHub API")
            pr = self.github_operations.create_pull_request(
                title=title, body=body, base_branch=self.base_branch, head_branch=branch_name
            )

            logger.info(f"Successfully created pull request #{pr.number}: {pr.html_url}")
            return pr
        except Exception as e:
            logger.error(f"Error creating pull request: {str(e)}", exc_info=True)
            return None

    def run(self, branch_name: Optional[str] = None) -> Optional[PullRequest]:
        """
        Run the PR creation workflow.

        Args:
            branch_name: Name of the branch to create PR from. If None, uses the current branch.

        Returns:
            Created PullRequest object or None if no PR was created
        """
        if not branch_name:
            branch_name = self._get_current_branch()

        logger.info(f"Running PullRequestAIAgent for branch: {branch_name}")
        logger.debug("Starting PR creation workflow")

        # Step 1: Check if branch is outdated
        logger.info("Checking if branch is outdated")
        is_outdated = self.is_branch_outdated(branch_name)
        logger.info(f"Branch is outdated: {is_outdated}")

        # Step 2: Check if PR already exists
        logger.info("Checking if PR already exists")
        pr_exists = self.is_pr_already_opened(branch_name)
        logger.info(f"PR already exists: {pr_exists}")

        if pr_exists:
            logger.info("Skipping PR creation as PR already exists for this branch")
            return None

        # Step 3: Update branch from base if needed
        if is_outdated:
            logger.info("Branch is outdated, attempting to update from base branch")
            try:
                self.fetch_and_merge_latest_from_base_branch(branch_name)
                logger.info("Successfully updated branch with latest changes from base branch")
            except GitCodeConflictError as e:
                logger.error(f"Merge conflict detected: {str(e)}")
                logger.info("Cannot proceed with automatic PR creation due to merge conflicts")
                return None
            except Exception as e:
                logger.error(f"Error updating branch: {str(e)}", exc_info=True)
                logger.info("Cannot proceed with automatic PR creation due to update error")
                return None

        # Step 4: Get commits from the branch
        logger.info("Getting commits from branch")
        commits = self.get_branch_commits(branch_name)
        if not commits:
            logger.warning("No commits found in branch, cannot create PR")
            return None
        logger.info(f"Found {len(commits)} commits in branch")

        # Step 5: Extract ticket IDs from branch name
        logger.info("Extracting ticket ID from branch name")
        ticket_id = self.extract_ticket_id(branch_name)

        # Step 6: Get ticket details
        ticket_details = []
        if ticket_id:
            logger.info(f"Getting details for ticket: {ticket_id}")
            ticket_details = self.get_ticket_details([ticket_id])
        else:
            logger.info("No ticket ID found in branch name, skipping ticket details")

        # Step 7: Prepare AI prompt
        logger.info("Preparing AI prompt")
        prompt = self.prepare_ai_prompt(commits, ticket_details)

        # Step 8: Generate PR content using AI
        logger.info("Generating PR content using AI")
        try:
            ai_response_title = self.ai_client.get_content(prompt.title)
            ai_response_body = self.ai_client.get_content(prompt.description)
            logger.info("Successfully generated content using AI")
            logger.debug(f"AI response for PR title length: {len(ai_response_title)} characters")
            logger.debug(f"AI response for PR title: {ai_response_title}")
            logger.debug(f"AI response for PR body length: {len(ai_response_body)} characters")
            logger.debug(f"AI response for PR body: {ai_response_body}")
        except Exception as e:
            logger.error(f"Error generating content with AI: {str(e)}", exc_info=True)
            logger.info("Using fallback PR content due to AI failure")
            # Create a fallback PR with generic content
            current_branch = self._get_current_branch()
            title = f"Update {current_branch}"
            body = "Automated pull request."
            return self.create_pull_request(title, body, current_branch)

        # Step 9: Parse AI response
        logger.info("Parsing AI response")
        pr_title = self._parse_ai_response_title(ai_response_title)
        pr_body = self._parse_ai_response_body(ai_response_body)

        # Step 10: Create PR
        logger.info("Creating pull request")
        pr = self.create_pull_request(pr_title, pr_body, branch_name)

        if pr:
            logger.info(f"PR creation workflow completed successfully: {pr.html_url}")
        else:
            logger.warning("PR creation workflow completed but no PR was created")

        return pr

    def _extract_ticket_info(self, ticket: BaseImmutableModel) -> Dict[str, str]:
        """
        Extract relevant information from a ticket based on its type.

        Args:
            ticket: Ticket object as a BaseImmutableModel

        Returns:
            Dictionary with standardized ticket information
        """
        ticket_info = {"id": "", "title": "", "description": "", "status": ""}
        ticket_id = getattr(ticket, "id", "unknown")
        logger.debug(f"Extracting information from ticket {ticket_id}")

        # Handle different ticket types
        if self.project_management_tool_type == self.PM_TOOL_CLICKUP:
            logger.debug("Processing ClickUp ticket format")
            ticket_info["id"] = getattr(ticket, "id", "")
            ticket_info["title"] = getattr(ticket, "name", "")

            # Use text_content if available, otherwise use description
            description = getattr(ticket, "text_content", None)
            if not description:
                description = getattr(ticket, "description", "")
            ticket_info["description"] = description or ""

            # Get status if available
            status = getattr(ticket, "status", None)
            if status:
                ticket_info["status"] = getattr(status, "status", "")

        elif self.project_management_tool_type == self.PM_TOOL_JIRA:
            logger.debug("Processing Jira ticket format")
            ticket_info["id"] = getattr(ticket, "id", "")
            ticket_info["title"] = getattr(ticket, "title", "")
            ticket_info["description"] = getattr(ticket, "description", "")
            ticket_info["status"] = getattr(ticket, "status", "")
        else:
            logger.debug("Processing unknown ticket type using generic extraction")
            # Try to extract common attributes
            for field in ["id", "title", "name", "description", "status"]:
                value = getattr(ticket, field, None)
                if value and isinstance(value, str):
                    if field == "name" and not ticket_info["title"]:
                        ticket_info["title"] = value
                    else:
                        ticket_info[field] = value

        logger.debug(
            f"Extracted ticket info: ID={ticket_info['id']}, Title={ticket_info['title']}, Status={ticket_info['status']}"
        )
        return ticket_info
