"""Modal dialogs for SubTUI."""

import uuid
from datetime import datetime

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

    def __init__(self, subjects: list[Subject]):
        """Initialize dialog with available subjects."""
        super().__init__()
        self.subjects = subjects

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
                yield Label("Subject:")
                subject_options = [(s.name, s.id) for s in self.subjects]
                yield Select(subject_options, id="subject-select")

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

    def action_cancel(self) -> None:
        """Cancel and close dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Create action and close dialog."""
        # Get input values
        subject_select = self.query_one("#subject-select", Select)
        title_input = self.query_one("#title-input", Input)
        due_date_input = self.query_one("#due-date-input", Input)
        status_select = self.query_one("#status-select", Select)
        tags_input = self.query_one("#tags-input", Input)
        description_area = self.query_one("#description-area", TextArea)

        subject_id = subject_select.value
        if not subject_id:
            self.notify("Please select a subject", severity="error")
            return

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

        # Create action object
        action = Action(
            id=str(uuid.uuid4())[:8],
            subject_id=subject_id,
            title=title,
            description=description,
            status=status,
            due_date=due_date,
            tags=tags,
            created_at=datetime.now(),
        )

        self.dismiss(action)


class ViewMeetingDialog(ModalScreen[Meeting | None]):
    """Dialog for viewing and editing a meeting."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "toggle_markdown_edit", "Edit Content", priority=True),
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

    def __init__(self, meeting: Meeting):
        """Initialize dialog with meeting to view/edit."""
        super().__init__()
        self.meeting = meeting
        self.markdown_edit_mode = False

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            # Metadata section (editable)
            with VerticalScroll(id="metadata-section"):
                yield Label("Date (YYYY-MM-DD HH:MM):")
                date_str = self.meeting.date.strftime("%Y-%m-%d %H:%M")
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

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        # Get metadata values
        date_input = self.query_one("#date-input", Input)
        attendees_input = self.query_one("#attendees-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        # Parse date
        try:
            meeting_date = datetime.strptime(date_input.value.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            self.notify("Invalid date format. Use YYYY-MM-DD HH:MM", severity="error")
            return

        # Parse attendees
        attendees_str = attendees_input.value.strip()
        attendees = [a.strip() for a in attendees_str.split(",") if a.strip()] if attendees_str else []

        # Update meeting
        self.meeting.date = meeting_date
        self.meeting.attendees = attendees
        self.meeting.content = text_area.text
        self.meeting.updated_at = datetime.now()

        self.dismiss(self.meeting)


class ViewNoteDialog(ModalScreen[Note | None]):
    """Dialog for viewing and editing a note."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "toggle_markdown_edit", "Edit Content", priority=True),
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

    def __init__(self, note: Note):
        """Initialize dialog with note to view/edit."""
        super().__init__()
        self.note = note
        self.markdown_edit_mode = False

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
