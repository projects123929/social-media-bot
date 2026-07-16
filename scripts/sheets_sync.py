"""Orchestrates the GitHub-native, Google-Sheets-driven generation flow.

Called as separate steps from .github/workflows/sheet_generate.yml and
.github/workflows/check_approvals.yml — see docs/AUTOMATION_ARCHITECTURE.md
for the full picture. Subcommands:

  claim            Find the oldest Pending/blank row (or a stale In-Progress
                    row older than 25 min), claim it, print its fields as
                    GITHUB_OUTPUT lines.
  progress         Update a row's Progress bar text.
  complete         Mark a row Completed and send the approval email.
  fail             Mark a row failed (Rejected/Failed) after a generation error.
  check-approvals  Scan Completed+Pending rows for a Gmail Approve/Reject
                    reply and sync it back to the sheet.
"""
import argparse
import datetime
import os
import sys

import sheets_client
import gmail_client

STALE_MINUTES = 25


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bar(percent: int) -> str:
    filled = round(percent / 10)
    return "▓" * filled + "░" * (10 - filled) + f" {percent}%"


def _gh_output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    line = f"{key}={value}"
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    print(line)


def cmd_claim(args):
    rows = sheets_client.get_rows()

    # Stale-row recovery: an "In Progress" row whose Last Updated is old
    # likely means a previous run crashed. Treat it as failed-and-requeue.
    for row in rows:
        if row["Status"] == "In Progress":
            last = row.get("Last Updated", "")
            try:
                ts = datetime.datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                age_min = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() / 60
            except ValueError:
                age_min = STALE_MINUTES + 1  # blank/unparseable Last Updated -> treat as stale
            if age_min > STALE_MINUTES:
                sheets_client.update_row(row["row_number"], {
                    "Status": "Pending",
                    "Progress": "⚠ previous attempt stalled, retrying",
                    "Last Updated": _now(),
                })
                row["Status"] = "Pending"  # so it's eligible for claiming below

    candidates = [r for r in rows if r["Status"] in ("", "Pending")]
    if not candidates:
        _gh_output("has_row", "false")
        return

    row = candidates[0]  # oldest = first in sheet order
    row_number = row["row_number"]
    title = row["Video Title"]
    aspect = row["Aspect Ratio"]
    today = datetime.date.today().isoformat()
    run_folder = f"{today}-row{row_number}"

    if "9:16" not in aspect:
        sheets_client.update_row(row_number, {
            "Status": "Completed",
            "Progress": "⚠ unsupported aspect ratio (9:16 only for now)",
            "Approval Status": "Rejected",
            "Upload Status": "Failed",
            "Last Updated": _now(),
        })
        _gh_output("has_row", "false")
        return

    sheets_client.update_row(row_number, {
        "Status": "In Progress",
        "Progress": _bar(0),
        "Last Updated": _now(),
    })

    _gh_output("has_row", "true")
    _gh_output("row_number", row_number)
    _gh_output("idea", title)
    _gh_output("run_folder", run_folder)
    _gh_output("today", today)


def cmd_progress(args):
    sheets_client.update_row(args.row, {"Progress": _bar(args.percent), "Last Updated": _now()})


def cmd_complete(args):
    sheets_client.update_row(args.row, {
        "Status": "Completed",
        "Progress": _bar(100),
        "Approval Status": "Pending",
        "Upload Status": "Pending",
        "Last Updated": _now(),
    })
    subject = f"Approval Needed: {args.title} [Row {args.row}]"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;border:1px solid #e5e0f5;border-radius:12px;overflow:hidden;">
      <div style="background:#351C75;padding:24px 28px;">
        <h1 style="color:#ffffff;font-size:20px;margin:0;">Video Ready for Approval</h1>
      </div>
      <div style="padding:28px;background:#ffffff;">
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
          <tr><td style="padding:8px 0;color:#5A5A6E;font-size:13px;width:140px;">Video Title</td>
              <td style="padding:8px 0;color:#1A1A2E;font-size:14px;font-weight:600;">{args.title}</td></tr>
          <tr><td style="padding:8px 0;color:#5A5A6E;font-size:13px;">Aspect Ratio</td>
              <td style="padding:8px 0;color:#1A1A2E;font-size:14px;">Vertical (9:16)</td></tr>
          <tr><td style="padding:8px 0;color:#5A5A6E;font-size:13px;">Preview</td>
              <td style="padding:8px 0;"><a href="{args.video_url}" style="color:#6C3EF4;font-weight:600;">Watch the video</a></td></tr>
        </table>
        <div style="background:#F1ECFE;border-radius:8px;padding:16px 20px;">
          <p style="margin:0 0 8px 0;color:#1A1A2E;font-size:14px;font-weight:600;">Reply to this email with exactly one word:</p>
          <p style="margin:0;font-size:14px;"><span style="color:#1E7E34;font-weight:700;">Approve</span> or <span style="color:#B00020;font-weight:700;">Reject</span></p>
        </div>
        <p style="color:#5A5A6E;font-size:12px;margin-top:20px;">Automated message from the Cartoon Short Pipeline (GitHub Actions).</p>
      </div>
    </div>
    """
    gmail_client.send_html_email(subject, body)


def cmd_fail(args):
    sheets_client.update_row(args.row, {
        "Status": "Completed",
        "Progress": "⚠ failed - see logs",
        "Approval Status": "Rejected",
        "Upload Status": "Failed",
        "Last Updated": _now(),
    })


def cmd_check_approvals(args):
    rows = sheets_client.get_rows()
    checked = 0
    updated = 0
    for row in rows:
        if row["Status"] != "Completed" or row["Approval Status"] != "Pending":
            continue
        checked += 1
        result = gmail_client.check_reply(f"[Row {row['row_number']}]")
        if result == "approve":
            sheets_client.update_row(row["row_number"], {"Approval Status": "Approved", "Last Updated": _now()})
            updated += 1
        elif result == "reject":
            sheets_client.update_row(row["row_number"], {"Approval Status": "Rejected", "Last Updated": _now()})
            updated += 1
    print(f"Checked {checked} pending-approval row(s), updated {updated}.")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("claim").set_defaults(func=cmd_claim)

    p = sub.add_parser("progress")
    p.add_argument("--row", type=int, required=True)
    p.add_argument("--percent", type=int, required=True)
    p.set_defaults(func=cmd_progress)

    p = sub.add_parser("complete")
    p.add_argument("--row", type=int, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--video-url", required=True)
    p.set_defaults(func=cmd_complete)

    p = sub.add_parser("fail")
    p.add_argument("--row", type=int, required=True)
    p.set_defaults(func=cmd_fail)

    sub.add_parser("check-approvals").set_defaults(func=cmd_check_approvals)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
