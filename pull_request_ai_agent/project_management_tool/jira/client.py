import base64
import json
import logging
from http import HTTPMethod
from typing import Optional

import urllib3

from pull_request_ai_agent.project_management_tool._base.client import (
    BaseProjectManagementAPIClient,
)

from .model import JiraTicket

# Configure logging
logger = logging.getLogger(__name__)


class JiraAPIClient(BaseProjectManagementAPIClient):
    """Client for interacting with JIRA REST API."""

    def __init__(self, base_url: str, email: str, api_token: str):
        """
        Initialize JIRA API client.

        Args:
            base_url: Base URL of your JIRA instance (e.g., 'https://your-domain.atlassian.net')
            email: Email address associated with your JIRA account
            api_token: JIRA API token for authentication
        """
        logger.debug(f"Initializing JIRA API client for {base_url}")
        super().__init__(api_token=api_token)
        self.base_url = base_url.rstrip("/")
        logger.debug(f"JIRA base URL set to: {self.base_url}")

        # Create auth header manually
        auth_string = f"{email}:{self.api_token}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
        logger.debug(f"JIRA authentication created for user: {email}")

        # Combine all required headers
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "JiraApiClient/1.0",
        }
        logger.info("Successfully initialized JIRA API client")

    def get_ticket(self, ticket_id: str) -> Optional[JiraTicket]:
        """
        Fetch details of a JIRA ticket by its ID.

        Args:
            ticket_id: The JIRA ticket ID (e.g., 'PROJ-123')

        Returns:
            JiraTicket object if found, None if not found

        Raises:
            urllib3.exceptions.HTTPError: If the API request fails
        """
        logger.info(f"Fetching JIRA ticket with ID: {ticket_id}")
        url = f"{self.base_url}/rest/api/2/issue/{ticket_id}"
        logger.debug(f"Making request to JIRA API: {url}")

        try:
            logger.debug("Sending GET request to JIRA API")
            response = self.http.request(HTTPMethod.GET, url, headers=self.headers)
            logger.debug(f"Received response with status code: {response.status}")

            if response.status == 404:
                logger.warning(f"JIRA ticket not found: {ticket_id}")
                return None

            if response.status != 200:
                error_msg = f"JIRA API request failed with status {response.status}"
                logger.error(error_msg)
                response.drain_conn()
                raise urllib3.exceptions.HTTPError(error_msg)

            logger.debug("Parsing JIRA API response")
            data = json.loads(response.data.decode("utf-8"))
            
            # Log some basic info about the ticket
            if "key" in data and "fields" in data:
                logger.info(f"Successfully retrieved JIRA ticket: {data['key']}")
                if "summary" in data["fields"]:
                    logger.debug(f"Ticket summary: {data['fields']['summary']}")
            
            ticket = JiraTicket.serialize(data)
            logger.debug("Successfully created JiraTicket object from API response")
            return ticket

        except urllib3.exceptions.HTTPError as e:
            logger.error(f"HTTP error while fetching JIRA ticket: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JIRA API response as JSON: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching JIRA ticket: {str(e)}", exc_info=True)
            raise
        finally:
            if "response" in locals():
                response.drain_conn()
                logger.debug("Connection drained")

    def search_tickets(self, jql: str, max_results: int = 50) -> list[JiraTicket]:
        """
        Search for JIRA tickets using JQL (JIRA Query Language).

        Args:
            jql: JQL search string
            max_results: Maximum number of results to return

        Returns:
            List of JiraTicket objects matching the search criteria

        Raises:
            urllib3.exceptions.HTTPError: If the API request fails
        """
        logger.info(f"Searching JIRA tickets with JQL: {jql}")
        logger.debug(f"Max results: {max_results}")
        url = f"{self.base_url}/rest/api/2/search"
        
        try:
            logger.debug(f"Making request to JIRA search API: {url}")
            response = self.http.request(
                HTTPMethod.GET, url, headers=self.headers, fields={"jql": jql, "maxResults": max_results}
            )
            logger.debug(f"Received response with status code: {response.status}")

            if response.status != 200:
                error_msg = f"JIRA search API request failed with status {response.status}"
                logger.error(error_msg)
                response.drain_conn()
                raise urllib3.exceptions.HTTPError(error_msg)

            logger.debug("Parsing JIRA search API response")
            data = json.loads(response.data.decode("utf-8"))
            
            # Log some basic info about the search results
            total = data.get("total", 0)
            logger.info(f"JIRA search returned {total} total results, processing up to {max_results}")
            
            tickets = JiraTicket.serialize_list(data)
            logger.debug(f"Successfully created {len(tickets)} JiraTicket objects from search results")
            return tickets
            
        except urllib3.exceptions.HTTPError as e:
            logger.error(f"HTTP error while searching JIRA tickets: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JIRA search API response as JSON: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while searching JIRA tickets: {str(e)}", exc_info=True)
            raise
        finally:
            if "response" in locals():
                response.drain_conn()
                logger.debug("Connection drained")
