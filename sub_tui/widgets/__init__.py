"""Reusable widgets for SubTUI.

This module will contain:
- dialogs.py: Modal dialogs (NewSubjectDialog, NewActionDialog, etc.)
- list_items.py: Custom ListItem classes for various content types
"""

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
