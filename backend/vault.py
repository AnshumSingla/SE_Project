"""
Token vault: one Fernet-encrypted file per user in the ADMIN's Drive appDataFolder.
No database and no extra storage account: the file lives in the app's private,
hidden Drive space. The encryption key (TOKEN_ENCRYPTION_KEY) lives only in the
server environment, so the Drive files alone are useless.

Entry: {'sub', 'email', 'refresh_token', 'last_run'}.
"""
import hashlib
import json
import os
import time
from typing import Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

PREFIX = 'tok-'


def _fernet() -> MultiFernet:
    """TOKEN_ENCRYPTION_KEY may hold several comma-separated keys: the first encrypts,
    all decrypt, so a key can be rotated without locking anyone out."""
    keys = [k.strip() for k in (os.environ.get('TOKEN_ENCRYPTION_KEY') or '').split(',') if k.strip()]
    if not keys:
        raise RuntimeError('TOKEN_ENCRYPTION_KEY is not set')
    return MultiFernet([Fernet(k.encode()) for k in keys])


def file_name(sub: str) -> str:
    return PREFIX + hashlib.sha256(sub.encode()).hexdigest()[:40] + '.enc'


class TokenVault:
    def __init__(self, store):
        self.store = store          # DriveStore (or anything with load/save/delete/list_names)

    def put(self, sub: str, email: str, refresh_token: str, last_run: Optional[float] = None) -> None:
        entry = {'sub': sub, 'email': email, 'refresh_token': refresh_token, 'last_run': last_run or 0}
        ct = _fernet().encrypt(json.dumps(entry).encode()).decode()
        self.store.save(file_name(sub), {'ct': ct})

    def _decode(self, blob: Optional[Dict]) -> Optional[Dict]:
        if not blob or 'ct' not in blob:
            return None
        try:
            return json.loads(_fernet().decrypt(blob['ct'].encode()))
        except (InvalidToken, ValueError):
            return None                 # wrong key / corrupt file behaves like "no entry"

    def get(self, sub: str) -> Optional[Dict]:
        return self._decode(self.store.load(file_name(sub)))

    def delete(self, sub: str) -> None:
        self.store.delete(file_name(sub))

    def touch(self, sub: str) -> None:
        entry = self.get(sub)
        if entry:
            self.put(sub, entry['email'], entry['refresh_token'], time.time())

    def users(self) -> List[Dict]:
        """All entries, least recently scanned first (fair rotation when a run can't finish everyone)."""
        entries = [e for e in (self._decode(self.store.load(n)) for n in self.store.list_names(PREFIX)) if e]
        return sorted(entries, key=lambda e: e.get('last_run', 0))
