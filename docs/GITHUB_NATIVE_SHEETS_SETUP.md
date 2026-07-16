# Setting Up the GitHub-Native Sheets Automation (Apps Script version)

One-time setup for `.github/workflows/generate.yml`'s Sheets-driven flow.
No Google Cloud Console needed — everything happens inside Google Sheets
itself.

## 1. Open the Apps Script editor

1. Open the dashboard spreadsheet: https://docs.google.com/spreadsheets/d/1PrzhIFtDSPpGp1wbemoL_ZZDIRSAhJQKUS1my1vhLNY/edit
2. Menu: **Extensions → Apps Script**. A new tab opens with a blank code editor.

## 2. Paste in the script

1. Delete whatever's in the default `Code.gs` file.
2. Open [`apps_script/Code.gs`](../apps_script/Code.gs) from this repo, copy its entire contents, paste into the Apps Script editor.
3. Near the top, find this line:
   ```
   var SHARED_SECRET = "REPLACE_WITH_A_RANDOM_STRING";
   ```
   Replace `REPLACE_WITH_A_RANDOM_STRING` with any random string of your choosing (e.g. mash the keyboard, or use a password generator) — keep it somewhere, you'll need the exact same value in step 5.
4. Click the **Save** icon (or Ctrl+S).

## 3. Deploy as a Web App

1. Click **Deploy** (top right) → **New deployment**.
2. Click the gear icon next to "Select type" → choose **Web app**.
3. Fill in:
   - Description: anything (e.g. "Pipeline bridge")
   - Execute as: **Me (ai@ms2.co.in)**
   - Who has access: **Anyone**
     *(this sounds scary, but the `SHARED_SECRET` check inside the script means nobody can actually use it without that secret — it's not truly open)*
4. Click **Deploy**.
5. It will ask you to **Authorize access** — click through it: choose your `ai@ms2.co.in` account → you'll likely see a "Google hasn't verified this app" warning (expected, since this is your own personal script, not a published app) → click **Advanced** → **Go to [project name] (unsafe)** → **Allow**.
6. After deploying, copy the **Web app URL** shown (looks like `https://script.google.com/macros/s/AKfycb.../exec`).

## 4. Add the two GitHub secrets

Go to `https://github.com/projects123929/social-media-bot/settings/secrets/actions` → **New repository secret**:

| Name | Value |
|---|---|
| `GAS_WEBAPP_URL` | The Web app URL from step 3.6 |
| `GAS_SHARED_SECRET` | The exact same random string you put in `Code.gs` in step 2.3 |

(These are in addition to your existing `HIGGSFIELD_CREDENTIALS` and `CLAUDE_CODE_OAUTH_TOKEN` secrets.)

## 5. Test it

1. Add a row to the dashboard sheet: Video Title + Aspect Ratio = "Vertical (9:16)".
2. Go to **Actions → Generate cartoon short and request approval → Run workflow** to trigger it immediately instead of waiting up to 20 minutes.
3. Watch the run. If the "Claim a pending row" step fails, double check the secrets match exactly what's in `Code.gs`, and that the deployment's "Execute as" is set to your account.

## If you ever update `Code.gs`

Editing the script alone isn't enough — after any change, go to **Deploy → Manage deployments → (pencil/edit icon) → New version → Deploy** so the live Web App URL picks up the change. The URL itself stays the same across versions.

## Note on the old scheduled-task version

The original Claude-scheduled-task automation (`sheets-pipeline-sync`) is
paused, not deleted, in case this version needs debugging against it later.
Don't re-enable it while this GitHub Actions version is active — both would
try to claim the same sheet rows.
