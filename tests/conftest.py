"""Pytest fixtures for SubTUI tests."""

import pytest
from datetime import datetime

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


@pytest.fixture
def db():
    """Create in-memory database for testing."""
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def sample_subject():
    """Create a sample subject for testing."""
    return Subject(
        id="test-sub",
        name="Test Project",
        type=SubjectType.PROJECT,
        code="TST",
        description="A test project",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        last_reviewed_at=datetime(2024, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def sample_action(sample_subject):
    """Create a sample action for testing."""
    return Action(
        id="test-act",
        subject_id=sample_subject.id,
        title="Test Action",
        status=ActionStatus.TODO,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        description="A test action",
        due_date=datetime(2024, 1, 10, 12, 0, 0),
        tags=["test", "sample"],
    )


@pytest.fixture
def sample_meeting(sample_subject):
    """Create a sample meeting for testing."""
    return Meeting(
        id="test-mtg",
        subject_id=sample_subject.id,
        title="Test Meeting",
        date=datetime(2024, 1, 5, 10, 0, 0),
        attendees=["Alice", "Bob"],
        content="# Meeting Notes\n\nDiscussed the project.",
        created_at=datetime(2024, 1, 5, 10, 0, 0),
        updated_at=datetime(2024, 1, 5, 11, 0, 0),
    )


@pytest.fixture
def sample_note(sample_subject):
    """Create a sample note for testing."""
    return Note(
        id="test-note",
        subject_id=sample_subject.id,
        title="Test Note",
        content="# Knowledge Note\n\nSome important information.",
        tags=["documentation", "reference"],
        created_at=datetime(2024, 1, 3, 12, 0, 0),
        updated_at=datetime(2024, 1, 3, 14, 0, 0),
    )


@pytest.fixture
def sample_agenda_item(sample_subject):
    """Create a sample agenda item for testing."""
    return AgendaItem(
        id="test-agn",
        subject_id=sample_subject.id,
        title="Test Agenda Item",
        priority=5,
        status=AgendaStatus.ACTIVE,
        created_at=datetime(2024, 1, 2, 12, 0, 0),
        description="An item to discuss",
    )


@pytest.fixture
def populated_db(db, sample_subject, sample_action, sample_meeting, sample_note, sample_agenda_item):
    """Create a database populated with sample data."""
    db.add_subject(sample_subject)
    db.add_action(sample_action)
    db.add_meeting(sample_meeting)
    db.add_note(sample_note)
    db.add_agenda_item(sample_agenda_item)
    return db
