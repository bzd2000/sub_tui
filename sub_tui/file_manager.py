"""File manager for exporting data to markdown/YAML files.

NOTE: This module is deprecated for primary storage.
Database (database.py) is now the source of truth.
FileManager is kept for future export/backup functionality.
"""

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .models import (
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


class FileManager:
    """
    Manages file operations for exporting/importing data.

    DEPRECATED: Database is now the primary storage.
    This class is kept for future export/backup features (JSON dump, markdown export).
    """

    def __init__(self, data_dir: str = "data"):
        """Initialize file manager with data directory."""
        self.data_dir = Path(data_dir)
        self.subjects_dir = self.data_dir / "subjects"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.data_dir.mkdir(exist_ok=True)
        self.subjects_dir.mkdir(exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        """Convert name to safe directory name (lowercase, spaces→underscores)."""
        # Remove special characters, convert to lowercase, replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', name.lower())
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized.strip('_')

    def _get_subject_dir(self, subject_name: str) -> Path:
        """Get directory path for a subject."""
        return self.subjects_dir / self._sanitize_name(subject_name)

    def _atomic_write(self, path: Path, content: str) -> None:
        """Atomically write content to file."""
        # Write to temporary file first
        dir_path = path.parent
        dir_path.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=dir_path,
            delete=False,
            prefix='.tmp_',
            suffix=path.suffix
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Atomic rename
        os.replace(tmp_path, path)

    # Subject operations

    def save_subject(self, subject: Subject) -> None:
        """Save subject metadata to YAML file."""
        subject_dir = self._get_subject_dir(subject.name)
        subject_file = subject_dir / "subject.yaml"

        content = yaml.dump(subject.to_dict(), default_flow_style=False, sort_keys=False)
        self._atomic_write(subject_file, content)

    def load_subject(self, subject_name: str) -> Optional[Subject]:
        """Load subject from YAML file."""
        subject_file = self._get_subject_dir(subject_name) / "subject.yaml"

        if not subject_file.exists():
            return None

        with open(subject_file, 'r') as f:
            data = yaml.safe_load(f)

        return Subject.from_dict(data)

    def list_subjects(self) -> list[Subject]:
        """List all subjects."""
        subjects = []

        for subject_dir in self.subjects_dir.iterdir():
            if subject_dir.is_dir():
                subject_file = subject_dir / "subject.yaml"
                if subject_file.exists():
                    with open(subject_file, 'r') as f:
                        data = yaml.safe_load(f)
                    subjects.append(Subject.from_dict(data))

        return subjects

    def delete_subject(self, subject_name: str) -> None:
        """Delete a subject and all its data."""
        import shutil
        subject_dir = self._get_subject_dir(subject_name)
        if subject_dir.exists():
            shutil.rmtree(subject_dir)

    # Agenda operations

    def save_agenda_items(self, subject_name: str, items: list[AgendaItem]) -> None:
        """Save agenda items to YAML file."""
        subject_dir = self._get_subject_dir(subject_name)
        agenda_file = subject_dir / "agenda.yaml"

        data = [item.to_dict() for item in items]
        content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        self._atomic_write(agenda_file, content)

    def load_agenda_items(self, subject_name: str) -> list[AgendaItem]:
        """Load agenda items from YAML file."""
        agenda_file = self._get_subject_dir(subject_name) / "agenda.yaml"

        if not agenda_file.exists():
            return []

        with open(agenda_file, 'r') as f:
            data = yaml.safe_load(f) or []

        return [AgendaItem.from_dict(item) for item in data]

    # Meeting operations

    def save_meeting(self, subject_name: str, meeting: Meeting) -> None:
        """Save meeting to markdown file."""
        subject_dir = self._get_subject_dir(subject_name)
        meetings_dir = subject_dir / "meetings"

        # Use date as filename: YYYY-MM-DD.md (or add time if multiple per day)
        date_str = meeting.date.strftime("%Y-%m-%d")
        meeting_file = meetings_dir / f"{date_str}.md"

        # If file exists, add time to make unique
        if meeting_file.exists():
            date_str = meeting.date.strftime("%Y-%m-%d_%H%M%S")
            meeting_file = meetings_dir / f"{date_str}.md"

        # Create header with metadata
        header = f"""---
id: {meeting.id}
date: {meeting.date.isoformat()}
attendees: {', '.join(meeting.attendees)}
---

"""
        content = header + meeting.content
        self._atomic_write(meeting_file, content)

    def load_meeting(self, subject_name: str, meeting_file: str) -> Optional[Meeting]:
        """Load meeting from markdown file."""
        meetings_dir = self._get_subject_dir(subject_name) / "meetings"
        file_path = meetings_dir / meeting_file

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            content = f.read()

        # Parse YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                markdown_content = parts[2].strip()

                return Meeting(
                    id=frontmatter['id'],
                    subject_id=frontmatter.get('subject_id', ''),
                    date=datetime.fromisoformat(frontmatter['date']),
                    attendees=frontmatter.get('attendees', '').split(', '),
                    content=markdown_content,
                    created_at=datetime.fromisoformat(frontmatter.get('created_at', frontmatter['date'])),
                    updated_at=datetime.fromisoformat(frontmatter.get('updated_at', frontmatter['date'])),
                )

        return None

    def list_meetings(self, subject_name: str) -> list[Meeting]:
        """List all meetings for a subject."""
        meetings_dir = self._get_subject_dir(subject_name) / "meetings"

        if not meetings_dir.exists():
            return []

        meetings = []
        for meeting_file in sorted(meetings_dir.glob("*.md"), reverse=True):
            meeting = self.load_meeting(subject_name, meeting_file.name)
            if meeting:
                meetings.append(meeting)

        return meetings

    # Action operations

    def save_action(self, subject_name: str, action: Action) -> None:
        """Save action to YAML file."""
        subject_dir = self._get_subject_dir(subject_name)
        actions_dir = subject_dir / "actions"
        action_file = actions_dir / f"{action.id}.yaml"

        content = yaml.dump(action.to_dict(), default_flow_style=False, sort_keys=False)
        self._atomic_write(action_file, content)

    def load_action(self, subject_name: str, action_id: str) -> Optional[Action]:
        """Load action from YAML file."""
        action_file = self._get_subject_dir(subject_name) / "actions" / f"{action_id}.yaml"

        if not action_file.exists():
            return None

        with open(action_file, 'r') as f:
            data = yaml.safe_load(f)

        return Action.from_dict(data)

    def list_actions(self, subject_name: str) -> list[Action]:
        """List all actions for a subject."""
        actions_dir = self._get_subject_dir(subject_name) / "actions"

        if not actions_dir.exists():
            return []

        actions = []
        for action_file in actions_dir.glob("*.yaml"):
            with open(action_file, 'r') as f:
                data = yaml.safe_load(f)
            actions.append(Action.from_dict(data))

        return actions

    def delete_action(self, subject_name: str, action_id: str) -> None:
        """Delete an action file."""
        action_file = self._get_subject_dir(subject_name) / "actions" / f"{action_id}.yaml"
        if action_file.exists():
            action_file.unlink()

    # Note operations

    def save_note(self, subject_name: str, note: Note) -> None:
        """Save note to markdown file."""
        subject_dir = self._get_subject_dir(subject_name)
        notes_dir = subject_dir / "notes"
        note_file = notes_dir / f"{note.id}.md"

        # Create header with metadata
        header = f"""---
id: {note.id}
title: {note.title}
tags: {', '.join(note.tags)}
created_at: {note.created_at.isoformat()}
updated_at: {note.updated_at.isoformat()}
---

"""
        content = header + note.content
        self._atomic_write(note_file, content)

    def load_note(self, subject_name: str, note_id: str) -> Optional[Note]:
        """Load note from markdown file."""
        note_file = self._get_subject_dir(subject_name) / "notes" / f"{note_id}.md"

        if not note_file.exists():
            return None

        with open(note_file, 'r') as f:
            content = f.read()

        # Parse YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                markdown_content = parts[2].strip()

                return Note(
                    id=frontmatter['id'],
                    subject_id=frontmatter.get('subject_id', ''),
                    title=frontmatter['title'],
                    content=markdown_content,
                    tags=frontmatter.get('tags', '').split(', ') if frontmatter.get('tags') else [],
                    created_at=datetime.fromisoformat(frontmatter['created_at']),
                    updated_at=datetime.fromisoformat(frontmatter['updated_at']),
                )

        return None

    def list_notes(self, subject_name: str) -> list[Note]:
        """List all notes for a subject."""
        notes_dir = self._get_subject_dir(subject_name) / "notes"

        if not notes_dir.exists():
            return []

        notes = []
        for note_file in notes_dir.glob("*.md"):
            note = self.load_note(subject_name, note_file.stem)
            if note:
                notes.append(note)

        return notes
