import os
import unittest
from unittest import mock

from cryptography.fernet import Fernet

import vault as vt
from tests.test_profile_drive import FakeDrive
from drive_store import DriveStore

KEY1, KEY2 = Fernet.generate_key().decode(), Fernet.generate_key().decode()


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.drive = FakeDrive()
        self.drive.delete = lambda fileId: mock.Mock(execute=lambda: self.drive.files_.pop(fileId))   # add delete to the fake
        orig_list = self.drive.list
        def list_(spaces=None, q=None, fields=None, pageSize=None, pageToken=None, **kw):
            assert spaces == 'appDataFolder'
            if q is None:
                from unittest import mock as m
                return m.Mock(execute=lambda: {'files': [{'name': f['name']} for f in self.drive.files_.values()]})
            return orig_list(spaces=spaces, q=q)
        self.drive.list = list_
        self.store = DriveStore(self.drive)
        self.env = mock.patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': KEY1}); self.env.start()
        self.v = vt.TokenVault(self.store)

    def tearDown(self):
        self.env.stop()

    def test_roundtrip_and_token_is_not_readable_in_drive(self):
        self.v.put('sub1', 'a@x.com', 'REFRESH-SECRET')
        self.assertEqual(self.v.get('sub1')['refresh_token'], 'REFRESH-SECRET')
        raw = str(self.drive.files_)
        self.assertNotIn('REFRESH-SECRET', raw)
        self.assertNotIn('a@x.com', raw)
        self.assertNotIn('sub1', raw)                                                  # file name is a hash too

    def test_wrong_key_behaves_like_no_entry(self):
        self.v.put('sub1', 'a@x.com', 'RT')
        with mock.patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': KEY2}):
            self.assertIsNone(self.v.get('sub1'))

    def test_key_rotation(self):
        self.v.put('sub1', 'a@x.com', 'RT')
        with mock.patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': f'{KEY2},{KEY1}'}):   # new key first, old still decrypts
            self.assertEqual(self.v.get('sub1')['refresh_token'], 'RT')
            self.v.put('sub1', 'a@x.com', 'RT2')
        with mock.patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': KEY2}):
            self.assertEqual(self.v.get('sub1')['refresh_token'], 'RT2')

    def test_missing_key_raises(self):
        with mock.patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': ''}):
            with self.assertRaises(RuntimeError):
                self.v.put('s', 'e', 'r')

    def test_users_sorted_by_last_run_and_delete(self):
        self.v.put('a', 'a@x.com', 'r', last_run=300); self.v.put('b', 'b@x.com', 'r', last_run=100); self.v.put('c', 'c@x.com', 'r', last_run=200)
        self.drive.files_['junk'] = {'name': 'profile.json', 'data': b'{}'}             # other appdata files are ignored
        self.assertEqual([u['sub'] for u in self.v.users()], ['b', 'c', 'a'])
        self.v.delete('b')
        self.assertEqual([u['sub'] for u in self.v.users()], ['c', 'a'])
        self.assertIsNone(self.v.get('b'))

    def test_touch_moves_user_to_the_back(self):
        self.v.put('a', 'a@x.com', 'r', last_run=1); self.v.put('b', 'b@x.com', 'r', last_run=2)
        self.v.touch('a')
        self.assertEqual([u['sub'] for u in self.v.users()], ['b', 'a'])


if __name__ == '__main__':
    unittest.main()
