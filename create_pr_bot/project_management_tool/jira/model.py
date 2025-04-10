from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class JiraTicket:
    """Represents a JIRA ticket with essential fields."""

    id: str
    title: str
    description: str
    status: str
    assignee: Optional[str]
    project_key: str

    @classmethod
    def serialize(cls, data: Dict[str, Any]) -> "JiraTicket":
        """
        Create a JiraTicket instance from JIRA API response data.

        Args:
            data: Dictionary containing JIRA issue data from API response

        Returns:
            JiraTicket instance populated with the API data
        """
        fields = data["fields"]
        return cls(
            id=data["key"],
            title=fields["summary"],
            description=fields["description"] or "",
            status=fields["status"]["name"],
            assignee=fields["assignee"]["displayName"] if fields["assignee"] else None,
            project_key=fields["project"]["key"],
        )

    @classmethod
    def serialize_list(cls, data: Dict[str, Any]) -> list["JiraTicket"]:
        """
        Create a list of JiraTicket instances from JIRA API search response.

        Args:
            data: Dictionary containing JIRA search results from API response

        Returns:
            List of JiraTicket instances
        """
        return [cls.serialize(issue) for issue in data["issues"]]
