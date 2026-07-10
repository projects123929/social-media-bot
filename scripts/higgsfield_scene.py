"""Generates one video scene via the Higgsfield CLI and downloads it.

A thin, reusable wrapper so callers (including Claude Code) don't need to
hand-write subprocess/curl calls for every scene.

Usage:
  python scripts/higgsfield_scene.py --prompt "..." --out clips/scene1.mp4 \
      [--model kling3_0_turbo] [--duration 5] [--aspect-ratio 9:16] \
      [--resolution 720p] [--start-image path_or_id]
"""
import argparse
import os
import subprocess


def generate_scene(prompt, out_path, model, duration, aspect_ratio, resolution, start_image=None):
    cmd = [
        "higgsfield", "generate", "create", model,
        "--prompt", prompt,
        "--aspect_ratio", aspect_ratio,
        "--duration", str(duration),
        "--resolution", resolution,
        "--wait",
    ]
    if start_image:
        cmd += ["--start-image", start_image]

    print(f"[higgsfield_scene] Requesting: {prompt[:70]}...")
    result = subprocess.run(
        cmd, capture_output=True, text=True, shell=(os.name == "nt"),
    )
    if result.returncode != 0:
        raise RuntimeError(f"higgsfield CLI failed:\n{result.stdout}\n{result.stderr}")

    video_url = result.stdout.strip().splitlines()[-1]
    print(f"[higgsfield_scene] Downloading {video_url}")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run(["curl", "-sL", "-o", out_path, video_url], check=True)
    print(f"[higgsfield_scene] Saved to {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="kling3_0_turbo")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--resolution", default="720p")
    parser.add_argument("--start-image", default=None)
    args = parser.parse_args()
    generate_scene(
        args.prompt, args.out, args.model, args.duration,
        args.aspect_ratio, args.resolution, args.start_image,
    )
