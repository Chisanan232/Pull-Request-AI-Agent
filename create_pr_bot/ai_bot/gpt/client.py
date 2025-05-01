"""
Client for interacting with OpenAI's GPT models.
Provides functionality to send prompts and receive responses.
"""

import json
import logging
from typing import Any, Dict, Optional

from urllib3.response import HTTPResponse

from create_pr_bot.ai_bot._base.client import BaseAIClient
from create_pr_bot.ai_bot.gpt.model import GPTChoice, GPTMessage, GPTResponse, GPTUsage

# Configure logging
logger = logging.getLogger(__name__)


class GPTClient(BaseAIClient):
    """Client for interacting with OpenAI's GPT models."""

    # GPT API defaults
    BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 800

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize the GPT client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY environment variable)
            model: GPT model to use (defaults to DEFAULT_MODEL)
            temperature: Temperature setting for generation (0-1)
            max_tokens: Maximum tokens to generate in the response

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        super().__init__(
            api_key=api_key, model=model, temperature=temperature, max_tokens=max_tokens, env_var_name="OPENAI_API_KEY"
        )

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the OpenAI API request.

        Returns:
            Dictionary of HTTP headers.
        """
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

    def _prepare_payload(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare the payload for the OpenAI API request.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Dictionary payload for the API request.
        """
        messages = []

        # Add system message if provided
        if system_message:
            messages.append({"role": "system", "content": system_message})

        # Add user prompt
        messages.append({"role": "user", "content": prompt})

        return {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def _parse_response(self, response: HTTPResponse) -> GPTResponse:
        """
        Parse the HTTP response from the OpenAI API.

        Args:
            response: HTTP response from the API

        Returns:
            Parsed GPTResponse object

        Raises:
            ValueError: If the response is invalid or contains an error
        """
        if response.status != 200:
            error_message = f"API request failed with status {response.status}"
            try:
                error_data = json.loads(response.data.decode("utf-8"))
                if "error" in error_data and "message" in error_data["error"]:
                    error_message = f"{error_message}: {error_data['error']['message']}"
            except Exception:
                pass
            raise ValueError(error_message)

        try:
            data = json.loads(response.data.decode("utf-8"))

            # Create GPTMessage objects for each choice's message
            choices = []
            for choice in data.get("choices", []):
                message_data = choice.get("message", {})
                message = GPTMessage(role=message_data.get("role", ""), content=message_data.get("content", ""))
                choices.append(
                    GPTChoice(
                        index=choice.get("index", 0), message=message, finish_reason=choice.get("finish_reason", "")
                    )
                )

            # Create usage data
            usage_data = data.get("usage", {})
            usage = GPTUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Create and return the full response object
            return GPTResponse(
                id=data.get("id", ""),
                object=data.get("object", ""),
                created=data.get("created", 0),
                model=data.get("model", ""),
                choices=choices,
                usage=usage,
            )
        except Exception as e:
            raise ValueError(f"Failed to parse API response: {str(e)}")

    def ask(self, prompt: str, system_message: Optional[str] = None) -> GPTResponse:
        """
        Send a prompt to the GPT model and get a response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Parsed GPTResponse object with the model's response

        Raises:
            ValueError: If the API request fails or returns an error
        """
        endpoint = f"{self.BASE_URL}/chat/completions"
        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, system_message)

        return self._make_request(method="POST", url=endpoint, headers=headers, payload=payload, service_name="GPT")

    def get_content(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Get just the content string from the GPT model's response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            The content string from the first choice in the GPT response

        Raises:
            ValueError: If the API request fails or returns an error
            IndexError: If the response contains no choices
        """
        response = self.ask(prompt, system_message)
        if not response.choices:
            raise IndexError("GPT response contains no choices")
        return response.choices[0].message.content
