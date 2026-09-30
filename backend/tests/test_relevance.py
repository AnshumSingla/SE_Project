import unittest
import relevance as r

SWE = {'roles': 'Software Engineer', 'disciplines': 'Computer Science', 'graduation_year': 2026, 'cgpa': 7.0}


def chk(subject, body, audience='broadcast', profile=SWE):
    return r.check_relevance({'subject': subject, 'body': body}, profile, audience)


class Canonical(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(r.canonical('Computer Science & Engg'), 'cs')
        self.assertEqual(r.canonical('CSE'), 'cs')
        self.assertEqual(r.canonical('Mechanical Engineering'), 'mechanical')
        self.assertEqual(r.canonical('ECE'), 'ece')
        self.assertIsNone(r.canonical('underwater basket weaving'))

    def test_profile_normalised(self):
        p = r.normalize_profile({'disciplines': 'CSE, IT', 'cgpa': '11', 'graduation_year': '2026', 'junk': 1})
        self.assertEqual(p['discipline_groups'], ['cs'])
        self.assertIsNone(p['cgpa'])
        self.assertEqual(p['graduation_year'], 2026)
        self.assertNotIn('junk', p)


class Filtering(unittest.TestCase):
    def test_other_branch_filtered_with_reason(self):
        out = chk('Campus drive - Tata Motors', 'Eligible branches: Mechanical, Production and Automobile Engineering. Test on 12 Oct.')
        self.assertFalse(out['relevant'])
        self.assertIn('mechanical', out['reason'])

    def test_own_branch_kept(self):
        self.assertTrue(chk('Drive', 'Eligible branches: CSE, IT, ECE.')['relevant'])

    def test_all_branches_kept(self):
        self.assertTrue(chk('Drive', 'Open to all branches. Eligible students can register.')['relevant'])

    def test_personal_never_filtered(self):
        out = chk('Interview', 'Mechanical round for you', audience='personal')
        self.assertTrue(out['relevant'])

    def test_no_restriction_is_kept(self):
        self.assertTrue(chk('Test on Monday', 'Please be on time.')['relevant'])

    def test_word_it_in_prose_is_not_a_branch(self):
        self.assertTrue(chk('Drive', 'Please submit it before the deadline. Eligible students only.')['relevant'])

    def test_batch_mismatch(self):
        out = chk('Hiring', 'Open for 2025 batch only.')
        self.assertFalse(out['relevant'])
        self.assertTrue(chk('Hiring', 'Open for 2026 batch.')['relevant'])

    def test_cgpa_only_in_strict_mode(self):
        body = 'Eligibility: CGPA of 8.0 and above.'
        self.assertTrue(chk('Drive', body)['relevant'])
        self.assertFalse(chk('Drive', body, profile=dict(SWE, strictness='strict'))['relevant'])

    def test_lenient_ignores_branch(self):
        self.assertTrue(chk('Drive', 'Eligible branches: Civil only.', profile=dict(SWE, strictness='lenient'))['relevant'])

    def test_exclude_keyword(self):
        out = chk('Sales internship', 'Apply now', profile=dict(SWE, exclude_keywords='sales'))
        self.assertFalse(out['relevant'])

    def test_empty_profile_keeps_everything(self):
        self.assertTrue(chk('Drive', 'Eligible branches: Civil only.', profile={})['relevant'])


if __name__ == '__main__':
    unittest.main()


class FixtureRelevance(unittest.TestCase):
    """Labelled mails: 'show' must stay visible, 'hide_for_software_profile' must be filtered."""
    def test_fixtures(self):
        from tests.eval_extraction import FIXTURES, extract_body, payload_from_fixture
        for fx in FIXTURES:
            effect = fx['expected'].get('profile_effect')
            if effect not in ('show', 'hide_for_software_profile'):
                continue
            e = fx['email']
            mail = {'subject': e['subject'], 'body': extract_body(payload_from_fixture(fx))}
            out = r.check_relevance(mail, dict(SWE, graduation_year=2027), fx['expected'].get('audience', 'broadcast'))
            self.assertEqual(out['relevant'], effect == 'show', f"{fx['id']}: {out}")
