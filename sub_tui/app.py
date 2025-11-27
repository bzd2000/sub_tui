"""Main TUI application."""

from textual.app import App

from .database import Database
from .screens import MainDashboard


class SubTUIApp(App):
    """SubTUI application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    #actions-section {
        width: 100%;
        height: 1fr;
        padding: 0 1 1 1;
        border: solid $primary;
        border-title-color: $text-muted;
        border-title-style: bold;
        background: $surface;
    }

    #actions-section:focus-within {
        border: solid $accent;
        border-title-color: $accent;
    }

    #actions-table {
        width: 100%;
        height: 1fr;
    }

    #subjects-grid {
        width: 100%;
        height: 1fr;
        grid-size: 2 2;
        grid-gutter: 0;
    }

    .subject-card {
        width: 100%;
        height: 100%;
        padding: 0 1 1 1;
        border: solid $primary;
        border-title-color: $text-muted;
        border-title-style: bold;
        background: $surface;
    }

    .subject-card:focus-within {
        border: solid $accent;
        border-title-color: $accent;
    }

    .subject-table {
        width: 100%;
        height: 1fr;
    }

    DataTable {
        height: 100%;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: $boost;
    }

    DataTable > .datatable--cursor {
        background: $accent 20%;
    }
    """

    def __init__(self):
        """Initialize app."""
        super().__init__()
        self.db = Database()

    def on_mount(self) -> None:
        """Handle mount event."""
        # Show main dashboard
        self.push_screen(MainDashboard(self.db))

    def on_unmount(self) -> None:
        """Handle unmount event."""
        self.db.close()


def main():
    """Run the application."""
    app = SubTUIApp()
    app.run()


if __name__ == "__main__":
    main()
