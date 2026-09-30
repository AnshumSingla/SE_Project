import unittest
from datetime import datetime, timedelta

from tests.test_phase0 import (api, FakeCalendar, FakeGmailService, FakeHttpError, GmailIntegrator,
                               future, gmail_msg)
import scanner
import core
from drive_store import PROFILE_FILE, STATE_FILE


class MemStore:
    """Stands in for DriveStore."""
    def __init__(self, **files):
        self.files = dict(files); self.writes = []
    def load(self, name): return self.files.get(name)
    def save(self, name, data): self.files[name] = data; self.writes.append(name)


def system_for(messages):
    g = GmailIntegrator(credentials=None); g.service = FakeGmailService(messages)
    s = api.IntegratedEmailReminderSystem(use_llm=False); s.gmail = g
    return s


class ScannerTests(unittest.TestCase):
    def setUp(self):
        d, ds = future()
        self.day = d.strftime('%Y-%m-%d')
        self.clear = gmail_msg('c1', f'Software Engineer Internship - Application Deadline {ds}',
                               f'Apply now. The application deadline is {ds} at 11:59 PM.', 'careers@acme.com')
        # no year -> extractor flags it (year inferred) or gives lower confidence: must go to review
        self.vague = gmail_msg('v1', 'Hiring update', 'Please submit the form by next Friday for the internship job.', 'hr@x.com')
        self.other_branch = gmail_msg('o1', f'Campus drive {ds}',
                                      f'Eligible branches: Mechanical and Civil only. Application deadline {ds}.', 'cell@x.edu')
        self.none = gmail_msg('n1', 'job newsletter', 'Nothing to see here about any job.', 'news@x.com')

    def run_scan(self, msgs, store=None, cal=None, processed=(), **kw):
        store = store or MemStore()
        cal = cal or FakeCalendar()
        out = scanner.run_scan(system_for(msgs), cal, store, processed, FakeHttpError,
                               now=kw.pop('now', datetime.now()), **kw)
        return out, store, cal

    def test_confident_event_is_added_with_full_body(self):
        out, store, cal = self.run_scan([self.clear])
        self.assertEqual((out['added'], out['for_review']), (1, 0))
        self.assertEqual(cal.inserted[0]['id'], core.make_event_id('c1', 0))
        self.assertIn(self.day, cal.inserted[0]['start']['dateTime'])
        self.assertIn('c1', store.files[STATE_FILE]['seen'])
        self.assertEqual(store.writes, [STATE_FILE])                      # one Drive write per scan

    def test_second_run_adds_nothing(self):
        _, store, cal = self.run_scan([self.clear])
        out, _, _ = self.run_scan([self.clear], store=store, cal=cal)
        self.assertEqual(out['added'], 0)
        self.assertEqual(len(cal.inserted), 1)

    def test_even_if_seen_list_is_lost_calendar_ids_prevent_duplicates(self):
        _, store, cal = self.run_scan([self.clear])
        store.files.pop(STATE_FILE)
        out, _, _ = self.run_scan([self.clear], store=store, cal=cal, processed={'c1'})
        self.assertEqual(out['added'], 0)
        # and even with no processed list at all, the 409 makes it a no-op
        out, _, _ = self.run_scan([self.clear], store=MemStore(), cal=cal)
        self.assertEqual(out['added'], 0)
        self.assertEqual(len(cal.inserted), 1)

    def test_profile_filters_other_branch_into_filtered_list(self):
        store = MemStore(**{PROFILE_FILE: {'disciplines': 'Computer Science'}})
        out, store, cal = self.run_scan([self.other_branch], store=store)
        self.assertEqual((out['added'], out['filtered_out']), (0, 1))
        self.assertEqual(cal.inserted, [])
        self.assertIn('mechanical', store.files[STATE_FILE]['filtered'][0]['relevance']['reason'])

    def test_auto_add_off_sends_everything_to_review(self):
        store = MemStore(**{PROFILE_FILE: {'auto_add': 'off'}})
        out, store, cal = self.run_scan([self.clear], store=store)
        self.assertEqual((out['added'], out['for_review']), (0, 1))
        self.assertEqual(cal.inserted, [])

    def test_paused_does_nothing(self):
        store = MemStore(**{PROFILE_FILE: {'scan_paused': True}})
        out, store, cal = self.run_scan([self.clear], store=store)
        self.assertEqual(out['status'], 'paused')
        self.assertEqual((cal.inserted, store.writes), ([], []))

    def test_accept_and_dismiss_from_review(self):
        store = MemStore(**{PROFILE_FILE: {'auto_add': 'off'}})
        _, store, cal = self.run_scan([self.clear], store=store)
        eid = core.make_event_id('c1', 0)
        r = scanner.resolve_item(store, eid, 'accept', cal, FakeHttpError)
        self.assertEqual(r['status'], 'created')
        self.assertEqual(len(cal.inserted), 1)
        self.assertEqual(store.files[STATE_FILE]['review'], [])
        self.assertEqual(scanner.resolve_item(store, 'nope', 'accept', cal, FakeHttpError)['status'], 'not_found')

    def test_dismissed_never_comes_back(self):
        store = MemStore(**{PROFILE_FILE: {'auto_add': 'off'}})
        _, store, cal = self.run_scan([self.clear], store=store)
        eid = core.make_event_id('c1', 0)
        scanner.resolve_item(store, eid, 'dismiss', cal, FakeHttpError)
        store.files[STATE_FILE]['seen'] = []                              # force re-analysis
        out, store, _ = self.run_scan([self.clear], store=store, cal=cal)
        self.assertEqual((out['for_review'], out['added']), (0, 0))

    def test_failed_insert_goes_to_review_not_lost(self):
        class Boom(FakeCalendar):
            def insert(self, calendarId, body):
                from unittest import mock
                return mock.Mock(execute=mock.Mock(side_effect=RuntimeError('quota')))
        out, store, _ = self.run_scan([self.clear], cal=Boom())
        self.assertEqual((out['added'], out['for_review'], out['errors']), (0, 1, 1))

    def test_days_back_uses_last_scan_with_overlap(self):
        now = datetime(2026, 9, 30, 12)
        self.assertEqual(scanner._days_back(None, now), 7)
        self.assertEqual(scanner._days_back((now - timedelta(hours=6)).isoformat(), now), 2)
        self.assertEqual(scanner._days_back((now - timedelta(days=90)).isoformat(), now), 14)
        self.assertEqual(scanner._days_back('garbage', now), 7)

    def test_state_is_capped(self):
        store = MemStore()
        st = scanner.empty_state(); st['seen'] = [str(i) for i in range(3000)]
        scanner.save_state(store, st)
        self.assertEqual(len(store.files[STATE_FILE]['seen']), scanner.CAPS['seen'])
        self.assertEqual(store.files[STATE_FILE]['seen'][-1], '2999')


class DecideTests(unittest.TestCase):
    def cand(self, conf, flags=()):
        return {'deadline': {'confidence': conf, 'flags': list(flags)}}

    def test_policy(self):
        self.assertEqual(scanner.decide(self.cand(0.8), 'confident'), 'add')
        self.assertEqual(scanner.decide(self.cand(0.6), 'confident'), 'review')
        self.assertEqual(scanner.decide(self.cand(0.9, ['weekday_mismatch']), 'confident'), 'review')
        self.assertEqual(scanner.decide(self.cand(0.8, ['weekday_ok']), 'confident'), 'add')       # corroboration, not a warning
        self.assertEqual(scanner.decide(self.cand(0.8, ['weekday_corrected']), 'confident'), 'review')
        self.assertEqual(scanner.decide(self.cand(0.1), 'all'), 'add')
        self.assertEqual(scanner.decide(self.cand(1.0), 'off'), 'review')


if __name__ == '__main__':
    unittest.main()
