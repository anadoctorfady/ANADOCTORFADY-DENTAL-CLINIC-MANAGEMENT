"""Round 24: Save-session handler for the unified clinical table
(helpers: clinical_session_store.py).

NEW session: the four clinical fields are required (the standing
gate -- a field counts as filled when it has text OR a row was
already saved for this patient on the ENTRY date; the bilingual
error names the missing fields and nothing is saved). The visit
note is saved with the session, never gated on. Money (Total /
Paid of THIS session) is validated through session_money.validate
-- Paid may exceed the session's own Total up to the patient's
outstanding balance from earlier sessions (item 3) -- and stored
as ONE financial row via session_money.save_session_money.

MONEY-ONLY save (coordinator addition): when all four fields are
empty but a clinical session already exists for the entry date,
Save writes just the financial row.

EDIT save (from clinical_session_edit.start_edit): the all-four
gate does NOT apply; money goes through replace_session_money
with the session's own rows excluded from the cap -- and is
skipped entirely when the user lacks finance.edit_amounts (the
money boxes are locked in that state). <200 lines."""
from src.config.strings import t
from src.models import session_money as _sm
from src.ui import clinical_session_entry as _entry
from src.ui import clinical_session_store as _store
from src.ui import clinical_tables as _ct


def save_session(tab):
    """The unified Save-session button: edit save while editing,
    otherwise a new session (or a money-only save)."""
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
    if not any(txts.values()):
        # Money-only path: the clinical part must already exist
        # for the entry date; 0/0 with it saved is a silent no-op
        # (the old save_all behaviour for an already-saved visit).
        if _store.has_clinical_on(fid, date):
            if total == 0 and paid == 0:
                return True
            return _save_money_part(tab, fid, date, tooth, total, paid)
        _store.gate_error(tab, [k for k, _a, _t in _ct.FIELDS])
        return False
    missing = _store.missing(tab, fid, date, txts)
    if missing:
        _store.gate_error(tab, missing)
        return False
    # Validate money + resolve its context BEFORE writing anything,
    # so a refused payment leaves no clinical-only session behind.
    if not _save_money_part(tab, fid, date, tooth, total, paid, clinical_pending=True):
        return False
    note = _ct._text(tab, "txt_visit_note")
    _store.insert_clinical(tab, fid, date, tooth, txts, note)
    if total or paid:
        ctx = _store.money_context(tab)
        cur, rate, rdate, base, doctor = ctx
        _sm.save_session_money(fid, date, tooth, total, paid, currency=cur, rate=rate,
                               rate_date=rdate, base=base, doctor=doctor,
                               entered_by=getattr(tab, "current_user", "fady"))
    _entry.clear_entry(tab)
    _after(tab, fid)
    return True


def _save_money_part(tab, fid, date, tooth, total, paid, clinical_pending=False):
    """Validate the money part; for the money-only path also store
    it. With clinical_pending=True only validation + the payment
    permission run here -- the caller stores the row AFTER the
    clinical rows, so money never lands without its session."""
    if total == 0 and paid == 0:
        return True
    if not _store.validate_money(tab, fid, total, paid):
        return False
    ctx = _store.money_context(tab)
    if ctx is None:
        return False
    cur, rate, rdate, base, doctor = ctx
    if not _store.check_payment_perm(tab, doctor):
        return False
    if clinical_pending:
        return True
    _sm.save_session_money(fid, date, tooth, total, paid, currency=cur, rate=rate,
                           rate_date=rdate, base=base, doctor=doctor,
                           entered_by=getattr(tab, "current_user", "fady"))
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
