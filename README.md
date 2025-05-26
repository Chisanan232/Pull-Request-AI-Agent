# Pull-Request-AI-Agent

[![PyPI](https://img.shields.io/pypi/v/pull-request-ai-agent?color=%23099cec&amp;label=PyPI&amp;logo=pypi&amp;logoColor=white)](https://pypi.org/project/pull-request-ai-agent)
[![Release](https://img.shields.io/github/release/Chisanan232/Pull-Request-AI-Agent.svg?label=Release&logo=github)](https://github.com/Chisanan232/Pull-Request-AI-Agent/releases)
[![CI](https://github.com/Chisanan232/Pull-Request-AI-Agent/actions/workflows/ci.yaml/badge.svg)](https://github.com/Chisanan232/Pull-Request-AI-Agent/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/Chisanan232/Pull-Request-AI-Agent/graph/badge.svg?token=GJYBfInkzX)](https://codecov.io/gh/Chisanan232/Pull-Request-AI-Agent)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Chisanan232/Pull-Request-AI-Agent/master.svg)](https://results.pre-commit.ci/latest/github/Chisanan232/Pull-Request-AI-Agent/master)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Chisanan232_Pull-Request-AI-Agent&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Chisanan232_Pull-Request-AI-Agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🤖 A bot helps developers open pull request with details.

[Overview](#overview) | [Python versions support](#Python-versions-support) | [Quickly Start](#quickly-start) | [Configuration](#configuration) | [Documentation](#documentation)
<hr>

## Overview

🚧 Clear brief of your lib


## Python versions support

🚧 The required Python versions of this library

[![Supported Versions](https://img.shields.io/pypi/pyversions/pull-request-ai-agent.svg?logo=python&logoColor=FBE072)](https://pypi.org/project/pull-request-ai-agent)


## Quickly Start

🚧 The details of quickly start as simple demonstration for users

## Configuration

Pull request AI agent can be configured in multiple ways:

1. **Command Line Arguments**: Pass options directly when running the bot
2. **Environment Variables**: Set options using environment variables
3. **Configuration File**: Use a YAML configuration file

### Configuration File

You can configure the bot using a YAML configuration file. By default, the bot will look for a configuration file at `.github/pr-creator.yaml` or `.github/pr-creator.yml` in your repository.

You can also specify a custom configuration file path using the `--config` command line argument:

```bash
poetry run python -m pr-ai-agent --config /path/to/your/config.yaml
```

#### Example Configuration File

```yaml
# Git settings
git:
  repo_path: "."
  base_branch: "main"
  # branch_name: "feature/my-feature"  # Uncomment to specify a branch name

# GitHub settings
github:
  # token: "your-github-token"  # It's recommended to use environment variables for tokens
  repo: "owner/repo"

# AI settings
ai:
  client_type: "claude"  # Options: gpt, claude, gemini
  # api_key: "your-api-key"  # It's recommended to use environment variables for API keys

# Project management tool settings
project_management_tool:
  type: "clickup"  # Options: clickup, jira
  # api_key: "your-api-key"  # It's recommended to use environment variables for API keys
  # organization_id: "your-org-id"
  # project_id: "your-project-id"
  # base_url: "https://api.example.com"
  # username: "your-username"
```

### Configuration Priority

The bot uses the following priority order when determining configuration values:

1. Command line arguments (highest priority)
2. Configuration file
3. Environment variables (lowest priority)

This means that command line arguments will override values from the configuration file, which will override environment variables.

## Documentation

🚧 The details of documentation ...


## Coding style and following rules

**_<your lib name>_** follows coding styles **_black_** and **_PyLint_** to control code quality.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)


## Downloading state

🚧 The download state for your library

[![Downloads](https://pepy.tech/badge/pull-request-ai-agent)](https://pepy.tech/project/pull-request-ai-agent)
[![Downloads](https://pepy.tech/badge/pull-request-ai-agent/month)](https://pepy.tech/project/pull-request-ai-agent)

## License

[MIT License](./LICENSE)
