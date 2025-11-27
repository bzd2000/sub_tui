"""Tests for SubTUI data models."""

from datetime import datetime

import pytest

from sub_tui.models import (
    Action,
    ActionStatus,
    AgendaItem,
    AgendaStatus,
    Meeting,
    Note,
    RecurrencePattern,
    Subject,
    SubjectType,
)


class TestSubject:
    """Tests for Subject model."""

    def test_to_dict(self, sample_subject):
        """Test Subject serialization."""
        data = sample_subject.to_dict()

        assert data["id"] == "test-sub"
        assert data["name"] == "Test Project"
        assert data["type"] == "project"
        assert data["code"] == "TST"
        assert data["description"] == "A test project"
        assert "created_at" in data
        assert "last_reviewed_at" in data

    def test_from_dict(self, sample_subject):
        """Test Subject deserialization."""
        data = sample_subject.to_dict()
        restored = Subject.from_dict(data)

        assert restored.id == sample_subject.id
        assert restored.name == sample_subject.name
        assert restored.type == sample_subject.type
        assert restored.code == sample_subject.code
        assert restored.description == sample_subject.description

    def test_from_dict_minimal(self):
        """Test Subject deserialization with minimal data."""
        data = {
            "id": "min-sub",
            "name": "Minimal Subject",
            "type": "board",
            "created_at": "2024-01-01T00:00:00",
            "last_reviewed_at": "2024-01-01T00:00:00",
        }
        subject = Subject.from_dict(data)

        assert subject.id == "min-sub"
        assert subject.name == "Minimal Subject"
        assert subject.type == SubjectType.BOARD
        assert subject.code is None
        assert subject.description is None

    def test_subject_types(self):
        """Test all SubjectType values."""
        assert SubjectType.BOARD.value == "board"
        assert SubjectType.PROJECT.value == "project"
        assert SubjectType.TEAM.value == "team"
        assert SubjectType.PERSON.value == "person"


class TestAction:
    """Tests for Action model."""

    def test_to_dict(self, sample_action):
        """Test Action serialization."""
        data = sample_action.to_dict()

        assert data["id"] == "test-act"
        assert data["title"] == "Test Action"
        assert data["status"] == "todo"
        assert data["tags"] == ["test", "sample"]

    def test_from_dict(self, sample_action):
        """Test Action deserialization."""
        data = sample_action.to_dict()
        restored = Action.from_dict(data)

        assert restored.id == sample_action.id
        assert restored.title == sample_action.title
        assert restored.status == sample_action.status
        assert restored.tags == sample_action.tags

    def test_from_dict_tags_as_string(self):
        """Test Action deserialization with tags as comma-separated string."""
        data = {
            "id": "act-str",
            "subject_id": "sub-1",
            "title": "Action with string tags",
            "status": "todo",
            "created_at": "2024-01-01T00:00:00",
            "tags": "tag1, tag2, tag3",
        }
        action = Action.from_dict(data)

        assert action.tags == ["tag1", "tag2", "tag3"]

    def test_from_dict_tags_empty(self):
        """Test Action deserialization with empty/None tags."""
        data = {
            "id": "act-empty",
            "subject_id": "sub-1",
            "title": "Action without tags",
            "status": "in_progress",
            "created_at": "2024-01-01T00:00:00",
            "tags": None,
        }
        action = Action.from_dict(data)

        assert action.tags == []

    def test_action_statuses(self):
        """Test all ActionStatus values."""
        assert ActionStatus.TODO.value == "todo"
        assert ActionStatus.IN_PROGRESS.value == "in_progress"
        assert ActionStatus.DONE.value == "done"


class TestMeeting:
    """Tests for Meeting model."""

    def test_to_dict(self, sample_meeting):
        """Test Meeting serialization."""
        data = sample_meeting.to_dict()

        assert data["id"] == "test-mtg"
        assert data["title"] == "Test Meeting"
        assert data["attendees"] == ["Alice", "Bob"]
        assert "# Meeting Notes" in data["content"]

    def test_from_dict(self, sample_meeting):
        """Test Meeting deserialization."""
        data = sample_meeting.to_dict()
        restored = Meeting.from_dict(data)

        assert restored.id == sample_meeting.id
        assert restored.title == sample_meeting.title
        assert restored.attendees == sample_meeting.attendees

    def test_from_dict_default_title(self):
        """Test Meeting deserialization with missing title defaults to 'Meeting'."""
        data = {
            "id": "mtg-no-title",
            "subject_id": "sub-1",
            "date": "2024-01-01T10:00:00",
            "attendees": ["Person1"],
            "content": "Notes",
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T10:00:00",
        }
        meeting = Meeting.from_dict(data)

        assert meeting.title == "Meeting"


class TestNote:
    """Tests for Note model."""

    def test_to_dict(self, sample_note):
        """Test Note serialization."""
        data = sample_note.to_dict()

        assert data["id"] == "test-note"
        assert data["title"] == "Test Note"
        assert data["tags"] == ["documentation", "reference"]

    def test_from_dict(self, sample_note):
        """Test Note deserialization."""
        data = sample_note.to_dict()
        restored = Note.from_dict(data)

        assert restored.id == sample_note.id
        assert restored.title == sample_note.title
        assert restored.tags == sample_note.tags

    def test_from_dict_tags_as_string(self):
        """Test Note deserialization with tags as comma-separated string."""
        data = {
            "id": "note-str",
            "subject_id": "sub-1",
            "title": "Note with string tags",
            "content": "Content",
            "tags": "doc, ref",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        note = Note.from_dict(data)

        assert note.tags == ["doc", "ref"]

    def test_from_dict_tags_empty(self):
        """Test Note deserialization with empty/None tags."""
        data = {
            "id": "note-empty",
            "subject_id": "sub-1",
            "title": "Note without tags",
            "content": "Content",
            "tags": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        note = Note.from_dict(data)

        assert note.tags == []


class TestAgendaItem:
    """Tests for AgendaItem model."""

    def test_to_dict(self, sample_agenda_item):
        """Test AgendaItem serialization."""
        data = sample_agenda_item.to_dict()

        assert data["id"] == "test-agn"
        assert data["title"] == "Test Agenda Item"
        assert data["priority"] == 5
        assert data["status"] == "active"

    def test_from_dict(self, sample_agenda_item):
        """Test AgendaItem deserialization."""
        data = sample_agenda_item.to_dict()
        restored = AgendaItem.from_dict(data)

        assert restored.id == sample_agenda_item.id
        assert restored.title == sample_agenda_item.title
        assert restored.priority == sample_agenda_item.priority

    def test_from_dict_with_recurrence(self):
        """Test AgendaItem deserialization with recurrence settings."""
        data = {
            "id": "agn-rec",
            "subject_id": "sub-1",
            "title": "Recurring Item",
            "priority": 3,
            "status": "active",
            "created_at": "2024-01-01T00:00:00",
            "is_recurring": True,
            "recurrence_pattern": "weekly",
        }
        item = AgendaItem.from_dict(data)

        assert item.is_recurring is True
        assert item.recurrence_pattern == RecurrencePattern.WEEKLY

    def test_agenda_statuses(self):
        """Test all AgendaStatus values."""
        assert AgendaStatus.ACTIVE.value == "active"
        assert AgendaStatus.DISCUSSED.value == "discussed"
        assert AgendaStatus.ARCHIVED.value == "archived"

    def test_recurrence_patterns(self):
        """Test all RecurrencePattern values."""
        assert RecurrencePattern.WEEKLY.value == "weekly"
        assert RecurrencePattern.MONTHLY.value == "monthly"
        assert RecurrencePattern.QUARTERLY.value == "quarterly"
