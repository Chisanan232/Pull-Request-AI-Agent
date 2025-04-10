from typing import Any, Dict, Optional
import pytest
from unittest.mock import Mock
import json
import urllib3
from pytest import MonkeyPatch
from .client import JiraApiClient
from .model import JiraTicket


class TestJIRAApiClient:
    """Test cases for JIRA API client."""
    
    @pytest.fixture
    def jira_client(self) -> JiraApiClient:
        """Fixture for creating a JiraApiClient instance."""
        return JiraApiClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token"
        )

    @pytest.fixture
    def mock_response(self) -> Mock:
        """Fixture for creating a mock response."""
        response: Mock = Mock()
        response.drain_conn = Mock()
        return response

    @pytest.fixture
    def sample_ticket_data(self) -> Dict[str, Any]:
        """Fixture for sample ticket data."""
        return {
            'key': 'TEST-123',
            'fields': {
                'summary': 'Test ticket',
                'description': 'Test description',
                'status': {'name': 'Open'},
                'assignee': {'displayName': 'John Doe'},
                'project': {'key': 'TEST'}
            }
        }

    @pytest.fixture
    def sample_search_data(self) -> Dict[str, list[Dict[str, Any]]]:
        """Fixture for sample search results data."""
        return {
            'issues': [
                {
                    'key': 'TEST-1',
                    'fields': {
                        'summary': 'First ticket',
                        'description': 'First description',
                        'status': {'name': 'Open'},
                        'assignee': {'displayName': 'John Doe'},
                        'project': {'key': 'TEST'}
                    }
                },
                {
                    'key': 'TEST-2',
                    'fields': {
                        'summary': 'Second ticket',
                        'description': None,
                        'status': {'name': 'In Progress'},
                        'assignee': None,
                        'project': {'key': 'TEST'}
                    }
                }
            ]
        }

    def test_client_initialization(self, jira_client: JiraApiClient) -> None:
        """Test client initialization."""
        assert jira_client.base_url == "https://test.atlassian.net"
        assert isinstance(jira_client.http, urllib3.PoolManager)
        assert 'Authorization' in jira_client.headers
        assert 'Accept' in jira_client.headers
        assert jira_client.headers['Accept'] == 'application/json'

    def test_get_ticket_success(
        self,
        jira_client: JiraApiClient,
        mock_response: Mock,
        sample_ticket_data: Dict[str, Any],
        monkeypatch: MonkeyPatch
    ) -> None:
        """Test successful ticket retrieval."""
        mock_response.status = 200
        mock_response.data = json.dumps(sample_ticket_data).encode('utf-8')
        
        def mock_request(*args: Any, **kwargs: Any) -> Mock:
            return mock_response
        
        monkeypatch.setattr(jira_client.http, 'request', mock_request)
        
        ticket: Optional[JiraTicket] = jira_client.get_ticket('TEST-123')
        
        assert isinstance(ticket, JiraTicket)
        assert ticket.id == 'TEST-123'
        assert ticket.title == 'Test ticket'
        assert ticket.description == 'Test description'
        assert ticket.status == 'Open'
        assert ticket.assignee == 'John Doe'
        assert ticket.project_key == 'TEST'

    def test_get_ticket_not_found(
        self,
        jira_client: JiraApiClient,
        mock_response: Mock,
        monkeypatch: MonkeyPatch
    ) -> None:
        """Test ticket not found scenario."""
        mock_response.status = 404
        
        def mock_request(*args: Any, **kwargs: Any) -> Mock:
            return mock_response
        
        monkeypatch.setattr(jira_client.http, 'request', mock_request)
        
        ticket: Optional[JiraTicket] = jira_client.get_ticket('TEST-999')
        assert ticket is None

    def test_get_ticket_error(
        self,
        jira_client: JiraApiClient,
        mock_response: Mock,
        monkeypatch: MonkeyPatch
    ) -> None:
        """Test error handling in get_ticket."""
        mock_response.status = 500
        
        def mock_request(*args: Any, **kwargs: Any) -> Mock:
            return mock_response
        
        monkeypatch.setattr(jira_client.http, 'request', mock_request)
        
        with pytest.raises(urllib3.exceptions.HTTPError):
            jira_client.get_ticket('TEST-123')

    def test_search_tickets_success(
        self,
        jira_client: JiraApiClient,
        mock_response: Mock,
        sample_search_data: Dict[str, list[Dict[str, Any]]],
        monkeypatch: MonkeyPatch
    ) -> None:
        """Test successful ticket search."""
        mock_response.status = 200
        mock_response.data = json.dumps(sample_search_data).encode('utf-8')
        
        def mock_request(*args: Any, **kwargs: Any) -> Mock:
            assert kwargs['fields']['jql'] == 'project = TEST'
            assert kwargs['fields']['maxResults'] == 2
            return mock_response
        
        monkeypatch.setattr(jira_client.http, 'request', mock_request)
        
        tickets: list[JiraTicket] = jira_client.search_tickets('project = TEST', max_results=2)
        
        assert len(tickets) == 2
        assert isinstance(tickets[0], JiraTicket)
        assert tickets[0].id == 'TEST-1'
        assert tickets[0].assignee == 'John Doe'
        assert tickets[1].id == 'TEST-2'
        assert tickets[1].assignee is None
        assert tickets[1].description == ''

    def test_search_tickets_error(
        self,
        jira_client: JiraApiClient,
        mock_response: Mock,
        monkeypatch: MonkeyPatch
    ) -> None:
        """Test error handling in search_tickets."""
        mock_response.status = 400
        
        def mock_request(*args: Any, **kwargs: Any) -> Mock:
            return mock_response
        
        monkeypatch.setattr(jira_client.http, 'request', mock_request)
        
        with pytest.raises(urllib3.exceptions.HTTPError):
            jira_client.search_tickets('invalid jql')

    @pytest.mark.parametrize("ticket_data,expected_assignee", [
        ({
            'key': 'TEST-1',
            'fields': {
                'summary': 'Test',
                'description': 'Test',
                'status': {'name': 'Open'},
                'assignee': {'displayName': 'John Doe'},
                'project': {'key': 'TEST'}
            }
        }, 'John Doe'),
        ({
            'key': 'TEST-2',
            'fields': {
                'summary': 'Test',
                'description': 'Test',
                'status': {'name': 'Open'},
                'assignee': None,
                'project': {'key': 'TEST'}
            }
        }, None),
    ])
    def test_ticket_assignee_handling(
        self,
        jira_client: JiraApiClient,
        mock_response: Mock,
        ticket_data: Dict[str, Any],
        expected_assignee: Optional[str],
        monkeypatch: MonkeyPatch
    ) -> None:
        """Test handling of different assignee scenarios."""
        mock_response.status = 200
        mock_response.data = json.dumps(ticket_data).encode('utf-8')
        
        def mock_request(*args: Any, **kwargs: Any) -> Mock:
            return mock_response
        
        monkeypatch.setattr(jira_client.http, 'request', mock_request)
        
        ticket: Optional[JiraTicket] = jira_client.get_ticket(ticket_data['key'])
        assert ticket is not None
        assert ticket.assignee == expected_assignee

    def test_ticket_serialize(self, sample_ticket_data: Dict[str, Any]) -> None:
        """Test JiraTicket serialization from API response data."""
        ticket = JiraTicket.serialize(sample_ticket_data)
        
        assert isinstance(ticket, JiraTicket)
        assert ticket.id == 'TEST-123'
        assert ticket.title == 'Test ticket'
        assert ticket.description == 'Test description'
        assert ticket.status == 'Open'
        assert ticket.assignee == 'John Doe'
        assert ticket.project_key == 'TEST'

    def test_tickets_serialize_list(self, sample_search_data: Dict[str, list[Dict[str, Any]]]) -> None:
        """Test JiraTicket list serialization from API search response data."""
        tickets = JiraTicket.serialize_list(sample_search_data)
        
        assert len(tickets) == 2
        assert all(isinstance(ticket, JiraTicket) for ticket in tickets)
        assert tickets[0].id == 'TEST-1'
        assert tickets[0].assignee == 'John Doe'
        assert tickets[1].id == 'TEST-2'
        assert tickets[1].assignee is None
        assert tickets[1].description == ''
