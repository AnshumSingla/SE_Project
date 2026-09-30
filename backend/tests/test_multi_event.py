import unittest
from unittest import mock

from tests import stubs  # noqa: F401  (installs fake google modules)
from tests.test_phase0 import ReminderTests, api, future


class MultiEventReminderTests(ReminderTests):
    def test_two_events_from_one_mail_get_distinct_ids_and_times(self):
        d, _ = future()
        day = d.strftime('%Y-%m-%d')
        base = {'email_id': 'm1', 'subject': 'Campus Details', 'sender': 'cell@x.edu', 'snippet': ''}
        test = dict(base, event_index=0, deadline={'has_deadline': True, 'date': day, 'time': '19:30',
                                                   'end_time': '20:15', 'type': 'test', 'title': 'EXL aptitude test'})
        itv = dict(base, event_index=1, deadline={'has_deadline': True, 'date': day, 'time': '21:00',
                                                  'duration_min': 30, 'type': 'interview', 'title': 'EXL interview'})
        j = self.post([test, itv]).get_json()
        self.assertEqual(len(j['created_events']), 2, j)
        ids = [e['id'] for e in self.cal.inserted]
        self.assertEqual(ids, [api.make_event_id('m1', 0), api.make_event_id('m1', 1)])
        self.assertIn('T19:30', self.cal.inserted[0]['start']['dateTime'])
        self.assertIn('T20:15', self.cal.inserted[0]['end']['dateTime'])
        self.assertIn('T21:30', self.cal.inserted[1]['end']['dateTime'])
        self.assertIn('EXL aptitude test', self.cal.inserted[0]['summary'])
        self.assertEqual(self.cal.inserted[1]['extendedProperties']['private']['eventIndex'], '1')
        again = self.post([test, itv]).get_json()
        self.assertEqual((len(again['created_events']), len(again['duplicate_events'])), (0, 2))


del ReminderTests  # don't re-run the inherited tests twice

if __name__ == '__main__':
    unittest.main()
