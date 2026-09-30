"""
Tiny JSON store in the user's own Google Drive appDataFolder (scope
drive.appdata). No database: the file lives in the user's Drive, is invisible
in their Drive UI, is only reachable by this app, and is deleted when they
revoke access.

Files used: profile.json (written by the website), state.json (background job).
"""
import io
import json
from typing import Dict, Optional

PROFILE_FILE = 'profile.json'
STATE_FILE = 'state.json'
MAX_BYTES = 256 * 1024          # appDataFolder is for small settings, not bulk data


class DriveStore:
    def __init__(self, service):
        self.svc = service

    def _find(self, name: str) -> Optional[str]:
        safe = name.replace("\\", "\\\\").replace("'", "\\'")
        res = self.svc.files().list(spaces='appDataFolder', q=f"name = '{safe}'",
                                    fields='files(id,name,modifiedTime)', pageSize=10).execute()
        files = res.get('files', [])
        return files[0]['id'] if files else None

    def load(self, name: str) -> Optional[Dict]:
        file_id = self._find(name)
        if not file_id:
            return None
        raw = self.svc.files().get_media(fileId=file_id).execute()
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode('utf-8')
        try:
            data = json.loads(raw)
        except ValueError:
            return None                     # corrupt file behaves like "no file"
        return data if isinstance(data, dict) else None

    def save(self, name: str, data: Dict) -> None:
        payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        if len(payload) > MAX_BYTES:
            raise ValueError('data too large for appDataFolder store')
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(io.BytesIO(payload), mimetype='application/json', resumable=False)
        file_id = self._find(name)
        if file_id:
            self.svc.files().update(fileId=file_id, media_body=media).execute()
        else:
            self.svc.files().create(body={'name': name, 'parents': ['appDataFolder']},
                                    media_body=media, fields='id').execute()

    def delete(self, name: str) -> None:
        file_id = self._find(name)
        if file_id:
            self.svc.files().delete(fileId=file_id).execute()

    def list_names(self, prefix: str = '') -> list:
        """Names of all files in the appDataFolder starting with `prefix` (filtered here: Drive's
        `name contains` matches whole words and would miss names like tok-ab12...)."""
        names, token = [], None
        while True:
            res = self.svc.files().list(spaces='appDataFolder', fields='nextPageToken,files(name)', pageSize=100, pageToken=token).execute()
            names += [f['name'] for f in res.get('files', []) if f['name'].startswith(prefix)]
            token = res.get('nextPageToken')
            if not token:
                return names
