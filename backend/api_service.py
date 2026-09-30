"""
Email Reminder API Service

Flask-based API service that provides endpoints for the web/mobile app
to interact with the AutoGen email processing system.
"""

from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests
import urllib.parse
import secrets
import html
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import traceback

# Gemini AI
try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. Run: pip install google-generativeai")

# Load environment variables
load_dotenv()

# Import our email processing system
import auth
import core
import scanner
from core import make_event_id, EVENT_SOURCE   # make_event_id re-exported for tests
from relevance import normalize_profile
from drive_store import DriveStore, PROFILE_FILE, STATE_FILE
from vault import TokenVault
from complete_system import IntegratedEmailReminderSystem

# Load environment variables
load_dotenv()

app = Flask(__name__)

# SECRET_KEY signs the API tokens handed to the browser. Without one, tokens would
# stop working on every restart / serverless instance, so set it in production.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    print("⚠️ SECRET_KEY not set - using a random key (logins will not survive a restart)")
    SECRET_KEY = secrets.token_hex(32)
app.secret_key = SECRET_KEY

# Flask's session cookie only carries the short-lived OAuth `state` (first-party popup).
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = (os.environ.get('BACKEND_URL') or '').startswith('https://')

# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    os.environ.get('FRONTEND_URL', '').rstrip('/'),
    os.environ.get('VITE_FRONTEND_URL', '').rstrip('/')
]
# Remove empty strings
ALLOWED_ORIGINS = [origin for origin in ALLOWED_ORIGINS if origin]

# Enable CORS with credentials and explicit methods
CORS(app, 
     origins=ALLOWED_ORIGINS, 
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Google OAuth Configuration (Manual - No Authlib!)
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
# Use environment variable for redirect URI (NO FALLBACK - must be set in production)
BACKEND_URL = os.environ.get('BACKEND_URL')
if not BACKEND_URL:
    print("⚠️ BACKEND_URL not set in environment. Defaulting to http://localhost:5000 for local development.")
    BACKEND_URL = 'http://localhost:5000'
REDIRECT_URI = f"{BACKEND_URL.rstrip('/')}/auth/google/callback"
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.appdata'   # profile/settings in the user's own Drive
]

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers (credentials, deterministic event IDs, error handling)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_TIMEZONE = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Kolkata')
_PLACEHOLDER_TOKENS = {'', 'demo_token_for_testing', 'demo_access_token', 'server_auth_token'}



_creds_cache = {}          # sub -> Credentials (google-auth refreshes access tokens itself)
_admin_creds = None


def _make_credentials(refresh_token):
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        token_uri=GOOGLE_TOKEN_URL,
        scopes=SCOPES,
    )


def admin_credentials():
    """Admin's credentials (from GOOGLE_REFRESH_TOKEN): used only to reach the token vault in the admin's Drive."""
    global _admin_creds
    rt = os.environ.get('GOOGLE_REFRESH_TOKEN')
    if not rt:
        return None
    if _admin_creds is None or _admin_creds.refresh_token != rt:
        _admin_creds = _make_credentials(rt)
    return _admin_creds


def _vault():
    creds = admin_credentials()
    if not creds:
        raise ValueError('GOOGLE_REFRESH_TOKEN (vault owner) is not configured')
    return TokenVault(_drive_store(_ensure_valid_credentials(creds)))


def forget_user(sub):
    _creds_cache.pop(sub, None)


def user_credentials(claims):
    """Google credentials for a signed-in user, from the vault. None if they have none stored."""
    sub = claims['sub']
    if sub in _creds_cache:
        return _creds_cache[sub]
    if claims.get('email', '').lower() == auth.admin_email() and admin_credentials():
        creds = admin_credentials()
    else:
        entry = _vault().get(sub)
        if not entry:
            return None
        creds = _make_credentials(entry['refresh_token'])
    _creds_cache[sub] = creds
    return creds


def current_user():
    """Claims of the signed-in user (from the Authorization header) or None."""
    return auth.verify_token(SECRET_KEY, request.headers.get('Authorization'))


def resolve_credentials(*_ignored):
    """
    Google credentials for THIS request's user: looked up server-side from the signed
    token. Credentials sent by the client (body, query string) are ignored; the
    parameters exist only for old call sites.
    """
    claims = current_user()
    return user_credentials(claims) if claims else None


def _server_error(e: Exception, status: int = 500):
    """Log the traceback server-side; never leak it to the client."""
    print(f"❌ {type(e).__name__}: {e}")
    traceback.print_exc()
    return jsonify({"success": False, "error": "Internal server error"}), status


def _clamp_int(value, low, high, default=None):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default if default is not None else low


def _calendar_service(credentials):
    from googleapiclient.discovery import build
    return build('calendar', 'v3', credentials=credentials, cache_discovery=False)


def _drive_store(credentials):
    from googleapiclient.discovery import build
    return DriveStore(build('drive', 'v3', credentials=credentials, cache_discovery=False))


def _load_profile(credentials):
    """Profile from the user's Drive, or None. Never raises: a missing scope or a
    Drive outage must not break scanning (mails just stay unfiltered)."""
    try:
        return _drive_store(credentials).load(PROFILE_FILE)
    except Exception as e:
        print(f"⚠️ profile unavailable: {type(e).__name__}")
        return None


def _is_scope_error(e: Exception) -> bool:
    status = getattr(getattr(e, 'resp', None), 'status', None)
    return status in (401, 403)


def _new_system(credentials):
    """
    Build a fresh processing system for ONE request. Never share a system (or
    its Gmail client / processed-ID cache) between requests: the previous global
    instance let one user's credentials and state leak into another's request.
    """
    from gmail_integration import GmailIntegrator
    system = IntegratedEmailReminderSystem(use_llm=False, connect=False)
    system.gmail = GmailIntegrator(credentials=credentials)
    return system


# Everything except these needs a valid signed-in user token. The cron endpoint has its own
# shared-secret check. One gate here means a new route can't be left open by accident.
PUBLIC_PATHS = {'/health', '/auth/google', '/auth/google/callback', '/api/cron/scan'}


@app.before_request
def require_login():
    if request.method == 'OPTIONS' or request.path in PUBLIC_PATHS:
        return None
    if not current_user():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    return None


@app.after_request
def after_request(response):
    """Ensure CORS headers are set on all responses"""
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/auth/google')
def google_login():
    """Start Google sign-in (opened in a popup by the frontend)."""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    params = {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'state': state,
        'access_type': 'offline',   # we need a refresh token for background scanning
        'prompt': 'consent',
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")


def _popup_page(title: str, body_html: str, message: Optional[Dict] = None) -> str:
    """Tiny result page. The message goes ONLY to the configured frontend origin."""
    frontend = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
    script = ''
    if message is not None:
        script = ("<script>if (window.opener) { window.opener.postMessage(%s, %s); setTimeout(() => window.close(), 800); }</script>"
                  % (json.dumps(message).replace('<', '\\u003c'), json.dumps(frontend)))
    return f"<!DOCTYPE html><html><head><title>{html.escape(title)}</title></head><body style=\"font-family:Arial;padding:40px;text-align:center\">{body_html}{script}</body></html>"


@app.route('/auth/google/callback')
def google_callback():
    """Finish sign-in. Only allowed accounts (college domain / listed emails) get a token.
    Google secrets and refresh tokens stay on the server."""
    try:
        if not request.args.get('state') or request.args.get('state') != session.pop('oauth_state', None):
            raise ValueError('Invalid state')
        code = request.args.get('code')
        if not code:
            raise ValueError('No authorization code received')

        token_response = requests.post(GOOGLE_TOKEN_URL, data={
            'code': code,
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code',
        }, timeout=15)
        token_response.raise_for_status()
        token = token_response.json()

        info = requests.get(GOOGLE_USERINFO_URL, headers={'Authorization': f"Bearer {token.get('access_token')}"}, timeout=15)
        info.raise_for_status()
        user = info.json()
        email, sub = (user.get('email') or '').lower(), user.get('id')

        if not sub or not auth.is_allowed(email, user.get('hd')) or user.get('verified_email') is False:
            print(f"⛔ sign-in refused for {email}")
            return _popup_page('Not allowed', f'<h2>This app is for {html.escape(auth.allowed_domain())} accounts.</h2>',
                               {'success': False, 'error': 'This account is not allowed'}), 403

        refresh = token.get('refresh_token')

        # Bootstrap: the vault lives in the admin's Drive and needs the admin's refresh token in the
        # environment. Show it ONCE to the admin (never via postMessage); everyone else is told to wait.
        if not admin_credentials():
            if email == auth.admin_email() and refresh:
                return _popup_page('One-time setup', (
                    '<h2>One-time setup</h2><p>Set this as <code>GOOGLE_REFRESH_TOKEN</code> in the server '
                    'environment, redeploy, then sign in again. Do not share it.</p>'
                    f'<textarea readonly rows="4" cols="60">{html.escape(refresh)}</textarea>'))
            return _popup_page('Not ready', '<h2>The app is not set up yet.</h2><p>Please try again later.</p>',
                               {'success': False, 'error': 'The app is not set up yet'}), 503

        vault = _vault()
        if refresh:
            vault.put(sub, email, refresh)
            forget_user(sub)                      # pick up the fresh token
        elif not vault.get(sub):
            return _popup_page('Sign-in failed', '<h2>Google did not return a refresh token.</h2>'
                               '<p>Remove this app at myaccount.google.com/permissions and sign in again.</p>',
                               {'success': False, 'error': 'No refresh token; remove the app in your Google account and retry'}), 400

        api_token = auth.issue_token(SECRET_KEY, {'email': email, 'name': user.get('name'),
                                                  'picture': user.get('picture'), 'sub': sub})
        return _popup_page('Signed in', '<h2>Signed in</h2><p>You can close this window.</p>', {
            'success': True,
            'user': {'email': email, 'name': user.get('name'), 'picture': user.get('picture'), 'sub': sub},
            'apiToken': api_token,
        })
    except Exception as e:
        print(f"❌ OAuth callback error: {type(e).__name__}: {e}")
        return _popup_page('Sign-in failed', '<h2>Sign-in failed</h2><p>Please close this window and try again.</p>',
                           {'success': False, 'error': 'Sign-in failed'}), 400


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """Is the stored token still valid? Used by the frontend on load."""
    user = current_user()
    if not user:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    return jsonify({"success": True, "user": {k: user.get(k) for k in ('email', 'name', 'picture', 'sub')}})


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_ready": True
    })

def _ensure_valid_credentials(credentials):
    """
    Validate credentials and refresh them if expired (or missing an access token).
    Returns the credentials or raises ValueError.
    """
    from google.auth.transport.requests import Request

    if not credentials:
        raise ValueError("No credentials provided")

    if credentials.expired or not credentials.token:
        if not credentials.refresh_token:
            raise ValueError("Token expired and no refresh token available")
        try:
            credentials.refresh(Request())
        except Exception as e:
            raise ValueError(f"Token refresh failed: {e}")
    return credentials


def _creds_unavailable(e):
    """Google access for this user is missing or was revoked. Log why, tell the client briefly."""
    print(f"⚠️ credentials unavailable: {e}")
    return jsonify({"success": False, "error": "google_access_unavailable",
                    "message": "Google access is not available. Please sign in again."}), 401


def _user_services():
    """(credentials, calendar_service, drive_store) for the signed-in user, or raises ValueError."""
    creds = resolve_credentials()
    if not creds:
        raise ValueError('no stored Google access for this user')
    creds = _ensure_valid_credentials(creds)
    return creds, _calendar_service(creds), _drive_store(creds)


def _scan_with(creds, cal, store, email, reset_seen=False, max_emails=50):
    from googleapiclient.errors import HttpError
    processed = _get_processed_gmail_ids(credentials_override=creds)
    return scanner.run_scan(_new_system(creds), cal, store, processed, HttpError, tz=DEFAULT_TIMEZONE,
                            reset_seen=reset_seen, owner_email=email, max_emails=max_emails)


def _run_user_scan(reset_seen=False):
    creds, cal, store = _user_services()
    return _scan_with(creds, cal, store, current_user()['email'], reset_seen)


def _is_revoked(e: Exception) -> bool:
    return 'invalid_grant' in str(e).lower()


def run_all_users(budget_seconds=45, max_users=None):
    """
    Scheduled pass over every user in the vault, least recently scanned first.
    Each user is isolated: one failure never stops the rest. Users who revoked access are
    removed from the vault. Returns counts only (no personal data).
    """
    import time
    started = time.monotonic()
    max_users = max_users or int(os.environ.get('CRON_MAX_USERS', '50'))
    vault = _vault()
    users = vault.users()
    todo = users[:max_users]
    out = {'users_total': len(users), 'scanned': 0, 'failed': 0, 'revoked': 0, 'added': 0,
           'for_review': 0, 'skipped_for_time': 0}
    for i, u in enumerate(todo):
        if time.monotonic() - started > budget_seconds:
            out['skipped_for_time'] = len(todo) - i
            break
        try:
            creds = _ensure_valid_credentials(_make_credentials(u['refresh_token']))
            res = _scan_with(creds, _calendar_service(creds), _drive_store(creds), u['email'], max_emails=30)
            out['scanned'] += 1
            out['added'] += res.get('added', 0)
            out['for_review'] += res.get('for_review', 0)
            vault.touch(u['sub'])
        except ValueError as e:                     # refresh failed
            if _is_revoked(e):
                vault.delete(u['sub']); forget_user(u['sub']); out['revoked'] += 1
            else:
                out['failed'] += 1
        except Exception as e:
            print(f"⚠️ scan failed for one user: {type(e).__name__}")
            out['failed'] += 1
    out['skipped_for_time'] += max(0, len(users) - len(todo))
    return out


@app.route('/api/cron/scan', methods=['POST', 'GET'])
def cron_scan():
    """
    Called by the scheduler (GitHub Actions / Cloud Scheduler) with
    `Authorization: Bearer $CRON_SECRET`. Scans every user's new mail.
    """
    if not auth.cron_authorized(request.headers.get('Authorization')):
        return jsonify({"success": False, "error": "unauthorized"}), 401
    try:
        return jsonify({"success": True, **run_all_users()})
    except ValueError as e:
        print(f"⚠️ cron: {e}")
        return jsonify({"success": False, "error": "vault_unavailable"}), 503
    except Exception as e:
        return _server_error(e)


@app.route('/api/scan/run', methods=['POST'])
def scan_run():
    """Website "Scan now": the same scan as the scheduled one, for the signed-in user."""
    try:
        data = request.get_json(silent=True) or {}
        return jsonify({"success": True, **_run_user_scan(reset_seen=bool(data.get('reset_seen')))})
    except ValueError as e:
        return _creds_unavailable(e)
    except Exception as e:
        if _is_scope_error(e):
            return jsonify({"success": False, "error": "drive_permission_needed",
                            "message": "Sign in again to allow saving settings to your Google Drive."}), 403
        return _server_error(e)


@app.route('/api/review', methods=['GET'])
def review_list():
    """Review queue, filtered-out list, activity log and last scan time."""
    try:
        _, _, store = _user_services()
        st = scanner.load_state(store)
        today = datetime.now().date()
        live = lambda items: [c for c in items if core.is_future_date((c.get('deadline') or {}).get('date'), today)]
        return jsonify({"success": True, "review": live(st['review']), "filtered_out": live(st['filtered']),
                        "log": st['log'][-10:][::-1], "last_scan": st['last_scan']})
    except ValueError as e:
        return _creds_unavailable(e)
    except Exception as e:
        if _is_scope_error(e):
            return jsonify({"success": False, "error": "drive_permission_needed"}), 403
        return _server_error(e)


@app.route('/api/review/<event_id>/<action>', methods=['POST'])
def review_resolve(event_id, action):
    """accept = create the event now; dismiss = never show it again."""
    if action not in ('accept', 'dismiss'):
        return jsonify({"success": False, "error": "bad_action"}), 400
    try:
        from googleapiclient.errors import HttpError
        _, cal, store = _user_services()
        try:
            res = scanner.resolve_item(store, event_id, action, cal, HttpError, tz=DEFAULT_TIMEZONE)
        except core.Skip as skip:
            return jsonify({"success": False, "error": skip.reason}), 409
        if res['status'] == 'not_found':
            return jsonify({"success": False, "error": "not_found"}), 404
        return jsonify({"success": True, **res})
    except ValueError as e:
        return _creds_unavailable(e)
    except Exception as e:
        return _server_error(e)


@app.route('/api/account', methods=['DELETE'])
def delete_account():
    """
    Delete-my-data: removes the stored token, profile and scan state, then revokes the app's
    access at Google. Calendar events the app already created are left alone (they are yours).
    """
    claims = current_user()
    try:
        creds = resolve_credentials()
        if creds:
            creds = _ensure_valid_credentials(creds)
            store = _drive_store(creds)
            for name in (PROFILE_FILE, STATE_FILE):          # while we still have Drive access
                store.delete(name)
            if claims['email'].lower() != auth.admin_email():   # the admin's token also opens the vault: never revoke it
                try:
                    requests.post('https://oauth2.googleapis.com/revoke', params={'token': creds.refresh_token or creds.token}, timeout=10)
                except Exception:
                    pass                                      # best effort; the vault entry is what matters
        if claims['email'].lower() != auth.admin_email():
            _vault().delete(claims['sub'])
        forget_user(claims['sub'])
        return jsonify({"success": True})
    except ValueError as e:
        # token already dead: still remove our copy
        try:
            _vault().delete(claims['sub']); forget_user(claims['sub'])
        except Exception:
            pass
        return jsonify({"success": True, "note": "access was already revoked"})
    except Exception as e:
        return _server_error(e)


@app.route('/api/emails/scan', methods=['POST'])
def scan_emails():
    """
    Scan the user's Gmail and return deadline CANDIDATES. Read-only: this
    endpoint never writes to Google Calendar. Accepted candidates are created
    through POST /api/calendar/reminders (idempotent, deterministic event IDs).

    Expected payload:
    {
        "user_id": "...", "max_emails": 50, "days_back": 7,
        "search_query": "optional gmail search terms",
        "include_self_sent": false
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        max_emails = _clamp_int(data.get('max_emails', 50), 1, 100, 50)
        days_back = _clamp_int(data.get('days_back', 7), 1, 60, 7)
        search_query = (data.get('search_query') or '').strip()
        include_self_sent = bool(data.get('include_self_sent', False))
        profile = data.get('profile') if isinstance(data.get('profile'), dict) else None

        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        credentials = resolve_credentials(data.get('credentials'), data.get('access_token'))
        if not credentials:
            return jsonify({
                "success": False,
                "error": "Gmail authentication required",
                "message": "Please sign in with Google to scan your emails"
            }), 401

        try:
            credentials = _ensure_valid_credentials(credentials)
        except ValueError as e:
            print(f"❌ Credential validation failed: {e}")
            return jsonify({
                "success": False,
                "error": "Token expired and refresh failed",
                "message": "Please login again"
            }), 401

        # Message IDs that already have a calendar event. Filtered out BEFORE the
        # emails are fetched/analysed so they cost no Gmail or LLM calls.
        if profile is None:
            profile = _load_profile(credentials)

        processed_gmail_ids = _get_processed_gmail_ids(credentials_override=credentials)
        print(f"🔍 {len(processed_gmail_ids)} Gmail message IDs already in Calendar")

        system = _new_system(credentials)
        results = system.process_user_emails(
            user_id=user_id,
            max_emails=max_emails,
            days_back=days_back,
            search_query=search_query,
            skip_ids=processed_gmail_ids,
            exclude_self_sent=not include_self_sent,
        )

        built = core.build_candidates(results, processed_gmail_ids, profile)
        formatted_results, filtered_out, stats = built['relevant'], built['filtered'], built['stats']
        skipped_count, expired_count, duplicate_count = stats['skipped'], stats['expired'], stats['duplicates']

        print(f"📊 scan: {len(results)} analysed, {len(formatted_results)} new candidates, "
              f"{expired_count} expired, {duplicate_count} duplicates, {skipped_count} skipped")

        job_related_count = sum(1 for r in formatted_results if r['classification']['is_job_related'])
        return jsonify({
            "success": True,
            "scan_timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "summary": {
                "total_emails_scanned": len(results),
                "valid_future_deadlines": len(formatted_results),
                "new_reminders_ready": len(formatted_results),
                "calendar_events_created": 0,  # scanning never writes to the calendar
                "job_related_emails": job_related_count,
                "expired_filtered": expired_count,
                "duplicates_filtered": duplicate_count,
                "total_filtered": skipped_count,
                "filtered_by_profile": len(filtered_out),
                "upcoming_only": True,
                "scan_parameters": {
                    "max_emails": max_emails,
                    "days_back": days_back,
                    "search_query": search_query,
                    "include_self_sent": include_self_sent
                }
            },
            "emails": formatted_results,
            "filtered_out": filtered_out
        })

    except Exception as e:
        msg = str(e)
        if "Gmail authentication required" in msg:
            return jsonify({
                "success": False,
                "error": "Gmail authentication required",
                "message": "Please sign in with Google to access your Gmail account"
            }), 401
        if "Failed to fetch emails" in msg:
            return jsonify({
                "success": False,
                "error": "Failed to fetch emails from Gmail",
                "message": "Unable to access your Gmail. Please check your permissions and try again."
            }), 502
        return _server_error(e)


@app.route('/api/profile', methods=['GET', 'PUT'])
def profile_endpoint():
    """
    The user's profile (role, discipline, graduation year, ...) lives in THEIR Google
    Drive appDataFolder - no database. GET returns it (or null); PUT validates and saves it.
    Credentials: query/body `credentials` | `access_token`, like the other endpoints.
    """
    try:
        body = request.get_json(silent=True) or {} if request.method == 'PUT' else {}
        src = body if request.method == 'PUT' else request.args
        credentials = resolve_credentials(src.get('credentials'), src.get('access_token'))
        if not credentials:
            return jsonify({"success": False, "error": "Authentication required. Please sign in again."}), 401
        try:
            credentials = _ensure_valid_credentials(credentials)
        except ValueError:
            return jsonify({"success": False, "error": "Token expired. Please login again."}), 401

        store = _drive_store(credentials)
        try:
            if request.method == 'GET':
                return jsonify({"success": True, "profile": store.load(PROFILE_FILE)})
            profile = normalize_profile(body.get('profile'))
            store.save(PROFILE_FILE, profile)
            return jsonify({"success": True, "profile": profile})
        except Exception as e:
            if _is_scope_error(e):
                return jsonify({"success": False, "error": "drive_permission_needed",
                                "message": "Please sign in again to allow saving your profile to your Google Drive."}), 403
            raise
    except Exception as e:
        return _server_error(e)


@app.route('/api/calendar/reminders', methods=['POST'])
def create_calendar_reminders():
    """
    Create Google Calendar events for accepted candidates. Idempotent: the event
    ID is derived from the Gmail message ID, so a repeated request (or a user
    having deleted the event earlier) comes back as a 409 and is reported under
    `duplicate_events` instead of creating a second event.

    Expected payload:
    {
        "user_id": "...",
        "emails": [{"email_id": "...", "subject": "...", "deadline": {...}}],
        "reminder_preferences": {"default_reminders": [1440, 60]},
        "credentials": {...} | "access_token": "..."
    }
    """
    try:
        from googleapiclient.errors import HttpError

        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        emails = data.get('emails') or []
        reminder_prefs = data.get('reminder_preferences') or {}

        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        credentials = resolve_credentials(data.get('credentials'), data.get('access_token'))
        if not credentials:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please sign in again."
            }), 401
        try:
            credentials = _ensure_valid_credentials(credentials)
        except ValueError:
            return jsonify({"success": False, "error": "Token expired. Please login again."}), 401

        calendar_service = _calendar_service(credentials)
        default_reminders = reminder_prefs.get('default_reminders') or [1440, 60]

        created_events, failed_events, skipped_events, duplicate_events = [], [], [], []
        today = datetime.now().date()

        for email in emails:
            email_id = email.get('email_id')
            subject = email.get('subject') or 'Job Deadline'
            try:
                try:
                    event_body = core.event_body(email, default_reminders, DEFAULT_TIMEZONE, today)
                except core.Skip as skip:
                    if skip.reason == 'missing_email_id':
                        failed_events.append({"email_id": None, "error": "missing email_id"})
                    else:
                        skipped_events.append({"email_id": email_id, "reason": skip.reason})
                    continue

                if core.insert_event(calendar_service, event_body, HttpError) == 'duplicate':
                    duplicate_events.append({
                        "email_id": email_id,
                        "event_id": event_body['id'],
                        "reason": "already_exists_or_dismissed"
                    })
                    continue

                created_events.append({
                    "event_id": event_body['id'],
                    "email_id": email_id,
                    "title": event_body['summary'],
                    "start_time": event_body['start']['dateTime'],
                    "status": "synced_to_google_calendar"
                })

            except Exception as e:
                print(f"❌ Failed to create event for '{subject[:50]}': {e}")
                failed_events.append({"email_id": email_id, "error": "create_failed"})

        print(f"📅 reminders: {len(created_events)} created, {len(duplicate_events)} duplicates, "
              f"{len(failed_events)} failed, {len(skipped_events)} skipped")

        return jsonify({
            "success": len(failed_events) == 0,
            "user_id": user_id,
            "created_events": created_events,
            "duplicate_events": duplicate_events,
            "failed_events": failed_events,
            "skipped_events": skipped_events,
            "summary": {
                "total_events_created": len(created_events),
                "duplicate_events": len(duplicate_events),
                "failed_events": len(failed_events),
                "skipped_events": len(skipped_events),
                "synced_to_google_calendar": True
            }
        })

    except Exception as e:
        return _server_error(e)

@app.route('/api/calendar/reminders/<event_id>', methods=['DELETE', 'OPTIONS'])
def delete_calendar_reminder(event_id):
    """
    Delete a reminder from Google Calendar.

    Note: Google keeps the IDs of deleted events reserved, so a deleted reminder
    is NOT recreated by later scans (event IDs are derived from the Gmail ID).
    """
    if request.method == 'OPTIONS':
        return ('', 204)  # CORS headers are added by flask-cors / after_request

    try:
        from googleapiclient.errors import HttpError

        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400
        if not event_id:
            return jsonify({"success": False, "error": "event_id is required"}), 400

        credentials = resolve_credentials(request.args.get('credentials'), request.args.get('access_token'))
        if not credentials:
            return jsonify({"success": False, "error": "Authentication required. Please sign in again."}), 401
        try:
            credentials = _ensure_valid_credentials(credentials)
        except ValueError:
            return jsonify({"success": False, "error": "Token expired. Please login again."}), 401

        service = _calendar_service(credentials)
        try:
            service.events().delete(calendarId='primary', eventId=event_id).execute()
        except HttpError as he:
            if he.resp.status in (404, 410):  # already deleted
                return jsonify({"success": True, "message": "Event not found (already deleted)",
                                "event_id": event_id}), 200
            raise

        return jsonify({"success": True, "message": "Reminder deleted successfully from Google Calendar",
                        "event_id": event_id}), 200

    except Exception as e:
        return _server_error(e)

def _is_app_event(event: dict) -> bool:
    """True only for events this app created (new tag, old tag, or legacy title)."""
    private = (event.get('extendedProperties') or {}).get('private') or {}
    if private.get('source') == EVENT_SOURCE or private.get('created_by') == 'email_reminder_system':
        return True
    # Legacy events were created without tags but always carried this title prefix.
    return (event.get('summary') or '').startswith('📧')


def _days_until(start_str: str) -> int:
    """Whole days from now until an event start (timezone-safe; all-day aware)."""
    now_utc = datetime.now(timezone.utc)
    try:
        if 'T' in start_str:
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        else:  # all-day event: YYYY-MM-DD
            start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        return int((start - now_utc).total_seconds() // 86400)
    except Exception:
        return 0


@app.route('/api/calendar/upcoming', methods=['GET'])
def get_upcoming_reminders():
    """
    Upcoming deadlines created by this app (other calendar events are ignored).

    Query parameters: user_id, days_ahead (default 90), credentials | access_token
    """
    try:
        user_id = request.args.get('user_id')
        days_ahead = _clamp_int(request.args.get('days_ahead', 90), 1, 365, 90)

        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        credentials = resolve_credentials(request.args.get('credentials'), request.args.get('access_token'))
        if not credentials:
            return jsonify({
                "success": True, "upcoming_events": [], "total_count": 0,
                "note": "Please sign in again to sync with Google Calendar"
            }), 200
        try:
            credentials = _ensure_valid_credentials(credentials)
        except ValueError:
            return jsonify({
                "success": True, "upcoming_events": [], "total_count": 0,
                "note": "Token expired. Please login again."
            }), 200

        service = _calendar_service(credentials)
        now = datetime.now(timezone.utc)
        time_min = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        time_max = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%dT%H:%M:%SZ')

        events, page_token = [], None
        while True:
            params = dict(calendarId='primary', timeMin=time_min, timeMax=time_max,
                          maxResults=250, singleEvents=True, orderBy='startTime')
            if page_token:
                params['pageToken'] = page_token
            resp = service.events().list(**params).execute()
            events.extend(resp.get('items', []))
            page_token = resp.get('nextPageToken')
            if not page_token:
                break

        upcoming_events = []
        for event in events:
            if event.get('status') == 'cancelled' or not _is_app_event(event):
                continue
            start = event['start'].get('dateTime', event['start'].get('date'))
            days_until = _days_until(start)
            if days_until < 0:
                continue

            urgency = "high" if days_until <= 3 else "medium" if days_until <= 7 else "low"
            private = (event.get('extendedProperties') or {}).get('private') or {}
            deadline_type = private.get('deadlineType') or private.get('deadline_type')
            if not deadline_type:
                title_lower = (event.get('summary') or '').lower()
                if 'interview' in title_lower:
                    deadline_type = 'interview'
                elif 'assessment' in title_lower or 'coding' in title_lower:
                    deadline_type = 'assessment'
                elif 'application' in title_lower:
                    deadline_type = 'application'
                else:
                    deadline_type = 'other'

            upcoming_events.append({
                "event_id": event['id'],
                "title": event.get('summary', 'No Title'),
                "start_time": start,
                "deadline_type": deadline_type,
                "urgency": urgency,
                "days_until": days_until,
                "calendar_link": event.get('htmlLink'),
                "description": event.get('description', ''),
                "gmail_message_id": private.get('gmailMessageId', '')
            })

        return jsonify({
            "success": True,
            "user_id": user_id,
            "query_parameters": {"days_ahead": days_ahead},
            "upcoming_events": upcoming_events,
            "summary": {
                "total_events": len(upcoming_events),
                "high_urgency": sum(1 for e in upcoming_events if e['days_until'] <= 3),
                "medium_urgency": sum(1 for e in upcoming_events if 3 < e['days_until'] <= 7),
                "low_urgency": sum(1 for e in upcoming_events if e['days_until'] > 7)
            }
        })

    except Exception as e:
        return _server_error(e)

def _get_processed_gmail_ids(credentials_override=None) -> set:
    """
    Fetch the set of Gmail message IDs that have already been processed and
    stored as Calendar events (via extendedProperties.private.gmailMessageId).

    This replaces the old fuzzy title-matching approach with an exact O(1)
    set membership check — zero false positives, zero false negatives.
    """
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from datetime import timedelta

    try:
        credentials = credentials_override
        if not credentials:
            print("⚠️ No credentials for ID-based duplicate check — allowing all through")
            return set()

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        service = build('calendar', 'v3', credentials=credentials)

        # Fetch events from the past 180 days + next 365 days to cover all cases
        time_min = (datetime.utcnow() - timedelta(days=180)).isoformat() + 'Z'
        time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + 'Z'

        processed_ids = set()
        page_token = None

        while True:
            params = dict(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=250,
                singleEvents=True,
                # Request privateExtendedProperty to filter only our events efficiently
                privateExtendedProperty='source=smart_reminder',
            )
            if page_token:
                params['pageToken'] = page_token

            response = service.events().list(**params).execute()

            for event in response.get('items', []):
                private = (event.get('extendedProperties') or {}).get('private', {})
                gmail_id = private.get('gmailMessageId', '').strip()
                if gmail_id:
                    processed_ids.add(gmail_id)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        print(f"📅 Found {len(processed_ids)} already-processed Gmail IDs in Calendar")
        return processed_ids

    except Exception as e:
        print(f"⚠️ Gmail ID duplicate check failed: {e} — falling back to allow-all")
        return set()

# ============================================================
# GEMINI AI ENDPOINTS
# ============================================================

def _get_gemini_model():
    """Initialise and return a Gemini generative model, or None if unavailable."""
    if not _GEMINI_AVAILABLE:
        return None
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("⚠️ GEMINI_API_KEY not set in environment")
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """
    Chat with Gemini AI about upcoming deadlines.

    Expected payload:
    {
        "user_id": "...",
        "message": "What should I focus on today?",
        "events": [
            {"title": "Assignment due", "start": "2026-07-01", "resource": {"urgency": "high"}},
            ...
        ],
        "history": [{"role": "user", "parts": "..."}, {"role": "model", "parts": "..."}]
    }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        events = data.get('events', [])
        history = data.get('history', [])  # previous turns for multi-turn chat

        if not user_message:
            return jsonify({'success': False, 'error': 'message is required'}), 400

        model = _get_gemini_model()
        if not model:
            return jsonify({
                'success': False,
                'error': 'Gemini AI is not configured. Set GEMINI_API_KEY environment variable.'
            }), 503

        # Build context from upcoming events
        events_context = ''
        if events:
            lines = []
            for e in events[:20]:  # cap at 20 to stay within token limits
                title = e.get('title', 'Untitled')
                start = e.get('start', 'Unknown date')
                urgency = (e.get('resource') or {}).get('urgency', 'medium')
                days_until = (e.get('resource') or {}).get('daysUntil', '?')
                lines.append(f"- {title} | Due: {start} | Urgency: {urgency} | Days left: {days_until}")
            events_context = 'User\'s upcoming deadlines:\n' + '\n'.join(lines)
        else:
            events_context = 'User has no upcoming deadlines in their calendar.'

        system_prompt = (
            "You are a proactive AI productivity companion. "
            "You help users manage ALL kinds of deadlines — job applications, university assignments, "
            "bill payments, interviews, personal goals, events, and more. "
            "You have access to the user's upcoming deadlines (shown below) and use them to give "
            "specific, actionable advice. Be encouraging, concise, and practical. "
            "When relevant, suggest concrete next steps. "
            "If the user's question maps to a specific deadline, call it out by name.\n\n"
            + events_context
        )

        # Build multi-turn history for Gemini
        chat_history = []
        for turn in history[-10:]:  # keep last 10 turns to manage context length
            role = turn.get('role', 'user')
            parts = turn.get('parts', '')
            if role in ('user', 'model') and parts:
                chat_history.append({'role': role, 'parts': [parts]})

        chat = model.start_chat(history=chat_history)

        # Prepend system context to the first user message in this turn
        full_user_message = f"{system_prompt}\n\nUser: {user_message}"
        response = chat.send_message(full_user_message)
        ai_text = response.text

        print(f"🤖 Gemini AI responded ({len(ai_text)} chars) to: {user_message[:60]}...")

        return jsonify({
            'success': True,
            'response': ai_text,
            'updated_history': [
                *history[-10:],
                {'role': 'user', 'parts': user_message},
                {'role': 'model', 'parts': ai_text}
            ]
        })

    except Exception as e:
        print(f"❌ AI chat error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route('/api/ai/prioritize', methods=['POST'])
def ai_prioritize():
    """
    Use Gemini to rank deadlines by urgency and importance.

    Expected payload:
    {
        "user_id": "...",
        "events": [
            {"id": "...", "title": "...", "start": "2026-07-01", "resource": {"urgency": "high"}},
            ...
        ]
    }
    Returns a ranked list with reasons and suggested actions.
    """
    try:
        data = request.get_json()
        events = data.get('events', [])

        if not events:
            return jsonify({'success': True, 'priorities': [], 'summary': 'No upcoming deadlines to prioritise.'})

        model = _get_gemini_model()
        if not model:
            return jsonify({
                'success': False,
                'error': 'Gemini AI is not configured. Set GEMINI_API_KEY environment variable.'
            }), 503

        # Format events for the prompt
        events_text = '\n'.join([
            f"{i+1}. ID={e.get('id','?')} | Title: {e.get('title','Untitled')} | "
            f"Due: {e.get('start','?')} | Urgency: {(e.get('resource') or {}).get('urgency','medium')} | "
            f"Days left: {(e.get('resource') or {}).get('daysUntil','?')}"
            for i, e in enumerate(events[:20])
        ])

        prompt = f"""You are a productivity AI assistant. Rank the following deadlines from most to least urgent/important.
Consider: days remaining, stated urgency, type of task (job, assignment, personal, bill, etc.).
For each item provide a brief reason and a suggested immediate action.

Deadlines:
{events_text}

Respond ONLY with valid JSON in this exact format:
{{
  "priorities": [
    {{
      "rank": 1,
      "event_id": "<id>",
      "title": "<title>",
      "reason": "<1-2 sentence explanation of why this is ranked here>",
      "suggested_action": "<specific next step the user should take>",
      "time_estimate": "<rough time needed, e.g. '2 hours'>"
    }}
  ],
  "focus_today": "<title of the single most important task to do today>",
  "summary": "<2-3 sentence overall productivity advice based on their deadlines>"
}}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        print(f"🎯 Gemini prioritised {len(result.get('priorities', []))} deadlines")

        return jsonify({'success': True, **result})

    except json.JSONDecodeError as e:
        print(f"⚠️ Gemini returned non-JSON: {e}")
        # Return a graceful fallback
        return jsonify({
            'success': True,
            'priorities': [],
            'focus_today': events[0].get('title', 'Your most urgent deadline') if events else None,
            'summary': 'Could not parse AI priorities. Focus on your nearest deadline first.'
        })
    except Exception as e:
        print(f"❌ AI prioritize error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("🚀 Email Reminder API Service Starting...")
    print("🔗 API Endpoints Available:")
    print("   • POST /api/emails/scan - Scan Gmail and return deadline candidates (read-only)")
    print("   • POST /api/calendar/reminders - Create calendar events (idempotent)")
    print("   • GET  /api/calendar/upcoming - Get upcoming deadlines")
    print("=" * 50)
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
