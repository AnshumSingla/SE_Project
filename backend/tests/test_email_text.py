"""Body extraction tests (email_text.py). Run from backend/:  python -m unittest tests.test_email_text -v"""
import base64, json, os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))   # backend/
from email_text import extract_body, html_to_text, list_attachments, strip_quoted_reply

FIXTURES = json.load(open(os.path.join(os.path.dirname(__file__), 'fixtures', 'emails.json'), encoding='utf-8'))['emails']


def b64(s, pad=True, enc='utf-8'):
    d = base64.urlsafe_b64encode(s.encode(enc)).decode()
    return d if pad else d.rstrip('=')


def payload_from_fixture(fx):
    """Build a Gmail-API-shaped payload from a fixture's parts."""
    parts = [{'mimeType': p['mimeType'], 'body': {'data': b64(p['text'])}} for p in fx['email']['parts']]
    if len(parts) == 1:
        return parts[0]
    root = {'mimeType': 'multipart/alternative', 'parts': parts}
    if fx['email'].get('attachments'):
        root = {'mimeType': 'multipart/mixed', 'parts': [root] + [
            {'mimeType': 'application/octet-stream', 'filename': n, 'body': {'attachmentId': 'x'}}
            for n in fx['email']['attachments']]}
    return root


class ExlEmailTests(unittest.TestCase):
    """The real placement-cell mail: plain+html alternative, a table, an attachment."""
    def setUp(self):
        self.fx = next(f for f in FIXTURES if f['id'] == 'real_thapar_exl_aptitude')
        self.payload = payload_from_fixture(self.fx)

    def test_alternative_not_duplicated(self):
        body = extract_body(self.payload)
        self.assertEqual(body.count('Aptitude Test'), 1, body)
        self.assertEqual(body.count('Dear Students'), 1)

    def test_table_row_kept_together(self):
        body = extract_body(self.payload)
        self.assertIn('Aptitude Test\t17-Sep-26\tThursday\t7:30 PM-8:15 PM\tVirtual', body)
        self.assertIn('Interviews\tTo be shared later', body)

    def test_html_only_table_becomes_rows_not_a_run_on(self):
        html = next(p['text'] for p in self.fx['email']['parts'] if p['mimeType'] == 'text/html')
        text = html_to_text(html)
        self.assertIn('Aptitude Test\t17-Sep-26\tThursday\t7:30 PM-8:15 PM\tVirtual', text)
        self.assertNotIn('Test17-Sep', text)                 # the old regex strip produced this
        self.assertNotIn('<', text)

    def test_attachments_listed_not_in_body(self):
        self.assertEqual(list_attachments(self.payload), ['EXL_TIET.xlsx'])
        self.assertNotIn('EXL_TIET.xlsx', extract_body(self.payload))


class ReplyAndForwardTests(unittest.TestCase):
    def test_quoted_reply_removed_plain(self):
        fx = next(f for f in FIXTURES if f['id'] == 'syn_reply_quote')
        body = extract_body(payload_from_fixture(fx))
        self.assertIn('Thanks, noted.', body)
        self.assertNotIn('17-Oct-26', body)

    def test_outlook_and_wrapped_markers(self):
        self.assertEqual(strip_quoted_reply('Ok\n\n-----Original Message-----\nFrom: a\nSent: b\nDeadline 5 Nov 2026'), 'Ok')
        self.assertEqual(strip_quoted_reply('Ok\nOn Mon, 14 Sep 2026 at 10:00, X <x@y.z>\nwrote:\n> old date 1 Dec 2026'), 'Ok')
        self.assertEqual(strip_quoted_reply('Ok\n> quoted line\nstill mine'), 'Ok\nstill mine')

    def test_html_blockquote_dropped(self):
        html = '<div>Noted.</div><div class="gmail_quote"><blockquote>old: apply by 3 Dec 2026</blockquote></div>'
        self.assertEqual(html_to_text(html), 'Noted.')

    def test_forwarded_content_kept(self):
        body = 'FYI\n\n---------- Forwarded message ---------\nFrom: Placements <p@u.edu>\nSubject: Test\n\nAptitude test on 17-Oct-26'
        out = strip_quoted_reply(body)
        self.assertIn('Aptitude test on 17-Oct-26', out)


class RobustnessTests(unittest.TestCase):
    def test_unpadded_base64_and_latin1(self):
        p = {'mimeType': 'text/plain',
             'headers': [{'name': 'Content-Type', 'value': 'text/plain; charset="iso-8859-1"'}],
             'body': {'data': b64('Café - deadline', pad=False, enc='latin-1')}}
        self.assertEqual(extract_body(p), 'Café - deadline')   # decoded as latin-1, not mangled

    def test_stub_plain_loses_to_rich_html(self):
        alt = {'mimeType': 'multipart/alternative', 'parts': [
            {'mimeType': 'text/plain', 'body': {'data': b64('View in browser')}},
            {'mimeType': 'text/html', 'body': {'data': b64('<p>' + 'Interview on 3 Nov 2026 at 10:00 AM. ' * 6 + '</p>')}}]}
        self.assertIn('Interview on 3 Nov 2026', extract_body(alt))

    def test_script_style_ignored(self):
        self.assertEqual(html_to_text('<style>p{color:red}</style><script>var d="1 Jan 2030"</script><p>Hello</p>'), 'Hello')

    def test_garbage_does_not_raise(self):
        self.assertEqual(extract_body({'mimeType': 'multipart/mixed', 'parts': [{'mimeType': 'image/png', 'body': {}}]}), '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
