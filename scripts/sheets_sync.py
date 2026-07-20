"""Orchestrates the GitHub-native, Google-Sheets-driven generation flow,
built on the Apps Script Web App bridge (scripts/sheets_gas_client.py) —
no Google Cloud project needed. Called as steps from
.github/workflows/generate.yml — see docs/AUTOMATION_ARCHITECTURE.md.

Subcommands:
  claim            Find the oldest Pending/blank row (or recover a stale
                    In-Progress row older than 25 min), claim it, print its
                    fields as GITHUB_OUTPUT lines.
  progress         Update a row's Progress bar text.
  complete         Mark a row Completed and send the approval email.
  fail             Mark a row failed (Rejected/Failed) after an error.
  check-approvals  Scan Completed+Pending rows for a Gmail Approve/Reject
                    reply and sync it back to the sheet.
"""
import argparse
import datetime
import os
import sys

import requests

import sheets_gas_client as gas
from publish import publish_to_instagram

STALE_MINUTES = 25
MEDIA_REPO = "projects123929/media"


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


GENERATION_START_UTC = datetime.time(5, 30)  # 11:00 IST


def cmd_claim(args):
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if now_utc.time() < GENERATION_START_UTC:
        _gh_output("has_row", "false")
        print(f"Before daily generation start time (11:00 IST / {GENERATION_START_UTC} UTC); skipping claim.")
        return

    rows = gas.get_rows()

    # Stale-row recovery: an "In Progress" row whose Last Updated is old
    # likely means a previous run crashed. Requeue it rather than leaving
    # it stuck forever.
    for row in rows:
        if row["Status"] == "In Progress":
            last = row.get("Last Updated", "")
            try:
                ts = datetime.datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                age_min = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() / 60
            except ValueError:
                age_min = STALE_MINUTES + 1
            if age_min > STALE_MINUTES:
                gas.update_row(row["row_number"], {
                    "Status": "Pending",
                    "Progress": "⚠ previous attempt stalled, retrying",
                    "Last Updated": _now(),
                })
                row["Status"] = "Pending"

    # One video per day, regardless of how many rows are queued: if any row
    # was already claimed/processed today (any outcome), don't claim another.
    today_str = datetime.date.today().isoformat()
    for row in rows:
        if row["Status"] in ("In Progress", "Completed") and row.get("Last Updated", "").startswith(today_str):
            _gh_output("has_row", "false")
            print(f"Row {row['row_number']} already processed today ({today_str}); skipping claim.")
            return

    candidates = [r for r in rows if r["Status"] in ("", "Pending")]
    if not candidates:
        _gh_output("has_row", "false")
        return

    row = candidates[0]
    row_number = row["row_number"]
    title = row["Video Title"]
    aspect = row["Aspect Ratio"]
    today = datetime.date.today().isoformat()
    run_folder = f"{today}-row{row_number}"

    if "9:16" not in aspect:
        gas.update_row(row_number, {
            "Status": "Completed",
            "Progress": "⚠ unsupported aspect ratio (9:16 only for now)",
            "Approval Status": "Rejected",
            "Upload Status": "Failed",
            "Last Updated": _now(),
        })
        _gh_output("has_row", "false")
        return

    gas.update_row(row_number, {"Status": "In Progress", "Progress": _bar(0), "Last Updated": _now()})

    _gh_output("has_row", "true")
    _gh_output("row_number", row_number)
    _gh_output("idea", title)
    _gh_output("run_folder", run_folder)
    _gh_output("today", today)


def cmd_progress(args):
    gas.update_row(args.row, {"Progress": _bar(args.percent), "Last Updated": _now()})


def cmd_complete(args):
    gas.update_row(args.row, {
        "Status": "Completed",
        "Progress": _bar(100),
        "Approval Status": "Pending",
        "Upload Status": "Pending",
        "Last Updated": _now(),
        "Video URL": args.video_url,
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
    gas.send_html_email(subject, body)


def cmd_fail(args):
    gas.update_row(args.row, {
        "Status": "Completed",
        "Progress": "⚠ failed - see logs",
        "Approval Status": "Rejected",
        "Upload Status": "Failed",
        "Last Updated": _now(),
    })


def _download_private_asset(video_url):
    # video_url looks like https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}
    # Plain authenticated GETs to that browser-download URL 404 for private
    # repos in automation - GitHub's documented way is via the API's asset
    # endpoint instead: look up the release by tag, find the asset's API
    # `url`, then GET that with Accept: application/octet-stream.
    token = os.environ["GITHUB_TOKEN"]
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    parts = video_url.rstrip("/").split("/")
    filename, tag = parts[-1], parts[-2]
    owner_repo = "/".join(parts[3:5])

    release_resp = requests.get(
        f"https://api.github.com/repos/{owner_repo}/releases/tags/{tag}",
        headers=headers, timeout=30,
    )
    release_resp.raise_for_status()
    assets = release_resp.json()["assets"]
    asset = next((a for a in assets if a["name"] == filename), None)
    if asset is None:
        raise RuntimeError(f"Asset '{filename}' not found in release '{tag}'")

    asset_resp = requests.get(
        asset["url"],
        headers={"Authorization": f"token {token}", "Accept": "application/octet-stream"},
        timeout=120,
    )
    asset_resp.raise_for_status()
    return asset_resp.content


def _reupload_to_media_repo(video_bytes, tag_name):
    token = os.environ["MEDIA_REPO_PAT"]
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    create_resp = requests.post(
        f"https://api.github.com/repos/{MEDIA_REPO}/releases",
        headers=headers,
        json={"tag_name": tag_name, "name": tag_name},
        timeout=30,
    )
    if not create_resp.ok:
        raise RuntimeError(
            f"Create release failed ({create_resp.status_code}): {create_resp.text}"
        )
    upload_url = create_resp.json()["upload_url"].split("{")[0]

    upload_resp = requests.post(
        upload_url,
        headers={**headers, "Content-Type": "video/mp4"},
        params={"name": "final.mp4"},
        data=video_bytes,
        timeout=120,
    )
    upload_resp.raise_for_status()
    return upload_resp.json()["browser_download_url"]


def _publish_row(row):
    row_number = row["row_number"]
    try:
        video_bytes = _download_private_asset(row["Video URL"])
        safe_ts = _now().replace(":", "").replace("-", "")  # git tags can't contain ':'
        public_url = _reupload_to_media_repo(video_bytes, f"sheet-row{row_number}-{safe_ts}")
        result = publish_to_instagram(public_url, row["Video Title"])
    except Exception as e:
        gas.update_row(row_number, {"Upload Status": "Failed", "Last Updated": _now()})
        print(f"Row {row_number}: publish failed - {e}")
        return

    if result["success"]:
        gas.update_row(row_number, {"Upload Status": "Posted", "Last Updated": _now()})
        print(f"Row {row_number}: posted - {result.get('permalink')}")
    else:
        gas.update_row(row_number, {"Upload Status": "Failed", "Last Updated": _now()})
        print(f"Row {row_number}: publish failed - {result['error']}")


def cmd_check_approvals(args):
    rows = gas.get_rows()
    checked = 0
    updated = 0
    for row in rows:
        if row["Status"] != "Completed":
            continue

        # Already approved but never successfully published (e.g. Video URL
        # was added after approval, or a previous publish attempt failed) -
        # retry without needing a fresh Gmail reply.
        if row["Approval Status"] == "Approved" and row["Upload Status"] != "Posted":
            if row.get("Video URL"):
                _publish_row(row)
            continue

        if row["Approval Status"] != "Pending":
            continue
        checked += 1
        result = gas.check_reply(f"[Row {row['row_number']}]")
        if result == "approve":
            gas.update_row(row["row_number"], {"Approval Status": "Approved", "Last Updated": _now()})
            updated += 1
            row["Approval Status"] = "Approved"
            _publish_row(row)
        elif result == "reject":
            gas.update_row(row["row_number"], {"Approval Status": "Rejected", "Last Updated": _now()})
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
