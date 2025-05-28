import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

from pull_request_ai_agent.ai_bot import AiModuleClient
from pull_request_ai_agent.model import (
    AISettings,
    BotSettings,
    GitHubSettings,
    GitSettings,
    ProjectManagementToolSettings,
    find_default_config_path,
    load_yaml_config,
)
from pull_request_ai_agent.project_management_tool import ProjectManagementToolType


class TestLoadYamlConfig:
    """Tests for the load_yaml_config function."""

    def test_load_yaml_config_success(self) -> None:
        """Test loading a valid YAML configuration file."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as temp:
            temp.write(
                """
            git:
              repo_path: "/path/to/repo"
              base_branch: "main"
            github:
              token: "github_token"
              repo: "user/repo"
            project_management_tool:
              type: "jira"
              api_key: "api_key"
              base_url: "https://example.atlassian.net"
              username: "username@example.com"
            ai:
              client_type: "gpt"
              api_key: "api_key"
            """
            )
            temp.flush()
            temp_path = temp.name

        try:
            config: Dict[str, Any] = load_yaml_config(temp_path)
            assert config["git"]["repo_path"] == "/path/to/repo"
            assert config["git"]["base_branch"] == "main"
            assert config["github"]["token"] == "github_token"
            assert config["github"]["repo"] == "user/repo"
            assert config["project_management_tool"]["type"] == "jira"
            assert config["project_management_tool"]["api_key"] == "api_key"
            assert config["project_management_tool"]["base_url"] == "https://example.atlassian.net"
            assert config["project_management_tool"]["username"] == "username@example.com"
            assert config["ai"]["client_type"] == "gpt"
            assert config["ai"]["api_key"] == "api_key"
        finally:
            os.unlink(temp_path)

    def test_load_yaml_config_file_not_found(self) -> None:
        """Test loading a non-existent YAML configuration file."""
        with pytest.raises(FileNotFoundError):
            load_yaml_config("/path/to/nonexistent/file.yaml")

    def test_load_yaml_config_invalid_yaml(self) -> None:
        """Test loading an invalid YAML configuration file."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as temp:
            temp.write("invalid: yaml: content:")
            temp.flush()
            temp_path = temp.name

        try:
            with pytest.raises(yaml.YAMLError):
                load_yaml_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_yaml_config_empty_file(self) -> None:
        """Test loading an empty YAML configuration file."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as temp:
            temp.flush()
            temp_path = temp.name

        try:
            config: Dict[str, Any] = load_yaml_config(temp_path)
            assert config == {}
        finally:
            os.unlink(temp_path)


class TestFindDefaultConfigPath:
    """Tests for the find_default_config_path function."""

    def test_find_default_config_path_yaml(self) -> None:
        """Test finding the default YAML configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .github directory
            github_dir = Path(temp_dir) / ".github"
            github_dir.mkdir()

            # Create pr-creator.yaml file
            config_path = github_dir / "pr-creator.yaml"
            config_path.touch()

            # Test finding the file
            result: Optional[Path] = find_default_config_path(temp_dir)
            assert result == config_path

    def test_find_default_config_path_yml(self) -> None:
        """Test finding the default YML configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .github directory
            github_dir = Path(temp_dir) / ".github"
            github_dir.mkdir()

            # Create pr-creator.yml file
            config_path = github_dir / "pr-creator.yml"
            config_path.touch()

            # Test finding the file
            result: Optional[Path] = find_default_config_path(temp_dir)
            assert result == config_path

    def test_find_default_config_path_both_extensions(self) -> None:
        """Test finding the default configuration file when both extensions exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .github directory
            github_dir = Path(temp_dir) / ".github"
            github_dir.mkdir()

            # Create both pr-creator.yaml and pr-creator.yml files
            yaml_path = github_dir / "pr-creator.yaml"
            yaml_path.touch()

            yml_path = github_dir / "pr-creator.yml"
            yml_path.touch()

            # Test finding the file (should prefer .yaml)
            result: Optional[Path] = find_default_config_path(temp_dir)
            assert result == yaml_path

    def test_find_default_config_path_not_found(self) -> None:
        """Test finding the default configuration file when it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .github directory without config file
            github_dir = Path(temp_dir) / ".github"
            github_dir.mkdir()

            # Test finding the file
            result: Optional[Path] = find_default_config_path(temp_dir)
            assert result is None

    def test_find_default_config_path_no_github_dir(self) -> None:
        """Test finding the default configuration file when .github directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test finding the file
            result: Optional[Path] = find_default_config_path(temp_dir)
            assert result is None


class TestProjectManagementToolSettings:
    """Tests for the ProjectManagementToolSettings class."""

    def test_from_env_empty(self) -> None:
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings: ProjectManagementToolSettings = ProjectManagementToolSettings.from_env()
            assert settings.tool_type is None
            assert settings.api_key is None
            assert settings.organization_id is None
            assert settings.project_id is None
            assert settings.base_url is None
            assert settings.username is None

    def test_from_env_with_values(self) -> None:
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
            settings: ProjectManagementToolSettings = ProjectManagementToolSettings.from_env()
            assert settings.tool_type == ProjectManagementToolType.CLICKUP
            assert settings.api_key == "test-api-key"
            assert settings.organization_id == "test-org-id"
            assert settings.project_id == "test-project-id"
            assert settings.base_url == "https://example.com"
            assert settings.username == "test-user"

    def test_from_env_invalid_tool_type(self) -> None:
        """Test loading settings with invalid tool type."""
        env_vars = {
            "CREATE_PR_BOT_PM_TOOL_TYPE": "invalid-type",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("logging.Logger.warning") as mock_warning:
                settings: ProjectManagementToolSettings = ProjectManagementToolSettings.from_env()
                assert settings.tool_type is None
                mock_warning.assert_called_once()

    def test_serialize_empty(self) -> None:
        """Test loading settings from an empty dictionary."""
        settings: ProjectManagementToolSettings = ProjectManagementToolSettings.serialize({})
        assert settings.tool_type is None
        assert settings.api_key is None
        assert settings.organization_id is None
        assert settings.project_id is None
        assert settings.base_url is None
        assert settings.username is None

    def test_serialize_with_values(self) -> None:
        """Test loading settings from a dictionary with values."""
        config = {
            "project_management_tool": {
                "type": "clickup",
                "api_key": "test-api-key",
                "organization_id": "test-org-id",
                "project_id": "test-project-id",
                "base_url": "https://example.com",
                "username": "test-user",
            }
        }

        settings: ProjectManagementToolSettings = ProjectManagementToolSettings.serialize(config)
        assert settings.tool_type == ProjectManagementToolType.CLICKUP
        assert settings.api_key == "test-api-key"
        assert settings.organization_id == "test-org-id"
        assert settings.project_id == "test-project-id"
        assert settings.base_url == "https://example.com"
        assert settings.username == "test-user"

    def test_serialize_invalid_tool_type(self) -> None:
        """Test loading settings with invalid tool type."""
        config = {
            "project_management_tool": {
                "type": "invalid-type",
            }
        }

        with patch("logging.Logger.warning") as mock_warning:
            settings: ProjectManagementToolSettings = ProjectManagementToolSettings.serialize(config)
            assert settings.tool_type is None
            mock_warning.assert_called_once()


class TestAISettings:
    """Tests for the AISettings class."""

    def test_from_env_empty(self) -> None:
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings: AISettings = AISettings.from_env()
            assert settings.client_type == AiModuleClient.GPT
            assert settings.api_key is None

    def test_from_env_with_values(self) -> None:
        """Test loading settings from environment variables with values."""
        env_vars = {
            "CREATE_PR_BOT_AI_CLIENT_TYPE": "claude",
            "CREATE_PR_BOT_AI_API_KEY": "test-api-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings: AISettings = AISettings.from_env()
            assert settings.client_type == AiModuleClient.CLAUDE
            assert settings.api_key == "test-api-key"

    def test_from_env_invalid_client_type(self) -> None:
        """Test loading settings with invalid client type."""
        env_vars = {
            "CREATE_PR_BOT_AI_CLIENT_TYPE": "invalid-type",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("logging.Logger.warning") as mock_warning:
                settings: AISettings = AISettings.from_env()
                assert settings.client_type == AiModuleClient.GPT
                mock_warning.assert_called_once()

    def test_serialize_empty(self) -> None:
        """Test loading settings from an empty dictionary."""
        settings: AISettings = AISettings.serialize({})
        assert settings.client_type == AiModuleClient.GPT
        assert settings.api_key is None

    def test_serialize_with_values(self) -> None:
        """Test loading settings from a dictionary with values."""
        config = {
            "ai": {
                "client_type": "claude",
                "api_key": "test-api-key",
            }
        }

        settings: AISettings = AISettings.serialize(config)
        assert settings.client_type == AiModuleClient.CLAUDE
        assert settings.api_key == "test-api-key"

    def test_serialize_invalid_client_type(self) -> None:
        """Test loading settings with invalid client type."""
        config = {
            "ai": {
                "client_type": "invalid-type",
            }
        }

        with patch("logging.Logger.warning") as mock_warning:
            settings: AISettings = AISettings.serialize(config)
            assert settings.client_type == AiModuleClient.GPT
            mock_warning.assert_called_once()


class TestGitHubSettings:
    """Tests for the GitHubSettings class."""

    def test_from_env_empty(self) -> None:
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings: GitHubSettings = GitHubSettings.from_env()
            assert settings.token is None
            assert settings.repo is None

    def test_from_env_with_values(self) -> None:
        """Test loading settings from environment variables with values."""
        env_vars = {
            "CREATE_PR_BOT_GITHUB_TOKEN": "test-token",
            "CREATE_PR_BOT_GITHUB_REPO": "owner/repo",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings: GitHubSettings = GitHubSettings.from_env()
            assert settings.token == "test-token"
            assert settings.repo == "owner/repo"

    def test_from_env_fallback_token(self) -> None:
        """Test loading token from fallback environment variables."""
        env_vars = {
            "GITHUB_TOKEN": "fallback-token",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings: GitHubSettings = GitHubSettings.from_env()
            assert settings.token == "fallback-token"

    def test_serialize_empty(self) -> None:
        """Test loading settings from an empty dictionary."""
        settings: GitHubSettings = GitHubSettings.serialize({})
        assert settings.token is None
        assert settings.repo is None

    def test_serialize_with_values(self) -> None:
        """Test loading settings from a dictionary with values."""
        config = {
            "github": {
                "token": "test-token",
                "repo": "owner/repo",
            }
        }

        settings: GitHubSettings = GitHubSettings.serialize(config)
        assert settings.token == "test-token"
        assert settings.repo == "owner/repo"


class TestGitSettings:
    """Tests for the GitSettings class."""

    def test_from_env_empty(self) -> None:
        """Test loading settings from empty environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings: GitSettings = GitSettings.from_env()
            assert settings.repo_path == "."
            assert settings.base_branch == "main"
            assert settings.branch_name is None

    def test_from_env_with_values(self) -> None:
        """Test loading settings from environment variables with values."""
        env_vars = {
            "CREATE_PR_BOT_GIT_REPO_PATH": "/path/to/repo",
            "CREATE_PR_BOT_GIT_BASE_BRANCH": "master",
            "CREATE_PR_BOT_GIT_BRANCH_NAME": "feature/test",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings: GitSettings = GitSettings.from_env()
            assert settings.repo_path == "/path/to/repo"
            assert settings.base_branch == "master"
            assert settings.branch_name == "feature/test"

    def test_serialize_empty(self) -> None:
        """Test loading settings from an empty dictionary."""
        settings: GitSettings = GitSettings.serialize({})
        assert settings.repo_path == "."
        assert settings.base_branch == "main"
        assert settings.branch_name is None

    def test_serialize_with_values(self) -> None:
        """Test loading settings from a dictionary with values."""
        config = {
            "git": {
                "repo_path": "/path/to/repo",
                "base_branch": "master",
                "branch_name": "feature/test",
            }
        }

        settings: GitSettings = GitSettings.serialize(config)
        assert settings.repo_path == "/path/to/repo"
        assert settings.base_branch == "master"
        assert settings.branch_name == "feature/test"


class TestBotSettings:
    """Tests for the BotSettings class."""

    def test_from_env(self) -> None:
        """Test loading settings from environment variables."""
        with patch("pull_request_ai_agent.model.GitSettings.from_env") as mock_git:
            with patch("pull_request_ai_agent.model.GitHubSettings.from_env") as mock_github:
                with patch("pull_request_ai_agent.model.AISettings.from_env") as mock_ai:
                    with patch("pull_request_ai_agent.model.ProjectManagementToolSettings.from_env") as mock_pm:
                        mock_git.return_value = MagicMock(spec=GitSettings)
                        mock_github.return_value = MagicMock(spec=GitHubSettings)
                        mock_ai.return_value = MagicMock(spec=AISettings)
                        mock_pm.return_value = MagicMock(spec=ProjectManagementToolSettings)

                        settings: BotSettings = BotSettings.from_env()

                        assert settings.git is mock_git.return_value
                        assert settings.github is mock_github.return_value
                        assert settings.ai is mock_ai.return_value
                        assert settings.pm_tool is mock_pm.return_value

                        mock_git.assert_called_once()
                        mock_github.assert_called_once()
                        mock_ai.assert_called_once()
                        mock_pm.assert_called_once()

    def test_from_args(self) -> None:
        """Test loading settings from command line arguments."""
        # Create mock args
        args = MagicMock()
        args.repo_path = "/path/to/repo"
        args.base_branch = "master"
        args.branch_name = "feature/test"
        args.github_token = "test-token"
        args.github_repo = "owner/repo"
        args.ai_client_type = "claude"
        args.ai_api_key = "test-ai-key"
        args.pm_tool_type = "jira"
        args.pm_tool_api_key = "test-pm-key"
        args.config_file = None

        # Create mock settings
        env_settings = MagicMock()
        env_settings.git = MagicMock()
        env_settings.github = MagicMock()
        env_settings.ai = MagicMock()
        env_settings.pm_tool = MagicMock()

        with patch("pull_request_ai_agent.model.BotSettings.from_env", return_value=env_settings):
            with patch("pull_request_ai_agent.model.find_default_config_path", return_value=None):
                settings: BotSettings = BotSettings.from_args(args)

                # Verify settings were updated from args
                assert settings.git.repo_path == "/path/to/repo"
                assert settings.git.base_branch == "master"
                assert settings.git.branch_name == "feature/test"
                assert settings.github.token == "test-token"
                assert settings.github.repo == "owner/repo"
                assert settings.ai.client_type == AiModuleClient.CLAUDE
                assert settings.ai.api_key == "test-ai-key"
                assert settings.pm_tool.tool_type == ProjectManagementToolType.JIRA
                assert settings.pm_tool.api_key == "test-pm-key"

    def test_serialize(self) -> None:
        """Test loading settings from a dictionary."""
        with patch("pull_request_ai_agent.model.GitSettings.serialize") as mock_git:
            with patch("pull_request_ai_agent.model.GitHubSettings.serialize") as mock_github:
                with patch("pull_request_ai_agent.model.AISettings.serialize") as mock_ai:
                    with patch("pull_request_ai_agent.model.ProjectManagementToolSettings.serialize") as mock_pm:
                        mock_git.return_value = MagicMock(spec=GitSettings)
                        mock_github.return_value = MagicMock(spec=GitHubSettings)
                        mock_ai.return_value = MagicMock(spec=AISettings)
                        mock_pm.return_value = MagicMock(spec=ProjectManagementToolSettings)

                        config: Dict[str, Any] = {"test": "config"}
                        settings: BotSettings = BotSettings.serialize(config)

                        assert settings.git is mock_git.return_value
                        assert settings.github is mock_github.return_value
                        assert settings.ai is mock_ai.return_value
                        assert settings.pm_tool is mock_pm.return_value

                        mock_git.assert_called_once_with(config)
                        mock_github.assert_called_once_with(config)
                        mock_ai.assert_called_once_with(config)
                        mock_pm.assert_called_once_with(config)

    def test_from_config_file(self) -> None:
        """Test loading settings from a configuration file."""
        with patch("pull_request_ai_agent.model.load_yaml_config") as mock_load:
            with patch("pull_request_ai_agent.model.BotSettings.serialize") as mock_serialize:
                mock_load.return_value = {"test": "config"}
                mock_serialize.return_value = MagicMock(spec=BotSettings)

                settings: BotSettings = BotSettings.from_config_file("/path/to/config.yaml")

                assert settings is mock_serialize.return_value
                mock_load.assert_called_once_with("/path/to/config.yaml")
                mock_serialize.assert_called_once_with({"test": "config"})

    def test_from_args_with_config_file(self) -> None:
        """Test loading settings from args with a config file."""
        # Create mock args
        args = MagicMock()
        args.config_file = "/path/to/config.yaml"

        # Create mock settings
        env_settings = MagicMock()
        config_settings = MagicMock()

        with patch("pull_request_ai_agent.model.BotSettings.from_env", return_value=env_settings):
            with patch("pull_request_ai_agent.model.BotSettings.from_config_file", return_value=config_settings):
                # Mock the validation methods to avoid ValueError with MagicMock objects
                with patch("pull_request_ai_agent.model.AiModuleClient") as mock_ai_client:
                    with patch("pull_request_ai_agent.model.ProjectManagementToolType") as mock_pm_tool_type:
                        settings: BotSettings = BotSettings.from_args(args)

                        # Verify settings were updated from config file
                        assert settings.git is config_settings.git
                        assert settings.github is config_settings.github
                        assert settings.ai is config_settings.ai
                        assert settings.pm_tool is config_settings.pm_tool

    def test_from_args_with_default_config_file(self) -> None:
        """Test loading settings from args with a default config file."""
        # Create mock args
        args = MagicMock()
        args.config_file = None
        args.repo_path = "/path/to/repo"

        # Create mock settings
        env_settings = MagicMock()
        config_settings = MagicMock()

        with patch("pull_request_ai_agent.model.BotSettings.from_env", return_value=env_settings):
            with patch(
                "pull_request_ai_agent.model.find_default_config_path", return_value="/path/to/default/config.yaml"
            ):
                with patch("pull_request_ai_agent.model.BotSettings.from_config_file", return_value=config_settings):
                    with patch("logging.Logger.info") as mock_info:
                        # Mock the validation methods to avoid ValueError with MagicMock objects
                        with patch("pull_request_ai_agent.model.AiModuleClient") as mock_ai_client:
                            with patch("pull_request_ai_agent.model.ProjectManagementToolType") as mock_pm_tool_type:
                                settings: BotSettings = BotSettings.from_args(args)

                                # Verify settings were updated from default config file
                                assert settings.git is config_settings.git
                                assert settings.github is config_settings.github
                                assert settings.ai is config_settings.ai
                                assert settings.pm_tool is config_settings.pm_tool

                                # Verify log message
                                mock_info.assert_called_once()

    def test_from_args_no_config_file(self) -> None:
        """Test loading settings from args without a config file."""
        # Create mock args
        args = MagicMock()
        args.config_file = None
        args.repo_path = "/path/to/repo"
        args.base_branch = "master"
        args.branch_name = "feature/test"
        args.github_token = "test-token"
        args.github_repo = "owner/repo"
        args.ai_client_type = "claude"
        args.ai_api_key = "test-ai-key"
        args.pm_tool_type = "jira"
        args.pm_tool_api_key = "test-pm-key"

        # Create mock settings
        env_settings = MagicMock()
        env_settings.git = MagicMock()
        env_settings.github = MagicMock()
        env_settings.ai = MagicMock()
        env_settings.pm_tool = MagicMock()

        with patch("pull_request_ai_agent.model.BotSettings.from_env", return_value=env_settings):
            with patch("pull_request_ai_agent.model.find_default_config_path", return_value=None):
                settings: BotSettings = BotSettings.from_args(args)

                # Verify settings were updated from args
                assert settings.git.repo_path == "/path/to/repo"
                assert settings.git.base_branch == "master"
                assert settings.git.branch_name == "feature/test"
                assert settings.github.token == "test-token"
                assert settings.github.repo == "owner/repo"
                assert settings.ai.api_key == "test-ai-key"
                assert settings.pm_tool.api_key == "test-pm-key"
