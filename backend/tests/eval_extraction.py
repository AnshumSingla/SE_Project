"""
Extraction eval: run an extractor over tests/fixtures/emails.json and report
event-level precision / recall (date, and date+start time).

    python -m tests.eval_extraction            # baseline: current rule-based extractor

Not a unit test: it reports a score so extractor changes can be compared. Add a
new extractor by writing a function  (email: dict, now: datetime) -> [{'date','start'}]
and registering it in EXTRACTORS.
"""
import contextlib, datetime as _dt, io, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tests import stubs
stubs.install()
from tests.test_email_text import payload_from_fixture
from email_text import extract_body

def _load(name):
    return json.load(open(os.path.join(os.path.dirname(__file__), 'fixtures', name), encoding='utf-8'))['emails']

FIXTURE_SETS = {'emails.json': _load('emails.json'), 'stress.json': _load('stress.json')}
FIXTURES = FIXTURE_SETS['emails.json']


def rule_based(email, now):
    """The extractor used today (main_demo.EmailReminderSystem), with 'now' frozen."""
    import main_demo as md
    class Frozen(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(now.year, now.month, now.day, now.hour, now.minute)
    md.datetime = Frozen
    s = md.EmailReminderSystem()
    with contextlib.redirect_stdout(io.StringIO()):
        cls = s.classify_email_rule_based(email)
        d = s.extract_deadlines_rule_based(email) if cls['is_job_related'] else {}
    if d.get('has_deadline'):
        return [{'date': d['deadline_date'], 'start': d.get('deadline_time')}]
    return []


def rules_v2(email, now):
    """New general rule-based extractor (deadline_extractor.py)."""
    from deadline_extractor import extract_rule_based
    out = extract_rule_based(email, received=now, now=now)
    return [{'date': e['date'], 'start': e['start']} for e in out['events']]


EXTRACTORS = {'rule_based (old, main_demo)': rule_based, 'rules_v2 (deadline_extractor)': rules_v2}


def evaluate(name, fn, FIXTURES=None, label=''):
    FIXTURES = FIXTURES or globals()['FIXTURES']
    tp_d = fp_d = fn_d = tp_t = 0
    rows = []
    for fx in FIXTURES:
        e = fx['email']
        body = extract_body(payload_from_fixture(fx))
        now = _dt.datetime.fromisoformat(fx['now']).replace(tzinfo=None)
        got = fn({'subject': e['subject'], 'sender': e['sender'], 'body': body}, now)
        exp = fx['expected']['events']
        exp_dates = {x['date'] for x in exp}; got_dates = {g['date'] for g in got}
        exp_dt = {(x['date'], x.get('start')) for x in exp}
        got_dt = {(g['date'], (g.get('start') or None)) for g in got}
        tp = len(exp_dates & got_dates); fp = len(got_dates - exp_dates); fnn = len(exp_dates - got_dates)
        tp_d += tp; fp_d += fp; fn_d += fnn
        tp_t += len({x for x in exp_dt if x[1] and x in got_dt})
        ok = (exp_dates == got_dates)
        rows.append((fx['id'], ok, sorted(exp_dates), sorted(got_dates)))
    timed = sum(1 for fx in FIXTURES for x in fx['expected']['events'] if x.get('start'))
    prec = tp_d / (tp_d + fp_d) if tp_d + fp_d else 1.0
    rec = tp_d / (tp_d + fn_d) if tp_d + fn_d else 1.0
    print(f"\n== {name} on {label} ==")
    for fid, ok, exp, got in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {fid:28s} expected={exp}  got={got}")
    print(f"  events: date precision {prec:.0%}  recall {rec:.0%}  |  start time correct {tp_t}/{timed}  |  fixtures fully right {sum(r[1] for r in rows)}/{len(rows)}")


if __name__ == '__main__':
    for set_name, fx in FIXTURE_SETS.items():
        for n, f in EXTRACTORS.items():
            evaluate(n, f, fx, set_name)
