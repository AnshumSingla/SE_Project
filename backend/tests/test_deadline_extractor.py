import json
import unittest
from datetime import datetime
from unittest import mock

import deadline_extractor as de

RECEIVED = datetime(2026, 9, 27, 10, 0)
EMAIL = {'subject': 'Online test', 'sender': 'cell@x.edu',
         'body': 'Your online test is on 5 October 2026 at 10:00 AM. Venue: Lab 3.'}


def llm_returning(obj):
    return lambda prompt, schema: json.dumps(obj)


def good_event(**kw):
    e = {'kind': 'test', 'title': 'Online test', 'date': '2026-10-05', 'start_time': '10:00',
         'evidence': 'on 5 October 2026 at 10:00 AM'}
    e.update(kw)
    return e


class ValidateLLM(unittest.TestCase):
    def run_validate(self, events, email=EMAIL):
        return de.validate_llm_output({'audience': 'personal', 'events': events}, email, RECEIVED)

    def test_accepts_grounded_event(self):
        out = self.run_validate([good_event()])
        self.assertEqual(len(out['events']), 1)
        self.assertEqual(out['events'][0]['start'], '10:00')
        self.assertEqual(out['audience'], 'personal')

    def test_drops_invented_evidence(self):
        out = self.run_validate([good_event(evidence='on 6 October at noon')])
        self.assertEqual(out['events'], [])
        self.assertEqual(out['dropped'][0]['reason'], 'evidence_not_in_email')

    def test_drops_out_of_range_and_bad_dates(self):
        out = self.run_validate([good_event(date='2019-01-01'), good_event(date='nope')])
        self.assertEqual(out['events'], [])
        self.assertEqual({d['reason'] for d in out['dropped']}, {'date_out_of_range', 'bad_date'})

    def test_bad_shape_raises(self):
        with self.assertRaises(ValueError):
            de.validate_llm_output({'nothing': 1}, EMAIL, RECEIVED)

    def test_invalid_time_becomes_none(self):
        out = self.run_validate([good_event(start_time='25:99')])
        self.assertIsNone(out['events'][0]['start'])

    def test_weekday_mismatch_lowers_confidence(self):
        email = {'subject': 's', 'body': 'Test on Monday 5 October 2026'}  # 5 Oct 2026 is a Monday
        ok = self.run_validate([good_event(date='2026-10-05', evidence='Monday 5 October 2026', confidence=0.9)], email)
        bad = self.run_validate([good_event(date='2026-10-06', evidence='Monday 5 October 2026', confidence=0.9)], email)
        self.assertEqual(ok['events'][0]['flags'], [])
        self.assertIn('weekday_mismatch', bad['events'][0]['flags'])
        self.assertLess(bad['events'][0]['confidence'], ok['events'][0]['confidence'])


class Entry(unittest.TestCase):
    def test_llm_used_when_valid(self):
        out = de.extract_events(EMAIL, RECEIVED, llm=llm_returning({'audience': 'broadcast', 'events': [good_event()]}))
        self.assertEqual(out['method'], 'llm')

    def test_falls_back_on_llm_error(self):
        def boom(p, s):
            raise RuntimeError('down')
        out = de.extract_events(EMAIL, RECEIVED, llm=boom)
        self.assertEqual(out['method'], 'rules_fallback')
        self.assertEqual([e['date'] for e in out['events']], ['2026-10-05'])

    def test_falls_back_on_bad_json(self):
        out = de.extract_events(EMAIL, RECEIVED, llm=lambda p, s: 'not json')
        self.assertEqual(out['method'], 'rules_fallback')

    def test_prompt_marks_email_as_data(self):
        p = de.build_prompt(EMAIL, RECEIVED)
        self.assertIn('DATA', p)
        self.assertIn('Sunday, 27 September 2026', p)


class Rules(unittest.TestCase):
    def test_past_date_is_ignored(self):
        email = {'subject': 'Update', 'body': 'Registration closes on 10 October 2026. Last year it was on 12 September 2026.'}
        out = de.extract_rule_based(email, RECEIVED)
        self.assertEqual([e['date'] for e in out['events']], ['2026-10-10'])

    def test_dmy_not_mdy(self):
        out = de.extract_rule_based({'subject': 'Deadline', 'body': 'Submit by 05/11/2026.'}, RECEIVED)
        self.assertEqual([e['date'] for e in out['events']], ['2026-11-05'])

    def test_no_dates_no_events(self):
        out = de.extract_rule_based({'subject': 'Hello', 'body': 'Please check the portal.'}, RECEIVED)
        self.assertEqual(out['events'], [])


class Gemini(unittest.TestCase):
    def test_request_shape(self):
        client = de.GeminiClient('KEY', model='m1')
        resp = mock.Mock()
        resp.json.return_value = {'candidates': [{'content': {'parts': [{'text': '{"events": []}'}]}}]}
        with mock.patch('requests.post', return_value=resp) as post:
            text = client('hi', de.LLM_SCHEMA)
        self.assertEqual(text, '{"events": []}')
        args, kw = post.call_args
        self.assertIn('models/m1:generateContent', args[0])
        self.assertEqual(kw['headers']['x-goog-api-key'], 'KEY')
        self.assertNotIn('KEY', args[0])
        self.assertEqual(kw['json']['generationConfig']['responseMimeType'], 'application/json')


if __name__ == '__main__':
    unittest.main()
