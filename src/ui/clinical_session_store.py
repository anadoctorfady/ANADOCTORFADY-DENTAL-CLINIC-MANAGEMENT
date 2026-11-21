"""Round 24: storage helpers for the unified-table Save handler
(split from clinical_session_save.py for the line cap): the
date-aware save gate, the money context (currency / rate /
treating doctor resolved from the clinical finance section), the
session_money validation wrapper, and the clinical-row insert /
update that mirror clinical_save.save_all's columns. <200 lines."""
from datetime import datetime
from src.config.strings import t
from src.config.strings_r24_session import sess_t
from src.models.database import get_connection
from src.models.permissions import can_add_payment
from src.models.phrases import save_phrase
from src.models import session_money as _sm
from src.ui import clinical_tables as _ct

_TABLE_FOR = {"complaint": "complaints", "symptom": "complaints",
              "diagnosis": "diagnoses", "procedure": "procedures"}


def texts(tab):
    return {key: _ct._text(tab, attr) for key, attr, _t in _ct.FIELDS}


def has_row(fid, table, date):
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM {table} WHERE patient_file=? AND visit_date=? LIMIT 1", (fid, date))
        row = cur.fetchone(); conn.close()
        return row is not None
    except Exception:
        return False


def has_clinical_on(fid, date):
    return any(has_row(fid, tb, date) for tb in ("complaints", "diagnoses", "procedures"))


def missing(tab, fid, date, txts):
    """Gate for a NEW session, evaluated against the ENTRY date:
    a field is missing when it has no text AND no row was already
    saved for this patient on that date in its table."""
    out = []
    for key, _attr, _t in _ct.FIELDS:
        if txts.get(key):
            continue
        if fid and has_row(fid, _TABLE_FOR[key], date):
            continue
        out.append(key)
    return out


def gate_error(tab, missing_keys):
    lang = getattr(tab.app, "lang", "en")
    names = ", ".join(t(_ct.FIELD_KEYS[k], lang) for k in missing_keys)
    _ct.messagebox.showerror(t("savegate.title", lang), t("savegate.missing", lang).format(fields=names))


def money_context(tab, edit=False):
    """(currency, rate, rate_date, base, doctor) from the clinical
    finance section widgets, or None (rate error already shown).
    In edit mode the session's own currency/rate win."""
    from src.models.currency import get_rate, save_rate, default_currency
    lang = getattr(tab.app, "lang", "en")
    base = getattr(tab, "base_cur", None) or default_currency()
    cur = getattr(tab, "_edit_currency", None) if edit else None
    if not cur:
        try:
            cur = tab.cur_code()
        except Exception:
            cur = base
    rdate = datetime.now().strftime("%Y-%m-%d")
    w = getattr(tab, "e_rate_date", None)
    if w is not None and w.get().strip():
        rdate = w.get().strip()
    rate = None
    if cur != base:
        if edit and getattr(tab, "_edit_rate", None):
            rate = float(tab._edit_rate)
        else:
            w = getattr(tab, "e_rate", None)
            try:
                rate = float(w.get()) if w is not None else None
                if rate is not None and rate <= 0:
                    rate = None
            except Exception:
                rate = None
            if rate is None:
                rate = get_rate(rdate, cur, base)
            if not rate:
                _ct.messagebox.showerror(t("clinical.rate_required_title", lang),
                                         t("clinical.rate_required_msg", lang).format(cur=cur, base=base))
                return None
            save_rate(rdate, rate, cur, base)
    doctor = ""
    dv = getattr(tab, "doctor_var", None)
    if dv is not None:
        doctor = dv.get().strip()
    return (cur, rate, rdate, base, doctor or getattr(tab, "current_user", "fady"))


def validate_money(tab, fid, total, paid, exclude=()):
    """session_money.validate with bilingual refusals. True = ok."""
    lang = getattr(tab.app, "lang", "en")
    if total < 0 or paid < 0:
        _ct.messagebox.showerror(t("clinical.error", lang), t("clinical.invalid_numbers", lang))
        return False
    ok, cap = _sm.validate(fid, total, paid, exclude)
    if not ok:
        _ct.messagebox.showerror(sess_t("sess.overpay_title", lang),
                                 sess_t("sess.overpay_msg", lang).format(paid=f"{paid:g}", cap=f"{cap:g}"))
        return False
    return True


def check_payment_perm(tab, doctor):
    lang = getattr(tab.app, "lang", "en")
    user = getattr(tab, "current_user", "fady"); role = getattr(tab, "current_role", "admin")
    if can_add_payment(role, doctor, user):
        return True
    _ct.messagebox.showerror(t("clinical.permission_title", lang), t("clinical.permission_msg", lang))
    return False


def insert_clinical(tab, fid, date, tooth, txts, note):
    """Insert the session's clinical rows (clinical_save.save_all's
    columns, but on the ENTRY date + entry tooth)."""
    now = datetime.now().isoformat()
    author = getattr(tab, "current_user", None) or getattr(tab.app, "current_user", None) or "fady"
    conn = get_connection(); cur = conn.cursor()
    if txts["complaint"] or txts["symptom"]:
        cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,symptoms,notes,symptoms_notes,author,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (fid, date, txts["complaint"], txts["symptom"], note, note, author, now))
    for kind in ("diagnosis", "procedure"):
        if not txts[kind]:
            continue
        table, col = _ct.TABLES[kind]
        cur.execute(f"INSERT INTO {table}(patient_file,visit_date,tooth_number,{col},notes,author,created_at) VALUES(?,?,?,?,?,?,?)",
                    (fid, date, tooth, txts[kind], note, author, now))
    conn.commit(); conn.close()
    if txts["complaint"]:
        save_phrase("complaint", txts["complaint"])
    if txts["symptom"]:
        save_phrase("symptom", txts["symptom"])
    if txts["procedure"]:
        save_phrase("service", txts["procedure"])


def update_clinical(tab, fid, session, txts, note):
    """Apply edited texts to the session's rows: the complaints row
    is updated in place (or inserted when the session had none);
    multi-row kinds collapse to the newest row updated + the others
    deleted; an emptied kind's rows are deleted. The original
    author / created_at of kept rows are preserved."""
    now = datetime.now().isoformat()
    author = getattr(tab, "current_user", None) or getattr(tab.app, "current_user", None) or "fady"
    date = session.get("date") or ""; tooth = session.get("tooth_raw") or ""
    conn = get_connection(); cur = conn.cursor()
    cid = session.get("complaints_id")
    if cid:
        cur.execute("UPDATE complaints SET complaint=?, symptoms=?, notes=?, symptoms_notes=? WHERE id=? AND patient_file=?",
                    (txts["complaint"], txts["symptom"], note, note, cid, fid))
    elif txts["complaint"] or txts["symptom"]:
        cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,symptoms,notes,symptoms_notes,author,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (fid, date, txts["complaint"], txts["symptom"], note, note, author, now))
    for kind, idkey in (("diagnosis", "diagnosis_ids"), ("procedure", "procedure_ids")):
        table, col = _ct.TABLES[kind]
        ids = list(session.get(idkey) or []); text = txts[kind]
        if not text:
            for rid in ids:
                cur.execute(f"DELETE FROM {table} WHERE id=? AND patient_file=?", (rid, fid))
        elif ids:
            keep = max(ids)
            cur.execute(f"UPDATE {table} SET {col}=?, notes=? WHERE id=? AND patient_file=?", (text, note, keep, fid))
            for rid in ids:
                if rid != keep:
                    cur.execute(f"DELETE FROM {table} WHERE id=? AND patient_file=?", (rid, fid))
        else:
            cur.execute(f"INSERT INTO {table}(patient_file,visit_date,tooth_number,{col},notes,author,created_at) VALUES(?,?,?,?,?,?,?)",
                        (fid, date, tooth, text, note, author, now))
    conn.commit(); conn.close()
