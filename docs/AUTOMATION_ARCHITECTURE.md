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

## Update: moving to a GitHub-native version via Zapier MCP, not Google Cloud (in progress, 2026-07-16)

A Google-Cloud-service-account-based standalone implementation
(`scripts/sheets_client.py`, `gmail_client.py`, `sheets_sync.py`, two extra
workflow files) was built and then **removed** — the user explicitly wants
to avoid Google Cloud Console setup and run everything through the existing
`.github/workflows/generate.yml` only.

The chosen replacement approach: connect the *same already-authorized*
Zapier MCP connector (the one used interactively in Claude for the Sheets/
Gmail actions described above) directly to the headless `claude -p` call
inside `generate.yml`, via Zapier's remote MCP server URL + API token
(obtained from the user's own https://mcp.zapier.com dashboard — not a
Google Cloud credential). This avoids a second, separate auth system
entirely.

Status: **not yet wired up** — waiting on the Zapier MCP server URL and an
API token (to be stored as the `ZAPIER_MCP_TOKEN` GitHub secret) from the
user's Zapier MCP dashboard before `generate.yml` can be updated to add
this as an MCP server for its `claude -p` invocation, change its schedule
from daily to frequent polling, and change its prompt to read/act on the
Sheets dashboard. `CLAUDE.md`'s "Sheets-driven mode" section above already
anticipates this — it's written to be implementation-agnostic (says "use
whatever Google Sheets/Gmail tool is available in this session" rather
than naming a specific script), so no further changes to it should be
needed once the MCP connection itself is wired up.
