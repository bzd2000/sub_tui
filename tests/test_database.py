"""Tests for SubTUI database operations."""

from datetime import datetime, timedelta

import pytest

from sub_tui.database import Database
from sub_tui.models import (
    Action,
    ActionStatus,
    AgendaItem,
    AgendaStatus,
    Meeting,
    Note,
    Subject,
    SubjectType,
)


class TestSubjectCRUD:
    """Tests for Subject CRUD operations."""

    def test_add_and_get_subject(self, db, sample_subject):
        """Test adding and retrieving a subject."""
        db.add_subject(sample_subject)

        retrieved = db.get_subject(sample_subject.id)

        assert retrieved is not None
        assert retrieved.id == sample_subject.id
        assert retrieved.name == sample_subject.name
        assert retrieved.type == sample_subject.type

    def test_get_nonexistent_subject(self, db):
        """Test getting a subject that doesn't exist."""
        result = db.get_subject("nonexistent-id")
        assert result is None

    def test_get_all_subjects(self, db, sample_subject):
        """Test getting all subjects."""
        db.add_subject(sample_subject)

        # Add another subject
        another = Subject(
            id="sub-2",
            name="Another Project",
            type=SubjectType.TEAM,
            created_at=datetime.now(),
            last_reviewed_at=datetime.now(),
        )
        db.add_subject(another)

        subjects = db.get_all_subjects()

        assert len(subjects) == 2

    def test_update_subject(self, db, sample_subject):
        """Test updating a subject."""
        db.add_subject(sample_subject)

        sample_subject.name = "Updated Name"
        sample_subject.description = "Updated description"
        db.update_subject(sample_subject)

        retrieved = db.get_subject(sample_subject.id)

        assert retrieved.name == "Updated Name"
        assert retrieved.description == "Updated description"

    def test_delete_subject(self, db, sample_subject):
        """Test deleting a subject."""
        db.add_subject(sample_subject)
        db.delete_subject(sample_subject.id)

        result = db.get_subject(sample_subject.id)
        assert result is None


class TestCascadeDelete:
    """Tests for cascade delete on subject deletion."""

    def test_delete_subject_cascades_to_actions(self, populated_db, sample_subject):
        """Test that deleting a subject also deletes its actions."""
        # Verify action exists
        actions = populated_db.get_actions(sample_subject.id)
        assert len(actions) > 0

        # Delete subject
        populated_db.delete_subject(sample_subject.id)

        # Verify action is also deleted
        actions = populated_db.get_actions(sample_subject.id)
        assert len(actions) == 0

    def test_delete_subject_cascades_to_meetings(self, populated_db, sample_subject):
        """Test that deleting a subject also deletes its meetings."""
        # Verify meeting exists
        meetings = populated_db.get_meetings(sample_subject.id)
        assert len(meetings) > 0

        # Delete subject
        populated_db.delete_subject(sample_subject.id)

        # Verify meeting is also deleted
        meetings = populated_db.get_meetings(sample_subject.id)
        assert len(meetings) == 0

    def test_delete_subject_cascades_to_notes(self, populated_db, sample_subject):
        """Test that deleting a subject also deletes its notes."""
        # Verify note exists
        notes = populated_db.get_notes(sample_subject.id)
        assert len(notes) > 0

        # Delete subject
        populated_db.delete_subject(sample_subject.id)

        # Verify note is also deleted
        notes = populated_db.get_notes(sample_subject.id)
        assert len(notes) == 0

    def test_delete_subject_cascades_to_agenda_items(self, populated_db, sample_subject):
        """Test that deleting a subject also deletes its agenda items."""
        # Verify agenda item exists
        items = populated_db.get_agenda_items(sample_subject.id)
        assert len(items) > 0

        # Delete subject
        populated_db.delete_subject(sample_subject.id)

        # Verify agenda item is also deleted
        items = populated_db.get_agenda_items(sample_subject.id)
        assert len(items) == 0


class TestActionCRUD:
    """Tests for Action CRUD operations."""

    def test_add_and_get_action(self, db, sample_subject, sample_action):
        """Test adding and retrieving an action."""
        db.add_subject(sample_subject)
        db.add_action(sample_action)

        retrieved = db.get_action(sample_action.id)

        assert retrieved is not None
        assert retrieved.id == sample_action.id
        assert retrieved.title == sample_action.title

    def test_get_actions_for_subject(self, db, sample_subject, sample_action):
        """Test getting all actions for a subject."""
        db.add_subject(sample_subject)
        db.add_action(sample_action)

        actions = db.get_actions(sample_subject.id)

        assert len(actions) == 1
        assert actions[0].id == sample_action.id

    def test_update_action(self, db, sample_subject, sample_action):
        """Test updating an action."""
        db.add_subject(sample_subject)
        db.add_action(sample_action)

        sample_action.title = "Updated Title"
        sample_action.status = ActionStatus.DONE
        db.update_action(sample_action)

        retrieved = db.get_action(sample_action.id)

        assert retrieved.title == "Updated Title"
        assert retrieved.status == ActionStatus.DONE

    def test_delete_action(self, db, sample_subject, sample_action):
        """Test deleting an action."""
        db.add_subject(sample_subject)
        db.add_action(sample_action)
        db.delete_action(sample_action.id)

        result = db.get_action(sample_action.id)
        assert result is None


class TestMeetingCRUD:
    """Tests for Meeting CRUD operations."""

    def test_add_and_get_meeting(self, db, sample_subject, sample_meeting):
        """Test adding and retrieving a meeting."""
        db.add_subject(sample_subject)
        db.add_meeting(sample_meeting)

        retrieved = db.get_meeting(sample_meeting.id)

        assert retrieved is not None
        assert retrieved.id == sample_meeting.id
        assert retrieved.title == sample_meeting.title

    def test_get_meetings_for_subject(self, db, sample_subject, sample_meeting):
        """Test getting all meetings for a subject."""
        db.add_subject(sample_subject)
        db.add_meeting(sample_meeting)

        meetings = db.get_meetings(sample_subject.id)

        assert len(meetings) == 1
        assert meetings[0].id == sample_meeting.id

    def test_update_meeting(self, db, sample_subject, sample_meeting):
        """Test updating a meeting."""
        db.add_subject(sample_subject)
        db.add_meeting(sample_meeting)

        sample_meeting.title = "Updated Meeting Title"
        sample_meeting.content = "Updated content"
        db.update_meeting(sample_meeting)

        retrieved = db.get_meeting(sample_meeting.id)

        assert retrieved.title == "Updated Meeting Title"
        assert retrieved.content == "Updated content"

    def test_delete_meeting(self, db, sample_subject, sample_meeting):
        """Test deleting a meeting."""
        db.add_subject(sample_subject)
        db.add_meeting(sample_meeting)
        db.delete_meeting(sample_meeting.id)

        result = db.get_meeting(sample_meeting.id)
        assert result is None


class TestNoteCRUD:
    """Tests for Note CRUD operations."""

    def test_add_and_get_note(self, db, sample_subject, sample_note):
        """Test adding and retrieving a note."""
        db.add_subject(sample_subject)
        db.add_note(sample_note)

        retrieved = db.get_note(sample_note.id)

        assert retrieved is not None
        assert retrieved.id == sample_note.id
        assert retrieved.title == sample_note.title

    def test_get_notes_for_subject(self, db, sample_subject, sample_note):
        """Test getting all notes for a subject."""
        db.add_subject(sample_subject)
        db.add_note(sample_note)

        notes = db.get_notes(sample_subject.id)

        assert len(notes) == 1
        assert notes[0].id == sample_note.id

    def test_update_note(self, db, sample_subject, sample_note):
        """Test updating a note."""
        db.add_subject(sample_subject)
        db.add_note(sample_note)

        sample_note.title = "Updated Note Title"
        db.update_note(sample_note)

        retrieved = db.get_note(sample_note.id)

        assert retrieved.title == "Updated Note Title"

    def test_delete_note(self, db, sample_subject, sample_note):
        """Test deleting a note."""
        db.add_subject(sample_subject)
        db.add_note(sample_note)
        db.delete_note(sample_note.id)

        result = db.get_note(sample_note.id)
        assert result is None


class TestAgendaItemCRUD:
    """Tests for AgendaItem CRUD operations."""

    def test_add_and_get_agenda_item(self, db, sample_subject, sample_agenda_item):
        """Test adding and retrieving an agenda item."""
        db.add_subject(sample_subject)
        db.add_agenda_item(sample_agenda_item)

        retrieved = db.get_agenda_item(sample_agenda_item.id)

        assert retrieved is not None
        assert retrieved.id == sample_agenda_item.id
        assert retrieved.title == sample_agenda_item.title

    def test_get_agenda_items_for_subject(self, db, sample_subject, sample_agenda_item):
        """Test getting all agenda items for a subject."""
        db.add_subject(sample_subject)
        db.add_agenda_item(sample_agenda_item)

        items = db.get_agenda_items(sample_subject.id)

        assert len(items) == 1
        assert items[0].id == sample_agenda_item.id

    def test_update_agenda_item(self, db, sample_subject, sample_agenda_item):
        """Test updating an agenda item."""
        db.add_subject(sample_subject)
        db.add_agenda_item(sample_agenda_item)

        sample_agenda_item.title = "Updated Agenda Title"
        sample_agenda_item.priority = 10
        db.update_agenda_item(sample_agenda_item)

        retrieved = db.get_agenda_item(sample_agenda_item.id)

        assert retrieved.title == "Updated Agenda Title"
        assert retrieved.priority == 10

    def test_delete_agenda_item(self, db, sample_subject, sample_agenda_item):
        """Test deleting an agenda item."""
        db.add_subject(sample_subject)
        db.add_agenda_item(sample_agenda_item)
        db.delete_agenda_item(sample_agenda_item.id)

        result = db.get_agenda_item(sample_agenda_item.id)
        assert result is None


class TestActionsByTimeframe:
    """Tests for get_actions_by_timeframe."""

    def test_actions_today(self, db, sample_subject):
        """Test filtering actions due today."""
        db.add_subject(sample_subject)

        today = datetime.now()
        action_today = Action(
            id="act-today",
            subject_id=sample_subject.id,
            title="Due Today",
            status=ActionStatus.TODO,
            created_at=today,
            due_date=today,
            tags=[],
        )
        db.add_action(action_today)

        results = db.get_actions_by_timeframe("today")

        assert len(results) == 1
        assert results[0]["id"] == "act-today"

    def test_actions_all_excludes_old_done(self, db, sample_subject):
        """Test that 'all' filter excludes old completed actions."""
        db.add_subject(sample_subject)

        old_date = datetime.now() - timedelta(days=30)
        old_done = Action(
            id="act-old-done",
            subject_id=sample_subject.id,
            title="Old Done Action",
            status=ActionStatus.DONE,
            created_at=old_date,
            completed_at=old_date,
            tags=[],
        )
        db.add_action(old_done)

        results = db.get_actions_by_timeframe("all")

        # Should not include old completed action
        assert all(r["id"] != "act-old-done" for r in results)


class TestSearch:
    """Tests for unified full-text search."""

    def test_search_subjects(self, populated_db):
        """Test searching for subjects."""
        results = populated_db.search("Test Project", content_types=["subject"])

        assert len(results) > 0
        assert any(r["content_type"] == "subject" for r in results)

    def test_search_actions(self, populated_db):
        """Test searching for actions."""
        results = populated_db.search("Test Action", content_types=["action"])

        assert len(results) > 0
        assert any(r["content_type"] == "action" for r in results)

    def test_search_notes(self, populated_db):
        """Test searching for notes."""
        results = populated_db.search("Knowledge Note", content_types=["note"])

        assert len(results) > 0
        assert any(r["content_type"] == "note" for r in results)

    def test_search_all_types(self, populated_db):
        """Test searching across all content types."""
        results = populated_db.search("Test")

        assert len(results) > 0
        # Should find multiple types
        types_found = set(r["content_type"] for r in results)
        assert len(types_found) >= 1


class TestActionsByContent:
    """Tests for getting actions linked to meetings/notes."""

    def test_get_actions_by_meeting(self, db, sample_subject, sample_meeting):
        """Test getting actions linked to a meeting."""
        db.add_subject(sample_subject)
        db.add_meeting(sample_meeting)

        action_linked = Action(
            id="act-linked",
            subject_id=sample_subject.id,
            title="Linked Action",
            status=ActionStatus.TODO,
            created_at=datetime.now(),
            meeting_id=sample_meeting.id,
            tags=[],
        )
        db.add_action(action_linked)

        results = db.get_actions_by_meeting(sample_meeting.id)

        assert len(results) == 1
        assert results[0].id == "act-linked"

    def test_get_actions_by_note(self, db, sample_subject, sample_note):
        """Test getting actions linked to a note."""
        db.add_subject(sample_subject)
        db.add_note(sample_note)

        action_linked = Action(
            id="act-from-note",
            subject_id=sample_subject.id,
            title="Action from Note",
            status=ActionStatus.TODO,
            created_at=datetime.now(),
            note_id=sample_note.id,
            tags=[],
        )
        db.add_action(action_linked)

        results = db.get_actions_by_note(sample_note.id)

        assert len(results) == 1
        assert results[0].id == "act-from-note"
