"""Patient alert strip (Job 4, round 12).

Shown on the patient panel (clinical page AND patient form) when the
selected patient has:
  (a) a drug allergy (patients.allergies) or current medication
      (patients.current_medications) -> RED strip;
  (b) an unpaid balance (patient_totals()["remaining"] > 0) -> AMBER strip;
  (c) a CREDIT balance (remaining < 0, round 38: advance payments --
      the clinic owes the patient) -> TEAL strip. (b) and (c) are
      mutually exclusive by construction.
All can show at once except (b)/(c). A clean patient shows nothing
(strip hidden).

Colours are deliberately far from the normal Warm Sand UI so the
alerts cannot be missed. patient_alerts() is pure (no widgets) so
tests can check the logic without a display.
"""
import tkinter as tk

from src.config.strings import t
from src.config.strings_r38 import r38_t
from src.models.finance import patient_totals

HEALTH_BG = "#DC2626"   # strong red
HEALTH_FG = "white"
BALANCE_BG = "#F59E0B"  # strong amber
BALANCE_FG = "#1F2937"
CREDIT_BG = "#0F766E"   # round 38: teal — white on it is 5.47:1
CREDIT_FG = "white"


def patient_alerts(patient, lang="en"):
    """List of (kind, message) for `patient` (dict-like row or None).
    kind is "health", "balance" or "credit" (round 38). Empty = clean."""
    if not patient:
        return []
    out = []
    allergies = (patient.get("allergies") or "").strip()
    if allergies:
        out.append(("health", t("alert.allergy", lang).format(detail=allergies)))
    meds = (patient.get("current_medications") or "").strip()
    if meds:
        out.append(("health", t("alert.meds", lang).format(detail=meds)))
    fid = patient.get("file_number")
    if fid:
        try:
            remaining = patient_totals(fid)["remaining"]
        except Exception:
            remaining = 0
        if remaining and remaining > 0:
            out.append(("balance", t("alert.balance", lang).format(
                amount=f"{remaining:,.2f}")))
        elif remaining and remaining < 0:
            out.append(("credit", r38_t("alert.credit", lang).format(
                amount=f"{abs(remaining):,.2f}")))
    return out


def make_alert_strip(parent):
    """Create the (initially hidden) strip; pack it into `parent`.
    Returns the frame; its .lbl_health / .lbl_balance children hold
    the two messages. Call refresh_alert_strip() on patient change."""
    strip = tk.Frame(parent)
    strip.lbl_health = tk.Label(strip, bg=HEALTH_BG, fg=HEALTH_FG,
                                font=("Segoe UI", 9, "bold"), wraplength=180,
                                justify="left")
    strip.lbl_health.pack(fill="x", padx=2, pady=1)
    strip.lbl_balance = tk.Label(strip, bg=BALANCE_BG, fg=BALANCE_FG,
                                 font=("Segoe UI", 9, "bold"), wraplength=180,
                                 justify="left")
    strip.lbl_balance.pack(fill="x", padx=2, pady=1)
    strip.lbl_credit = tk.Label(strip, bg=CREDIT_BG, fg=CREDIT_FG,
                                font=("Segoe UI", 9, "bold"), wraplength=180,
                                justify="left")
    strip.lbl_credit.pack(fill="x", padx=2, pady=1)
    strip.pack(fill="x", padx=8, pady=2)
    strip.pack_forget()  # hidden until a patient has an alert
    return strip


def refresh_alert_strip(strip, patient, lang="en"):
    """Show/hide the strip for `patient` (None = hide)."""
    if strip is None:
        return
    alerts = patient_alerts(patient, lang)
    health = [m for k, m in alerts if k == "health"]
    balance = [m for k, m in alerts if k == "balance"]
    credit = [m for k, m in alerts if k == "credit"]
    if not alerts:
        strip.pack_forget()
        return alerts
    if health:
        strip.lbl_health.config(text="\n".join(health))
        strip.lbl_health.pack(fill="x", padx=2, pady=1)
    else:
        strip.lbl_health.pack_forget()
    if balance:
        strip.lbl_balance.config(text="\n".join(balance))
        strip.lbl_balance.pack(fill="x", padx=2, pady=1)
    else:
        strip.lbl_balance.pack_forget()
    if credit:
        strip.lbl_credit.config(text="\n".join(credit))
        strip.lbl_credit.pack(fill="x", padx=2, pady=1)
    else:
        strip.lbl_credit.pack_forget()
    strip.pack(fill="x", padx=8, pady=2)
    return alerts
