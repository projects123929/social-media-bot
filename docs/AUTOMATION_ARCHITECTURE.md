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
