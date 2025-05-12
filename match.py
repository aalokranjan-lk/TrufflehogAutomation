#!/usr/bin/env python3
"""
Sync “Validity status” between two TruffleHog Google Sheets.

• Q4 sheet : 1BwWRodq-aUOHq1hn0S8c52_SfXd20TkJ-uejlEJ4x0I  (worksheet “TruffleHog”)
      · key column  :  Github Links
      · status value:  column N  (zero-based index 13)

• Q2 sheet : 1D0IDweZfF5rD24SAVq3kyYY_2-MS3NMuO10u5W7GR_Y  (worksheet “Trufflehog Data”)
      · key column  :  Link
      · target col  :  Validity status   (added/updated)

Dependencies
------------
pip install gspread google-auth pandas tqdm
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from tqdm import tqdm

# ───────────────────────── CONFIG ──────────────────────────
SERVICE_ACCOUNT_KEY = "aalok-spreadsheet_credentials.json"

Q4_SPREADSHEET_ID = "1BwWRodq-aUOHq1hn0S8c52_SfXd20TkJ-uejlEJ4x0I"
Q4_WS_NAME        = "TruffleHog"
Q4_LINK_HEADER    = "Github Links"
Q4_STATUS_COL_N   = 13               # column N (0-based)

Q2_SPREADSHEET_ID = "1D0IDweZfF5rD24SAVq3kyYY_2-MS3NMuO10u5W7GR_Y"
Q2_WS_NAME        = "Trufflehog Data"
Q2_LINK_HEADER    = "Link"
Q2_STATUS_HEADER  = "Validity status"

UPLOAD_CHUNK      = 2000             # rows per API call
# ────────────────────────────────────────────────────────────


# ---------- helpers -----------------------------------------------------------

def gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    return gspread.authorize(
        Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY, scopes=scopes)
    )


def ws_to_df(ws) -> pd.DataFrame:
    rows = ws.get_all_values()
    return pd.DataFrame(rows[1:], columns=rows[0])


def build_q4_mapping(ws) -> Dict[str, str]:
    """Return {github_link: status} from the Q4 worksheet."""
    rows = ws.get_all_values()
    header = rows[0]
    try:
        link_idx = header.index(Q4_LINK_HEADER)
    except ValueError:
        sys.exit(f"[ERROR] Column {Q4_LINK_HEADER!r} not found in Q4 sheet.")

    mapping: Dict[str, str] = {}
    for r in rows[1:]:
        if len(r) <= max(link_idx, Q4_STATUS_COL_N):
            continue
        link   = r[link_idx].strip()
        status = r[Q4_STATUS_COL_N].strip()
        if link:
            mapping[link] = status
    return mapping


def ensure_status_column(ws_q2, df_q2: pd.DataFrame):
    """Add ‘Validity status’ column (sheet + DataFrame) if missing."""
    if Q2_STATUS_HEADER in df_q2.columns:
        return df_q2, df_q2.columns.get_loc(Q2_STATUS_HEADER)

    # add empty column at far right
    ws_q2.add_cols(1)
    new_col_idx_1 = len(df_q2.columns) + 1  # 1-based
    ws_q2.update_cell(1, new_col_idx_1, Q2_STATUS_HEADER)

    df_q2[Q2_STATUS_HEADER] = ""
    return df_q2, new_col_idx_1 - 1          # return 0-based index


def col_letter(idx_1based: int) -> str:
    """Convert 1-based column index to sheet column letters."""
    res = ""
    while idx_1based:
        idx_1based, rem = divmod(idx_1based - 1, 26)
        res = chr(65 + rem) + res
    return res


# ---------- main flow ---------------------------------------------------------

def main() -> None:
    if not Path(SERVICE_ACCOUNT_KEY).exists():
        sys.exit("[FATAL] Service-account key file not found.")

    gc = gspread_client()

    # Q4 mapping
    ws_q4 = gc.open_by_key(Q4_SPREADSHEET_ID).worksheet(Q4_WS_NAME)
    link_to_status = build_q4_mapping(ws_q4)
    print(f"[INFO] Q4 → collected {len(link_to_status):,} link→status pairs")

    # Q2 data
    ws_q2 = gc.open_by_key(Q2_SPREADSHEET_ID).worksheet(Q2_WS_NAME)
    df_q2 = ws_to_df(ws_q2)
    print(f"[INFO] Q2 → loaded {len(df_q2):,} rows")

    # ensure target column exists
    df_q2, status_col_zero = ensure_status_column(ws_q2, df_q2)
    status_col_one = status_col_zero + 1

    # copy statuses on link match
    matches = 0
    for idx, row in df_q2.iterrows():
        link = row.get(Q2_LINK_HEADER, "").strip()
        if link in link_to_status:
            df_q2.at[idx, Q2_STATUS_HEADER] = link_to_status[link]
            matches += 1
    print(f"[INFO] {matches:,} links matched – updating Q2 sheet…")

    # push updates in chunks
    colLtr = col_letter(status_col_one)
    total  = len(df_q2)
    values = [[v] for v in df_q2[Q2_STATUS_HEADER].tolist()]

    for i in tqdm(range(0, total, UPLOAD_CHUNK), desc="Uploading", ncols=80):
        chunk_vals = values[i : i + UPLOAD_CHUNK]
        start_row  = i + 2                       # skip header (row 1)
        end_row    = start_row + len(chunk_vals) - 1
        rng        = f"{colLtr}{start_row}:{colLtr}{end_row}"

        # new order: values first, range second
        ws_q2.update(chunk_vals, rng, value_input_option="RAW")

    print("✅ Sync complete — open the Q2 sheet to verify.")


if __name__ == "__main__":
    main()
