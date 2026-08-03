# Project Context — Automated Cartoon Short Video Pipeline

Snapshot of what's been built, why, and what's left. See `PROJECT_BRIEF.md`
(parent folder) for the original spec this deviates from in places — see
"Deviations from the original brief" below for what changed and why.

Repo: https://github.com/projects123929/social-media-bot

---

## Goal

Pull an idea from a source (originally: Google Sheets), generate a ~30-35s
cartoon short via Higgsfield, send it for human approval, then publish to
Instagram and YouTube Shorts. Runs unattended on a schedule, no human
present except to click Approve/Reject.

---

## Status by phase

### Phase 1 — Environment setup: done
- Node.js, Claude Code CLI, project folder structure all confirmed working.
- Higgsfield: no official MCP server exists (`@higgsfield/mcp-server` isn't
  a real package). Using the official `@higgsfield/cli` instead, shelled
  out to via subprocess.
- ffmpeg installed for assembly/captions.
- One important lesson learned mid-project: the assistant's own Bash/
  PowerShell tool calls run in an environment that does **not** reliably
  share global installs (npm global packages, winget installs) with the
  user's real machine, even though it *does* share the actual project
  folder (it's on OneDrive). Anything that needs to exist on the real
  machine (CLI tools, auth) should be run by the user directly, not
  inferred from the assistant's own tool output.

### Phase 2 — Config files: partially done
- `rules.md` — now a generic, reusable production-pipeline template
  (English), covering fixed constraints (30-35s, 9:16, ≤5 scenes, burned
  captions, content restrictions) plus a 9-panel-storyboard/start-end-frame
  methodology reference (not fully implemented in code yet — see
  "Known gaps" below).
- `config/theme.json` — **still placeholder** (niche/tone/content pillars
  not decided). `CLAUDE.md` explicitly blocks "full" (real/publishable)
  generation runs until this is filled in for real; "test" mode runs are
  allowed to proceed with a generic placeholder idea for pipeline-mechanics
  testing only.
- `config/characters.json` — intentionally empty (`[]`). See deviation
  below: every video has different characters, so there's no fixed
  character library. This file is reserved only for the rare
  explicitly-recurring character (e.g. a mascot), which hasn't come up yet.

### Phase 3 — Google Sheets integration: deferred
Not started. Generation currently gets its idea either from an `IDEA` env
var or invents one itself (see Phase 4).

### Phase 4 — Generation flow: done (Claude-Code-orchestrated)
- `CLAUDE.md` contains the real generation instructions, run either
  interactively (`claude`, locally) or headlessly (`claude -p
  --dangerously-skip-permissions`, in CI).
- Claude Code itself does the creative work each run: invents an idea
  (grounded in `theme.json`), designs 1-3 one-off characters, writes a
  short script (title/concept/emotion arc/per-scene beats), then turns
  that into visual prompts.
- Continuity: one reference image is generated for the whole run (all
  characters together), used as the `--start-image` for scene 1. After
  each scene, its last frame is extracted locally via ffmpeg
  (`scripts/extract_last_frame.py`, free — no Higgsfield credits) and used
  as the next scene's `--start-image`, so clips chain visually instead of
  each starting independently from the same reference image.
- Standard run size: 3 scenes × 10 seconds = 30 seconds total,
  `kling3_0_turbo`, 720p, 9:16 (`GENERATION_MODE=test`). `full` mode allows
  1080p and up to 5 scenes.
- Reusable helper scripts Claude calls instead of hand-writing subprocess/
  ffmpeg logic each run:
  - `scripts/higgsfield_scene.py` — generate + download one scene
  - `scripts/extract_last_frame.py` — extract a clip's last frame
  - `scripts/burn_caption.py` — burn a caption via ffmpeg drawtext
  - `scripts/concat_clips.py` — stitch clips into the final video with a
    0.5s crossfade at each cut (xfade/acrossfade), not a hard cut
  - `scripts/write_status.py` — write `storage/pending/{date}/status.json`
    in the schema the approval scripts expect
- Hard credit-usage guardrails are written into `CLAUDE.md`: exactly 1
  reference image per run, ≤3 (or ≤5 in full mode) video generations, no
  regenerating anything that already succeeded, at most one retry on
  failure.

### Phase 5 — Approval: done, two parallel mechanisms
- **Local/interactive**: email-based (your choice, replacing the brief's
  Telegram plan). `scripts/send_approval_email.py` sends the video as a
  Gmail attachment (sender: a personal Gmail account with an App Password,
  since the Workspace account `ai@ms2.co.in` has app passwords disabled by
  admin policy) with Approve/Reject links pointing at
  `scripts/approval_server.py`, a local HTTP listener you run in a
  separate terminal (`python scripts/approval_server.py`). Confirmed
  working end-to-end once the server is actually running.
- **CI/cloud**: GitHub Issues-based (chosen over a webhook-relay + email
  approach — fewer moving parts, no third-party service, access control is
  just repo permissions). `scripts/open_approval_issue.py` opens an issue
  with the idea + a link to the video (uploaded as a GitHub Release asset
  by the workflow, not committed into git history). You approve by adding
  the `approved` label to the issue (or `rejected` to reject).
  - Known open issue: GitHub's own email notification for new issues
    didn't arrive in testing — likely a repo "Watch" setting
    (needs "All Activity") or personal GitHub notification-email setting,
    not a pipeline bug. Not yet fixed/confirmed.

### Phase 6 — Publishing: stubbed, blocked on external account setup
- `scripts/publish.py` exists but is currently a stub — logs/comments what
  it *would* publish, doesn't actually post anywhere yet.
- **Instagram**: requires a Business/Creator account linked to a Facebook
  Page (hard Meta API requirement, not configurable around). In progress:
  new Instagram account being set up for testing; a company Facebook
  account will be used (avoiding the personal-account phone-number-conflict
  issue hit earlier) — paused pending access to that.
- **YouTube**: not started. Needs a Google Cloud project + YouTube Data
  API v3 + OAuth credentials. Deliberately sequenced after Instagram per
  your instruction.
- `.github/workflows/publish.yml` — triggers on the `approved` issue label,
  downloads the video from the release, calls `publish.py`. Ready to wire
  up real Instagram/YouTube logic once those accounts exist.

### Phase 7 — Cloud deployment: reworked from the brief's VPS plan to GitHub Actions
- **Why**: same "runs unattended, no human intervention" goal as the
  brief's VPS plan, but free (private repo: 2,000 free Actions minutes/
  month, comfortably covers one video/day) instead of renting a VPS.
- `.github/workflows/generate.yml` — scheduled daily (06:00 UTC cron) +
  manual `workflow_dispatch` for testing. Installs Node/Python/ffmpeg/
  Higgsfield CLI/Claude Code CLI on a fresh Ubuntu runner each time,
  restores Higgsfield credentials from a secret, runs `claude -p
  --dangerously-skip-permissions` to do the actual generation, commits
  `characters.json` back if Claude trained a new Soul, uploads the final
  video as a GitHub Release asset, opens the approval issue.
- `.github/workflows/publish.yml` — triggers on `approved` label, runs the
  (currently stubbed) publish step.
- **Auth mechanisms figured out for headless/CI use** (this took a few
  iterations):
  - Higgsfield CLI only supports interactive browser OAuth login — no
    static API key exposed via the CLI itself (a separate official
    `@higgsfield/client` Node SDK does support static Key ID/Secret keys,
    but no "API Keys" section was found on the account's dashboard to
    generate one). Workaround: the CLI's local credentials file
    (`~/.config/higgsfield/credentials.json`, contains `access_token` +
    `refresh_token` + `expires_at`) is stored as a GitHub secret
    (`HIGGSFIELD_CREDENTIALS`) and restored before each run; the CLI
    refreshes the access token itself using the refresh token. Not yet
    confirmed whether the refresh token rotates on use (if it does, the
    secret will eventually need re-syncing — not yet automated).
  - Claude Code: `claude setup-token` produces a long-lived
    `CLAUDE_CODE_OAUTH_TOKEN` (requires an active Claude subscription),
    generated once locally and stored as a GitHub secret. Not regenerated
    per run.
- Required secrets on the repo: `HIGGSFIELD_CREDENTIALS`,
  `CLAUDE_CODE_OAUTH_TOKEN`. Required labels: `pending-approval`,
  `approved`, `rejected`.
- **Note**: the repo was recreated once (`projects123929/social-media-bot`,
  replacing an earlier repo that became unreachable) — secrets and labels
  had to be re-added on the new repo.
- First successful headless end-to-end run (video generated, release
  uploaded, approval issue opened) confirmed working, after fixing: an
  invalid `CLAUDE_CODE_OAUTH_TOKEN` secret (re-entered, fixed), and
  incorrect `pipeline/...` path prefixes in both workflow files (the git
  repo root is the `pipeline` folder itself, not a parent folder containing
  it — paths needed to drop that prefix).

---

## Deviations from the original brief (and why)

| Brief said | Actually built | Why |
|---|---|---|
| Higgsfield MCP server | Official `@higgsfield/cli` via subprocess | `@higgsfield/mcp-server` package doesn't exist |
| Telegram approval bot | Email (local) / GitHub Issues (CI) | Your choice; Telegram never built |
| Fixed character library per sheet row | Claude invents idea + characters fresh every run | Every video has different characters/story, by your instruction |
| VPS for cloud deployment | GitHub Actions (scheduled workflow) | Free (within Actions minutes), no server to maintain; only real limitation is no persistent process, solved by using GitHub Issues instead of a long-running approval server in the cloud path |
| Fixed Python script does generation | Claude Code (via `CLAUDE.md`) does generation, calling small Python helper scripts as tools | You clarified Claude Code itself should do idea/prompt/storyboard generation, not a static script |

---

## Known gaps / things not yet done

- `theme.json` is still a placeholder — needs a real niche/tone/content
  pillars decision before any "full" (real, publishable) run.
- `rules.md`'s full 9-panel-storyboard-image + separate-video-chunk
  methodology is documented but **not implemented** — the actual
  `CLAUDE.md` flow is a lighter version (one combined reference image +
  frame-chaining between scenes, not a full 9-panel image storyboard with
  image-to-video per 3-panel group). This was a deliberate sequencing
  choice (get the simpler pipeline working end-to-end first); revisit if
  quality still isn't good enough after the continuity/script-structure
  improvements just made.
- No lip-synced dialogue — spoken/lip-synced dialogue audio isn't
  implemented, despite `rules.md`'s template describing that. Burned-in
  captions are now off by default too (only added when the sheet's Video
  Title/`IDEA` explicitly asks for captions/subtitles).
- GitHub Issue email notifications not confirmed working (separate from
  the pipeline itself — a GitHub notification-settings question).
- Instagram: blocked on Facebook Page / Meta Developer App setup (company
  account, in progress).
- YouTube: not started (Google Cloud project + OAuth credentials needed).
- `publish.py` is a stub — no real posting logic yet for either platform.
- Phase 3 (Google Sheets) not started — `IDEA` env var or Claude's own
  invention is the only input source right now.
- Higgsfield refresh-token rotation behavior in CI is unconfirmed — if it
  turns out to rotate, the `HIGGSFIELD_CREDENTIALS` secret will need an
  automated re-sync step (requires a GitHub PAT with secret-write
  permission, since the default Actions token can't modify secrets).

---

## Where things live

- Repo root = `pipeline/` folder contents (not the parent
  `social_media_bot_new` folder — that's just the local OneDrive path
  this was developed in).
- `CLAUDE.md` — generation task instructions (the actual "brain" of Phase 4)
- `rules.md` — fixed constraints + generic production methodology template
- `config/theme.json`, `config/characters.json` — see gaps above
- `config/.env` (local only, gitignored) — Gmail credentials for local
  email approval
- `scripts/` — all helper scripts (generation, approval, publishing stub)
- `.github/workflows/generate.yml`, `.github/workflows/publish.yml` — the
  two CI workflows
- `storage/pending/{date}/` — per-run output (clips, final video,
  status.json) — gitignored, not committed
