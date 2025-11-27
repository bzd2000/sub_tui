"""SQLite database for storing and querying all application data."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Action, AgendaItem, Meeting, Note, Subject


class Database:
    """SQLite database for indexing and querying subjects data."""

    def __init__(self, db_path: str = "data/index.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Create tables
        self.conn.executescript("""
            -- Subjects table
            CREATE TABLE IF NOT EXISTS subjects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT,
                type TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                last_reviewed_at TEXT NOT NULL
            );

            -- Agenda items table
            CREATE TABLE IF NOT EXISTS agenda_items (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                discussed_at TEXT,
                is_recurring INTEGER NOT NULL,
                recurrence_pattern TEXT,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );

            -- Meetings table
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                attendees TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );

            -- Actions table
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                due_date TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                archived_at TEXT,
                meeting_id TEXT,
                agenda_item_id TEXT,
                tags TEXT,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );

            -- Notes table
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );

            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_subjects_name ON subjects(name);
            CREATE INDEX IF NOT EXISTS idx_subjects_type ON subjects(type);
            CREATE INDEX IF NOT EXISTS idx_agenda_subject ON agenda_items(subject_id);
            CREATE INDEX IF NOT EXISTS idx_agenda_status ON agenda_items(status);
            CREATE INDEX IF NOT EXISTS idx_meetings_subject ON meetings(subject_id);
            CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date);
            CREATE INDEX IF NOT EXISTS idx_actions_subject ON actions(subject_id);
            CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
            CREATE INDEX IF NOT EXISTS idx_actions_due_date ON actions(due_date);
            CREATE INDEX IF NOT EXISTS idx_notes_subject ON notes(subject_id);

            -- Unified full-text search across all content types
            CREATE VIRTUAL TABLE IF NOT EXISTS unified_fts USING fts5(
                content_type,     -- 'subject', 'agenda', 'meeting', 'action', 'note'
                content_id,       -- ID of the entity
                subject_id,       -- Subject ID (NULL for subjects themselves)
                subject_name,     -- Subject name for display
                title,            -- Title/name for display in results
                searchable_text,  -- Combined searchable content
                tokenize='porter unicode61'
            );

            -- FTS triggers for subjects
            CREATE TRIGGER IF NOT EXISTS subjects_fts_insert AFTER INSERT ON subjects BEGIN
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                VALUES ('subject', new.id, NULL, new.name, new.name,
                        new.name || ' ' || COALESCE(new.code, '') || ' ' || COALESCE(new.description, ''));
            END;

            CREATE TRIGGER IF NOT EXISTS subjects_fts_delete AFTER DELETE ON subjects BEGIN
                DELETE FROM unified_fts WHERE content_type = 'subject' AND content_id = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS subjects_fts_update AFTER UPDATE ON subjects BEGIN
                DELETE FROM unified_fts WHERE content_type = 'subject' AND content_id = old.id;
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                VALUES ('subject', new.id, NULL, new.name, new.name,
                        new.name || ' ' || COALESCE(new.code, '') || ' ' || COALESCE(new.description, ''));
            END;

            -- FTS triggers for agenda items
            CREATE TRIGGER IF NOT EXISTS agenda_fts_insert AFTER INSERT ON agenda_items BEGIN
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'agenda', new.id, new.subject_id, s.name, new.title,
                       new.title || ' ' || COALESCE(new.description, '')
                FROM subjects s WHERE s.id = new.subject_id;
            END;

            CREATE TRIGGER IF NOT EXISTS agenda_fts_delete AFTER DELETE ON agenda_items BEGIN
                DELETE FROM unified_fts WHERE content_type = 'agenda' AND content_id = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS agenda_fts_update AFTER UPDATE ON agenda_items BEGIN
                DELETE FROM unified_fts WHERE content_type = 'agenda' AND content_id = old.id;
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'agenda', new.id, new.subject_id, s.name, new.title,
                       new.title || ' ' || COALESCE(new.description, '')
                FROM subjects s WHERE s.id = new.subject_id;
            END;

            -- FTS triggers for meetings
            CREATE TRIGGER IF NOT EXISTS meetings_fts_insert AFTER INSERT ON meetings BEGIN
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'meeting', new.id, new.subject_id, s.name, 'Meeting ' || date(new.date),
                       'Meeting ' || new.attendees || ' ' || new.content
                FROM subjects s WHERE s.id = new.subject_id;
            END;

            CREATE TRIGGER IF NOT EXISTS meetings_fts_delete AFTER DELETE ON meetings BEGIN
                DELETE FROM unified_fts WHERE content_type = 'meeting' AND content_id = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS meetings_fts_update AFTER UPDATE ON meetings BEGIN
                DELETE FROM unified_fts WHERE content_type = 'meeting' AND content_id = old.id;
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'meeting', new.id, new.subject_id, s.name, 'Meeting ' || date(new.date),
                       'Meeting ' || new.attendees || ' ' || new.content
                FROM subjects s WHERE s.id = new.subject_id;
            END;

            -- FTS triggers for actions
            CREATE TRIGGER IF NOT EXISTS actions_fts_insert AFTER INSERT ON actions BEGIN
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'action', new.id, new.subject_id, s.name, new.title,
                       new.title || ' ' || COALESCE(new.description, '') || ' ' || COALESCE(new.tags, '')
                FROM subjects s WHERE s.id = new.subject_id;
            END;

            CREATE TRIGGER IF NOT EXISTS actions_fts_delete AFTER DELETE ON actions BEGIN
                DELETE FROM unified_fts WHERE content_type = 'action' AND content_id = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS actions_fts_update AFTER UPDATE ON actions BEGIN
                DELETE FROM unified_fts WHERE content_type = 'action' AND content_id = old.id;
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'action', new.id, new.subject_id, s.name, new.title,
                       new.title || ' ' || COALESCE(new.description, '') || ' ' || COALESCE(new.tags, '')
                FROM subjects s WHERE s.id = new.subject_id;
            END;

            -- FTS triggers for notes
            CREATE TRIGGER IF NOT EXISTS notes_fts_insert AFTER INSERT ON notes BEGIN
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'note', new.id, new.subject_id, s.name, new.title,
                       new.title || ' ' || new.content || ' ' || COALESCE(new.tags, '')
                FROM subjects s WHERE s.id = new.subject_id;
            END;

            CREATE TRIGGER IF NOT EXISTS notes_fts_delete AFTER DELETE ON notes BEGIN
                DELETE FROM unified_fts WHERE content_type = 'note' AND content_id = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS notes_fts_update AFTER UPDATE ON notes BEGIN
                DELETE FROM unified_fts WHERE content_type = 'note' AND content_id = old.id;
                INSERT INTO unified_fts(content_type, content_id, subject_id, subject_name, title, searchable_text)
                SELECT 'note', new.id, new.subject_id, s.name, new.title,
                       new.title || ' ' || new.content || ' ' || COALESCE(new.tags, '')
                FROM subjects s WHERE s.id = new.subject_id;
            END;
        """)

        self.conn.commit()

        # Database migrations
        self._run_migrations()

    def _run_migrations(self) -> None:
        """Run database migrations for schema updates."""
        # Migration 1: Add title column to meetings table
        cursor = self.conn.execute("PRAGMA table_info(meetings)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'title' not in columns:
            self.conn.execute("ALTER TABLE meetings ADD COLUMN title TEXT DEFAULT 'Meeting'")
            self.conn.commit()

        # Migration 2: Add note_id column to actions table
        cursor = self.conn.execute("PRAGMA table_info(actions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'note_id' not in columns:
            self.conn.execute("ALTER TABLE actions ADD COLUMN note_id TEXT")
            self.conn.commit()

    # ==================== Subject CRUD ====================

    def add_subject(self, subject: Subject) -> None:
        """Add a new subject."""
        self.conn.execute(
            """INSERT INTO subjects (id, name, code, type, description, created_at, last_reviewed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                subject.id,
                subject.name,
                subject.code,
                subject.type.value,
                subject.description,
                subject.created_at.isoformat(),
                subject.last_reviewed_at.isoformat(),
            )
        )
        self.conn.commit()

    def get_subject(self, subject_id: str) -> Optional[Subject]:
        """Get a subject by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM subjects WHERE id = ?",
            (subject_id,)
        )
        row = cursor.fetchone()
        if row:
            return Subject.from_dict(dict(row))
        return None

    def get_all_subjects(self) -> list[Subject]:
        """Get all subjects."""
        cursor = self.conn.execute("SELECT * FROM subjects ORDER BY last_reviewed_at DESC")
        return [Subject.from_dict(dict(row)) for row in cursor.fetchall()]

    def update_subject(self, subject: Subject) -> None:
        """Update an existing subject."""
        self.conn.execute(
            """UPDATE subjects
               SET name = ?, code = ?, type = ?, description = ?,
                   created_at = ?, last_reviewed_at = ?
               WHERE id = ?""",
            (
                subject.name,
                subject.code,
                subject.type.value,
                subject.description,
                subject.created_at.isoformat(),
                subject.last_reviewed_at.isoformat(),
                subject.id,
            )
        )
        self.conn.commit()

    def delete_subject(self, subject_id: str) -> None:
        """Delete a subject and all related data."""
        # Delete related data first (cascade)
        self.conn.execute("DELETE FROM agenda_items WHERE subject_id = ?", (subject_id,))
        self.conn.execute("DELETE FROM meetings WHERE subject_id = ?", (subject_id,))
        self.conn.execute("DELETE FROM actions WHERE subject_id = ?", (subject_id,))
        self.conn.execute("DELETE FROM notes WHERE subject_id = ?", (subject_id,))
        # Delete the subject itself
        self.conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        self.conn.commit()

    # ==================== Agenda Item CRUD ====================

    def add_agenda_item(self, item: AgendaItem) -> None:
        """Add a new agenda item."""
        self.conn.execute(
            """INSERT INTO agenda_items
               (id, subject_id, title, description, priority, status, created_at,
                discussed_at, is_recurring, recurrence_pattern)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.id,
                item.subject_id,
                item.title,
                item.description,
                item.priority,
                item.status.value,
                item.created_at.isoformat(),
                item.discussed_at.isoformat() if item.discussed_at else None,
                1 if item.is_recurring else 0,
                item.recurrence_pattern.value if item.recurrence_pattern else None,
            )
        )
        self.conn.commit()

    def get_agenda_items(self, subject_id: str) -> list[AgendaItem]:
        """Get all agenda items for a subject."""
        cursor = self.conn.execute(
            "SELECT * FROM agenda_items WHERE subject_id = ? ORDER BY priority DESC",
            (subject_id,)
        )
        return [AgendaItem.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_agenda_item(self, item_id: str) -> Optional[AgendaItem]:
        """Get a single agenda item by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM agenda_items WHERE id = ?",
            (item_id,)
        )
        row = cursor.fetchone()
        return AgendaItem.from_dict(dict(row)) if row else None

    def update_agenda_item(self, item: AgendaItem) -> None:
        """Update an existing agenda item."""
        self.conn.execute(
            """UPDATE agenda_items
               SET title = ?, description = ?, priority = ?, status = ?,
                   discussed_at = ?, is_recurring = ?, recurrence_pattern = ?
               WHERE id = ?""",
            (
                item.title,
                item.description,
                item.priority,
                item.status.value,
                item.discussed_at.isoformat() if item.discussed_at else None,
                1 if item.is_recurring else 0,
                item.recurrence_pattern.value if item.recurrence_pattern else None,
                item.id,
            )
        )
        self.conn.commit()

    def delete_agenda_item(self, item_id: str) -> None:
        """Delete an agenda item."""
        self.conn.execute("DELETE FROM agenda_items WHERE id = ?", (item_id,))
        self.conn.commit()

    # ==================== Meeting CRUD ====================

    def add_meeting(self, meeting: Meeting) -> None:
        """Add a new meeting."""
        self.conn.execute(
            """INSERT INTO meetings
               (id, subject_id, title, date, attendees, content, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                meeting.id,
                meeting.subject_id,
                meeting.title,
                meeting.date.isoformat(),
                json.dumps(meeting.attendees),
                meeting.content,
                meeting.created_at.isoformat(),
                meeting.updated_at.isoformat(),
            )
        )
        self.conn.commit()

    def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Get a meeting by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM meetings WHERE id = ?",
            (meeting_id,)
        )
        row = cursor.fetchone()
        if row:
            return Meeting.from_dict(dict(row))
        return None

    def get_meetings(self, subject_id: str) -> list[Meeting]:
        """Get all meetings for a subject."""
        cursor = self.conn.execute(
            "SELECT * FROM meetings WHERE subject_id = ? ORDER BY date DESC",
            (subject_id,)
        )
        return [Meeting.from_dict(dict(row)) for row in cursor.fetchall()]

    def update_meeting(self, meeting: Meeting) -> None:
        """Update an existing meeting."""
        self.conn.execute(
            """UPDATE meetings
               SET title = ?, date = ?, attendees = ?, content = ?, updated_at = ?
               WHERE id = ?""",
            (
                meeting.title,
                meeting.date.isoformat(),
                json.dumps(meeting.attendees),
                meeting.content,
                meeting.updated_at.isoformat(),
                meeting.id,
            )
        )
        self.conn.commit()

    def delete_meeting(self, meeting_id: str) -> None:
        """Delete a meeting."""
        self.conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        self.conn.commit()

    # ==================== Action CRUD ====================

    def add_action(self, action: Action) -> None:
        """Add a new action."""
        self.conn.execute(
            """INSERT INTO actions
               (id, subject_id, title, description, status, due_date, created_at,
                completed_at, archived_at, meeting_id, note_id, agenda_item_id, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                action.id,
                action.subject_id,
                action.title,
                action.description,
                action.status.value,
                action.due_date.isoformat() if action.due_date else None,
                action.created_at.isoformat(),
                action.completed_at.isoformat() if action.completed_at else None,
                action.archived_at.isoformat() if action.archived_at else None,
                action.meeting_id,
                action.note_id,
                action.agenda_item_id,
                ', '.join(action.tags) if action.tags else None,
            )
        )
        self.conn.commit()

    def get_action(self, action_id: str) -> Optional[Action]:
        """Get an action by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,)
        )
        row = cursor.fetchone()
        if row:
            return Action.from_dict(dict(row))
        return None

    def get_actions(self, subject_id: str) -> list[Action]:
        """Get all actions for a subject."""
        cursor = self.conn.execute(
            "SELECT * FROM actions WHERE subject_id = ? ORDER BY due_date ASC",
            (subject_id,)
        )
        return [Action.from_dict(dict(row)) for row in cursor.fetchall()]

    def update_action(self, action: Action) -> None:
        """Update an existing action."""
        self.conn.execute(
            """UPDATE actions
               SET title = ?, description = ?, status = ?, due_date = ?,
                   completed_at = ?, archived_at = ?, meeting_id = ?, note_id = ?,
                   agenda_item_id = ?, tags = ?
               WHERE id = ?""",
            (
                action.title,
                action.description,
                action.status.value,
                action.due_date.isoformat() if action.due_date else None,
                action.completed_at.isoformat() if action.completed_at else None,
                action.archived_at.isoformat() if action.archived_at else None,
                action.meeting_id,
                action.note_id,
                action.agenda_item_id,
                ', '.join(action.tags) if action.tags else None,
                action.id,
            )
        )
        self.conn.commit()

    def delete_action(self, action_id: str) -> None:
        """Delete an action."""
        self.conn.execute("DELETE FROM actions WHERE id = ?", (action_id,))
        self.conn.commit()

    def get_actions_by_timeframe(self, timeframe: str, include_archived: bool = False) -> list[dict]:
        """Get actions by timeframe (today, week, next_week, all)."""
        now = datetime.now()

        conditions = []
        params = []

        if not include_archived:
            conditions.append("archived_at IS NULL")

        if timeframe == "today":
            conditions.append("date(due_date) = date(?)")
            params.append(now.isoformat())
        elif timeframe == "week":
            conditions.append("date(due_date) BETWEEN date(?) AND date(?, '+7 days')")
            params.extend([now.isoformat(), now.isoformat()])
        elif timeframe == "next_week":
            conditions.append("date(due_date) BETWEEN date(?, '+8 days') AND date(?, '+14 days')")
            params.extend([now.isoformat(), now.isoformat()])
        elif timeframe == "all":
            if not include_archived:
                conditions.append("status != 'done' OR completed_at >= date('now', '-7 days')")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor = self.conn.execute(
            f"""SELECT a.*, s.name as subject_name
                FROM actions a
                JOIN subjects s ON a.subject_id = s.id
                WHERE {where_clause}
                ORDER BY
                    CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                    due_date ASC""",
            params
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_actions_by_meeting(self, meeting_id: str) -> list[Action]:
        """Get all actions created from a meeting."""
        cursor = self.conn.execute(
            "SELECT * FROM actions WHERE meeting_id = ? AND archived_at IS NULL ORDER BY created_at DESC",
            (meeting_id,)
        )
        return [Action.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_actions_by_note(self, note_id: str) -> list[Action]:
        """Get all actions created from a note."""
        cursor = self.conn.execute(
            "SELECT * FROM actions WHERE note_id = ? AND archived_at IS NULL ORDER BY created_at DESC",
            (note_id,)
        )
        return [Action.from_dict(dict(row)) for row in cursor.fetchall()]

    # ==================== Note CRUD ====================

    def add_note(self, note: Note) -> None:
        """Add a new note."""
        self.conn.execute(
            """INSERT INTO notes
               (id, subject_id, title, content, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                note.id,
                note.subject_id,
                note.title,
                note.content,
                ', '.join(note.tags) if note.tags else None,
                note.created_at.isoformat(),
                note.updated_at.isoformat(),
            )
        )
        self.conn.commit()

    def get_note(self, note_id: str) -> Optional[Note]:
        """Get a note by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM notes WHERE id = ?",
            (note_id,)
        )
        row = cursor.fetchone()
        if row:
            return Note.from_dict(dict(row))
        return None

    def get_notes(self, subject_id: str) -> list[Note]:
        """Get all notes for a subject."""
        cursor = self.conn.execute(
            "SELECT * FROM notes WHERE subject_id = ? ORDER BY updated_at DESC",
            (subject_id,)
        )
        return [Note.from_dict(dict(row)) for row in cursor.fetchall()]

    def update_note(self, note: Note) -> None:
        """Update an existing note."""
        self.conn.execute(
            """UPDATE notes
               SET title = ?, content = ?, tags = ?, updated_at = ?
               WHERE id = ?""",
            (
                note.title,
                note.content,
                ', '.join(note.tags) if note.tags else None,
                note.updated_at.isoformat(),
                note.id,
            )
        )
        self.conn.commit()

    def delete_note(self, note_id: str) -> None:
        """Delete a note."""
        self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()

    # ==================== Unified Search ====================

    def search(self, query: str, content_types: Optional[list[str]] = None) -> list[dict]:
        """
        Search across all content types using unified FTS.

        Args:
            query: Search query string
            content_types: Optional list to filter by type(s): 'subject', 'agenda', 'meeting', 'action', 'note'

        Returns:
            List of dicts with: content_type, content_id, subject_id, subject_name, title, rank
            Returns empty list if query is invalid (e.g., unbalanced quotes)
        """
        if not query or not query.strip():
            return []

        conditions = ["unified_fts MATCH ?"]
        params = [query]

        if content_types:
            placeholders = ','.join('?' * len(content_types))
            conditions.append(f"content_type IN ({placeholders})")
            params.extend(content_types)

        where_clause = " AND ".join(conditions)

        try:
            cursor = self.conn.execute(
                f"""SELECT content_type, content_id, subject_id, subject_name, title,
                           rank
                    FROM unified_fts
                    WHERE {where_clause}
                    ORDER BY rank
                    LIMIT 50""",
                params
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Invalid FTS query (e.g., unbalanced quotes, invalid syntax)
            return []

    # ==================== Utility ====================

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
