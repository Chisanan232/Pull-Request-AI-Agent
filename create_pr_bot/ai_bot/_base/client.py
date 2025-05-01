"""
Abstract base class for AI model clients.
This module provides a common interface for all AI API clients.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, TypeVar, Generic

import urllib3
from urllib3.response import HTTPResponse

# Configure logging
logger = logging.getLogger(__name__)

# Generic type for response objects
T = TypeVar('T')


class BaseAIClient(ABC, Generic[T]):
    """Abstract base class for AI client implementations."""

    # API defaults to be overridden by subclasses
    BASE_URL = ""
    DEFAULT_MODEL = ""
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 800

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 temperature: float = DEFAULT_TEMPERATURE,
                 max_tokens: int = DEFAULT_MAX_TOKENS,
                 env_var_name: str = ""):
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
        self.api_key = api_key or os.environ.get(env_var_name, "")
        if not self.api_key:
            raise ValueError(f"API key is required. Provide it as a parameter or set the {env_var_name} environment variable.")

        self.model = model or self.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._http = urllib3.PoolManager()

    @abstractmethod
    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the API request.

        Returns:
            Dictionary of HTTP headers.
        """
        pass

    @abstractmethod
    def _prepare_payload(self, prompt: str,
                         system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare the payload for the API request.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Dictionary payload for the API request.
        """
        pass

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
        pass

    def _handle_error_response(self, response: HTTPResponse) -> str:
        """
        Extract error message from an error response.

        Args:
            response: HTTP response from the API

        Returns:
            Formatted error message
        """
        error_message = f"API request failed with status {response.status}"
        try:
            error_data = json.loads(response.data.decode('utf-8'))
            if 'error' in error_data:
                if 'message' in error_data['error']:
                    error_message = f"{error_message}: {error_data['error']['message']}"
                elif isinstance(error_data['error'], str):
                    error_message = f"{error_message}: {error_data['error']}"
        except Exception:
            pass
        return error_message

    @abstractmethod
    def ask(self, prompt: str,
            system_message: Optional[str] = None) -> T:
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
        pass

    @abstractmethod
    def get_content(self, prompt: str,
                    system_message: Optional[str] = None) -> str:
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
        pass

    def _make_request(self, method: str, url: str, headers: Dict[str, str],
                      payload: Dict[str, Any], service_name: str) -> T:
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
        try:
            response = self._http.request(
                method,
                url,
                headers=headers,
                body=json.dumps(payload).encode('utf-8')
            )
            return self._parse_response(response)
        except Exception as e:
            raise ValueError(f"Failed to call {service_name} API: {str(e)}")
