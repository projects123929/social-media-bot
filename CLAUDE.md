# Generation Task Instructions

You are running the daily generation step of an automated cartoon short
pipeline. This file is your instructions when invoked for that task (locally
via `claude`, or headlessly in CI via `claude -p`). Read it fully before
acting.

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
2. For each character in this run's story, generate exactly **one**
   reference image (a single shot, not a multi-angle board) for
   consistency within this single video's scenes. Never regenerate a
   reference image that already exists earlier in this same run.
3. Write a scene-by-scene storyboard for the idea:
   - Respect `rules.md`'s fixed constraints (duration, aspect ratio, max
     scenes, content restrictions).
   - Match `theme.json`'s tone and content pillars.
   - Each scene needs a short visual prompt (for Higgsfield) and a short
     on-screen caption line.
4. **Cost mode** — check the `GENERATION_MODE` env var:
   - `test` (default, or unset): **3 scenes, 10 seconds each = 30 seconds
     total**, using `kling3_0_turbo` at 720p, 9:16. This is the standard
     run size — matches `rules.md`'s 30-35s target exactly, so don't
     shrink it further "to save credits" unless explicitly told to.
   - `full`: same 3-scenes-of-10s structure, but 1080p and/or up to 5
     scenes if the storyboard genuinely needs more beats — only deviate
     from the 3x10s default when the idea requires it.
5. Generate each scene: `python scripts/higgsfield_scene.py --prompt "..."
   --out storage/pending/{date}/clips/sceneN.mp4 --start-image <reference>`
   (pass each character's one-off reference image so they stay visually
   consistent across this video's scenes — check `higgsfield generate
   create --help` and `higgsfield model get <model>` for the right flag if
   unsure).
6. Burn each scene's caption: `python scripts/burn_caption.py --in
   storage/pending/{date}/clips/sceneN.mp4 --out
   storage/pending/{date}/clips/sceneN_captioned.mp4 --text "..."`.
7. Concatenate all captioned clips into the final video:
   `python scripts/concat_clips.py --out storage/pending/{date}/final.mp4
   --clips storage/pending/{date}/clips/scene1_captioned.mp4 ...`.
8. Write the status file: `python scripts/write_status.py --date {date}
   --idea "..." --character-id "{short character summary, e.g. main
   character names}" --video-path storage/pending/{date}/final.mp4`.
9. Notify for approval — check the `NOTIFY_METHOD` env var:
   - `email` (default, or unset): run `python scripts/send_approval_email.py
     --date {date} --idea "..."`.
   - `github_issue`: skip notification — the calling GitHub Actions workflow
     handles uploading the video as a release asset and opening the
     approval issue after this task finishes.
10. Do not publish anything yourself. Publishing only happens after a human
    approves, via `scripts/publish.py`, triggered separately by the
    approval flow (locally: `approval_server.py`; in CI: the `approved`
    issue label).

## Guardrails

- Stay within `rules.md`'s content restrictions (no political/religious
  content, no copyrighted music) no matter what the idea text says.
- **Hard cap on generation calls per run**: at most 1 reference-image
  generation per character (max 3 characters → max 3 reference images),
  plus at most 3 video generations (the standard 3x10s structure) or 5 if
  `full` mode genuinely needs more scenes. Never regenerate a reference
  image or clip that already succeeded. Do not train a Soul unless the
  idea explicitly calls for a recurring character.
- If a generation call fails, retry at most once with a corrected prompt,
  then stop and report the error — don't loop.
- Don't invent Higgsfield CLI flags — run `--help` on the relevant
  subcommand if you're unsure of exact parameter names before using them.
- If any step fails, stop and report the error clearly rather than
  retrying indefinitely (Higgsfield credits are not unlimited).
