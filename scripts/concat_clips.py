"""Concatenates multiple video clips into one, using a short crossfade
transition at each cut instead of a hard cut.

Hard-cutting independently-generated AI clips together (even after
re-encoding) tends to read as a stutter/pause at each seam: the clips
often have a near-static settle frame at their very start/end, and
timestamp/keyframe misalignment between separately-encoded segments can
add a stall of its own. A short crossfade (ffmpeg's `xfade`/`acrossfade`
filters) blends over both problems instead of cutting straight across
them.

Usage:
  python scripts/concat_clips.py --out final.mp4 \
      --clips clips/scene1_captioned.mp4 clips/scene2_captioned.mp4 ... \
      [--transition-duration 0.5] [--transition fade]
"""
import argparse
import json
import os
import subprocess


def _probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-show_entries", "format=duration",
         "-of", "json", path],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    return {
        "duration": float(data["format"]["duration"]),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": fps,
    }


def concat_clips(clip_paths, out_path, transition="fade", transition_duration=0.5):
    if len(clip_paths) == 1:
        subprocess.run(
            ["ffmpeg", "-y", "-i", clip_paths[0],
             "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", out_path],
            check=True, capture_output=True, text=True,
        )
        print(f"[concat_clips] Single clip, wrote {out_path} unchanged (no transition needed)")
        return out_path

    probes = [_probe(p) for p in clip_paths]
    # Normalize every clip to the first clip's resolution/fps so xfade
    # never chokes on mismatched inputs from independent generations.
    width, height, fps = probes[0]["width"], probes[0]["height"], probes[0]["fps"]
    durations = [p["duration"] for p in probes]

    if any(d <= transition_duration for d in durations):
        raise ValueError(
            f"transition_duration ({transition_duration}s) must be shorter than "
            f"every clip's duration; got clip durations {durations}"
        )

    inputs = []
    filter_parts = []
    for i, p in enumerate(clip_paths):
        inputs += ["-i", p]
        filter_parts.append(
            f"[{i}:v]fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{i}]"
        )
        filter_parts.append(
            f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]"
        )

    prev_v, prev_a = "v0", "a0"
    cumulative = durations[0]
    for i in range(1, len(clip_paths)):
        offset = cumulative - transition_duration
        out_v, out_a = f"vx{i}", f"ax{i}"
        filter_parts.append(
            f"[{prev_v}][v{i}]xfade=transition={transition}:"
            f"duration={transition_duration}:offset={offset:.3f}[{out_v}]"
        )
        filter_parts.append(f"[{prev_a}][a{i}]acrossfade=d={transition_duration}[{out_a}]")
        prev_v, prev_a = out_v, out_a
        cumulative += durations[i] - transition_duration

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_v}]", "-map", f"[{prev_a}]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(
        f"[concat_clips] Wrote {out_path} — {len(clip_paths)} clips, "
        f"'{transition}' crossfade, {transition_duration}s each, "
        f"~{cumulative:.1f}s total"
    )
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--clips", nargs="+", required=True)
    parser.add_argument("--transition", default="fade",
                         help="ffmpeg xfade transition name (fade, dissolve, wipeleft, slideleft, circleopen, ...)")
    parser.add_argument("--transition-duration", type=float, default=0.5)
    args = parser.parse_args()
    concat_clips(args.clips, args.out, args.transition, args.transition_duration)
