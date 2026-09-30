import os
import unittest
from unittest import mock

from tests.test_phase0 import api, authed_client, FakeCalendar, FakeHttpError, future, gmail_msg
from tests.test_scanner import MemStore, system_for
from tests.test_auth import MemVault
import scanner
from drive_store import PROFILE_FILE, STATE_FILE

CRON = 'c' * 32


class UserEndpointTests(unittest.TestCase):
    """Website endpoints: the signed-in user's own services."""
    def setUp(self):
        _, ds = future()
        self.msg = gmail_msg('c1', f'Internship - Application Deadline {ds}',
                             f'The application deadline is {ds} at 11:59 PM.', 'careers@acme.com')
        self.store, self.cal = MemStore(), FakeCalendar()
        self.patches = [
            mock.patch.object(api, '_user_services', lambda: (object(), self.cal, self.store)),
            mock.patch.object(api, '_get_processed_gmail_ids', lambda credentials_override=None: set()),
            mock.patch.object(api, '_new_system', lambda creds: system_for([self.msg])),
        ]
        for p in self.patches: p.start()
        self.anon = api.app.test_client()

    def tearDown(self):
        for p in self.patches: p.stop()

    def test_scan_run_requires_login_and_adds(self):
        self.assertEqual(self.anon.post('/api/scan/run').status_code, 401)
        self.assertEqual(authed_client().post('/api/scan/run').get_json()['added'], 1)
        self.assertEqual(authed_client().post('/api/scan/run').get_json()['added'], 0)    # idempotent
        self.assertEqual(len(self.cal.inserted), 1)

    def test_missing_google_access_asks_to_sign_in_again(self):
        with mock.patch.object(api, '_user_services', side_effect=ValueError('no stored Google access for this user')):
            r = authed_client().post('/api/scan/run')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json()['error'], 'google_access_unavailable')

    def test_review_flow(self):
        self.store.files[PROFILE_FILE] = {'auto_add': 'off'}
        authed_client().post('/api/scan/run')
        c = authed_client()
        r = c.get('/api/review').get_json()
        self.assertEqual(len(r['review']), 1); self.assertIsNotNone(r['last_scan'])
        eid = r['review'][0]['event_id']
        self.assertEqual(self.anon.get('/api/review').status_code, 401)
        self.assertEqual(c.post(f'/api/review/{eid}/explode').status_code, 400)
        self.assertEqual(c.post('/api/review/nope/accept').status_code, 404)
        self.assertEqual(c.post(f'/api/review/{eid}/accept').get_json()['status'], 'created')
        self.assertEqual(len(self.cal.inserted), 1)
        self.assertEqual(c.get('/api/review').get_json()['review'], [])

    def test_accept_past_event_is_conflict_not_crash(self):
        old = {'event_id': 'x1', 'email_id': 'm', 'deadline': {'has_deadline': True, 'date': '2020-01-01'}}
        self.store.files[STATE_FILE] = dict(scanner.empty_state(), review=[old])
        self.assertEqual(authed_client().post('/api/review/x1/accept').status_code, 409)


class CronTests(unittest.TestCase):
    """Scheduled pass over all users in the vault."""
    def setUp(self):
        self.vault = MemVault()
        for n in ('a', 'b', 'c'):
            self.vault.put(n, f'{n}@example.com', f'RT-{n}')
        self.scanned = []
        def scan_with(creds, cal, store, email, reset_seen=False, max_emails=50):
            self.scanned.append(email)
            if email == 'b@example.com':
                raise RuntimeError('gmail exploded')
            return {'added': 2, 'for_review': 1}
        self.patches = [
            mock.patch.dict(os.environ, {'CRON_SECRET': CRON}),
            mock.patch.object(api, '_vault', lambda: self.vault),
            mock.patch.object(api, '_ensure_valid_credentials', lambda c: c),
            mock.patch.object(api, '_calendar_service', lambda c: object()),
            mock.patch.object(api, '_drive_store', lambda c: object()),
            mock.patch.object(api, '_scan_with', scan_with),
        ]
        for p in self.patches: p.start()
        self.anon = api.app.test_client()

    def tearDown(self):
        for p in self.patches: p.stop()

    def cron(self, secret=CRON):
        return self.anon.post('/api/cron/scan', headers={'Authorization': f'Bearer {secret}'})

    def test_needs_secret_not_a_user_token(self):
        self.assertEqual(self.anon.post('/api/cron/scan').status_code, 401)
        self.assertEqual(self.cron('wrong' * 8).status_code, 401)
        self.assertEqual(authed_client().post('/api/cron/scan').status_code, 401)
        self.assertEqual(self.scanned, [])

    def test_one_users_failure_does_not_stop_the_others(self):
        j = self.cron().get_json()
        self.assertEqual(sorted(self.scanned), ['a@example.com', 'b@example.com', 'c@example.com'])
        self.assertEqual((j['scanned'], j['failed'], j['added'], j['for_review']), (2, 1, 4, 2))
        self.assertNotIn('@', str(j))                                   # counts only, no personal data

    def test_revoked_user_is_removed_from_vault(self):
        real_ensure = api._ensure_valid_credentials
        def ensure(c):
            if c.refresh_token == 'RT-c':
                raise ValueError('Token refresh failed: invalid_grant: Token has been expired or revoked.')
            return c
        with mock.patch.object(api, '_ensure_valid_credentials', ensure):
            j = self.cron().get_json()
        self.assertEqual(j['revoked'], 1)
        self.assertNotIn('c', self.vault.d)
        self.assertEqual(sorted(self.vault.d), ['a', 'b'])

    def test_transient_refresh_error_keeps_the_user(self):
        def ensure(c):
            if c.refresh_token == 'RT-c':
                raise ValueError('Token refresh failed: network down')
            return c
        with mock.patch.object(api, '_ensure_valid_credentials', ensure):
            j = self.cron().get_json()
        self.assertEqual((j['revoked'], 'c' in self.vault.d), (0, True))

    def test_time_budget_stops_the_run_politely(self):
        with mock.patch.dict(os.environ, {'CRON_MAX_USERS': '50'}):
            out = api.run_all_users(budget_seconds=-1)
        self.assertEqual((out['scanned'], out['skipped_for_time']), (0, 3))

    def test_user_cap(self):
        out = api.run_all_users(max_users=2)
        self.assertEqual(out['skipped_for_time'], 1)
        self.assertEqual(len(self.scanned), 2)

    def test_vault_down_is_503_without_details(self):
        with mock.patch.object(api, '_vault', side_effect=ValueError('GOOGLE_REFRESH_TOKEN (vault owner) is not configured')):
            r = self.cron()
        self.assertEqual(r.status_code, 503)
        self.assertNotIn('GOOGLE_REFRESH_TOKEN', r.get_data(as_text=True))


class DeleteAccountTests(unittest.TestCase):
    def setUp(self):
        self.vault = MemVault(); self.vault.put('s1', 'student@example.com', 'RT'); self.vault.put('1', 'owner@example.com', 'RT-admin')
        self.deleted, self.revoked = [], []
        class Store:
            def delete(s, name): self.deleted.append(name)
        self.patches = [
            mock.patch.object(api, '_vault', lambda: self.vault),
            mock.patch.object(api, '_ensure_valid_credentials', lambda c: c),
            mock.patch.object(api, '_drive_store', lambda c: Store()),
            mock.patch.object(api.requests, 'post', lambda url, **kw: self.revoked.append(url)),
        ]
        for p in self.patches: p.start()
    def tearDown(self):
        for p in self.patches: p.stop()

    def test_student_data_token_and_access_are_removed(self):
        r = authed_client('student@example.com', 's1').delete('/api/account')
        self.assertTrue(r.get_json()['success'])
        self.assertEqual(sorted(self.deleted), [PROFILE_FILE, STATE_FILE])
        self.assertNotIn('s1', self.vault.d)
        self.assertEqual(len(self.revoked), 1)

    def test_admin_delete_never_revokes_the_vault_token(self):
        authed_client('owner@example.com', '1').delete('/api/account')
        self.assertEqual(self.revoked, [])
        self.assertIn('1', self.vault.d)

    def test_requires_login(self):
        self.assertEqual(api.app.test_client().delete('/api/account').status_code, 401)


if __name__ == '__main__':
    unittest.main()
