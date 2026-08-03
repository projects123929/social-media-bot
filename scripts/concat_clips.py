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
    # Re-encode (not "-c copy" stream-copy) - each clip comes from a
    # separate, independently-encoded Higgsfield generation, and
    # stream-copying them together is prone to seam artifacts (a brief
    # freeze/pause or audio glitch right at each cut) from inconsistent
    # keyframe alignment/timestamps between clips. Re-encoding forces
    # ffmpeg to produce clean, continuous timestamps across the whole
    # video instead.
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", out_path],
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
