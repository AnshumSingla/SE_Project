"""
The background scan: one pass over new mail -> calendar events / review queue.
Used by the scheduled endpoint and the website's "Scan now" button, so both
behave the same. All state lives in the user's own Drive (state.json).

State (small, capped): seen message IDs, dismissed event IDs, the review queue,
the filtered-out list and a short activity log.
"""
import math
from datetime import datetime
from typing import Dict, Optional

import core
import shortlist
from drive_store import PROFILE_FILE, STATE_FILE
from relevance import normalize_profile

CONFIDENT = 0.75
BENIGN_FLAGS = {'weekday_ok'}          # a weekday that agrees with the date is good news, not a warning
CAPS = {'seen': 2000, 'dismissed': 500, 'review': 50, 'filtered': 50, 'log': 30}


def empty_state() -> Dict:
    return {'version': 1, 'last_scan': None, 'seen': [], 'dismissed': [], 'review': [], 'filtered': [], 'log': []}


def load_state(store) -> Dict:
    st = empty_state()
    loaded = store.load(STATE_FILE) or {}
    for k in ('seen', 'dismissed', 'review', 'filtered', 'log'):
        if isinstance(loaded.get(k), list):
            st[k] = loaded[k]
    st['last_scan'] = loaded.get('last_scan')
    return st


def save_state(store, st: Dict) -> None:
    for k, cap in CAPS.items():
        st[k] = st[k][-cap:]
    store.save(STATE_FILE, st)


def decide(candidate: Dict, mode: str) -> str:
    """'add' or 'review' for a RELEVANT candidate."""
    if mode == 'off':
        return 'review'
    if mode == 'all':
        return 'add'
    d = candidate.get('deadline') or {}
    warnings = [f for f in (d.get('flags') or []) if f not in BENIGN_FLAGS]
    sure = (d.get('confidence') or 0) >= CONFIDENT and not warnings
    return 'add' if sure else 'review'


def _days_back(last_scan: Optional[str], now: datetime, default: int = 7) -> int:
    if not last_scan:
        return default
    try:
        gap = (now - datetime.fromisoformat(last_scan)).total_seconds() / 86400
    except ValueError:
        return default
    return max(1, min(14, math.ceil(gap) + 1))         # one day of overlap; safe: IDs are idempotent


def _not_past(c: Dict, today) -> bool:
    return core.is_future_date((c.get('deadline') or {}).get('date'), today)


def run_scan(system, calendar_service, store, processed_ids, http_error_cls, *,
             now: Optional[datetime] = None, max_emails: int = 50, reminders=(10080, 1440),
             tz: str = 'Asia/Kolkata', reset_seen: bool = False, owner_email: Optional[str] = None) -> Dict:
    now = now or datetime.now()
    profile = normalize_profile(store.load(PROFILE_FILE))
    if profile['scan_paused']:
        return {'status': 'paused'}

    state = load_state(store)
    if reset_seen:
        state['seen'] = []
    skip_ids = set(processed_ids) | set(state['seen'])
    days_back = _days_back(state['last_scan'], now)

    results = system.process_user_emails(user_id='owner', max_emails=max_emails, days_back=days_back,
                                         skip_ids=skip_ids, exclude_self_sent=True)
    shortlists = {}
    my_emails = [e for e in [owner_email] + profile['other_emails'] if e]
    if profile['check_shortlists'] and (my_emails or profile['roll_number']) and hasattr(system.gmail, 'get_attachment'):
        for r in results:
            mail = r.get('email_data', {})
            if r.get('events') and mail.get('id'):
                status = shortlist.shortlist_status(mail, system.gmail.get_attachment, my_emails, profile['roll_number'])
                if status != 'unknown':
                    shortlists[mail['id']] = status
    built = core.build_candidates(results, set(processed_ids), profile, now.date(), shortlists)
    dismissed = set(state['dismissed'])
    relevant = [c for c in built['relevant'] if c['event_id'] not in dismissed]
    filtered = [c for c in built['filtered'] if c['event_id'] not in dismissed]

    added, to_review, errors = [], [], 0
    for c in relevant:
        if decide(c, profile['auto_add']) == 'review':
            to_review.append(c)
            continue
        try:
            body = core.event_body(c, list(reminders), tz, now.date())
            outcome = core.insert_event(calendar_service, body, http_error_cls)
            if outcome == 'created':
                added.append({'event_id': c['event_id'], 'title': body['summary'], 'start': body['start']['dateTime']})
        except core.Skip:
            pass
        except Exception as e:                          # one bad event must not stop the rest
            errors += 1
            print(f"⚠️ add failed: {type(e).__name__}")
            to_review.append(c)                         # keep it: the user can add it by hand

    today = now.date()
    known = {c['event_id'] for c in to_review}
    state['review'] = [c for c in state['review'] if _not_past(c, today) and c['event_id'] not in known] + to_review
    known_f = {c['event_id'] for c in filtered}
    state['filtered'] = [c for c in state['filtered'] if _not_past(c, today) and c['event_id'] not in known_f] + filtered
    state['seen'] = state['seen'] + [r['email_data']['id'] for r in results if r.get('email_data', {}).get('id')]
    state['last_scan'] = now.isoformat(timespec='seconds')
    summary = {'status': 'ok', 'mails_analysed': len(results), 'added': len(added),
               'for_review': len(to_review), 'filtered_out': len(filtered), 'errors': errors}
    state['log'].append(dict(summary, at=state['last_scan'], titles=[a['title'] for a in added][:5]))
    save_state(store, state)                            # single write at the end
    summary['added_events'] = added
    return summary


def resolve_item(store, event_id: str, action: str, calendar_service, http_error_cls, *,
                 now: Optional[datetime] = None, reminders=(10080, 1440), tz: str = 'Asia/Kolkata') -> Dict:
    """Accept (create the event) or dismiss an item from the review queue / filtered list."""
    now = now or datetime.now()
    st = load_state(store)
    item = next((c for c in st['review'] + st['filtered'] if c['event_id'] == event_id), None)
    if not item:
        return {'status': 'not_found'}
    outcome = 'dismissed'
    if action == 'accept':
        outcome = core.insert_event(calendar_service, core.event_body(item, list(reminders), tz, now.date()), http_error_cls)
    elif action != 'dismiss':
        return {'status': 'bad_action'}
    st['review'] = [c for c in st['review'] if c['event_id'] != event_id]
    st['filtered'] = [c for c in st['filtered'] if c['event_id'] != event_id]
    if action == 'dismiss' or outcome == 'duplicate':
        st['dismissed'].append(event_id)
    save_state(store, st)
    return {'status': outcome}
