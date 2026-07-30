# Background music library (mood-tagged)

`scripts/mix_music.py` mixes a track from this folder under every
generated video's dialogue, with the music volume automatically ducked
(via sidechain compression keyed off the dialogue track) whenever someone
is speaking, and back up in the gaps.

The generation step (`CLAUDE.md`) picks a **mood** from the video's actual
story/emotion arc - not randomly - then asks for a track from that mood's
subfolder. If a mood folder is empty, it falls back to any other track;
if there are no tracks anywhere yet, videos are produced without music
(not an error).

## Folder layout

```
assets/music/
  happy/
  calm/
  epic/
  emotional/
  playful/
  festive/
  suspense/
```

Add more mood subfolders anytime - just create the folder and drop tracks
in; `CLAUDE.md` isn't restricted to only this list, it names whatever mood
fits the story (these are just the starter set).

## Adding tracks (one-time per track, manual - no public API for this exists)

There is no programmatic way to search/download the YouTube Audio Library
catalog - it's a manual web UI only. To seed a mood folder:

1. Go to YouTube Studio's audio library: https://studio.youtube.com →
   left sidebar → **Audio Library**.
2. Filter by mood/genre matching one of the folders above (e.g. "Happy",
   "Calm") - pick tracks with **no attribution required** unless you're
   OK adding a credit line to video descriptions.
3. Download the MP3 and drop it into the matching `assets/music/{mood}/`
   folder.
4. Commit it to the repo (small MP3s, a few MB each, are fine to commit
   normally - no need to add them to `.gitignore`).

The more tracks per mood, the more variety (one is picked at random
within the chosen mood each run). Even 2-3 tracks per mood is enough to
start - add more over time.
