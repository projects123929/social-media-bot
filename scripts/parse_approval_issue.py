"""Extracts date and video URL from an approval issue's title/body.

Used by .github/workflows/publish.yml (issue title/body -> GITHUB_OUTPUT).
"""
import argparse
import json
import re
import sys


def parse(title, body):
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title) or re.search(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", body)
    video_match = re.search(r"\*\*Video:\*\*\s*(\S+)", body)

    if not date_match or not video_match:
        print("Could not parse date/video URL from issue.", file=sys.stderr)
        sys.exit(1)

    return date_match.group(1), video_match.group(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", required=True, help="JSON-encoded issue body string")
    args = parser.parse_args()

    body_text = json.loads(args.body)
    date, video_url = parse(args.title, body_text)
    print(f"date={date}")
    print(f"video_url={video_url}")
