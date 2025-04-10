"""ClickUp API client implementation."""

import json
from typing import Optional

import urllib3

from .model import ClickUpTask
from create_pr_bot.project_management_tool._base.client import BaseProjectManagementAPIClient


class ClickUpClient(BaseProjectManagementAPIClient):
    """ClickUp API client for interacting with ClickUp services."""

    BASE_URL = "https://api.clickup.com/api/v2"

    def get_ticket(self, ticket_id: str) -> Optional[ClickUpTask]:
        """Fetch task details from ClickUp by task ID.

        Args:
            ticket_id (str): The ID of the task to retrieve

        Returns:
            Optional[ClickUpTask]: Task details as a ClickUpTask object or None if request fails

        Raises:
            urllib3.exceptions.HTTPError: If the HTTP request fails
            json.JSONDecodeError: If the response cannot be parsed as JSON
        """
        if not ticket_id or not isinstance(ticket_id, str) or not ticket_id.strip():
            print("Error: Invalid task ID provided")
            return None

        headers = {"Authorization": self.api_token, "Content-Type": "application/json"}

        try:
            response = self.http.request("GET", f"{self.BASE_URL}/task/{ticket_id}", headers=headers)

            if response.status == 200:
                response_data = json.loads(response.data.decode("utf-8"))
                return ClickUpTask.serialize(response_data)
            else:
                print(f"Error: Request failed with status {response.status}")
                print(f"Response: {response.data.decode('utf-8')}")
                return None

        except urllib3.exceptions.HTTPError as e:
            print(f"HTTP Error occurred: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            return None
