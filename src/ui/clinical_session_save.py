"""Round 24: Save-session handler for the unified clinical table
(helpers: clinical_session_store.py). Round 40 (item 1): the
unified entry is the ONE payment place — the money flow (split
plan/store + pure advance) lives in clinical_money_flow.py.

NEW session: the four clinical fields are required (the standing
gate -- a field counts as filled when it has text OR a row was
already saved for this patient on the ENTRY date; the bilingual
error names the missing fields and nothing is saved). The visit
note is saved with the session, never gated on. Money (Total /
Paid of THIS session) follows the round-40 split: the session
absorbs Paid up to the round-24 cap (session_money.payment_cap);
any EXCESS is recorded as a standalone advance payment (patient
credit) with a bilingual info note — it is no longer refused.

MONEY-ONLY saves (no clinical text): with a session already saved
for the entry date, Save writes just the money (same split). With
NO tooth, NO text and Total 0, a Paid > 0 is a PURE ADVANCE
payment: one standalone row, directly.

EDIT save (from clinical_session_edit.start_edit): the all-four
gate does NOT apply; money goes through replace_session_money
with the session's own rows excluded from the cap -- and is
skipped entirely when the user lacks finance.edit_amounts (the
money boxes are locked in that state). <200 lines."""
from src.config.strings import t
from src.models import session_money as _sm
from src.ui import clinical_money_flow as _flow
from src.ui import clinical_session_entry as _entry
from src.ui import clinical_session_store as _store
from src.ui import clinical_tables as _ct


def save_session(tab):
    """The unified Save-session button: edit save while editing,
    otherwise a new session (or a money-only / advance save)."""
    if getattr(tab, "_editing_session", None) is not None:
        return _save_edit(tab)
    return _save_new(tab)


def _save_new(tab):
    if not tab._need():
        return False
    lang = getattr(tab.app, "lang", "en")
    fid = tab.app.current_patient["file_number"]
    date = _entry.entry_date(tab); tooth = _entry.entry_tooth(tab)
    txts = _store.texts(tab)
    try:
        total, paid = _entry.get_money(tab)
    except Exception:
        _ct.messagebox.showerror(t("clinical.error", lang), t("clinical.invalid_numbers", lang))
        return False
    note = _flow.entry_note(tab)
    if not any(txts.values()):
        return _save_money_only(tab, fid, date, tooth, total, paid, note)
    missing = _store.missing(tab, fid, date, txts)
    if missing:
        _store.gate_error(tab, missing)
        return False
    # Plan the money BEFORE writing anything, so a refused payment
    # leaves no clinical-only session behind.
    plan = _flow.plan_split(tab, fid, total, paid)
    if plan is None:
        return False
    visit_note = _ct._text(tab, "txt_visit_note")
    _store.insert_clinical(tab, fid, date, tooth, txts, visit_note)
    excess = _flow.store_split(tab, fid, date, tooth, total, plan, note)
    if excess:
        _flow.split_info(tab, excess, plan[2])
    _entry.clear_entry(tab)
    _after(tab, fid)
    return True


def _save_money_only(tab, fid, date, tooth, total, paid, note):
    """No clinical text in the entry: a 0/0 no-op when the day's
    session exists, a PURE ADVANCE standalone row (no tooth, Total
    0, Paid > 0), else a money-only save against the day's session
    (same split). Without a session that day: the gate error."""
    if total == 0 and paid == 0:
        if _store.has_clinical_on(fid, date):
            return True  # already saved: silent no-op (old save_all)
        _store.gate_error(tab, [k for k, _a, _t in _ct.FIELDS])
        return False
    if total == 0 and paid > 0 and not tooth:
        if not _flow.save_advance(tab, fid, date, paid, note):
            return False
        _entry.set_money(tab, 0, 0)
        _after(tab, fid)
        return True
    if not _store.has_clinical_on(fid, date):
        _store.gate_error(tab, [k for k, _a, _t in _ct.FIELDS])
        return False
    plan = _flow.plan_split(tab, fid, total, paid)
    if plan is None:
        return False
    excess = _flow.store_split(tab, fid, date, tooth, total, plan, note)
    if excess:
        _flow.split_info(tab, excess, plan[2])
    _entry.set_money(tab, 0, 0)
    _after(tab, fid)
    return True


def _save_edit(tab):
    from src.ui import clinical_session_edit as _edit
    session = tab._editing_session
    if not tab._need():
        return False
    lang = getattr(tab.app, "lang", "en")
    fid = tab.app.current_patient["file_number"]
    txts = _store.texts(tab)
    note = _ct._text(tab, "txt_visit_note")
    locked = not _edit.can_edit_money(tab)
    total = paid = None; ctx = None
    if not locked:
        try:
            total, paid = _entry.get_money(tab)
        except Exception:
            _ct.messagebox.showerror(t("clinical.error", lang), t("clinical.invalid_numbers", lang))
            return False
        if not _store.validate_money(tab, fid, total, paid, exclude=session.get("financial_ids") or ()):
            return False
        ctx = _store.money_context(tab, edit=True)
        if ctx is None:
            return False
    _store.update_clinical(tab, fid, session, txts, note)
    if not locked:
        cur, rate, rdate, base, doctor = ctx
        _sm.replace_session_money(fid, session, total, paid, currency=cur, rate=rate,
                                  rate_date=rdate, base=base, doctor=doctor,
                                  entered_by=getattr(tab, "current_user", "fady"))
    tab._editing_session = None; tab._edit_currency = None; tab._edit_rate = None
    _edit.set_editing_ui(tab, None)
    _entry.clear_entry(tab)
    _after(tab, fid)
    return True


def _after(tab, fid):
    try:
        tab.load(fid)
    except Exception:
        pass
    try:
        tab.app.refresh_clinical()
    except Exception:
        pass
