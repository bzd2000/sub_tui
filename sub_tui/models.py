"""Data models for SubTUI application."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SubjectType(str, Enum):
    """Types of subjects that can be managed."""
    BOARD = "board"
    PROJECT = "project"
    TEAM = "team"
    PERSON = "person"


class AgendaStatus(str, Enum):
    """Status of agenda items."""
    ACTIVE = "active"
    DISCUSSED = "discussed"
    ARCHIVED = "archived"


class RecurrencePattern(str, Enum):
    """Recurrence patterns for agenda items."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ActionStatus(str, Enum):
    """Status of actions."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Subject:
    """A subject represents a context for organizing information."""
    id: str
    name: str
    type: SubjectType
    created_at: datetime
    last_reviewed_at: datetime
    code: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "code": self.code,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_reviewed_at": self.last_reviewed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subject":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            type=SubjectType(data["type"]),
            code=data.get("code"),
            description=data.get("description"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_reviewed_at=datetime.fromisoformat(data["last_reviewed_at"]),
        )


@dataclass
class AgendaItem:
    """Things to discuss in the next encounter with a subject."""
    id: str
    subject_id: str
    title: str
    priority: int  # 1-10
    status: AgendaStatus
    created_at: datetime
    description: Optional[str] = None
    discussed_at: Optional[datetime] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "discussed_at": self.discussed_at.isoformat() if self.discussed_at else None,
            "is_recurring": self.is_recurring,
            "recurrence_pattern": self.recurrence_pattern.value if self.recurrence_pattern else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgendaItem":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            subject_id=data["subject_id"],
            title=data["title"],
            description=data.get("description"),
            priority=data["priority"],
            status=AgendaStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            discussed_at=datetime.fromisoformat(data["discussed_at"]) if data.get("discussed_at") else None,
            is_recurring=data.get("is_recurring", False),
            recurrence_pattern=RecurrencePattern(data["recurrence_pattern"]) if data.get("recurrence_pattern") else None,
        )


@dataclass
class Meeting:
    """Records of encounters with a subject."""
    id: str
    subject_id: str
    date: datetime
    attendees: list[str]
    content: str  # Markdown content
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "date": self.date.isoformat(),
            "attendees": self.attendees,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Meeting":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            subject_id=data["subject_id"],
            date=datetime.fromisoformat(data["date"]),
            attendees=data["attendees"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class Action:
    """Personal tasks related to subjects."""
    id: str
    subject_id: str
    title: str
    status: ActionStatus
    created_at: datetime
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    meeting_id: Optional[str] = None  # If created during meeting
    agenda_item_id: Optional[str] = None  # If originated from agenda item
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "meeting_id": self.meeting_id,
            "agenda_item_id": self.agenda_item_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            subject_id=data["subject_id"],
            title=data["title"],
            description=data.get("description"),
            status=ActionStatus(data["status"]),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            archived_at=datetime.fromisoformat(data["archived_at"]) if data.get("archived_at") else None,
            meeting_id=data.get("meeting_id"),
            agenda_item_id=data.get("agenda_item_id"),
            tags=data.get("tags", []),
        )


@dataclass
class Note:
    """Reference information and documentation."""
    id: str
    subject_id: str
    title: str
    content: str  # Markdown content
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            subject_id=data["subject_id"],
            title=data["title"],
            content=data["content"],
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
