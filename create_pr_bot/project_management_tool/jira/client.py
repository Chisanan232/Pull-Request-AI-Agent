import urllib3
import json
from typing import Dict, Optional
from urllib3.util import make_headers
from .model import JiraTicket

class JiraApiClient:
    """Client for interacting with JIRA REST API."""
    
    def __init__(self, base_url: str, email: str, api_token: str):
        """
        Initialize JIRA API client.
        
        Args:
            base_url: Base URL of your JIRA instance (e.g., 'https://your-domain.atlassian.net')
            email: Email address associated with your JIRA account
            api_token: JIRA API token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.http = urllib3.PoolManager()
        
        # Create basic auth headers
        self.headers = make_headers(
            basic_auth=f"{email}:{api_token}",
            user_agent="JiraApiClient/1.0",
            accept="application/json",
            content_type="application/json"
        )

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
        url = f"{self.base_url}/rest/api/2/issue/{ticket_id}"
        
        try:
            response = self.http.request('GET', url, headers=self.headers)
            
            if response.status == 404:
                return None
                
            if response.status != 200:
                response.drain_conn()
                raise urllib3.exceptions.HTTPError(f"Request failed with status {response.status}")
            
            data = json.loads(response.data.decode('utf-8'))
            return JiraTicket(
                id=data['key'],
                title=data['fields']['summary'],
                description=data['fields']['description'] or '',
                status=data['fields']['status']['name'],
                assignee=data['fields']['assignee']['displayName'] if data['fields']['assignee'] else None,
                project_key=data['fields']['project']['key']
            )
            
        finally:
            if 'response' in locals():
                response.drain_conn()

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
        url = f"{self.base_url}/rest/api/2/search"
        
        try:
            response = self.http.request(
                'GET',
                url,
                headers=self.headers,
                fields={'jql': jql, 'maxResults': max_results}
            )
            
            if response.status != 200:
                response.drain_conn()
                raise urllib3.exceptions.HTTPError(f"Request failed with status {response.status}")
            
            data = json.loads(response.data.decode('utf-8'))
            return [
                JiraTicket(
                    id=issue['key'],
                    title=issue['fields']['summary'],
                    description=issue['fields']['description'] or '',
                    status=issue['fields']['status']['name'],
                    assignee=issue['fields']['assignee']['displayName'] if issue['fields']['assignee'] else None,
                    project_key=issue['fields']['project']['key']
                )
                for issue in data['issues']
            ]
            
        finally:
            if 'response' in locals():
                response.drain_conn()
