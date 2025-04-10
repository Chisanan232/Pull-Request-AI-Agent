from typing import Any, Dict, Optional

import pytest

from create_pr_bot.project_management_tool.jira.model import JiraTicket


class TestJiraTicket:
    """Test cases for JiraTicket model."""

    @pytest.fixture
    def sample_ticket_data(self) -> Dict[str, Any]:
        """Fixture for a single ticket data."""
        return {
            "key": "TEST-123",
            "fields": {
                "summary": "Test ticket",
                "description": "Test description",
                "status": {"name": "Open"},
                "assignee": {"displayName": "John Doe"},
                "project": {"key": "TEST"},
            },
        }

    @pytest.fixture
    def sample_search_data(self) -> Dict[str, list[Dict[str, Any]]]:
        """Fixture for search results data containing multiple tickets."""
        return {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "First ticket",
                        "description": "First description",
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "John Doe"},
                        "project": {"key": "TEST"},
                    },
                },
                {
                    "key": "TEST-2",
                    "fields": {
                        "summary": "Second ticket",
                        "description": None,
                        "status": {"name": "In Progress"},
                        "assignee": None,
                        "project": {"key": "TEST"},
                    },
                },
            ]
        }

    def test_serialize_basic(self, sample_ticket_data: Dict[str, Any]) -> None:
        """Test basic ticket serialization with all fields present."""
        ticket = JiraTicket.serialize(sample_ticket_data)

        assert isinstance(ticket, JiraTicket)
        assert ticket.id == "TEST-123"
        assert ticket.title == "Test ticket"
        assert ticket.description == "Test description"
        assert ticket.status == "Open"
        assert ticket.assignee == "John Doe"
        assert ticket.project_key == "TEST"

    def test_serialize_with_missing_description(self) -> None:
        """Test ticket serialization with missing description."""
        data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test ticket",
                "description": None,
                "status": {"name": "Open"},
                "assignee": {"displayName": "John Doe"},
                "project": {"key": "TEST"},
            },
        }

        ticket = JiraTicket.serialize(data)
        assert ticket.description == ""

    def test_serialize_with_missing_assignee(self) -> None:
        """Test ticket serialization with missing assignee."""
        data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test ticket",
                "description": "Test description",
                "status": {"name": "Open"},
                "assignee": None,
                "project": {"key": "TEST"},
            },
        }

        ticket = JiraTicket.serialize(data)
        assert ticket.assignee is None

    def test_serialize_list_basic(self, sample_search_data: Dict[str, list[Dict[str, Any]]]) -> None:
        """Test basic list serialization with multiple tickets."""
        tickets = JiraTicket.serialize_list(sample_search_data)

        assert len(tickets) == 2
        assert all(isinstance(ticket, JiraTicket) for ticket in tickets)

        # Check first ticket
        assert tickets[0].id == "TEST-1"
        assert tickets[0].title == "First ticket"
        assert tickets[0].description == "First description"
        assert tickets[0].status == "Open"
        assert tickets[0].assignee == "John Doe"
        assert tickets[0].project_key == "TEST"

        # Check second ticket
        assert tickets[1].id == "TEST-2"
        assert tickets[1].title == "Second ticket"
        assert tickets[1].description == ""  # None converted to empty string
        assert tickets[1].status == "In Progress"
        assert tickets[1].assignee is None
        assert tickets[1].project_key == "TEST"

    def test_serialize_list_empty(self) -> None:
        """Test list serialization with empty results."""
        data = {"issues": []}
        tickets = JiraTicket.serialize_list(data)
        assert len(tickets) == 0
        assert isinstance(tickets, list)

    def test_serialize_with_invalid_data(self) -> None:
        """Test serialization with invalid data structure."""
        invalid_data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test ticket"
                # Missing required fields
            },
        }

        with pytest.raises(KeyError):
            JiraTicket.serialize(invalid_data)

    @pytest.mark.parametrize(
        "field_value,expected",
        [
            ({"displayName": "John Doe"}, "John Doe"),
            (None, None),
            ({}, None),  # Empty dict should be treated as no assignee
            ({"displayName": None}, None),  # None display name should be treated as no assignee
        ],
    )
    def test_serialize_assignee_variations(self, field_value: Any, expected: Optional[str]) -> None:
        """Test different variations of assignee field values."""
        data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test ticket",
                "description": "Test description",
                "status": {"name": "Open"},
                "assignee": field_value,
                "project": {"key": "TEST"},
            },
        }

        ticket = JiraTicket.serialize(data)
        assert ticket.assignee == expected

    def test_serialize_preserves_dataclass_immutability(self, sample_ticket_data: Dict[str, Any]) -> None:
        """Test that serialized ticket instances maintain dataclass immutability."""
        ticket = JiraTicket.serialize(sample_ticket_data)

        with pytest.raises(AttributeError):
            ticket.id = "NEW-ID"  # Should raise error if JiraTicket is frozen
