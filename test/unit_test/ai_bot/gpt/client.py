"""
Unit tests for the GPT client functionality.
"""

import json
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from urllib3.response import HTTPResponse

from pull_request_ai_agent.ai_bot.gpt.client import GPTClient
from pull_request_ai_agent.ai_bot.gpt.model import (
    GPTChoice,
    GPTMessage,
    GPTResponse,
    GPTUsage,
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
def sample_gpt_response_data() -> Dict[str, Any]:
    """Fixture for sample GPT response data."""
    return {
        "id": "chatcmpl-123456789",
        "object": "chat.completion",
        "created": 1677858242,
        "model": "gpt-4",
        "usage": {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
        "choices": [
            {
                "message": {"role": "assistant", "content": "The capital of France is Paris."},
                "finish_reason": "stop",
                "index": 0,
            }
        ],
    }


@pytest.fixture
def sample_gpt_response(sample_gpt_response_data) -> GPTResponse:
    """Fixture for a sample GPTResponse object."""
    choice_data = sample_gpt_response_data["choices"][0]
    message_data = choice_data["message"]

    message = GPTMessage(role=message_data["role"], content=message_data["content"])

    choice = GPTChoice(index=choice_data["index"], message=message, finish_reason=choice_data["finish_reason"])

    usage_data = sample_gpt_response_data["usage"]
    usage = GPTUsage(
        prompt_tokens=usage_data["prompt_tokens"],
        completion_tokens=usage_data["completion_tokens"],
        total_tokens=usage_data["total_tokens"],
    )

    return GPTResponse(
        id=sample_gpt_response_data["id"],
        object=sample_gpt_response_data["object"],
        created=sample_gpt_response_data["created"],
        model=sample_gpt_response_data["model"],
        choices=[choice],
        usage=usage,
    )


@pytest.fixture
def gpt_client(mock_api_key) -> GPTClient:
    """Fixture for a GPTClient instance with a mock API key."""
    return GPTClient(api_key=mock_api_key)


def test_gpt_message_dataclass():
    """Test that GPTMessage is a frozen dataclass with the expected attributes."""
    message = GPTMessage(role="user", content="Test content")
    assert message.role == "user"
    assert message.content == "Test content"

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        message.content = "New content"


def test_gpt_choice_dataclass():
    """Test that GPTChoice is a frozen dataclass with the expected attributes."""
    message = GPTMessage(role="assistant", content="Test response")
    choice = GPTChoice(index=0, message=message, finish_reason="stop")

    assert choice.index == 0
    assert choice.message == message
    assert choice.finish_reason == "stop"

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        choice.message = GPTMessage(role="user", content="Another message")


def test_gpt_usage_dataclass():
    """Test that GPTUsage is a frozen dataclass with the expected attributes."""
    usage = GPTUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25)

    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 15
    assert usage.total_tokens == 25

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        usage.total_tokens = 30


def test_gpt_response_dataclass():
    """Test that GPTResponse is a frozen dataclass with the expected attributes."""
    message = GPTMessage(role="assistant", content="Test response")
    choice = GPTChoice(index=0, message=message, finish_reason="stop")
    usage = GPTUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25)

    response = GPTResponse(
        id="test-id", object="chat.completion", created=123456789, model="gpt-4", choices=[choice], usage=usage
    )

    assert response.id == "test-id"
    assert response.object == "chat.completion"
    assert response.created == 123456789
    assert response.model == "gpt-4"
    assert response.choices == [choice]
    assert response.usage == usage

    # Test immutability (frozen=True)
    with pytest.raises(AttributeError):
        response.choices = []


def test_gpt_client_init_with_api_key(mock_api_key):
    """Test GPTClient initialization with an explicitly provided API key."""
    client = GPTClient(api_key=mock_api_key)

    assert client.api_key == mock_api_key
    assert client.model == GPTClient.DEFAULT_MODEL
    assert client.temperature == GPTClient.DEFAULT_TEMPERATURE
    assert client.max_tokens == GPTClient.DEFAULT_MAX_TOKENS


def test_gpt_client_init_with_env_api_key():
    """Test GPTClient initialization with an API key from environment variables."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "env-api-key"}):
        client = GPTClient()
        assert client.api_key == "env-api-key"


def test_gpt_client_init_missing_api_key():
    """Test that GPTClient initialization raises ValueError when no API key is available."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            GPTClient()
        assert "API key is required" in str(excinfo.value)


def test_gpt_client_init_custom_parameters():
    """Test GPTClient initialization with custom parameters."""
    client = GPTClient(api_key="custom-api-key", model="gpt-3.5-turbo", temperature=0.5, max_tokens=1000)

    assert client.api_key == "custom-api-key"
    assert client.model == "gpt-3.5-turbo"
    assert client.temperature == 0.5
    assert client.max_tokens == 1000


def test_prepare_headers(gpt_client, mock_api_key):
    """Test that _prepare_headers returns the expected headers."""
    headers = gpt_client._prepare_headers()

    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"] == f"Bearer {mock_api_key}"


def test_prepare_payload_basic(gpt_client, sample_prompt):
    """Test that _prepare_payload returns the expected payload with a basic prompt."""
    payload = gpt_client._prepare_payload(sample_prompt)

    assert payload["model"] == gpt_client.model
    assert payload["temperature"] == gpt_client.temperature
    assert payload["max_tokens"] == gpt_client.max_tokens
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == sample_prompt


def test_prepare_payload_with_system_message(gpt_client, sample_prompt, sample_system_message):
    """Test that _prepare_payload returns the expected payload with a system message."""
    payload = gpt_client._prepare_payload(sample_prompt, sample_system_message)

    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == sample_system_message
    assert payload["messages"][1]["role"] == "user"
    assert payload["messages"][1]["content"] == sample_prompt


def test_parse_response_success(gpt_client, sample_gpt_response_data):
    """Test that _parse_response correctly parses a successful API response."""
    # Create a mock HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_gpt_response_data).encode("utf-8")

    # Parse the response
    parsed_response = gpt_client._parse_response(mock_response)

    # Verify the parsed response
    assert parsed_response.id == sample_gpt_response_data["id"]
    assert parsed_response.object == sample_gpt_response_data["object"]
    assert parsed_response.created == sample_gpt_response_data["created"]
    assert parsed_response.model == sample_gpt_response_data["model"]
    assert len(parsed_response.choices) == 1

    # Verify the choice
    choice = parsed_response.choices[0]
    choice_data = sample_gpt_response_data["choices"][0]
    assert choice.index == choice_data["index"]
    assert choice.finish_reason == choice_data["finish_reason"]

    # Verify the message
    message = choice.message
    message_data = choice_data["message"]
    assert message.role == message_data["role"]
    assert message.content == message_data["content"]

    # Verify the usage
    usage = parsed_response.usage
    usage_data = sample_gpt_response_data["usage"]
    assert usage.prompt_tokens == usage_data["prompt_tokens"]
    assert usage.completion_tokens == usage_data["completion_tokens"]
    assert usage.total_tokens == usage_data["total_tokens"]


def test_parse_response_error(gpt_client):
    """Test that _parse_response raises ValueError for error responses."""
    # Create a mock error HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 400
    mock_response.data = json.dumps({"error": {"message": "Invalid request", "type": "invalid_request_error"}}).encode(
        "utf-8"
    )

    # Verify that parsing raises the expected error
    with pytest.raises(ValueError) as excinfo:
        gpt_client._parse_response(mock_response)
    assert "API request failed" in str(excinfo.value)
    assert "Invalid request" in str(excinfo.value)


def test_parse_response_malformed(gpt_client):
    """Test that _parse_response raises ValueError for malformed responses."""
    # Create a mock malformed HTTPResponse
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = "Not valid JSON".encode("utf-8")

    # Verify that parsing raises the expected error
    with pytest.raises(ValueError) as excinfo:
        gpt_client._parse_response(mock_response)
    assert "Failed to parse API response" in str(excinfo.value)


@patch("urllib3.PoolManager.request")
def test_ask_success(mock_request, gpt_client, sample_prompt, sample_gpt_response_data):
    """Test that ask successfully calls the API and returns a parsed response."""
    # Set up the mock response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_gpt_response_data).encode("utf-8")
    mock_request.return_value = mock_response

    # Call ask
    response = gpt_client.ask(sample_prompt)

    # Verify the request was made with the expected parameters
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == f"{GPTClient.BASE_URL}/chat/completions"

    # Verify headers
    headers = call_args[1]["headers"]
    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"] == f"Bearer {gpt_client.api_key}"

    # Verify payload
    payload = json.loads(call_args[1]["body"].decode("utf-8"))
    assert payload["model"] == gpt_client.model
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == sample_prompt

    # Verify response
    assert response.id == sample_gpt_response_data["id"]
    assert len(response.choices) == 1
    assert response.choices[0].message.content == sample_gpt_response_data["choices"][0]["message"]["content"]


@patch("urllib3.PoolManager.request")
def test_ask_with_system_message(
    mock_request, gpt_client, sample_prompt, sample_system_message, sample_gpt_response_data
):
    """Test that ask correctly includes a system message when provided."""
    # Set up the mock response
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.status = 200
    mock_response.data = json.dumps(sample_gpt_response_data).encode("utf-8")
    mock_request.return_value = mock_response

    # Call ask with a system message
    gpt_client.ask(sample_prompt, sample_system_message)

    # Verify payload includes the system message
    payload = json.loads(mock_request.call_args[1]["body"].decode("utf-8"))
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == sample_system_message
    assert payload["messages"][1]["role"] == "user"
    assert payload["messages"][1]["content"] == sample_prompt


@patch("urllib3.PoolManager.request")
def test_ask_api_error(mock_request, gpt_client, sample_prompt):
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
        gpt_client.ask(sample_prompt)
    assert "API request failed" in str(excinfo.value)


@patch("urllib3.PoolManager.request")
def test_ask_connection_error(mock_request, gpt_client, sample_prompt):
    """Test that ask raises ValueError when a connection error occurs."""
    # Set up the mock to raise an exception
    mock_request.side_effect = Exception("Connection error")

    # Verify that ask raises the expected error
    with pytest.raises(ValueError) as excinfo:
        gpt_client.ask(sample_prompt)
    assert "Failed to call GPT API" in str(excinfo.value)


@patch("pull_request_ai_agent.ai_bot.gpt.client.GPTClient.ask")
def test_get_content(mock_ask, gpt_client, sample_prompt, sample_gpt_response):
    """Test that get_content returns just the content from the first choice."""
    # Set up the mock to return a sample response
    mock_ask.return_value = sample_gpt_response

    # Call get_content
    content = gpt_client.get_content(sample_prompt)

    # Verify that ask was called with the correct parameters
    mock_ask.assert_called_once_with(sample_prompt, None)

    # Verify the returned content
    expected_content = sample_gpt_response.choices[0].message.content
    assert content == expected_content


@patch("pull_request_ai_agent.ai_bot.gpt.client.GPTClient.ask")
def test_get_content_no_choices(mock_ask, gpt_client, sample_prompt):
    """Test that get_content raises IndexError when there are no choices in the response."""
    # Create a response with no choices
    empty_response = GPTResponse(
        id="test-id",
        object="chat.completion",
        created=123456789,
        model="gpt-4",
        choices=[],
        usage=GPTUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
    )

    # Set up the mock to return the empty response
    mock_ask.return_value = empty_response

    # Verify that get_content raises the expected error
    with pytest.raises(IndexError) as excinfo:
        gpt_client.get_content(sample_prompt)
    assert "GPT response contains no choices" in str(excinfo.value)
