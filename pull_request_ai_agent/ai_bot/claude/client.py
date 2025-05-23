"""
Client for interacting with Anthropic's Claude models.
Provides functionality to send prompts and receive responses.
"""

import json
import logging
from typing import Any, Dict, Optional

from urllib3.response import HTTPResponse

from pull_request_ai_agent.ai_bot._base.client import BaseAIClient
from pull_request_ai_agent.ai_bot.claude.model import ClaudeContent, ClaudeResponse, ClaudeUsage

# Configure logging
logger = logging.getLogger(__name__)


class ClaudeClient(BaseAIClient):
    """Client for interacting with Anthropic's Claude models."""

    # Claude API defaults
    BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-3-opus-20240229"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 800
    API_VERSION = "2023-06-01"  # Anthropic API version

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize the Claude client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)
            model: Claude model to use (defaults to DEFAULT_MODEL)
            temperature: Temperature setting for generation (0-1)
            max_tokens: Maximum tokens to generate in the response

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        super().__init__(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            env_var_name="ANTHROPIC_API_KEY",
        )

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the Claude API request.

        Returns:
            Dictionary of HTTP headers.
        """
        assert self.api_key
        return {"Content-Type": "application/json", "x-api-key": self.api_key, "anthropic-version": self.API_VERSION}

    def _prepare_payload(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare the payload for the Claude API request.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Dictionary payload for the API request.
        """
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }

        # Add system message if provided
        if system_message:
            payload["system"] = system_message

        return payload

    def _parse_response(self, response: HTTPResponse) -> ClaudeResponse:
        """
        Parse the HTTP response from the Claude API.

        Args:
            response: HTTP response from the API

        Returns:
            Parsed ClaudeResponse object

        Raises:
            ValueError: If the response is invalid or contains an error
        """
        if response.status != 200:
            raise ValueError(self._handle_error_response(response))

        try:
            data = json.loads(response.data.decode("utf-8"))

            # Create ClaudeContent objects for each content item
            content_items = []
            for item in data.get("content", []):
                content_items.append(ClaudeContent(type=item.get("type", ""), text=item.get("text", "")))

            # Create usage data
            usage_data = data.get("usage", {})
            usage = ClaudeUsage(
                input_tokens=usage_data.get("input_tokens", 0), output_tokens=usage_data.get("output_tokens", 0)
            )

            # Create and return the full response object
            return ClaudeResponse(
                id=data.get("id", ""),
                type=data.get("type", ""),
                role=data.get("role", ""),
                content=content_items,
                model=data.get("model", ""),
                stop_reason=data.get("stop_reason"),
                stop_sequence=data.get("stop_sequence"),
                usage=usage,
            )
        except Exception as e:
            raise ValueError(f"Failed to parse API response: {str(e)}")

    def ask(self, prompt: str, system_message: Optional[str] = None) -> ClaudeResponse:
        """
        Send a prompt to the Claude model and get a response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Parsed ClaudeResponse object with the model's response

        Raises:
            ValueError: If the API request fails or returns an error
        """
        endpoint = f"{self.BASE_URL}/messages"
        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, system_message)

        return self._make_request(method="POST", url=endpoint, headers=headers, payload=payload, service_name="Claude")

    def get_content(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Get just the content string from the Claude model's response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            The combined content string from all text elements in the Claude response

        Raises:
            ValueError: If the API request fails or returns an error
            IndexError: If the response contains no content
        """
        response = self.ask(prompt, system_message)
        if not response.content:
            raise IndexError("Claude response contains no content")

        # Return the text from the first content item (typically there's only one)
        return response.content[0].text
