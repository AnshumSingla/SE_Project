import io
import unittest
import zipfile
from datetime import datetime

import shortlist as sl
import scanner
from drive_store import PROFILE_FILE, STATE_FILE
from tests.test_phase0 import FakeCalendar, FakeHttpError, future, gmail_msg
from tests.test_scanner import MemStore, system_for


def make_xlsx(rows, shared=True):
    """Minimal but valid-enough .xlsx built with zipfile (as Excel/Sheets would write it)."""
    strings, body = [], []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, v in enumerate(row):
            ref = f'{chr(65 + c)}{r}'
            if isinstance(v, (int, float)):
                cells.append(f'<c r="{ref}"><v>{v}</v></c>')
            elif shared:
                strings.append(v); cells.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{v}</t></is></c>')
        body.append(f'<row r="{r}">{"".join(cells)}</row>')
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetData>{"".join(body)}</sheetData></worksheet>')
        if shared:
            z.writestr('xl/sharedStrings.xml', f'<sst xmlns="{ns}">' + ''.join(f'<si><t>{s}</t></si>' for s in strings) + '</sst>')
    return buf.getvalue()


HEADER = ['ID', 'Enrollment Number', 'Name', 'Email']
ROWS = [HEADER, [1, 102103001, 'Asha', 'asha@thapar.edu'], [2, 102103456, 'Anshum', 'anshum@thapar.edu']]


class ReaderTests(unittest.TestCase):
    def test_reads_shared_and_inline_strings_and_numbers(self):
        for shared in (True, False):
            rows = sl.read_xlsx(make_xlsx(ROWS, shared))
            self.assertEqual(rows[2][3], 'anshum@thapar.edu')
            self.assertEqual(sl.norm(rows[2][1]), '102103456')

    def test_csv(self):
        rows = sl.read_table('list.csv', b'Name,Email\nA,a@x.com\n')
        self.assertEqual(rows[1], ['A', 'a@x.com'])

    def test_rejects_junk_big_and_unsafe(self):
        with self.assertRaises(ValueError): sl.read_table('x.xlsx', b'not a zip')
        with self.assertRaises(ValueError): sl.read_table('x.pdf', b'%PDF')
        with self.assertRaises(ValueError): sl.read_table('x.csv', b'a' * (sl.MAX_BYTES + 1))
        evil = io.BytesIO()
        with zipfile.ZipFile(evil, 'w') as z:
            z.writestr('xl/worksheets/sheet1.xml', '<!DOCTYPE x [<!ENTITY a "b">]><worksheet/>')
        with self.assertRaises(ValueError): sl.read_xlsx(evil.getvalue())


class CheckTests(unittest.TestCase):
    rows = staticmethod(lambda: sl.read_xlsx(make_xlsx(ROWS)))

    def test_listed_by_roll_or_email(self):
        self.assertEqual(sl.check_table(self.rows(), [], '102103456'), 'listed')
        self.assertEqual(sl.check_table(self.rows(), ['Anshum@Thapar.edu'], None), 'listed')

    def test_not_listed_only_with_a_comparable_column(self):
        self.assertEqual(sl.check_table(self.rows(), [], '999'), 'not_listed')                # roll column exists
        self.assertEqual(sl.check_table(self.rows(), ['me@gmail.com'], None), 'not_listed')   # email column exists
        no_email = sl.read_xlsx(make_xlsx([['Name', 'Company'], ['Asha', 'EXL']]))
        self.assertEqual(sl.check_table(no_email, ['me@gmail.com'], '999'), 'unknown')        # nothing comparable

    def test_unknown_without_identifiers_or_rows(self):
        self.assertEqual(sl.check_table(self.rows(), [], None), 'unknown')
        self.assertEqual(sl.check_table([], ['a@b.c'], '1'), 'unknown')
        self.assertEqual(sl.check_table([HEADER], [], '999'), 'unknown')                      # header only


class StatusTests(unittest.TestCase):
    def mail(self, body='Shortlist is attached', name='EXL_TIET.xlsx'):
        return {'id': 'm1', 'subject': 'Campus Details', 'body': body,
                'attachment_refs': [{'name': name, 'attachment_id': 'a1', 'size': 100}]}

    def test_statuses(self):
        fetch = lambda mid, aid: make_xlsx(ROWS)
        self.assertEqual(sl.shortlist_status(self.mail(), fetch, [], '102103456'), 'listed')
        self.assertEqual(sl.shortlist_status(self.mail(), fetch, [], '555'), 'not_listed')
        self.assertEqual(sl.shortlist_status(self.mail(body='Dear all'), fetch, [], '555'), 'unknown')   # not about a shortlist
        self.assertEqual(sl.shortlist_status(self.mail(name='a.pdf'), fetch, [], '555'), 'unknown')

    def test_fetch_failure_is_unknown_not_error(self):
        def boom(mid, aid): raise RuntimeError('network')
        self.assertEqual(sl.shortlist_status(self.mail(), boom, [], '555'), 'unknown')


class ScanIntegration(unittest.TestCase):
    def setUp(self):
        _, ds = future()
        self.msg = gmail_msg('s1', f'Campus drive - Shortlist - Online test {ds}',
                             f'Shortlist is attached. Online test on {ds} at 10:00 AM.', 'cell@thapar.edu')
        p = self.msg['payload']
        self.msg['payload'] = {'mimeType': 'multipart/mixed', 'parts': [
            p, {'mimeType': 'application/octet-stream', 'filename': 'list.xlsx', 'body': {'attachmentId': 'att1', 'size': 500}}]}

    def run_scan(self, roll):
        store = MemStore(**{PROFILE_FILE: {'roll_number': roll}}); cal = FakeCalendar()
        system = system_for([self.msg])
        system.gmail.get_attachment = lambda mid, aid: make_xlsx(ROWS)
        out = scanner.run_scan(system, cal, store, set(), FakeHttpError, now=datetime.now(), owner_email='me@gmail.com')
        return out, store, cal

    def test_on_shortlist_is_added(self):
        out, store, cal = self.run_scan('102103456')
        self.assertEqual((out['added'], out['filtered_out']), (1, 0))

    def test_not_on_shortlist_is_filtered_with_reason_not_calendar(self):
        out, store, cal = self.run_scan('555')
        self.assertEqual((out['added'], out['filtered_out']), (0, 1))
        self.assertEqual(cal.inserted, [])
        item = store.files[STATE_FILE]['filtered'][0]
        self.assertEqual(item['relevance']['reason'], 'You are not on the attached shortlist')
        self.assertEqual(item['shortlist'], 'not_listed')


if __name__ == '__main__':
    unittest.main()
