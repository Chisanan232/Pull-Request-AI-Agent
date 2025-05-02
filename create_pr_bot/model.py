import argparse
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from create_pr_bot.ai_bot import AiModuleClient
from create_pr_bot.project_management_tool import ProjectManagementToolType

logger = logging.getLogger(__name__)


class EnvVarPrefix(Enum):
    """Enum for environment variable prefixes."""

    CREATE_PR_BOT = "CREATE_PR_BOT"


@dataclass
class ProjectManagementToolSettings:
    """Settings for project management tool."""

    tool_type: Optional[ProjectManagementToolType] = None
    api_key: Optional[str] = None
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ProjectManagementToolSettings":
        """Load settings from environment variables."""
        prefix = f"{EnvVarPrefix.CREATE_PR_BOT.value}_PM_TOOL"

        # Get tool type
        tool_type_str = os.environ.get(f"{prefix}_TYPE")
        tool_type = None
        if tool_type_str:
            try:
                tool_type = ProjectManagementToolType(tool_type_str.lower())
            except ValueError:
                logger.warning(f"Invalid project management tool type: {tool_type_str}")

        return cls(
            tool_type=tool_type,
            api_key=os.environ.get(f"{prefix}_API_KEY"),
            organization_id=os.environ.get(f"{prefix}_ORGANIZATION_ID"),
            project_id=os.environ.get(f"{prefix}_PROJECT_ID"),
            base_url=os.environ.get(f"{prefix}_BASE_URL"),
            username=os.environ.get(f"{prefix}_USERNAME"),
        )

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert settings to configuration dictionary."""
        config = {}

        if self.api_key:
            config["api_key"] = self.api_key

        if self.organization_id:
            config["organization_id"] = self.organization_id

        if self.project_id:
            config["project_id"] = self.project_id

        if self.base_url:
            config["base_url"] = self.base_url

        if self.username:
            config["username"] = self.username

        return config


@dataclass
class AISettings:
    """Settings for AI client."""

    client_type: AiModuleClient = AiModuleClient.GPT
    api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AISettings":
        """Load settings from environment variables."""
        prefix = f"{EnvVarPrefix.CREATE_PR_BOT.value}_AI"

        # Get client type
        client_type_str = os.environ.get(f"{prefix}_CLIENT_TYPE", "gpt")
        client_type = AiModuleClient.GPT  # Default to GPT

        try:
            client_type = AiModuleClient(client_type_str.lower())
        except ValueError:
            logger.warning(f"Invalid AI client type: {client_type_str}. Using default: {client_type.value}")

        return cls(
            client_type=client_type,
            api_key=os.environ.get(f"{prefix}_API_KEY"),
        )


@dataclass
class GitHubSettings:
    """Settings for GitHub operations."""

    token: Optional[str] = None
    repo: Optional[str] = None

    @classmethod
    def from_env(cls) -> "GitHubSettings":
        """Load settings from environment variables."""
        prefix = f"{EnvVarPrefix.CREATE_PR_BOT.value}_GITHUB"

        # Try both specific and generic GitHub token env vars
        token = os.environ.get(f"{prefix}_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

        return cls(
            token=token,
            repo=os.environ.get(f"{prefix}_REPO"),
        )


@dataclass
class GitSettings:
    """Settings for Git operations."""

    repo_path: str = "."
    base_branch: str = "main"
    branch_name: Optional[str] = None

    @classmethod
    def from_env(cls) -> "GitSettings":
        """Load settings from environment variables."""
        prefix = f"{EnvVarPrefix.CREATE_PR_BOT.value}_GIT"

        return cls(
            repo_path=os.environ.get(f"{prefix}_REPO_PATH", "."),
            base_branch=os.environ.get(f"{prefix}_BASE_BRANCH", "main"),
            branch_name=os.environ.get(f"{prefix}_BRANCH_NAME"),
        )


@dataclass
class BotSettings:
    """Settings for the Create PR Bot."""

    git: GitSettings
    github: GitHubSettings
    ai: AISettings
    pm_tool: ProjectManagementToolSettings

    @classmethod
    def from_env(cls) -> "BotSettings":
        """Load settings from environment variables."""
        return cls(
            git=GitSettings.from_env(),
            github=GitHubSettings.from_env(),
            ai=AISettings.from_env(),
            pm_tool=ProjectManagementToolSettings.from_env(),
        )

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "BotSettings":
        """Load settings from command line arguments."""
        # Start with environment variables
        settings = cls.from_env()

        # Override with command line arguments if provided
        if args.repo_path:
            settings.git.repo_path = args.repo_path

        if args.base_branch:
            settings.git.base_branch = args.base_branch

        if args.branch_name:
            settings.git.branch_name = args.branch_name

        if args.github_token:
            settings.github.token = args.github_token

        if args.github_repo:
            settings.github.repo = args.github_repo

        if args.ai_client_type:
            try:
                settings.ai.client_type = AiModuleClient(args.ai_client_type.lower())
            except ValueError:
                logger.warning(f"Invalid AI client type: {args.ai_client_type}")

        if args.ai_api_key:
            settings.ai.api_key = args.ai_api_key

        if args.pm_tool_type:
            try:
                settings.pm_tool.tool_type = ProjectManagementToolType(args.pm_tool_type.lower())
            except ValueError:
                logger.warning(f"Invalid project management tool type: {args.pm_tool_type}")

        if args.pm_tool_api_key:
            settings.pm_tool.api_key = args.pm_tool_api_key

        return settings
