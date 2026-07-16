"""Thin Google Sheets API wrapper for the GitHub-native dashboard automation.

Auth: a Google Cloud service account JSON key, provided via the
GOOGLE_SERVICE_ACCOUNT_JSON env var (the raw JSON content, not a file path).
The sheet must be shared with that service account's email as an Editor.
"""
import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = "1PrzhIFtDSPpGp1wbemoL_ZZDIRSAhJQKUS1my1vhLNY"
WORKSHEET = "Sheet1"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

COLUMNS = ["Video Title", "Aspect Ratio", "Status", "Progress", "Approval Status", "Upload Status", "Last Updated"]
COL_LETTERS = ["A", "B", "C", "D", "E", "F", "G"]


def _service():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError("Missing GOOGLE_SERVICE_ACCOUNT_JSON env var (service account key JSON)")
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def get_rows():
    """Returns a list of dicts, one per data row, each with a 'row_number' key (1-indexed sheet row)."""
    svc = _service()
    result = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{WORKSHEET}!A2:G500",
    ).execute()
    values = result.get("values", [])
    rows = []
    for i, row in enumerate(values):
        row = row + [""] * (len(COLUMNS) - len(row))
        entry = {COLUMNS[j]: row[j] for j in range(len(COLUMNS))}
        entry["row_number"] = i + 2  # sheet is 1-indexed, row 1 is the header
        rows.append(entry)
    return rows


def update_row(row_number, values: dict):
    """values: dict of {column_name: new_value}, only the given columns are touched."""
    svc = _service()
    data = []
    for col_name, val in values.items():
        if col_name not in COLUMNS:
            raise ValueError(f"Unknown column: {col_name}")
        letter = COL_LETTERS[COLUMNS.index(col_name)]
        data.append({
            "range": f"{WORKSHEET}!{letter}{row_number}",
            "values": [[val]],
        })
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()
