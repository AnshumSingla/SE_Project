"""
Turn a Gmail API message payload into clean text for deadline extraction.

Fixes the old behaviour, which (a) concatenated the text/plain AND text/html
versions of the same message, (b) stripped HTML tags with a regex so table cells
ran together ("Aptitude Test17-Sep-26Thursday7:30 PM"), and (c) left quoted
earlier messages in place, so a date inside "> On Mon ... wrote:" looked like a
new deadline.

Standard library only.
"""
import base64
import re
from html.parser import HTMLParser
from typing import Dict, List

_BLOCK_TAGS = {'p', 'div', 'br', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
               'table', 'tbody', 'thead', 'tfoot', 'section', 'article', 'header', 'footer', 'hr', 'pre'}
_SKIP_TAGS = {'script', 'style', 'head', 'title'}


class _HtmlToText(HTMLParser):
    """HTML -> text. Table cells become tab-separated, rows become lines.
    <blockquote> content (reply quotes) is dropped; forwarded content is kept."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self._skip = 0
        self._quote = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag == 'blockquote':
            self._quote += 1
        elif tag == 'tr':
            self.out.append('\n')
        elif tag in ('td', 'th'):
            self.out.append('\t')
        elif tag in _BLOCK_TAGS:
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag == 'blockquote':
            self._quote = max(0, self._quote - 1)
            self.out.append('\n')
        elif tag in _BLOCK_TAGS or tag == 'tr':
            self.out.append('\n')

    def handle_data(self, data):
        if not self._skip and not self._quote:
            self.out.append(data)

    def text(self) -> str:
        return ''.join(self.out)


def html_to_text(html: str) -> str:
    parser = _HtmlToText()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return re.sub(r'<[^>]+>', ' ', html)   # malformed HTML: best effort
    return _tidy(parser.text())


def _tidy(text: str) -> str:
    text = text.replace('\xa0', ' ').replace('​', '').replace('\r\n', '\n').replace('\r', '\n')
    lines = []
    for line in text.split('\n'):
        cells = [re.sub(r'[ ]+', ' ', c).strip() for c in line.split('\t')]
        while cells and not cells[-1]:          # drop empty trailing cells
            cells.pop()
        lines.append('\t'.join(cells).strip('\t') if any(cells) else '')
    out = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines))
    return out.strip()


_REPLY_MARKERS = [
    re.compile(r'^On .{5,200}wrote:\s*$', re.I),                 # Gmail/Apple: "On Mon, Sep 14 ... wrote:"
    re.compile(r'^-{2,}\s*Original Message\s*-{2,}\s*$', re.I),   # Outlook
    re.compile(r'^From:\s.+\n?', re.I),                           # only honoured after "Sent:" (see below)
]


def strip_quoted_reply(text: str) -> str:
    """Remove the quoted earlier conversation from a reply, keep forwards intact."""
    lines = text.split('\n')
    cut = None
    for i, line in enumerate(lines):
        s = line.strip()
        if _REPLY_MARKERS[0].match(s) or _REPLY_MARKERS[1].match(s):
            cut = i; break
        # "On Mon, Sep 14, 2026 at 10:00 AM Name <a@b> \n wrote:" wrapped over two lines
        if s.startswith('On ') and i + 1 < len(lines) and lines[i + 1].strip().lower() == 'wrote:':
            cut = i; break
        # Outlook header block: From:/Sent: pair at the top of a quoted message
        if s.lower().startswith('from:') and i + 1 < len(lines) and lines[i + 1].strip().lower().startswith('sent:'):
            cut = i; break
    if cut is not None:
        lines = lines[:cut]
    lines = [l for l in lines if not l.lstrip().startswith('>')]   # "> quoted" lines
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def _decode_part(part: Dict) -> str:
    data = (part.get('body') or {}).get('data')
    if not data:
        return ''
    raw = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))   # Gmail omits padding
    charset = 'utf-8'
    for h in part.get('headers', []) or []:
        if h.get('name', '').lower() == 'content-type':
            m = re.search(r'charset="?([\w-]+)"?', h.get('value', ''), re.I)
            if m:
                charset = m.group(1)
    try:
        return raw.decode(charset, errors='replace')
    except LookupError:
        return raw.decode('utf-8', errors='replace')


def _part_text(part: Dict) -> str:
    mime = (part.get('mimeType') or '').lower()
    if part.get('filename'):                    # attachment, not body
        return ''
    if mime.startswith('multipart/'):
        children = part.get('parts') or []
        texts = [_part_text(c) for c in children]
        if mime == 'multipart/alternative':
            return _best_alternative(children, texts)
        return '\n\n'.join(t for t in texts if t)
    if mime == 'text/plain':
        return _tidy(_decode_part(part))
    if mime == 'text/html':
        return html_to_text(_decode_part(part))
    return ''


def _best_alternative(children: List[Dict], texts: List[str]) -> str:
    """multipart/alternative holds the SAME message in several formats: pick one,
    never concatenate. Prefer text/plain unless it is a stub next to a far richer HTML."""
    plain = html = ''
    for c, t in zip(children, texts):
        mime = (c.get('mimeType') or '').lower()
        if mime == 'text/plain' and not plain:
            plain = t
        elif mime == 'text/html' and not html:
            html = t
        elif mime.startswith('multipart/') and not html:   # nested (e.g. related -> html)
            html = t
    if plain and (len(plain) >= 0.3 * len(html) or not html):
        return plain
    return html or plain


def extract_body(payload: Dict) -> str:
    """Clean body text of a Gmail message payload (no attachments, no quoted replies)."""
    return strip_quoted_reply(_part_text(payload))


def list_attachments(payload: Dict) -> List[str]:
    """Filenames of attachments (e.g. 'Shortlist.xlsx'), useful as a relevance signal."""
    names = []
    def walk(p):
        if p.get('filename'):
            names.append(p['filename'])
        for c in p.get('parts') or []:
            walk(c)
    walk(payload)
    return names


def list_attachment_refs(payload: Dict) -> List[Dict]:
    """Attachments that can be downloaded later: name, Gmail attachment id, mime type, size."""
    refs = []
    def walk(p):
        body = p.get('body') or {}
        if p.get('filename') and body.get('attachmentId'):
            refs.append({'name': p['filename'], 'attachment_id': body['attachmentId'],
                         'mime': p.get('mimeType', ''), 'size': body.get('size', 0)})
        for c in p.get('parts') or []:
            walk(c)
    walk(payload)
    return refs
