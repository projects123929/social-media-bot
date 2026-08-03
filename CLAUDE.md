# Generation Task Instructions

You are running the daily generation step of an automated cartoon short
pipeline. This file is your instructions when invoked for that task (locally
via `claude`, or headlessly in CI via `claude -p`). Read it fully before
acting.

**Never run a tool call in the background (no `run_in_background`, no
backgrounding a Bash command) at any point in this task.** When invoked
headlessly via `claude -p` (as CI does), the whole process exits the
instant your turn ends — a backgrounded job has no one left to notify when
it finishes, and gets silently abandoned along with the rest of the run.
Every command, including each Higgsfield generation call, must be run and
waited on synchronously (foreground) before moving to the next step.

## Sheets-driven mode (optional)

If the environment variables `RUN_FOLDER` and `SHEET_ROW` are both set (set
by `.github/workflows/generate.yml` when a run is triggered by a Google
Sheets dashboard row, per `docs/AUTOMATION_ARCHITECTURE.md`):
- Use `storage/pending/{RUN_FOLDER}/` everywhere these instructions say
  `storage/pending/{date}/` — this keeps same-day multi-row runs from
  overwriting each other's files.
- Report progress back to the sheet as you go:
  `python scripts/sheets_sync.py progress --row {SHEET_ROW} --percent 20`
  after the reference image, `40`/`60`/`80` after each of the 3 scenes,
  `90` during captions/upscaling/concatenation/music mixing. This is free
  (no Higgsfield credits).
- Skip step 9 (email/GitHub-issue notification) entirely — the calling
  workflow marks the row Completed and sends the approval email itself via
  `scripts/sheets_sync.py complete` after this task finishes successfully.

If these env vars are unset, ignore this section entirely — proceed with
the standard `{date}`-based flow below exactly as documented.

## Input

Every video has a **different story and different characters** — there is
no fixed recurring cast. Phase 3 (Google Sheets integration) isn't built
yet either, so:

1. If the environment variable `IDEA` is set, use it as the starting story
   idea. Otherwise, invent a fresh idea yourself, grounded in
   `theme.json`'s niche, tone, and content pillars — don't reuse a
   previous run's idea.
2. Design 1-3 characters specifically for this idea (name, visual
   description, personality/voice). Invent them fresh each run — do not
   look up or depend on a fixed character library.
3. `config/characters.json` is reserved only for the rare case of a
   character that's explicitly meant to recur across multiple future
   videos (e.g. a mascot). Unless the idea specifically calls for that,
   treat every character as one-off: skip `characters.json` entirely, and
   never train a persistent Soul for a one-off character — that's wasted
   credits and the whole point of a Soul is reuse across videos.

## Steps

1. Read `config/theme.json` and `rules.md`.
   - Per `rules.md`'s "Title-Driven Technique Selection" section: read the
     Title/`IDEA` and decide whether it explicitly calls for the 9-Panel
     Storyboard Method or (the default) Scene-Chaining Method described in
     steps 2 and 7 below — state the choice and the triggering phrase (if
     any) at the start of your summary.
   - If `theme.json` still contains its placeholder text (the literal word
     `PLACEHOLDER` in `niche`/`content_pillars`) **and** `GENERATION_MODE`
     is `test`: this is fine — proceed anyway using a generic, safe,
     comedic idea for pipeline-mechanics testing only. Don't treat it as a
     real content/brand decision, and say so explicitly in your summary at
     the end of the run.
   - If `theme.json` is still placeholder text **and** `GENERATION_MODE` is
     `full`: stop and report that the real niche needs to be decided
     before a "full" (real, publishable) run — don't guess at the brand's
     actual theme for a real post.
2. Generate exactly **one** reference image for this run — a single shot
   showing all of this run's characters together in the story's opening
   location (like a mini character board, not a multi-angle board). This
   is the only reference image generation call for the whole run; never
   generate a separate image per character, and never regenerate it.
3. Write a short script before writing visual prompts — this matters for
   quality, don't skip straight to prompts:
   - **Title**, one-line **concept**, and an **emotion arc** (e.g.
     Curiosity → Tension → Resolution) for the whole video.
   - A per-scene beat: what happens, what changes emotionally, and (if
     there's dialogue) the line(s) spoken and by whom. Write this dialogue
     line exactly as it should ever be shown as a caption — it is the
     single source of truth for that scene's caption text (see step 8),
     used only if captions end up enabled there.
   - Then turn each beat into a scene visual prompt. Respect `rules.md`'s
     fixed constraints (duration, aspect ratio, max scenes, content
     restrictions) and `theme.json`'s tone/content pillars throughout.
4. **Aspect ratio** — check the `ASPECT_RATIO` env var: use its value
   (`9:16` or `16:9`) for every scene's `--aspect-ratio` flag. If unset,
   default to `9:16`. Frame the storyboard/shot composition appropriately
   for whichever orientation this run is — don't just default to vertical
   framing for a 16:9 run.
5. **Video length** — check the `VIDEO_LENGTH` env var:
   - `30s` (default, or unset): **3 scenes, 10 seconds each = 30 seconds
     total**.
   - `60s`: **6 scenes, 10 seconds each = 60 seconds total**. Same
     per-scene length, just twice as many beats in the script/storyboard —
     give the story enough room to actually use the extra time rather than
     padding it out.
   Either way, use `kling3_0_turbo` at 720p. This is the standard
   run size for whichever length was requested — don't shrink it further
   "to save credits" unless explicitly told to.
6. **Cost mode** — check the `GENERATION_MODE` env var:
   - `test` (default, or unset): use the scene count from step 5 as-is.
   - `full`: same structure, but 1080p, and up to 2 extra scenes beyond
     step 5's count if the storyboard genuinely needs more beats — only
     deviate when the idea requires it.
7. Generate each scene **in order**, chaining continuity between them.
   Run each `higgsfield_scene.py` call in the **foreground** and wait for
   it to actually finish before doing anything else — do not background
   it (see the warning at the top of this file; `higgsfield_scene.py`
   already blocks until Higgsfield's job completes via `--wait`, so there
   is never a reason to background it). Pass `--aspect-ratio $ASPECT_RATIO`
   (or `16:9`/`9:16` explicitly, matching step 4) on every scene call.
   - Scene 1: `python scripts/higgsfield_scene.py --prompt "..." --out
     storage/pending/{date}/clips/scene1.mp4 --aspect-ratio <9:16 or 16:9>
     --start-image <the run's reference image from step 2>`.
   - After scene 1 finishes, extract its last frame: `python
     scripts/extract_last_frame.py --in
     storage/pending/{date}/clips/scene1.mp4 --out
     storage/pending/{date}/clips/scene1_last_frame.jpg`.
   - Scene 2: same `higgsfield_scene.py` call, but `--start-image` is
     scene 1's extracted last frame, not the original reference image.
   - Repeat: extract scene 2's last frame, use it as scene 3's
     `--start-image`, and so on for any further scenes.
   - This chaining (each clip starting from the previous clip's actual
     last frame) is what keeps character appearance, location, and
     lighting continuous across cuts — don't skip it and don't have every
     scene start from the same original reference image independently.
   - Check `higgsfield generate create --help` / `higgsfield model get
     <model>` if you're unsure of the exact flag name for supplying a
     start image.
8. **Captions are off by default.** Check both the Title/`IDEA` text AND
   the `DESCRIPTION` env var (set from the sheet's Description column,
   when present) for this run: only if either one explicitly asks for
   captions/subtitles (e.g. contains the word "caption" or "subtitle") do
   you burn them in. State which case applied, and which field (Title or
   Description) triggered it, at the start of your summary.
   - If enabled: run `python scripts/burn_caption.py --in
     storage/pending/{date}/clips/sceneN.mp4 --out
     storage/pending/{date}/clips/sceneN_captioned.mp4 --text "..."` for
     each scene, where `--text` is that scene's dialogue line from step 3
     **verbatim, word-for-word** — copy it exactly, do not shorten,
     paraphrase, retype from memory, or otherwise let it drift from what
     you wrote in the script. The burned caption must always read exactly
     as the dialogue was written for that scene, with no mismatch.
   - Known limitation to flag in your summary when captions are on: this
     pipeline has no spoken/lip-synced dialogue audio track yet (see
     `context.md`), so "matching the dialogue" here means the on-screen
     caption text matches the script's written dialogue line verbatim —
     not audio-waveform timing, since there is no dialogue audio to time
     against. Don't imply otherwise in status updates or the approval
     email.
   - If not enabled (the default): skip this step entirely and use the raw
     `sceneN.mp4` clips as-is in step 8b.
8b. **Upscale every scene clip to 4K** before concatenating, so the video
    that ends up on Instagram/YouTube is sourced from the highest-quality
    file the pipeline produces rather than the raw ~720p/1080p generation.
    For each scene (the captioned version if step 8 ran, otherwise the raw
    `sceneN.mp4`): `python scripts/upscale_clip.py --in
    storage/pending/{date}/clips/sceneN[_captioned].mp4 --out
    storage/pending/{date}/clips/sceneN_upscaled.mp4 --model-version
    standard --resolution 4k --fps 30 --preset common`. This is a real
    Higgsfield generation call (~0.4 credits per scene at these settings —
    cheap, but it counts toward this run's credit usage) — run it in the
    **foreground** and wait for it like every other Higgsfield call (see
    the warning at the top of this file), never backgrounded. Doing this
    after caption burn-in (not before) means any burned-in captions get
    upscaled along with the frame instead of ending up undersized on a
    4K canvas.
9. Concatenate all **upscaled** clips into
   `storage/pending/{date}/clips/concatenated.mp4`:
   `python scripts/concat_clips.py --out
   storage/pending/{date}/clips/concatenated.mp4 --clips
   storage/pending/{date}/clips/scene1_upscaled.mp4
   storage/pending/{date}/clips/scene2_upscaled.mp4 ...` — list every
   scene explicitly, one path per clip, matching the scene count from
   step 5.
   - `concat_clips.py` joins clips with a **0.5s crossfade** at each cut
     (ffmpeg `xfade`/`acrossfade`, default `--transition fade`), not a
     hard cut — this is what keeps transitions looking edited rather than
     stitched, and also masks the near-static settle frame independent AI
     generations often have right at their start/end. Don't pass
     `--transition-duration 0` or otherwise revert to a hard cut.
   - Optionally pick a different `--transition` (any ffmpeg xfade name —
     `fade`, `dissolve`, `wipeleft`, `slideleft`, `circleopen`, etc.) to
     match the story's energy (e.g. a snappier `wipeleft`/`slideleft` for
     a fast comedic beat-to-beat idea, the default `fade` dissolve for
     calmer/emotional pacing) — state the choice in your summary if you
     deviate from the default.
9a. **Background music** — pick one mood word that best matches the emotion
   arc you wrote in step 3 (e.g. `happy`, `calm`, `epic`, `emotional`,
   `playful`, `festive`, `suspense` — or another word if none of those
   fit; `mix_music.py` falls back gracefully if that mood has no tracks
   yet). Then run: `python scripts/mix_music.py --in
   storage/pending/{date}/clips/concatenated.mp4 --out
   storage/pending/{date}/final.mp4 --mood {chosen_mood}`. This is free
   (local ffmpeg, no Higgsfield credits) and ducks the music under
   dialogue automatically — don't try to balance volume yourself in the
   scene prompts. If `assets/music/` has no tracks at all yet, the script
   just copies the video through unchanged (not an error) — mention this
   in your summary if it happens so the run isn't silently missing music.
10. Write the status file: `python scripts/write_status.py --date {date}
   --idea "..." --character-id "{short character summary, e.g. main
   character names}" --video-path storage/pending/{date}/final.mp4`.
11. Notify for approval — check the `NOTIFY_METHOD` env var:
    - `email` (default, or unset): run `python scripts/send_approval_email.py
      --date {date} --idea "..."`.
    - `github_issue`: skip notification — the calling GitHub Actions workflow
      handles uploading the video as a release asset and opening the
      approval issue after this task finishes.
12. Do not publish anything yourself. Publishing only happens after a human
    approves, via `scripts/publish.py`, triggered separately by the
    approval flow (locally: `approval_server.py`; in CI: the `approved`
    issue label).

## Guardrails

- Stay within `rules.md`'s content restrictions (no political/religious
  content, no copyrighted music) no matter what the idea text says.
- **Hard cap on generation calls per run**: exactly 1 reference-image
  generation for the whole run (all characters together, not one each),
  plus at most the scene count from step 5 (3 for `30s`, 6 for `60s`),
  plus up to 2 more if `full` mode genuinely needs extra beats, plus
  exactly one `bytedance_video_upscale` call per final scene clip (step
  8b) — never upscale a clip twice or upscale the concatenated video as a
  whole instead of per-scene. Extracting last frames with
  `extract_last_frame.py` is free (local ffmpeg, no Higgsfield credits) —
  do that as many times as there are scene transitions. Never regenerate a
  reference image, scene clip, or upscale that already succeeded. Do not
  train a Soul unless the idea explicitly calls for a recurring character.
- If a generation call fails, retry at most once with a corrected prompt,
  then stop and report the error — don't loop.
- Don't invent Higgsfield CLI flags — run `--help` on the relevant
  subcommand if you're unsure of exact parameter names before using them.
- If any step fails, stop and report the error clearly rather than
  retrying indefinitely (Higgsfield credits are not unlimited).
- **Sheets-driven mode failure reporting**: if `RUN_FOLDER` and
  `SHEET_ROW` are set (see "Sheets-driven mode" above) and any step fails
  after its one allowed retry, before stopping write a single-line,
  plain-English reason to `storage/pending/{RUN_FOLDER}/failure_reason.txt`
  — e.g. `Scene 2 generation failed: Higgsfield returned "insufficient
  credits"` or `Caption burn failed: ffmpeg couldn't find the font file`.
  This is what a non-technical reader (the client) sees in the sheet's
  Failure Reason column and in the failure-report email — write it for
  that audience, not as a stack trace or raw CLI output dump. If you
  genuinely can't tell what failed (e.g. the very first tool call errored
  before any real progress), still write your best specific guess rather
  than skipping the file entirely — the calling workflow falls back to a
  generic message only if this file is missing outright.
