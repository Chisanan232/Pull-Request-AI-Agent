"""
Client for interacting with Anthropic's Claude models.
Provides functionality to send prompts and receive responses.
"""

import json
import logging
from typing import Any, Dict, Optional

from urllib3.response import HTTPResponse

from pull_request_ai_agent.ai_bot._base.client import BaseAIClient
from pull_request_ai_agent.ai_bot.claude.model import (
    ClaudeContent,
    ClaudeResponse,
    ClaudeUsage,
)

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
        logger.debug(f"Initializing Claude client with model: {model or self.DEFAULT_MODEL}")
        try:
            super().__init__(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                env_var_name="ANTHROPIC_API_KEY",
            )
            logger.info(f"Successfully initialized Claude client with model: {self.model}")
            logger.debug(f"Claude client settings: temperature={temperature}, max_tokens={max_tokens}")
        except ValueError as e:
            logger.error(f"Failed to initialize Claude client: {str(e)}")
            raise

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the Claude API request.

        Returns:
            Dictionary of HTTP headers.
        """
        logger.debug("Preparing headers for Claude API request")
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
        logger.debug(f"Preparing payload for Claude API request to model: {self.model}")
        
        # Log prompt length for debugging token usage
        prompt_length = len(prompt)
        logger.debug(f"Prompt length: {prompt_length} characters")
        
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }

        # Add system message if provided
        if system_message:
            logger.debug(f"Including system message (length: {len(system_message)} characters)")
            payload["system"] = system_message
        else:
            logger.debug("No system message provided")
            
        logger.debug(f"Payload prepared for Claude API request with max_tokens={self.max_tokens}")
        return payload

    def _parse_response(self, response: HTTPResponse) -> ClaudeResponse:
        """
        Parse the HTTP response from the Anthropic API.

        Args:
            response: HTTP response from the API

        Returns:
            Parsed ClaudeResponse object

        Raises:
            ValueError: If the response is invalid or contains an error
        """
        logger.debug(f"Parsing Claude API response with status code: {response.status}")
        
        if response.status != 200:
            error_message = self._handle_error_response(response)
            logger.error(f"Claude API request failed: {error_message}")
            raise ValueError(error_message)

        try:
            data = json.loads(response.data.decode("utf-8"))
            logger.debug("Successfully parsed JSON response from Claude API")
            
            # Create content blocks
            content_blocks = []
            for block in data.get("content", []):
                content_blocks.append(
                    ClaudeContent(
                        type=block.get("type", ""),
                        text=block.get("text", ""),
                    )
                )
            
            # Extract token usage
            input_tokens = data.get("usage", {}).get("input_tokens", 0)
            output_tokens = data.get("usage", {}).get("output_tokens", 0)
            
            logger.info(f"Claude API token usage: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
            
            # Log warning if output is large relative to max tokens
            if output_tokens > 0.8 * self.max_tokens:
                logger.warning(f"High token usage: {output_tokens} output tokens (80%+ of max_tokens setting)")
            
            stop_reason = data.get("stop_reason", "")
            # Log stop reason which can be important for debugging
            if stop_reason == "max_tokens":
                logger.warning(f"Claude response was cut off due to token limit (stop_reason: {stop_reason})")
            elif stop_reason != "end_turn":
                logger.info(f"Claude response stop reason: {stop_reason}")
            
            # Create the usage object
            usage = ClaudeUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            return ClaudeResponse(
                id=data.get("id", ""),
                type=data.get("type", ""),
                role=data.get("role", ""),
                content=content_blocks,
                model=data.get("model", ""),
                stop_reason=stop_reason,
                stop_sequence=data.get("stop_sequence", None),
                usage=usage,
            )
        except Exception as e:
            error_msg = f"Failed to parse API response: {str(e)}"
            logger.error(f"Failed to parse Claude API response: {str(e)}", exc_info=True)
            raise ValueError(error_msg)

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
        logger.info(f"Sending prompt to Claude model: {self.model}")
        logger.debug(f"Prompt begins with: {prompt[:50]}..." if len(prompt) > 50 else f"Prompt: {prompt}")
        
        endpoint = f"{self.BASE_URL}/messages"
        logger.debug(f"Using Claude API endpoint: {endpoint}")
        
        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, system_message)
        
        try:
            logger.debug("Making request to Claude API")
            response = self._make_request(method="POST", url=endpoint, headers=headers, payload=payload, service_name="Claude")
            logger.info("Successfully received response from Claude API")
            return response
        except ValueError as e:
            logger.error(f"Error in Claude API request: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error in Claude API request: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

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
        logger.info("Requesting content from Claude model")
        try:
            response = self.ask(prompt, system_message)
            
            if not response.content:
                error_msg = "Claude response contains no content"
                logger.error(error_msg)
                raise IndexError(error_msg)
                
            # Get text content from the first content item
            content = response.content[0].text
            content_preview = content[:50] + "..." if len(content) > 50 else content
            logger.info(f"Successfully received content from Claude, begins with: {content_preview}")
            logger.debug(f"Content length: {len(content)} characters")
            
            return content
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to get content from Claude: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error getting content from Claude: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
