"""
ClickUp data models for task details and related entities.
This module contains dataclasses that represent the ClickUp API response structures.
"""

from dataclasses import dataclass
from typing import List, Optional, Any
from datetime import datetime


@dataclass
class ClickUpUser:
    """Represents a ClickUp user entity"""
    id: int
    username: str
    email: str
    color: str
    profile_picture: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'ClickUpUser':
        return cls(
            id=data.get('id'),
            username=data.get('username'),
            email=data.get('email'),
            color=data.get('color'),
            profile_picture=data.get('profilePicture')
        )


@dataclass
class ClickUpStatus:
    """Represents a ClickUp task status"""
    status: str
    color: str
    type: str
    orderindex: int

    @classmethod
    def from_dict(cls, data: dict) -> 'ClickUpStatus':
        return cls(
            status=data.get('status'),
            color=data.get('color'),
            type=data.get('type'),
            orderindex=data.get('orderindex', 0)
        )


@dataclass
class ClickUpPriority:
    """Represents a ClickUp task priority"""
    priority: str
    color: str

    @classmethod
    def from_dict(cls, data: dict) -> Optional['ClickUpPriority']:
        if not data:
            return None
        return cls(
            priority=data.get('priority'),
            color=data.get('color')
        )


@dataclass
class ClickUpTag:
    """Represents a ClickUp task tag"""
    name: str
    tag_fg: str
    tag_bg: str
    creator: int

    @classmethod
    def from_dict(cls, data: dict) -> 'ClickUpTag':
        return cls(
            name=data.get('name'),
            tag_fg=data.get('tag_fg'),
            tag_bg=data.get('tag_bg'),
            creator=data.get('creator')
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
    def from_dict(cls, data: dict) -> 'ClickUpChecklistItem':
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            orderindex=data.get('orderindex', 0),
            assignee=ClickUpUser.from_dict(data['assignee']) if data.get('assignee') else None,
            checked=data.get('checked', False),
            date_created=datetime.fromtimestamp(int(data.get('date_created', 0)) / 1000)
        )


@dataclass
class ClickUpChecklist:
    """Represents a ClickUp checklist"""
    id: str
    name: str
    orderindex: int
    items: List[ClickUpChecklistItem]

    @classmethod
    def from_dict(cls, data: dict) -> 'ClickUpChecklist':
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            orderindex=data.get('orderindex', 0),
            items=[ClickUpChecklistItem.from_dict(item) for item in data.get('items', [])]
        )


@dataclass
class ClickUpCustomField:
    """Represents a custom field in a ClickUp task"""
    id: str
    name: str
    type: str
    type_config: dict
    date_created: datetime
    hide_from_guests: bool
    value: Any
    required: bool

    @classmethod
    def from_dict(cls, data: dict) -> 'ClickUpCustomField':
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            type=data.get('type'),
            type_config=data.get('type_config', {}),
            date_created=datetime.fromtimestamp(int(data.get('date_created', 0)) / 1000),
            hide_from_guests=data.get('hide_from_guests', False),
            value=data.get('value'),
            required=data.get('required', False)
        )


@dataclass
class ClickUpLocation:
    """Represents a location in ClickUp (list, project, folder, or space)"""
    id: str
    name: str
    hidden: bool = False
    access: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> Optional['ClickUpLocation']:
        if not data:
            return None
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            hidden=data.get('hidden', False),
            access=data.get('access', True)
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
    time_spent: Optional[int]     # in milliseconds
    custom_fields: List[ClickUpCustomField]
    custom_id: Optional[str]
    url: str
    permission_level: str
    list: Optional[ClickUpLocation]
    project: Optional[ClickUpLocation]
    folder: Optional[ClickUpLocation]
    space: Optional[ClickUpLocation]

    @classmethod
    def from_dict(cls, data: dict) -> 'ClickUpTask':
        """
        Create a ClickUpTask instance from a dictionary (typically from API response).
        
        Args:
            data (dict): The task data from the ClickUp API
            
        Returns:
            ClickUpTask: A new instance with the provided data
        """
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            text_content=data.get('text_content'),
            description=data.get('description'),
            status=ClickUpStatus.from_dict(data.get('status', {})),
            orderindex=data.get('orderindex', '0'),
            date_created=datetime.fromtimestamp(int(data.get('date_created', 0)) / 1000),
            date_updated=datetime.fromtimestamp(int(data.get('date_updated', 0)) / 1000),
            date_closed=datetime.fromtimestamp(int(data.get('date_closed', 0)) / 1000) if data.get('date_closed') else None,
            creator=ClickUpUser.from_dict(data.get('creator', {})),
            assignees=[ClickUpUser.from_dict(u) for u in data.get('assignees', [])],
            watchers=[ClickUpUser.from_dict(u) for u in data.get('watchers', [])],
            checklists=[ClickUpChecklist.from_dict(c) for c in data.get('checklists', [])],
            tags=[ClickUpTag.from_dict(t) for t in data.get('tags', [])],
            parent=data.get('parent'),
            priority=ClickUpPriority.from_dict(data.get('priority')) if data.get('priority') else None,
            due_date=datetime.fromtimestamp(int(data.get('due_date', 0)) / 1000) if data.get('due_date') else None,
            start_date=datetime.fromtimestamp(int(data.get('start_date', 0)) / 1000) if data.get('start_date') else None,
            points=data.get('points'),
            time_estimate=data.get('time_estimate'),
            time_spent=data.get('time_spent'),
            custom_fields=[ClickUpCustomField.from_dict(f) for f in data.get('custom_fields', [])],
            custom_id=data.get('custom_id'),
            url=data.get('url'),
            permission_level=data.get('permission_level'),
            list=ClickUpLocation.from_dict(data.get('list')) if data.get('list') else None,
            project=ClickUpLocation.from_dict(data.get('project')) if data.get('project') else None,
            folder=ClickUpLocation.from_dict(data.get('folder')) if data.get('folder') else None,
            space=ClickUpLocation.from_dict(data.get('space')) if data.get('space') else None
        )
