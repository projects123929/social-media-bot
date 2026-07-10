"""Phase 6 publishing flow - stub.

Triggered only after an Approve action (locally: approval_server.py;
in CI: .github/workflows/publish.yml on the 'approved' issue label).

Instagram (Graph API) and YouTube (Data API v3) upload logic go here once:
  - Instagram: Business account is linked to a Facebook Page, and a
    Meta Developer App + Page Access Token exist.
  - YouTube: a Google Cloud project with YouTube Data API v3 enabled and
    OAuth credentials exist for the target channel.

Until then, this just logs what it would have done so the rest of the
pipeline (generation -> approval) can be exercised end-to-end.
"""
import argparse
import os

import requests


def comment_on_issue(message):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    issue_number = os.environ.get("ISSUE_NUMBER")
    if not (token and repo and issue_number):
        return  # running locally, not in the CI issue-based flow
    requests.post(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"body": message},
        timeout=30,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--video-path", default=None)
    args = parser.parse_args()

    message = (
        f"Publish step stub reached for {args.date} "
        f"(video: {args.video_path or '(local status.json path)'}).\n\n"
        f"Instagram and YouTube upload are not wired up yet:\n"
        f"- Instagram needs the Business account linked to a Facebook Page "
        f"and a Meta Developer App (in progress).\n"
        f"- YouTube needs a Google Cloud project + OAuth credentials "
        f"(not started).\n\n"
        f"No post was published."
    )
    print(f"[publish] {message}")
    comment_on_issue(message)


if __name__ == "__main__":
    main()
