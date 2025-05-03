import argparse
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from create_pr_bot.ai_bot import AiModuleClient
from create_pr_bot.model import (
    AISettings,
    BotSettings,
    GitHubSettings,
    GitSettings,
    ProjectManagementToolSettings, load_yaml_config, find_default_config_path,
)
from create_pr_bot.project_management_tool import ProjectManagementToolType


class TestLoadYamlConfig:
    """Tests for the load_yaml_config function."""

    def test_load_yaml_config_success(self):
        """Test loading a valid YAML configuration file."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as temp:
            temp.write("""
            git:
              repo_path: "/path/to/repo"
              base_branch: "main"
            github:
              token: "test-token"
              repo: "owner/repo"
            """)
            temp_path = temp.name

        try:
            config = load_yaml_config(temp_path)
            assert config["git"]["repo_path"] == "/path/to/repo"
            assert config["git"]["base_branch"] == "main"
            assert config["github"]["token"] == "test-token"
            assert config["github"]["repo"] == "owner/repo"
        finally:
            os.unlink(temp_path)

    def test_load_yaml_config_empty_file(self):
        """Test loading an empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as temp:
            temp.write("")
            temp_path = temp.name

        try:
            config = load_yaml_config(temp_path)
            assert config == {}
        finally:
            os.unlink(temp_path)

    def test_load_yaml_config_comments_only(self):
        """Test loading a YAML file with only comments."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as temp:
            temp.write("# This is a comment\n# Another comment")
            temp_path = temp.name

        try:
            config = load_yaml_config(temp_path)
            assert config == {}
        finally:
            os.unlink(temp_path)

    def test_load_yaml_config_file_not_found(self):
        """Test loading a non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            load_yaml_config("/path/to/nonexistent/file.yaml")

    def test_load_yaml_config_invalid_yaml(self):
        """Test loading an invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as temp:
            temp.write("invalid: yaml: :")
            temp_path = temp.name

        try:
            with pytest.raises(yaml.YAMLError):
                load_yaml_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_yaml_config_invalid_format(self):
        """Test loading a YAML file with invalid format (not a dictionary)."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as temp:
            temp.write("- item1\n- item2")
            temp_path = temp.name

        try:
            with pytest.raises(ValueError):
                load_yaml_config(temp_path)
        finally:
            os.unlink(temp_path)


class TestFindDefaultConfigPath:
    """Tests for the find_default_config_path function."""

    def test_find_default_config_path_yaml(self):
        """Test finding the default YAML configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .github directory
            github_dir = Path(temp_dir) / ".github"
            github_dir.mkdir()

            # Create pr-creator.yaml file
            config_path = github_dir / "pr-creator.yaml"
            config_path.touch()

            # Test finding the file
            result = find_default_config_path(temp_dir)
            assert result == config_path

    def test_find_default_config_path_yml(self):
        """Test finding the default YML configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .github directory
            github_dir = Path(temp_dir) / ".github"
            github_dir.mkdir()

            # Create pr-creator.yml file
            config_path = github_dir / "pr-creator.yml"
            config_path.touch()

            # Test finding the file
            result = find_default_config_path(temp_dir)
            assert result == config_path

    def test_find_default_config_path_both_extensions(self):
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
            result = find_default_config_path(temp_dir)
            assert result == yaml_path

    def test_find_default_config_path_not_found(self):
        """Test finding the default configuration file when it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .github directory without config file
            github_dir = Path(temp_dir) / ".github"
            github_dir.mkdir()

            # Test finding the file
            result = find_default_config_path(temp_dir)
            assert result is None

    def test_find_default_config_path_no_github_dir(self):
        """Test finding the default configuration file when .github directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test finding the file
            result = find_default_config_path(temp_dir)
            assert result is None


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

    def test_from_dict_empty(self):
        """Test loading settings from an empty dictionary."""
        settings = ProjectManagementToolSettings.from_dict({})
        assert settings.tool_type is None
        assert settings.api_key is None
        assert settings.organization_id is None
        assert settings.project_id is None
        assert settings.base_url is None
        assert settings.username is None

    def test_from_dict_with_values(self):
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

        settings = ProjectManagementToolSettings.from_dict(config)
        assert settings.tool_type == ProjectManagementToolType.CLICKUP
        assert settings.api_key == "test-api-key"
        assert settings.organization_id == "test-org-id"
        assert settings.project_id == "test-project-id"
        assert settings.base_url == "https://example.com"
        assert settings.username == "test-user"

    def test_from_dict_invalid_tool_type(self):
        """Test loading settings with invalid tool type."""
        config = {
            "project_management_tool": {
                "type": "invalid-type",
            }
        }

        with patch("logging.Logger.warning") as mock_warning:
            settings = ProjectManagementToolSettings.from_dict(config)
            assert settings.tool_type is None
            mock_warning.assert_called_once()


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

    def test_from_dict_empty(self):
        """Test loading settings from an empty dictionary."""
        settings = AISettings.from_dict({})
        assert settings.client_type == AiModuleClient.GPT
        assert settings.api_key is None

    def test_from_dict_with_values(self):
        """Test loading settings from a dictionary with values."""
        config = {
            "ai": {
                "client_type": "claude",
                "api_key": "test-api-key",
            }
        }

        settings = AISettings.from_dict(config)
        assert settings.client_type == AiModuleClient.CLAUDE
        assert settings.api_key == "test-api-key"

    def test_from_dict_invalid_client_type(self):
        """Test loading settings with invalid client type."""
        config = {
            "ai": {
                "client_type": "invalid-type",
            }
        }

        with patch("logging.Logger.warning") as mock_warning:
            settings = AISettings.from_dict(config)
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

    def test_from_dict_empty(self):
        """Test loading settings from an empty dictionary."""
        settings = GitHubSettings.from_dict({})
        assert settings.token is None
        assert settings.repo is None

    def test_from_dict_with_values(self):
        """Test loading settings from a dictionary with values."""
        config = {
            "github": {
                "token": "test-token",
                "repo": "owner/repo",
            }
        }

        settings = GitHubSettings.from_dict(config)
        assert settings.token == "test-token"
        assert settings.repo == "owner/repo"


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

    def test_from_dict_empty(self):
        """Test loading settings from an empty dictionary."""
        settings = GitSettings.from_dict({})
        assert settings.repo_path == "."
        assert settings.base_branch == "main"
        assert settings.branch_name is None

    def test_from_dict_with_values(self):
        """Test loading settings from a dictionary with values."""
        config = {
            "git": {
                "repo_path": "/path/to/repo",
                "base_branch": "master",
                "branch_name": "feature/test",
            }
        }

        settings = GitSettings.from_dict(config)
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

    def test_from_dict(self):
        """Test loading settings from a dictionary."""
        with patch("create_pr_bot.model.GitSettings.from_dict") as mock_git:
            with patch("create_pr_bot.model.GitHubSettings.from_dict") as mock_github:
                with patch("create_pr_bot.model.AISettings.from_dict") as mock_ai:
                    with patch("create_pr_bot.model.ProjectManagementToolSettings.from_dict") as mock_pm:
                        mock_git.return_value = "git_settings"
                        mock_github.return_value = "github_settings"
                        mock_ai.return_value = "ai_settings"
                        mock_pm.return_value = "pm_settings"

                        config = {"test": "config"}
                        settings = BotSettings.from_dict(config)

                        assert settings.git == "git_settings"
                        assert settings.github == "github_settings"
                        assert settings.ai == "ai_settings"
                        assert settings.pm_tool == "pm_settings"

                        mock_git.assert_called_once_with(config)
                        mock_github.assert_called_once_with(config)
                        mock_ai.assert_called_once_with(config)
                        mock_pm.assert_called_once_with(config)

    def test_from_config_file(self):
        """Test loading settings from a configuration file."""
        with patch("create_pr_bot.model.load_yaml_config") as mock_load:
            with patch("create_pr_bot.model.BotSettings.from_dict") as mock_from_dict:
                mock_load.return_value = {"test": "config"}
                mock_from_dict.return_value = "bot_settings"

                settings = BotSettings.from_config_file("/path/to/config.yaml")

                assert settings == "bot_settings"
                mock_load.assert_called_once_with("/path/to/config.yaml")
                mock_from_dict.assert_called_once_with({"test": "config"})

    def test_from_args_with_config_file(self):
        """Test loading settings from args with a config file."""
        # Create mock args
        args = MagicMock()
        args.config_file = "/path/to/config.yaml"
        args.ai_client_type = "gpt"
        args.pm_tool_type = "jira"

        # Create mock settings
        env_settings = MagicMock()
        config_settings = MagicMock()

        with patch("create_pr_bot.model.BotSettings.from_env", return_value=env_settings):
            with patch("create_pr_bot.model.BotSettings.from_config_file", return_value=config_settings):
                settings = BotSettings.from_args(args)

                # Verify settings were updated from config file
                assert settings.git == config_settings.git
                assert settings.github == config_settings.github
                assert settings.ai == config_settings.ai
                assert settings.pm_tool == config_settings.pm_tool

    def test_from_args_with_default_config_file(self):
        """Test loading settings from args with a default config file."""
        # Create mock args
        args = MagicMock()
        args.config_file = None
        args.repo_path = "/path/to/repo"
        args.ai_client_type = "gpt"
        args.pm_tool_type = "jira"

        # Create mock settings
        env_settings = MagicMock()
        config_settings = MagicMock()

        with patch("create_pr_bot.model.BotSettings.from_env", return_value=env_settings):
            with patch("create_pr_bot.model.find_default_config_path", return_value="/path/to/default/config.yaml"):
                with patch("create_pr_bot.model.BotSettings.from_config_file", return_value=config_settings):
                    with patch("logging.Logger.info") as mock_info:
                        settings = BotSettings.from_args(args)

                        # Verify settings were updated from default config file
                        assert settings.git == config_settings.git
                        assert settings.github == config_settings.github
                        assert settings.ai == config_settings.ai
                        assert settings.pm_tool == config_settings.pm_tool

                        # Verify log message
                        mock_info.assert_called_once()

    def test_from_args_no_config_file(self):
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

        with patch("create_pr_bot.model.BotSettings.from_env", return_value=env_settings):
            with patch("create_pr_bot.model.find_default_config_path", return_value=None):
                settings = BotSettings.from_args(args)

                # Verify settings were updated from args
                assert settings.git.repo_path == "/path/to/repo"
                assert settings.git.base_branch == "master"
                assert settings.git.branch_name == "feature/test"
                assert settings.github.token == "test-token"
                assert settings.github.repo == "owner/repo"
                assert settings.ai.api_key == "test-ai-key"
                assert settings.pm_tool.api_key == "test-pm-key"
