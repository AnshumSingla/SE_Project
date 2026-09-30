"""
"Shortlist is attached": open the attached .xlsx/.csv IN MEMORY and check whether
the owner is on it. Nothing is stored or sent to an LLM. Stdlib only.

Result per mail: 'listed' | 'not_listed' | 'unknown'. 'not_listed' is only claimed when the
table has a column of the same kind as an identifier we hold (an email column and we know
the email, or a roll-number column and we know the roll number); otherwise 'unknown'.
"""
import csv
import io
import re
import zipfile
from typing import Dict, List, Optional, Set
from xml.etree import ElementTree as ET

MAX_BYTES = 2 * 1024 * 1024
MAX_UNZIPPED = 20 * 1024 * 1024
MAX_ROWS = 20000
SHORTLIST_WORDS = re.compile(r'short[\s-]?list|selected\s+candidates|list\s+of\s+(?:selected|eligible)', re.I)
_EMAIL_HDR = re.compile(r'e-?mail', re.I)
_ROLL_HDR = re.compile(r'roll|enrol|reg(?:istration)?\s*(?:no|number)|student\s*id|\bid\b', re.I)


def _local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def read_xlsx(data: bytes) -> List[List[str]]:
    """All sheets' rows as lists of strings. Raises ValueError for anything odd."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ValueError('not an xlsx') from e
    if sum(i.file_size for i in zf.infolist()) > MAX_UNZIPPED:
        raise ValueError('too large when unzipped')

    def parse(name):
        raw = zf.read(name)
        if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
            raise ValueError('unsafe xml')
        return ET.fromstring(raw)

    shared: List[str] = []
    if 'xl/sharedStrings.xml' in zf.namelist():
        for si in parse('xl/sharedStrings.xml'):
            shared.append(''.join(t.text or '' for t in si.iter() if _local(t.tag) == 't'))

    rows: List[List[str]] = []
    for name in sorted(n for n in zf.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', n)):
        for row in (r for r in parse(name).iter() if _local(r.tag) == 'row'):
            cells: Dict[int, str] = {}
            for c in row:
                if _local(c.tag) != 'c':
                    continue
                ref = re.match(r'([A-Z]+)', c.get('r') or '')
                col = 0
                for ch in (ref.group(1) if ref else 'A'):
                    col = col * 26 + ord(ch) - 64
                kind = c.get('t')
                text = ''
                for ch in c:
                    if _local(ch.tag) == 'v':
                        text = ch.text or ''
                        if kind == 's' and text.isdigit() and int(text) < len(shared):
                            text = shared[int(text)]
                    elif _local(ch.tag) == 'is':
                        text = ''.join(t.text or '' for t in ch.iter() if _local(t.tag) == 't')
                cells[col] = text
            if cells:
                rows.append([cells.get(i, '') for i in range(1, max(cells) + 1)])
            if len(rows) >= MAX_ROWS:
                return rows
    return rows


def read_csv(data: bytes) -> List[List[str]]:
    text = data.decode('utf-8-sig', errors='replace')
    return [r for _, r in zip(range(MAX_ROWS), csv.reader(io.StringIO(text))) if any(r)]


def read_table(filename: str, data: bytes) -> List[List[str]]:
    if len(data) > MAX_BYTES:
        raise ValueError('attachment too large')
    low = (filename or '').lower()
    if low.endswith('.xlsx'):
        return read_xlsx(data)
    if low.endswith('.csv'):
        return read_csv(data)
    raise ValueError('unsupported attachment type')


def norm(value: str) -> str:
    v = re.sub(r'[^a-z0-9@._+-]', '', (value or '').strip().lower())
    return v[:-2] if v.endswith('.0') and v[:-2].isdigit() else v     # 102103456.0 -> 102103456


def _header_row(rows: List[List[str]]) -> Optional[int]:
    for i, r in enumerate(rows[:10]):
        if sum(1 for c in r if _EMAIL_HDR.search(c or '') or _ROLL_HDR.search(c or '')) >= 1 and len(r) >= 2:
            return i
    return None


def check_table(rows: List[List[str]], emails=None, roll: Optional[str] = None) -> str:
    emails = [emails] if isinstance(emails, str) else [e for e in (emails or []) if e]
    ids: Set[str] = {norm(x) for x in emails + ([roll] if roll else [])}
    ids.discard('')
    if not rows or not ids:
        return 'unknown'
    if any(norm(c) in ids for r in rows for c in r):
        return 'listed'
    h = _header_row(rows)
    if h is None:
        return 'unknown'
    header = rows[h]
    has_email_col = any(_EMAIL_HDR.search(c or '') for c in header)
    has_roll_col = any(_ROLL_HDR.search(c or '') and not _EMAIL_HDR.search(c or '') for c in header)
    comparable = (emails and has_email_col) or (roll and has_roll_col)
    return 'not_listed' if comparable and len(rows) - h - 1 >= 1 else 'unknown'


def mentions_shortlist(subject: str, body: str, names: List[str]) -> bool:
    return bool(SHORTLIST_WORDS.search(subject or '') or SHORTLIST_WORDS.search(body or '')
                or any(SHORTLIST_WORDS.search(n or '') for n in names))


def shortlist_status(mail: Dict, fetch, emails, roll: Optional[str], max_files: int = 2) -> str:
    """
    `fetch(message_id, attachment_id) -> bytes`. Looks only at .xlsx/.csv attachments of mails
    that talk about a shortlist. Any failure -> 'unknown' (never blocks the scan).
    """
    refs = [r for r in mail.get('attachment_refs') or [] if (r.get('name') or '').lower().endswith(('.xlsx', '.csv'))]
    if not refs or not (emails or roll):
        return 'unknown'
    if not mentions_shortlist(mail.get('subject'), mail.get('body'), [r['name'] for r in refs]):
        return 'unknown'
    statuses = []
    for ref in refs[:max_files]:
        if (ref.get('size') or 0) > MAX_BYTES:
            continue
        try:
            statuses.append(check_table(read_table(ref['name'], fetch(mail['id'], ref['attachment_id'])), emails, roll))
        except Exception as e:
            print(f"⚠️ shortlist check skipped ({type(e).__name__})")
    if 'listed' in statuses:
        return 'listed'
    return 'not_listed' if statuses and all(s == 'not_listed' for s in statuses) else 'unknown'
