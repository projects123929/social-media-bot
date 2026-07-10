"""Opens a GitHub Issue for approval (used in CI instead of email).

Requires env vars (auto-provided in GitHub Actions, or set manually):
  GITHUB_TOKEN       - a token with 'issues: write' permission
  GITHUB_REPOSITORY  - "owner/repo"

Usage:
  python scripts/open_approval_issue.py --date 2026-07-10 \
      --idea "..." --video-url "https://github.com/.../releases/download/..."
"""
import argparse
import os
import sys

import requests


def open_approval_issue(date, idea, video_url):
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]

    title = f"Video ready for approval - {date}"
    body = (
        f"A new cartoon short is ready for review.\n\n"
        f"**Idea:** {idea}\n"
        f"**Date:** {date}\n"
        f"**Video:** {video_url}\n\n"
        f"---\n"
        f"To approve, add the `approved` label to this issue.\n"
        f"To reject, add the `rejected` label (or just close this issue).\n"
    )

    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"title": title, "body": body, "labels": ["pending-approval"]},
        timeout=30,
    )
    resp.raise_for_status()
    issue = resp.json()
    print(f"[open_approval_issue] Opened issue #{issue['number']}: {issue['html_url']}")
    return issue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--idea", required=True)
    parser.add_argument("--video-url", required=True)
    args = parser.parse_args()
    open_approval_issue(args.date, args.idea, args.video_url)
