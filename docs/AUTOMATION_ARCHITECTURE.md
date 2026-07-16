# Google Sheets Dashboard, Email Approval & Scheduled Automation

This document exists so this part of the system is visible in the repo. It
is **not implemented as source code checked into this repository** — it was
built using Claude's connector/agent capabilities, not hand-written scripts.
This file explains exactly what exists, where it actually lives, and why
there's no corresponding `.py` file the way there is for
`scripts/higgsfield_scene.py` etc.

## What exists

1. **Google Sheets "Control Panel" dashboard**
   - Lives entirely on Google's servers as a live spreadsheet, not a file in
     this repo.
   - URL: https://docs.google.com/spreadsheets/d/1PrzhIFtDSPpGp1wbemoL_ZZDIRSAhJQKUS1my1vhLNY/edit
   - Columns: Video Title, Aspect Ratio, Status, Progress, Approval Status,
     Upload Status, Last Updated.
   - A point-in-time data snapshot is committed alongside this file as
     `dashboard_snapshot.csv` for reference (it will go stale — the sheet
     itself is the live source of truth).

2. **Scheduled sync automation ("sheets-pipeline-sync")**
   - Runs on a cron schedule (every 15 minutes) as a Claude scheduled task.
   - Lives locally at
     `C:\Users\ASUS\.claude\scheduled-tasks\sheets-pipeline-sync\SKILL.md`
     on the machine that set it up — **not inside this git repo**, since
     it's part of the Claude app's own configuration, not project source.
   - Its full instructions/logic are backed up (not "live", just a copy)
     at [`docs/sheets-pipeline-sync.SKILL.md`](./sheets-pipeline-sync.SKILL.md)
     in this same repo.
   - What it does each run: reads new/updated rows from the sheet, runs
     this repo's existing generation flow (`CLAUDE.md`, the `scripts/`
     helpers) using the row's Video Title as the idea, updates
     Status/Progress live, and once a video is done, sends the approval
     email described below.

3. **Email approval flow**
   - Not a script — the scheduled task sends email directly via a Gmail
     connector (OAuth-authorized to `ai@ms2.co.in`) and reads replies the
     same way.
   - This replaces/supersedes `scripts/send_approval_email.py`
     (SMTP/app-password based) for rows that come through the Sheets
     dashboard — that script is still in the repo and still used for the
     original CLI-driven local flow described in `CLAUDE.md`, but the
     Sheets-driven flow uses Gmail's API via the connector instead.
   - Flow: video completes → premium HTML email sent to `ai@ms2.co.in`
     with a Google Drive preview link → reviewer replies "Approve" or
     "Reject" → next scheduled run detects the reply and writes it into
     the sheet's Approval Status column.

## Why this can't just be "pushed" like the rest of the code

Everything else in this repo (`scripts/*.py`, `CLAUDE.md`, the GitHub
Actions workflows) is source code you can open, read, and run yourself.
The Sheets/Gmail automation described here is different: it's Claude
itself, running on a schedule, calling Google's APIs directly through an
authorized connector — there was no script written for it to check in.
This document plus the SKILL.md backup are the closest equivalent to
"the code" for this part of the system.

If a fully self-contained, standalone script version of this same
automation (own Google service-account credentials, runnable without
Claude/connectors) is wanted instead, that would be new work — a genuinely
different implementation from what's described here, not something to
"find and push."

## Update: a GitHub-native version now also exists (added 2026-07-16)

The above (Claude scheduled task + connectors) was the first version built,
and still works. A second, independent implementation now also exists that
runs entirely inside GitHub Actions with no dependency on Claude or a local
machine being on:

- `scripts/sheets_client.py` / `scripts/gmail_client.py` — real Python
  wrappers around the Sheets and Gmail APIs
- `scripts/sheets_sync.py` — the orchestrator CLI (`claim` / `progress` /
  `complete` / `fail` / `check-approvals`)
- `scripts/gmail_oauth_setup.py` — one-time local script to obtain a Gmail
  OAuth refresh token
- `.github/workflows/sheet_generate.yml` — polls the sheet every 20 minutes,
  claims a pending row, runs generation, uploads the video as a GitHub
  Release, and emails for approval
- `.github/workflows/check_approvals.yml` — polls Gmail every 15 minutes for
  Approve/Reject replies and syncs them back to the sheet
- `CLAUDE.md`'s new "Sheets-driven mode" section — makes the existing
  generation flow per-row-safe (`RUN_FOLDER`) and reports progress back to
  the sheet, only when `RUN_FOLDER`/`SHEET_ROW` env vars are set (fully
  backward compatible with the original local/CLI flow)

See `docs/GITHUB_NATIVE_SHEETS_SETUP.md` for the exact credential setup
steps this version needs (a Google Cloud service account for Sheets, and an
OAuth client for Gmail — different from, and in addition to, the Higgsfield/
Claude secrets already in use).

Both versions read/write the same Google Sheet, so **don't run both at
once** — pick one (recommended: the GitHub-native version, since it doesn't
require the Claude app to stay open) and disable the other to avoid two
systems claiming the same row.
