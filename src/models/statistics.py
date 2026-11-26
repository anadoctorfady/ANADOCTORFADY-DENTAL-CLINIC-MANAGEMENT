"""Statistics dashboard data (Round 49, Section G).

Treatments come from the UNIFIED session store: for every patient
with clinical/financial rows in the period, history_money
.session_rows() yields one session per (visit_date, tooth set) with
its joined procedure text and its base-currency session total
(converted_amounts). A session's procedure text may join several
procedures with " | " — the whole text is ONE treatment group.

Grouping: strip + casefold for the key; the displayed label is the
most common original casing seen for that group.

EMPTY-PROCEDURE DECISION: sessions whose procedure text is empty
are SKIPPED in both treatment charts (they name no treatment),
but their money still counts in period_summary()/monthly_series()
income, because those reuse the finance aggregations over ALL
financial rows. No "Unspecified" bucket is drawn.

Money is NEVER re-implemented here: period figures come from
finance_totals.flexible_totals() with every component included
(the SETTLED rule: total expenses INCLUDE salaries; lab is a cost
too, so expenses_total = operating + salaries + lab and
net = income - expenses_total, identical to flexible_totals'
net_income). Amounts are floats; dates are ISO strings.

Admin-only: every public function takes role=None; when a role is
passed it must be admin (finance_scope == "full") or PermissionError
is raised — the same refusal pattern as models/salaries.py.
"""
from collections import Counter, defaultdict
from datetime import date

from src.models.database import get_connection, init_db
from src.models.finance_totals import flexible_totals
from src.models.history_money import session_rows
from src.models.permissions import finance_scope


def ensure_admin(role):
    """Raise PermissionError unless `role` has full finance scope."""
    if finance_scope(role) != "full":
        raise PermissionError("statistics are admin-only")


def _check(role):
    if role is not None:
        ensure_admin(role)


def _sessions(date_from, date_to):
    """All unified sessions with date_from <= date <= date_to."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT DISTINCT patient_file FROM (
        SELECT patient_file FROM procedures
            WHERE visit_date BETWEEN ? AND ?
        UNION SELECT patient_file FROM financials
            WHERE visit_date BETWEEN ? AND ?
        UNION SELECT patient_file FROM diagnoses
            WHERE visit_date BETWEEN ? AND ?)""",
                (date_from, date_to) * 3)
    files = [r[0] for r in cur.fetchall() if r[0] is not None]
    conn.close()
    out = []
    for fid in files:
        for s in session_rows(fid):
            if date_from <= (s.get("date") or "") <= date_to:
                out.append(s)
    return out


def _groups(date_from, date_to):
    """{casefolded procedure: (display label, count, income)} over
    the period's sessions; empty-procedure sessions skipped."""
    counts = Counter(); income = defaultdict(float); casings = {}
    for s in _sessions(date_from, date_to):
        # R55: flatten to one line BEFORE grouping -- a procedure
        # text can carry a newline from its multi-line entry field,
        # and the same treatment typed with/without one is one
        # group (draw_hbars flattens again as a belt-and-braces).
        raw = " ".join((s.get("procedure") or "").split())
        if not raw:
            continue  # see module docstring: skipped in charts
        key = raw.casefold()
        counts[key] += 1
        income[key] += float(s.get("total") or 0.0)
        casings.setdefault(key, Counter())[raw] += 1
    return {k: (casings[k].most_common(1)[0][0], counts[k], income[k])
            for k in counts}


def top_treatments_by_count(date_from, date_to, limit=10, role=None):
    """[(label, count)] most frequent treatments first."""
    _check(role)
    g = _groups(date_from, date_to)
    rows = sorted(g.values(), key=lambda v: (-v[1], v[0].casefold()))
    return [(label, int(cnt)) for label, cnt, _inc in rows[:limit]]


def top_treatments_by_income(date_from, date_to, limit=10, role=None):
    """[(label, amount)] by summed session totals (base currency)."""
    _check(role)
    g = _groups(date_from, date_to)
    rows = sorted(g.values(), key=lambda v: (-v[2], v[0].casefold()))
    return [(label, float(inc)) for label, _cnt, inc in rows[:limit]]


def period_summary(date_from, date_to, role=None):
    """{income, expenses_operating, lab, salaries, expenses_total,
    net} for the period, from flexible_totals (all included)."""
    _check(role)
    r = flexible_totals(date_from, date_to)
    exp_total = r["expenses_only"] + r["salaries"] + r["total_lab"]
    return {"income": float(r["total_income"]),
            "expenses_operating": float(r["expenses_only"]),
            "lab": float(r["total_lab"]),
            "salaries": float(r["salaries"]),
            "expenses_total": float(exp_total),
            "net": float(r["total_income"] - exp_total)}


def _month_bounds(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    nxt = date(y + (m == 12), (m % 12) + 1, 1)
    from datetime import timedelta
    return ym + "-01", (nxt - timedelta(days=1)).isoformat()


def monthly_series(date_from, date_to, role=None):
    """[(yyyy-mm, income, expenses_total)] one row per month the
    period touches, in order; months without data report zeros."""
    _check(role)
    if not date_from or not date_to or date_to < date_from:
        return []
    months = []
    y, m = int(date_from[:4]), int(date_from[5:7])
    end = (int(date_to[:4]), int(date_to[5:7]))
    while (y, m) <= end:
        months.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    out = []
    for ym in months:
        first, last = _month_bounds(ym)
        s = period_summary(max(date_from, first), min(date_to, last))
        out.append((ym, s["income"], s["expenses_total"]))
    return out
