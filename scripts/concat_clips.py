"""Joins multiple video clips into one file using crossfade transitions
(not a hard concat) - independently-generated scenes often have slightly
different lighting/exposure even with last-frame chaining for continuity,
and a hard cut makes that mismatch obvious. A short crossfade blends each
transition instead of jumping straight across it.

Usage:
  python scripts/concat_clips.py --out final.mp4 \
      --clips clips/scene1.mp4 clips/scene2.mp4 ... [--transition 0.5]
"""
import argparse
import json
import subprocess

TRANSITION_SECONDS_DEFAULT = 0.5


def _duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path],
        check=True, capture_output=True, text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def concat_clips(clip_paths, out_path, transition=TRANSITION_SECONDS_DEFAULT):
    if len(clip_paths) == 1:
        # Nothing to transition between - just re-encode for consistency.
        subprocess.run(
            ["ffmpeg", "-y", "-i", clip_paths[0],
             "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path],
            check=True, capture_output=True, text=True,
        )
        print(f"[concat_clips] Wrote {out_path} (single clip, no transition)")
        return out_path

    durations = [_duration(p) for p in clip_paths]

    inputs = []
    for p in clip_paths:
        inputs += ["-i", p]

    filter_parts = []
    v_label = "0:v"
    a_label = "0:a"
    cumulative = durations[0]
    for i in range(1, len(clip_paths)):
        offset = cumulative - transition
        next_v = f"v{i}"
        next_a = f"a{i}"
        filter_parts.append(
            f"[{v_label}][{i}:v]xfade=transition=fade:duration={transition}:"
            f"offset={offset}[{next_v}]"
        )
        filter_parts.append(
            f"[{a_label}][{i}:a]acrossfade=d={transition}[{next_a}]"
        )
        v_label, a_label = next_v, next_a
        cumulative += durations[i] - transition

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{v_label}]", "-map", f"[{a_label}]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(f"[concat_clips] Wrote {out_path} ({len(clip_paths)} clips, "
          f"{transition}s crossfades)")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--clips", nargs="+", required=True)
    parser.add_argument("--transition", type=float, default=TRANSITION_SECONDS_DEFAULT,
                         help="Crossfade duration in seconds (default: 0.5)")
    args = parser.parse_args()
    concat_clips(args.clips, args.out, args.transition)
