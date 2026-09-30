"""
Logic shared by the website endpoints and the background scan, so both behave
identically: deterministic event IDs, candidate building, calendar event bodies.
No Flask, no Google imports here.
"""
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from relevance import check_relevance

EVENT_SOURCE = 'smart_reminder'


def make_event_id(gmail_message_id: str, index: int = 0) -> str:
    """
    Deterministic Google Calendar event ID for (Gmail message, event index).

    Google requires IDs of 5-1024 chars using only a-v and 0-9 (base32hex,
    lowercase). Inserting an ID that already exists - including one the user has
    since deleted - returns HTTP 409, which makes event creation idempotent:
    retries, double clicks and overlapping scans can never create duplicates,
    and an event the user deleted is never silently recreated.
    """
    digest = hashlib.sha1(f"{gmail_message_id}:{index}".encode('utf-8')).digest()
    return base64.b32hexencode(digest).decode('ascii').lower().rstrip('=')


def is_future_date(date_str: Optional[str], today=None) -> bool:
    """True if the date is today or later."""
    if not date_str:
        return False
    try:
        d = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except ValueError:
        return False
    return d >= (today or datetime.now().date())


def urgency_days(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        delta = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None) - datetime.now()
        return max(0, delta.days)
    except ValueError:
        return None


def build_candidates(results: List[Dict], processed_ids, profile: Optional[Dict], today=None,
                     shortlists: Optional[Dict[str, str]] = None) -> Dict:
    """
    Turn analysed mails (complete_system.analyze_for_scan results) into calendar
    candidates, one per event. Returns
    {'relevant': [...], 'filtered': [...], 'stats': {...}}.
    """
    relevant, filtered = [], []
    stats = {'analysed': len(results), 'skipped': 0, 'expired': 0, 'duplicates': 0}
    seen = set()
    for result in results:
        email = result.get('email_data', {})
        classification = result.get('classification', {})
        events = result.get('events') or []
        msg_id = email.get('id', '')
        if not events or not msg_id:
            stats['skipped'] += 1
            continue
        if msg_id in processed_ids:
            stats['duplicates'] += 1
            stats['skipped'] += 1
            continue

        audience = (result.get('extraction') or {}).get('audience', 'unknown')
        rel = check_relevance(email, profile, audience)
        listed = (shortlists or {}).get(msg_id, 'unknown')
        if listed == 'not_listed' and audience != 'personal':
            rel = {'relevant': False, 'reason': 'You are not on the attached shortlist', 'signals': rel.get('signals', {})}
        elif listed == 'listed' and rel['relevant']:
            rel = dict(rel, reason='You are on the attached shortlist')

        for idx, ev in enumerate(events):
            date = ev.get('date')
            if not is_future_date(date, today):
                stats['expired'] += 1
                stats['skipped'] += 1
                continue
            # Several messages in one thread (reminders, replies) often repeat the
            # same event: keep only the first (Gmail returns newest first).
            key = (email.get('thread_id') or msg_id, date, ev.get('kind'))
            if key in seen:
                stats['duplicates'] += 1
                stats['skipped'] += 1
                continue
            seen.add(key)
            (relevant if rel['relevant'] else filtered).append({
                'email_id': msg_id,
                'event_index': idx,
                'thread_id': email.get('thread_id', ''),
                'event_id': make_event_id(msg_id, idx),
                'subject': email.get('subject', ''),
                'sender': email.get('sender', ''),
                'date': email.get('date', ''),
                'snippet': email.get('snippet', email.get('body', '')[:200]),
                'classification': {
                    'is_job_related': classification.get('is_job_related', False),
                    'category': classification.get('category', 'other'),
                    'urgency': classification.get('urgency', 'low'),
                    'confidence': classification.get('confidence', 0.8),
                    'reasoning': classification.get('reason', classification.get('reasoning', '')),
                },
                'audience': audience,
                'shortlist': listed,
                'relevance': {'relevant': rel['relevant'], 'reason': rel['reason']},
                'deadline': {
                    'has_deadline': True,
                    'date': date,
                    'time': ev.get('start'),
                    'end_time': ev.get('end'),
                    'end_date': ev.get('end_date'),
                    'duration_min': ev.get('duration_min'),
                    'type': ev.get('kind'),
                    'title': ev.get('title'),
                    'description': ev.get('title'),
                    'text': ev.get('evidence'),
                    'confidence': ev.get('confidence'),
                    'flags': ev.get('flags') or [],
                    'urgency_days': urgency_days(date),
                },
                'pending': result.get('pending') or [],
            })
    return {'relevant': relevant, 'filtered': filtered, 'stats': stats}


class Skip(Exception):
    """A candidate that must not become an event; `reason` is machine-readable."""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def event_body(candidate: Dict, reminders: List[int], tz: str, today=None) -> Dict:
    """Google Calendar event body for a candidate. Raises Skip(reason)."""
    deadline = candidate.get('deadline') or {}
    email_id = candidate.get('email_id')
    if not email_id:
        raise Skip('missing_email_id')
    if not deadline.get('has_deadline') or not deadline.get('date'):
        raise Skip('no_deadline')

    t = deadline.get('time')
    if not t or t == 'None':
        t = '23:59:00'
    if len(t) == 5:
        t += ':00'
    try:
        start = datetime.fromisoformat(f"{deadline['date']}T{t}")
    except ValueError:
        raise Skip('bad_date')
    if start.date() < (today or datetime.now().date()):
        raise Skip('past_deadline')

    idx = _clamp(candidate.get('event_index', 0), 0, 99, 0)
    end = start
    end_time = deadline.get('end_time')
    if end_time and end_time != 'None':
        end_time = end_time + ':00' if len(end_time) == 5 else end_time
        try:
            cand = datetime.fromisoformat(f"{deadline.get('end_date') or deadline['date']}T{end_time}")
            if cand >= start:
                end = cand
        except ValueError:
            pass
    elif deadline.get('duration_min') and deadline.get('time'):
        end = start + timedelta(minutes=_clamp(deadline['duration_min'], 1, 1440, 60))

    subject = candidate.get('subject') or 'Job Deadline'
    title = str(deadline.get('title') or subject)[:100]
    return {
        'id': make_event_id(email_id, idx),
        'summary': f'📧 {title}',
        'description': f'{deadline.get("description") or ""}\n\nFrom: {candidate.get("sender", "")}\n'
                       f'Email: {candidate.get("snippet", "")}'.strip(),
        'start': {'dateTime': start.isoformat(), 'timeZone': tz},
        'end': {'dateTime': end.isoformat(), 'timeZone': tz},
        'reminders': {'useDefault': False,
                      'overrides': [{'method': 'popup', 'minutes': int(m)} for m in reminders]},
        'colorId': '11',
        'extendedProperties': {'private': {
            'source': EVENT_SOURCE,
            'gmailMessageId': str(email_id),
            'eventIndex': str(idx),
            'deadlineType': str(deadline.get('type') or 'other'),
        }},
    }


def insert_event(service, body: Dict, http_error_cls) -> str:
    """'created', or 'duplicate' when the ID already exists (409: present or deleted by the user)."""
    try:
        service.events().insert(calendarId='primary', body=body).execute()
        return 'created'
    except http_error_cls as e:
        if getattr(getattr(e, 'resp', None), 'status', None) == 409:
            return 'duplicate'
        raise
