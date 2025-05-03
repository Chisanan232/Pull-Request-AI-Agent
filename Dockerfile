FROM python:3.12-slim

LABEL maintainer="Chisanan232 <chi10211201@cycu.org.tw>"
LABEL org.opencontainers.image.source="https://github.com/Chisanan232/Create-PR-Bot"
LABEL org.opencontainers.image.description="Create PR Bot - Automate pull request creation with AI-generated content"
LABEL org.opencontainers.image.licenses="MIT"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Install git and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
#RUN curl -sSL https://install.python-poetry.org | python3 -
#ENV PATH="$POETRY_HOME/bin:$PATH"
RUN pip install -U pip
RUN pip install -U poetry
RUN poetry --version

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install dependencies
RUN poetry install --no-interaction --without=dev
# # It already in a virtual runtime environment --- a Docker container, so it doesn't need to create another independent
# # virtual enviroment again in Docker virtual environment
RUN poetry config virtualenvs.create false

# Create a volume for configuration
VOLUME ["/config"]

# Create entrypoint script
RUN echo '#!/bin/bash\n\
\n\
# Build command arguments based on environment variables\n\
ARGS=""\n\
\n\
# Add config file if provided\n\
if [ ! -z "$CREATE_PR_BOT_CONFIG_FILE" ]; then\n\
  ARGS="$ARGS --config $CREATE_PR_BOT_CONFIG_FILE"\n\
fi\n\
\n\
# Add git settings if provided\n\
if [ ! -z "$CREATE_PR_BOT_GIT_REPO_PATH" ]; then\n\
  ARGS="$ARGS --repo-path $CREATE_PR_BOT_GIT_REPO_PATH"\n\
fi\n\
\n\
if [ ! -z "$CREATE_PR_BOT_GIT_BASE_BRANCH" ]; then\n\
  ARGS="$ARGS --base-branch $CREATE_PR_BOT_GIT_BASE_BRANCH"\n\
fi\n\
\n\
if [ ! -z "$CREATE_PR_BOT_GIT_BRANCH_NAME" ]; then\n\
  ARGS="$ARGS --branch-name $CREATE_PR_BOT_GIT_BRANCH_NAME"\n\
fi\n\
\n\
# Add GitHub settings if provided\n\
if [ ! -z "$CREATE_PR_BOT_GITHUB_TOKEN" ]; then\n\
  ARGS="$ARGS --github-token $CREATE_PR_BOT_GITHUB_TOKEN"\n\
fi\n\
\n\
if [ ! -z "$CREATE_PR_BOT_GITHUB_REPO" ]; then\n\
  ARGS="$ARGS --github-repo $CREATE_PR_BOT_GITHUB_REPO"\n\
fi\n\
\n\
# Add AI settings if provided\n\
if [ ! -z "$CREATE_PR_BOT_AI_CLIENT_TYPE" ]; then\n\
  ARGS="$ARGS --ai-client-type $CREATE_PR_BOT_AI_CLIENT_TYPE"\n\
fi\n\
\n\
if [ ! -z "$CREATE_PR_BOT_AI_API_KEY" ]; then\n\
  ARGS="$ARGS --ai-api-key $CREATE_PR_BOT_AI_API_KEY"\n\
fi\n\
\n\
# Add PM tool settings if provided\n\
if [ ! -z "$CREATE_PR_BOT_PM_TOOL_TYPE" ]; then\n\
  ARGS="$ARGS --pm-tool-type $CREATE_PR_BOT_PM_TOOL_TYPE"\n\
fi\n\
\n\
if [ ! -z "$CREATE_PR_BOT_PM_TOOL_API_KEY" ]; then\n\
  ARGS="$ARGS --pm-tool-api-key $CREATE_PR_BOT_PM_TOOL_API_KEY"\n\
fi\n\
\n\
# Run the bot with the constructed arguments\n\
# Note: Other PM tool settings (organization_id, project_id, base_url, username)\n\
# will be picked up from environment variables by BotSettings.from_env()\n\
poetry run create-pr-bot $ARGS\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# # For debug
#ENTRYPOINT ["tail", "-f", "/dev/null"]
