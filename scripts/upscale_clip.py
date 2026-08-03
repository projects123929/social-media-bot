"""Upscales one video clip via Higgsfield's Bytedance Video Upscale model
and downloads the result.

Run this on each scene clip (after caption burn-in, if any) before
concatenation, so captions get upscaled along with the frame instead of
looking undersized on a higher-resolution final video.

Usage:
  python scripts/upscale_clip.py --in clips/scene1_captioned.mp4 \
      --out clips/scene1_upscaled.mp4 [--model-version standard] \
      [--resolution 4k] [--fps 30] [--preset common]
"""
import argparse
import os
import subprocess


def upscale_clip(in_path, out_path, model_version="standard", resolution="4k",
                  fps=30, preset="common"):
    cmd = [
        "higgsfield", "generate", "create", "bytedance_video_upscale",
        "--video-references", in_path,
        "--model_version", model_version,
        "--resolution", resolution,
        "--fps", str(fps),
        "--preset", preset,
        "--wait",
    ]
    print(f"[upscale_clip] Upscaling {in_path} -> {resolution}/{fps}fps/{model_version}...")
    result = subprocess.run(
        cmd, capture_output=True, text=True, shell=(os.name == "nt"),
    )
    if result.returncode != 0:
        raise RuntimeError(f"higgsfield upscale CLI failed:\n{result.stdout}\n{result.stderr}")

    video_url = result.stdout.strip().splitlines()[-1]
    print(f"[upscale_clip] Downloading {video_url}")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run(["curl", "-sL", "-o", out_path, video_url], check=True)
    print(f"[upscale_clip] Saved to {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model-version", default="standard", choices=["standard", "pro"])
    parser.add_argument("--resolution", default="4k", choices=["1080p", "2k", "4k"])
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--preset", default="common",
                         choices=["common", "aigc", "short_series", "ugc", "old_film"])
    args = parser.parse_args()
    upscale_clip(args.in_path, args.out, args.model_version, args.resolution, args.fps, args.preset)
