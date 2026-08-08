"""Google Sheets push service — write extraction rows to a spreadsheet."""

import json
import logging
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.config import settings
from app.models.domain.sheets import SheetsError, SheetsPushResult

logger = logging.getLogger("sheets")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_service():
    creds_json = settings.google_service_account_json
    if not creds_json:
        raise SheetsError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    if creds_json.startswith("{"):
        info = json.loads(creds_json)
    else:
        with open(creds_json) as file:
            info = json.load(file)

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def _extract_sheet_id(url_or_id: str) -> str:
    if "/spreadsheets/d/" in url_or_id:
        return url_or_id.split("/spreadsheets/d/")[1].split("/")[0]
    return url_or_id


def _a1_range(sheet_name: str, cell: str = "A1") -> str:
    """Build an A1 range, quoting sheet names that contain spaces or quotes."""
    if " " in sheet_name or "'" in sheet_name or "!" in sheet_name:
        escaped = sheet_name.replace("'", "''")
        return f"'{escaped}'!{cell}"
    return f"{sheet_name}!{cell}"


async def push_rows_to_sheet(
    spreadsheet_url: str,
    rows: list[dict[str, Any]],
    sheet_name: str = "AgentFlow Results",
) -> SheetsPushResult:
    if not rows:
        raise SheetsError("No rows to push")

    service = _get_service()
    spreadsheet_id = _extract_sheet_id(spreadsheet_url)

    skip = {"flags", "document_id"}
    headers = [key for key in rows[0].keys() if key not in skip]

    flag_keys: list[str] = []
    for row in rows:
        for flag in row.get("flags", {}):
            if flag not in flag_keys:
                flag_keys.append(flag)
    all_headers = headers + flag_keys

    values = [all_headers]
    for row in rows:
        row_values: list[str] = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            row_values.append(str(value) if value is not None else "")
        for flag in flag_keys:
            row_values.append(str(row.get("flags", {}).get(flag, "")))
        values.append(row_values)

    try:
        try:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
                },
            ).execute()
        except Exception:
            pass

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=_a1_range(sheet_name),
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()

        logger.info("Pushed %d rows to sheet %s", len(rows), spreadsheet_id)
        return SheetsPushResult(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            rows_written=len(rows),
        )
    except SheetsError:
        raise
    except Exception as exc:
        logger.error("Sheets push failed: %s", str(exc))
        raise SheetsError(f"Failed to push to Google Sheets: {exc}") from exc
