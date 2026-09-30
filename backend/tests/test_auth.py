import os
import unittest
from unittest import mock

from tests.test_phase0 import api, auth, authed_client, auth_header  # noqa: F401  (installs stubs, sets env)


def token(email, sub='1', key='k' * 32):
    return 'Bearer ' + auth.issue_token(key, {'email': email, 'sub': sub})


class AllowedTests(unittest.TestCase):
    def test_domain_and_hd(self):
        self.assertTrue(auth.is_allowed('a@example.com'))
        self.assertTrue(auth.is_allowed('A@Example.com', 'example.com'))
        self.assertFalse(auth.is_allowed('a@example.com', 'other.org'))     # Google says another org
        self.assertFalse(auth.is_allowed('a@gmail.com'))
        self.assertFalse(auth.is_allowed('a@evil-example.com'))
        self.assertFalse(auth.is_allowed('a@example.com.evil.io'))
        self.assertFalse(auth.is_allowed('example.com'))
        self.assertFalse(auth.is_allowed(None))

    def test_extra_emails_and_empty_domain(self):
        with mock.patch.dict(os.environ, {'ALLOWED_EMAILS': 'Friend@gmail.com, x@y.org'}):
            self.assertTrue(auth.is_allowed('friend@gmail.com'))
            self.assertFalse(auth.is_allowed('other@gmail.com'))
        with mock.patch.dict(os.environ, {'ALLOWED_DOMAIN': ''}):
            self.assertFalse(auth.is_allowed('a@example.com'))               # misconfigured = closed


class TokenTests(unittest.TestCase):
    def test_roundtrip_and_only_identity_inside(self):
        t = auth.issue_token('k' * 32, {'email': 'a@example.com', 'sub': '7', 'refresh_token': 'SECRET'})
        claims = auth.verify_token('k' * 32, 'Bearer ' + t)
        self.assertEqual((claims['email'], claims['sub']), ('a@example.com', '7'))
        self.assertNotIn('refresh_token', claims)

    def test_rejects_tampered_wrong_key_malformed(self):
        t = auth.issue_token('k' * 32, {'email': 'a@example.com', 'sub': '7'})
        self.assertIsNone(auth.verify_token('other' * 8, 'Bearer ' + t))
        self.assertIsNone(auth.verify_token('k' * 32, 'Bearer ' + t[:-2] + 'xx'))
        self.assertIsNone(auth.verify_token('k' * 32, t))
        self.assertIsNone(auth.verify_token('k' * 32, None))

    def test_other_domain_and_missing_sub_rejected(self):
        self.assertIsNone(auth.verify_token('k' * 32, token('x@gmail.com')))
        self.assertIsNone(auth.verify_token('k' * 32, token('a@example.com', sub='')))

    def test_expired(self):
        t = auth.issue_token('k' * 32, {'email': 'a@example.com', 'sub': '7'})
        with mock.patch.object(auth, 'TOKEN_TTL_SECONDS', -1):
            self.assertIsNone(auth.verify_token('k' * 32, 'Bearer ' + t))

    def test_cron_secret(self):
        with mock.patch.dict(os.environ, {'CRON_SECRET': 'a' * 24}):
            self.assertTrue(auth.cron_authorized('Bearer ' + 'a' * 24))
            self.assertFalse(auth.cron_authorized('Bearer ' + 'b' * 24))
            self.assertFalse(auth.cron_authorized(None))
        with mock.patch.dict(os.environ, {'CRON_SECRET': ''}):
            self.assertFalse(auth.cron_authorized('Bearer '))
        with mock.patch.dict(os.environ, {'CRON_SECRET': 'short'}):
            self.assertFalse(auth.cron_authorized('Bearer short'))


class MeEndpoint(unittest.TestCase):
    def test_me(self):
        self.assertEqual(authed_client().get('/api/auth/me').get_json()['user']['email'], 'owner@example.com')
        self.assertEqual(api.app.test_client().get('/api/auth/me').status_code, 401)
        self.assertEqual(authed_client('x@y.com').get('/api/auth/me').status_code, 401)

    def test_removed_endpoints(self):
        c = authed_client()
        self.assertEqual(c.post('/api/auth/refresh', json={}).status_code, 404)   # used to accept client secrets
        self.assertEqual(c.post('/api/auth/setup', json={}).status_code, 404)


def fake_google(email, verified=True, refresh='RT-SECRET', hd=None, sub='42'):
    def post(url, data=None, **kw):
        r = mock.Mock(); r.json.return_value = {'access_token': 'at', 'refresh_token': refresh}; return r
    def get(url, **kw):
        info = {'email': email, 'name': 'N', 'id': sub, 'verified_email': verified}
        if hd: info['hd'] = hd
        r = mock.Mock(); r.json.return_value = info; return r
    return mock.patch.object(api.requests, 'post', post), mock.patch.object(api.requests, 'get', get)


class MemVault:
    def __init__(self): self.d = {}
    def put(self, sub, email, rt, last_run=None): self.d[sub] = {'sub': sub, 'email': email, 'refresh_token': rt, 'last_run': last_run or 0}
    def get(self, sub): return self.d.get(sub)
    def delete(self, sub): self.d.pop(sub, None)
    def touch(self, sub): pass
    def users(self): return list(self.d.values())


class CallbackTests(unittest.TestCase):
    def setUp(self):
        self.vault = MemVault()
        self.patches = [mock.patch.object(api, '_vault', lambda: self.vault),
                        mock.patch.object(api, 'admin_credentials', lambda: object()),
                        mock.patch.dict(os.environ, {'FRONTEND_URL': 'https://app.example'})]
        for p in self.patches: p.start()
    def tearDown(self):
        for p in self.patches: p.stop()

    def go(self, email, **kw):
        c = api.app.test_client()
        with c.session_transaction() as s:
            s['oauth_state'] = 'st'
        p, g = fake_google(email, **kw)
        with p, g:
            return c.get('/auth/google/callback?state=st&code=c')

    def test_student_gets_token_and_token_goes_to_vault_not_browser(self):
        r = self.go('student@example.com', sub='s1')
        body = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('apiToken', body)
        self.assertNotIn('RT-SECRET', body)
        self.assertNotIn('client_secret', body)
        self.assertIn('"https://app.example"', body)                    # targetOrigin is not '*'
        self.assertNotIn(", '*')", body)
        self.assertEqual(self.vault.d['s1']['refresh_token'], 'RT-SECRET')

    def test_other_domain_refused_and_nothing_stored(self):
        r = self.go('x@gmail.com')
        self.assertEqual(r.status_code, 403)
        self.assertNotIn('apiToken', r.get_data(as_text=True))
        self.assertEqual(self.vault.d, {})

    def test_hd_mismatch_refused(self):
        self.assertEqual(self.go('student@example.com', hd='other.org').status_code, 403)

    def test_bad_state_refused(self):
        c = api.app.test_client()
        with c.session_transaction() as s:
            s['oauth_state'] = 'st'
        self.assertEqual(c.get('/auth/google/callback?state=other&code=c').status_code, 400)

    def test_returning_user_without_new_refresh_token_keeps_old_one(self):
        self.vault.put('s1', 'student@example.com', 'OLD')
        r = self.go('student@example.com', sub='s1', refresh=None)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.vault.d['s1']['refresh_token'], 'OLD')

    def test_new_user_without_refresh_token_is_told_how_to_fix(self):
        self.assertEqual(self.go('student@example.com', sub='new', refresh=None).status_code, 400)

    def test_error_page_does_not_reflect_exception_text(self):
        c = api.app.test_client()
        with c.session_transaction() as s:
            s['oauth_state'] = 'st'
        with mock.patch.object(api.requests, 'post', side_effect=RuntimeError('<script>x</script>')):
            r = c.get('/auth/google/callback?state=st&code=c')
        self.assertNotIn('<script>x', r.get_data(as_text=True))


class BootstrapTests(unittest.TestCase):
    def go(self, email):
        c = api.app.test_client()
        with c.session_transaction() as s:
            s['oauth_state'] = 'st'
        p, g = fake_google(email)
        with p, g, mock.patch.object(api, 'admin_credentials', lambda: None):
            return c.get('/auth/google/callback?state=st&code=c')

    def test_admin_sees_refresh_token_once_others_do_not(self):
        admin, student = self.go('owner@example.com'), self.go('student@example.com')
        self.assertIn('RT-SECRET', admin.get_data(as_text=True))
        self.assertNotIn('apiToken', admin.get_data(as_text=True))
        self.assertNotIn('RT-SECRET', student.get_data(as_text=True))
        self.assertEqual(student.status_code, 503)


class EndpointProtectionTests(unittest.TestCase):
    def test_ai_endpoints_need_login(self):
        anon = api.app.test_client()
        self.assertEqual(anon.post('/api/ai/chat', json={'message': 'hi'}).status_code, 401)
        self.assertEqual(anon.post('/api/ai/prioritize', json={'events': [1]}).status_code, 401)
        self.assertNotEqual(authed_client().post('/api/ai/prioritize', json={'events': []}).status_code, 401)

    def test_fake_endpoints_are_gone(self):
        c = authed_client()
        self.assertEqual(c.post('/api/notifications/send', json={}).status_code, 404)
        self.assertEqual(c.get('/api/analytics/dashboard').status_code, 404)

    def test_every_data_route_is_protected(self):
        """Any route that is not explicitly public must answer 401 to a stranger."""
        public = {'/health', '/auth/google', '/auth/google/callback', '/api/cron/scan'}
        anon = api.app.test_client()
        bad = []
        for rule in api.app.url_map.iter_rules():
            if rule.rule in public:
                continue
            path = rule.rule.replace('<event_id>', 'x').replace('<action>', 'accept').replace('<path:filename>', 'a')
            for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
                r = anon.open(path, method=method, json={} if method in ('POST', 'PUT', 'DELETE') else None)
                if r.status_code != 401:
                    bad.append(f'{method} {rule.rule} -> {r.status_code}')
        self.assertEqual(bad, [])

    def test_cron_route_needs_its_secret(self):
        self.assertEqual(api.app.test_client().post('/api/cron/scan').status_code, 401)


if __name__ == '__main__':
    unittest.main()
