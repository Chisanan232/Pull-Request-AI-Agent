"""
Abstract base class for AI model clients.
This module provides a common interface for all AI API clients.
"""

import json
import logging
import os
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

import urllib3
from urllib3.response import HTTPResponse

# Configure logging
logger = logging.getLogger(__name__)

# Generic type for response objects
T = TypeVar("T")


class BaseAIClient(ABC, Generic[T]):
    """Abstract base class for AI client implementations."""

    # API defaults to be overridden by subclasses
    BASE_URL = ""
    DEFAULT_MODEL = ""
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 800

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        env_var_name: str = "",
    ):
        """
        Initialize the AI client with common parameters.

        Args:
            api_key: API key for the AI service
            model: Model to use
            temperature: Temperature setting for generation (0-1)
            max_tokens: Maximum tokens to generate in the response
            env_var_name: Environment variable name for the API key

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        logger.debug(f"Initializing base AI client with env var: {env_var_name}")

        # Set API key from parameter or environment variable
        self.api_key = api_key or os.environ.get(env_var_name, "")
        if not self.api_key:
            error_msg = (
                f"API key is required. Provide it as a parameter or set the {env_var_name} environment variable."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            logger.debug(f"API key found for {env_var_name}")

        # Set client parameters
        self.model = model or self.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        logger.debug(f"Base client settings: model={self.model}, temperature={temperature}, max_tokens={max_tokens}")

        # Initialize HTTP client
        self._http = urllib3.PoolManager()
        logger.debug("HTTP client initialized for API requests")

    @abstractmethod
    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the API request.

        Returns:
            Dictionary of HTTP headers.
        """

    @abstractmethod
    def _prepare_payload(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare the payload for the API request.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Dictionary payload for the API request.
        """

    @abstractmethod
    def _parse_response(self, response: HTTPResponse) -> T:
        """
        Parse the HTTP response from the API.

        Args:
            response: HTTP response from the API

        Returns:
            Parsed response object

        Raises:
            ValueError: If the response is invalid or contains an error
        """

    def _handle_error_response(self, response: HTTPResponse) -> str:
        """
        Extract error message from an error response.

        Args:
            response: HTTP response from the API

        Returns:
            Formatted error message
        """
        logger.debug(f"Handling error response with status code: {response.status}")
        error_message = f"API request failed with status {response.status}"

        try:
            response_body = response.data.decode("utf-8")
            logger.debug(
                f"Error response body: {response_body[:200]}..."
                if len(response_body) > 200
                else f"Error response body: {response_body}"
            )

            error_data = json.loads(response_body)
            if "error" in error_data:
                if "message" in error_data["error"]:
                    error_message = f"{error_message}: {error_data['error']['message']}"
                    logger.debug(f"Extracted error message: {error_data['error']['message']}")
                elif isinstance(error_data["error"], str):
                    error_message = f"{error_message}: {error_data['error']}"
                    logger.debug(f"Extracted error string: {error_data['error']}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse error response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error when parsing error response: {str(e)}")
            traceback.print_exc()

        logger.debug(f"Final error message: {error_message}")
        return error_message

    @abstractmethod
    def ask(self, prompt: str, system_message: Optional[str] = None) -> T:
        """
        Send a prompt to the AI model and get a response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Parsed response object with the model's response

        Raises:
            ValueError: If the API request fails or returns an error
        """

    @abstractmethod
    def get_content(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Get just the content string from the AI model's response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            The content string from the response

        Raises:
            ValueError: If the API request fails or returns an error
        """

    def _make_request(
        self, method: str, url: str, headers: Dict[str, str], payload: Dict[str, Any], service_name: str
    ) -> T:
        """
        Make an HTTP request to the API endpoint.

        Args:
            method: HTTP method (e.g., "POST", "GET")
            url: API endpoint URL
            headers: HTTP headers
            payload: Request payload
            service_name: Name of the AI service for error reporting

        Returns:
            Parsed response object

        Raises:
            ValueError: If the request fails
        """
        logger.debug(f"Making {method} request to {service_name} API")
        logger.debug(f"Request URL: {url.split('?')[0]}")  # Log URL without query parameters for security

        # Log headers (excluding authorization)
        safe_headers = {k: v for k, v in headers.items() if k.lower() != "authorization"}
        logger.debug(f"Request headers: {safe_headers}")

        # Log payload size but not content (for security/privacy)
        payload_size = len(json.dumps(payload))
        logger.debug(f"Request payload size: {payload_size} bytes")

        try:
            logger.debug(f"Sending request to {service_name} API")
            response = self._http.request(method, url, headers=headers, body=json.dumps(payload).encode("utf-8"))
            logger.debug(f"Received response with status code: {response.status}")

            if response.status >= 200 and response.status < 300:
                logger.info(f"Successful {service_name} API request with status: {response.status}")
            else:
                logger.warning(f"{service_name} API request returned non-success status: {response.status}")

            return self._parse_response(response)
        except urllib3.exceptions.HTTPError as e:
            error_msg = f"HTTP error in {service_name} API request: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to encode payload for {service_name} API: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Failed to call {service_name} API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
