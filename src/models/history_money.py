"""Per-session money for the clinical History (R23 item 2; R24
extends session_rows for the unified clinical table).

A session = the diagnoses/procedures rows for one patient on one
visit_date with one tooth selection, plus that date's visit-level
complaints row (complaints carry no tooth, so complaint/symptom
text shows on every session row of the date).

Money attribution: a financial row belongs to a session when
patient_file, visit_date AND the tooth SET all match (order /
whitespace insensitive) -- financials.tooth_number is the
comma-joined chart selection captured at payment time, like
diagnoses/procedures.tooth_number at save time. Same-session rows
SUM; a multi-tooth row ("16,11") shows IN FULL only on the
exact-set session (never split/duplicated); a row matching no
session appears in no session row but still counts in
patient_totals(). Round 38: row_kind='payment' rows (standalone
payments) are excluded here entirely — patient-level money only.
Amounts are base-currency via converted_amounts().

R24 session keys (existing keys unchanged): complaints_id
(latest complaints row id for the date or None), diagnosis_ids /
procedure_ids / financial_ids, meta {"complaint"/"diagnosis"/
"procedure": (author, created_at) of latest/newest row or None}
for the 24h rule, tooth_raw (stored tooth_number, "" toothless)
and money_currency (rows' single currency, blank = base, else
None)."""
from src.models.database import get_connection, init_db
from src.models.finance_totals import converted_amounts
from src.models.currency import default_currency


def parse_teeth(raw):
    """Normalised tooth set from a stored tooth_number string:
    "16, 11" / "16,11" / "16" / "" / None -> frozenset of str."""
    if not raw:
        return frozenset()
    return frozenset(p.strip() for p in str(raw).split(",") if p.strip())


def _money(row):
    """(total, paid, remaining) floats from one financials row, base via converted_amounts()."""
    return converted_amounts(row)


def _fin_detail(patient_file):
    """{(visit_date, tooth frozenset): {"total","paid","remaining",
    "ids","currencies"}} over the patient's SESSION financial rows
    (row_kind='payment' rows excluded, R38). {} for null file / none."""
    if not patient_file:
        return {}
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM financials WHERE patient_file=?"
                    " ORDER BY id", (patient_file,))
        rows = [dict(r) for r in cur.fetchall()]
    except Exception:
        rows = []
    conn.close()
    base = default_currency()
    out = {}
    for r in rows:
        if (r.get("row_kind") or "session") == "payment":
            continue  # R38: standalone payments are patient-level money
        key = (r.get("visit_date") or "", parse_teeth(r.get("tooth_number")))
        tot, paid, rem = _money(r)
        acc = out.setdefault(key, {"total": 0.0, "paid": 0.0,
                                   "remaining": 0.0, "ids": [],
                                   "currencies": set()})
        acc["total"] += tot; acc["paid"] += paid; acc["remaining"] += rem
        if r.get("id") is not None:
            acc["ids"].append(r["id"])
        acc["currencies"].add((r.get("currency") or "").strip().upper() or base)
    return out


def money_map(patient_file):
    """{(visit_date, tooth frozenset): {"total","paid","remaining"}}
    summed over the patient's session rows. {} for null / none."""
    return {k: {"total": v["total"], "paid": v["paid"],
                "remaining": v["remaining"]}
            for k, v in _fin_detail(patient_file).items()}


def session_money(patient_file, visit_date, tooth_number, mmap=None):
    """One session's {"total","paid","remaining"} (base currency),
    or None when NO session financial row matches patient + date +
    tooth set exactly (caller renders None as blank cells)."""
    mmap = money_map(patient_file) if mmap is None else mmap
    return mmap.get((visit_date or "", parse_teeth(tooth_number)))


def _single_currency(detail_entry):
    """The session's money currency when its financial rows all
    share one (normalised) currency, else None (also None when the
    session has no financial rows at all)."""
    if not detail_entry or not detail_entry["ids"]:
        return None
    cur = detail_entry["currencies"]
    return next(iter(cur)) if len(cur) == 1 else None


def _mk(date, tooth, texts, diag, proc, money, cid, dids, pids,
        meta, tooth_raw):
    """One session dict: the R23 display keys + the R24 keys."""
    return {"date": date, "tooth": tooth,
            "complaint": " | ".join(c for c, _ in texts if c),
            "symptom": " | ".join(x for _, x in texts if x),
            "diagnosis": diag, "procedure": proc,
            "total": money["total"] if money else None,
            "paid": money["paid"] if money else None,
            "remaining": money["remaining"] if money else None,
            "complaints_id": cid, "diagnosis_ids": dids,
            "procedure_ids": pids,
            "financial_ids": money["ids"] if money else [],
            "meta": meta, "tooth_raw": tooth_raw,
            "money_currency": _single_currency(money)}


def session_rows(patient_file):
    """Unified History rows for one patient, newest first (see
    _mk for the dict shape) with total/paid/remaining None when
    the session has no matching financial row. Sessions are the
    diagnoses / procedures rows grouped by (visit_date, tooth
    set); a date with complaints but no diagnosis / procedure
    still yields one tooth-less row so the complaint is visible.
    Multiple texts in one session join with " | ". [] if none."""
    if not patient_file:
        return []
    init_db()
    conn = get_connection(); cur = conn.cursor()
    complaints = {}
    try:
        cur.execute("SELECT * FROM complaints WHERE patient_file=?"
                    " ORDER BY id", (patient_file,))
        for r in cur.fetchall():
            d = dict(r); date = d.get("visit_date") or ""
            e = complaints.setdefault(date, {"texts": [], "id": None,
                                             "meta": None})
            e["texts"].append((d.get("complaint") or "", d.get("symptoms") or ""))
            e["id"] = d.get("id")  # ascending ids: last = latest
            e["meta"] = (d.get("author"), d.get("created_at"))
    except Exception:
        pass
    sessions = {}
    order = []
    for table, col, field in (("diagnoses", "diagnosis", "diagnosis"),
                              ("procedures", "procedure_done", "procedure")):
        try:
            cur.execute(f"SELECT * FROM {table} WHERE patient_file=?"
                        " ORDER BY id", (patient_file,))
            rows = cur.fetchall()
        except Exception:
            rows = []
        for r in rows:
            d = dict(r)
            key = (d.get("visit_date") or "", parse_teeth(d.get("tooth_number")))
            if key not in sessions:
                sessions[key] = {"date": key[0],
                                 "tooth": d.get("tooth_number") or "",
                                 "diagnosis": [], "procedure": [],
                                 "diagnosis_ids": [], "procedure_ids": [],
                                 "meta_diag": None, "meta_proc": None}
                order.append(key)
            s = sessions[key]
            if d.get(col):
                s[field].append(d[col])
            s[field + "_ids"].append(d.get("id"))
            meta = (d.get("author"), d.get("created_at"))
            if field == "diagnosis":
                s["meta_diag"] = meta  # ascending: last = newest
            else:
                s["meta_proc"] = meta
    conn.close()
    detail = _fin_detail(patient_file)
    out = []
    seen_dates = set()
    for key in order:
        s = sessions[key]
        seen_dates.add(s["date"])
        comp = complaints.get(s["date"])
        out.append(_mk(s["date"], s["tooth"],
                       comp["texts"] if comp else [],
                       " | ".join(s["diagnosis"]),
                       " | ".join(s["procedure"]), detail.get(key),
                       comp["id"] if comp else None, s["diagnosis_ids"],
                       s["procedure_ids"],
                       {"complaint": comp["meta"] if comp else None,
                        "diagnosis": s["meta_diag"],
                        "procedure": s["meta_proc"]}, s["tooth"]))
    for date, comp in complaints.items():
        if date in seen_dates:
            continue
        out.append(_mk(date, "", comp["texts"], "", "",
                       detail.get((date, frozenset())), comp["id"], [], [],
                       {"complaint": comp["meta"], "diagnosis": None,
                        "procedure": None}, ""))
    out.sort(key=lambda s: s["date"], reverse=True)
    return out
