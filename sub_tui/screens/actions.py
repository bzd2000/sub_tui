"""Main dashboard screen."""

from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Grid
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from ..database import Database
from ..widgets import NewActionDialog


class MainDashboard(Screen):
    """Main dashboard showing actions across all subjects."""

    BINDINGS = [
        Binding("1", "filter_today", "Today", priority=True),
        Binding("2", "filter_week", "This Week", priority=True),
        Binding("3", "filter_next_week", "Next Week", priority=True),
        Binding("a", "filter_all", "All Active", priority=True),
        Binding("t", "toggle_archived", "Toggle Archived"),
        Binding("x", "add_action", "New Action"),
        Binding("space", "toggle_action_status", "Toggle Status"),
        Binding("d", "delete_action", "Delete"),
        Binding("ctrl+p", "subject_lookup", "Find Subject"),
        Binding("/", "subject_lookup", "Find Subject"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, db: Database):
        """Initialize actions dashboard."""
        super().__init__()
        self.db = db
        self.current_filter = "today"
        self.show_archived = False
        self.action_ids: list[str] = []  # Maps table rows to action IDs
        self.project_ids: list[str] = []  # Maps table rows to project IDs
        self.board_ids: list[str] = []  # Maps table rows to board IDs
        self.team_ids: list[str] = []  # Maps table rows to team IDs
        self.person_ids: list[str] = []  # Maps table rows to person IDs

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()

        with Container(id="main-container"):
            yield Static("Main Dashboard", id="title")

            # Filter tabs
            with Horizontal(id="filter-tabs"):
                yield Label("1:Today  2:Week  3:Next  A:All  T:Archive", id="filter-label")

            # Actions table (full width, top half)
            with Container(id="actions-section"):
                yield Label("Actions", id="actions-header")
                table = DataTable(id="actions-table")
                table.add_columns("Subject", "Title", "Due", "Status")
                table.cursor_type = "row"
                yield table

            # Subjects grid (2x2, bottom half)
            with Grid(id="subjects-grid"):
                # Projects
                with Container(classes="subject-card"):
                    yield Label("Projects", classes="subject-card-header")
                    projects_table = DataTable(id="projects-table", classes="subject-table")
                    projects_table.add_columns("Name", "Actions")
                    projects_table.cursor_type = "row"
                    yield projects_table

                # Boards
                with Container(classes="subject-card"):
                    yield Label("Boards", classes="subject-card-header")
                    boards_table = DataTable(id="boards-table", classes="subject-table")
                    boards_table.add_columns("Name", "Actions")
                    boards_table.cursor_type = "row"
                    yield boards_table

                # Teams
                with Container(classes="subject-card"):
                    yield Label("Teams", classes="subject-card-header")
                    teams_table = DataTable(id="teams-table", classes="subject-table")
                    teams_table.add_columns("Name", "Actions")
                    teams_table.cursor_type = "row"
                    yield teams_table

                # People
                with Container(classes="subject-card"):
                    yield Label("People", classes="subject-card-header")
                    people_table = DataTable(id="people-table", classes="subject-table")
                    people_table.add_columns("Name", "Actions")
                    people_table.cursor_type = "row"
                    yield people_table

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self.refresh_actions()
        self.refresh_subjects()

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection (Enter key on a row)."""
        table_id = event.data_table.id

        if table_id == "actions-table":
            # Open the subject detail screen for this action
            self.action_open_subject()
        elif table_id == "projects-table":
            self.open_subject_from_table(self.project_ids, event.cursor_row)
        elif table_id == "boards-table":
            self.open_subject_from_table(self.board_ids, event.cursor_row)
        elif table_id == "teams-table":
            self.open_subject_from_table(self.team_ids, event.cursor_row)
        elif table_id == "people-table":
            self.open_subject_from_table(self.person_ids, event.cursor_row)

    def refresh_actions(self) -> None:
        """Refresh the actions list."""
        table = self.query_one("#actions-table", DataTable)
        table.clear()
        self.action_ids = []  # Reset ID mapping

        actions = self.db.get_actions_by_timeframe(
            self.current_filter,
            include_archived=self.show_archived
        )

        now = datetime.now()

        for action in actions:
            subject_name = action.get("subject_name", "Unknown")
            title = action["title"]
            due = action.get("due_date", "")
            status = action["status"]
            action_id = action["id"]

            # Store action ID for this row
            self.action_ids.append(action_id)

            # Format due date
            if due:
                due_dt = datetime.fromisoformat(due)
                due_str = due_dt.strftime("%Y-%m-%d")

                # Highlight overdue
                if due_dt.date() < now.date() and status != "done":
                    due_str = f"[red]{due_str}[/red]"
            else:
                due_str = "-"

            # Format status
            status_map = {
                "todo": "[dim]TODO[/dim]",
                "in_progress": "[yellow]IN PROGRESS[/yellow]",
                "done": "[green]DONE[/green]"
            }
            status_str = status_map.get(status, status)

            table.add_row(subject_name, title, due_str, status_str)

    def action_filter_today(self) -> None:
        """Filter to today's actions."""
        self.current_filter = "today"
        self.refresh_actions()

    def action_filter_week(self) -> None:
        """Filter to this week's actions."""
        self.current_filter = "week"
        self.refresh_actions()

    def action_filter_next_week(self) -> None:
        """Filter to next week's actions."""
        self.current_filter = "next_week"
        self.refresh_actions()

    def action_filter_all(self) -> None:
        """Show all active actions."""
        self.current_filter = "all"
        self.refresh_actions()

    def action_toggle_archived(self) -> None:
        """Toggle showing archived actions."""
        self.show_archived = not self.show_archived
        self.refresh_actions()

    @work
    async def action_add_action(self) -> None:
        """Add new action."""
        # Get all subjects for the dialog
        subjects = self.db.get_all_subjects()
        if not subjects:
            self.notify("No subjects found. Create a subject first.", severity="warning")
            return

        # Show dialog and wait for result
        result = await self.app.push_screen_wait(NewActionDialog(subjects))

        if result:
            # Add to database
            self.db.add_action(result)
            # Refresh the UI (already on main thread after await)
            self.refresh_actions()
            self.notify(f"Action '{result.title}' created successfully")

    def action_toggle_action_status(self) -> None:
        """Toggle status of selected action (TODO → IN_PROGRESS → DONE → TODO)."""
        table = self.query_one("#actions-table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self.action_ids):
            return

        action_id = self.action_ids[table.cursor_row]
        action = self.db.get_action(action_id)
        if not action:
            return

        # Cycle through statuses
        from ..models import ActionStatus
        if action.status == ActionStatus.TODO:
            action.status = ActionStatus.IN_PROGRESS
        elif action.status == ActionStatus.IN_PROGRESS:
            action.status = ActionStatus.DONE
            action.completed_at = datetime.now()
        else:  # DONE
            action.status = ActionStatus.TODO
            action.completed_at = None

        self.db.update_action(action)
        self.refresh_actions()
        self.notify(f"Action status: {action.status.value}")

    def action_delete_action(self) -> None:
        """Delete selected action."""
        table = self.query_one("#actions-table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self.action_ids):
            return

        action_id = self.action_ids[table.cursor_row]
        action = self.db.get_action(action_id)
        if not action:
            return

        self.db.delete_action(action_id)
        self.refresh_actions()
        self.notify(f"Deleted action: {action.title}")

    def action_open_subject(self) -> None:
        """Open subject detail view for the selected action."""
        table = self.query_one("#actions-table", DataTable)

        if table.cursor_row is None:
            self.notify("No action selected", severity="warning")
            return

        if table.cursor_row >= len(self.action_ids):
            self.notify("Invalid action selected", severity="error")
            return

        action_id = self.action_ids[table.cursor_row]
        action = self.db.get_action(action_id)
        if not action:
            self.notify("Action not found", severity="error")
            return

        # Import here to avoid circular dependency
        from .subjects import SubjectDetailScreen

        # Push subject detail screen with selected action
        self.app.push_screen(SubjectDetailScreen(self.db, action.subject_id, selected_action_id=action_id))

    def action_subject_lookup(self) -> None:
        """Open subject lookup."""
        # TODO: Show subject lookup screen
        pass

    def open_subject_from_table(self, subject_ids: list[str], row_index: int) -> None:
        """Open subject detail screen from a subject table."""
        if row_index is None or row_index >= len(subject_ids):
            return

        subject_id = subject_ids[row_index]
        # Import here to avoid circular dependency
        from .subjects import SubjectDetailScreen
        self.app.push_screen(SubjectDetailScreen(self.db, subject_id))

    def refresh_subjects(self) -> None:
        """Refresh the subjects tables."""
        from ..models import SubjectType

        # Get all subjects
        all_subjects = self.db.get_all_subjects()

        # Group by type
        projects = [s for s in all_subjects if s.type == SubjectType.PROJECT]
        boards = [s for s in all_subjects if s.type == SubjectType.BOARD]
        teams = [s for s in all_subjects if s.type == SubjectType.TEAM]
        people = [s for s in all_subjects if s.type == SubjectType.PERSON]

        # Update projects table
        projects_table = self.query_one("#projects-table", DataTable)
        projects_table.clear()
        self.project_ids = []
        for subject in projects:
            self.project_ids.append(subject.id)
            action_count = len(self.db.get_actions(subject.id))
            projects_table.add_row(subject.name, str(action_count))

        # Update boards table
        boards_table = self.query_one("#boards-table", DataTable)
        boards_table.clear()
        self.board_ids = []
        for subject in boards:
            self.board_ids.append(subject.id)
            action_count = len(self.db.get_actions(subject.id))
            boards_table.add_row(subject.name, str(action_count))

        # Update teams table
        teams_table = self.query_one("#teams-table", DataTable)
        teams_table.clear()
        self.team_ids = []
        for subject in teams:
            self.team_ids.append(subject.id)
            action_count = len(self.db.get_actions(subject.id))
            teams_table.add_row(subject.name, str(action_count))

        # Update people table
        people_table = self.query_one("#people-table", DataTable)
        people_table.clear()
        self.person_ids = []
        for subject in people:
            self.person_ids.append(subject.id)
            action_count = len(self.db.get_actions(subject.id))
            people_table.add_row(subject.name, str(action_count))
