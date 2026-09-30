"""
Profile-based relevance filter for BROADCAST mails (placement-cell / mailing-list
style). Extraction (what/when) is separate and never changes; this only decides
whether the mail is meant for the user.

Principles:
- Personal mails are never filtered.
- Filter only on explicit evidence (a named branch / batch / CGPA floor that
  excludes the user). Anything unclear stays visible.
- A filtered mail is not dropped: the caller shows it under "Filtered out" with
  `reason`, so a wrong call is one click to undo.
"""
import re
from typing import Dict, List, Optional, Set

# canonical discipline -> aliases (lowercase). Matched on word boundaries.
DISCIPLINES: Dict[str, List[str]] = {
    'cs': ['cse', 'cs', 'computer science', 'computer engineering', 'coe', 'csbs', 'cse-bs', 'it',
           'information technology', 'software engineering', 'csai', 'cs&ai', 'artificial intelligence',
           'ai/ml', 'aiml', 'data science', 'machine learning', 'cyber security'],
    'ece': ['ece', 'electronics and communication', 'electronics & communication', 'e&c', 'eic',
            'electronics and computer', 'electronics engineering', 'vlsi', 'ecece'],
    'electrical': ['ee', 'eee', 'electrical', 'electrical engineering', 'electrical and electronics'],
    'mechanical': ['me', 'mech', 'mechanical', 'mechanical engineering', 'mechatronics', 'production',
                   'manufacturing', 'industrial engineering', 'automobile'],
    'civil': ['ce', 'civil', 'civil engineering', 'construction', 'structural'],
    'chemical': ['chemical', 'chemical engineering', 'che', 'petroleum'],
    'biotech': ['biotech', 'biotechnology', 'bt', 'biomedical', 'bioinformatics'],
    'mba': ['mba', 'management', 'pgdm', 'business administration'],
    'science': ['physics', 'chemistry', 'mathematics', 'maths', 'statistics', 'msc', 'm.sc'],
}
# Aliases short enough to be ordinary words only count in an eligibility context.
_AMBIGUOUS = {'it', 'me', 'ce', 'cs', 'bt', 'ee', 'che', 'production', 'management', 'construction', 'structural'}

_ALL_BRANCHES = re.compile(
    r'\b(all\s+(the\s+)?(branches|streams|disciplines|departments|courses)|any\s+(branch|stream|discipline)|'
    r'open\s+to\s+all|all\s+eligible\s+students|all\s+b\.?\s?tech|irrespective\s+of\s+(the\s+)?(branch|stream))\b', re.I)
_ELIG_CUE = re.compile(
    r'\b(eligible|eligibility|branches|branch|open\s+to|open\s+for|for\s+students\s+of|students\s+of|'
    r'department|departments|invited|applicable|allowed|criteria|streams?|disciplines?|courses?|batch|'
    r'pass(?:ing)?[\s-]*out|graduat\w*)\b', re.I)
_BATCH = re.compile(r"\b(?:(20\d{2})\s*(?:batch|passouts?|pass[\s-]*outs?|graduates?|graduating)|"
                    r"(?:batch|class)\s+of\s+(20\d{2})|(?:2k)(\d{2})\s*batch|"
                    r"(?:passing|graduating)\s+(?:out\s+)?(?:in|of)\s+(20\d{2}))", re.I)
_CGPA = re.compile(r'(?:cgpa|gpa|cpi)\s*(?:of|:|>=|≥|above|minimum|min\.?|at\s+least)?\s*(?:of\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*(?:\+|and\s+above|or\s+above|\&\s*above)?', re.I)
_PCT = re.compile(r'(\d{2}(?:\.\d+)?)\s*%\s*(?:and\s+above|or\s+above|\+|throughout|aggregate)?', re.I)


def canonical(text: str) -> Optional[str]:
    """Map a free-text discipline ('Computer Science & Engg') to a canonical group."""
    t = re.sub(r'[^a-z0-9& /.-]+', ' ', (text or '').lower()).replace('engg', 'engineering').strip()
    if not t:
        return None
    best = None
    for group, aliases in DISCIPLINES.items():
        for a in aliases:
            if t == a or re.search(rf'(?<![a-z]){re.escape(a)}(?![a-z])', t):
                if a in _AMBIGUOUS and t != a:
                    continue
                if best is None or len(a) > best[1]:
                    best = (group, len(a))
    return best[0] if best else None


def normalize_profile(p: Optional[Dict]) -> Dict:
    """Clean user-supplied profile. Unknown keys are dropped; everything is optional."""
    p = p or {}
    def lst(v):
        if isinstance(v, str):
            v = re.split(r'[,\n;]', v)
        return [str(x).strip() for x in (v or []) if str(x).strip()][:30]
    def num(v, lo, hi):
        try:
            f = float(v)
            return f if lo <= f <= hi else None
        except (TypeError, ValueError):
            return None
    disciplines = lst(p.get('disciplines') or p.get('discipline'))
    return {
        'roles': lst(p.get('roles') or p.get('role')),
        'disciplines': disciplines,
        'discipline_groups': sorted({g for g in map(canonical, disciplines) if g}),
        'graduation_year': int(num(p.get('graduation_year'), 2000, 2100) or 0) or None,
        'cgpa': num(p.get('cgpa'), 0, 10),
        'exclude_keywords': [k.lower() for k in lst(p.get('exclude_keywords'))],
        'strictness': p.get('strictness') if p.get('strictness') in ('lenient', 'balanced', 'strict') else 'balanced',
        # background scan policy: 'confident' adds clear events and queues unsure ones for review
        'auto_add': p.get('auto_add') if p.get('auto_add') in ('off', 'confident', 'all') else 'confident',
        'scan_paused': bool(p.get('scan_paused')),
        # shortlist check: compared in memory against attached shortlists, never stored elsewhere
        'roll_number': str(p.get('roll_number') or '').strip()[:30],
        'other_emails': [e.lower() for e in lst(p.get('other_emails')) if '@' in e][:5],   # e.g. your college address
        'check_shortlists': p.get('check_shortlists', True) is not False,
    }


def _eligibility_text(subject: str, body: str) -> str:
    """Subject plus sentences/lines that talk about who may apply."""
    parts = [subject or '']
    for unit in re.split(r'(?<=[.!?])\s+|\n', body or ''):
        if _ELIG_CUE.search(unit) and len(unit) < 600:
            parts.append(unit)
    return '\n'.join(parts)


def mentioned_groups(text: str) -> Set[str]:
    found: Set[str] = set()
    low = text.lower().replace('engg', 'engineering')
    for group, aliases in DISCIPLINES.items():
        for a in aliases:
            if a in _AMBIGUOUS:
                pat = rf'(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])'
                # ambiguous short forms count only when written as a branch code, e.g. "IT", "ME"
                if re.search(pat, text.replace('engg', 'engineering')) and a.upper() in re.findall(r'\b[A-Z]{2,4}\b', text):
                    found.add(group)
            elif re.search(rf'(?<![a-z]){re.escape(a)}(?![a-z])', low):
                found.add(group)
    return found


def check_relevance(email: Dict, profile: Optional[Dict], audience: str = 'unknown') -> Dict:
    """
    -> {'relevant': bool, 'reason': str, 'signals': {...}}
    `email` needs subject/body. `audience` comes from the extractor ('personal'|'broadcast'|'unknown').
    """
    prof = normalize_profile(profile)
    subject, body = email.get('subject') or '', email.get('body') or ''
    text = subject + '\n' + body
    signals: Dict = {'audience': audience}

    def ok(reason):
        return {'relevant': True, 'reason': reason, 'signals': signals}

    def no(reason):
        return {'relevant': False, 'reason': reason, 'signals': signals}

    if audience == 'personal':
        return ok('addressed to you')

    # user's own exclusions (hard, but only for non-personal mail)
    low = text.lower()
    for k in prof['exclude_keywords']:
        if k and k in low:
            signals['exclude_keyword'] = k
            return no(f'contains your excluded keyword "{k}"')

    if not any([prof['discipline_groups'], prof['graduation_year'], prof['cgpa']]):
        return ok('no profile set')

    elig = _eligibility_text(subject, body)
    if _ALL_BRANCHES.search(text):
        signals['all_branches'] = True
    else:
        groups = mentioned_groups(elig)
        signals['branches'] = sorted(groups)
        if groups and prof['discipline_groups']:
            mine = set(prof['discipline_groups'])
            if groups & mine:
                signals['matched'] = sorted(groups & mine)
            elif prof['strictness'] != 'lenient':
                names = ', '.join(sorted(groups))
                return no(f'meant for {names}; your profile: {", ".join(sorted(mine))}')

    years = {int(next(g for g in m if g)) if not m[2] else 2000 + int(m[2]) for m in _BATCH.findall(elig)}
    signals['batches'] = sorted(years)
    if years and prof['graduation_year'] and prof['graduation_year'] not in years and prof['strictness'] != 'lenient':
        return no(f'meant for batch {", ".join(map(str, sorted(years)))}; yours is {prof["graduation_year"]}')

    if prof['cgpa'] is not None and prof['strictness'] == 'strict':
        floors = [float(x) for x in _CGPA.findall(elig) if 4 <= float(x) <= 10]
        if floors:
            signals['min_cgpa'] = max(floors)
            if prof['cgpa'] < max(floors):
                return no(f'asks for CGPA {max(floors):g}+; yours is {prof["cgpa"]:g}')

    return ok('matches your profile' if signals.get('matched') else 'no restriction found')
