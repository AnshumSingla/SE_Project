# Setup (college-only, multi-user)

Any `thapar.edu` Google account can sign in. Nobody else can. Google access is done by the
server; the browser only holds a signed token that proves who you are.

## How it works
- Each user's Google refresh token is stored **encrypted** (one file per user) in a hidden, app-only
  folder of the **admin's** Google Drive (the "vault"). The encryption key lives only in the server
  environment, so the Drive files alone are useless. No database, no extra storage account.
- Each user's profile and scan state live in **their own** Drive (same hidden app folder).
- A scheduler calls `/api/cron/scan`; the server scans each user in turn (least recently scanned first),
  isolated from the others, with a time budget and a per-run user cap.
- "Delete my data" on the profile card removes the token, profile and state and revokes access.

Honest trade-off: the admin's server can, technically, read every user's Gmail in the background.
Tell users (the landing page already says so), keep the key safe, and don't log mail content.

## 1. Google Cloud Console (once)
1. APIs & Services -> Library: enable **Gmail API**, **Google Calendar API**, **Google Drive API**.
2. OAuth consent screen: User type **Internal** (this is what your project already uses: it is owned by
   the thapar.edu organization). Internal apps need no verification, show no "unverified" warning,
   have no 100-user cap and their refresh tokens do not expire after 7 days.
   Add the scopes `gmail.readonly`, `calendar`, `drive.appdata`.
3. Credentials -> your OAuth client: Authorized redirect URI = `BACKEND_URL/auth/google/callback`.
4. Internal also means **only thapar.edu accounts work**; personal Gmail accounts cannot sign in.
   If Thapar's Workspace admins restrict third-party apps, they must allow this client ID.
   When the admin account leaves the college, the vault (and the app) stops: plan a successor.

## 2. Environment variables (see `.env.template`)
Backend: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_DOMAIN` (default `thapar.edu`),
`ADMIN_EMAIL` (your thapar.edu address), `SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `CRON_SECRET`,
`BACKEND_URL`, `FRONTEND_URL`, optional `GEMINI_API_KEY` + `GEMINI_MODEL`, `CRON_MAX_USERS`.
Generate keys with:
- `SECRET_KEY`: `python -c "import secrets;print(secrets.token_hex(32))"`
- `TOKEN_ENCRYPTION_KEY`: `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`
  (to rotate: put the new key first, old key second, comma-separated; later drop the old one)
Frontend: `VITE_API_BASE_URL` = the backend URL.

## 3. First sign-in (vault bootstrap, admin only)
1. Leave `GOOGLE_REFRESH_TOKEN` empty, deploy, open the site, sign in as `ADMIN_EMAIL`.
2. The popup shows a one-time page with the admin's refresh token. Put it in `GOOGLE_REFRESH_TOKEN`
   (the vault lives in that account's Drive), redeploy, sign in again.
3. Other students can sign in only after this step.

## 4. Background scan
Copy `deploy/github-scan-workflow.yml` to `.github/workflows/scan.yml` in the repo root and add two
repository secrets: `BACKEND_URL` and `CRON_SECRET` (same value as on the backend).
It calls `/api/cron/scan` every 15 minutes. Test it once with "Run workflow".
GitHub pauses scheduled workflows in repositories with no activity for 60 days.
Capacity: each run handles up to `CRON_MAX_USERS` (default 50) users within ~45 s; with more users,
the ones waited longest go first. Add a second scheduler or raise limits as the user count grows.
Gemini's free quota is shared by all users: when it runs out, extraction falls back to the rule-based reader.

## 5. Security clean-up (do this before anything else)
These files were committed to git and must be treated as leaked:
`backend/gmail_token.json`, `backend/calendar_token.json`, and any `client_secret*.json` / `credentials.json`.
1. Revoke the app at https://myaccount.google.com/permissions and create a new OAuth client secret.
2. `git rm --cached` the files, commit, and purge history (`git filter-repo` or BFG) if the repo was ever public.
3. The root `.gitignore` and `backend/.dockerignore` keep them out from now on.

## 6. Files that are no longer used (safe to delete)
Old/duplicate code: `api_service_new.py`, `main.py`, `api_only_demo.py`, `api_client_demo.py`,
`oauth_handler.py`, `user_management.py` (SQLite + local key file), `verify_requirements.py`,
`requirements_full.txt`.
Old tests and notes that describe removed behaviour: `test_api_filtering.py`, `test_cors_delete.py`,
`test_delete_endpoint.py`, `test_delete_reminder.py`, `test_duplicate_fix.py`, `test_filtering_system.py`,
`test_system.py`, and the `*_FIX*.md`, `*_SUMMARY.md`, `TOKEN_REFRESH_GUIDE.md`, `OAUTH_FIX_INSTRUCTIONS.md` files.
Run the real tests with: `python -m unittest discover -s tests`.
