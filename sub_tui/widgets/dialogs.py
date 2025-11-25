"""Modal dialogs for SubTUI."""

import uuid
from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical, VerticalScroll, Container
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, TextArea, Static, Markdown, Header

from ..models import Action, ActionStatus, Subject, Meeting, Note, AgendaItem, AgendaStatus


class NewActionDialog(ModalScreen[Action | None]):
    """Dialog for creating a new action."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Create"),
    ]

    CSS = """
    NewActionDialog {
        background: black;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        margin: 2 2;
        background: black;
        border: solid $primary;
    }

    #form-header {
        width: 100%;
        height: auto;
        background: black;
        padding: 0 2;
        border-bottom: solid $primary;
    }

    #form-header Static {
        text-style: bold;
        color: $accent;
    }

    #form-content {
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }

    #form-content Label {
        margin-top: 0;
        color: $text-muted;
    }

    #form-content Input {
        margin-bottom: 0;
    }

    #form-content Select {
        margin-bottom: 0;
    }

    #form-content TextArea {
        height: 1fr;
        min-height: 10;
    }

    #instructions {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        color: $warning;
    }
    """

    def __init__(self, subject_id: str, meeting_id: str = None, note_id: str = None):
        """Initialize dialog with subject and optional content source.

        Args:
            subject_id: ID of the subject this action belongs to
            meeting_id: Optional ID of meeting if action created from meeting
            note_id: Optional ID of note if action created from note
        """
        super().__init__()
        self.subject_id = subject_id
        self.meeting_id = meeting_id
        self.note_id = note_id

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            # Header
            with Container(id="form-header"):
                yield Static("New Action")

            # Instructions
            yield Static("Fill in the details below. Ctrl+S to create, Esc to cancel.", id="instructions")

            # Form content
            with VerticalScroll(id="form-content"):
                yield Label("Title:")
                yield Input(placeholder="Action title", id="title-input")

                yield Label("Due Date (YYYY-MM-DD, optional):")
                yield Input(placeholder="2025-11-25", id="due-date-input")

                yield Label("Status:")
                yield Select(
                    [
                        ("TODO", "todo"),
                        ("In Progress", "in_progress"),
                    ],
                    value="todo",
                    id="status-select"
                )

                yield Label("Tags (comma-separated, optional):")
                yield Input(placeholder="backend, urgent", id="tags-input")

                yield Label("Description (Markdown, optional):")
                text_area = TextArea.code_editor("", language="markdown", theme="monokai", id="description-area")
                yield text_area

    def on_mount(self) -> None:
        """Focus the title input when dialog opens."""
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

    def action_cancel(self) -> None:
        """Cancel and close dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Create action and close dialog."""
        # Get input values
        title_input = self.query_one("#title-input", Input)
        due_date_input = self.query_one("#due-date-input", Input)
        status_select = self.query_one("#status-select", Select)
        tags_input = self.query_one("#tags-input", Input)
        description_area = self.query_one("#description-area", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        description = description_area.text.strip() or None

        # Parse due date
        due_date = None
        if due_date_input.value.strip():
            try:
                due_date = datetime.fromisoformat(due_date_input.value.strip())
            except ValueError:
                self.notify("Invalid date format. Use YYYY-MM-DD", severity="error")
                return

        # Parse tags
        tags_str = tags_input.value.strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        status = ActionStatus(status_select.value)

        # Create action object with source tracking
        action = Action(
            id=str(uuid.uuid4())[:8],
            subject_id=self.subject_id,
            title=title,
            description=description,
            status=status,
            due_date=due_date,
            meeting_id=self.meeting_id,
            note_id=self.note_id,
            tags=tags,
            created_at=datetime.now(),
        )

        self.dismiss(action)


class NewMeetingDialog(ModalScreen[Meeting | None]):
    """Dialog for creating a new meeting."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Create"),
        Binding("ctrl+e", "toggle_markdown_edit", "Preview", priority=True),
        Binding("ctrl+a", "add_action_from_content", "Add Action", priority=True),
    ]

    CSS = """
    NewMeetingDialog {
        background: black;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        margin: 2 2;
        background: black;
        border: solid $primary;
    }

    #metadata-section {
        width: 100%;
        height: auto;
        background: black;
        padding: 0 2;
        border-bottom: solid $primary;
    }

    #metadata-section Label {
        color: $text-muted;
        margin-top: 0;
    }

    #metadata-section Input {
        margin-bottom: 0;
    }

    #instructions {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        color: $warning;
    }

    #content-container {
        width: 100%;
        height: 1fr;
    }

    #markdown-scroll {
        width: 100%;
        height: 100%;
    }

    #markdown-viewer {
        width: 100%;
        padding: 1 2;
    }

    #content-editor {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, subject_id: str, db=None):
        """Initialize dialog.

        Args:
            subject_id: ID of the subject for this content
            db: Optional Database instance for creating actions from content
        """
        super().__init__()
        self.subject_id = subject_id
        self.markdown_edit_mode = True  # Start in edit mode
        self.db = db
        self.content_id = None  # Will be set when content is created

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            # Metadata section (editable)
            with VerticalScroll(id="metadata-section"):
                yield Label("Title:")
                yield Input(placeholder="Meeting title", id="title-input")

                yield Label("Date (YYYY-MM-DD):")
                yield Input(value=datetime.now().strftime("%Y-%m-%d"), id="date-input")

                yield Label("Attendees (comma-separated):")
                yield Input(placeholder="John Doe, Jane Smith", id="attendees-input")

            # Instructions
            yield Static("Editing content. Ctrl+E to preview, Ctrl+S to create, Esc to cancel", id="instructions")

            # Content area
            with Container(id="content-container"):
                # Markdown viewer (hidden by default)
                with VerticalScroll(id="markdown-scroll") as scroll:
                    scroll.display = False
                    content_with_breaks = "# Meeting Notes\n\n".replace('\n', '  \n')
                    yield Markdown(content_with_breaks, id="markdown-viewer")

                # Text editor (visible by default)
                text_area = TextArea.code_editor("# Meeting Notes\n\n", language="markdown", theme="monokai", id="content-editor")
                yield text_area

    def on_mount(self) -> None:
        """Focus the title input when dialog opens."""
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)
        instructions = self.query_one("#instructions", Static)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
            instructions.update("Editing content. Ctrl+E to preview, Ctrl+S to create, Esc to cancel")
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)
            instructions.update("Ctrl+E to edit content, Ctrl+S to create, Esc to cancel")

    @work
    async def action_add_action_from_content(self) -> None:
        """Add action from current content."""
        if not self.db:
            self.notify("Cannot create action: database not available", severity="error")
            return

        # Get the text area and cursor position
        text_area = self.query_one("#content-editor", TextArea)
        cursor_row, cursor_col = text_area.cursor_location

        # Show action creation dialog
        # For new content, we can't link to meeting_id/note_id yet since it doesn't exist
        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.subject_id,
                meeting_id=self.content_id  # Will be None for new content
            )
        )

        if result:
            # Save action to database
            self.app.call_from_thread(self.db.add_action, result)

            # Insert action reference at cursor position
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            self.app.call_from_thread(text_area.insert, action_ref, (cursor_row, cursor_col))

            self.notify(f"Action '{result.title}' created and linked")

    def action_cancel(self) -> None:
        """Cancel and close dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Create meeting and close dialog."""
        title_input = self.query_one("#title-input", Input)
        date_input = self.query_one("#date-input", Input)
        attendees_input = self.query_one("#attendees-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        # Parse date (without time, set to noon)
        try:
            meeting_date = datetime.strptime(date_input.value.strip(), "%Y-%m-%d")
            # Set to noon to avoid any timezone issues
            meeting_date = meeting_date.replace(hour=12, minute=0, second=0, microsecond=0)
        except ValueError:
            self.notify("Invalid date format. Use YYYY-MM-DD", severity="error")
            return

        # Parse attendees
        attendees_str = attendees_input.value.strip()
        attendees = [a.strip() for a in attendees_str.split(",") if a.strip()] if attendees_str else []

        # Create meeting object with content from editor
        meeting = Meeting(
            id=str(uuid.uuid4())[:8],
            subject_id=self.subject_id,
            title=title,
            date=meeting_date,
            attendees=attendees,
            content=text_area.text,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.dismiss(meeting)


class ViewMeetingDialog(ModalScreen[Meeting | None]):
    """Dialog for viewing and editing a meeting."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "toggle_markdown_edit", "Edit Content", priority=True),
        Binding("ctrl+a", "add_action_from_content", "Add Action", priority=True),
    ]

    CSS = """
    ViewMeetingDialog {
        background: black;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        margin: 2 2;
        background: black;
        border: solid $primary;
    }

    #metadata-section {
        width: 100%;
        height: auto;
        background: black;
        padding: 0 2;
        border-bottom: solid $primary;
    }

    #metadata-section Label {
        color: $text-muted;
        margin-top: 0;
    }

    #metadata-section Input {
        margin-bottom: 0;
    }

    #instructions {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        color: $warning;
    }

    #content-container {
        width: 100%;
        height: 1fr;
    }

    #markdown-scroll {
        width: 100%;
        height: 100%;
    }

    #markdown-viewer {
        width: 100%;
        padding: 1 2;
    }

    #content-editor {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, meeting: Meeting, db=None):
        """Initialize dialog with meeting to view/edit.

        Args:
            meeting: The meeting to view/edit
            db: Optional Database instance for creating actions from content
        """
        super().__init__()
        self.meeting = meeting
        self.markdown_edit_mode = False
        self.db = db

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            # Metadata section (editable)
            with VerticalScroll(id="metadata-section"):
                yield Label("Title:")
                yield Input(value=self.meeting.title, id="title-input")

                yield Label("Date (YYYY-MM-DD):")
                date_str = self.meeting.date.strftime("%Y-%m-%d")
                yield Input(value=date_str, id="date-input")

                yield Label("Attendees (comma-separated):")
                yield Input(value=", ".join(self.meeting.attendees), id="attendees-input")

            # Instructions
            yield Static("Ctrl+E to edit content, Ctrl+S to save, Esc to close", id="instructions")

            # Content area
            with Container(id="content-container"):
                # Markdown viewer (default) - preserve line breaks
                # Add double spaces before newlines for proper markdown rendering
                with VerticalScroll(id="markdown-scroll"):
                    content_with_breaks = self.meeting.content.replace('\n', '  \n')
                    markdown_viewer = Markdown(content_with_breaks, id="markdown-viewer")
                    yield markdown_viewer

                # Text editor (hidden by default)
                text_area = TextArea.code_editor(self.meeting.content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)
        instructions = self.query_one("#instructions", Static)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
            instructions.update("Editing content. Ctrl+E to finish, Ctrl+S to save, Esc to cancel")
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)
            instructions.update("Ctrl+E to edit content, Ctrl+S to save, Esc to close")

    @work
    async def action_add_action_from_content(self) -> None:
        """Add action from current content."""
        if not self.db:
            self.notify("Cannot create action: database not available", severity="error")
            return

        # Get the text area and cursor position
        text_area = self.query_one("#content-editor", TextArea)
        cursor_row, cursor_col = text_area.cursor_location

        # Show action creation dialog
        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.meeting.subject_id,
                meeting_id=self.meeting.id
            )
        )

        if result:
            # Save action to database
            self.app.call_from_thread(self.db.add_action, result)

            # Insert action reference at cursor position
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            self.app.call_from_thread(text_area.insert, action_ref, (cursor_row, cursor_col))

            self.notify(f"Action '{result.title}' created and linked")

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        # Get metadata values
        title_input = self.query_one("#title-input", Input)
        date_input = self.query_one("#date-input", Input)
        attendees_input = self.query_one("#attendees-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        # Parse date (without time, set to noon)
        try:
            meeting_date = datetime.strptime(date_input.value.strip(), "%Y-%m-%d")
            # Set to noon to avoid any timezone issues
            meeting_date = meeting_date.replace(hour=12, minute=0, second=0, microsecond=0)
        except ValueError:
            self.notify("Invalid date format. Use YYYY-MM-DD", severity="error")
            return

        # Parse attendees
        attendees_str = attendees_input.value.strip()
        attendees = [a.strip() for a in attendees_str.split(",") if a.strip()] if attendees_str else []

        # Update meeting
        self.meeting.title = title
        self.meeting.date = meeting_date
        self.meeting.attendees = attendees
        self.meeting.content = text_area.text
        self.meeting.updated_at = datetime.now()

        self.dismiss(self.meeting)


class NewNoteDialog(ModalScreen[Note | None]):
    """Dialog for creating a new note."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Create"),
        Binding("ctrl+e", "toggle_markdown_edit", "Preview", priority=True),
        Binding("ctrl+a", "add_action_from_content", "Add Action", priority=True),
    ]

    CSS = """
    NewNoteDialog {
        background: black;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        margin: 2 2;
        background: black;
        border: solid $primary;
    }

    #metadata-section {
        width: 100%;
        height: auto;
        background: black;
        padding: 0 2;
        border-bottom: solid $primary;
    }

    #metadata-section Label {
        color: $text-muted;
        margin-top: 0;
    }

    #metadata-section Input {
        margin-bottom: 0;
    }

    #instructions {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        color: $warning;
    }

    #content-container {
        width: 100%;
        height: 1fr;
    }

    #markdown-scroll {
        width: 100%;
        height: 100%;
    }

    #markdown-viewer {
        width: 100%;
        padding: 1 2;
    }

    #content-editor {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, subject_id: str, db=None):
        """Initialize dialog.

        Args:
            subject_id: ID of the subject for this content
            db: Optional Database instance for creating actions from content
        """
        super().__init__()
        self.subject_id = subject_id
        self.markdown_edit_mode = True  # Start in edit mode
        self.db = db
        self.content_id = None  # Will be set when content is created

    def compose(self) -> ComposeResult:
        """Compose dialog UI."""
        with Container(id="dialog-container"):
            # Metadata section (editable)
            with VerticalScroll(id="metadata-section"):
                yield Label("Title:")
                yield Input(placeholder="Note title", id="title-input")

                yield Label("Tags (comma-separated, optional):")
                yield Input(placeholder="documentation, reference", id="tags-input")

            # Instructions
            yield Static("Editing content. Ctrl+E to preview, Ctrl+S to create, Esc to cancel", id="instructions")

            # Content area
            with Container(id="content-container"):
                # Markdown viewer (hidden by default)
                with VerticalScroll(id="markdown-scroll") as scroll:
                    scroll.display = False
                    content_with_breaks = "# Note\n\n".replace('\n', '  \n')
                    yield Markdown(content_with_breaks, id="markdown-viewer")

                # Text editor (visible by default)
                text_area = TextArea.code_editor("# Note\n\n", language="markdown", theme="monokai", id="content-editor")
                yield text_area

    def on_mount(self) -> None:
        """Focus the title input when dialog opens."""
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)
        instructions = self.query_one("#instructions", Static)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
            instructions.update("Editing content. Ctrl+E to preview, Ctrl+S to create, Esc to cancel")
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)
            instructions.update("Ctrl+E to edit content, Ctrl+S to create, Esc to cancel")

    @work
    async def action_add_action_from_content(self) -> None:
        """Add action from current content."""
        if not self.db:
            self.notify("Cannot create action: database not available", severity="error")
            return

        # Get the text area and cursor position
        text_area = self.query_one("#content-editor", TextArea)
        cursor_row, cursor_col = text_area.cursor_location

        # Show action creation dialog
        # For new content, we can't link to note_id yet since it doesn't exist
        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.subject_id,
                note_id=self.content_id  # Will be None for new content
            )
        )

        if result:
            # Save action to database
            self.app.call_from_thread(self.db.add_action, result)

            # Insert action reference at cursor position
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            self.app.call_from_thread(text_area.insert, action_ref, (cursor_row, cursor_col))

            self.notify(f"Action '{result.title}' created and linked")

    def action_cancel(self) -> None:
        """Cancel and close dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Create note and close dialog."""
        title_input = self.query_one("#title-input", Input)
        tags_input = self.query_one("#tags-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        # Parse tags
        tags_str = tags_input.value.strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        # Create note object with content from editor
        note = Note(
            id=str(uuid.uuid4())[:8],
            subject_id=self.subject_id,
            title=title,
            content=text_area.text,
            tags=tags,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.dismiss(note)


class ViewNoteDialog(ModalScreen[Note | None]):
    """Dialog for viewing and editing a note."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "toggle_markdown_edit", "Edit Content", priority=True),
        Binding("ctrl+a", "add_action_from_content", "Add Action", priority=True),
    ]

    CSS = """
    ViewNoteDialog {
        background: black;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        margin: 2 2;
        background: black;
        border: solid $primary;
    }

    #metadata-section {
        width: 100%;
        height: auto;
        background: black;
        padding: 0 2;
        border-bottom: solid $primary;
    }

    #metadata-section Label {
        color: $text-muted;
        margin-top: 0;
    }

    #metadata-section Input {
        margin-bottom: 0;
    }

    #instructions {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        color: $warning;
    }

    #content-container {
        width: 100%;
        height: 1fr;
    }

    #markdown-scroll {
        width: 100%;
        height: 100%;
    }

    #markdown-viewer {
        width: 100%;
        padding: 1 2;
    }

    #content-editor {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, note: Note, db=None):
        """Initialize dialog with note to view/edit.

        Args:
            note: The note to view/edit
            db: Optional Database instance for creating actions from content
        """
        super().__init__()
        self.note = note
        self.markdown_edit_mode = False
        self.db = db

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            # Metadata section (editable)
            with VerticalScroll(id="metadata-section"):
                yield Label("Title:")
                yield Input(value=self.note.title, id="title-input")

                yield Label("Tags (comma-separated, optional):")
                yield Input(value=", ".join(self.note.tags) if self.note.tags else "", id="tags-input")

            # Instructions
            yield Static("Ctrl+E to edit content, Ctrl+S to save, Esc to close", id="instructions")

            # Content area
            with Container(id="content-container"):
                # Markdown viewer (default)
                with VerticalScroll(id="markdown-scroll"):
                    content_with_breaks = self.note.content.replace('\n', '  \n')
                    markdown_viewer = Markdown(content_with_breaks, id="markdown-viewer")
                    yield markdown_viewer

                # Text editor (hidden by default)
                text_area = TextArea.code_editor(self.note.content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)
        instructions = self.query_one("#instructions", Static)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
            instructions.update("Editing content. Ctrl+E to finish, Ctrl+S to save, Esc to cancel")
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)
            instructions.update("Ctrl+E to edit content, Ctrl+S to save, Esc to close")

    @work
    async def action_add_action_from_content(self) -> None:
        """Add action from current content."""
        if not self.db:
            self.notify("Cannot create action: database not available", severity="error")
            return

        # Get the text area and cursor position
        text_area = self.query_one("#content-editor", TextArea)
        cursor_row, cursor_col = text_area.cursor_location

        # Show action creation dialog
        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.note.subject_id,
                note_id=self.note.id
            )
        )

        if result:
            # Save action to database
            self.app.call_from_thread(self.db.add_action, result)

            # Insert action reference at cursor position
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            self.app.call_from_thread(text_area.insert, action_ref, (cursor_row, cursor_col))

            self.notify(f"Action '{result.title}' created and linked")

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        # Get metadata values
        title_input = self.query_one("#title-input", Input)
        tags_input = self.query_one("#tags-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        # Parse tags
        tags_str = tags_input.value.strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        # Update note
        self.note.title = title
        self.note.tags = tags
        self.note.content = text_area.text
        self.note.updated_at = datetime.now()

        self.dismiss(self.note)


class ViewActionDialog(ModalScreen[Action | None]):
    """Dialog for viewing and editing an action."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "toggle_markdown_edit", "Edit Content", priority=True),
    ]

    CSS = """
    ViewActionDialog {
        background: black;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        margin: 2 2;
        background: black;
        border: solid $primary;
    }

    #metadata-section {
        width: 100%;
        height: auto;
        background: black;
        padding: 0 2;
        border-bottom: solid $primary;
    }

    #metadata-section Label {
        color: $text-muted;
        margin-top: 0;
    }

    #metadata-section Input {
        margin-bottom: 0;
    }

    #metadata-section Select {
        margin-bottom: 0;
    }

    #instructions {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        color: $warning;
    }

    #content-container {
        width: 100%;
        height: 1fr;
    }

    #markdown-scroll {
        width: 100%;
        height: 100%;
    }

    #markdown-viewer {
        width: 100%;
        padding: 1 2;
    }

    #content-editor {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, action: Action):
        """Initialize dialog with action to view/edit."""
        super().__init__()
        self.action = action
        self.markdown_edit_mode = False

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            # Metadata section (editable)
            with VerticalScroll(id="metadata-section"):
                yield Label("Title:")
                yield Input(value=self.action.title, id="title-input")

                yield Label("Due Date (YYYY-MM-DD, optional):")
                due_date_str = self.action.due_date.strftime("%Y-%m-%d") if self.action.due_date else ""
                yield Input(value=due_date_str, placeholder="2025-11-25", id="due-date-input")

                yield Label("Status:")
                yield Select(
                    [
                        ("TODO", "todo"),
                        ("In Progress", "in_progress"),
                        ("Done", "done"),
                    ],
                    value=self.action.status.value,
                    id="status-select"
                )

                yield Label("Tags (comma-separated, optional):")
                yield Input(value=", ".join(self.action.tags), id="tags-input")

            # Instructions
            yield Static("Ctrl+E to edit content, Ctrl+S to save, Esc to close", id="instructions")

            # Content area - description as markdown
            with Container(id="content-container"):
                # Markdown viewer (default)
                with VerticalScroll(id="markdown-scroll"):
                    content = self.action.description or "*No description*"
                    content_with_breaks = content.replace('\n', '  \n')
                    markdown_viewer = Markdown(content_with_breaks, id="markdown-viewer")
                    yield markdown_viewer

                # Text editor (hidden by default)
                text_area = TextArea.code_editor(content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)
        instructions = self.query_one("#instructions", Static)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
            instructions.update("Editing content. Ctrl+E to finish, Ctrl+S to save, Esc to cancel")
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)
            instructions.update("Ctrl+E to edit content, Ctrl+S to save, Esc to close")

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        # Get metadata values
        title_input = self.query_one("#title-input", Input)
        due_date_input = self.query_one("#due-date-input", Input)
        status_select = self.query_one("#status-select", Select)
        tags_input = self.query_one("#tags-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        # Parse due date
        due_date = None
        if due_date_input.value.strip():
            try:
                due_date = datetime.fromisoformat(due_date_input.value.strip())
            except ValueError:
                self.notify("Invalid date format. Use YYYY-MM-DD", severity="error")
                return

        # Parse tags
        tags_str = tags_input.value.strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        old_status = self.action.status
        new_status = ActionStatus(status_select.value)

        # Update action
        self.action.title = title
        self.action.due_date = due_date
        self.action.status = new_status
        self.action.tags = tags
        self.action.description = text_area.text if text_area.text.strip() else None

        # Update completed_at if status changed
        if old_status != ActionStatus.DONE and new_status == ActionStatus.DONE:
            self.action.completed_at = datetime.now()
        elif old_status == ActionStatus.DONE and new_status != ActionStatus.DONE:
            self.action.completed_at = None

        self.dismiss(self.action)


class ViewAgendaDialog(ModalScreen[AgendaItem | None]):
    """Dialog for viewing and editing an agenda item."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "toggle_markdown_edit", "Edit Content", priority=True),
    ]

    CSS = """
    ViewAgendaDialog {
        background: black;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        margin: 2 2;
        background: black;
        border: solid $primary;
    }

    #metadata-section {
        width: 100%;
        height: auto;
        background: black;
        padding: 0 2;
        border-bottom: solid $primary;
    }

    #metadata-section Label {
        color: $text-muted;
        margin-top: 0;
    }

    #metadata-section Input {
        margin-bottom: 0;
    }

    #metadata-section Select {
        margin-bottom: 0;
    }

    #instructions {
        width: 100%;
        height: auto;
        padding: 0 2;
        background: $boost;
        color: $warning;
    }

    #content-container {
        width: 100%;
        height: 1fr;
    }

    #markdown-scroll {
        width: 100%;
        height: 100%;
    }

    #markdown-viewer {
        width: 100%;
        padding: 1 2;
    }

    #content-editor {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, agenda_item: AgendaItem):
        """Initialize dialog with agenda item to view/edit."""
        super().__init__()
        self.agenda_item = agenda_item
        self.markdown_edit_mode = False

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            # Metadata section (editable)
            with VerticalScroll(id="metadata-section"):
                yield Label("Title:")
                yield Input(value=self.agenda_item.title, id="title-input")

                yield Label("Priority (1-10):")
                yield Input(value=str(self.agenda_item.priority), id="priority-input")

                yield Label("Status:")
                yield Select(
                    [
                        ("Active", "active"),
                        ("Discussed", "discussed"),
                        ("Archived", "archived"),
                    ],
                    value=self.agenda_item.status.value,
                    id="status-select"
                )

            # Instructions
            yield Static("Ctrl+E to edit content, Ctrl+S to save, Esc to close", id="instructions")

            # Content area - description as markdown
            with Container(id="content-container"):
                # Markdown viewer (default)
                with VerticalScroll(id="markdown-scroll"):
                    content = self.agenda_item.description or "*No description*"
                    content_with_breaks = content.replace('\n', '  \n')
                    markdown_viewer = Markdown(content_with_breaks, id="markdown-viewer")
                    yield markdown_viewer

                # Text editor (hidden by default)
                text_area = TextArea.code_editor(content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)
        instructions = self.query_one("#instructions", Static)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
            instructions.update("Editing content. Ctrl+E to finish, Ctrl+S to save, Esc to cancel")
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)
            instructions.update("Ctrl+E to edit content, Ctrl+S to save, Esc to close")

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        # Get metadata values
        title_input = self.query_one("#title-input", Input)
        priority_input = self.query_one("#priority-input", Input)
        status_select = self.query_one("#status-select", Select)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        # Parse priority
        try:
            priority = int(priority_input.value.strip())
            if priority < 1 or priority > 10:
                self.notify("Priority must be between 1 and 10", severity="error")
                return
        except ValueError:
            self.notify("Priority must be a number", severity="error")
            return

        old_status = self.agenda_item.status
        new_status = AgendaStatus(status_select.value)

        # Update agenda item
        self.agenda_item.title = title
        self.agenda_item.priority = priority
        self.agenda_item.status = new_status
        self.agenda_item.description = text_area.text if text_area.text.strip() else None

        # Update discussed_at if status changed to discussed
        if old_status != AgendaStatus.DISCUSSED and new_status == AgendaStatus.DISCUSSED:
            self.agenda_item.discussed_at = datetime.now()

        self.dismiss(self.agenda_item)
