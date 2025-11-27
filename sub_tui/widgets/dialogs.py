"""Modal dialogs for SubTUI."""

import uuid
from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll, Container
from textual.screen import ModalScreen
from textual.widgets import Footer, Input, Label, Markdown, Select, TextArea

from ..models import Action, ActionStatus, Subject, SubjectType, Meeting, Note, AgendaItem, AgendaStatus
from ..database import Database


class ConfirmDialog(ModalScreen[bool]):
    """Simple confirmation dialog."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "confirm", "Confirm", show=True),
        Binding("y", "confirm", "Yes", show=True),
        Binding("n", "cancel", "No", show=True),
    ]

    CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #confirm-container {
        width: 50%;
        height: auto;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 1 2;
    }

    #confirm-message {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }
    """

    def __init__(self, title: str, message: str):
        """Initialize confirmation dialog."""
        super().__init__()
        self.title = title
        self.message = message

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        container = Container(id="confirm-container")
        container.border_title = self.title
        with container:
            yield Label(self.message, id="confirm-message")
        yield Footer()

    def action_confirm(self) -> None:
        """Confirm the action."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel the action."""
        self.dismiss(False)


class SubjectLookupDialog(ModalScreen[str | None]):
    """Dialog for searching and selecting a subject."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "select", "Select", show=True),
        Binding("down", "focus_next", "Next", show=False),
        Binding("up", "focus_previous", "Previous", show=False),
    ]

    CSS = """
    SubjectLookupDialog {
        align: center middle;
    }

    #lookup-container {
        width: 70%;
        height: 70%;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 0 1 1 1;
    }

    #search-input {
        margin: 1 1 0 1;
    }

    #results-table {
        margin: 1;
        height: 1fr;
    }

    #no-results {
        margin: 1;
        color: $text-muted;
        text-align: center;
    }
    """

    def __init__(self, db: Database):
        """Initialize dialog with database reference.

        Args:
            db: Database instance for searching subjects
        """
        super().__init__()
        self.db = db
        self.subject_ids: list[str] = []

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        from textual.widgets import DataTable

        container = Container(id="lookup-container")
        container.border_title = "Find Subject"
        with container:
            yield Input(placeholder="Type to search subjects...", id="search-input")
            table = DataTable(id="results-table")
            table.add_columns("Type", "Name", "Code", "Description")
            table.cursor_type = "row"
            yield table
            yield Label("Start typing to search...", id="no-results")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the search input and load all subjects initially."""
        self.query_one("#search-input", Input).focus()
        self._refresh_results("")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._refresh_results(event.value)

    def _refresh_results(self, query: str) -> None:
        """Refresh the results table based on search query."""
        from textual.widgets import DataTable

        table = self.query_one("#results-table", DataTable)
        no_results_label = self.query_one("#no-results", Label)
        table.clear()
        self.subject_ids = []

        # Get subjects - either all or filtered by search
        if query.strip():
            # Add prefix matching with * suffix for FTS5
            # Escape special FTS characters and add wildcard
            search_query = query.strip()
            # Add * to each word for prefix matching
            words = search_query.split()
            fts_query = " ".join(f"{word}*" for word in words if word)

            # Use FTS search for subjects only
            results = self.db.search(fts_query, content_types=['subject'])
            subject_ids = [r['content_id'] for r in results]
            subjects = [self.db.get_subject(sid) for sid in subject_ids]
            subjects = [s for s in subjects if s is not None]

            # If FTS returns nothing, fall back to simple LIKE search
            if not subjects:
                all_subjects = self.db.get_all_subjects()
                search_lower = query.strip().lower()
                subjects = [
                    s for s in all_subjects
                    if search_lower in s.name.lower()
                    or (s.code and search_lower in s.code.lower())
                    or (s.description and search_lower in s.description.lower())
                ]
        else:
            # Show all subjects when no query
            subjects = self.db.get_all_subjects()

        if subjects:
            table.display = True
            no_results_label.display = False

            for subject in subjects:
                self.subject_ids.append(subject.id)
                type_icon = {
                    SubjectType.PROJECT: "PRJ",
                    SubjectType.BOARD: "BRD",
                    SubjectType.TEAM: "TEM",
                    SubjectType.PERSON: "PER",
                }.get(subject.type, "???")
                table.add_row(
                    type_icon,
                    subject.name,
                    subject.code or "-",
                    (subject.description or "-")[:40],
                )

            # Select first row if available
            if table.row_count > 0:
                table.move_cursor(row=0)
        else:
            table.display = False
            no_results_label.display = True
            if query.strip():
                no_results_label.update("No subjects found")
            else:
                no_results_label.update("No subjects available")

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_select(self) -> None:
        """Select the current subject and close."""
        from textual.widgets import DataTable

        table = self.query_one("#results-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.subject_ids):
            subject_id = self.subject_ids[table.cursor_row]
            self.dismiss(subject_id)
        else:
            self.dismiss(None)

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection (Enter/double-click on table)."""
        if event.data_table.id == "results-table":
            self.action_select()


# Shared CSS for all View dialogs
VIEW_DIALOG_CSS = """
    align: center middle;

    #dialog-container {
        width: 95%;
        height: 90%;
        layout: vertical;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        border-subtitle-color: $text-muted;
        padding: 0 1 1 1;
    }

    /* Subject metadata - non-selectable display */
    #subject-info {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: $boost;
    }

    #subject-info Label {
        color: $text-muted;
    }

    #subject-info .value {
        color: $text;
    }

    /* Item metadata - selectable, toggle editable */
    #metadata-section {
        width: 100%;
        height: auto;
        padding: 0 1 1 1;
        border: solid $primary;
        border-title-color: $text-muted;
        border-title-style: bold;
    }

    #metadata-section:focus-within {
        border: solid $accent;
        border-title-color: $accent;
    }

    #metadata-display, #metadata-edit {
        width: 100%;
        height: auto;
    }

    .metadata-row {
        width: 100%;
        height: auto;
        padding: 0;
    }

    .metadata-field {
        width: 1fr;
        height: auto;
        padding-right: 2;
    }

    .metadata-field Label {
        color: $text-muted;
        margin: 0;
    }

    .metadata-field .display-value {
        color: $text;
        margin: 0;
        padding: 0 1;
    }

    .metadata-field Input {
        margin: 0;
    }

    .metadata-field Select {
        margin: 0;
    }

    /* Content section - selectable, toggle editable */
    #content-section {
        width: 100%;
        height: 1fr;
        padding: 0 1 1 1;
        border: solid $primary;
        border-title-color: $text-muted;
        border-title-style: bold;
    }

    #content-section:focus-within {
        border: solid $accent;
        border-title-color: $accent;
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
    }
"""


class BaseViewDialog(ModalScreen[object]):
    """Base class for view/edit dialogs with metadata and content sections."""

    BINDINGS = [
        Binding("escape", "cancel", "Close", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("e", "toggle_edit", "Edit", show=True),
    ]

    # Override in subclasses to customize empty content placeholder
    EMPTY_CONTENT_PLACEHOLDER = "*No content*"

    def __init__(self) -> None:
        """Initialize base dialog state."""
        super().__init__()
        self.metadata_edit_mode: bool = False
        self.content_edit_mode: bool = False

    def _is_child_of(self, widget, parent) -> bool:
        """Check if widget is a descendant of parent."""
        current = widget.parent
        while current:
            if current == parent:
                return True
            current = current.parent
        return False

    def action_toggle_edit(self) -> None:
        """Toggle edit mode for the focused section."""
        focused = self.app.focused

        metadata_section = self.query_one("#metadata-section", Container)
        content_section = self.query_one("#content-section", Container)

        if focused == metadata_section or (focused and self._is_child_of(focused, metadata_section)):
            self._toggle_metadata_edit()
        elif focused == content_section or (focused and self._is_child_of(focused, content_section)):
            self._toggle_content_edit()

    def _toggle_metadata_edit(self) -> None:
        """Toggle metadata editing mode. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _toggle_metadata_edit")

    def _toggle_content_edit(self) -> None:
        """Toggle content editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)

        self.content_edit_mode = not self.content_edit_mode

        if self.content_edit_mode:
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
        else:
            text_area.display = False
            markdown_scroll.display = True
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks if text_area.text.strip() else self.EMPTY_CONTENT_PLACEHOLDER)
            self.query_one("#content-section", Container).focus()

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save changes and close the dialog. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement action_save")


class NewSubjectDialog(ModalScreen[Subject | None]):
    """Dialog for creating a new subject."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "save", "Create", show=True),
    ]

    CSS = """
    NewSubjectDialog {
        align: center middle;
    }

    #dialog-container {
        width: 60%;
        height: auto;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 0 1 1 1;
    }

    #form-content {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    #form-content Label {
        margin-top: 1;
        color: $text-muted;
    }

    #form-content Input {
        margin: 0;
    }

    #form-content Select {
        margin: 0;
    }
    """

    def __init__(self, subject_type: SubjectType = None):
        """Initialize dialog with optional pre-selected type.

        Args:
            subject_type: Optional pre-selected subject type
        """
        super().__init__()
        self.default_type = subject_type

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        container = Container(id="dialog-container")
        container.border_title = "New Subject"
        with container:
            # Form content
            with Vertical(id="form-content"):
                yield Label("Name:")
                yield Input(placeholder="Subject name", id="name-input")

                yield Label("Type:")
                type_options = [
                    ("Project", "project"),
                    ("Board", "board"),
                    ("Team", "team"),
                    ("Person", "person"),
                ]
                default_value = self.default_type.value if self.default_type else "project"
                yield Select(type_options, value=default_value, id="type-select")

                yield Label("Code (optional):")
                yield Input(placeholder="Short code (e.g., PROJ-1)", id="code-input")

                yield Label("Description (optional):")
                yield Input(placeholder="Brief description", id="description-input")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the name input when dialog opens."""
        name_input = self.query_one("#name-input", Input)
        name_input.focus()

    def action_cancel(self) -> None:
        """Cancel and close dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Create subject and close dialog."""
        name_input = self.query_one("#name-input", Input)
        type_select = self.query_one("#type-select", Select)
        code_input = self.query_one("#code-input", Input)
        description_input = self.query_one("#description-input", Input)

        name = name_input.value.strip()
        if not name:
            self.notify("Name is required", severity="error")
            return

        subject_type = SubjectType(type_select.value)
        code = code_input.value.strip() or None
        description = description_input.value.strip() or None

        now = datetime.now()
        subject = Subject(
            id=str(uuid.uuid4())[:8],
            name=name,
            type=subject_type,
            code=code,
            description=description,
            created_at=now,
            last_reviewed_at=now,
        )

        self.dismiss(subject)


class EditSubjectDialog(ModalScreen[Subject | None]):
    """Dialog for editing a subject."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
    ]

    CSS = """
    EditSubjectDialog {
        align: center middle;
    }

    #dialog-container {
        width: 60%;
        height: auto;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 0 1 1 1;
    }

    #form-content {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    #form-content Label {
        margin-top: 1;
        color: $text-muted;
    }

    #form-content Input {
        margin: 0;
    }

    #form-content Select {
        margin: 0;
    }
    """

    def __init__(self, subject: Subject):
        """Initialize dialog with subject to edit.

        Args:
            subject: The subject to edit
        """
        super().__init__()
        self.subject = subject

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        container = Container(id="dialog-container")
        container.border_title = "Edit Subject"
        with container:
            # Form content
            with Vertical(id="form-content"):
                yield Label("Name:")
                yield Input(value=self.subject.name, id="name-input")

                yield Label("Type:")
                type_options = [
                    ("Project", "project"),
                    ("Board", "board"),
                    ("Team", "team"),
                    ("Person", "person"),
                ]
                yield Select(type_options, value=self.subject.type.value, id="type-select")

                yield Label("Code (optional):")
                yield Input(value=self.subject.code or "", placeholder="Short code (e.g., PROJ-1)", id="code-input")

                yield Label("Description (optional):")
                yield Input(value=self.subject.description or "", placeholder="Brief description", id="description-input")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the name input when dialog opens."""
        name_input = self.query_one("#name-input", Input)
        name_input.focus()

    def action_cancel(self) -> None:
        """Cancel and close dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save subject and close dialog."""
        name_input = self.query_one("#name-input", Input)
        type_select = self.query_one("#type-select", Select)
        code_input = self.query_one("#code-input", Input)
        description_input = self.query_one("#description-input", Input)

        name = name_input.value.strip()
        if not name:
            self.notify("Name is required", severity="error")
            return

        # Update subject
        self.subject.name = name
        self.subject.type = SubjectType(type_select.value)
        self.subject.code = code_input.value.strip() or None
        self.subject.description = description_input.value.strip() or None

        self.dismiss(self.subject)


class NewActionDialog(ModalScreen[Action | None]):
    """Dialog for creating a new action."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "save", "Create", show=True),
    ]

    CSS = """
    NewActionDialog {
        align: center middle;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        border-subtitle-color: $text-muted;
        padding: 0 1 1 1;
    }

    #title-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    #metadata-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .metadata-field {
        width: 1fr;
        height: auto;
        padding-right: 2;
    }

    .metadata-field Label {
        color: $text-muted;
        margin: 0;
    }

    .metadata-field Input {
        margin: 0;
    }

    .metadata-field Select {
        margin: 0;
    }

    #content-section {
        width: 100%;
        height: 1fr;
        padding: 0 1 1 1;
    }

    #content-section Label {
        color: $text-muted;
        margin: 0;
    }

    #content-section TextArea {
        height: 1fr;
        min-height: 5;
    }
    """

    def __init__(self, subject_id: str, subject_name: str = "", meeting_id: str = None, note_id: str = None):
        """Initialize dialog with subject and optional content source.

        Args:
            subject_id: ID of the subject this action belongs to
            subject_name: Name of the subject (for display in header)
            meeting_id: Optional ID of meeting if action created from meeting
            note_id: Optional ID of note if action created from note
        """
        super().__init__()
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.meeting_id = meeting_id
        self.note_id = note_id

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        container = Container(id="dialog-container")
        container.border_title = "New Action"
        if self.subject_name:
            container.border_subtitle = self.subject_name
        with container:
            # Title row (full width)
            with Horizontal(id="title-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Title:")
                    yield Input(placeholder="Action title", id="title-input")

            # Dense metadata row
            with Horizontal(id="metadata-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Due Date:")
                    yield Input(placeholder="YYYY-MM-DD", id="due-date-input")

                with Vertical(classes="metadata-field"):
                    yield Label("Status:")
                    yield Select(
                        [("TODO", "todo"), ("In Progress", "in_progress")],
                        value="todo",
                        id="status-select"
                    )

                with Vertical(classes="metadata-field"):
                    yield Label("Tags:")
                    yield Input(placeholder="tag1, tag2", id="tags-input")

            # Content area (description)
            with Vertical(id="content-section"):
                yield Label("Description (Markdown):")
                yield TextArea.code_editor("", language="markdown", theme="monokai", id="description-area")
        yield Footer()

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
        Binding("escape", "cancel", "Close", show=True),
        Binding("ctrl+s", "save", "Create", show=True),
        Binding("ctrl+e", "toggle_markdown_edit", "Preview", show=True),
        Binding("ctrl+a", "add_action_from_content", "Add Action", show=True),
    ]

    CSS = """
    NewMeetingDialog {
        align: center middle;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        border-subtitle-color: $text-muted;
        padding: 0 1 1 1;
    }

    #title-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    #metadata-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .metadata-field {
        width: 1fr;
        height: auto;
        padding-right: 2;
    }

    .metadata-field Label {
        color: $text-muted;
        margin: 0;
    }

    .metadata-field Input {
        margin: 0;
    }

    #content-container {
        width: 100%;
        height: 1fr;
        padding: 0 1 1 1;
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
    }
    """

    def __init__(self, subject_id: str, subject_name: str = "", db=None):
        """Initialize dialog.

        Args:
            subject_id: ID of the subject for this content
            subject_name: Name of the subject (for display in header)
            db: Optional Database instance for creating actions from content
        """
        super().__init__()
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.markdown_edit_mode = True  # Start in edit mode
        self.db = db

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        container = Container(id="dialog-container")
        container.border_title = "New Meeting"
        if self.subject_name:
            container.border_subtitle = self.subject_name
        with container:
            # Title row (full width)
            with Horizontal(id="title-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Title:")
                    yield Input(placeholder="Meeting title", id="title-input")

            # Dense metadata row
            with Horizontal(id="metadata-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Date:")
                    yield Input(value=datetime.now().strftime("%Y-%m-%d"), id="date-input")

                with Vertical(classes="metadata-field"):
                    yield Label("Attendees:")
                    yield Input(placeholder="John, Jane", id="attendees-input")

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
        yield Footer()

    def on_mount(self) -> None:
        """Focus the title input when dialog opens."""
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)

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
        # Note: meeting_id is None because the meeting doesn't exist yet (created on save)
        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.subject_id,
                subject_name=self.subject_name,
                meeting_id=None
            )
        )

        if result:
            # Save action to database
            self.db.add_action(result)

            # Insert action reference at cursor position
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            text_area.insert(action_ref, (cursor_row, cursor_col))

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


class ViewMeetingDialog(BaseViewDialog):
    """Dialog for viewing and editing a meeting."""

    BINDINGS = BaseViewDialog.BINDINGS + [
        Binding("ctrl+a", "add_action_from_content", "Add Action", show=True),
    ]

    CSS = f"ViewMeetingDialog {{ {VIEW_DIALOG_CSS} }}"

    def __init__(self, meeting: Meeting, subject_name: str = "", db=None):
        """Initialize dialog with meeting to view/edit."""
        super().__init__()
        self.meeting = meeting
        self.subject_name = subject_name
        self.db = db

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        date_str = self.meeting.date.strftime("%Y-%m-%d")
        attendees_str = ", ".join(self.meeting.attendees) if self.meeting.attendees else "-"

        container = Container(id="dialog-container")
        container.border_title = "Meeting"
        with container:
            with Horizontal(id="subject-info"):
                yield Label(f"Subject: ")
                yield Label(self.subject_name or "-", classes="value")

            metadata_section = Container(id="metadata-section")
            metadata_section.border_title = "Metadata"
            metadata_section.can_focus = True
            with metadata_section:
                with Vertical(id="metadata-display"):
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Label(self.meeting.title, classes="display-value", id="title-display")
                        with Vertical(classes="metadata-field"):
                            yield Label("Date:")
                            yield Label(date_str, classes="display-value", id="date-display")
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Attendees:")
                            yield Label(attendees_str, classes="display-value", id="attendees-display")

                edit_container = Vertical(id="metadata-edit")
                edit_container.display = False
                with edit_container:
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Input(value=self.meeting.title, id="title-input")
                        with Vertical(classes="metadata-field"):
                            yield Label("Date:")
                            yield Input(value=date_str, id="date-input")
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Attendees:")
                            yield Input(value=", ".join(self.meeting.attendees), id="attendees-input")

            content_section = Container(id="content-section")
            content_section.border_title = "Minutes"
            content_section.can_focus = True
            with content_section:
                with VerticalScroll(id="markdown-scroll"):
                    content_with_breaks = self.meeting.content.replace('\n', '  \n')
                    yield Markdown(content_with_breaks, id="markdown-viewer")

                text_area = TextArea.code_editor(self.meeting.content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area
        yield Footer()

    def _toggle_metadata_edit(self) -> None:
        """Toggle metadata editing mode."""
        metadata_display = self.query_one("#metadata-display", Vertical)
        metadata_edit = self.query_one("#metadata-edit", Vertical)

        self.metadata_edit_mode = not self.metadata_edit_mode

        if self.metadata_edit_mode:
            metadata_display.display = False
            metadata_edit.display = True
            self.query_one("#title-input", Input).focus()
        else:
            self.query_one("#title-display", Label).update(self.query_one("#title-input", Input).value or "-")
            self.query_one("#date-display", Label).update(self.query_one("#date-input", Input).value or "-")
            self.query_one("#attendees-display", Label).update(self.query_one("#attendees-input", Input).value or "-")

            metadata_edit.display = False
            metadata_display.display = True
            self.query_one("#metadata-section", Container).focus()

    @work
    async def action_add_action_from_content(self) -> None:
        """Add action from current content."""
        if not self.db:
            self.notify("Cannot create action: database not available", severity="error")
            return

        text_area = self.query_one("#content-editor", TextArea)
        cursor_row, cursor_col = text_area.cursor_location

        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.meeting.subject_id,
                subject_name=self.subject_name,
                meeting_id=self.meeting.id
            )
        )

        if result:
            self.db.add_action(result)
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            text_area.insert(action_ref, (cursor_row, cursor_col))
            self.notify(f"Action '{result.title}' created and linked")

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        title_input = self.query_one("#title-input", Input)
        date_input = self.query_one("#date-input", Input)
        attendees_input = self.query_one("#attendees-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        try:
            meeting_date = datetime.strptime(date_input.value.strip(), "%Y-%m-%d")
            meeting_date = meeting_date.replace(hour=12, minute=0, second=0, microsecond=0)
        except ValueError:
            self.notify("Invalid date format. Use YYYY-MM-DD", severity="error")
            return

        attendees_str = attendees_input.value.strip()
        attendees = [a.strip() for a in attendees_str.split(",") if a.strip()] if attendees_str else []

        self.meeting.title = title
        self.meeting.date = meeting_date
        self.meeting.attendees = attendees
        self.meeting.content = text_area.text
        self.meeting.updated_at = datetime.now()

        self.dismiss(self.meeting)


class NewNoteDialog(ModalScreen[Note | None]):
    """Dialog for creating a new note."""

    BINDINGS = [
        Binding("escape", "cancel", "Close", show=True),
        Binding("ctrl+s", "save", "Create", show=True),
        Binding("ctrl+e", "toggle_markdown_edit", "Preview", show=True),
        Binding("ctrl+a", "add_action_from_content", "Add Action", show=True),
    ]

    CSS = """
    NewNoteDialog {
        align: center middle;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        border-subtitle-color: $text-muted;
        padding: 0 1 1 1;
    }

    #title-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    #metadata-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .metadata-field {
        width: 1fr;
        height: auto;
        padding-right: 2;
    }

    .metadata-field Label {
        color: $text-muted;
        margin: 0;
    }

    .metadata-field Input {
        margin: 0;
    }

    #content-container {
        width: 100%;
        height: 1fr;
        padding: 0 1 1 1;
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
    }
    """

    def __init__(self, subject_id: str, subject_name: str = "", db=None):
        """Initialize dialog.

        Args:
            subject_id: ID of the subject for this content
            subject_name: Name of the subject (for display in header)
            db: Optional Database instance for creating actions from content
        """
        super().__init__()
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.markdown_edit_mode = True  # Start in edit mode
        self.db = db

    def compose(self) -> ComposeResult:
        """Compose dialog UI."""
        container = Container(id="dialog-container")
        container.border_title = "New Note"
        if self.subject_name:
            container.border_subtitle = self.subject_name
        with container:
            # Title row (full width)
            with Horizontal(id="title-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Title:")
                    yield Input(placeholder="Note title", id="title-input")

            # Dense metadata row
            with Horizontal(id="metadata-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Tags:")
                    yield Input(placeholder="tag1, tag2", id="tags-input")

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
        yield Footer()

    def on_mount(self) -> None:
        """Focus the title input when dialog opens."""
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

    def action_toggle_markdown_edit(self) -> None:
        """Toggle markdown editing mode."""
        markdown_scroll = self.query_one("#markdown-scroll", VerticalScroll)
        markdown_viewer = self.query_one("#markdown-viewer", Markdown)
        text_area = self.query_one("#content-editor", TextArea)

        self.markdown_edit_mode = not self.markdown_edit_mode

        if self.markdown_edit_mode:
            # Switch to markdown edit mode
            markdown_scroll.display = False
            text_area.display = True
            text_area.focus()
        else:
            # Switch back to view mode, update markdown with edited content
            text_area.display = False
            markdown_scroll.display = True
            # Preserve line breaks in markdown (double space + newline)
            content_with_breaks = text_area.text.replace('\n', '  \n')
            markdown_viewer.update(content_with_breaks)

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
        # Note: note_id is None because the note doesn't exist yet (created on save)
        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.subject_id,
                subject_name=self.subject_name,
                note_id=None
            )
        )

        if result:
            # Save action to database
            self.db.add_action(result)

            # Insert action reference at cursor position
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            text_area.insert(action_ref, (cursor_row, cursor_col))

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


class NewAgendaDialog(ModalScreen[AgendaItem | None]):
    """Dialog for creating a new agenda item."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "save", "Create", show=True),
    ]

    CSS = """
    NewAgendaDialog {
        align: center middle;
    }

    #dialog-container {
        width: 95%;
        height: 90%;
        background: $surface;
        border: solid $primary;
        border-title-color: $accent;
        border-title-style: bold;
        border-subtitle-color: $text-muted;
        padding: 0 1 1 1;
    }

    #title-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    #metadata-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .metadata-field {
        width: 1fr;
        height: auto;
        padding-right: 2;
    }

    .metadata-field Label {
        color: $text-muted;
        margin: 0;
    }

    .metadata-field Input {
        margin: 0;
    }

    .metadata-field Select {
        margin: 0;
    }

    #content-section {
        width: 100%;
        height: 1fr;
        padding: 0 1 1 1;
    }

    #content-section Label {
        color: $text-muted;
        margin: 0;
    }

    #content-section TextArea {
        height: 1fr;
        min-height: 5;
    }
    """

    def __init__(self, subject_id: str, subject_name: str = ""):
        """Initialize dialog with subject ID.

        Args:
            subject_id: ID of the subject this agenda item belongs to
            subject_name: Name of the subject (for display in header)
        """
        super().__init__()
        self.subject_id = subject_id
        self.subject_name = subject_name

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        container = Container(id="dialog-container")
        container.border_title = "New Agenda Item"
        if self.subject_name:
            container.border_subtitle = self.subject_name
        with container:
            # Title row (full width)
            with Horizontal(id="title-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Title:")
                    yield Input(placeholder="Agenda item title", id="title-input")

            # Dense metadata row
            with Horizontal(id="metadata-row"):
                with Vertical(classes="metadata-field"):
                    yield Label("Priority (1-10):")
                    priority_options = [(str(i), i) for i in range(1, 11)]
                    yield Select(priority_options, value=5, id="priority-select")

            # Content area (description)
            with Vertical(id="content-section"):
                yield Label("Description (Markdown):")
                yield TextArea.code_editor("", language="markdown", theme="monokai", id="description-area")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the title input when dialog opens."""
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

    def action_cancel(self) -> None:
        """Cancel and close dialog."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Create agenda item and close dialog."""
        title_input = self.query_one("#title-input", Input)
        priority_select = self.query_one("#priority-select", Select)
        description_area = self.query_one("#description-area", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        priority = priority_select.value
        description = description_area.text.strip() or None

        agenda_item = AgendaItem(
            id=str(uuid.uuid4())[:8],
            subject_id=self.subject_id,
            title=title,
            description=description,
            priority=priority,
            status=AgendaStatus.ACTIVE,
            created_at=datetime.now(),
        )

        self.dismiss(agenda_item)


class ViewNoteDialog(BaseViewDialog):
    """Dialog for viewing and editing a note."""

    BINDINGS = BaseViewDialog.BINDINGS + [
        Binding("ctrl+a", "add_action_from_content", "Add Action", priority=True, show=True),
    ]

    CSS = f"ViewNoteDialog {{ {VIEW_DIALOG_CSS} }}"

    def __init__(self, note: Note, subject_name: str = "", db=None):
        """Initialize dialog with note to view/edit."""
        super().__init__()
        self.note = note
        self.subject_name = subject_name
        self.db = db

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        tags_str = ", ".join(self.note.tags) if self.note.tags else "-"

        container = Container(id="dialog-container")
        container.border_title = "Note"
        with container:
            with Horizontal(id="subject-info"):
                yield Label(f"Subject: ")
                yield Label(self.subject_name or "-", classes="value")

            metadata_section = Container(id="metadata-section")
            metadata_section.border_title = "Metadata"
            metadata_section.can_focus = True
            with metadata_section:
                with Vertical(id="metadata-display"):
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Label(self.note.title, classes="display-value", id="title-display")
                        with Vertical(classes="metadata-field"):
                            yield Label("Tags:")
                            yield Label(tags_str, classes="display-value", id="tags-display")

                edit_container = Vertical(id="metadata-edit")
                edit_container.display = False
                with edit_container:
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Input(value=self.note.title, id="title-input")
                        with Vertical(classes="metadata-field"):
                            yield Label("Tags:")
                            yield Input(value=", ".join(self.note.tags) if self.note.tags else "", id="tags-input")

            content_section = Container(id="content-section")
            content_section.border_title = "Content"
            content_section.can_focus = True
            with content_section:
                with VerticalScroll(id="markdown-scroll"):
                    content_with_breaks = self.note.content.replace('\n', '  \n')
                    yield Markdown(content_with_breaks, id="markdown-viewer")

                text_area = TextArea.code_editor(self.note.content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area
        yield Footer()

    def _toggle_metadata_edit(self) -> None:
        """Toggle metadata editing mode."""
        metadata_display = self.query_one("#metadata-display", Vertical)
        metadata_edit = self.query_one("#metadata-edit", Vertical)

        self.metadata_edit_mode = not self.metadata_edit_mode

        if self.metadata_edit_mode:
            metadata_display.display = False
            metadata_edit.display = True
            self.query_one("#title-input", Input).focus()
        else:
            self.query_one("#title-display", Label).update(self.query_one("#title-input", Input).value or "-")
            self.query_one("#tags-display", Label).update(self.query_one("#tags-input", Input).value or "-")

            metadata_edit.display = False
            metadata_display.display = True
            self.query_one("#metadata-section", Container).focus()

    @work
    async def action_add_action_from_content(self) -> None:
        """Add action from current content."""
        if not self.db:
            self.notify("Cannot create action: database not available", severity="error")
            return

        text_area = self.query_one("#content-editor", TextArea)
        cursor_row, cursor_col = text_area.cursor_location

        result = await self.app.push_screen_wait(
            NewActionDialog(
                subject_id=self.note.subject_id,
                subject_name=self.subject_name,
                note_id=self.note.id
            )
        )

        if result:
            self.db.add_action(result)
            action_ref = f"@action[{result.id}]{{{result.title}}}\n"
            text_area.insert(action_ref, (cursor_row, cursor_col))
            self.notify(f"Action '{result.title}' created and linked")

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        title_input = self.query_one("#title-input", Input)
        tags_input = self.query_one("#tags-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        tags_str = tags_input.value.strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        self.note.title = title
        self.note.tags = tags
        self.note.content = text_area.text
        self.note.updated_at = datetime.now()

        self.dismiss(self.note)


class ViewActionDialog(BaseViewDialog):
    """Dialog for viewing and editing an action."""

    CSS = f"ViewActionDialog {{ {VIEW_DIALOG_CSS} }}"
    EMPTY_CONTENT_PLACEHOLDER = "*No description*"

    def __init__(self, action: Action, subject_name: str = ""):
        """Initialize dialog with action to view/edit."""
        super().__init__()
        self.action = action
        self.subject_name = subject_name

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        content = self.action.description or ""
        due_date_str = self.action.due_date.strftime("%Y-%m-%d") if self.action.due_date else "-"
        status_display = {"todo": "TODO", "in_progress": "In Progress", "done": "Done"}.get(self.action.status.value, self.action.status.value)
        tags_str = ", ".join(self.action.tags) if self.action.tags else "-"

        container = Container(id="dialog-container")
        container.border_title = "Action"
        with container:
            with Horizontal(id="subject-info"):
                yield Label(f"Subject: ")
                yield Label(self.subject_name or "-", classes="value")

            metadata_section = Container(id="metadata-section")
            metadata_section.border_title = "Metadata"
            metadata_section.can_focus = True
            with metadata_section:
                with Vertical(id="metadata-display"):
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Label(self.action.title, classes="display-value", id="title-display")
                        with Vertical(classes="metadata-field"):
                            yield Label("Due Date:")
                            yield Label(due_date_str, classes="display-value", id="due-display")
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Status:")
                            yield Label(status_display, classes="display-value", id="status-display")
                        with Vertical(classes="metadata-field"):
                            yield Label("Tags:")
                            yield Label(tags_str, classes="display-value", id="tags-display")

                edit_container = Vertical(id="metadata-edit")
                edit_container.display = False
                with edit_container:
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Input(value=self.action.title, id="title-input")
                        with Vertical(classes="metadata-field"):
                            yield Label("Due Date:")
                            due_input_str = self.action.due_date.strftime("%Y-%m-%d") if self.action.due_date else ""
                            yield Input(value=due_input_str, placeholder="YYYY-MM-DD", id="due-date-input")
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Status:")
                            yield Select(
                                [("TODO", "todo"), ("In Progress", "in_progress"), ("Done", "done")],
                                value=self.action.status.value,
                                id="status-select"
                            )
                        with Vertical(classes="metadata-field"):
                            yield Label("Tags:")
                            yield Input(value=", ".join(self.action.tags), id="tags-input")

            content_section = Container(id="content-section")
            content_section.border_title = "Description"
            content_section.can_focus = True
            with content_section:
                with VerticalScroll(id="markdown-scroll"):
                    display_content = content or "*No description*"
                    content_with_breaks = display_content.replace('\n', '  \n')
                    yield Markdown(content_with_breaks, id="markdown-viewer")

                text_area = TextArea.code_editor(content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area
        yield Footer()

    def _toggle_metadata_edit(self) -> None:
        """Toggle metadata editing mode."""
        metadata_display = self.query_one("#metadata-display", Vertical)
        metadata_edit = self.query_one("#metadata-edit", Vertical)

        self.metadata_edit_mode = not self.metadata_edit_mode

        if self.metadata_edit_mode:
            metadata_display.display = False
            metadata_edit.display = True
            self.query_one("#title-input", Input).focus()
        else:
            self.query_one("#title-display", Label).update(self.query_one("#title-input", Input).value or "-")
            self.query_one("#due-display", Label).update(self.query_one("#due-date-input", Input).value or "-")
            status_select = self.query_one("#status-select", Select)
            status_display = {"todo": "TODO", "in_progress": "In Progress", "done": "Done"}.get(status_select.value, status_select.value)
            self.query_one("#status-display", Label).update(status_display)
            self.query_one("#tags-display", Label).update(self.query_one("#tags-input", Input).value or "-")

            metadata_edit.display = False
            metadata_display.display = True
            self.query_one("#metadata-section", Container).focus()

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        title_input = self.query_one("#title-input", Input)
        due_date_input = self.query_one("#due-date-input", Input)
        status_select = self.query_one("#status-select", Select)
        tags_input = self.query_one("#tags-input", Input)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        due_date = None
        if due_date_input.value.strip():
            try:
                due_date = datetime.fromisoformat(due_date_input.value.strip())
            except ValueError:
                self.notify("Invalid date format. Use YYYY-MM-DD", severity="error")
                return

        tags_str = tags_input.value.strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        old_status = self.action.status
        new_status = ActionStatus(status_select.value)

        self.action.title = title
        self.action.due_date = due_date
        self.action.status = new_status
        self.action.tags = tags
        self.action.description = text_area.text if text_area.text.strip() else None

        if old_status != ActionStatus.DONE and new_status == ActionStatus.DONE:
            self.action.completed_at = datetime.now()
        elif old_status == ActionStatus.DONE and new_status != ActionStatus.DONE:
            self.action.completed_at = None

        self.dismiss(self.action)


class ViewAgendaDialog(BaseViewDialog):
    """Dialog for viewing and editing an agenda item."""

    CSS = f"ViewAgendaDialog {{ {VIEW_DIALOG_CSS} }}"
    EMPTY_CONTENT_PLACEHOLDER = "*No description*"

    def __init__(self, agenda_item: AgendaItem, subject_name: str = ""):
        """Initialize dialog with agenda item to view/edit."""
        super().__init__()
        self.agenda_item = agenda_item
        self.subject_name = subject_name

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        content = self.agenda_item.description or ""
        status_display = {"active": "Active", "discussed": "Discussed", "archived": "Archived"}.get(self.agenda_item.status.value, self.agenda_item.status.value)

        container = Container(id="dialog-container")
        container.border_title = "Agenda Item"
        with container:
            with Horizontal(id="subject-info"):
                yield Label(f"Subject: ")
                yield Label(self.subject_name or "-", classes="value")

            metadata_section = Container(id="metadata-section")
            metadata_section.border_title = "Metadata"
            metadata_section.can_focus = True
            with metadata_section:
                with Vertical(id="metadata-display"):
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Label(self.agenda_item.title, classes="display-value", id="title-display")
                        with Vertical(classes="metadata-field"):
                            yield Label("Priority:")
                            yield Label(str(self.agenda_item.priority), classes="display-value", id="priority-display")
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Status:")
                            yield Label(status_display, classes="display-value", id="status-display")

                edit_container = Vertical(id="metadata-edit")
                edit_container.display = False
                with edit_container:
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Title:")
                            yield Input(value=self.agenda_item.title, id="title-input")
                        with Vertical(classes="metadata-field"):
                            yield Label("Priority (1-10):")
                            priority_options = [(str(i), i) for i in range(1, 11)]
                            yield Select(priority_options, value=self.agenda_item.priority, id="priority-select")
                    with Horizontal(classes="metadata-row"):
                        with Vertical(classes="metadata-field"):
                            yield Label("Status:")
                            yield Select(
                                [("Active", "active"), ("Discussed", "discussed"), ("Archived", "archived")],
                                value=self.agenda_item.status.value,
                                id="status-select"
                            )

            content_section = Container(id="content-section")
            content_section.border_title = "Description"
            content_section.can_focus = True
            with content_section:
                with VerticalScroll(id="markdown-scroll"):
                    display_content = content or "*No description*"
                    content_with_breaks = display_content.replace('\n', '  \n')
                    yield Markdown(content_with_breaks, id="markdown-viewer")

                text_area = TextArea.code_editor(content, language="markdown", theme="monokai", id="content-editor")
                text_area.display = False
                yield text_area
        yield Footer()

    def _toggle_metadata_edit(self) -> None:
        """Toggle metadata editing mode."""
        metadata_display = self.query_one("#metadata-display", Vertical)
        metadata_edit = self.query_one("#metadata-edit", Vertical)

        self.metadata_edit_mode = not self.metadata_edit_mode

        if self.metadata_edit_mode:
            metadata_display.display = False
            metadata_edit.display = True
            self.query_one("#title-input", Input).focus()
        else:
            self.query_one("#title-display", Label).update(self.query_one("#title-input", Input).value or "-")
            priority_select = self.query_one("#priority-select", Select)
            self.query_one("#priority-display", Label).update(str(priority_select.value) if priority_select.value else "-")
            status_select = self.query_one("#status-select", Select)
            status_display = {"active": "Active", "discussed": "Discussed", "archived": "Archived"}.get(status_select.value, status_select.value)
            self.query_one("#status-display", Label).update(status_display)

            metadata_edit.display = False
            metadata_display.display = True
            self.query_one("#metadata-section", Container).focus()

    def action_save(self) -> None:
        """Save changes and close the dialog."""
        title_input = self.query_one("#title-input", Input)
        priority_select = self.query_one("#priority-select", Select)
        status_select = self.query_one("#status-select", Select)
        text_area = self.query_one("#content-editor", TextArea)

        title = title_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        old_status = self.agenda_item.status
        new_status = AgendaStatus(status_select.value)

        self.agenda_item.title = title
        self.agenda_item.priority = priority_select.value
        self.agenda_item.status = new_status
        self.agenda_item.description = text_area.text if text_area.text.strip() else None

        if old_status != AgendaStatus.DISCUSSED and new_status == AgendaStatus.DISCUSSED:
            self.agenda_item.discussed_at = datetime.now()

        self.dismiss(self.agenda_item)
