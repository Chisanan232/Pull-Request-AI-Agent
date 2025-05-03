import argparse
import os
from unittest.mock import MagicMock, patch

from create_pr_bot.ai_bot import AiModuleClient
from create_pr_bot.model import (
    AISettings,
    BotSettings,
    GitHubSettings,
    GitSettings,
    ProjectManagementToolSettings,
)
from create_pr_bot.project_management_tool import ProjectManagementToolType


class TestProjectManagementToolSettings:
    """Tests for the ProjectManagementToolSettings class."""

    def test_from_env_empty(self):
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings = ProjectManagementToolSettings.from_env()
            assert settings.tool_type is None
            assert settings.api_key is None
            assert settings.organization_id is None
            assert settings.project_id is None
            assert settings.base_url is None
            assert settings.username is None

    def test_from_env_with_values(self):
        """Test loading settings from environment variables with values."""
        env_vars = {
            "CREATE_PR_BOT_PM_TOOL_TYPE": "clickup",
            "CREATE_PR_BOT_PM_TOOL_API_KEY": "test-api-key",
            "CREATE_PR_BOT_PM_TOOL_ORGANIZATION_ID": "test-org-id",
            "CREATE_PR_BOT_PM_TOOL_PROJECT_ID": "test-project-id",
            "CREATE_PR_BOT_PM_TOOL_BASE_URL": "https://example.com",
            "CREATE_PR_BOT_PM_TOOL_USERNAME": "test-user",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = ProjectManagementToolSettings.from_env()
            assert settings.tool_type == ProjectManagementToolType.CLICKUP
            assert settings.api_key == "test-api-key"
            assert settings.organization_id == "test-org-id"
            assert settings.project_id == "test-project-id"
            assert settings.base_url == "https://example.com"
            assert settings.username == "test-user"

    def test_from_env_invalid_tool_type(self):
        """Test loading settings with invalid tool type."""
        env_vars = {
            "CREATE_PR_BOT_PM_TOOL_TYPE": "invalid-type",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("logging.Logger.warning") as mock_warning:
                settings = ProjectManagementToolSettings.from_env()
                assert settings.tool_type is None
                mock_warning.assert_called_once()

    def test_to_config_dict_empty(self):
        """Test converting empty settings to config dict."""
        settings = ProjectManagementToolSettings()
        config = settings.to_config_dict()
        assert config == {}

    def test_to_config_dict_with_values(self):
        """Test converting settings with values to config dict."""
        settings = ProjectManagementToolSettings(
            tool_type=ProjectManagementToolType.CLICKUP,
            api_key="test-api-key",
            organization_id="test-org-id",
            project_id="test-project-id",
            base_url="https://example.com",
            username="test-user",
        )

        config = settings.to_config_dict()
        assert config["api_key"] == "test-api-key"
        assert config["organization_id"] == "test-org-id"
        assert config["project_id"] == "test-project-id"
        assert config["base_url"] == "https://example.com"
        assert config["username"] == "test-user"


class TestAISettings:
    """Tests for the AISettings class."""

    def test_from_env_empty(self):
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings = AISettings.from_env()
            assert settings.client_type == AiModuleClient.GPT
            assert settings.api_key is None

    def test_from_env_with_values(self):
        """Test loading settings from environment variables with values."""
        env_vars = {
            "CREATE_PR_BOT_AI_CLIENT_TYPE": "claude",
            "CREATE_PR_BOT_AI_API_KEY": "test-api-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = AISettings.from_env()
            assert settings.client_type == AiModuleClient.CLAUDE
            assert settings.api_key == "test-api-key"

    def test_from_env_invalid_client_type(self):
        """Test loading settings with invalid client type."""
        env_vars = {
            "CREATE_PR_BOT_AI_CLIENT_TYPE": "invalid-type",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("logging.Logger.warning") as mock_warning:
                settings = AISettings.from_env()
                assert settings.client_type == AiModuleClient.GPT
                mock_warning.assert_called_once()


class TestGitHubSettings:
    """Tests for the GitHubSettings class."""

    def test_from_env_empty(self):
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings = GitHubSettings.from_env()
            assert settings.token is None
            assert settings.repo is None

    def test_from_env_with_values(self):
        """Test loading settings from environment variables with values."""
        env_vars = {
            "CREATE_PR_BOT_GITHUB_TOKEN": "test-token",
            "CREATE_PR_BOT_GITHUB_REPO": "owner/repo",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = GitHubSettings.from_env()
            assert settings.token == "test-token"
            assert settings.repo == "owner/repo"

    def test_from_env_fallback_token(self):
        """Test loading token from fallback environment variables."""
        # Test GITHUB_TOKEN fallback
        with patch.dict(os.environ, {"GITHUB_TOKEN": "github-token"}, clear=True):
            settings = GitHubSettings.from_env()
            assert settings.token == "github-token"

        # Test GH_TOKEN fallback
        with patch.dict(os.environ, {"GH_TOKEN": "gh-token"}, clear=True):
            settings = GitHubSettings.from_env()
            assert settings.token == "gh-token"

        # Test priority order
        env_vars = {
            "CREATE_PR_BOT_GITHUB_TOKEN": "specific-token",
            "GITHUB_TOKEN": "github-token",
            "GH_TOKEN": "gh-token",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = GitHubSettings.from_env()
            assert settings.token == "specific-token"


class TestGitSettings:
    """Tests for the GitSettings class."""

    def test_from_env_empty(self):
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings = GitSettings.from_env()
            assert settings.repo_path == "."
            assert settings.base_branch == "main"
            assert settings.branch_name is None

    def test_from_env_with_values(self):
        """Test loading settings from environment variables with values."""
        env_vars = {
            "CREATE_PR_BOT_GIT_REPO_PATH": "/path/to/repo",
            "CREATE_PR_BOT_GIT_BASE_BRANCH": "master",
            "CREATE_PR_BOT_GIT_BRANCH_NAME": "feature/test",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = GitSettings.from_env()
            assert settings.repo_path == "/path/to/repo"
            assert settings.base_branch == "master"
            assert settings.branch_name == "feature/test"


class TestBotSettings:
    """Tests for the BotSettings class."""

    def test_from_env(self):
        """Test loading settings from environment variables."""
        with patch("create_pr_bot.model.GitSettings.from_env") as mock_git:
            with patch("create_pr_bot.model.GitHubSettings.from_env") as mock_github:
                with patch("create_pr_bot.model.AISettings.from_env") as mock_ai:
                    with patch("create_pr_bot.model.ProjectManagementToolSettings.from_env") as mock_pm:
                        mock_git.return_value = "git_settings"
                        mock_github.return_value = "github_settings"
                        mock_ai.return_value = "ai_settings"
                        mock_pm.return_value = "pm_settings"

                        settings = BotSettings.from_env()

                        assert settings.git == "git_settings"
                        assert settings.github == "github_settings"
                        assert settings.ai == "ai_settings"
                        assert settings.pm_tool == "pm_settings"

                        mock_git.assert_called_once()
                        mock_github.assert_called_once()
                        mock_ai.assert_called_once()
                        mock_pm.assert_called_once()

    def test_from_args(self):
        """Test loading settings from command line arguments."""
        # Create mock args
        args = argparse.Namespace(
            repo_path="/path/to/repo",
            base_branch="master",
            branch_name="feature/test",
            github_token="test-token",
            github_repo="owner/repo",
            ai_client_type="claude",
            ai_api_key="test-ai-key",
            pm_tool_type="jira",
            pm_tool_api_key="test-pm-key",
        )

        # Create mock settings
        mock_settings = MagicMock()
        mock_settings.git = MagicMock()
        mock_settings.github = MagicMock()
        mock_settings.ai = MagicMock()
        mock_settings.pm_tool = MagicMock()

        with patch("create_pr_bot.__main__.BotSettings.from_env", return_value=mock_settings):
            settings = BotSettings.from_args(args)

            # Verify settings were updated
            assert settings.git.repo_path == "/path/to/repo"
            assert settings.git.base_branch == "master"
            assert settings.git.branch_name == "feature/test"
            assert settings.github.token == "test-token"
            assert settings.github.repo == "owner/repo"
            assert settings.ai.api_key == "test-ai-key"
            assert settings.pm_tool.api_key == "test-pm-key"
