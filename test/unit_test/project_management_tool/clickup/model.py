import pytest
from datetime import datetime
from create_pr_bot.project_management_tool.clickup.model import (
    ClickUpUser,
    ClickUpStatus,
    ClickUpPriority,
    ClickUpTag,
    ClickUpChecklistItem,
    ClickUpChecklist,
    ClickUpCustomField,
    ClickUpLocation,
    ClickUpTask
)


class TestClickUpUser:
    def test_deserialize_complete_data(self):
        data = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "color": "#FF0000",
            "profilePicture": "https://example.com/pic.jpg"
        }
        user = ClickUpUser.deserialize(data)
        assert user.id == 123
        assert user.username == "test_user"
        assert user.email == "test@example.com"
        assert user.color == "#FF0000"
        assert user.profile_picture == "https://example.com/pic.jpg"

    def test_deserialize_minimal_data(self):
        data = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "color": "#FF0000"
        }
        user = ClickUpUser.deserialize(data)
        assert user.profile_picture is None


class TestClickUpStatus:
    def test_deserialize_complete_data(self):
        data = {
            "status": "in progress",
            "color": "#YELLOW",
            "type": "custom",
            "orderindex": 1
        }
        status = ClickUpStatus.deserialize(data)
        assert status.status == "in progress"
        assert status.color == "#YELLOW"
        assert status.type == "custom"
        assert status.orderindex == 1

    def test_deserialize_with_default_orderindex(self):
        data = {
            "status": "in progress",
            "color": "#YELLOW",
            "type": "custom"
        }
        status = ClickUpStatus.deserialize(data)
        assert status.orderindex == 0


class TestClickUpPriority:
    def test_deserialize_complete_data(self):
        data = {
            "priority": "high",
            "color": "#FF0000"
        }
        priority = ClickUpPriority.deserialize(data)
        assert priority.priority == "high"
        assert priority.color == "#FF0000"

    def test_deserialize_none_data(self):
        priority = ClickUpPriority.deserialize(None)
        assert priority is None


class TestClickUpTag:
    def test_deserialize_complete_data(self):
        data = {
            "name": "test_tag",
            "tag_fg": "#FFFFFF",
            "tag_bg": "#000000",
            "creator": 123
        }
        tag = ClickUpTag.deserialize(data)
        assert tag.name == "test_tag"
        assert tag.tag_fg == "#FFFFFF"
        assert tag.tag_bg == "#000000"
        assert tag.creator == 123


class TestClickUpChecklistItem:
    def test_deserialize_complete_data(self):
        data = {
            "id": "item123",
            "name": "Test Item",
            "orderindex": 1,
            "assignee": {
                "id": 123,
                "username": "test_user",
                "email": "test@example.com",
                "color": "#FF0000"
            },
            "checked": True,
            "date_created": 1625097600000  # 2021-07-01 00:00:00 UTC
        }
        item = ClickUpChecklistItem.deserialize(data)
        assert item.id == "item123"
        assert item.name == "Test Item"
        assert item.orderindex == 1
        assert item.assignee.username == "test_user"
        assert item.checked is True
        assert isinstance(item.date_created, datetime)

    def test_deserialize_without_assignee(self):
        data = {
            "id": "item123",
            "name": "Test Item",
            "orderindex": 1,
            "checked": True,
            "date_created": 1625097600000
        }
        item = ClickUpChecklistItem.deserialize(data)
        assert item.assignee is None


class TestClickUpChecklist:
    def test_deserialize_complete_data(self):
        data = {
            "id": "checklist123",
            "name": "Test Checklist",
            "orderindex": 1,
            "items": [
                {
                    "id": "item123",
                    "name": "Test Item",
                    "orderindex": 1,
                    "checked": True,
                    "date_created": 1625097600000
                }
            ]
        }
        checklist = ClickUpChecklist.deserialize(data)
        assert checklist.id == "checklist123"
        assert checklist.name == "Test Checklist"
        assert checklist.orderindex == 1
        assert len(checklist.items) == 1
        assert checklist.items[0].name == "Test Item"


class TestClickUpCustomField:
    def test_deserialize_complete_data(self):
        data = {
            "id": "field123",
            "name": "Test Field",
            "type": "text",
            "type_config": {"default": "test"},
            "date_created": 1625097600000,
            "hide_from_guests": False,
            "value": "test value",
            "required": True
        }
        field = ClickUpCustomField.deserialize(data)
        assert field.id == "field123"
        assert field.name == "Test Field"
        assert field.type == "text"
        assert field.type_config == {"default": "test"}
        assert isinstance(field.date_created, datetime)
        assert field.hide_from_guests is False
        assert field.value == "test value"
        assert field.required is True


class TestClickUpLocation:
    def test_deserialize_complete_data(self):
        data = {
            "id": "loc123",
            "name": "Test Location",
            "hidden": True,
            "access": False
        }
        location = ClickUpLocation.deserialize(data)
        assert location.id == "loc123"
        assert location.name == "Test Location"
        assert location.hidden is True
        assert location.access is False

    def test_deserialize_none_data(self):
        location = ClickUpLocation.deserialize(None)
        assert location is None


class TestClickUpTask:
    @pytest.fixture
    def complete_task_data(self):
        return {
            "id": "task123",
            "name": "Test Task",
            "text_content": "Test Content",
            "description": "Test Description",
            "status": {
                "status": "in progress",
                "color": "#YELLOW",
                "type": "custom",
                "orderindex": 1
            },
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "date_closed": None,
            "creator": {
                "id": 123,
                "username": "test_user",
                "email": "test@example.com",
                "color": "#FF0000"
            },
            "assignees": [],
            "watchers": [],
            "checklists": [],
            "tags": [],
            "parent": None,
            "priority": {
                "priority": "high",
                "color": "#FF0000"
            },
            "due_date": 1625184000000,
            "start_date": 1625097600000,
            "points": 5,
            "time_estimate": 3600000,
            "time_spent": 1800000,
            "custom_fields": [],
            "custom_id": "TASK-123",
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
            "list": {
                "id": "list123",
                "name": "Test List",
                "access": True
            },
            "project": {
                "id": "proj123",
                "name": "Test Project",
                "access": True
            },
            "folder": {
                "id": "folder123",
                "name": "Test Folder",
                "access": True
            },
            "space": {
                "id": "space123"
            }
        }

    def test_deserialize_complete_data(self, complete_task_data):
        task = ClickUpTask.deserialize(complete_task_data)
        assert task.id == "task123"
        assert task.name == "Test Task"
        assert task.text_content == "Test Content"
        assert task.description == "Test Description"
        assert isinstance(task.status, ClickUpStatus)
        assert task.status.status == "in progress"
        assert isinstance(task.creator, ClickUpUser)
        assert task.creator.username == "test_user"
        assert isinstance(task.date_created, datetime)
        assert isinstance(task.date_updated, datetime)
        assert task.date_closed is None
        assert isinstance(task.priority, ClickUpPriority)
        assert task.priority.priority == "high"
        assert isinstance(task.due_date, datetime)
        assert isinstance(task.start_date, datetime)
        assert task.points == 5
        assert task.time_estimate == 3600000
        assert task.time_spent == 1800000
        assert task.custom_id == "TASK-123"
        assert task.url == "https://app.clickup.com/t/task123"
        assert task.permission_level == "read"
        assert isinstance(task.list, ClickUpLocation)
        assert task.list.name == "Test List"
        assert isinstance(task.project, ClickUpLocation)
        assert task.project.name == "Test Project"
        assert isinstance(task.folder, ClickUpLocation)
        assert task.folder.name == "Test Folder"
        assert isinstance(task.space, ClickUpLocation)
        assert task.space.id == "space123"

    def test_deserialize_minimal_data(self):
        minimal_data = {
            "id": "task123",
            "name": "Test Task",
            "status": {
                "status": "in progress",
                "color": "#YELLOW",
                "type": "custom",
                "orderindex": 1
            },
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": {
                "id": 123,
                "username": "test_user",
                "email": "test@example.com",
                "color": "#FF0000"
            },
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read"
        }
        task = ClickUpTask.deserialize(minimal_data)
        assert task.id == "task123"
        assert task.text_content is None
        assert task.description is None
        assert task.date_closed is None
        assert task.parent is None
        assert task.priority is None
        assert task.due_date is None
        assert task.start_date is None
        assert task.points is None
        assert task.time_estimate is None
        assert task.time_spent is None
        assert task.custom_id is None
        assert len(task.assignees) == 0
        assert len(task.watchers) == 0
        assert len(task.checklists) == 0
        assert len(task.tags) == 0
        assert len(task.custom_fields) == 0
