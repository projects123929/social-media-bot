"""Sends the Approve/Reject email for a finished video.

Usage: python scripts/send_approval_email.py --date 2026-07-06 --idea "..."
"""
import argparse
import json
import mimetypes
import os
import secrets
import smtplib
import sys
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_config import load_env, require, PIPELINE_ROOT

PENDING_DIR = os.path.join(PIPELINE_ROOT, "storage", "pending")

# Gmail's hard attachment limit is 25MB; leave headroom for MIME overhead.
MAX_ATTACHMENT_BYTES = 23 * 1024 * 1024


def send_approval_email(date, idea):
    load_env()
    gmail_user = require("GMAIL_USER")
    gmail_app_password = require("GMAIL_APP_PASSWORD")
    recipient = require("APPROVAL_RECIPIENT")
    host = os.environ.get("APPROVAL_SERVER_HOST", "localhost")
    port = os.environ.get("APPROVAL_SERVER_PORT", "8765")

    run_dir = os.path.join(PENDING_DIR, date)
    status_path = os.path.join(run_dir, "status.json")
    if not os.path.exists(status_path):
        raise FileNotFoundError(f"No status.json found at {status_path}")

    with open(status_path, "r", encoding="utf-8") as f:
        status = json.load(f)

    token = secrets.token_urlsafe(16)
    status["token"] = token
    status["status"] = "Generated"
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    approve_url = f"http://{host}:{port}/approve?date={date}&token={token}"
    reject_url = f"http://{host}:{port}/reject?date={date}&token={token}"

    video_path = status.get("video_path")
    video_note = "See attached video."
    attach_video = False
    if video_path and os.path.exists(video_path):
        size = os.path.getsize(video_path)
        if size <= MAX_ATTACHMENT_BYTES:
            attach_video = True
        else:
            video_note = (
                f"Video too large to attach ({size / (1024 * 1024):.1f} MB, "
                f"limit ~23 MB). File: {video_path}"
            )
    else:
        video_note = "(video file not found)"

    msg = EmailMessage()
    msg["Subject"] = f"Video ready for approval - {date}"
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.set_content(
        f"A new cartoon short is ready for review.\n\n"
        f"Idea: {idea}\n"
        f"{video_note}\n\n"
        f"Approve: {approve_url}\n"
        f"Reject: {reject_url}\n\n"
        f"(These links only work while scripts/approval_server.py is running "
        f"on this machine.)"
    )
    msg.add_alternative(
        f"""
        <html><body>
          <p>A new cartoon short is ready for review.</p>
          <p><b>Idea:</b> {idea}<br>
             {video_note}</p>
          <p>
            <a href="{approve_url}" style="padding:8px 16px;background:#2e7d32;color:white;text-decoration:none;border-radius:4px;">Approve</a>
            &nbsp;
            <a href="{reject_url}" style="padding:8px 16px;background:#c62828;color:white;text-decoration:none;border-radius:4px;">Reject</a>
          </p>
          <p style="color:gray;font-size:12px;">These links only work while
          scripts/approval_server.py is running on this machine.</p>
        </body></html>
        """,
        subtype="html",
    )

    if attach_video:
        ctype, _ = mimetypes.guess_type(video_path)
        maintype, subtype = (ctype or "video/mp4").split("/", 1)
        with open(video_path, "rb") as f:
            msg.add_attachment(
                f.read(), maintype=maintype, subtype=subtype,
                filename=os.path.basename(video_path),
            )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_app_password)
        smtp.send_message(msg)

    print(f"[send_approval_email] Sent approval email for {date} to {recipient}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--idea", default="(no idea text provided)")
    args = parser.parse_args()
    send_approval_email(args.date, args.idea)
