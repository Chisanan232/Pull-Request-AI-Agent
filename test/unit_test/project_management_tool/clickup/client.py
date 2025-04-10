"""Unit tests for ClickUp API client."""

import json
from datetime import datetime
from unittest.mock import Mock, patch
from http import HTTPMethod

import pytest
import urllib3

from create_pr_bot.project_management_tool.clickup.client import ClickUpAPIClient
from create_pr_bot.project_management_tool.clickup.model import (
    ClickUpStatus,
    ClickUpTask,
    ClickUpUser,
)


@pytest.fixture
def mock_successful_response() -> dict:
    """Fixture for successful API response data"""
    return {
        "id": "abc123",
        "name": "Test Task",
        "text_content": "Test Content",
        "description": "Test Description",
        "status": {"status": "in progress", "color": "#yellow", "type": "custom", "orderindex": 1},
        "orderindex": "1",
        "date_created": "1625097600000",
        "date_updated": "1625097600000",
        "creator": {"id": 123, "username": "test_user", "email": "test@example.com", "color": "#FF0000"},
        "assignees": [],
        "watchers": [],
        "checklists": [],
        "tags": [],
        "url": "https://app.clickup.com/t/abc123",
        "permission_level": "read",
    }


@pytest.fixture
def clickup_client() -> ClickUpAPIClient:
    """Fixture for ClickUpClient instance"""
    return ClickUpAPIClient(api_token="test_token")


class TestClickUpAPIClient:
    """Test suite for ClickUpClient class"""

    def test_successful_get_ticket_retrieval(self, clickup_client: ClickUpAPIClient, mock_successful_response: dict):
        """Test successful retrieval of task details"""
        with patch("urllib3.PoolManager.request") as mock_request:
            # Setup mock response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.data = json.dumps(mock_successful_response).encode("utf-8")
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_ticket("abc123")

            # Verify results
            assert isinstance(result, ClickUpTask)
            assert result.id == "abc123"
            assert result.name == "Test Task"
            assert result.text_content == "Test Content"
            assert result.description == "Test Description"

            # Verify nested objects
            assert isinstance(result.status, ClickUpStatus)
            assert result.status.status == "in progress"
            assert result.status.color == "#yellow"

            assert isinstance(result.creator, ClickUpUser)
            assert result.creator.username == "test_user"
            assert result.creator.email == "test@example.com"

            # Verify datetime conversion
            assert isinstance(result.date_created, datetime)
            assert isinstance(result.date_updated, datetime)

            # Verify request was made correctly
            mock_request.assert_called_once_with(
                HTTPMethod.GET,
                "https://api.clickup.com/api/v2/task/abc123",
                headers={"Authorization": "test_token", "Content-Type": "application/json"},
            )

    def test_get_ticket_http_error(self, clickup_client: ClickUpAPIClient):
        """Test handling of HTTP errors"""
        with patch("urllib3.PoolManager.request") as mock_request:
            # Setup mock to raise HTTP error
            mock_request.side_effect = urllib3.exceptions.HTTPError("Mock HTTP Error")

            # Execute test
            result = clickup_client.get_ticket("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    def test_get_ticket_invalid_json(self, clickup_client: ClickUpAPIClient):
        """Test handling of invalid JSON response"""
        with patch("urllib3.PoolManager.request") as mock_request:
            # Setup mock response with invalid JSON
            mock_response = Mock()
            mock_response.status = 200
            mock_response.data = "Invalid JSON".encode("utf-8")
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_ticket("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    def test_get_ticket_non_200_response(self, clickup_client: ClickUpAPIClient):
        """Test handling of non-200 HTTP response"""
        with patch("urllib3.PoolManager.request") as mock_request:
            # Setup mock response with 404 status
            mock_response = Mock()
            mock_response.status = 404
            mock_response.data = json.dumps({"err": "Task not found"}).encode("utf-8")
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_ticket("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    def test_get_ticket_empty_response(self, clickup_client: ClickUpAPIClient):
        """Test handling of empty response"""
        with patch("urllib3.PoolManager.request") as mock_request:
            # Setup mock response with empty data
            mock_response = Mock()
            mock_response.status = 200
            mock_response.data = "".encode("utf-8")
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_ticket("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    @pytest.mark.parametrize("task_id", ["", None, "   "])
    def test_get_ticket_invalid_task_id(self, clickup_client: ClickUpAPIClient, task_id):
        """Test handling of invalid task IDs"""
        result = clickup_client.get_ticket(task_id)
        assert result is None
