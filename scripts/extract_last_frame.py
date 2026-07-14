"""Extracts the last frame of a video as a still image (for chaining into
the next scene's --start-image, so consecutive clips stay visually
continuous without spending extra Higgsfield credits).

Usage:
  python scripts/extract_last_frame.py --in clips/scene1.mp4 --out clips/scene1_last_frame.jpg
"""
import argparse
import subprocess


def extract_last_frame(in_path, out_path):
    subprocess.run(
        ["ffmpeg", "-y", "-sseof", "-1", "-i", in_path,
         "-frames:v", "1", "-q:v", "2", out_path],
        check=True, capture_output=True, text=True,
    )
    print(f"[extract_last_frame] Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    extract_last_frame(args.in_path, args.out)
