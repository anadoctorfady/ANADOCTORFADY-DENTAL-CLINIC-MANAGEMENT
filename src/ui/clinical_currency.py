"""Clinical finance per-currency breakdown (Round 19, Job R19-E).

When the open patient has financial records in MORE THAN ONE
currency, a compact breakdown block appears under the clinical
totals: one RAW line per currency (total / paid / remaining, no
conversion -- the totals boxes above show the converted base sums,
which is exactly why the per-currency split matters). A patient
with records in a single currency (or none) sees nothing new: the
frame stays empty and collapses. Own functions only -- a later
layout job repositions the frame, it does not rewrite this logic.
"""
import tkinter as tk
from src.config.strings import t
from src.config.theme import TABLE, is_dark
from src.models.finance_currency import patient_totals_by_currency

# Round 21 (item 3): in dark mode the finance SECTION takes the
# cost boxes' treatment -- its background becomes the Total box's
# deep brown (#92400E, BOXES below) and its label
# colours switch to the boxes' light foregrounds. Light mode is
# byte-identical to before (TABLE tint + dark text).
FIN_BG_DARK = "#92400E"

# Distinct box colours: name -> ((light bg, fg), (dark bg, fg)).
# Round 40: moved here from clinical_finance (deleted with the
# round-38 Payment entry zone) — the unified entry's Date / Paid
# boxes and the rate-date box wear them now.
BOXES = {"total": (("#FDE68A", "#2C241D"), ("#92400E", "#FFFFFF")),
         "date": (("#EDE9FE", "#2C241D"), ("#6D28D9", "#FFFFFF"))}


def _box(name):
    """The active (bg, fg) of a coloured box for the mode."""
    return BOXES[name][1] if is_dark() else BOXES[name][0]


def fin_bg():
    """The clinical finance section background for the mode."""
    return FIN_BG_DARK if is_dark() else TABLE["finance"]


def fin_fg():
    """Primary label colour inside the finance section."""
    return "#FFFFFF" if is_dark() else "#2C241D"


def fin_muted():
    """Muted label colour inside the finance section."""
    return "#F3D9B8" if is_dark() else "#6B5E53"


def build_currency_breakdown(tab, parent):
    """Create the (initially empty) breakdown frame under the
    totals row of the clinical finance section. Round 24: the
    frame also carries the PATIENT totals line (tab.lbl_pat_
    totals) -- the finance boxes are a per-payment entry now
    (session_money semantics), so the patient's cumulative
    Total / Paid / Remaining lives on this label instead."""
    frame = tk.Frame(parent, bg=fin_bg())
    frame.pack(fill="x", pady=1)
    tab._cur_break_frame = frame
    tab.lbl_pat_totals = tk.Label(frame, text="", bg=fin_bg(),
                                  fg=fin_fg(), font=("Segoe UI", 9, "bold"),
                                  justify="left", anchor="w")
    tab.lbl_pat_totals.pack(fill="x", padx=2)
    tab.lbl_cur_break = tk.Label(frame, text="", bg=fin_bg(),
                                 fg=fin_muted(), font=("Segoe UI", 8),
                                 justify="left", anchor="w")


def refresh_patient_totals(tab, fid):
    """Fill tab.lbl_pat_totals from finance.patient_totals (base
    currency); blank when no patient / no label. Round 38: a
    NEGATIVE remaining is patient CREDIT (advance payments) — the
    line switches to the credit wording + the credit colour
    (theme.credit_color on this section's background)."""
    lbl = getattr(tab, "lbl_pat_totals", None)
    if lbl is None:
        return
    if not fid:
        lbl.config(text="")
        return
    try:
        from src.models.finance import patient_totals
        from src.config.strings import t as _t
        from src.config.strings_r38 import r38_t
        from src.config.theme import credit_color, is_dark
        tot = patient_totals(fid)
        lang = getattr(tab.app, "lang", "en")
        if tot["remaining"] < 0:
            lbl.config(text=r38_t("credit.balance_fmt", lang).format(
                total=f"{tot['total']:,.2f}", paid=f"{tot['paid']:,.2f}",
                remaining=f"{abs(tot['remaining']):,.2f}"),
                fg=credit_color(is_dark()))
        else:
            lbl.config(text=_t("sess.pat_balance", lang).format(
                total=f"{tot['total']:,.2f}", paid=f"{tot['paid']:,.2f}",
                remaining=f"{tot['remaining']:,.2f}"), fg=fin_fg())
    except Exception:
        pass


def refresh_currency_breakdown(tab, fid):
    """Fill the breakdown for patient `fid`; >1 currency -> show
    one raw line per currency, otherwise hide it completely."""
    lbl = getattr(tab, "lbl_cur_break", None)
    if lbl is None or fid is None:
        return
    try:
        rows = patient_totals_by_currency(fid)
    except Exception:
        rows = []
    if len(rows) <= 1:
        try:
            lbl.pack_forget()
        except Exception:
            pass
        return
    lang = getattr(tab.app, "lang", "en")
    lines = [t("fincur.breakdown_title", lang)]
    for r in rows:
        lines.append(t("fincur.patient_line", lang).format(
            cur=r["currency"], total=f"{r['total']:.2f}",
            paid=f"{r['paid']:.2f}", rem=f"{r['remaining']:.2f}"))
    lbl.config(text="\n".join(lines))
    if not lbl.winfo_ismapped():
        lbl.pack(fill="x", padx=2)
