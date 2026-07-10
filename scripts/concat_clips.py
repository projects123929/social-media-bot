"""Concatenates multiple video clips (same codec/resolution) into one file.

Usage:
  python scripts/concat_clips.py --out final.mp4 \
      --clips clips/scene1_captioned.mp4 clips/scene2_captioned.mp4 ...
"""
import argparse
import os
import subprocess


def concat_clips(clip_paths, out_path):
    run_dir = os.path.dirname(os.path.abspath(out_path))
    concat_list_path = os.path.join(run_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", concat_list_path, "-c", "copy", out_path],
        check=True, capture_output=True, text=True,
    )
    print(f"[concat_clips] Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--clips", nargs="+", required=True)
    args = parser.parse_args()
    concat_clips(args.clips, args.out)
