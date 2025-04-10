"""
ClickUp data models for task details and related entities.
This module contains dataclasses that represent the ClickUp API response structures.
"""

from __future__ import annotations  # Enable forward references

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ClickUpUser:
    """Represents a ClickUp user entity"""

    id: int
    username: str
    email: str
    color: str
    profile_picture: Optional[str] = None

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ClickUpUser:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            id=int(data.get("id", 0)),  # Ensure int type
            username=str(data.get("username", "")),
            email=str(data.get("email", "")),
            color=str(data.get("color", "")),
            profile_picture=str(data.get("profilePicture")) if data.get("profilePicture") else None,
        )


@dataclass
class ClickUpStatus:
    """Represents a ClickUp task status"""

    status: str
    color: str
    type: str
    orderindex: int

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ClickUpStatus:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            status=str(data.get("status", "")),
            color=str(data.get("color", "")),
            type=str(data.get("type", "")),
            orderindex=int(data.get("orderindex", 0)),
        )


@dataclass
class ClickUpPriority:
    """Represents a ClickUp task priority"""

    priority: str
    color: str

    @classmethod
    def deserialize(cls, data: Optional[Dict[str, Any]]) -> Optional[ClickUpPriority]:
        if not data:
            return None
        return cls(
            priority=str(data.get("priority", "")),
            color=str(data.get("color", "")),
        )


@dataclass
class ClickUpTag:
    """Represents a ClickUp task tag"""

    name: str
    tag_fg: str
    tag_bg: str
    creator: int

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ClickUpTag:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            name=str(data.get("name", "")),
            tag_fg=str(data.get("tag_fg", "")),
            tag_bg=str(data.get("tag_bg", "")),
            creator=int(data.get("creator", 0)),
        )


@dataclass
class ClickUpChecklistItem:
    """Represents an item in a ClickUp checklist"""

    id: str
    name: str
    orderindex: int
    assignee: Optional[ClickUpUser]
    checked: bool
    date_created: datetime

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ClickUpChecklistItem:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            orderindex=int(data.get("orderindex", 0)),
            assignee=ClickUpUser.deserialize(data["assignee"]) if data.get("assignee") else None,
            checked=bool(data.get("checked", False)),
            date_created=datetime.fromtimestamp(int(data.get("date_created", 0)) / 1000),
        )


@dataclass
class ClickUpChecklist:
    """Represents a ClickUp checklist"""

    id: str
    name: str
    orderindex: int
    items: List[ClickUpChecklistItem]

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ClickUpChecklist:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            orderindex=int(data.get("orderindex", 0)),
            items=[ClickUpChecklistItem.deserialize(item) for item in data.get("items", [])],
        )


@dataclass
class ClickUpCustomField:
    """Represents a custom field in a ClickUp task"""

    id: str
    name: str
    type: str
    type_config: Dict[str, Any]
    date_created: datetime
    hide_from_guests: bool
    value: Any
    required: bool

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ClickUpCustomField:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            type=str(data.get("type", "")),
            type_config=dict(data.get("type_config", {})),
            date_created=datetime.fromtimestamp(int(data.get("date_created", 0)) / 1000),
            hide_from_guests=bool(data.get("hide_from_guests", False)),
            value=data.get("value"),
            required=bool(data.get("required", False)),
        )


@dataclass
class ClickUpLocation:
    """Represents a location in ClickUp (list, project, folder, or space)"""

    id: str
    name: str
    hidden: bool = False
    access: bool = True

    @classmethod
    def deserialize(cls, data: Optional[Dict[str, Any]]) -> Optional[ClickUpLocation]:
        if not data:
            return None
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            hidden=bool(data.get("hidden", False)),
            access=bool(data.get("access", True)),
        )


@dataclass
class ClickUpTask:
    """
    Represents a ClickUp task with all its details.
    This is the main data model that encapsulates all task-related information.
    """

    id: str
    name: str
    text_content: Optional[str]
    description: Optional[str]
    status: ClickUpStatus
    orderindex: str
    date_created: datetime
    date_updated: datetime
    date_closed: Optional[datetime]
    creator: ClickUpUser
    assignees: List[ClickUpUser]
    watchers: List[ClickUpUser]
    checklists: List[ClickUpChecklist]
    tags: List[ClickUpTag]
    parent: Optional[str]
    priority: Optional[ClickUpPriority]
    due_date: Optional[datetime]
    start_date: Optional[datetime]
    points: Optional[float]
    time_estimate: Optional[int]  # in milliseconds
    time_spent: Optional[int]  # in milliseconds
    custom_fields: List[ClickUpCustomField]
    custom_id: Optional[str]
    url: str
    permission_level: str
    list: Optional[ClickUpLocation]
    project: Optional[ClickUpLocation]
    folder: Optional[ClickUpLocation]
    space: Optional[ClickUpLocation]

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ClickUpTask:
        """
        Create a ClickUpTask instance from a dictionary (typically from API response).

        Args:
            data: The task data from the ClickUp API

        Returns:
            A new instance with the provided data

        Raises:
            ValueError: If input data is not a dictionary
        """
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            text_content=str(data.get("text_content")) if data.get("text_content") else None,
            description=str(data.get("description")) if data.get("description") else None,
            status=ClickUpStatus.deserialize(data.get("status", {})),
            orderindex=str(data.get("orderindex", "0")),
            date_created=datetime.fromtimestamp(int(data.get("date_created", 0)) / 1000),
            date_updated=datetime.fromtimestamp(int(data.get("date_updated", 0)) / 1000),
            date_closed=(
                datetime.fromtimestamp(int(data.get("date_closed", 0)) / 1000) if data.get("date_closed") else None
            ),
            creator=ClickUpUser.deserialize(data.get("creator", {})),
            assignees=[ClickUpUser.deserialize(u) for u in data.get("assignees", [])],
            watchers=[ClickUpUser.deserialize(u) for u in data.get("watchers", [])],
            checklists=[ClickUpChecklist.deserialize(c) for c in data.get("checklists", [])],
            tags=[ClickUpTag.deserialize(t) for t in data.get("tags", [])],
            parent=str(data.get("parent")) if data.get("parent") else None,
            priority=ClickUpPriority.deserialize(data.get("priority")) if data.get("priority") else None,
            due_date=datetime.fromtimestamp(int(data.get("due_date", 0)) / 1000) if data.get("due_date") else None,
            start_date=(
                datetime.fromtimestamp(int(data.get("start_date", 0)) / 1000) if data.get("start_date") else None
            ),
            points=float(str(data.get("points", 0.0))) if data.get("points") is not None else None,
            time_estimate=int(data.get("time_estimate", 0)) if data.get("time_estimate") is not None else None,
            time_spent=int(data.get("time_spent", 0)) if data.get("time_spent") is not None else None,
            custom_fields=[ClickUpCustomField.deserialize(f) for f in data.get("custom_fields", [])],
            custom_id=str(data.get("custom_id")) if data.get("custom_id") else None,
            url=str(data.get("url", "")),
            permission_level=str(data.get("permission_level", "")),
            list=ClickUpLocation.deserialize(data.get("list")) if data.get("list") else None,
            project=ClickUpLocation.deserialize(data.get("project")) if data.get("project") else None,
            folder=ClickUpLocation.deserialize(data.get("folder")) if data.get("folder") else None,
            space=ClickUpLocation.deserialize(data.get("space")) if data.get("space") else None,
        )
