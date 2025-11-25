# SubTUI

A Terminal User Interface (TUI) application for managing subjects (boards, projects, teams, people) with agendas, meeting minutes, actions, and knowledge notes.

## Features

- **Subjects**: Organize boards, projects, teams, and people
- **Agenda Items**: Track discussion topics with priorities and recurring patterns
- **Meetings**: Record meeting minutes in markdown format
- **Actions**: Personal task management with due dates and auto-archiving
- **Notes**: Knowledge base with markdown support and tagging
- **Actions Dashboard**: Start with a view of all your actions across subjects
- **Quick Lookup**: Fast subject switching with command palette (Ctrl+P)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m sub_tui
```

## Data Storage

All data is stored as human-readable files:
- Markdown files for meetings and notes
- YAML files for structured data
- SQLite index for fast queries (can be rebuilt)

Data location: `./data/`

## Documentation

See [REQUIREMENTS.md](REQUIREMENTS.md) for detailed functional requirements.
