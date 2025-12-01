from datetime import date, datetime, timedelta
import locale
import re

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Input
from textual.widget import Widget
from textual import events


def format_date_locale(d: date | datetime | None, with_day_prefix: bool = True) -> str:
    """Format a date with locale-aware format and optional day prefix.

    Args:
        d: The date to format (date or datetime)
        with_day_prefix: Whether to include day name prefix (e.g., "Mon ")

    Returns:
        Formatted date string like "Mon 01/12/2024" or "01/12/2024"
    """
    if d is None:
        return "-"

    if isinstance(d, datetime):
        d = d.date()

    # Detect locale separator
    sample = date(2000, 11, 22).strftime('%x')
    separator = '/'
    for char in sample:
        if not char.isdigit():
            separator = char
            break

    # Detect date format (day-first or month-first)
    sample = date(2003, 11, 22).strftime('%x')
    if '22' in sample and '11' in sample:
        day_pos = sample.find('22')
        month_pos = sample.find('11')
        if day_pos < month_pos:
            date_format = f"%d{separator}%m{separator}%Y"
        else:
            date_format = f"%m{separator}%d{separator}%Y"
    else:
        date_format = f"%d{separator}%m{separator}%Y"

    formatted = d.strftime(date_format)

    if with_day_prefix:
        day_name = d.strftime('%a')
        return f"{day_name} {formatted}"

    return formatted


class DateInput(Widget, can_focus=True):
    """Custom date input with arrow key navigation and locale-aware formatting."""

    DEFAULT_CSS = """
    DateInput {
        height: auto;
        width: auto;
    }
    DateInput Horizontal {
        height: auto;
        width: auto;
    }
    DateInput .day-prefix {
        width: 4;
        padding: 0 1 0 0;
    }
    DateInput .date-field {
        width: 20;
    }
    """

    def __init__(
        self,
        value: date | None = None,
        default_today: bool = True,
        locale_name: str = "",
        id: str | None = None,
        **kwargs
    ):
        super().__init__(id=id, **kwargs)
        self._locale = locale_name
        if value is None and default_today:
            self._date = date.today()
        else:
            self._date = value
        # Get locale separator (/ or - or .)
        self._separator = self._get_locale_separator()

    def _get_locale_separator(self) -> str:
        """Detect date separator from locale."""
        sample = date(2000, 11, 22).strftime('%x')  # Use distinct numbers
        # Find the separator between digits
        for char in sample:
            if not char.isdigit():
                return char
        return '/'

    def _get_date_format(self) -> str:
        """Detect date format from locale (day-first or month-first)."""
        # Use a date where day, month, year are all different to detect order
        sample = date(2003, 11, 22).strftime('%x')  # 22/11/03 or 11/22/03
        sep = self._separator
        # Check if day comes first (22 before 11)
        if '22' in sample and '11' in sample:
            day_pos = sample.find('22')
            month_pos = sample.find('11')
            if day_pos < month_pos:
                return f"%d{sep}%m{sep}%Y"  # dd/mm/yyyy
            else:
                return f"%m{sep}%d{sep}%Y"  # mm/dd/yyyy
        return f"%d{sep}%m{sep}%Y"  # Default to day-first

    def _get_day_name(self, d: date | None) -> str:
        """Get locale-aware abbreviated day name."""
        if d is None:
            return "   "
        if self._locale:
            old_locale = locale.getlocale(locale.LC_TIME)
            try:
                locale.setlocale(locale.LC_TIME, self._locale)
                return d.strftime('%a')
            finally:
                locale.setlocale(locale.LC_TIME, old_locale)
        return d.strftime('%a')

    def _format_date_only(self, d: date | None) -> str:
        """Format just the date part (without day name) with 4-digit year."""
        if d is None:
            return ""
        return d.strftime(self._get_date_format())

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(self._get_day_name(self._date), classes="day-prefix", id="day-prefix")
            yield Input(
                value=self._format_date_only(self._date),
                placeholder=f"dd{self._separator}mm{self._separator}yyyy",
                classes="date-field",
                id="date-field",
                restrict=r"[0-9" + re.escape(self._separator) + r"]*",
            )

    def on_mount(self) -> None:
        """Set up input handling."""
        self._input = self.query_one("#date-field", Input)
        self._day_label = self.query_one("#day-prefix", Static)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Auto-insert separators and update day name."""
        if event.input.id != "date-field":
            return

        # Prevent re-entry when we update the input value
        if getattr(self, '_updating', False):
            return

        text = event.value
        digits = ''.join(c for c in text if c.isdigit())

        # Build formatted text with auto-inserted separators
        if len(digits) <= 2:
            new_text = digits
        elif len(digits) <= 4:
            new_text = digits[:2] + self._separator + digits[2:]
        else:
            new_text = digits[:2] + self._separator + digits[2:4] + self._separator + digits[4:8]

        # Update input if text changed (to insert separators)
        if new_text != text:
            self._updating = True
            self._input.value = new_text
            # Move cursor to end after inserting separator
            self._input.cursor_position = len(new_text)
            self._updating = False

        # Try to parse and update day name
        parsed = self._parse_date(new_text)
        if parsed:
            self._date = parsed
            self._day_label.update(self._get_day_name(parsed))

    def _parse_date(self, text: str) -> date | None:
        """Parse date from explicit format with 4-digit year."""
        if not text or not text.strip():
            return None
        try:
            return datetime.strptime(text.strip(), self._get_date_format()).date()
        except ValueError:
            return None

    def _adjust_date(self, days: int) -> None:
        """Adjust date by given number of days."""
        current = self._date or date.today()
        self._date = current + timedelta(days=days)
        self._input.value = self._format_date_only(self._date)
        self._day_label.update(self._get_day_name(self._date))

    def on_key(self, event: events.Key) -> None:
        """Handle arrow keys for date navigation."""
        if event.key == "up":
            self._adjust_date(1)
            event.prevent_default()
        elif event.key == "down":
            self._adjust_date(-1)
            event.prevent_default()
        elif event.key == "shift+up":
            self._adjust_date(7)
            event.prevent_default()
        elif event.key == "shift+down":
            self._adjust_date(-7)
            event.prevent_default()

    @property
    def date_value(self) -> date | None:
        """Get the current date value."""
        return self._date

    @date_value.setter
    def date_value(self, d: date | None) -> None:
        """Set the date value."""
        self._date = d
        if hasattr(self, '_input'):
            self._input.value = self._format_date_only(d)
            self._day_label.update(self._get_day_name(d))
