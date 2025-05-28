"""
Unit tests for the Claude client functionality.
"""

import json
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from urllib3.response import HTTPResponse

from pull_request_ai_agent.ai_bot.claude.client import ClaudeClient
from pull_request_ai_agent.ai_bot.claude.model import (
    ClaudeContent,
    ClaudeMessage,
    ClaudeResponse,
    ClaudeUsage,
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
def sample_claude_response_data() -> Dict[str, Any]:
    """Fixture for sample Claude response data."""
    return {
        "id": "msg_012345abcdef",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "The capital of France is Paris."}],
        "model": "claude-3-opus-20240229",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 15, "output_tokens": 8},
    }


@pytest.fixture
def sample_claude_response(sample_claude_response_data: Dict[str, Any]) -> ClaudeResponse:
    """Fixture for a sample ClaudeResponse object."""
    content_items = [
        ClaudeContent(type=item["type"], text=item["text"]) for item in sample_claude_response_data["content"]
    ]

    usage_data = sample_claude_response_data["usage"]
    usage = ClaudeUsage(input_tokens=usage_data["input_tokens"], output_tokens=usage_data["output_tokens"])

    return ClaudeResponse(
        id=sample_claude_response_data["id"],
        type=sample_claude_response_data["type"],
        role=sample_claude_response_data["role"],
        content=content_items,
        model=sample_claude_response_data["model"],
        stop_reason=sample_claude_response_data["stop_reason"],
        stop_sequence=sample_claude_response_data["stop_sequence"],
        usage=usage,
    )


@pytest.fixture
def claude_client(mock_api_key: str) -> ClaudeClient:
    """Fixture for a ClaudeClient instance with a mock API key."""
    return ClaudeClient(api_key=mock_api_key)


def test_claude_content_dataclass() -> None:
    """Test that ClaudeContent is a frozen dataclass with the expected attributes."""
    content = ClaudeContent(type="text", text="Test content")
    assert content.type == "text"
    assert content.text == "Test content"

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        content.text = "New content"  # type: ignore[misc]


def test_claude_message_dataclass() -> None:
    """Test that ClaudeMessage is a frozen dataclass with the expected attributes."""
    content = ClaudeContent(type="text", text="Test content")
    message = ClaudeMessage(
        id="msg_123",
        type="message",
        role="assistant",
        content=[content],
        model="claude-3-opus-20240229",
        stop_reason="end_turn",
        stop_sequence=None,
    )

    assert message.id == "msg_123"
    assert message.type == "message"
    assert message.role == "assistant"
    assert message.content == [content]
    assert message.model == "claude-3-opus-20240229"
    assert message.stop_reason == "end_turn"
    assert message.stop_sequence is None

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        message.content = []  # type: ignore[misc]


def test_claude_usage_dataclass() -> None:
    """Test that ClaudeUsage is a frozen dataclass with the expected attributes."""
    usage = ClaudeUsage(input_tokens=15, output_tokens=8)

    assert usage.input_tokens == 15
    assert usage.output_tokens == 8

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        usage.input_tokens = 20  # type: ignore[misc]


def test_claude_response_dataclass() -> None:
    """Test that ClaudeResponse is a frozen dataclass with the expected attributes."""
    content = ClaudeContent(type="text", text="Test content")
    usage = ClaudeUsage(input_tokens=15, output_tokens=8)

    response = ClaudeResponse(
        id="msg_123",
        type="message",
        role="assistant",
        content=[content],
        model="claude-3-opus-20240229",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=usage,
    )

    assert response.id == "msg_123"
    assert response.type == "message"
    assert response.role == "assistant"
    assert response.content == [content]
    assert response.model == "claude-3-opus-20240229"
    assert response.stop_reason == "end_turn"
    assert response.stop_sequence is None
    assert response.usage == usage

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        response.content = []  # type: ignore[misc]


def test_claude_client_init_with_api_key(mock_api_key: str) -> None:
    """Test ClaudeClient initialization with an explicitly provided API key."""
    client = ClaudeClient(api_key=mock_api_key)

    assert client.api_key == mock_api_key
    assert client.model == ClaudeClient.DEFAULT_MODEL
    assert client.temperature == ClaudeClient.DEFAULT_TEMPERATURE
    assert client.max_tokens == ClaudeClient.DEFAULT_MAX_TOKENS


def test_claude_client_init_with_env_api_key() -> None:
    """Test ClaudeClient initialization with an API key from environment variables."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-api-key"}):
        client = ClaudeClient()
        assert client.api_key == "env-api-key"


def test_claude_client_init_missing_api_key() -> None:
    """Test that ClaudeClient initialization raises ValueError when no API key is available."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            ClaudeClient()
        assert "API key is required" in str(excinfo.value)


def test_claude_client_init_custom_parameters() -> None:
    """Test ClaudeClient initialization with custom parameters."""
    client = ClaudeClient(api_key="custom-api-key", model="claude-3-sonnet-20240229", temperature=0.5, max_tokens=1000)

    assert client.api_key == "custom-api-key"
    assert client.model == "claude-3-sonnet-20240229"
    assert client.temperature == 0.5
    assert client.max_tokens == 1000


def test_prepare_headers(claude_client: ClaudeClient, mock_api_key: str) -> None:
    """Test that _prepare_headers returns the expected headers."""
    headers = claude_client._prepare_headers()

    assert headers["Content-Type"] == "application/json"
    assert headers["x-api-key"] == mock_api_key
    assert headers["anthropic-version"] == ClaudeClient.API_VERSION


def test_prepare_payload_basic(claude_client: ClaudeClient, sample_prompt: str) -> None:
    """Test that _prepare_payload returns the expected payload with a basic prompt."""
    payload = claude_client._prepare_payload(sample_prompt)

    assert payload["model"] == claude_client.model
    assert payload["temperature"] == claude_client.temperature
    assert payload["max_tokens"] == claude_client.max_tokens
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert len(payload["messages"][0]["content"]) == 1
    assert payload["messages"][0]["content"][0]["type"] == "text"
    assert payload["messages"][0]["content"][0]["text"] == sample_prompt
    assert "system" not in payload


def test_prepare_payload_with_system_message(
    claude_client: ClaudeClient, sample_prompt: str, sample_system_message: str
) -> None:
    """Test that _prepare_payload returns the expected payload with a system message."""
    payload = claude_client._prepare_payload(sample_prompt, sample_system_message)

    assert "system" in payload
    assert payload["system"] == sample_system_message


def test_parse_response_success(claude_client: ClaudeClient, sample_claude_response_data: Dict[str, Any]) -> None:
    """Test that _parse_response correctly parses a successful API response."""
    # Create a mock HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_claude_response_data).encode("utf-8")

    # Parse the response
    parsed_response = claude_client._parse_response(mock_response)

    # Verify the parsed response
    assert parsed_response.id == sample_claude_response_data["id"]
    assert parsed_response.type == sample_claude_response_data["type"]
    assert parsed_response.role == sample_claude_response_data["role"]
    assert parsed_response.model == sample_claude_response_data["model"]
    assert parsed_response.stop_reason == sample_claude_response_data["stop_reason"]
    assert parsed_response.stop_sequence == sample_claude_response_data["stop_sequence"]

    # Verify the content
    assert len(parsed_response.content) == len(sample_claude_response_data["content"])
    for i, content_item in enumerate(parsed_response.content):
        assert content_item.type == sample_claude_response_data["content"][i]["type"]
        assert content_item.text == sample_claude_response_data["content"][i]["text"]

    # Verify the usage
    usage = parsed_response.usage
    usage_data = sample_claude_response_data["usage"]
    assert usage.input_tokens == usage_data["input_tokens"]
    assert usage.output_tokens == usage_data["output_tokens"]


def test_parse_response_error(claude_client: ClaudeClient) -> None:
    """Test that _parse_response raises ValueError for error responses."""
    # Create a mock error HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 400
    mock_response.data = json.dumps({"error": {"message": "Invalid request", "type": "invalid_request_error"}}).encode(
        "utf-8"
    )

    # Verify that parsing raises the expected error
    with pytest.raises(ValueError) as excinfo:
        claude_client._parse_response(mock_response)
    assert "API request failed" in str(excinfo.value)


def test_parse_response_malformed(claude_client: ClaudeClient) -> None:
    """Test that _parse_response raises ValueError for malformed responses."""
    # Create a mock malformed HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = "Not valid JSON".encode("utf-8")

    # Verify that parsing raises the expected error
    with pytest.raises(ValueError) as excinfo:
        claude_client._parse_response(mock_response)
    assert "Failed to parse API response" in str(excinfo.value)


@patch("urllib3.PoolManager.request")
def test_ask_success(
    mock_request: Any, claude_client: ClaudeClient, sample_prompt: str, sample_claude_response_data: Dict[str, Any]
) -> None:
    """Test that ask successfully calls the API and returns a parsed response."""
    # Set up the mock response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_claude_response_data).encode("utf-8")
    mock_request.return_value = mock_response

    # Call ask
    response = claude_client.ask(sample_prompt)

    # Verify the request was made with the expected parameters
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == f"{ClaudeClient.BASE_URL}/messages"

    # Verify headers
    headers = call_args[1]["headers"]
    assert headers["Content-Type"] == "application/json"
    assert headers["x-api-key"] == claude_client.api_key

    # Verify payload
    payload = json.loads(call_args[1]["body"].decode("utf-8"))
    assert payload["model"] == claude_client.model
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"][0]["text"] == sample_prompt

    # Verify response
    assert response.id == sample_claude_response_data["id"]
    assert response.content[0].text == sample_claude_response_data["content"][0]["text"]


@patch("urllib3.PoolManager.request")
def test_ask_with_system_message(
    mock_request: Any,
    claude_client: ClaudeClient,
    sample_prompt: str,
    sample_system_message: str,
    sample_claude_response_data: Dict[str, Any],
) -> None:
    """Test that ask correctly includes a system message when provided."""
    # Set up the mock response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_claude_response_data).encode("utf-8")
    mock_request.return_value = mock_response

    # Call ask with a system message
    claude_client.ask(sample_prompt, sample_system_message)

    # Verify payload includes the system message
    payload = json.loads(mock_request.call_args[1]["body"].decode("utf-8"))
    assert "system" in payload
    assert payload["system"] == sample_system_message


@patch("urllib3.PoolManager.request")
def test_ask_api_error(mock_request: Any, claude_client: ClaudeClient, sample_prompt: str) -> None:
    """Test that ask raises ValueError when the API returns an error."""
    # Set up the mock error response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 400
    mock_response.data = json.dumps({"error": {"message": "Invalid request", "type": "invalid_request_error"}}).encode(
        "utf-8"
    )
    mock_request.return_value = mock_response

    # Verify that ask raises the expected error
    with pytest.raises(ValueError) as excinfo:
        claude_client.ask(sample_prompt)
    assert "API request failed" in str(excinfo.value)


@patch("urllib3.PoolManager.request")
def test_ask_connection_error(mock_request: Any, claude_client: ClaudeClient, sample_prompt: str) -> None:
    """Test that ask raises ValueError when a connection error occurs."""
    # Set up the mock to raise an exception
    mock_request.side_effect = Exception("Connection error")

    # Verify that ask raises the expected error
    with pytest.raises(ValueError) as excinfo:
        claude_client.ask(sample_prompt)
    assert "Failed to call Claude API" in str(excinfo.value)


@patch("pull_request_ai_agent.ai_bot.claude.client.ClaudeClient.ask")
def test_get_content(
    mock_ask: Any, claude_client: ClaudeClient, sample_prompt: str, sample_claude_response: ClaudeResponse
) -> None:
    """Test that get_content returns just the content from the response."""
    # Set up the mock to return a sample response
    mock_ask.return_value = sample_claude_response

    # Call get_content
    content = claude_client.get_content(sample_prompt)

    # Verify that ask was called with the correct parameters
    mock_ask.assert_called_once_with(sample_prompt, None)

    # Verify the returned content
    expected_content = sample_claude_response.content[0].text
    assert content == expected_content


@patch("pull_request_ai_agent.ai_bot.claude.client.ClaudeClient.ask")
def test_get_content_no_content(mock_ask: Any, claude_client: ClaudeClient, sample_prompt: str) -> None:
    """Test that get_content raises IndexError when there is no content in the response."""
    # Create a response with no content
    empty_response = ClaudeResponse(
        id="msg_123",
        type="message",
        role="assistant",
        content=[],
        model="claude-3-opus-20240229",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=ClaudeUsage(input_tokens=0, output_tokens=0),
    )

    # Set up the mock to return the empty response
    mock_ask.return_value = empty_response

    # Verify that get_content raises the expected error
    with pytest.raises(IndexError) as excinfo:
        claude_client.get_content(sample_prompt)
    assert "Claude response contains no content" in str(excinfo.value)
