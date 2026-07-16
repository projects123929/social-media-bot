# Setting Up the GitHub-Native Sheets Automation

This is the one-time credential setup for `.github/workflows/sheet_generate.yml`
and `.github/workflows/check_approvals.yml`. Two Google Cloud credentials
are needed: a **service account** (for the Sheet) and an **OAuth client**
(for Gmail — a service account cannot send/read mail as a personal inbox).

## 1. Create a Google Cloud project (skip if you already have one)

1. Go to https://console.cloud.google.com/
2. Top-left project dropdown → **New Project** → name it (e.g.
   "cartoon-pipeline") → **Create**.

## 2. Enable the two APIs

1. In the Cloud Console search bar, search **"Google Sheets API"** → **Enable**.
2. Search **"Gmail API"** → **Enable**.

## 3. Create the Service Account (for Sheets)

1. Search **"Service Accounts"** → **Create Service Account**.
2. Name it anything (e.g. "sheets-automation") → **Create and Continue** →
   **Done** (no roles needed at the project level).
3. Click into the new service account → **Keys** tab → **Add Key** →
   **Create new key** → type **JSON** → **Create**. A `.json` file downloads.
4. Open that file, copy its **entire contents**.
5. Copy the service account's **email address** (looks like
   `sheets-automation@your-project.iam.gserviceaccount.com`, shown on its
   details page).
6. Open the dashboard sheet, click **Share**, paste that email address in,
   give it **Editor** access, uncheck "Notify people", click **Share**.

## 4. Create the OAuth Client (for Gmail)

1. In Cloud Console, go to **APIs & Services → OAuth consent screen**.
   - User type: **External** (unless you have a Workspace org that allows Internal).
   - Fill in the required fields (app name, your email) → **Save and Continue** through the rest.
   - Under **Test users**, add `ai@ms2.co.in` (required while the app is in "Testing" mode).
2. Go to **APIs & Services → Credentials** → **Create Credentials** →
   **OAuth client ID**.
   - Application type: **Desktop app**.
   - Name it anything → **Create**.
   - Click **Download JSON** on the new client — save it locally, e.g.
     `client_secret.json`.

## 5. Get the Gmail refresh token (run once, locally)

```powershell
cd "C:\Users\ASUS\MS2\Yt Automation\extracted\social-media-bot-main"
pip install -r requirements.txt
python scripts/gmail_oauth_setup.py --client-secret "C:\path\to\client_secret.json"
```

This opens a browser — **log in as `ai@ms2.co.in`** and approve access.
The terminal then prints three values:

```
GMAIL_CLIENT_ID       = ...
GMAIL_CLIENT_SECRET   = ...
GMAIL_REFRESH_TOKEN   = ...
```

## 6. Add all four secrets to GitHub

Go to `https://github.com/projects123929/social-media-bot/settings/secrets/actions`
→ **New repository secret**, once each for:

| Secret name | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | The full JSON content from step 3.4 |
| `GMAIL_CLIENT_ID` | From step 5's output |
| `GMAIL_CLIENT_SECRET` | From step 5's output |
| `GMAIL_REFRESH_TOKEN` | From step 5's output |

(In addition to the `HIGGSFIELD_CREDENTIALS` and `CLAUDE_CODE_OAUTH_TOKEN`
secrets already required by the original `generate.yml`.)

## 7. Test it

1. Add a row to the dashboard sheet (Video Title + Aspect Ratio = "Vertical (9:16)").
2. Go to **Actions → Sheets-driven video generation → Run workflow** to trigger
   it immediately instead of waiting up to 20 minutes.
3. Watch the run logs. If it fails at the "Claim a pending row" step, the
   service account likely doesn't have Editor access to the sheet — recheck
   step 3.6.

## Avoiding double-processing

If the original Claude-scheduled-task version (`sheets-pipeline-sync`) is
still running, **disable it** before relying on this version — both read/
write the same sheet and could otherwise both claim the same row. Pause it
from the Scheduled section of the Claude app, or ask Claude to disable it.
