"""Round 40 (item 1): money flow of the ONE payment place.

The unified session entry is the only money entry now. Its Save
covers every money case through ONE split rule, computed from
session_money.payment_cap (the round-24 cap, unchanged):

  session_paid = min(Paid, max(cap, 0))   — what the session absorbs
  excess       = Paid - session_paid      — recorded as a round-38
                                            standalone payment row
                                            (patient CREDIT)

- Normal save: Paid <= cap -> excess 0, exactly the round-24 flow.
- Overpayment: the session absorbs up to the cap; the excess lands
  as an advance (credit) row and the user is told (bilingual info).
- Pure advance (Paid > 0, no tooth, no clinical text, Total 0):
  save_advance() records the standalone row directly.

The payment Note from the entry (tab.e_pay_note) is applied to
every money row the save creates. All refusals that existed stay:
negative amounts (validate), a missing foreign rate and the
payment permission (money_context / check_payment_perm, in
clinical_session_store). The EDIT path is untouched (round-24
validate + replace_session_money). <200 lines."""
from src.config.strings import t
from src.config.strings_r40 import r40_t
from src.models import session_money as _sm
from src.models import payments as _pay
from src.ui import clinical_session_store as _store
from src.ui import clinical_tables as _ct


def entry_note(tab):
    """The unified entry's optional payment note ('' when absent)."""
    w = getattr(tab, "e_pay_note", None)
    return w.get().strip() if w is not None else ""


def plan_split(tab, fid, total, paid):
    """(session_paid, excess, ctx) for a NEW-session / money-only
    save, or None when refused (the refusal dialog already shown:
    negative amounts, missing rate, payment permission). ctx is
    the money_context tuple (currency, rate, rate_date, base,
    doctor). No row is written here."""
    lang = getattr(tab.app, "lang", "en")
    if total < 0 or paid < 0:
        _ct.messagebox.showerror(t("clinical.error", lang),
                                 t("clinical.invalid_numbers", lang))
        return None
    if total == 0 and paid == 0:
        return (0.0, 0.0, None)
    ctx = _store.money_context(tab)
    if ctx is None:
        return None
    if not _store.check_payment_perm(tab, ctx[4]):
        return None
    cap = _sm.payment_cap(fid, total)
    session_paid = min(paid, max(cap, 0.0))
    return (session_paid, paid - session_paid, ctx)


def store_split(tab, fid, date, tooth, total, plan, note=""):
    """Write the planned rows: the session row (when it carries a
    Total or an absorbed Paid) + the standalone excess row (when
    any). Returns the excess actually recorded."""
    session_paid, excess, ctx = plan
    if ctx is None:
        return 0.0
    cur, rate, rdate, base, doctor = ctx
    user = getattr(tab, "current_user", "fady")
    if total or session_paid:
        _sm.save_session_money(fid, date, tooth, total, session_paid,
                               currency=cur, rate=rate, rate_date=rdate,
                               base=base, doctor=doctor, entered_by=user,
                               note=note)
    if excess > 1e-9:
        _pay.save_standalone_payment(fid, excess, date, currency=cur,
                                     rate=rate, rate_date=rdate, base=base,
                                     doctor=doctor, entered_by=user,
                                     note=note)
        return excess
    return 0.0


def split_info(tab, excess, ctx):
    """The bilingual info note: the excess became advance credit."""
    lang = getattr(tab.app, "lang", "en")
    _ct.messagebox.showinfo(
        r40_t("pay.split_title", lang),
        r40_t("pay.split_msg", lang).format(amount=f"{excess:g}",
                                            cur=ctx[0]))


def save_advance(tab, fid, date, paid, note=""):
    """Pure advance payment: ONE standalone row, never capped.
    True when saved (permission / rate refusals already shown)."""
    ctx = _store.money_context(tab)
    if ctx is None:
        return False
    if not _store.check_payment_perm(tab, ctx[4]):
        return False
    cur, rate, rdate, base, doctor = ctx
    _pay.save_standalone_payment(fid, paid, date, currency=cur, rate=rate,
                                 rate_date=rdate, base=base, doctor=doctor,
                                 entered_by=getattr(tab, "current_user", "fady"),
                                 note=note)
    return True
