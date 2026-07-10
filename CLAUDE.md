# Generation Task Instructions

You are running the daily generation step of an automated cartoon short
pipeline. This file is your instructions when invoked for that task (locally
via `claude`, or headlessly in CI via `claude -p`). Read it fully before
acting.

## Input

Phase 3 (Google Sheets integration) isn't built yet, so there is no sheet row
to pull from. Use these, in priority order:

1. If the environment variables `IDEA` and `CHARACTER_ID` are set, use those.
2. Otherwise, use this placeholder test idea (clearly a stand-in, keep it
   cheap — see "Cost mode" below):
   - Idea: "A cheerful fox discovers a giant pancake in the forest and
     shares it with friends."
   - Character ID: `dummy_fox`

## Steps

1. Read `config/theme.json`, `rules.md`, and `config/characters.json`.
2. Look up the character by `character_id` in `config/characters.json`.
   - If `soul_id` is `null` and `recurring` is `true`: this character should
     get a persistent Soul. Use the `higgsfield` CLI (`higgsfield soul-id
     --help` to see the exact subcommand and required inputs) to train one
     from the character's `visual_description`, then edit
     `config/characters.json` to save the returned `soul_id` back onto that
     character's entry. This file change should be committed (in CI, the
     workflow handles committing; locally, just leave it modified and tell
     the user to commit it).
   - If `soul_id` is `null` and `recurring` is `false`: generate exactly
     **one** reference image (a single shot, not a multi-angle board) for
     consistency within this single video. Do not edit `characters.json`.
   - If `soul_id` is already set: reuse it directly. Never regenerate a
     Soul or reference image that already exists — that's wasted credits.
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
   --out storage/pending/{date}/clips/sceneN.mp4 [--start-image ...]`
   (pass the character's soul_id/reference image so scenes stay visually
   consistent — check `higgsfield generate create --help` and `higgsfield
   model get <model>` for the right flag if unsure).
6. Burn each scene's caption: `python scripts/burn_caption.py --in
   storage/pending/{date}/clips/sceneN.mp4 --out
   storage/pending/{date}/clips/sceneN_captioned.mp4 --text "..."`.
7. Concatenate all captioned clips into the final video:
   `python scripts/concat_clips.py --out storage/pending/{date}/final.mp4
   --clips storage/pending/{date}/clips/scene1_captioned.mp4 ...`.
8. Write the status file: `python scripts/write_status.py --date {date}
   --idea "..." --character-id {character_id} --video-path
   storage/pending/{date}/final.mp4`.
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
- In `test` cost mode, never exceed 2 scenes / 5 seconds each — this step
  spends real Higgsfield credits.
- **Hard cap on generation calls per run**: at most 1 Soul/reference-image
  generation per character per run (0 if the character already has a
  `soul_id` or you already generated its reference image earlier in this
  same run), plus at most 3 video generations (the standard 3x10s
  structure) or 5 if `full` mode genuinely needs more scenes. Do not
  generate "just in case" extra takes, alternate angles, or retries of a
  clip that already succeeded.
- If a generation call fails, retry at most once with a corrected prompt,
  then stop and report the error — don't loop.
- Don't invent Higgsfield CLI flags — run `--help` on the relevant
  subcommand if you're unsure of exact parameter names before using them.
- If any step fails, stop and report the error clearly rather than
  retrying indefinitely (Higgsfield credits are not unlimited).
