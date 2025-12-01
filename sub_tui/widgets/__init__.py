"""Reusable widgets for SubTUI.

This module will contain:
- dialogs.py: Modal dialogs (NewSubjectDialog, NewActionDialog, etc.)
- list_items.py: Custom ListItem classes for various content types
- date_input.py: Custom date input widget with locale support
"""

from .date_input import DateInput, format_date_locale
from .dialogs import (
    ConfirmDialog,
    EditSubjectDialog,
    NewActionDialog,
    NewAgendaDialog,
    NewMeetingDialog,
    NewNoteDialog,
    NewSubjectDialog,
    SubjectLookupDialog,
    ViewActionDialog,
    ViewAgendaDialog,
    ViewMeetingDialog,
    ViewNoteDialog,
)

__all__ = [
    "ConfirmDialog",
    "DateInput",
    "format_date_locale",
    "EditSubjectDialog",
    "NewActionDialog",
    "NewAgendaDialog",
    "NewMeetingDialog",
    "NewNoteDialog",
    "NewSubjectDialog",
    "SubjectLookupDialog",
    "ViewActionDialog",
    "ViewAgendaDialog",
    "ViewMeetingDialog",
    "ViewNoteDialog",
]
