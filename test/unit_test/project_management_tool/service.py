import pytest
import json
from unittest.mock import Mock, patch
from typing import Dict

import urllib3

from create_pr_bot.project_management_tool.service import ClickUpClient


@pytest.fixture
def mock_successful_response() -> Dict:
    """Fixture for successful API response data"""
    return {
        "id": "abc123",
        "custom_id": None,
        "name": "Test Task",
        "text_content": "This is a test task",
        "description": "Test Description",
        "status": {
            "status": "in progress",
            "color": "#yellow",
            "type": "custom",
            "orderindex": 1
        },
        "orderindex": "1",
        "date_created": "1683900000000",
        "date_updated": "1683900000000",
        "date_closed": None,
        "creator": {
            "id": 123,
            "username": "Test User",
            "email": "test@example.com",
            "color": "#ff0000",
            "profilePicture": "https://example.com/picture.jpg"
        },
        "assignees": [],
        "watchers": [],
        "checklists": [],
        "tags": [],
        "parent": None,
        "priority": {
            "priority": "normal",
            "color": "#ffff00"
        },
        "due_date": "1684500000000",
        "start_date": "1683900000000",
        "points": None,
        "time_estimate": "3600000",  # 1 hour in milliseconds
        "time_spent": "1800000",     # 30 minutes in milliseconds
        "custom_fields": [],
        "dependencies": [],
        "linked_tasks": [],
        "team_id": "team123",
        "url": "https://app.clickup.com/t/abc123",
        "permission_level": "read",
        "list": {
            "id": "list123",
            "name": "Test List",
            "access": True
        },
        "project": {
            "id": "proj123",
            "name": "Test Project",
            "hidden": False,
            "access": True
        },
        "folder": {
            "id": "folder123",
            "name": "Test Folder",
            "hidden": False,
            "access": True
        },
        "space": {
            "id": "space123"
        }
    }


@pytest.fixture
def clickup_client() -> ClickUpClient:
    """Fixture for ClickUpClient instance"""
    return ClickUpClient(api_token="test_token")


class TestClickUpClient:
    """Test suite for ClickUpClient class"""

    def test_successful_task_details_retrieval(self, clickup_client: ClickUpClient, mock_successful_response: Dict):
        """Test successful retrieval of task details"""
        with patch('urllib3.PoolManager.request') as mock_request:
            # Setup mock response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.data = json.dumps(mock_successful_response).encode('utf-8')
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_task_details("abc123")

            # Verify results
            assert result == mock_successful_response
            mock_request.assert_called_once_with(
                "GET",
                "https://api.clickup.com/api/v2/task/abc123",
                headers={
                    "Authorization": "test_token",
                    "Content-Type": "application/json"
                }
            )

    def test_task_details_http_error(self, clickup_client: ClickUpClient):
        """Test handling of HTTP errors"""
        with patch('urllib3.PoolManager.request') as mock_request:
            # Setup mock to raise HTTP error
            mock_request.side_effect = urllib3.exceptions.HTTPError("Mock HTTP Error")

            # Execute test
            result = clickup_client.get_task_details("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    def test_task_details_invalid_json(self, clickup_client: ClickUpClient):
        """Test handling of invalid JSON response"""
        with patch('urllib3.PoolManager.request') as mock_request:
            # Setup mock response with invalid JSON
            mock_response = Mock()
            mock_response.status = 200
            mock_response.data = "Invalid JSON".encode('utf-8')
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_task_details("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    def test_task_details_non_200_response(self, clickup_client: ClickUpClient):
        """Test handling of non-200 HTTP response"""
        with patch('urllib3.PoolManager.request') as mock_request:
            # Setup mock response with 404 status
            mock_response = Mock()
            mock_response.status = 404
            mock_response.data = json.dumps({"err": "Task not found"}).encode('utf-8')
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_task_details("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    def test_task_details_empty_response(self, clickup_client: ClickUpClient):
        """Test handling of empty response"""
        with patch('urllib3.PoolManager.request') as mock_request:
            # Setup mock response with empty data
            mock_response = Mock()
            mock_response.status = 200
            mock_response.data = "".encode('utf-8')
            mock_request.return_value = mock_response

            # Execute test
            result = clickup_client.get_task_details("abc123")

            # Verify results
            assert result is None
            mock_request.assert_called_once()

    @pytest.mark.parametrize("task_id", ["", None, "   "])
    def test_task_details_invalid_task_id(self, clickup_client: ClickUpClient, task_id):
        """Test handling of invalid task IDs"""
        with patch('urllib3.PoolManager.request') as mock_request:
            # Execute test
            result = clickup_client.get_task_details(task_id)

            # Verify results
            assert result is None
            mock_request.assert_called_once()
