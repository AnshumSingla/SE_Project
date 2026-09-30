"""Phase 0 regression tests. Run from backend/:  python -m unittest tests.test_phase0 -v
Google/Flask-CORS libraries are replaced by tests/stubs.py, so no network or real account is used."""
import base64, os, sys, unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from tests import stubs
stubs.install()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))   # backend/
os.environ.setdefault('DEFAULT_TIMEZONE', 'Asia/Kolkata')

os.environ['ALLOWED_DOMAIN'] = 'example.com'
os.environ['ADMIN_EMAIL'] = 'owner@example.com'
import api_service as api
import auth
from gmail_integration import GmailIntegrator, build_search_query, should_skip_message
from tests.stubs import FakeCredentials, FakeHttpError


api.user_credentials = lambda claims: FakeCredentials(token='ya29.real', refresh_token='rt')   # server-held creds


def auth_header(email='owner@example.com', sub='1'):
    return {'Authorization': 'Bearer ' + auth.issue_token(api.SECRET_KEY, {'email': email, 'name': 'O', 'sub': sub})}


def authed_client(email='owner@example.com', sub='1'):
    c = api.app.test_client()
    c.environ_base['HTTP_AUTHORIZATION'] = auth_header(email, sub)['Authorization']
    return c


def future(days=20):
    d = datetime.now() + timedelta(days=days)
    return d, d.strftime('%B %d, %Y').replace(' 0', ' ')


def gmail_msg(mid, subject, body, sender, labels=('INBOX',), thread=None):
    data = base64.urlsafe_b64encode(body.encode()).decode()
    return {'id': mid, 'threadId': thread or mid, 'snippet': body[:80], 'labelIds': list(labels),
            'payload': {'mimeType': 'text/plain', 'body': {'data': data},
                        'headers': [{'name': 'Subject', 'value': subject}, {'name': 'From', 'value': sender},
                                    {'name': 'Date', 'value': 'Mon, 01 Jun 2026 10:00:00 +0000'}]}}


class FakeGmail:
    def __init__(self, messages):
        self.messages, self.list_q, self.fetched = messages, None, []
    def users(self): return self
    def messages(self): return self   # noqa (shadowed below)


class FakeGmailService:
    def __init__(self, messages):
        self._m = {m['id']: m for m in messages}; self.query = None; self.fetched = []
    def users(self): return self
    def messages(self): return self
    def list(self, userId, q, maxResults):
        self.query = q
        ids = [{'id': i, 'threadId': self._m[i]['threadId']} for i in self._m]
        return mock.Mock(execute=lambda: {'messages': ids})
    def get(self, userId, id, format):
        self.fetched.append(id)
        return mock.Mock(execute=lambda: self._m[id])


class FakeCalendar:
    def __init__(self, existing_ids=(), events=()):
        self.inserted, self.existing, self._events = [], set(existing_ids), list(events)
    def events(self): return self
    def insert(self, calendarId, body):
        def run():
            if body['id'] in self.existing: raise FakeHttpError(409)
            self.existing.add(body['id']); self.inserted.append(body)
            return {'id': body['id'], 'htmlLink': 'http://cal/' + body['id']}
        return mock.Mock(execute=run)
    def list(self, **kw): return mock.Mock(execute=lambda: {'items': self._events})


class EventIdTests(unittest.TestCase):
    def test_valid_and_deterministic(self):
        a, b = api.make_event_id('18f3abc'), api.make_event_id('18f3abc')
        self.assertEqual(a, b)
        self.assertNotEqual(a, api.make_event_id('18f3abd'))
        self.assertNotEqual(a, api.make_event_id('18f3abc', 1))
        self.assertRegex(a, r'^[a-v0-9]{5,1024}$')   # Google's allowed alphabet/length

    def test_credentials_need_a_user_token_and_client_creds_are_ignored(self):
        with api.app.test_request_context():
            self.assertIsNone(api.resolve_credentials({'token': 't', 'refresh_token': 'r'}, 'ya29.attacker'))
        with api.app.test_request_context(headers=auth_header()):
            self.assertEqual(api.resolve_credentials({'token': 'evil'}, 'evil').token, 'ya29.real')
        with api.app.test_request_context(headers=auth_header('someone@else.com')):
            self.assertIsNone(api.resolve_credentials())         # wrong domain


class GmailFilterTests(unittest.TestCase):
    def test_query_excludes_noise_and_self(self):
        q = build_search_query(7, '', True)
        for frag in ('-from:me', '-category:promotions', '-category:social', '-in:drafts', 'after:'):
            self.assertIn(frag, q)
        self.assertNotIn('from:noreply', q)
        self.assertNotIn('-from:me', build_search_query(7, '', False))
        self.assertIn('(custom OR terms)', build_search_query(7, 'custom OR terms'))

    def test_label_rules(self):
        self.assertTrue(should_skip_message(['DRAFT']))
        self.assertTrue(should_skip_message(['INBOX', 'SENT'], True))        # self-sent test mail
        self.assertFalse(should_skip_message(['INBOX', 'SENT'], False))      # opted in
        self.assertTrue(should_skip_message(['SENT'], False))                # sent to someone else
        self.assertFalse(should_skip_message(['INBOX', 'UNREAD']))


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.client = authed_client()
        _, ds = future()
        self.ds = ds
        msgs = [
            gmail_msg('m1', f'Software Engineer Internship - Application Deadline {ds}',
                      f'Apply now. The application deadline is {ds} at 11:59 PM.', 'careers@acme.com', thread='t1'),
            gmail_msg('m2', f'Reminder: Software Engineer Internship - Application Deadline {ds}',
                      f'Reminder: application deadline is {ds}.', 'careers@acme.com', thread='t1'),
            gmail_msg('m3', 'test application deadline', f'test job application deadline {ds}',
                      'me@gmail.com', labels=('INBOX', 'SENT')),
            gmail_msg('m4', 'Already handled internship', f'application deadline {ds}', 'hr@x.com'),
            gmail_msg('m5', 'draft', f'job application deadline {ds}', 'me@gmail.com', labels=('DRAFT',)),
            gmail_msg('m6', 'Calendar: job interview', f'interview deadline {ds}',
                      'calendar-notification@google.com'),
        ]
        self.gsvc = FakeGmailService(msgs)
        def new_system(creds):
            s = api.IntegratedEmailReminderSystem(use_llm=False)
            g = GmailIntegrator(credentials=creds); g.service = self.gsvc
            s.gmail = g
            return s
        self.patches = [
            mock.patch.object(api, '_new_system', new_system),
            mock.patch.object(api, '_ensure_valid_credentials', lambda c: c),
            mock.patch.object(api, '_get_processed_gmail_ids', lambda credentials_override=None: {'m4'}),
            mock.patch.object(api, '_calendar_service',
                              lambda c: (_ for _ in ()).throw(AssertionError('scan must not touch Calendar'))),
        ]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in self.patches: p.stop()

    def post(self, **extra):
        body = {'user_id': 'u1', 'access_token': 'ya29.real'}; body.update(extra)
        return self.client.post('/api/emails/scan', json=body)

    def test_scan_is_readonly_filtered_and_deduped(self):
        r = self.post(); j = r.get_json()
        self.assertEqual(r.status_code, 200, j)
        ids = [e['email_id'] for e in j['emails']]
        self.assertEqual(ids, ['m1'], f'only the real mail should remain, got {ids}')   # m2 same thread, m3 self, m4 handled, m5 draft, m6 gcal
        self.assertNotIn('m4', self.gsvc.fetched)                                        # skipped BEFORE fetching
        self.assertEqual(j['summary']['calendar_events_created'], 0)
        self.assertEqual(j['emails'][0]['event_id'], api.make_event_id('m1'))
        self.assertEqual(j['emails'][0]['deadline']['date'], future()[0].strftime('%Y-%m-%d'))
        self.assertIn('-from:me', self.gsvc.query)

    def test_self_sent_opt_in(self):
        j = self.post(include_self_sent=True).get_json()
        self.assertIn('m3', [e['email_id'] for e in j['emails']])
        self.assertNotIn('-from:me', self.gsvc.query)

    def test_requires_real_credentials(self):
        r = api.app.test_client().post('/api/emails/scan', json={'user_id': 'u1', 'access_token': 'ya29.stolen'})
        self.assertEqual(r.status_code, 401)

    def test_no_traceback_leak(self):
        with mock.patch.object(api, '_new_system', side_effect=RuntimeError('secret detail')):
            j = self.post().get_json()
        self.assertNotIn('traceback', j); self.assertNotIn('secret detail', str(j))


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.client = authed_client(); self.cal = FakeCalendar()
        self.patches = [mock.patch.object(api, '_calendar_service', lambda c: self.cal),
                        mock.patch.object(api, '_ensure_valid_credentials', lambda c: c)]
        for p in self.patches: p.start()
        d, _ = future()
        self.email = {'email_id': 'm1', 'subject': 'SWE Internship', 'sender': 'careers@acme.com',
                      'snippet': 'apply', 'deadline': {'has_deadline': True, 'date': d.strftime('%Y-%m-%d'),
                                                       'time': None, 'type': 'application', 'description': 'd'}}
    def tearDown(self):
        for p in self.patches: p.stop()
    def post(self, emails, **extra):
        body = {'user_id': 'u1', 'access_token': 'ya29.real', 'emails': emails}; body.update(extra)
        return self.client.post('/api/calendar/reminders', json=body)

    def test_creates_once_then_reports_duplicate(self):
        j1 = self.post([self.email]).get_json()
        self.assertTrue(j1['success'], j1); self.assertEqual(len(j1['created_events']), 1)
        ev = self.cal.inserted[0]
        self.assertEqual(ev['id'], api.make_event_id('m1'))
        priv = ev['extendedProperties']['private']
        self.assertEqual((priv['source'], priv['gmailMessageId']), ('smart_reminder', 'm1'))
        self.assertIn('23:59', ev['start']['dateTime'])
        j2 = self.post([self.email]).get_json()            # same request again (double click / second scan)
        self.assertEqual(len(j2['created_events']), 0); self.assertEqual(len(j2['duplicate_events']), 1)
        self.assertEqual(len(self.cal.inserted), 1)

    def test_same_batch_twice_is_single_event(self):
        j = self.post([self.email, dict(self.email)]).get_json()
        self.assertEqual((len(j['created_events']), len(j['duplicate_events'])), (1, 1))

    def test_deleted_event_is_not_recreated(self):
        self.cal.existing.add(api.make_event_id('m1'))     # Google keeps deleted IDs reserved -> 409
        j = self.post([self.email]).get_json()
        self.assertEqual((len(j['created_events']), len(j['duplicate_events'])), (0, 1))

    def test_past_and_missing(self):
        past = dict(self.email, email_id='m9', deadline=dict(self.email['deadline'], date='2020-01-01'))
        none = {'email_id': 'm8', 'deadline': {'has_deadline': False}}
        j = self.post([past, none]).get_json()
        self.assertEqual(len(j['skipped_events']), 2); self.assertEqual(self.cal.inserted, [])

    def test_auth_required(self):
        r = api.app.test_client().post('/api/calendar/reminders', json={'user_id': 'u1', 'emails': [self.email]})
        self.assertEqual(r.status_code, 401)


class UpcomingTests(unittest.TestCase):
    def test_only_app_events_and_correct_days(self):
        now = datetime.now(timezone.utc)
        ist = timezone(timedelta(hours=5, minutes=30))
        in2 = (now + timedelta(days=2, hours=1)).astimezone(ist).isoformat()     # offset form, used to crash days calc
        in20 = (now + timedelta(days=20, hours=1)).astimezone(ist).isoformat()
        ev = lambda i, s, start, **k: dict({'id': i, 'summary': s, 'start': {'dateTime': start}}, **k)
        events = [
            ev('a', '📧 Job Deadline: X', in2, extendedProperties={'private': {'source': 'smart_reminder', 'deadlineType': 'interview'}}),
            ev('b', '📧 Legacy untagged', in20),
            ev('c', 'Dentist appointment', in2),                         # personal -> must not appear
            ev('d', 'Team standup', in20, extendedProperties={'private': {'foo': 'bar'}}),
            ev('e', '📧 Cancelled', in2, status='cancelled'),
        ]
        cal = FakeCalendar(events=events)
        with mock.patch.object(api, '_calendar_service', lambda c: cal), \
             mock.patch.object(api, '_ensure_valid_credentials', lambda c: c):
            j = authed_client().get('/api/calendar/upcoming', query_string={'user_id': 'u1', 'access_token': 'ya29.real'}).get_json()
        got = {e['event_id']: e for e in j['upcoming_events']}
        self.assertEqual(sorted(got), ['a', 'b'])
        self.assertEqual((got['a']['days_until'], got['a']['urgency'], got['a']['deadline_type']), (2, 'high', 'interview'))
        self.assertEqual((got['b']['days_until'], got['b']['urgency']), (20, 'low'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
