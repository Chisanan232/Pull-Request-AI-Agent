"""
Client for interacting with Google's Gemini models.
Provides functionality to send prompts and receive responses.
"""

import json
import logging
from typing import Any, Dict, Optional


from pull_request_ai_agent.ai_bot._base.client import BaseAIClient
from pull_request_ai_agent.ai_bot.gemini.model import (
    GeminiCandidate,
    GeminiContent,
    GeminiPromptFeedback,
    GeminiResponse,
    GeminiUsage,
)

# Configure logging
logger = logging.getLogger(__name__)


class GeminiClient(BaseAIClient):
    """Client for interacting with Google's Gemini models."""

    # Gemini API defaults
    BASE_URL = "https://generativelanguage.googleapis.com/v1"
    DEFAULT_MODEL = "gemini-1.5-pro"
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
        Initialize the Gemini client.

        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY environment variable)
            model: Gemini model to use (defaults to DEFAULT_MODEL)
            temperature: Temperature setting for generation (0-1)
            max_tokens: Maximum tokens to generate in the response

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        logger.debug(f"Initializing Gemini client with model: {model or self.DEFAULT_MODEL}")
        try:
            super().__init__(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                env_var_name="GOOGLE_API_KEY",
            )
            logger.info(f"Successfully initialized Gemini client with model: {self.model}")
            logger.debug(f"Gemini client settings: temperature={temperature}, max_tokens={max_tokens}")
        except ValueError as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare HTTP headers for the Gemini API request.

        Returns:
            Dictionary of HTTP headers.
        """
        logger.debug("Preparing headers for Gemini API request")
        return {"Content-Type": "application/json"}

    def _prepare_payload(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare the payload for the Gemini API request.

        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message for context/instructions

        Returns:
            Dictionary payload for the API request.
        """
        logger.debug(f"Preparing payload for Gemini API request to model: {self.model}")

        # Log prompt length for debugging token usage
        prompt_length = len(prompt)
        logger.debug(f"Prompt length: {prompt_length} characters")

        contents = []

        # Add system message if provided
        if system_message:
            logger.debug(f"Including system message (length: {len(system_message)} characters)")
            contents.append({"role": "system", "parts": [{"text": system_message}]})
        else:
            logger.debug("No system message provided")

        # Add user prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "topK": 40,
                "topP": 0.95,
            },
            "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}],
        }

        logger.debug(f"Payload prepared with {len(contents)} content items and maxOutputTokens={self.max_tokens}")
        return payload

    def _parse_response(self, response) -> GeminiResponse:
        """
        Parse the HTTP response from the Google AI API.

        Args:
            response: HTTP response from the API or a GeminiResponse object

        Returns:
            Parsed GeminiResponse object

        Raises:
            ValueError: If the response is invalid or contains an error
        """
        logger.debug("Parsing response from Gemini API")

        # If we already have a GeminiResponse object, return it directly
        if isinstance(response, GeminiResponse):
            logger.debug("Response is already a GeminiResponse object")
            return response

        # Handle HTTP response
        if hasattr(response, "status"):
            if response.status != 200:
                error_message = self._handle_error_response(response)
                logger.error(f"Gemini API request failed: {error_message}")
                raise ValueError(error_message)

            try:
                data = json.loads(response.data.decode("utf-8"))
                logger.debug("Successfully parsed JSON response from Gemini API")

                # Process candidates
                api_candidates = data.get("candidates", [])
                candidates = []

                for idx, api_candidate in enumerate(api_candidates):
                    # Extract content from candidate
                    api_content = api_candidate.get("content", {})
                    text_content = ""

                    # Extract text from parts
                    for part in api_content.get("parts", []):
                        if "text" in part:
                            text_content += part.get("text", "")

                    # Create GeminiContent with correct parameters (no part_type)
                    content = GeminiContent(text=text_content, role=api_content.get("role", "model"))

                    # Create candidate
                    candidate = GeminiCandidate(
                        content=content,
                        finish_reason=api_candidate.get("finishReason", ""),
                        index=idx,
                        safety_ratings=api_candidate.get("safetyRatings", []),
                    )
                    candidates.append(candidate)

                # Extract prompt feedback
                prompt_feedback = GeminiPromptFeedback(
                    safety_ratings=data.get("promptFeedback", {}).get("safetyRatings", [])
                )

                # Extract usage data
                prompt_token_count = data.get("usageMetadata", {}).get("promptTokenCount", 0)
                total_token_count = data.get("usageMetadata", {}).get("totalTokenCount", 0)
                candidates_token_count = data.get("usageMetadata", {}).get("candidatesTokenCount", 0)

                usage = GeminiUsage(
                    prompt_token_count=prompt_token_count,
                    total_token_count=total_token_count,
                    candidates_token_count=candidates_token_count,
                )

                logger.debug(f"Gemini API token usage: prompt={prompt_token_count}, total={total_token_count}")

                return GeminiResponse(candidates=candidates, prompt_feedback=prompt_feedback, usage=usage)
            except Exception as e:
                error_msg = f"Failed to parse API response: {str(e)}"
                logger.error(f"Failed to parse Gemini API response: {str(e)}", exc_info=True)
                raise ValueError(error_msg)
        else:
            # Not a valid response type
            error_msg = f"Invalid response type: {type(response)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def ask(self, prompt: str, system_message: Optional[str] = None) -> GeminiResponse:
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
        logger.info(f"Sending prompt to Gemini model: {self.model}")
        logger.debug(f"Prompt begins with: {prompt[:50]}..." if len(prompt) > 50 else f"Prompt: {prompt}")

        endpoint = f"{self.BASE_URL}/models/{self.model}:generateContent"
        endpoint = f"{endpoint}?key={self.api_key}"
        logger.debug(f"Using Gemini API endpoint: {endpoint}")

        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, system_message)

        try:
            logger.debug("Making request to Gemini API")
            response = self._make_request(
                method="POST", url=endpoint, headers=headers, payload=payload, service_name="Gemini"
            )
            logger.info("Successfully received response from Gemini API")
            return self._parse_response(response)
        except ValueError as e:
            logger.error(f"Error in Gemini API request: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error in Gemini API request: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    def get_content(self, prompt: str, system_message: Optional[str] = None) -> str:
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
        logger.info("Requesting content from Gemini model")
        try:
            response = self.ask(prompt, system_message)

            if not response.candidates:
                error_msg = "Gemini response contains no candidates"
                logger.error(error_msg)
                raise IndexError(error_msg)

            content = response.candidates[0].content.text
            content_preview = content[:50] + "..." if len(content) > 50 else content
            logger.info(f"Successfully received content from Gemini, begins with: {content_preview}")
            logger.debug(f"Content length: {len(content)} characters")

            return content
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to get content from Gemini: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error getting content from Gemini: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
