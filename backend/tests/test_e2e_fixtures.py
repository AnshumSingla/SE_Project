"""End to end on the labelled mails: Gmail (fake) -> scan -> calendar / review / filtered."""
import unittest
from datetime import datetime
from email.utils import format_datetime

from tests.test_phase0 import FakeCalendar, FakeGmailService, FakeHttpError
from tests.test_email_text import payload_from_fixture
from tests.test_scanner import MemStore, system_for
from tests.eval_extraction import FIXTURE_SETS
import scanner
from drive_store import PROFILE_FILE, STATE_FILE

PROFILE = {'roles': 'Software Engineer', 'disciplines': 'Computer Science', 'graduation_year': 2027}


def to_message(fx):
    e = fx['email']
    now = datetime.fromisoformat(fx['now']).replace(tzinfo=None)
    payload = payload_from_fixture(fx)
    payload['headers'] = [{'name': 'Subject', 'value': e['subject']}, {'name': 'From', 'value': e['sender']},
                          {'name': 'Date', 'value': format_datetime(now)}]
    return {'id': fx['id'], 'threadId': fx['id'], 'snippet': '', 'labelIds': e.get('labels', ['INBOX']), 'payload': payload}


class EndToEnd(unittest.TestCase):
    def run_one(self, fx):
        now = datetime.fromisoformat(fx['now']).replace(tzinfo=None)
        store, cal = MemStore(**{PROFILE_FILE: PROFILE}), FakeCalendar()
        scanner.run_scan(system_for([to_message(fx)]), cal, store, set(), FakeHttpError, now=now)
        st = store.files[STATE_FILE]
        added = sorted(ev['start']['dateTime'][:10] for ev in cal.inserted)
        review = sorted(c['deadline']['date'] for c in st['review'])
        filtered = sorted(c['deadline']['date'] for c in st['filtered'])
        return added, review, filtered, cal, st

    def test_labelled_mails(self):
        problems = []
        for fx in FIXTURE_SETS['emails.json']:
            exp = sorted(x['date'] for x in fx['expected']['events'])
            effect = fx['expected'].get('profile_effect')
            added, review, filtered, cal, st = self.run_one(fx)
            where = {'added': added, 'review': review, 'filtered': filtered}
            if effect == 'hide_for_software_profile':
                ok = filtered == exp and not added and not review
            elif effect == 'hide':                       # newsletter / quoted reply: nothing anywhere
                ok = not (added or review or filtered)
            else:                                        # 'show': on the calendar or waiting for review
                ok = sorted(added + review) == exp and not filtered
            if not ok:
                problems.append(f"{fx['id']}: expected {exp} ({effect}) got {where}")
        self.assertEqual(problems, [])

    def test_real_thapar_mails_land_on_calendar_with_times(self):
        for fid, start, end in (('real_thapar_exl_aptitude', '2026-09-17T19:30:00', '2026-09-17T20:15:00'),
                                ('real_thapar_slice_coding', '2026-09-28T07:30:00', '2026-09-28T09:00:00')):
            fx = next(f for f in FIXTURE_SETS['emails.json'] if f['id'] == fid)
            added, review, filtered, cal, st = self.run_one(fx)
            self.assertEqual(len(cal.inserted), 1, (fid, review, filtered))
            self.assertEqual((cal.inserted[0]['start']['dateTime'], cal.inserted[0]['end']['dateTime']), (start, end))
            self.assertEqual(st['review'], [])


if __name__ == '__main__':
    unittest.main()
