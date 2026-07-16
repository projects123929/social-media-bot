"""Run this ONCE, locally, to obtain a Gmail OAuth refresh token for the
GitHub-native Sheets automation (scripts/gmail_client.py).

Prerequisite: a Google Cloud OAuth 2.0 Client ID (Desktop app type) — see
docs/AUTOMATION_ARCHITECTURE.md for the exact Cloud Console steps. Download
its client secret JSON and pass its path below.

Usage:
  python scripts/gmail_oauth_setup.py --client-secret path/to/client_secret.json

This opens a browser for you to log in as ai@ms2.co.in and approve access,
then prints the three values to save as GitHub secrets: GMAIL_CLIENT_ID,
GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN. It does not save anything to disk.
"""
import argparse
import json

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-secret", required=True, help="Path to the OAuth client secret JSON downloaded from Google Cloud Console")
    args = parser.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(args.client_secret, "r", encoding="utf-8") as f:
        client_info = json.load(f)["installed"]

    print("\nSave these three values as GitHub repository secrets:\n")
    print(f"GMAIL_CLIENT_ID       = {client_info['client_id']}")
    print(f"GMAIL_CLIENT_SECRET   = {client_info['client_secret']}")
    print(f"GMAIL_REFRESH_TOKEN   = {creds.refresh_token}")


if __name__ == "__main__":
    main()
