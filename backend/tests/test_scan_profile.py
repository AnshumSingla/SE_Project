import unittest
from tests import stubs  # noqa: F401
from tests.test_phase0 import ScanTests


class ScanProfileTests(ScanTests):
    def test_profile_filters_into_filtered_out_with_reason(self):
        j = self.post(profile={'exclude_keywords': 'internship'}).get_json()
        self.assertEqual([e['email_id'] for e in j['emails']], [])
        fo = j['filtered_out']
        self.assertEqual([e['email_id'] for e in fo], ['m1'])
        self.assertIn('internship', fo[0]['relevance']['reason'])
        self.assertEqual(j['summary']['filtered_by_profile'], 1)

    def test_no_profile_shows_everything(self):
        j = self.post().get_json()
        self.assertEqual(j['filtered_out'], [])
        self.assertTrue(j['emails'][0]['relevance']['relevant'])

    def test_garbage_profile_is_ignored(self):
        j = self.post(profile='not a dict').get_json()
        self.assertEqual([e['email_id'] for e in j['emails']], ['m1'])


del ScanTests
if __name__ == '__main__':
    unittest.main()
