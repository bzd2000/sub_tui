# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SubTUI is a Terminal User Interface application for managing subjects (boards, projects, teams, people) with agendas, meeting minutes, actions, and knowledge notes. Built with Textual framework.

**Textual Documentation**: https://textual.textualize.io/ - Refer to this for widget APIs, CSS styling, event handling, and screen management patterns.

## Project Structure

```
sub_tui/
├── __init__.py
├── __main__.py          # Entry point (python -m sub_tui)
├── app.py               # Main App class only (minimal)
├── models.py            # Data models (dataclasses)
├── database.py          # Database operations (CRUD + FTS)
├── screens/             # Screen definitions
│   ├── __init__.py
│   └── actions.py       # ActionsDashboard
└── widgets/             # Reusable widgets
    ├── __init__.py
    └── dialogs.py       # Modal dialogs for CRUD operations
```

**Modular Design**: Each screen in its own file for better organization and scalability.

## Development Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Run application
python3 -m sub_tui

# Test the app manually
python3 create_test_data.py  # Creates sample data for testing
```

## Architecture

### Database-First Architecture

1. **Data Models** (`sub_tui/models.py`)
   - Pure dataclasses: `Subject`, `Action`, `AgendaItem`, `Note`, `Meeting`
   - Enums: `SubjectType`, `ActionStatus`, `AgendaStatus`, `RecurrencePattern`
   - No business logic, only data structure and serialization methods

2. **Persistence Layer** (`sub_tui/database.py`)
   - **SQLite database is the source of truth** for all application data
   - Full CRUD operations for all entities via Database class methods
   - Unified full-text search (FTS5) across all content types
   - Automatic FTS indexing via triggers when data changes
   - Markdown content stored directly in database (notes, meetings)
   - Database location: `data/index.db`

3. **UI Layer** (modular structure)
   - **`sub_tui/app.py`**: Main `SubTUIApp` class only (minimal)
   - **`sub_tui/screens/`**: Screen definitions (one file per screen/feature area)
     - `actions.py`: ActionsDashboard
     - Future: `subjects.py`, `meetings.py`, `notes.py`, `agenda.py`
   - **`sub_tui/widgets/`**: Reusable components
     - `dialogs.py`: Modal dialogs (NewSubjectDialog, ViewActionDialog, etc.)
   - Package is executable via `python3 -m sub_tui`

### Key Design Patterns

**Database-First**: Database is the single source of truth. All CRUD operations go through `Database` class methods which automatically handle FTS indexing via SQL triggers.

**Unified FTS**: Single `unified_fts` table indexes all searchable content (subjects, agenda items, meetings, actions, notes) for fast cross-content search.

**Automatic Indexing**: FTS indices are maintained automatically via SQL triggers. No manual reindexing needed.

**Screen Management**: Textual uses screen stack. Screens pushed/popped with `push_screen()` / `pop_screen()`. Modal dialogs use `push_screen_wait()` for return values.

**ListItem Pattern**: Custom `ListItem` subclasses must create widgets in `__init__` and yield them in `compose()`. Do NOT create widgets directly in `compose()` - this causes crashes.

## Critical Implementation Details

### Worker Decorator for Async Actions

**CRITICAL**: Any action method that calls `push_screen_wait()` MUST use the `@work` decorator.

```python
from textual import work

@work
async def action_new_subject(self) -> None:
    result = await self.push_screen_wait(NewSubjectDialog())
    # ... handle result
```

**Important**:
- Import from `textual`, NOT `textual.worker`
- The `@work` decorator automatically runs the method in a worker context
- Without `@work`, you'll get: `NoActiveWorker: push_screen must be run from a worker when wait_for_dismiss is True`
- **UI updates from workers MUST use `app.call_from_thread()` or `self.call_from_thread()`**
  ```python
  @work
  async def action_add_item(self):
      result = await self.app.push_screen_wait(DialogScreen())
      if result:
          self.manager.add_item(result)
          # ✓ Correct - schedule UI refresh on main thread
          self.app.call_from_thread(self.refresh_data)
          # ✗ Wrong - calling directly may not update UI
          # self.refresh_data()
  ```
- See [Textual Workers Guide](https://textual.textualize.io/guide/workers/) for more details

### ListItem Widget Construction

See [Textual ListView docs](https://textual.textualize.io/widgets/list_view/) for official patterns.

**WRONG** (causes crashes):
```python
def compose(self):
    yield Label("text")  # Created on each compose call
```

**CORRECT**:
```python
def __init__(self, text: str):
    super().__init__()
    self._label = Label(text)  # Created once in __init__

def compose(self):
    yield self._label  # Just yield existing widget
```

### Database Schema

**Main Tables:**
- `subjects` - Subject metadata (id, name, code, type, description, timestamps)
- `agenda_items` - Agenda items with priority, status, recurrence settings
- `meetings` - Meeting records with date, attendees, markdown content
- `actions` - Task items with due dates, status, tags
- `notes` - Knowledge notes with markdown content and tags

**Full-Text Search:**
- `unified_fts` - FTS5 virtual table indexing all searchable content
  - Columns: content_type, content_id, subject_id, subject_name, title, searchable_text
  - Automatically maintained via SQL triggers on INSERT/UPDATE/DELETE
  - Search with `db.search(query, content_types=['note', 'meeting'])`

**CRUD Operations:**
All entities have standard CRUD methods in Database class:
- `db.add_<entity>(obj)` - Create new
- `db.get_<entity>(id)` or `db.get_<entities>(subject_id)` - Read
- `db.update_<entity>(obj)` - Update existing
- `db.delete_<entity>(id)` - Delete

**Important**: FTS indexing happens automatically via triggers. No manual reindexing required.

## Common Development Patterns

### Adding New Content Type

1. **Model**: Add to `sub_tui/models.py` as dataclass with `to_dict()` and `from_dict()` methods
2. **Database Schema**: Add table in `sub_tui/database.py` `_init_db()` method
3. **FTS Indexing**: Add FTS triggers for the new table to `unified_fts`
4. **CRUD Methods**: Add to `Database` class (`add_*`, `get_*`, `update_*`, `delete_*`)
5. **UI Screen**: Create new file in `sub_tui/screens/` (e.g., `meetings.py`)
6. **UI Widgets**: If needed, create dialogs in `sub_tui/widgets/dialogs.py`
7. **Exports**: Update `sub_tui/screens/__init__.py` to export new screens
8. **Integration**: Import and use in `app.py` or link from other screens

### Testing Changes

Testing is done manually with test data:
1. Delete existing database: `rm data/index.db`
2. Run `python3 create_test_data.py` to create fresh test data
3. Run `python3 -m sub_tui` to test the application
4. Use `db.search(query)` to test unified full-text search

### Date Handling

**Storage Format**: All dates stored as ISO 8601 strings (YYYY-MM-DDTHH:MM:SS.ffffff)

**Action Due Date Queries** (`database.py:get_actions_by_timeframe()`):
- `"today"` - Due date between today 00:00 and tomorrow 00:00
- `"week"` - Due date between today and 7 days from now
- `"next_week"` - Due date between 7 days and 14 days from now
- `"all"` - All actions regardless of due date (filtered by status)

**Display Formatting**: Due dates shown as YYYY-MM-DD in the UI, with overdue dates highlighted in red.

## Data Directory

The `data/` directory is created at runtime and contains all user data:
- `data/index.db` - SQLite database (source of truth for all application data)

The database file is in `.gitignore` - this is intentional.

**Backup Strategy** (to be implemented):
- JSON dump: Export all data to `data/backup.json`
- Markdown export: Export meetings and notes to markdown files for readability

## Current Implementation Status

The application is in early development. Current functionality:
- Actions dashboard with filtering (today, week, next week, all)
- Database-first storage with full CRUD operations
- Unified full-text search across all content types
- Automatic FTS indexing via SQL triggers
- Complete data models for all entities

**Key Bindings (Actions Dashboard):**
- `1` - Filter to today's actions
- `2` - Filter to this week's actions
- `3` - Filter to next week's actions
- `a` - Show all active actions
- `t` - Toggle showing archived actions
- `x` - Add new action (not yet implemented)
- `ctrl+p` or `/` - Subject lookup (not yet implemented)
- `q` - Quit application

**Not yet implemented:**
- Adding/editing actions through UI (data must be created via test scripts)
- Subject detail screens
- Agenda items management
- Meetings/minutes recording
- Notes management
- Subject lookup/search

When implementing new features, refer to REQUIREMENTS.md for full functional requirements.
