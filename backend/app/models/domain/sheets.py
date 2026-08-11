"""Google Sheets domain models."""

from dataclasses import dataclass


@dataclass
class SheetsPushResult:
    spreadsheet_id: str
    sheet_name: str
    rows_written: int


class SheetsError(Exception):
    """Raised when Google Sheets operation fails."""
