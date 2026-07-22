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
  `90` during captions/concatenation. This is free (no Higgsfield credits).
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
     there's dialogue) the line(s) spoken and by whom.
   - Then turn each beat into a scene visual prompt and a short on-screen
     caption line. Respect `rules.md`'s fixed constraints (duration,
     aspect ratio, max scenes, content restrictions) and `theme.json`'s
     tone/content pillars throughout.
4. **Aspect ratio** — check the `ASPECT_RATIO` env var: use its value
   (`9:16` or `16:9`) for every scene's `--aspect-ratio` flag. If unset,
   default to `9:16`. Frame the storyboard/shot composition appropriately
   for whichever orientation this run is — don't just default to vertical
   framing for a 16:9 run.
5. **Cost mode** — check the `GENERATION_MODE` env var:
   - `test` (default, or unset): **3 scenes, 10 seconds each = 30 seconds
     total**, using `kling3_0_turbo` at 720p. This is the standard
     run size — matches `rules.md`'s 30-35s target exactly, so don't
     shrink it further "to save credits" unless explicitly told to.
   - `full`: same 3-scenes-of-10s structure, but 1080p and/or up to 5
     scenes if the storyboard genuinely needs more beats — only deviate
     from the 3x10s default when the idea requires it.
6. Generate each scene **in order**, chaining continuity between them.
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
7. Burn each scene's caption: `python scripts/burn_caption.py --in
   storage/pending/{date}/clips/sceneN.mp4 --out
   storage/pending/{date}/clips/sceneN_captioned.mp4 --text "..."`.
8. Concatenate all captioned clips into the final video:
   `python scripts/concat_clips.py --out storage/pending/{date}/final.mp4
   --clips storage/pending/{date}/clips/scene1_captioned.mp4 ...`.
9. Write the status file: `python scripts/write_status.py --date {date}
   --idea "..." --character-id "{short character summary, e.g. main
   character names}" --video-path storage/pending/{date}/final.mp4`.
10. Notify for approval — check the `NOTIFY_METHOD` env var:
    - `email` (default, or unset): run `python scripts/send_approval_email.py
      --date {date} --idea "..."`.
    - `github_issue`: skip notification — the calling GitHub Actions workflow
      handles uploading the video as a release asset and opening the
      approval issue after this task finishes.
11. Do not publish anything yourself. Publishing only happens after a human
    approves, via `scripts/publish.py`, triggered separately by the
    approval flow (locally: `approval_server.py`; in CI: the `approved`
    issue label).

## Guardrails

- Stay within `rules.md`'s content restrictions (no political/religious
  content, no copyrighted music) no matter what the idea text says.
- **Hard cap on generation calls per run**: exactly 1 reference-image
  generation for the whole run (all characters together, not one each),
  plus at most 3 video generations (the standard 3x10s structure) or 5 if
  `full` mode genuinely needs more scenes. Extracting last frames with
  `extract_last_frame.py` is free (local ffmpeg, no Higgsfield credits) —
  do that as many times as there are scene transitions. Never regenerate a
  reference image or clip that already succeeded. Do not train a Soul
  unless the idea explicitly calls for a recurring character.
- If a generation call fails, retry at most once with a corrected prompt,
  then stop and report the error — don't loop.
- Don't invent Higgsfield CLI flags — run `--help` on the relevant
  subcommand if you're unsure of exact parameter names before using them.
- If any step fails, stop and report the error clearly rather than
  retrying indefinitely (Higgsfield credits are not unlimited).
