"""One-time local setup: runs the OAuth consent flow for YouTube uploads
and saves the resulting refresh token to config/youtube_token.json.

Run this once, locally, logged in as the channel owner:
  python scripts/youtube_oauth_setup.py

Needs config/youtube_client_secret.json (downloaded from Google Cloud
Console) to already exist. Neither file is committed to git.
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

PIPELINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRET_PATH = os.path.join(PIPELINE_ROOT, "config", "youtube_client_secret.json")
TOKEN_PATH = os.path.join(PIPELINE_ROOT, "config", "youtube_token.json")


def main():
    if not os.path.exists(CLIENT_SECRET_PATH):
        raise FileNotFoundError(
            f"Missing {CLIENT_SECRET_PATH}. Download the OAuth client's "
            f"JSON from Google Cloud Console and save it there first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
    credentials = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "refresh_token": credentials.refresh_token,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "token_uri": credentials.token_uri,
        }, f, indent=2)

    print(f"Saved refresh token to {TOKEN_PATH}")
    print("Next: copy this file's contents into the YOUTUBE_TOKEN GitHub secret.")


if __name__ == "__main__":
    main()
