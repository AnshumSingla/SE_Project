"""Minimal stand-ins for libraries that cannot be installed in the sandbox
(PyPI is blocked). They only provide what api_service imports."""
import sys, types

def _mod(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m

class FakeCredentials:
    def __init__(self, token=None, refresh_token=None, token_uri=None, client_id=None,
                 client_secret=None, scopes=None, **kw):
        self.token, self.refresh_token, self.token_uri = token, refresh_token, token_uri
        self.client_id, self.client_secret, self.scopes = client_id, client_secret, scopes
        self.expired = False; self.expiry = None
    @classmethod
    def from_authorized_user_info(cls, info, scopes=None):
        return cls(token=info.get('token'), refresh_token=info.get('refresh_token'),
                   token_uri=info.get('token_uri'), client_id=info.get('client_id'),
                   client_secret=info.get('client_secret'), scopes=info.get('scopes'))
    def refresh(self, request): self.token = 'refreshed'; self.expired = False

class FakeHttpError(Exception):
    def __init__(self, status):
        self.resp = types.SimpleNamespace(status=status); super().__init__(f"HTTP {status}")

def install():
    _mod('flask_cors', CORS=lambda *a, **k: None)
    _mod('google'); _mod('google.oauth2'); _mod('google.oauth2.credentials', Credentials=FakeCredentials)
    _mod('google.auth'); _mod('google.auth.transport')
    _mod('google.auth.transport.requests', Request=object)
    _mod('google_auth_oauthlib'); _mod('google_auth_oauthlib.flow', InstalledAppFlow=object)
    _mod('googleapiclient'); _mod('googleapiclient.discovery', build=lambda *a, **k: None)
    _mod('googleapiclient.errors', HttpError=FakeHttpError)
    class _Upload:
        def __init__(self, fd, mimetype=None, resumable=False): self.data = fd.read()
    _mod('googleapiclient.http', MediaIoBaseUpload=_Upload)
