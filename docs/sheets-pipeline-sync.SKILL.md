---
name: sheets-pipeline-sync
description: Poll the Cartoon Short Pipeline Google Sheets dashboard for new/pending rows, drive video generation, send a premium Gmail approval-request email, monitor for Approve/Reject replies, and sync Status/Progress/Approval/Upload back to the sheet.
---

You are running a recurring sync step for a local automated cartoon-short video pipeline. This prompt is fully self-contained — you have no memory of any prior conversation about this project.

PROJECT LOCATION: C:\Users\ASUS\MS2\Yt Automation\extracted\social-media-bot-main
Contains CLAUDE.md (generation instructions), rules.md (fixed constraints: 30-35s, 9:16 aspect ratio, max 5 scenes), config/theme.json, config/characters.json, scripts/ (higgsfield_scene.py, extract_last_frame.py, burn_caption.py, concat_clips.py, write_status.py, publish.py). scripts/send_approval_email.py is NOT used here — approval emails are sent via the Gmail connector instead.

GOOGLE SHEETS DASHBOARD (control panel), selected_api "GoogleSheetsV2CLIAPI":
- Spreadsheet ID: 1PrzhIFtDSPpGp1wbemoL_ZZDIRSAhJQKUS1my1vhLNY, Worksheet: Sheet1
- URL: https://docs.google.com/spreadsheets/d/1PrzhIFtDSPpGp1wbemoL_ZZDIRSAhJQKUS1my1vhLNY/edit
- Columns: A=Video Title, B=Aspect Ratio, C=Status (Pending/In Progress/Completed), D=Progress (rendered text bar, not a formula), E=Approval Status (Pending/Approved/Rejected), F=Upload Status (Pending/Uploaded/Failed), G=Last Updated (ISO-ish timestamp string you write yourself, UTC, e.g. "2026-07-15T13:05:00Z"), H=Description (optional free text; may be blank)
- **Captions/subtitles trigger**: if Video Title OR Description contains
  the word "caption" or "subtitle" (case-insensitive), captions are ON for
  that row's generation — pass the full Description text through as the
  `DESCRIPTION` env var in step 3f below so CLAUDE.md can check it too.
  Otherwise leave `DESCRIPTION` unset/empty. This is a per-row decision;
  do not carry it over from a previous row.
- IMPORTANT — Aspect Ratio values are "Vertical (9:16)", "Horizontal (16:9)", "Square (1:1)" (NOT plain "9:16" — that string gets silently auto-converted by Sheets into a time-of-day value like "09:16" because it matches an H:MM pattern, which previously broke the matching logic below. Always match by checking whether the value CONTAINS "9:16", not exact-equals, as extra defense against future formatting drift).
- If the connector isn't enabled this session, call discover_zapier_actions / enable_zapier_action for "Google Sheets" first. Use execute_zapier_read_action / execute_zapier_write_action with actions like get_many_rows, update_row, add_row (call list_enabled_zapier_actions to confirm exact params — never guess).
- CRITICAL: get_many_rows returns each row's actual sheet row_number (e.g. 2, 3, 4...) alongside its column values. You MUST capture and reuse that exact row_number as the "row" parameter on every later update_row call for that row — do not assume row order or recompute it from position in a list, and do not confuse it with the row's position among only the filtered/matching rows.

GMAIL (approval emails), selected_api "GoogleMailV2CLIAPI":
- Reviewer/monitored address: ai@ms2.co.in (same account the connector is authorized as, so send-to-self is expected, not a bug).
- If not enabled this session, call discover_zapier_actions / enable_zapier_action for "Gmail".
- To send: execute_zapier_write_action, action "message" (the WRITE action — list_enabled_zapier_actions will show both a read and a write action both keyed "message"; use the one under execute_zapier_write_action). Params: to=["ai@ms2.co.in"], subject="Approval Needed: {Video Title} [Row {row_number}]", body_type="html", body=premium HTML (dark purple header #351C75, white bold header text, a details table listing Video Title / Aspect Ratio / Generated date / Preview link with label color #5A5A6E and value color #1A1A2E, a callout box background #F1ECFE telling the reviewer to reply with exactly one word "Approve" (green #1E7E34 bold) or "Reject" (red #B00020 bold), small gray footer noting this is automated).
  - The subject MUST include "[Row {row_number}]" using that row's real sheet row number — this is how replies get matched back to the correct row later, since Video Title alone is not guaranteed unique across rows.
- Preview link: upload storage/pending/{run_folder}/final.mp4 (see run_folder definition below) to Google Drive — use the Drive MCP connector's create_file action with base64Content + contentMimeType "video/mp4", parentId "12WmZDN1lCFx4IQrVaCks714IODJlTamL" (the existing shared pipeline videos folder) so uploads stay organized in one place rather than scattered in Drive root. If upload fails or the file is too large, write "(video attached is unavailable — check storage/pending/{run_folder}/final.mp4 locally)" instead of fabricating a link.
- To check for replies: execute_zapier_read_action, action "message", query like `subject:"[Row {row_number}]" newer_than:5d`. Inspect the most recent message that is NOT the original outbound one you sent. Trim whitespace, compare case-insensitively, and match on the reply starting with "approve" or "reject" (e.g. "Approve." or "Approve, looks good" both count). If no reply yet or it matches neither keyword, leave Approval Status "Pending" and do nothing further.
- Only ever send ONE approval email per row, at the exact moment that row's Status transitions to "Completed" (inside step 2f below). Step 3 (reply-checking for already-completed rows) only ever reads Gmail — it must never send a new email under any circumstance, including if no prior email is found; if that happens, just note it in your summary rather than sending one from step 3.

YOUR JOB THIS RUN:

1. Read all rows (get_many_rows, worksheet Sheet1, columns A:G, row_count ~200), keeping each row's row_number attached to its data for every step below.

2. STALE-ROW RECOVERY (do this before claiming any new row): for any row with Status="In Progress" whose Last Updated (column G) is more than 25 minutes old (or blank), treat it as abandoned by a crashed/killed previous run — do NOT resume generating it blindly. Instead:
   a. Check storage/pending/ on disk for a folder matching that row (see run_folder naming below) — if final.mp4 and status.json already exist there despite the sheet saying "In Progress", the row actually finished; just sync Status="Completed" etc. from status.json and continue to step 3 for it.
   b. Otherwise, treat the partial attempt as failed: set Status="Completed", Progress="⚠ stalled - retried" is wrong wording — set Progress="⚠ previous attempt stalled, retrying", Last Updated=now, and requeue it by immediately processing it fresh via step 2's normal flow below (counts toward this run's 2-new-row cap). Before regenerating anything, check whether that folder already has some scene clips/reference image from the stalled attempt and reuse/skip regenerating any that already exist on disk, per CLAUDE.md's own "never regenerate something that already succeeded" guardrail — do not blindly restart from scratch and waste Higgsfield credits on work already paid for.

3. For each row where Status is blank OR "Pending" (up to 2 oldest such rows this run — leave any extra Pending for a later run, to control Higgsfield credit usage):
   a. Read Video Title, Aspect Ratio, and Description for that row_number.
   b. Define run_folder = "{today's date}-row{row_number}" (e.g. "2026-07-15-row3") — NOT bare "{date}". Multiple rows can be processed on the same calendar day, and CLAUDE.md's default storage/pending/{date}/ path would silently overwrite one row's clips/final.mp4/status.json with another's if two rows shared a plain date folder. Substitute this run_folder everywhere CLAUDE.md/the helper scripts expect "{date}" for this row's own artifacts (storage/pending/{run_folder}/...).
   c. If Aspect Ratio does not contain "9:16" (current pipeline code only supports vertical 9:16 — hardcoded in rules.md and the scripts; "Horizontal (16:9)" and "Square (1:1)" are listed in the dropdown for future use but are NOT implemented yet): do not generate. Set Status="Completed", Progress="⚠ unsupported aspect ratio (9:16 only for now)", Approval Status="Rejected", Upload Status="Failed", Last Updated=now. Move to the next row.
   d. Otherwise, immediately update_row: Status="In Progress", Progress="░░░░░░░░░░ 0%", Last Updated=now (write Last Updated on every update in this flow, not just this one).
   e. Re-fetch just this row (get_row_by_id) right before you actually start spending credits, to guard against a race with another concurrent run — if it's no longer "In Progress" with the value you just wrote (e.g. something else already changed it), skip this row rather than double-processing it.
   f. cd into the project folder and run the generation yourself, following CLAUDE.md and rules.md exactly, using the row's Video Title as the IDEA, the row's Description as DESCRIPTION (blank if none), GENERATION_MODE=test, and run_folder (step 3b) wherever a {date} placeholder is used for this row's paths. Do NOT run scripts/send_approval_email.py or use NOTIFY_METHOD=email — you send the approval email yourself in step (h).
   g. As generation proceeds, update_row to advance Progress (and Last Updated each time): 20% after the reference image, 40/60/80% after each of the 3 scenes, 90% during captions/concatenation.
   h. Once storage/pending/{run_folder}/final.mp4 and status.json exist: update_row Status="Completed", Progress="▓▓▓▓▓▓▓▓▓▓ 100%", Approval Status="Pending", Last Updated=now. Then send the one-time Gmail approval email (subject includes "[Row {row_number}]"), uploading the video to Drive first for the preview link.
   i. Upload Status: publish.py is still a stub — always set Upload Status="Pending" (never "Uploaded") unless you've actually verified publish.py now calls a real Instagram/YouTube API.
   j. On any generation failure: retry at most once per CLAUDE.md's own guardrails, then Status="Completed", Progress="⚠ failed - see logs", Approval Status="Rejected", Upload Status="Failed", Last Updated=now. Never loop.

4. For every row with Status="Completed" and Approval Status="Pending" (from this run or earlier ones): search Gmail for a reply as described above, matched via "[Row {row_number}]" in the subject.
   - Reply says Approve → update_row Approval Status="Approved", Last Updated=now.
   - Reply says Reject → update_row Approval Status="Rejected", Last Updated=now.
   - No reply yet → leave Pending, no action, no re-send.

5. Never generate more than 1 reference image or more than 3 (test mode) / 5 (full mode) video scenes per row, per CLAUDE.md's existing hard caps.

Report back a factual summary (rows started, rows recovered from stale state, emails sent, replies detected and their resolution, any errors) — this is task output, not shown live to the user, so be complete rather than terse.