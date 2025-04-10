from datetime import datetime

import pytest

from create_pr_bot.project_management_tool.clickup.model import (
    ClickUpChecklist,
    ClickUpChecklistItem,
    ClickUpCustomField,
    ClickUpLocation,
    ClickUpPriority,
    ClickUpStatus,
    ClickUpTag,
    ClickUpTask,
    ClickUpUser,
)


class TestClickUpUser:
    def test_deserialize_complete_data(self):
        data = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "color": "#FF0000",
            "profilePicture": "https://example.com/pic.jpg",
        }
        user = ClickUpUser.deserialize(data)
        assert user.id == 123
        assert user.username == "test_user"
        assert user.email == "test@example.com"
        assert user.color == "#FF0000"
        assert user.profile_picture == "https://example.com/pic.jpg"

    def test_deserialize_minimal_data(self):
        data = {"id": 123, "username": "test_user", "email": "test@example.com", "color": "#FF0000"}
        user = ClickUpUser.deserialize(data)
        assert user.profile_picture is None

    def test_deserialize_invalid_data_type(self):
        """Test deserialize with invalid data types should raise ValueError"""
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpUser.deserialize(None)  # type: ignore
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpUser.deserialize([])  # type: ignore
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpUser.deserialize("invalid")  # type: ignore

    def test_deserialize_empty_dict(self):
        """Test deserialize with empty dictionary"""
        user = ClickUpUser.deserialize({})
        assert user.id == 0
        assert user.username == ""
        assert user.email == ""
        assert user.color == ""
        assert user.profile_picture is None

    def test_deserialize_invalid_id_type(self):
        """Test deserialize with invalid ID type should raise ValueError"""
        with pytest.raises(ValueError):
            ClickUpUser.deserialize(
                {"id": "not_a_number", "username": "test", "email": "test@test.com", "color": "#000"}
            )


class TestClickUpStatus:
    def test_deserialize_complete_data(self):
        data = {"status": "in progress", "color": "#YELLOW", "type": "custom", "orderindex": 1}
        status = ClickUpStatus.deserialize(data)
        assert status.status == "in progress"
        assert status.color == "#YELLOW"
        assert status.type == "custom"
        assert status.orderindex == 1

    def test_deserialize_with_default_orderindex(self):
        data = {"status": "in progress", "color": "#YELLOW", "type": "custom"}
        status = ClickUpStatus.deserialize(data)
        assert status.orderindex == 0

    def test_deserialize_invalid_data_type(self):
        """Test deserialize with invalid data types should raise ValueError"""
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpStatus.deserialize(None)  # type: ignore
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpStatus.deserialize([])  # type: ignore

    def test_deserialize_empty_dict(self):
        """Test deserialize with empty dictionary"""
        status = ClickUpStatus.deserialize({})
        assert status.status == ""
        assert status.color == ""
        assert status.type == ""
        assert status.orderindex == 0

    def test_deserialize_invalid_orderindex_type(self):
        """Test deserialize with invalid orderindex type should raise ValueError"""
        with pytest.raises(ValueError):
            ClickUpStatus.deserialize(
                {"status": "test", "color": "#000", "type": "custom", "orderindex": "not_a_number"}
            )


class TestClickUpPriority:
    def test_deserialize_complete_data(self):
        data = {"priority": "high", "color": "#FF0000"}
        priority = ClickUpPriority.deserialize(data)
        assert priority.priority == "high"
        assert priority.color == "#FF0000"

    def test_deserialize_none_data(self):
        priority = ClickUpPriority.deserialize(None)
        assert priority is None

    def test_deserialize_empty_dict(self):
        """Test deserialize with empty dictionary"""
        priority = ClickUpPriority.deserialize({})
        assert priority is None

    def test_deserialize_invalid_data_types(self):
        """Test deserialize with invalid data types"""
        assert ClickUpPriority.deserialize(None) is None
        assert ClickUpPriority.deserialize({}) is None


class TestClickUpTag:
    def test_deserialize_complete_data(self):
        data = {"name": "test_tag", "tag_fg": "#FFFFFF", "tag_bg": "#000000", "creator": 123}
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
            "assignee": {"id": 123, "username": "test_user", "email": "test@example.com", "color": "#FF0000"},
            "checked": True,
            "date_created": 1625097600000,  # 2021-07-01 00:00:00 UTC
        }
        item = ClickUpChecklistItem.deserialize(data)
        assert item.id == "item123"
        assert item.name == "Test Item"
        assert item.orderindex == 1
        assert item.assignee.username == "test_user"
        assert item.checked is True
        assert isinstance(item.date_created, datetime)

    def test_deserialize_without_assignee(self):
        data = {"id": "item123", "name": "Test Item", "orderindex": 1, "checked": True, "date_created": 1625097600000}
        item = ClickUpChecklistItem.deserialize(data)
        assert item.assignee is None

    def test_deserialize_invalid_data_type(self):
        """Test deserialize with invalid data types should raise ValueError"""
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpChecklistItem.deserialize(None)  # type: ignore
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpChecklistItem.deserialize([])  # type: ignore

    def test_deserialize_invalid_date_type(self):
        """Test deserialize with invalid date should raise ValueError"""
        data = {
            "id": "item123",
            "name": "Test Item",
            "orderindex": 1,
            "checked": True,
            "date_created": "not_a_timestamp",
        }
        with pytest.raises(ValueError):
            ClickUpChecklistItem.deserialize(data)

    def test_deserialize_invalid_assignee_type(self):
        """Test deserialize with invalid assignee data should raise ValueError"""
        data = {
            "id": "item123",
            "name": "Test Item",
            "orderindex": 1,
            "assignee": "invalid_assignee",  # Should be a dict
            "checked": True,
            "date_created": 1625097600000,
        }
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpChecklistItem.deserialize(data)

    def test_deserialize_empty_dict(self):
        """Test deserialize with empty dictionary"""
        item = ClickUpChecklistItem.deserialize({})
        assert item.id == ""
        assert item.name == ""
        assert item.orderindex == 0
        assert item.assignee is None
        assert item.checked is False
        assert isinstance(item.date_created, datetime)


class TestClickUpChecklist:
    def test_deserialize_complete_data(self):
        data = {
            "id": "checklist123",
            "name": "Test Checklist",
            "orderindex": 1,
            "items": [
                {"id": "item123", "name": "Test Item", "orderindex": 1, "checked": True, "date_created": 1625097600000}
            ],
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
            "required": True,
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

    def test_deserialize_invalid_data_type(self):
        """Test deserialize with invalid data types should raise ValueError"""
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpCustomField.deserialize(None)  # type: ignore
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpCustomField.deserialize([])  # type: ignore

    def test_deserialize_empty_dict(self):
        """Test deserialize with empty dictionary"""
        field = ClickUpCustomField.deserialize({})
        assert field.id == ""
        assert field.name == ""
        assert field.type == ""
        assert isinstance(field.type_config, dict)
        assert field.type_config == {}
        assert isinstance(field.date_created, datetime)
        assert field.hide_from_guests is False
        assert field.value is None
        assert field.required is False


class TestClickUpLocation:
    def test_deserialize_complete_data(self):
        data = {"id": "loc123", "name": "Test Location", "hidden": True, "access": False}
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
            "status": {"status": "in progress", "color": "#YELLOW", "type": "custom", "orderindex": 1},
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "date_closed": None,
            "creator": {"id": 123, "username": "test_user", "email": "test@example.com", "color": "#FF0000"},
            "assignees": [],
            "watchers": [],
            "checklists": [],
            "tags": [],
            "parent": None,
            "priority": {"priority": "high", "color": "#FF0000"},
            "due_date": 1625184000000,
            "start_date": 1625097600000,
            "points": 5,
            "time_estimate": 3600000,
            "time_spent": 1800000,
            "custom_fields": [],
            "custom_id": "TASK-123",
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
            "list": {"id": "list123", "name": "Test List", "access": True},
            "project": {"id": "proj123", "name": "Test Project", "access": True},
            "folder": {"id": "folder123", "name": "Test Folder", "access": True},
            "space": {"id": "space123"},
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
            "status": {"status": "in progress", "color": "#YELLOW", "type": "custom", "orderindex": 1},
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": {"id": 123, "username": "test_user", "email": "test@example.com", "color": "#FF0000"},
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
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

    def test_deserialize_invalid_data_type(self):
        """Test deserialize with invalid data types should raise ValueError"""
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpTask.deserialize(None)  # type: ignore
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpTask.deserialize([])  # type: ignore

    def test_deserialize_invalid_status_type(self):
        """Test deserialize with invalid status data should raise ValueError"""
        data = {
            "id": "task123",
            "name": "Test Task",
            "status": "invalid_status",  # Should be a dict
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": {"id": 123, "username": "test", "email": "test@test.com", "color": "#000"},
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
        }
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpTask.deserialize(data)

    def test_deserialize_invalid_creator_type(self):
        """Test deserialize with invalid creator data should raise ValueError"""
        data = {
            "id": "task123",
            "name": "Test Task",
            "status": {"status": "test", "color": "#000", "type": "custom", "orderindex": 1},
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": "invalid_creator",  # Should be a dict
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
        }
        with pytest.raises(ValueError, match="Input data must be a dictionary"):
            ClickUpTask.deserialize(data)

    def test_deserialize_invalid_numeric_values(self):
        """Test deserialize with invalid numeric values should raise ValueError"""
        data = {
            "id": "task123",
            "name": "Test Task",
            "status": {"status": "test", "color": "#000", "type": "custom", "orderindex": 1},
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": {"id": 123, "username": "test", "email": "test@test.com", "color": "#000"},
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
            "points": "not_a_number",
            "time_estimate": "not_a_number",
            "time_spent": "not_a_number",
        }
        with pytest.raises(ValueError):
            ClickUpTask.deserialize(data)

    def test_deserialize_invalid_dates(self):
        """Test deserialize with invalid dates should raise ValueError"""
        data = {
            "id": "task123",
            "name": "Test Task",
            "status": {"status": "test", "color": "#000", "type": "custom", "orderindex": 1},
            "orderindex": "1",
            "date_created": "invalid_date",
            "date_updated": "invalid_date",
            "creator": {"id": 123, "username": "test", "email": "test@test.com", "color": "#000"},
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
        }
        with pytest.raises(ValueError):
            ClickUpTask.deserialize(data)

    def test_deserialize_invalid_optional_dates(self):
        """Test deserialize with invalid optional dates should raise ValueError"""
        data = {
            "id": "task123",
            "name": "Test Task",
            "status": {"status": "test", "color": "#000", "type": "custom", "orderindex": 1},
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": {"id": 123, "username": "test", "email": "test@test.com", "color": "#000"},
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
            "due_date": "invalid_date",
            "start_date": "invalid_date",
            "date_closed": "invalid_date",
        }
        with pytest.raises(ValueError):
            ClickUpTask.deserialize(data)

    def test_deserialize_invalid_nested_objects(self):
        """Test deserialize with invalid nested objects should raise ValueError"""
        data = {
            "id": "task123",
            "name": "Test Task",
            "status": {
                "status": "test",
                "color": "#000",
                "type": "custom",
                "orderindex": "invalid",
            },  # Invalid orderindex
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": {"id": "invalid", "username": "test", "email": "test@test.com", "color": "#000"},  # Invalid id
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
        }
        with pytest.raises(ValueError):
            ClickUpTask.deserialize(data)

    def test_deserialize_invalid_list_items(self):
        """Test deserialize with invalid items in lists should raise ValueError"""
        data = {
            "id": "task123",
            "name": "Test Task",
            "status": {"status": "test", "color": "#000", "type": "custom", "orderindex": 1},
            "orderindex": "1",
            "date_created": 1625097600000,
            "date_updated": 1625097600000,
            "creator": {"id": 123, "username": "test", "email": "test@test.com", "color": "#000"},
            "url": "https://app.clickup.com/t/task123",
            "permission_level": "read",
            "assignees": [
                {"id": "invalid", "username": "test", "email": "test@test.com", "color": "#000"}  # Invalid id
            ],
        }
        with pytest.raises(ValueError):
            ClickUpTask.deserialize(data)

    def test_deserialize_empty_dict(self):
        """Test deserialize with empty dictionary"""
        task = ClickUpTask.deserialize({})
        assert task.id == ""
        assert task.name == ""
        assert task.text_content is None
        assert task.description is None
        assert isinstance(task.status, ClickUpStatus)
        assert task.orderindex == "0"
        assert isinstance(task.date_created, datetime)
        assert isinstance(task.date_updated, datetime)
        assert task.date_closed is None
        assert isinstance(task.creator, ClickUpUser)
        assert isinstance(task.assignees, list)
        assert isinstance(task.watchers, list)
        assert isinstance(task.checklists, list)
        assert isinstance(task.tags, list)
        assert task.parent is None
        assert task.priority is None
        assert task.due_date is None
        assert task.start_date is None
        assert task.points is None
        assert task.time_estimate is None
        assert task.time_spent is None
        assert isinstance(task.custom_fields, list)
        assert task.custom_id is None
        assert task.url == ""
        assert task.permission_level == ""
        assert task.list is None
        assert task.project is None
        assert task.folder is None
        assert task.space is None
