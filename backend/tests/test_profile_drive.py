import json
import unittest
from unittest import mock

from tests import stubs  # noqa: F401
from tests.stubs import FakeHttpError
from tests.test_phase0 import ScanTests, api, authed_client
from drive_store import DriveStore, PROFILE_FILE


class FakeDrive:
    """Just enough of the Drive v3 files() API, with appDataFolder semantics."""
    def __init__(self):
        self.files_, self.n, self.calls = {}, 0, []
    def files(self): return self
    def list(self, spaces=None, q=None, **kw):
        assert spaces == 'appDataFolder', 'must never look outside appDataFolder'
        name = q.split("'")[1]
        self.calls.append(('list', name)); self.last_q = q
        hits = [{'id': i, 'name': f['name']} for i, f in self.files_.items() if f['name'] == name]
        return mock.Mock(execute=lambda: {'files': hits})
    def get_media(self, fileId):
        return mock.Mock(execute=lambda: self.files_[fileId]['data'])
    def create(self, body, media_body, fields=None):
        assert body['parents'] == ['appDataFolder']
        def run():
            self.n += 1; fid = f'f{self.n}'
            self.files_[fid] = {'name': body['name'], 'data': media_body.data}
            return {'id': fid}
        return mock.Mock(execute=run)
    def update(self, fileId, media_body):
        def run():
            self.files_[fileId]['data'] = media_body.data
            return {}
        return mock.Mock(execute=run)


class StoreTests(unittest.TestCase):
    def test_roundtrip_and_update_in_place(self):
        d = FakeDrive(); st = DriveStore(d)
        self.assertIsNone(st.load(PROFILE_FILE))
        st.save(PROFILE_FILE, {'a': 1}); st.save(PROFILE_FILE, {'a': 2, 'नाम': 'ü'})
        self.assertEqual(len(d.files_), 1)                     # updated, not duplicated
        self.assertEqual(st.load(PROFILE_FILE), {'a': 2, 'नाम': 'ü'})

    def test_corrupt_file_is_treated_as_missing(self):
        d = FakeDrive(); st = DriveStore(d); st.save('x.json', {})
        d.files_['f1']['data'] = b'{not json'
        self.assertIsNone(st.load('x.json'))

    def test_too_large_rejected(self):
        with self.assertRaises(ValueError):
            DriveStore(FakeDrive()).save('x.json', {'k': 'v' * 300000})

    def test_quote_in_name_is_escaped(self):
        d = FakeDrive(); DriveStore(d).load("a'b")
        self.assertEqual(d.last_q, "name = 'a\\'b'")


class ProfileEndpointTests(unittest.TestCase):
    def setUp(self):
        self.drive = FakeDrive(); self.c = authed_client()
        self.patches = [mock.patch.object(api, '_drive_store', lambda creds: DriveStore(self.drive)),
                        mock.patch.object(api, '_ensure_valid_credentials', lambda c: c)]
        for p in self.patches: p.start()
    def tearDown(self):
        for p in self.patches: p.stop()

    def test_put_then_get(self):
        r = self.c.put('/api/profile', json={'access_token': 'ya29.x', 'profile': {
            'disciplines': 'CSE, IT', 'graduation_year': 2027, 'evil': '<script>'}})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('evil', r.get_json()['profile'])
        g = self.c.get('/api/profile?access_token=ya29.x').get_json()
        self.assertEqual(g['profile']['graduation_year'], 2027)
        self.assertEqual(g['profile']['discipline_groups'], ['cs'])

    def test_get_without_profile_is_null(self):
        self.assertIsNone(self.c.get('/api/profile?access_token=ya29.x').get_json()['profile'])

    def test_requires_auth(self):
        anon = api.app.test_client()
        self.assertEqual(anon.get('/api/profile').status_code, 401)
        self.assertEqual(anon.get('/api/profile?access_token=ya29.stolen').status_code, 401)

    def test_missing_drive_scope_asks_for_reauth(self):
        bad = mock.Mock(); bad.load.side_effect = FakeHttpError(403)
        with mock.patch.object(api, '_drive_store', lambda c: bad):
            r = self.c.get('/api/profile?access_token=ya29.x')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()['error'], 'drive_permission_needed')


class ScanUsesDriveProfile(ScanTests):
    def test_profile_from_drive_when_not_in_request(self):
        with mock.patch.object(api, '_load_profile', lambda c: {'exclude_keywords': 'internship'}):
            j = self.post().get_json()
        self.assertEqual([e['email_id'] for e in j['filtered_out']], ['m1'])

    def test_drive_failure_does_not_break_scan(self):
        with mock.patch.object(api, '_drive_store', side_effect=FakeHttpError(403)):
            j = self.post().get_json()
        self.assertEqual([e['email_id'] for e in j['emails']], ['m1'])


del ScanTests
if __name__ == '__main__':
    unittest.main()
