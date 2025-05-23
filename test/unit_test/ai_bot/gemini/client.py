"""
Unit tests for the Gemini client functionality.
"""

import json
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from urllib3.response import HTTPResponse

from pull_request_ai_agent.ai_bot.gemini.client import GeminiClient
from pull_request_ai_agent.ai_bot.gemini.model import (
    GeminiCandidate,
    GeminiContent,
    GeminiPromptFeedback,
    GeminiResponse,
    GeminiUsage,
)


@pytest.fixture
def mock_api_key() -> str:
    """Fixture for a mock API key."""
    return "mock-api-key"


@pytest.fixture
def sample_prompt() -> str:
    """Fixture for a sample prompt."""
    return "What is the capital of France?"


@pytest.fixture
def sample_system_message() -> str:
    """Fixture for a sample system message."""
    return "You are a helpful assistant."


@pytest.fixture
def sample_gemini_response_data() -> Dict[str, Any]:
    """Fixture for sample Gemini response data."""
    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": "The capital of France is Paris."}]},
                "finishReason": "STOP",
                "index": 0,
                "safetyRatings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "NEGLIGIBLE"}],
            }
        ],
        "promptFeedback": {
            "safetyRatings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "NEGLIGIBLE"}]
        },
        "usageMetadata": {"promptTokenCount": 13, "candidatesTokenCount": 8, "totalTokenCount": 21},
    }


@pytest.fixture
def sample_gemini_response(sample_gemini_response_data) -> GeminiResponse:
    """Fixture for a sample GeminiResponse object."""
    candidate_data = sample_gemini_response_data["candidates"][0]
    content_data = candidate_data["content"]

    content = GeminiContent(text=content_data["parts"][0]["text"], role=content_data["role"])

    candidate = GeminiCandidate(
        content=content,
        finish_reason=candidate_data["finishReason"],
        index=candidate_data["index"],
        safety_ratings=candidate_data["safetyRatings"],
    )

    prompt_feedback = GeminiPromptFeedback(
        safety_ratings=sample_gemini_response_data["promptFeedback"]["safetyRatings"]
    )

    usage_data = sample_gemini_response_data["usageMetadata"]
    usage = GeminiUsage(
        prompt_token_count=usage_data["promptTokenCount"],
        candidates_token_count=usage_data["candidatesTokenCount"],
        total_token_count=usage_data["totalTokenCount"],
    )

    return GeminiResponse(candidates=[candidate], prompt_feedback=prompt_feedback, usage=usage)


@pytest.fixture
def gemini_client(mock_api_key) -> GeminiClient:
    """Fixture for a GeminiClient instance with a mock API key."""
    return GeminiClient(api_key=mock_api_key)


def test_gemini_content_dataclass():
    """Test that GeminiContent is a frozen dataclass with the expected attributes."""
    content = GeminiContent(text="Test content", role="model")
    assert content.text == "Test content"
    assert content.role == "model"

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        content.text = "New content"


def test_gemini_candidate_dataclass():
    """Test that GeminiCandidate is a frozen dataclass with the expected attributes."""
    content = GeminiContent(text="Test content", role="model")
    safety_ratings = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "NEGLIGIBLE"}]

    candidate = GeminiCandidate(content=content, finish_reason="STOP", index=0, safety_ratings=safety_ratings)

    assert candidate.content == content
    assert candidate.finish_reason == "STOP"
    assert candidate.index == 0
    assert candidate.safety_ratings == safety_ratings

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        candidate.content = GeminiContent(text="New content", role="model")


def test_gemini_prompt_feedback_dataclass():
    """Test that GeminiPromptFeedback is a frozen dataclass with the expected attributes."""
    safety_ratings = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "NEGLIGIBLE"}]

    feedback = GeminiPromptFeedback(safety_ratings=safety_ratings)

    assert feedback.safety_ratings == safety_ratings

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        feedback.safety_ratings = []


def test_gemini_usage_dataclass():
    """Test that GeminiUsage is a frozen dataclass with the expected attributes."""
    usage = GeminiUsage(prompt_token_count=10, candidates_token_count=15, total_token_count=25)

    assert usage.prompt_token_count == 10
    assert usage.candidates_token_count == 15
    assert usage.total_token_count == 25

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        usage.prompt_token_count = 20


def test_gemini_response_dataclass():
    """Test that GeminiResponse is a frozen dataclass with the expected attributes."""
    content = GeminiContent(text="Test content", role="model")
    candidate = GeminiCandidate(content=content, finish_reason="STOP", index=0, safety_ratings=[])
    prompt_feedback = GeminiPromptFeedback(safety_ratings=[])
    usage = GeminiUsage(prompt_token_count=10, candidates_token_count=15, total_token_count=25)

    response = GeminiResponse(candidates=[candidate], prompt_feedback=prompt_feedback, usage=usage)

    assert response.candidates == [candidate]
    assert response.prompt_feedback == prompt_feedback
    assert response.usage == usage

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        response.candidates = []


def test_gemini_client_init_with_api_key(mock_api_key):
    """Test GeminiClient initialization with an explicitly provided API key."""
    client = GeminiClient(api_key=mock_api_key)

    assert client.api_key == mock_api_key
    assert client.model == GeminiClient.DEFAULT_MODEL
    assert client.temperature == GeminiClient.DEFAULT_TEMPERATURE
    assert client.max_tokens == GeminiClient.DEFAULT_MAX_TOKENS


def test_gemini_client_init_with_env_api_key():
    """Test GeminiClient initialization with an API key from environment variables."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-api-key"}):
        client = GeminiClient()
        assert client.api_key == "env-api-key"


def test_gemini_client_init_missing_api_key():
    """Test that GeminiClient initialization raises ValueError when no API key is available."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            GeminiClient()
        assert "API key is required" in str(excinfo.value)


def test_gemini_client_init_custom_parameters():
    """Test GeminiClient initialization with custom parameters."""
    client = GeminiClient(api_key="custom-api-key", model="gemini-1.5-flash", temperature=0.5, max_tokens=1000)

    assert client.api_key == "custom-api-key"
    assert client.model == "gemini-1.5-flash"
    assert client.temperature == 0.5
    assert client.max_tokens == 1000


def test_prepare_headers(gemini_client):
    """Test that _prepare_headers returns the expected headers."""
    headers = gemini_client._prepare_headers()

    assert headers["Content-Type"] == "application/json"


def test_prepare_payload_basic(gemini_client, sample_prompt):
    """Test that _prepare_payload returns the expected payload with a basic prompt."""
    payload = gemini_client._prepare_payload(sample_prompt)

    assert "contents" in payload
    assert len(payload["contents"]) == 1
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"][0]["text"] == sample_prompt

    assert "generationConfig" in payload
    assert payload["generationConfig"]["temperature"] == gemini_client.temperature
    assert payload["generationConfig"]["maxOutputTokens"] == gemini_client.max_tokens


def test_prepare_payload_with_system_message(gemini_client, sample_prompt, sample_system_message):
    """Test that _prepare_payload returns the expected payload with a system message."""
    payload = gemini_client._prepare_payload(sample_prompt, sample_system_message)

    assert len(payload["contents"]) == 2
    assert payload["contents"][0]["role"] == "system"
    assert payload["contents"][0]["parts"][0]["text"] == sample_system_message
    assert payload["contents"][1]["role"] == "user"
    assert payload["contents"][1]["parts"][0]["text"] == sample_prompt


def test_parse_response_success(gemini_client, sample_gemini_response_data):
    """Test that _parse_response correctly parses a successful API response."""
    # Create a mock HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_gemini_response_data).encode("utf-8")

    # Parse the response
    parsed_response = gemini_client._parse_response(mock_response)

    # Verify the parsed response
    assert len(parsed_response.candidates) == 1

    # Verify the candidate
    candidate = parsed_response.candidates[0]
    candidate_data = sample_gemini_response_data["candidates"][0]
    assert candidate.finish_reason == candidate_data["finishReason"]
    assert candidate.index == candidate_data["index"]

    # Verify the content
    content = candidate.content
    content_data = candidate_data["content"]
    assert content.role == content_data["role"]
    assert content.text == content_data["parts"][0]["text"]

    # Verify the usage
    usage = parsed_response.usage
    usage_data = sample_gemini_response_data["usageMetadata"]
    assert usage.prompt_token_count == usage_data["promptTokenCount"]
    assert usage.candidates_token_count == usage_data["candidatesTokenCount"]
    assert usage.total_token_count == usage_data["totalTokenCount"]


def test_parse_response_error(gemini_client):
    """Test that _parse_response raises ValueError for error responses."""
    # Create a mock error HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 400
    mock_response.data = json.dumps({"error": {"message": "Invalid request", "code": 400}}).encode("utf-8")

    # Verify that parsing raises the expected error
    with pytest.raises(ValueError) as excinfo:
        gemini_client._parse_response(mock_response)
    assert "API request failed" in str(excinfo.value)


def test_parse_response_malformed(gemini_client):
    """Test that _parse_response raises ValueError for malformed responses."""
    # Create a mock malformed HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = "Not valid JSON".encode("utf-8")

    # Verify that parsing raises the expected error
    with pytest.raises(ValueError) as excinfo:
        gemini_client._parse_response(mock_response)
    assert "Failed to parse API response" in str(excinfo.value)


@patch("urllib3.PoolManager.request")
def test_ask_success(mock_request, gemini_client, sample_prompt, sample_gemini_response_data):
    """Test that ask successfully calls the API and returns a parsed response."""
    # Set up the mock response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_gemini_response_data).encode("utf-8")
    mock_request.return_value = mock_response

    # Call ask
    response = gemini_client.ask(sample_prompt)

    # Verify the request was made with the expected parameters
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[0][0] == "POST"
    assert f"{GeminiClient.BASE_URL}/models/{gemini_client.model}:generateContent" in call_args[0][1]
    assert f"key={gemini_client.api_key}" in call_args[0][1]

    # Verify headers
    headers = call_args[1]["headers"]
    assert headers["Content-Type"] == "application/json"

    # Verify payload
    payload = json.loads(call_args[1]["body"].decode("utf-8"))
    assert len(payload["contents"]) == 1
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"][0]["text"] == sample_prompt

    # Verify response
    assert len(response.candidates) == 1
    assert (
        response.candidates[0].content.text
        == sample_gemini_response_data["candidates"][0]["content"]["parts"][0]["text"]
    )


@patch("urllib3.PoolManager.request")
def test_ask_with_system_message(
    mock_request, gemini_client, sample_prompt, sample_system_message, sample_gemini_response_data
):
    """Test that ask correctly includes a system message when provided."""
    # Set up the mock response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_gemini_response_data).encode("utf-8")
    mock_request.return_value = mock_response

    # Call ask with a system message
    gemini_client.ask(sample_prompt, sample_system_message)

    # Verify payload includes the system message
    payload = json.loads(mock_request.call_args[1]["body"].decode("utf-8"))
    assert len(payload["contents"]) == 2
    assert payload["contents"][0]["role"] == "system"
    assert payload["contents"][0]["parts"][0]["text"] == sample_system_message
    assert payload["contents"][1]["role"] == "user"
    assert payload["contents"][1]["parts"][0]["text"] == sample_prompt


@patch("urllib3.PoolManager.request")
def test_ask_api_error(mock_request, gemini_client, sample_prompt):
    """Test that ask raises ValueError when the API returns an error."""
    # Set up the mock error response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 400
    mock_response.data = json.dumps({"error": {"message": "Invalid request", "code": 400}}).encode("utf-8")
    mock_request.return_value = mock_response

    # Verify that ask raises the expected error
    with pytest.raises(ValueError) as excinfo:
        gemini_client.ask(sample_prompt)
    assert "API request failed" in str(excinfo.value)


@patch("urllib3.PoolManager.request")
def test_ask_connection_error(mock_request, gemini_client, sample_prompt):
    """Test that ask raises ValueError when a connection error occurs."""
    # Set up the mock to raise an exception
    mock_request.side_effect = Exception("Connection error")

    # Verify that ask raises the expected error
    with pytest.raises(ValueError) as excinfo:
        gemini_client.ask(sample_prompt)
    assert "Failed to call Gemini API" in str(excinfo.value)


@patch("pull_request_ai_agent.ai_bot.gemini.client.GeminiClient.ask")
def test_get_content(mock_ask, gemini_client, sample_prompt, sample_gemini_response):
    """Test that get_content returns just the content from the first candidate."""
    # Set up the mock to return a sample response
    mock_ask.return_value = sample_gemini_response

    # Call get_content
    content = gemini_client.get_content(sample_prompt)

    # Verify that ask was called with the correct parameters
    mock_ask.assert_called_once_with(sample_prompt, None)

    # Verify the returned content
    expected_content = sample_gemini_response.candidates[0].content.text
    assert content == expected_content


@patch("pull_request_ai_agent.ai_bot.gemini.client.GeminiClient.ask")
def test_get_content_no_candidates(mock_ask, gemini_client, sample_prompt):
    """Test that get_content raises IndexError when there are no candidates in the response."""
    # Create a response with no candidates
    empty_response = GeminiResponse(
        candidates=[],
        prompt_feedback=GeminiPromptFeedback(safety_ratings=[]),
        usage=GeminiUsage(prompt_token_count=0, candidates_token_count=0, total_token_count=0),
    )

    # Set up the mock to return the empty response
    mock_ask.return_value = empty_response

    # Verify that get_content raises the expected error
    with pytest.raises(IndexError) as excinfo:
        gemini_client.get_content(sample_prompt)
    assert "Gemini response contains no candidates" in str(excinfo.value)


@patch("urllib3.PoolManager.request")
def test_ask_with_custom_model(mock_request, mock_api_key, sample_prompt, sample_gemini_response_data):
    """Test that ask uses the custom model when specified."""
    # Set up the mock response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_gemini_response_data).encode("utf-8")
    mock_request.return_value = mock_response

    # Create client with custom model
    custom_model = "gemini-1.5-flash"
    client = GeminiClient(api_key=mock_api_key, model=custom_model)

    # Call ask
    client.ask(sample_prompt)

    # Verify the request was made with the custom model
    call_args = mock_request.call_args
    assert f"{GeminiClient.BASE_URL}/models/{custom_model}:generateContent" in call_args[0][1]
