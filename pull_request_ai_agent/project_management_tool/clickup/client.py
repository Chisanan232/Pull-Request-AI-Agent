"""ClickUp API client implementation."""

import json
import logging
from http import HTTPMethod
from typing import Optional

import urllib3

from pull_request_ai_agent.project_management_tool._base.client import (
    BaseProjectManagementAPIClient,
)

from .model import ClickUpTask

# Configure logging
logger = logging.getLogger(__name__)


class ClickUpAPIClient(BaseProjectManagementAPIClient):
    """ClickUp API client for interacting with ClickUp services."""

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, api_token: str):
        """Initialize ClickUp API client with API token.

        Args:
            api_token (str): Your ClickUp API personal token
        """
        logger.debug("Initializing ClickUp API client")
        super().__init__(api_token=api_token)
        logger.info("ClickUp API client successfully initialized")

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
            logger.error("Invalid ClickUp task ID provided")
            return None

        logger.info(f"Fetching ClickUp task with ID: {ticket_id}")
        headers = {"Authorization": self.api_token, "Content-Type": "application/json"}
        url = f"{self.BASE_URL}/task/{ticket_id}"
        logger.debug(f"Making request to ClickUp API: {url}")

        try:
            logger.debug("Sending GET request to ClickUp API")
            response = self.http.request(HTTPMethod.GET, url, headers=headers)
            logger.debug(f"Received response with status code: {response.status}")

            if response.status == 200:
                logger.debug("Successfully received response from ClickUp API")
                response_data = json.loads(response.data.decode("utf-8"))

                # Log basic task info if available
                if "id" in response_data:
                    logger.info(f"Successfully retrieved ClickUp task: {response_data['id']}")
                if "name" in response_data:
                    logger.debug(f"Task name: {response_data['name']}")
                if "status" in response_data and "status" in response_data["status"]:
                    logger.debug(f"Task status: {response_data['status']['status']}")

                task = ClickUpTask.serialize(response_data)
                logger.debug("Successfully created ClickUpTask object from API response")
                return task
            else:
                error_msg = f"ClickUp API request failed with status {response.status}"
                response_body = response.data.decode("utf-8")
                logger.error(f"{error_msg}: {response_body}")
                return None

        except urllib3.exceptions.HTTPError as e:
            logger.error(f"HTTP Error occurred while fetching ClickUp task: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ClickUp API response as JSON: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching ClickUp task: {str(e)}", exc_info=True)
            return None
