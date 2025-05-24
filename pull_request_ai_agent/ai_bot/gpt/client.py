"""
Client for interacting with OpenAI's GPT models.
Provides functionality to send prompts and receive responses.
"""

import json
import logging
from typing import Any, Dict, Optional

from urllib3.response import HTTPResponse

from pull_request_ai_agent.ai_bot._base.client import BaseAIClient
from pull_request_ai_agent.ai_bot.gpt.model import (
    GPTChoice,
    GPTMessage,
    GPTResponse,
    GPTUsage,
)

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
        logger.debug(f"Initializing GPT client with model: {model or self.DEFAULT_MODEL}")
        try:
            super().__init__(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                env_var_name="OPENAI_API_KEY",
            )
            logger.info(f"Successfully initialized GPT client with model: {self.model}")
            logger.debug(f"GPT client settings: temperature={temperature}, max_tokens={max_tokens}")
        except ValueError as e:
            logger.error(f"Failed to initialize GPT client: {str(e)}")
            raise

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the OpenAI API request.

        Returns:
            Dictionary of HTTP headers.
        """
        logger.debug("Preparing headers for GPT API request")
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
        logger.debug(f"Preparing payload for GPT API request to model: {self.model}")

        # Log prompt length for debugging token usage
        prompt_length = len(prompt)
        logger.debug(f"Prompt length: {prompt_length} characters")

        messages = []

        # Add system message if provided
        if system_message:
            logger.debug(f"Including system message (length: {len(system_message)} characters)")
            messages.append({"role": "system", "content": system_message})
        else:
            logger.debug("No system message provided")

        # Add user prompt
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        logger.debug(f"Payload prepared with {len(messages)} message(s)")
        return payload

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
        logger.debug(f"Parsing GPT API response with status code: {response.status}")

        if response.status != 200:
            error_message = self._handle_error_response(response)
            logger.error(f"GPT API request failed: {error_message}")
            raise ValueError(error_message)

        try:
            data = json.loads(response.data.decode("utf-8"))
            logger.debug("Successfully parsed JSON response from GPT API")

            # Extract usage data
            usage_data = data.get("usage", {})
            prompt_tokens = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)
            total_tokens = usage_data.get("total_tokens", 0)

            logger.info(
                f"GPT API token usage: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total"
            )

            # Log warning if getting close to context window limits
            if completion_tokens > 0.8 * self.max_tokens:
                logger.warning(f"High token usage: {completion_tokens} completion tokens (80%+ of max_tokens setting)")

            usage = GPTUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

            # Extract choices
            choices = []
            for choice_data in data.get("choices", []):
                message_data = choice_data.get("message", {})
                message = GPTMessage(
                    role=message_data.get("role", "assistant"),
                    content=message_data.get("content", ""),
                )

                finish_reason = choice_data.get("finish_reason", "")

                # Log finish reason which can be important for debugging
                if finish_reason == "length":
                    logger.warning(f"GPT response was cut off due to token limit (finish_reason: {finish_reason})")

                choice = GPTChoice(
                    index=choice_data.get("index", 0),
                    message=message,
                    finish_reason=finish_reason,
                )
                choices.append(choice)

            logger.debug(f"Parsed {len(choices)} choices from GPT response")

            return GPTResponse(
                id=data.get("id", ""),
                object=data.get("object", ""),
                created=data.get("created", 0),
                model=data.get("model", ""),
                choices=choices,
                usage=usage,
            )
        except Exception as e:
            error_msg = f"Failed to parse API response: {str(e)}"
            logger.error(f"Failed to parse GPT API response: {str(e)}", exc_info=True)
            raise ValueError(error_msg)

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
        logger.info(f"Sending prompt to GPT model: {self.model}")
        logger.debug(f"Prompt begins with: {prompt[:50]}..." if len(prompt) > 50 else f"Prompt: {prompt}")

        endpoint = f"{self.BASE_URL}/chat/completions"
        logger.debug(f"Using GPT API endpoint: {endpoint}")

        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, system_message)

        try:
            logger.debug("Making request to GPT API")
            response = self._make_request(
                method="POST", url=endpoint, headers=headers, payload=payload, service_name="GPT"
            )
            logger.info("Successfully received response from GPT API")
            return response
        except ValueError as e:
            logger.error(f"Error in GPT API request: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error in GPT API request: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

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
        logger.info("Requesting content from GPT model")
        try:
            response = self.ask(prompt, system_message)

            if not response.choices:
                error_msg = "GPT response contains no choices"
                logger.error(error_msg)
                raise IndexError(error_msg)

            content = response.choices[0].message.content
            content_preview = content[:50] + "..." if len(content) > 50 else content
            logger.info(f"Successfully received content from GPT, begins with: {content_preview}")
            logger.debug(f"Content length: {len(content)} characters")

            return content
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to get content from GPT: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error getting content from GPT: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
