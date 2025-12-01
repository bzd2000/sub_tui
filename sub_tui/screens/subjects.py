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
from ..models import Action, AgendaItem, Meeting, Note, Subject
from ..widgets import ConfirmDialog, EditSubjectDialog, NewActionDialog, NewAgendaDialog, NewMeetingDialog, NewNoteDialog, SubjectLookupDialog, ViewActionDialog, ViewAgendaDialog, ViewMeetingDialog, ViewNoteDialog, format_date_locale


class SubjectDetailScreen(Screen):
    """Screen showing comprehensive subject details with multiple sections."""

    CSS = """
    #subject-header {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        border: solid $primary;
        border-title-color: $text-muted;
        border-title-style: bold;
    }

    #subject-header:focus {
        border: solid $accent;
        border-title-color: $accent;
    }

    #sections-container {
        width: 100%;
        height: 1fr;
        padding: 0;
    }

    .section-card {
        width: 100%;
        height: 1fr;
        padding: 0 1 1 1;
        border: solid $primary;
        border-title-color: $text-muted;
        border-title-style: bold;
        background: $surface;
    }

    .section-card:focus-within {
        border: solid $accent;
        border-title-color: $accent;
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
        Binding("e", "edit_item", "Edit"),
        Binding("a", "add_item", "Add"),
        Binding("ctrl+d", "delete_item", "Delete"),
        Binding("/", "subject_lookup", "Find Subject"),
        Binding("ctrl+p", "subject_lookup", "Find Subject"),
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
        self.subject_name = ""  # Will be set when subject is loaded

        # Track IDs for each section
        self.action_ids: list[str] = []
        self.agenda_ids: list[str] = []
        self.meeting_ids: list[str] = []
        self.note_ids: list[str] = []

    def compose(self) -> ComposeResult:
        """Compose the UI with card-based sections in single column."""
        yield Header()

        # Subject header (focusable for editing)
        header = Container(id="subject-header")
        header.can_focus = True
        header.border_title = "Subject"
        with header:
            yield Static("", id="subject-title")
            yield Static("", id="subject-info")

        # Single column: Agenda, Actions, Meetings, Notes (equal height)
        with Vertical(id="sections-container"):
            # Agenda items section
            agenda_card = Vertical(classes="section-card")
            agenda_card.border_title = "Agenda Items"
            with agenda_card:
                table = DataTable(id="agenda-table", classes="section-table")
                table.add_columns("Title", "Priority", "Status")
                table.cursor_type = "row"
                yield table

            # Actions section
            actions_card = Vertical(classes="section-card")
            actions_card.border_title = "Actions"
            with actions_card:
                table = DataTable(id="actions-table", classes="section-table")
                table.add_columns("Title", "Due", "Status")
                table.cursor_type = "row"
                yield table

            # Meetings section
            meetings_card = Vertical(classes="section-card")
            meetings_card.border_title = "Meeting Minutes"
            with meetings_card:
                table = DataTable(id="meetings-table", classes="section-table")
                table.add_columns("Date", "Title", "Attendees")
                table.cursor_type = "row"
                yield table

            # Notes section
            notes_card = Vertical(classes="section-card")
            notes_card.border_title = "Knowledge Notes"
            with notes_card:
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

        # Store subject name for dialogs
        self.subject_name = subject.name

        # Update header border title with subject name
        header = self.query_one("#subject-header", Container)
        header.border_title = subject.name

        # Update header content
        title_widget = self.query_one("#subject-title", Static)
        title_widget.update(f"[dim]Type:[/dim] {subject.type.value.title()}")

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
                due_str = format_date_locale(action.due_date)
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

            date_str = format_date_locale(meeting.date)
            title = meeting.title or "Untitled"
            attendees_str = ", ".join(meeting.attendees[:3])
            if len(meeting.attendees) > 3:
                attendees_str += f" +{len(meeting.attendees)-3} more"

            table.add_row(date_str, title, attendees_str)

        if not self.meeting_ids:
            table.add_row("[dim italic]No meetings[/dim italic]", "", "")

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

            updated_str = format_date_locale(note.updated_at, with_day_prefix=False)

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
                result = await self.app.push_screen_wait(ViewActionDialog(action, self.subject_name))
                if result:
                    self.db.update_action(result)
                    self.refresh_actions()
                    self.notify(f"Action '{result.title}' updated")

        elif table_id == "agenda-table" and row_index < len(self.agenda_ids):
            agenda_id = self.agenda_ids[row_index]
            agenda_item = self.db.get_agenda_item(agenda_id)
            if agenda_item:
                result = await self.app.push_screen_wait(ViewAgendaDialog(agenda_item, self.subject_name))
                if result:
                    self.db.update_agenda_item(result)
                    self.refresh_agenda()
                    self.notify(f"Agenda item '{result.title}' updated")

        elif table_id == "meetings-table" and row_index < len(self.meeting_ids):
            meeting_id = self.meeting_ids[row_index]
            meeting = self.db.get_meeting(meeting_id)
            if meeting:
                result = await self.app.push_screen_wait(ViewMeetingDialog(meeting, self.subject_name, self.db))
                if result:
                    self.db.update_meeting(result)
                    self.refresh_meetings()
                    self.notify(f"Meeting updated")

        elif table_id == "notes-table" and row_index < len(self.note_ids):
            note_id = self.note_ids[row_index]
            note = self.db.get_note(note_id)
            if note:
                result = await self.app.push_screen_wait(ViewNoteDialog(note, self.subject_name, self.db))
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

    @work
    async def action_subject_lookup(self) -> None:
        """Open subject lookup dialog."""
        subject_id = await self.app.push_screen_wait(SubjectLookupDialog(self.db))
        if subject_id and subject_id != self.subject_id:
            # Switch to the selected subject
            self.app.switch_screen(SubjectDetailScreen(self.db, subject_id))

    def get_focused_table(self) -> tuple[DataTable | None, str]:
        """Get the currently focused table and its ID."""
        focused = self.app.focused
        if isinstance(focused, DataTable):
            return focused, focused.id or ""
        return None, ""

    def action_edit_item(self) -> None:
        """Edit the selected item (context-aware based on focused widget)."""
        # Check if subject header is focused
        try:
            focused = self.app.focused
            if focused and focused.id == "subject-header":
                subject = self.db.get_subject(self.subject_id)
                if subject:
                    self.app.call_later(self._edit_subject, subject)
                return
        except Exception:
            pass

        table, table_id = self.get_focused_table()

        # If no table is focused, do nothing
        if not table or table.cursor_row is None:
            return

        # Same as pressing Enter - opens the edit dialog for the selected row
        row_index = table.cursor_row

        if table_id == "actions-table" and row_index < len(self.action_ids):
            action_id = self.action_ids[row_index]
            action = self.db.get_action(action_id)
            if action:
                self.app.call_later(self._edit_action, action)
        elif table_id == "agenda-table" and row_index < len(self.agenda_ids):
            agenda_id = self.agenda_ids[row_index]
            agenda_item = self.db.get_agenda_item(agenda_id)
            if agenda_item:
                self.app.call_later(self._edit_agenda, agenda_item)
        elif table_id == "meetings-table" and row_index < len(self.meeting_ids):
            meeting_id = self.meeting_ids[row_index]
            meeting = self.db.get_meeting(meeting_id)
            if meeting:
                self.app.call_later(self._edit_meeting, meeting)
        elif table_id == "notes-table" and row_index < len(self.note_ids):
            note_id = self.note_ids[row_index]
            note = self.db.get_note(note_id)
            if note:
                self.app.call_later(self._edit_note, note)

    @work
    async def _edit_subject(self, subject: Subject) -> None:
        """Edit the subject metadata."""
        result = await self.app.push_screen_wait(EditSubjectDialog(subject))
        if result:
            self.db.update_subject(result)
            self.load_subject_data()
            self.notify(f"Subject '{result.name}' updated")

    @work
    async def _edit_action(self, action: Action) -> None:
        """Edit an action."""
        result = await self.app.push_screen_wait(ViewActionDialog(action, self.subject_name))
        if result:
            self.db.update_action(result)
            self.refresh_actions()
            self.notify(f"Action '{result.title}' updated")

    @work
    async def _edit_agenda(self, agenda_item: AgendaItem) -> None:
        """Edit an agenda item."""
        result = await self.app.push_screen_wait(ViewAgendaDialog(agenda_item, self.subject_name))
        if result:
            self.db.update_agenda_item(result)
            self.refresh_agenda()
            self.notify(f"Agenda item '{result.title}' updated")

    @work
    async def _edit_meeting(self, meeting: Meeting) -> None:
        """Edit a meeting."""
        result = await self.app.push_screen_wait(ViewMeetingDialog(meeting, self.subject_name, self.db))
        if result:
            self.db.update_meeting(result)
            self.refresh_meetings()
            self.notify("Meeting updated")

    @work
    async def _edit_note(self, note: Note) -> None:
        """Edit a note."""
        result = await self.app.push_screen_wait(ViewNoteDialog(note, self.subject_name, self.db))
        if result:
            self.db.update_note(result)
            self.refresh_notes()
            self.notify(f"Note '{result.title}' updated")

    def action_add_item(self) -> None:
        """Add new item (context-aware based on focused table)."""
        table, table_id = self.get_focused_table()

        if table_id == "agenda-table":
            self.app.call_later(self._add_agenda)
        elif table_id == "actions-table":
            self.app.call_later(self._add_action)
        elif table_id == "meetings-table":
            self.app.call_later(self._add_meeting)
        elif table_id == "notes-table":
            self.app.call_later(self._add_note)
        else:
            self.notify("Select a table first", severity="warning")

    @work
    async def _add_agenda(self) -> None:
        """Add a new agenda item."""
        result = await self.app.push_screen_wait(NewAgendaDialog(self.subject_id, self.subject_name))
        if result:
            self.db.add_agenda_item(result)
            self.refresh_agenda()
            self.notify(f"Agenda item '{result.title}' created")

    @work
    async def _add_action(self) -> None:
        """Add a new action."""
        result = await self.app.push_screen_wait(NewActionDialog(self.subject_id, self.subject_name))
        if result:
            self.db.add_action(result)
            self.refresh_actions()
            self.notify(f"Action '{result.title}' created")

    @work
    async def _add_meeting(self) -> None:
        """Add a new meeting."""
        result = await self.app.push_screen_wait(NewMeetingDialog(self.subject_id, self.subject_name, self.db))
        if result:
            self.db.add_meeting(result)
            self.refresh_meetings()
            self.notify("Meeting created")

    @work
    async def _add_note(self) -> None:
        """Add a new note."""
        result = await self.app.push_screen_wait(NewNoteDialog(self.subject_id, self.subject_name, self.db))
        if result:
            self.db.add_note(result)
            self.refresh_notes()
            self.notify(f"Note '{result.title}' created")

    def action_delete_item(self) -> None:
        """Delete the selected item (context-aware based on focused table)."""
        table, table_id = self.get_focused_table()
        if not table or table.cursor_row is None:
            return

        if table_id == "actions-table" and table.cursor_row < len(self.action_ids):
            action_id = self.action_ids[table.cursor_row]
            action = self.db.get_action(action_id)
            if action:
                self.app.call_later(self._confirm_delete_action, action)
        elif table_id == "agenda-table" and table.cursor_row < len(self.agenda_ids):
            agenda_id = self.agenda_ids[table.cursor_row]
            agenda_item = self.db.get_agenda_item(agenda_id)
            if agenda_item:
                self.app.call_later(self._confirm_delete_agenda, agenda_item)
        elif table_id == "meetings-table" and table.cursor_row < len(self.meeting_ids):
            meeting_id = self.meeting_ids[table.cursor_row]
            meeting = self.db.get_meeting(meeting_id)
            if meeting:
                self.app.call_later(self._confirm_delete_meeting, meeting)
        elif table_id == "notes-table" and table.cursor_row < len(self.note_ids):
            note_id = self.note_ids[table.cursor_row]
            note = self.db.get_note(note_id)
            if note:
                self.app.call_later(self._confirm_delete_note, note)

    @work
    async def _confirm_delete_action(self, action: Action) -> None:
        """Confirm and delete an action."""
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog("Delete Action", f"Delete action '{action.title}'?")
        )
        if confirmed:
            self.db.delete_action(action.id)
            self.refresh_actions()
            self.notify(f"Deleted action: {action.title}")

    @work
    async def _confirm_delete_agenda(self, agenda_item: AgendaItem) -> None:
        """Confirm and delete an agenda item."""
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog("Delete Agenda Item", f"Delete agenda item '{agenda_item.title}'?")
        )
        if confirmed:
            self.db.delete_agenda_item(agenda_item.id)
            self.refresh_agenda()
            self.notify(f"Deleted agenda item: {agenda_item.title}")

    @work
    async def _confirm_delete_meeting(self, meeting: Meeting) -> None:
        """Confirm and delete a meeting."""
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog("Delete Meeting", f"Delete meeting '{meeting.title}'?")
        )
        if confirmed:
            self.db.delete_meeting(meeting.id)
            self.refresh_meetings()
            self.notify(f"Deleted meeting: {meeting.title}")

    @work
    async def _confirm_delete_note(self, note: Note) -> None:
        """Confirm and delete a note."""
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog("Delete Note", f"Delete note '{note.title}'?")
        )
        if confirmed:
            self.db.delete_note(note.id)
            self.refresh_notes()
            self.notify(f"Deleted note: {note.title}")
