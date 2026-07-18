# Google Sheets Dashboard & Email Approval Automation

How the Sheets-driven generation flow actually works, end to end, and where
every piece of it lives.

## History (why this doc changed shape a few times)

Three designs were tried in order, for context if old references to them
turn up elsewhere:

1. **Claude scheduled task + Zapier connector** — worked, but only runs
   while the Claude app is open/running, and only Claude itself (not a bare
   GitHub Actions runner) can use that connector. Backed up at
   [`docs/sheets-pipeline-sync.SKILL.md`](./sheets-pipeline-sync.SKILL.md)
   for reference; **currently paused**, superseded by design #3 below.
2. **Google Cloud service account + OAuth client** — real, working
   standalone code, but required navigating Google Cloud Console (service
   account, OAuth consent screen, etc.), which the user wanted to avoid.
   Built, then removed.
3. **Google Apps Script Web App — the current, live design** (below). No
   Google Cloud Console needed at all.

## Current design

**`apps_script/Code.gs`** — paste this into the dashboard spreadsheet's
Extensions > Apps Script editor and deploy as a Web App (see
`docs/GITHUB_NATIVE_SHEETS_SETUP.md` for exact steps). It runs as whoever
deployed it (`ai@ms2.co.in`) and exposes one HTTP endpoint that can:
read all rows, update a row's columns, send an email via that account's own
Gmail, and search Gmail for an Approve/Reject reply. No service account, no
OAuth client, no Cloud Console — Apps Script inherits the deploying
account's Sheets + Gmail access automatically via one authorization click
in the Apps Script editor itself.

**`scripts/sheets_gas_client.py`** — thin Python wrapper that calls that Web
App URL via plain HTTP POST (`requests`, already a dependency — no new
libraries needed).

**`scripts/sheets_sync.py`** — the orchestrator CLI, built on the client
above:
- `claim` — finds the oldest Pending/blank row (or recovers a stale
  "In Progress" row abandoned by a crashed run >25 min ago), claims it,
  prints its Video Title/Aspect Ratio/row number as GitHub Actions outputs.
  **One video per day**: if any row was already claimed/processed today
  (any outcome - Completed, In Progress), claim is skipped even if other
  Pending rows exist in the queue.
- `progress --row N --percent P` — updates the Progress bar text.
- `complete --row N --title T --video-url U` — marks a row Completed and
  sends the HTML approval email (subject includes `[Row N]` for later
  reply-matching).
- `fail --row N` — marks a row failed after a generation error.
- `check-approvals` — scans Completed+Pending rows, checks Gmail for a
  reply, syncs Approved/Rejected back to the sheet.

**`.github/workflows/generate.yml`** — the single workflow that does
everything, on a 20-minute schedule: claims a row → runs the existing
`CLAUDE.md` generation flow (via `claude -p`, using `RUN_FOLDER`/
`SHEET_ROW` env vars so `CLAUDE.md`'s "Sheets-driven mode" section kicks
in) → uploads the video as a GitHub Release → marks the row Completed and
emails for approval → also checks for Approve/Reject replies on any
already-completed rows, every run.

**`CLAUDE.md`**'s "Sheets-driven mode" section — makes the existing
generation flow per-row-safe (`storage/pending/{RUN_FOLDER}/` instead of
`storage/pending/{date}/`, avoiding same-day collisions between rows) and
calls `sheets_sync.py progress` at each milestone. Fully backward
compatible — if `RUN_FOLDER`/`SHEET_ROW` aren't set, the original
`{date}`-based local/manual flow is untouched.

## Required GitHub secrets (in addition to the existing ones)

| Secret | What it is |
|---|---|
| `GAS_WEBAPP_URL` | The deployed Apps Script Web App URL |
| `GAS_SHARED_SECRET` | Must match `SHARED_SECRET` in `apps_script/Code.gs` — a lightweight check so random people can't call your Web App URL |

See `docs/GITHUB_NATIVE_SHEETS_SETUP.md` for the full setup walkthrough.

## Known gap

`publish.yml`'s GitHub-Issue-label-triggered publish flow is now orphaned
for Sheets-driven rows — approvals happen via email reply, not an issue
label. `publish.py` is still a stub regardless (no real Instagram/YouTube
posting yet), so this doesn't block anything today, but wiring "Approved"
in the sheet to actually trigger `publish.py` is unbuilt.
