"""
Authentication for a private, college-only app.

- Sign-in: any Google account in ALLOWED_DOMAIN (default thapar.edu), plus optional
  extra addresses in ALLOWED_EMAILS. Nobody else gets a token.
- The browser holds a signed API token (identity only, no Google secrets).
- Google access is done by the SERVER with each user's refresh token, kept encrypted in
  the vault (see vault.py). Tokens and the client secret never reach the browser.
"""
import hmac
import os
from typing import Dict, List, Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_TTL_SECONDS = 30 * 24 * 3600
_SALT = 'smart-reminder-api-v1'


def allowed_domain() -> str:
    return (os.environ.get('ALLOWED_DOMAIN', 'thapar.edu') or '').strip().lower().lstrip('@')


def extra_emails() -> List[str]:
    return [e.strip().lower() for e in (os.environ.get('ALLOWED_EMAILS') or '').split(',') if e.strip()]


def admin_email() -> str:
    """Whose Drive hosts the token vault, and who sees the one-time setup page."""
    return (os.environ.get('ADMIN_EMAIL') or '').strip().lower()


def is_allowed(email: Optional[str], hosted_domain: Optional[str] = None) -> bool:
    """Domain members (Google's `hd` claim must agree when present) or explicitly listed addresses."""
    e = (email or '').strip().lower()
    if not e or '@' not in e:
        return False
    if e in extra_emails():
        return True
    domain = allowed_domain()
    if not domain or e.rsplit('@', 1)[1] != domain:
        return False
    return hosted_domain is None or hosted_domain == '' or hosted_domain.lower() == domain


def _serializer(secret: str) -> URLSafeTimedSerializer:
    if not secret:
        raise RuntimeError('SECRET_KEY is not set')
    return URLSafeTimedSerializer(secret, salt=_SALT)


def issue_token(secret: str, user: Dict) -> str:
    claims = {k: str(user.get(k) or '')[:300] for k in ('email', 'name', 'picture', 'sub')}
    return _serializer(secret).dumps(claims)


def verify_token(secret: str, header: Optional[str]) -> Optional[Dict]:
    """Claims for a valid 'Bearer <token>' header of an allowed user, else None."""
    if not header or not header.lower().startswith('bearer '):
        return None
    try:
        claims = _serializer(secret).loads(header[7:].strip(), max_age=TOKEN_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    if not claims.get('sub') or not is_allowed(claims.get('email')):
        return None
    return claims


def cron_authorized(header: Optional[str]) -> bool:
    """Constant-time check of 'Bearer <CRON_SECRET>'. Unset/short secret = disabled."""
    expected = os.environ.get('CRON_SECRET') or ''
    if len(expected) < 16 or not header or not header.lower().startswith('bearer '):
        return False
    return hmac.compare_digest(header[7:].strip().encode(), expected.encode())
