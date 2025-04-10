from dataclasses import dataclass
from typing import Optional

@dataclass
class JiraTicket:
    """Represents a JIRA ticket with essential fields."""
    
    id: str
    title: str
    description: str
    status: str
    assignee: Optional[str]
    project_key: str
