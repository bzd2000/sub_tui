"""Subject detail screen with rich card-based layout."""

from datetime import datetime
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static, Label

from ..database import Database
from ..widgets import ViewActionDialog, ViewAgendaDialog, ViewMeetingDialog, ViewNoteDialog


class SubjectDetailScreen(Screen):
    """Screen showing comprehensive subject details with multiple sections."""

    CSS = """
    #subject-header {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        border: solid $primary;
    }

    #subject-title {
        text-style: bold;
        color: $accent;
    }

    #sections-container {
        width: 100%;
        height: 1fr;
        padding: 0;
    }

    .section-card {
        width: 100%;
        height: 1fr;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }

    .section-header {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
        padding: 0;
    }

    .section-table {
        height: 1fr;
        margin: 0;
        padding: 0;
    }

    .empty-message {
        color: $text-muted;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("escape", "pop_screen", "Back", priority=True),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, db: Database, subject_id: str, selected_action_id: Optional[str] = None):
        """Initialize subject detail screen.

        Args:
            db: Database instance
            subject_id: ID of the subject to display
            selected_action_id: Optional action ID to highlight
        """
        super().__init__()
        self.db = db
        self.subject_id = subject_id
        self.selected_action_id = selected_action_id

        # Track IDs for each section
        self.action_ids: list[str] = []
        self.agenda_ids: list[str] = []
        self.meeting_ids: list[str] = []
        self.note_ids: list[str] = []

    def compose(self) -> ComposeResult:
        """Compose the UI with card-based sections in single column."""
        yield Header()

        # Subject header
        with Container(id="subject-header"):
            yield Static("", id="subject-title")
            yield Static("", id="subject-info")

        # Single column: Agenda, Actions, Meetings, Notes (equal height)
        with Vertical(id="sections-container"):
            # Agenda items section
            with Vertical(classes="section-card"):
                yield Label("Agenda Items", classes="section-header")
                table = DataTable(id="agenda-table", classes="section-table")
                table.add_columns("Title", "Priority", "Status")
                table.cursor_type = "row"
                yield table

            # Actions section
            with Vertical(classes="section-card"):
                yield Label("Actions", classes="section-header")
                table = DataTable(id="actions-table", classes="section-table")
                table.add_columns("Title", "Due", "Status")
                table.cursor_type = "row"
                yield table

            # Meetings section
            with Vertical(classes="section-card"):
                yield Label("Meeting Minutes", classes="section-header")
                table = DataTable(id="meetings-table", classes="section-table")
                table.add_columns("Date", "Attendees")
                table.cursor_type = "row"
                yield table

            # Notes section
            with Vertical(classes="section-card"):
                yield Label("Knowledge Notes", classes="section-header")
                table = DataTable(id="notes-table", classes="section-table")
                table.add_columns("Title", "Tags", "Updated")
                table.cursor_type = "row"
                yield table

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self.load_subject_data()

    def load_subject_data(self) -> None:
        """Load all subject data."""
        # Load subject info
        subject = self.db.get_subject(self.subject_id)
        if not subject:
            self.notify("Subject not found", severity="error")
            self.app.pop_screen()
            return

        # Update header
        title_widget = self.query_one("#subject-title", Static)
        title_widget.update(f"{subject.name}")

        info_parts = []
        if subject.code:
            info_parts.append(f"[dim]Code:[/dim] {subject.code}")
        if subject.description:
            info_parts.append(f"[dim]{subject.description}[/dim]")
        if info_parts:
            info_widget = self.query_one("#subject-info", Static)
            info_widget.update(" | ".join(info_parts))

        # Load all sections
        self.refresh_actions()
        self.refresh_agenda()
        self.refresh_meetings()
        self.refresh_notes()

    def refresh_actions(self) -> None:
        """Refresh the actions section."""
        table = self.query_one("#actions-table", DataTable)
        table.clear()
        self.action_ids = []

        actions = self.db.get_actions(self.subject_id)

        for action in actions:
            # Skip archived actions
            if action.archived_at:
                continue

            self.action_ids.append(action.id)

            # Format due date
            due_str = "-"
            if action.due_date:
                due_str = action.due_date.strftime("%Y-%m-%d")
                if action.due_date.date() < datetime.now().date() and action.status.value != "done":
                    due_str = f"[red]{due_str}[/red]"

            # Format status
            status_map = {
                "todo": "[dim]TODO[/dim]",
                "in_progress": "[yellow]IN PROGRESS[/yellow]",
                "done": "[green]✓ DONE[/green]"
            }
            status_str = status_map.get(action.status.value, action.status.value)

            table.add_row(action.title, due_str, status_str)

        if not self.action_ids:
            table.add_row("[dim italic]No actions[/dim italic]", "", "")

    def refresh_agenda(self) -> None:
        """Refresh the agenda items section."""
        table = self.query_one("#agenda-table", DataTable)
        table.clear()
        self.agenda_ids = []

        items = self.db.get_agenda_items(self.subject_id)

        for item in items:
            # Skip archived items
            if item.status.value == "archived":
                continue

            self.agenda_ids.append(item.id)

            priority_str = "★" * item.priority if item.priority <= 5 else f"★★★★★+{item.priority-5}"

            status_map = {
                "active": "[yellow]ACTIVE[/yellow]",
                "discussed": "[dim]DISCUSSED[/dim]",
            }
            status_str = status_map.get(item.status.value, item.status.value)

            table.add_row(item.title, priority_str, status_str)

        if not self.agenda_ids:
            table.add_row("[dim italic]No agenda items[/dim italic]", "", "")

    def refresh_meetings(self) -> None:
        """Refresh the meetings section."""
        table = self.query_one("#meetings-table", DataTable)
        table.clear()
        self.meeting_ids = []

        meetings = self.db.get_meetings(self.subject_id)

        for meeting in meetings:
            self.meeting_ids.append(meeting.id)

            date_str = meeting.date.strftime("%Y-%m-%d")
            attendees_str = ", ".join(meeting.attendees[:3])
            if len(meeting.attendees) > 3:
                attendees_str += f" +{len(meeting.attendees)-3} more"

            table.add_row(date_str, attendees_str)

        if not self.meeting_ids:
            table.add_row("[dim italic]No meetings[/dim italic]", "")

    def refresh_notes(self) -> None:
        """Refresh the notes section."""
        table = self.query_one("#notes-table", DataTable)
        table.clear()
        self.note_ids = []

        notes = self.db.get_notes(self.subject_id)

        for note in notes:
            self.note_ids.append(note.id)

            tags_str = ", ".join(note.tags[:3]) if note.tags else "-"
            if note.tags and len(note.tags) > 3:
                tags_str += f" +{len(note.tags)-3}"

            updated_str = note.updated_at.strftime("%Y-%m-%d")

            table.add_row(note.title, tags_str, updated_str)

        if not self.note_ids:
            table.add_row("[dim italic]No notes[/dim italic]", "", "")

    @work
    async def on_data_table_row_selected(self, event) -> None:
        """Handle Enter key on any table row."""
        table_id = event.data_table.id
        row_index = event.cursor_row

        if table_id == "actions-table" and row_index < len(self.action_ids):
            action_id = self.action_ids[row_index]
            action = self.db.get_action(action_id)
            if action:
                result = await self.app.push_screen_wait(ViewActionDialog(action))
                if result:
                    self.db.update_action(result)
                    self.refresh_actions()
                    self.notify(f"Action '{result.title}' updated")

        elif table_id == "agenda-table" and row_index < len(self.agenda_ids):
            agenda_id = self.agenda_ids[row_index]
            agenda_item = self.db.get_agenda_item(agenda_id)
            if agenda_item:
                result = await self.app.push_screen_wait(ViewAgendaDialog(agenda_item))
                if result:
                    self.db.update_agenda_item(result)
                    self.refresh_agenda()
                    self.notify(f"Agenda item '{result.title}' updated")

        elif table_id == "meetings-table" and row_index < len(self.meeting_ids):
            meeting_id = self.meeting_ids[row_index]
            meeting = self.db.get_meeting(meeting_id)
            if meeting:
                result = await self.app.push_screen_wait(ViewMeetingDialog(meeting))
                if result:
                    self.db.update_meeting(result)
                    self.refresh_meetings()
                    self.notify(f"Meeting updated")

        elif table_id == "notes-table" and row_index < len(self.note_ids):
            note_id = self.note_ids[row_index]
            note = self.db.get_note(note_id)
            if note:
                result = await self.app.push_screen_wait(ViewNoteDialog(note))
                if result:
                    self.db.update_note(result)
                    self.refresh_notes()
                    self.notify(f"Note '{result.title}' updated")

    def action_refresh(self) -> None:
        """Refresh all sections."""
        self.load_subject_data()
        self.notify("Refreshed")

    def action_pop_screen(self) -> None:
        """Go back to main dashboard."""
        self.app.pop_screen()
