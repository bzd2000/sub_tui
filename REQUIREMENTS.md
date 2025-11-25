# SubTUI - Functional Requirements

## Overview
A Terminal User Interface (TUI) application for managing subjects (boards, projects, teams, people) with agendas, meeting minutes, actions, and knowledge notes. Content stored in markdown/YAML files with SQLite indexing for fast queries.

---

## 1. Core Entities

### 1.1 Subject
A subject represents a context for organizing information.

**Types:**
- Board
- Project
- Team
- Person

**Attributes:**
- Unique identifier
- Name
- Code (optional - e.g., project code, team code)
- Type (board/project/team/person)
- Description (optional)
- Created timestamp
- Last reviewed timestamp

**Requirements:**
- FR-1.1: User can create a new subject with name, type, optional code, and optional description
- FR-1.2: User can view list of all subjects
- FR-1.3: User can filter subjects by type
- FR-1.4: User can search subjects by name, code, or description
- FR-1.5: System tracks last review timestamp automatically
- FR-1.6: Subject code displayed alongside name in lists (if present)

---

### 1.2 Agenda Items
Things to discuss in the next encounter with a subject.

**Attributes:**
- Unique identifier
- Associated subject
- Title
- Description (optional)
- Priority (1-10)
- Status (active/discussed/archived)
- Created timestamp
- Discussed timestamp (when marked as discussed)
- Is recurring (boolean)
- Recurrence pattern (weekly/monthly/quarterly) if recurring

**Requirements:**
- FR-2.1: User can add agenda item to a subject with title and priority
- FR-2.2: User can edit agenda item title, description, and priority
- FR-2.3: User can mark agenda item as "discussed"
- FR-2.4: When marked as discussed, agenda item disappears from active view
- FR-2.5: User can toggle view to show archived agenda items
- FR-2.6: User can create recurring agenda items
- FR-2.7: When recurring item marked as discussed, system creates new instance for next occurrence
- FR-2.8: Agenda items displayed sorted by priority (highest first)

---

### 1.3 Meetings
Records of encounters with a subject.

**Attributes:**
- Unique identifier
- Associated subject
- Date/time
- Attendees (list of names)
- Content (markdown document)

**Content Structure:**
Meeting minutes are free-form markdown with embedded structure:
```markdown
# Meeting - [Date]

**Attendees**: [names]

## My Agenda Items

### [Agenda Item Title]
- Discussion notes
- **Decision**: [decision text]
- **Action**: [action created]

## Topics Raised by Others

### [Topic Title] (raised by [person])
- Discussion notes
- **Decision**: [decision text]
- **Action**: [action created]
```

**Requirements:**
- FR-3.1: User can create a meeting for a subject with date and attendees
- FR-3.2: User can edit meeting minutes in markdown format
- FR-3.3: Editor supports toggle between edit mode (markdown syntax) and preview mode (rendered)
- FR-3.4: User can reference agenda items in meeting minutes
- FR-3.5: User can add ad-hoc topics not from agenda
- FR-3.6: User can create actions directly from meeting minutes
- FR-3.7: Meeting minutes stored as markdown files on disk
- FR-3.8: User can view list of meetings for a subject, sorted by date (newest first)

---

### 1.4 Actions
Personal tasks related to subjects.

**Attributes:**
- Unique identifier
- Associated subject
- Title
- Description (optional)
- Status (todo/in_progress/done)
- Due date (optional)
- Created timestamp
- Completed timestamp (when marked done)
- Archived timestamp (auto-set to completed_at + 7 days)
- Meeting reference (optional - if created during meeting)
- Agenda item reference (optional - if originated from agenda item)
- Tags (list of strings)

**Requirements:**
- FR-4.1: User can create action with title, optional due date, description, and tags
- FR-4.2: User can edit action details
- FR-4.3: User can change action status (todo/in_progress/done)
- FR-4.4: Actions can be linked to subject, meeting, and/or agenda item
- FR-4.5: All actions are personal (no assignment to others)
- FR-4.6: Completed actions remain visible for 7 days
- FR-4.7: After 7 days, completed actions auto-archive
- FR-4.8: User can toggle view to show archived actions
- FR-4.9: User can view actions by timeframe:
  - Today (due today)
  - This week (due within 7 days)
  - Next week (due 8-14 days from now)
- FR-4.10: User can view all actions for a specific subject

---

### 1.5 Knowledge Notes
Reference information and documentation.

**Attributes:**
- Unique identifier
- Associated subject
- Title
- Content (markdown)
- Tags (list of strings)
- Created timestamp
- Updated timestamp

**Requirements:**
- FR-5.1: User can create note with title and markdown content
- FR-5.2: User can edit note title and content
- FR-5.3: Editor supports toggle between edit mode and preview mode
- FR-5.4: User can add tags to notes
- FR-5.5: User can search notes by title, content, or tags
- FR-5.6: Notes stored as markdown files on disk
- FR-5.7: User can view list of notes for a subject

---

## 2. Data Storage

### 2.1 File Structure

**Primary Storage: Markdown/YAML Files**

```
data/
├── index.db                      # SQLite index (cache)
└── subjects/
    └── [subject_name]/
        ├── subject.yaml          # Subject metadata
        ├── agenda.yaml           # List of agenda items
        ├── meetings/
        │   └── [YYYY-MM-DD].md   # Meeting minutes
        ├── actions/
        │   └── [action_id].yaml  # Action details
        └── notes/
            └── [note_id].md      # Knowledge notes
```

**Requirements:**
- FR-6.1: All content stored in human-readable files (markdown/YAML)
- FR-6.2: Files are the source of truth
- FR-6.3: SQLite database is index/cache only (can be rebuilt)
- FR-6.4: Subject folder name derived from subject name (lowercase, spaces→underscores)
- FR-6.5: Files can be version controlled with git
- FR-6.6: Files can be searched with external tools (grep, ripgrep)

### 2.2 SQLite Index

**Purpose:** Fast queries, filtering, and full-text search

**Tables:**
- subjects (id, name, type, description, created_at, last_reviewed_at)
- agenda_items (id, subject_id, title, status, priority, is_recurring, ...)
- meetings (id, subject_id, date, attendees)
- actions (id, subject_id, title, status, due_date, archived, ...)
- notes (id, subject_id, title, tags, ...)
- Full-text search indexes

**Requirements:**
- FR-6.7: Index rebuilds automatically on app startup if files modified
- FR-6.8: User can manually trigger index rebuild with keyboard command
- FR-6.9: When app writes data, both file and index updated atomically
- FR-6.10: Index tracks file modification times for sync detection

---

## 3. User Interface

### 3.1 Main Screen - Actions Dashboard

**Display:**
- Primary view showing actions across all subjects
- Tabs for: Today / This Week / Next Week / All Active
- Each action shows: subject name, title, due date, status
- Quick lookup bar for finding subjects
- Status bar showing key bindings

**Actions:**
- `1` - Show today's actions
- `2` - Show this week
- `3` - Show next week
- `a` - Show all active
- `t` - Toggle archived
- `Ctrl+P` or `/` - Quick subject lookup (command palette)
- `Enter` - Edit selected action
- `Space` - Toggle action status (todo→in_progress→done)
- `x` - Create new action
- `r` - Rebuild index
- `q` - Quit application

**Requirements:**
- FR-7.1: App starts directly on Actions Dashboard
- FR-7.2: Actions sorted by due date within each tab
- FR-7.3: Overdue actions highlighted
- FR-7.4: Quick subject lookup accessible via Ctrl+P or /
- FR-7.5: Keyboard navigation (up/down arrows)

### 3.2 Subject Detail Screen

**Display:**
Accessed via quick lookup from Actions Dashboard.
Tabbed interface with sections:
- Agenda (active items, toggle for archived)
- Meetings (chronological list)
- Actions (active items, toggle for archived)
- Notes (list with tags)

**Actions:**
- `a` - Add agenda item
- `m` - Add meeting
- `x` - Add action
- `n` - Add note
- `t` - Toggle show archived
- `Enter` - Open selected item
- `Escape` - Back to Actions Dashboard

**Requirements:**
- FR-7.6: Subject loaded via quick lookup (Ctrl+P or /) from Actions Dashboard
- FR-7.7: Tabs switch with Tab/Shift+Tab or number keys (1-4)
- FR-7.8: Each tab shows relevant keyboard shortcuts
- FR-7.9: Agenda items sorted by priority
- FR-7.10: Meetings sorted by date (newest first)
- FR-7.11: Actions sorted by due date
- FR-7.12: Archive toggle persists per session

### 3.3 Markdown Editor

**Display:**
Toggle between two modes:
1. **Edit Mode**: TextArea with markdown syntax highlighting
2. **Preview Mode**: MarkdownViewer with rendered output

**Actions:**
- `Tab` - Toggle between edit and preview mode
- `Ctrl+S` - Save and close
- `Ctrl+Q` or `Escape` - Close without saving (confirm if changes)

**Requirements:**
- FR-7.13: Editor loads existing content or starts blank
- FR-7.14: Syntax highlighting for markdown in edit mode
- FR-7.15: Proper rendering in preview mode (headers, lists, bold, italic, links)
- FR-7.16: Modal shows current mode (Edit/Preview)
- FR-7.17: Unsaved changes warning on exit

### 3.4 Quick Subject Lookup

**Display:**
Command palette style overlay for finding subjects quickly.
- Fuzzy search through subject names, codes, descriptions
- Shows matching subjects with type indicators
- Real-time filtering as user types

**Actions:**
- Type to filter subjects
- `Up/Down` - Navigate results
- `Enter` - Load selected subject
- `Escape` - Cancel and return to previous screen

**Requirements:**
- FR-7.18: Accessible from any screen via Ctrl+P or /
- FR-7.19: Fuzzy matching on name, code, and description
- FR-7.20: Shows subject type badge/icon
- FR-7.21: Can create new subject if no matches found

### 3.5 Quick Add Dialogs

For simple items that don't need full markdown editor:

**Agenda Item Dialog:**
- Title (required)
- Priority (1-10, default 5)
- Recurring? (yes/no)
- If recurring: pattern (weekly/monthly/quarterly)

**Action Dialog:**
- Title (required)
- Due date (optional, date picker)
- Tags (comma-separated)
- Description (short text)

**Requirements:**
- FR-7.22: Quick dialogs for simple data entry
- FR-7.23: Full editor for long-form content (meetings, notes)
- FR-7.24: Tab navigation through fields
- FR-7.25: Enter to submit, Escape to cancel

### 3.6 Global Navigation

**Navigation Flow:**
1. **Startup**: App opens to Actions Dashboard (Section 3.1)
2. **Subject Lookup**: Ctrl+P or / opens quick lookup (Section 3.4)
3. **Subject View**: Select subject → Subject Detail Screen (Section 3.2)
4. **Return**: Escape from Subject Detail → Back to Actions Dashboard

**Actions Across All Screens:**
- `Ctrl+P` or `/` - Quick subject lookup (command palette)
- `Ctrl+H` - Return to Actions Dashboard (home)
- `?` - Show contextual help with keyboard shortcuts
- `q` - Quit application (with confirmation if unsaved changes)

**Requirements:**
- FR-7.26: Ctrl+P and / globally accessible for subject lookup
- FR-7.27: Escape always returns to previous screen
- FR-7.28: Breadcrumb shows current context (Dashboard > Subject > Detail)
- FR-7.29: Status bar shows context-aware keyboard shortcuts
- FR-7.30: Help overlay (?) shows all available actions for current screen

---

## 4. Workflows

### 4.1 Planning a Meeting

1. User opens subject
2. User adds agenda items (priority-sorted)
3. (Optional) User adds recurring agenda items
4. Before meeting: User reviews agenda

### 4.2 Recording a Meeting

1. User creates new meeting (date, attendees)
2. Markdown editor opens
3. User writes notes, references agenda items
4. User marks decisions and creates actions inline
5. User saves meeting
6. Referenced agenda items auto-marked as "discussed"
7. If agenda item is recurring, new instance created

### 4.3 Managing Actions

1. User views actions dashboard (today/week/next week)
2. User sees actions from all subjects
3. User marks actions in-progress or done
4. Completed actions visible for 7 days
5. After 7 days, auto-archived (hidden by default)
6. User can toggle view to see archived actions

### 4.4 External Workflow

1. User edits files with external editor (vim, vscode, etc.)
2. On next app startup, system detects file changes
3. Index automatically rebuilds
4. User can manually rebuild with `r` key anytime

---

## 5. Search and Discovery

**Requirements:**
- FR-8.1: Search subjects by name or description
- FR-8.2: Full-text search in notes
- FR-8.3: Filter actions by status, due date, tags
- FR-8.4: External grep/ripgrep works on all markdown files
- FR-8.5: Search results highlight matching text

---

## 6. Data Management

**Requirements:**
- FR-9.1: Export subject to single markdown file (for sharing)
- FR-9.2: Backup entire data directory (just copy files)
- FR-9.3: Version control with git (manual, user-initiated)
- FR-9.4: Import from markdown (future enhancement)
- FR-9.5: Data migration/upgrade handled automatically

---

## 7. Non-Functional Requirements

### 7.1 Performance
- NFR-1: App startup < 1 second (for typical dataset < 1000 items)
- NFR-2: Index rebuild < 2 seconds (for typical dataset)
- NFR-3: UI responsive, no perceptible lag on user input

### 7.2 Reliability
- NFR-4: No data loss on crash (atomic file writes)
- NFR-5: Index can always be rebuilt from files
- NFR-6: Graceful handling of malformed files

### 7.3 Usability
- NFR-7: All features accessible via keyboard (no mouse required)
- NFR-8: Keyboard shortcuts displayed contextually
- NFR-9: Consistent navigation patterns across screens
- NFR-10: Clear visual feedback for all actions

### 7.4 Maintainability
- NFR-11: Clean separation: file layer, index layer, UI layer
- NFR-12: Comprehensive test coverage (unit + integration)
- NFR-13: Well-documented code and architecture
- NFR-14: Logging for debugging issues

---

## 8. Future Enhancements (Out of Scope for V1)

- Links between notes (wiki-style backlinks)
- Calendar view for meetings and actions
- Gantt chart for project timelines
- Templates for common meeting types
- Mobile companion app
- Web viewer (read-only)
- Collaboration features
- Encryption for sensitive data
