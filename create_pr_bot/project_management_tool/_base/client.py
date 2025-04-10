from abc import ABCMeta, abstractmethod
from typing import Optional

import urllib3

from .model import BaseImmutableModel


class BaseProjectManagementAPIClient(metaclass=ABCMeta):

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, api_token: str):
        """Initialize project management service client with API token.

        Args:
            api_token (str): Your ClickUp API personal token
        """
        self.api_token = api_token
        self.http = urllib3.PoolManager()

    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Optional[BaseImmutableModel]:
        """Fetch task details from project management service by task ID.

        Args:
            ticket_id (str): The ID of the task to retrieve

        Returns:
            Optional[BaseImmutableModel]: Task data model of task details

        Raises:
            urllib3.exceptions.HTTPError: If the HTTP request fails
            json.JSONDecodeError: If the response cannot be parsed as JSON
        """
