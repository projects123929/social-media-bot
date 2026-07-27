"""Phase 6 publishing flow.

Triggered only after an Approve action (locally: approval_server.py;
in CI: .github/workflows/publish.yml on the 'approved' issue label).

Both Instagram (Graph API) and YouTube (Data API v3) are wired up.
"""
import argparse
import io
import json
import os
import time

import requests

GRAPH_API_VERSION = "v25.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 300


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


def publish_to_instagram(video_url, caption):
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    ig_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    if not (access_token and ig_account_id):
        return {
            "platform": "instagram",
            "success": False,
            "error": "INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ACCOUNT_ID not set",
        }

    # Instagram deprecated the "VIDEO" media_type entirely - all video
    # posts (any aspect ratio) must use REELS now, confirmed by Instagram's
    # own API error: "The VIDEO value for media_type is deprecated. Use
    # the REELS media type to publish a video to your Instagram feed."
    media_type = "REELS"

    # 1. Create the media container.
    create_resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media",
        data={
            "video_url": video_url,
            "caption": caption,
            "media_type": media_type,
            "access_token": access_token,
        },
        timeout=60,
    )
    create_data = create_resp.json()
    if "id" not in create_data:
        return {"platform": "instagram", "success": False, "error": create_data}
    creation_id = create_data["id"]

    # 2. Poll until the container finishes processing.
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    status_code = None
    while time.time() < deadline:
        status_resp = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=30,
        )
        status_data = status_resp.json()
        status_code = status_data.get("status_code")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            return {"platform": "instagram", "success": False, "error": status_data}
        time.sleep(POLL_INTERVAL_SECONDS)
    else:
        return {
            "platform": "instagram", "success": False,
            "error": f"Timed out waiting for container to finish (last status: {status_code})",
        }

    # 3. Publish it.
    publish_resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=60,
    )
    publish_data = publish_resp.json()
    if "id" not in publish_data:
        return {"platform": "instagram", "success": False, "error": publish_data}
    media_id = publish_data["id"]

    # 4. Fetch the permalink for confirmation/logging.
    detail_resp = requests.get(
        f"{GRAPH_API_BASE}/{media_id}",
        params={"fields": "permalink", "access_token": access_token},
        timeout=30,
    )
    permalink = detail_resp.json().get("permalink")

    return {
        "platform": "instagram", "success": True,
        "media_id": media_id, "permalink": permalink,
    }


def publish_to_youtube(video_url, title, description):
    token_json = os.environ.get("YOUTUBE_TOKEN")
    if not token_json:
        return {"platform": "youtube", "success": False, "error": "YOUTUBE_TOKEN not set"}

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        token_data = json.loads(token_json)
        credentials = Credentials(
            token=None,
            refresh_token=token_data["refresh_token"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            token_uri=token_data["token_uri"],
        )

        video_resp = requests.get(video_url, timeout=120)
        video_resp.raise_for_status()
        media = MediaIoBaseUpload(
            io.BytesIO(video_resp.content), mimetype="video/mp4", resumable=True,
        )

        youtube = build("youtube", "v3", credentials=credentials)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "categoryId": "24",  # Entertainment
                },
                "status": {"privacyStatus": "public"},
            },
            media_body=media,
        )
        response = None
        while response is None:
            _, response = request.next_chunk()

        video_id = response["id"]
        return {
            "platform": "youtube", "success": True,
            "video_id": video_id,
            "permalink": f"https://youtube.com/shorts/{video_id}",
        }
    except Exception as e:
        return {"platform": "youtube", "success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--video-path", default=None)
    parser.add_argument("--video-url", default=None,
                         help="Publicly fetchable URL of the approved video "
                              "(required for Instagram)")
    parser.add_argument("--caption", default="")
    args = parser.parse_args()

    results = []

    if args.video_url:
        results.append(publish_to_instagram(args.video_url, args.caption))
        results.append(publish_to_youtube(args.video_url, args.caption, args.caption))
    else:
        results.append({
            "platform": "instagram", "success": False,
            "error": "No --video-url provided (Instagram/YouTube need a public URL, not a local path)",
        })

    lines = [f"Publish results for {args.date}:"]
    for r in results:
        if r["success"]:
            lines.append(f"- {r['platform']}: posted — {r.get('permalink', r.get('media_id'))}")
        else:
            lines.append(f"- {r['platform']}: FAILED — {r['error']}")
    message = "\n".join(lines)

    print(f"[publish] {message}")
    comment_on_issue(message)


if __name__ == "__main__":
    main()
