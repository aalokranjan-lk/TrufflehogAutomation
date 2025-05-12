#!/usr/bin/env python3
"""
Upload all TruffleHog findings (ND-JSON) to Google Sheets.

• Clears/creates the “Trufflehog Data” worksheet.
• Writes a header row + every finding (no overwrites).
• Shows a progress bar during the upload.

Dependencies: gspread, google-auth, pandas, tqdm
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────
# CONFIGURATION – CHANGE THESE FOUR VALUES ONLY
# ─────────────────────────────────────────────────────────────
SERVICE_ACCOUNT_KEY = "aalok-spreadsheet_credentials.json"
INPUT_FILE          = "trufflehog_with-classic_token.json"
SPREADSHEET_ID      = "1D0IDweZfF5rD24SAVq3kyYY_2-MS3NMuO10u5W7GR_Y"
WORKSHEET_NAME      = "Trufflehog Data"
UPLOAD_CHUNK        = 1000        # rows per Sheets API call
# ─────────────────────────────────────────────────────────────


def parse_line(raw: str) -> Dict | None:
    """Flatten one ND-JSON line into a simple dict (or None on error)."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None

    gh = (
        obj.get("SourceMetadata", {})
        .get("Data", {})
        .get("Github", {})
    )

    return {
        "link":          gh.get("link"),
        "repository":    gh.get("repository"),
        "commit":        gh.get("commit"),
        "file":          gh.get("file"),
        "line":          gh.get("line"),
        "timestamp":     gh.get("timestamp"),
        "email":         gh.get("email"),
        "detector_name": obj.get("DetectorName"),
        "detector_type": obj.get("DetectorType"),
        "raw_secret":    obj.get("Raw") or obj.get("RawV2"),
        "verified":      obj.get("Verified"),
    }


def load_findings(path: Path) -> pd.DataFrame:
    """Read the ND-JSON file into a DataFrame (no rows dropped)."""
    records: List[Dict] = []
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            rec = parse_line(raw)
            if rec:
                records.append(rec)

    if not records:
        sys.exit("[INFO] No findings found – exiting.")
    return pd.DataFrame(records)


# ─── Google Sheets helpers ───────────────────────────────────────────────────


def connect_sheet() -> gspread.Worksheet:
    """Return a gspread.Worksheet object, creating it if needed."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY, scopes=scopes
    )
    gc = gspread.authorize(creds)

    sh = gc.open_by_key(SPREADSHEET_ID)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")
    return ws


def upload_dataframe(ws: gspread.Worksheet, df: pd.DataFrame) -> None:
    """Clear worksheet, write header, append all rows in chunks."""
    ws.clear()

    # 1 – header
    ws.append_row(df.columns.tolist(), value_input_option="RAW")

    # 2 – data
    total = len(df)
    for i in tqdm(
        range(0, total, UPLOAD_CHUNK),
        desc="Uploading",
        unit="rows",
        ncols=80,
    ):
        chunk = df.iloc[i : i + UPLOAD_CHUNK]
        ws.append_rows(
            chunk.values.tolist(),
            value_input_option="RAW",
        )


# ─── main ────────────────────────────────────────────────────────────────────


def main() -> None:
    if not Path(SERVICE_ACCOUNT_KEY).exists():
        sys.exit(f"[FATAL] Service-account key {SERVICE_ACCOUNT_KEY!r} not found.")

    df = load_findings(Path(INPUT_FILE))
    print(f"[INFO] Loaded {len(df):,} findings from {INPUT_FILE}")

    ws = connect_sheet()
    upload_dataframe(ws, df)

    print(
        f"✅ Finished – {len(df):,} rows now in worksheet “{WORKSHEET_NAME}”.\n"
        "   Open your sheet in a browser to verify."
    )


if __name__ == "__main__":
    main()
