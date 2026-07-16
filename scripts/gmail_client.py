"""Thin Gmail API wrapper for sending approval-request emails and reading replies.

Auth: OAuth2 refresh token (NOT an App Password — the ai@ms2.co.in Workspace
account has App Passwords disabled by admin policy; OAuth is unaffected by
that restriction). Obtain the refresh token once locally via
scripts/gmail_oauth_setup.py, then store GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
GMAIL_REFRESH_TOKEN as GitHub secrets.
"""
import base64
import os
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]
REVIEWER = "ai@ms2.co.in"


def _service():
    creds = Credentials(
        None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("gmail", "v1", credentials=creds)


def send_html_email(subject: str, html_body: str, to: str = REVIEWER):
    svc = _service()
    msg = MIMEText(html_body, "html")
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()


def _extract_plain_text(payload):
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="replace")
    for part in payload.get("parts", []):
        text = _extract_plain_text(part)
        if text:
            return text
    return ""


def check_reply(subject_contains: str):
    """Searches for a thread whose subject contains subject_contains, and returns
    'approve', 'reject', or None (no reply yet, or reply doesn't match either keyword).
    Only looks at replies (messages after the first one in the thread)."""
    svc = _service()
    query = f'subject:"{subject_contains}" newer_than:7d'
    results = svc.users().messages().list(userId="me", q=query, maxResults=5).execute()
    messages = results.get("messages", [])
    if not messages:
        return None

    thread_ids = set()
    for m in messages:
        full = svc.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
        thread_ids.add(full["threadId"])

    for thread_id in thread_ids:
        thread = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
        msgs = thread.get("messages", [])
        if len(msgs) < 2:
            continue  # only the original outbound message, no reply yet
        reply = msgs[-1]
        body = _extract_plain_text(reply["payload"]).strip().lower()
        if body.startswith("approve"):
            return "approve"
        if body.startswith("reject"):
            return "reject"
    return None
