"""Phase 4 generation flow - test mode.

Uses a hardcoded test idea (Phase 3 / Google Sheets not wired up yet).
Reads theme.json, rules.md's fixed constraints, and the character from
characters.json, builds a short storyboard, generates each scene via the
Higgsfield CLI, assembles them with ffmpeg (captions burned in), saves the
final video, writes status.json, and sends the approval email.

Run with: python scripts/generate.py
"""
import json
import os
import subprocess
import sys
from datetime import date as date_cls

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_config import load_env, PIPELINE_ROOT

CONFIG_DIR = os.path.join(PIPELINE_ROOT, "config")
PENDING_DIR = os.path.join(PIPELINE_ROOT, "storage", "pending")

# Test-mode hardcoded input (stands in for a Google Sheet row until Phase 3).
TEST_IDEA = (
    "A cheerful fox discovers a giant pancake in the forest and shares it "
    "with friends."
)
TEST_CHARACTER_ID = "dummy_fox"

# Kept short (2 short scenes instead of the full 5-scene/30-35s spec) to
# minimize Higgsfield credit usage while validating the pipeline mechanics.
TEST_SCENES = [
    {
        "prompt": (
            "A cheerful orange cartoon fox stumbles upon a giant golden "
            "pancake in a sunny forest clearing, eyes wide with excitement, "
            "simple flat cartoon style"
        ),
        "caption": "The fox finds a GIANT pancake!",
    },
    {
        "prompt": (
            "The same cheerful orange cartoon fox joyfully invites forest "
            "animal friends over and they all share the giant pancake "
            "together, laughing, simple flat cartoon style"
        ),
        "caption": "Sharing is caring!",
    },
]

MODEL = "kling3_0_turbo"
DURATION = 5
ASPECT_RATIO = "9:16"
RESOLUTION = "720p"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_character(character_id):
    characters = load_json(os.path.join(CONFIG_DIR, "characters.json"))
    for c in characters:
        if c["id"] == character_id:
            return c
    raise ValueError(f"Character '{character_id}' not found in characters.json")


def run_higgsfield_scene(prompt, out_path):
    print(f"[generate] Requesting clip: {prompt[:70]}...")
    result = subprocess.run(
        [
            "higgsfield", "generate", "create", MODEL,
            "--prompt", prompt,
            "--aspect_ratio", ASPECT_RATIO,
            "--duration", str(DURATION),
            "--resolution", RESOLUTION,
            "--wait",
        ],
        capture_output=True, text=True, shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"higgsfield CLI failed:\n{result.stdout}\n{result.stderr}")
    video_url = result.stdout.strip().splitlines()[-1]
    print(f"[generate] Downloading {video_url}")
    subprocess.run(
        ["curl", "-sL", "-o", out_path, video_url],
        check=True,
    )
    return out_path


def burn_caption(in_path, out_path, caption_text):
    font_path = "C\\:/Windows/Fonts/arial.ttf"
    escaped_text = caption_text.replace("'", "’").replace(":", "\\:")
    drawtext = (
        f"drawtext=fontfile='{font_path}':text='{escaped_text}':"
        f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h-th-80"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", in_path, "-vf", drawtext,
         "-c:a", "copy", out_path],
        check=True, capture_output=True, text=True,
    )
    return out_path


def concat_clips(clip_paths, out_path, run_dir):
    concat_list_path = os.path.join(run_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", concat_list_path, "-c", "copy", out_path],
        check=True, capture_output=True, text=True,
    )
    return out_path


def main():
    load_env()
    character = get_character(TEST_CHARACTER_ID)
    print(f"[generate] Using character: {character['name']} ({character['id']})")

    today = date_cls.today().isoformat()
    run_dir = os.path.join(PENDING_DIR, today)
    clips_dir = os.path.join(run_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    raw_clips = []
    captioned_clips = []
    for i, scene in enumerate(TEST_SCENES, start=1):
        raw_path = os.path.join(clips_dir, f"scene{i}.mp4")
        run_higgsfield_scene(scene["prompt"], raw_path)
        raw_clips.append(raw_path)

        captioned_path = os.path.join(clips_dir, f"scene{i}_captioned.mp4")
        burn_caption(raw_path, captioned_path, scene["caption"])
        captioned_clips.append(captioned_path)

    final_path = os.path.join(run_dir, "final.mp4")
    concat_clips(captioned_clips, final_path, run_dir)
    print(f"[generate] Final video assembled: {final_path}")

    status = {
        "date": today,
        "idea": TEST_IDEA,
        "character_id": TEST_CHARACTER_ID,
        "status": "Generated",
        "video_path": final_path,
        "token": None,
    }
    with open(os.path.join(run_dir, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    print("[generate] Sending approval email...")
    subprocess.run(
        [sys.executable, os.path.join(PIPELINE_ROOT, "scripts", "send_approval_email.py"),
         "--date", today, "--idea", TEST_IDEA],
        check=True,
    )
    print("[generate] Done.")


if __name__ == "__main__":
    main()
