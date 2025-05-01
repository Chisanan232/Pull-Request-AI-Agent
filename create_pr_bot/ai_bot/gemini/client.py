"""
Client for interacting with Google's Gemini models.
Provides functionality to send prompts and receive responses.
"""

import os
import json
import logging
from typing import Dict, Optional, Any

import urllib3
from urllib3.response import HTTPResponse

from create_pr_bot.ai_bot.gemini.model import GeminiContent, GeminiCandidate, GeminiPromptFeedback, GeminiUsage, \
    GeminiResponse

# Configure logging
logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google's Gemini models."""

    # Gemini API defaults
    BASE_URL = "https://generativelanguage.googleapis.com/v1"
    DEFAULT_MODEL = "gemini-1.5-pro"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 800

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 temperature: float = DEFAULT_TEMPERATURE,
                 max_tokens: int = DEFAULT_MAX_TOKENS):
        """
        Initialize the Gemini client.

        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY environment variable)
            model: Gemini model to use (defaults to DEFAULT_MODEL)
            temperature: Temperature setting for generation (0-1)
            max_tokens: Maximum tokens to generate in the response

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Provide it as a parameter or set the GOOGLE_API_KEY environment variable.")

        self.model = model or self.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._http = urllib3.PoolManager()

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the Gemini API request.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "Content-Type": "application/json"
        }

    def _prepare_payload(self, prompt: str,
                         system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare the payload for the Gemini API request.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Dictionary payload for the API request.
        """
        contents = []

        # Add system message if provided
        if system_message:
            contents.append({
                "role": "system",
                "parts": [{"text": system_message}]
            })

        # Add user prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]

        })

        return {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "topK": 40,
                "topP": 0.95
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }

    def _parse_response(self, response: HTTPResponse) -> GeminiResponse:
        """
        Parse the HTTP response from the Gemini API.

        Args:
            response: HTTP response from the API

        Returns:
            Parsed GeminiResponse object

        Raises:
            ValueError: If the response is invalid or contains an error
        """
        if response.status != 200:
            error_message = f"API request failed with status {response.status}"
            try:
                error_data = json.loads(response.data.decode('utf-8'))
                if 'error' in error_data:
                    error_message = f"{error_message}: {error_data['error']['message']}"
            except Exception:
                pass
            raise ValueError(error_message)

        try:
            data = json.loads(response.data.decode('utf-8'))

            # Create candidates
            candidates = []
            for candidate_data in data.get('candidates', []):
                content_data = candidate_data.get('content', {})
                parts = content_data.get('parts', [{}])[0]

                content = GeminiContent(
                    text=parts.get('text', ''),
                    role=content_data.get('role', 'model')
                )

                candidates.append(GeminiCandidate(
                    content=content,
                    finish_reason=candidate_data.get('finishReason', ''),
                    index=candidate_data.get('index', 0),
                    safety_ratings=candidate_data.get('safetyRatings', [])
                ))

            # Create prompt feedback
            prompt_feedback = GeminiPromptFeedback(
                safety_ratings=data.get('promptFeedback', {}).get('safetyRatings', [])
            )

            # Create usage data
            usage_data = data.get('usageMetadata', {})
            usage = GeminiUsage(
                prompt_token_count=usage_data.get('promptTokenCount', 0),
                candidates_token_count=usage_data.get('candidatesTokenCount', 0),
                total_token_count=usage_data.get('totalTokenCount', 0)
            )

            # Create and return the full response object
            return GeminiResponse(
                candidates=candidates,
                prompt_feedback=prompt_feedback,
                usage=usage
            )
        except Exception as e:
            raise ValueError(f"Failed to parse API response: {str(e)}")

    def ask(self, prompt: str,
            system_message: Optional[str] = None) -> GeminiResponse:
        """
        Send a prompt to the Gemini model and get a response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Parsed GeminiResponse object with the model's response

        Raises:
            ValueError: If the API request fails or returns an error
        """
        endpoint = f"{self.BASE_URL}/models/{self.model}:generateContent"
        endpoint = f"{endpoint}?key={self.api_key}"
        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, system_message)

        try:
            response = self._http.request(
                "POST",
                endpoint,
                headers=headers,
                body=json.dumps(payload).encode('utf-8')
            )
            return self._parse_response(response)
        except Exception as e:
            raise ValueError(f"Failed to call Gemini API: {str(e)}")

    def get_content(self, prompt: str,
                    system_message: Optional[str] = None) -> str:
        """
        Get just the content string from the Gemini model's response.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            The content string from the first candidate in the Gemini response

        Raises:
            ValueError: If the API request fails or returns an error
            IndexError: If the response contains no candidates
        """
        response = self.ask(prompt, system_message)
        if not response.candidates:
            raise IndexError("Gemini response contains no candidates")
        return response.candidates[0].content.text
