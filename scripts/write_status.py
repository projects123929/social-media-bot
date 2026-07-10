"""Writes storage/pending/{date}/status.json in the schema the approval
scripts (send_approval_email.py, approval_server.py, open_approval_issue.py)
expect. Use this instead of hand-writing the JSON to avoid schema drift.

Usage:
  python scripts/write_status.py --date 2026-07-10 --idea "..." \
      --character-id dummy_fox --video-path storage/pending/2026-07-10/final.mp4
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_config import PIPELINE_ROOT

PENDING_DIR = os.path.join(PIPELINE_ROOT, "storage", "pending")


def write_status(date, idea, character_id, video_path):
    run_dir = os.path.join(PENDING_DIR, date)
    os.makedirs(run_dir, exist_ok=True)
    status = {
        "date": date,
        "idea": idea,
        "character_id": character_id,
        "status": "Generated",
        "video_path": video_path,
        "token": None,
    }
    status_path = os.path.join(run_dir, "status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
    print(f"[write_status] Wrote {status_path}")
    return status_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--idea", required=True)
    parser.add_argument("--character-id", required=True)
    parser.add_argument("--video-path", required=True)
    args = parser.parse_args()
    write_status(args.date, args.idea, args.character_id, args.video_path)
