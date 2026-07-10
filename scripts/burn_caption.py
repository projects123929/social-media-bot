"""Burns a caption into a video clip using ffmpeg drawtext.

Usage:
  python scripts/burn_caption.py --in clips/scene1.mp4 \
      --out clips/scene1_captioned.mp4 --text "Caption text here"
"""
import argparse
import subprocess


def burn_caption(in_path, out_path, caption_text):
    font_path = "C\\:/Windows/Fonts/arial.ttf" if _on_windows() else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    escaped_text = caption_text.replace("'", "'").replace(":", "\\:")
    drawtext = (
        f"drawtext=fontfile='{font_path}':text='{escaped_text}':"
        f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h-th-80"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", in_path, "-vf", drawtext, "-c:a", "copy", out_path],
        check=True, capture_output=True, text=True,
    )
    print(f"[burn_caption] Wrote {out_path}")
    return out_path


def _on_windows():
    import os
    return os.name == "nt"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--text", required=True)
    args = parser.parse_args()
    burn_caption(args.in_path, args.out, args.text)
