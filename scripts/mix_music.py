"""Mixes a mood-matched background music track under a video's existing
dialogue audio, with the music volume automatically ducked (sidechain
compression keyed off the dialogue track) whenever someone is speaking, and
back up in gaps - not just a flat quiet level for the whole video.

Tracks live in assets/music/{mood}/*.mp3 (see assets/music/README.md for
how to add them - manually downloaded from the YouTube Audio Library, since
there is no public API for that catalog). The mood is chosen by the caller
(the generation step, based on the video's actual emotion arc/story), not
guessed here.

If the requested mood folder is missing/empty, falls back to any track in
assets/music/ (any subfolder). If there are no tracks at all anywhere,
copies the video through unchanged rather than failing the run.

Usage:
  python scripts/mix_music.py --in concatenated.mp4 --out final.mp4 \
      --mood happy [--music-dir assets/music] [--track assets/music/happy/song.mp3]
"""
import argparse
import glob
import json
import os
import random
import shutil
import subprocess

MUSIC_BASE_VOLUME = 0.45  # level in gaps/no dialogue
DUCK_THRESHOLD = 0.04     # dialogue level above which ducking kicks in
DUCK_RATIO = 12           # how hard the music gets pulled down under dialogue


def _probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path],
        check=True, capture_output=True, text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def _tracks_in(directory):
    return sorted(
        glob.glob(os.path.join(directory, "*.mp3"))
        + glob.glob(os.path.join(directory, "*.m4a"))
        + glob.glob(os.path.join(directory, "*.wav"))
    )


def _pick_track(music_dir, mood):
    if mood:
        mood_tracks = _tracks_in(os.path.join(music_dir, mood))
        if mood_tracks:
            return random.choice(mood_tracks)
        print(f"[mix_music] No tracks in assets/music/{mood}/ - falling back to any available mood.")

    all_tracks = []
    for sub in sorted(glob.glob(os.path.join(music_dir, "*"))):
        if os.path.isdir(sub):
            all_tracks += _tracks_in(sub)
    all_tracks += _tracks_in(music_dir)  # also allow flat files directly in assets/music/
    return random.choice(all_tracks) if all_tracks else None


def mix_music(in_path, out_path, music_dir="assets/music", mood=None, track=None):
    chosen_track = track or _pick_track(music_dir, mood)
    if not chosen_track:
        print(f"[mix_music] No music tracks found under {music_dir} - copying video through without music.")
        shutil.copyfile(in_path, out_path)
        return out_path

    video_duration = _probe_duration(in_path)
    print(f"[mix_music] mood={mood!r} track={chosen_track}")

    # [1:a] = looped/trimmed music, raised to base volume.
    # sidechaincompress ducks it whenever [0:a] (dialogue) is loud, then it
    # recovers to base volume in gaps - real volume sync, not a flat level.
    filter_complex = (
        f"[1:a]volume={MUSIC_BASE_VOLUME},atrim=0:{video_duration},asetpts=PTS-STARTPTS[music];"
        f"[0:a]asplit=2[dia][dia_key];"
        f"[music][dia_key]sidechaincompress="
        f"threshold={DUCK_THRESHOLD}:ratio={DUCK_RATIO}:attack=20:release=400:makeup=1[music_ducked];"
        f"[dia][music_ducked]amix=inputs=2:duration=first:dropout_transition=3:weights=1 1[aout]"
    )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", in_path,
            "-stream_loop", "-1", "-i", chosen_track,
            "-filter_complex", filter_complex,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-shortest",
            out_path,
        ],
        check=True, capture_output=True, text=True,
    )
    print(f"[mix_music] Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--music-dir", default="assets/music")
    parser.add_argument("--mood", default=None,
                         help="Mood subfolder to pick from, e.g. happy/calm/epic/emotional/playful/festive/suspense")
    parser.add_argument("--track", default=None, help="Use this specific track instead of picking by mood")
    args = parser.parse_args()
    mix_music(args.in_path, args.out, args.music_dir, args.mood, args.track)
