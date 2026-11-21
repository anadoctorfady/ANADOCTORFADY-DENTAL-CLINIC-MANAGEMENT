"""Appointments quick-book (Job 8, round 12): one click books the next
free slot today for the patient already selected in the shell — no
typing of name or file number. The button lives on the booking row of
AppointmentsTab; its enabled state follows app.current_patient and is
refreshed by tab.load(). The time stays changeable via the existing
slot list + Add button. <200 lines."""
import tkinter as tk
from datetime import date
from tkinter import messagebox

from src.config.strings import t
from src.ui.rounded import rounded_button
from src.models.appointments import next_free_slot
from src.models.database import get_connection


def attach_quickbook(tab, row, th):
    """Add the patient prefill label + Quick-book button + hint to the
    booking row. Called once from AppointmentsTab._booking_row."""
    lang = tab.lang
    tab.lbl_qb_patient = tk.Label(row, bg=th["panel"], fg=th["text"],
                                  font=("Segoe UI", 10))
    tab.lbl_qb_patient.pack(side="left", padx=8)
    tab.btn_quickbook = rounded_button(row, text=t("appt.quickbook", lang),
                                  bg=th["accent"], fg="white", relief="flat",
                                  font=("Segoe UI", 10, "bold"),
                                  command=lambda: quickbook(tab))
    tab.btn_quickbook.pack(side="left", padx=4)
    tab.lbl_qb_hint = tk.Label(row, bg=th["panel"], fg=th["muted"],
                               font=("Segoe UI", 9))
    tab.lbl_qb_hint.pack(side="left", padx=4)
    refresh_quickbook(tab)


def refresh_quickbook(tab):
    """Enable the button only when a patient is selected; show the
    prefilled patient (name + file number) or a bilingual hint."""
    p = getattr(tab.app, "current_patient", None)
    lang = tab.lang
    if p:
        tab.btn_quickbook.config(state="normal")
        tab.lbl_qb_patient.config(text=t("appt.quickbook_patient", lang).format(
            name=p["full_name"], fid=p["file_number"]))
        tab.lbl_qb_hint.config(text="")
    else:
        tab.btn_quickbook.config(state="disabled")
        tab.lbl_qb_patient.config(text=t("appt.no_patient", lang))
        tab.lbl_qb_hint.config(text=t("appt.quickbook_hint", lang))


def quickbook(tab):
    """Book the next free slot today for the selected patient. Refuses
    (no insert) when the day is fully booked or the slot got taken."""
    p = getattr(tab.app, "current_patient", None)
    if not p:  # button is disabled then; guard anyway, never crash
        return
    lang = tab.lang
    today = date.today()
    conn = get_connection()
    slot = next_free_slot(conn, today)
    conn.close()
    if slot is None:
        messagebox.showinfo(t("appt.quickbook", lang),
                            t("appt.no_free_slot", lang))
        return
    rid = tab._insert(p["file_number"], today.isoformat(), slot,
                      tab.e_reason.get().strip()
                      or t("appt.default_reason", lang))
    if rid is None:  # slot taken between search and insert: warned in _insert
        return
    tab.pick(today, slot)
    tab.e_reason.delete(0, tk.END)
    tab.load()
    messagebox.showinfo(t("appt.quickbook_done_title", lang),
                        t("appt.quickbook_done", lang).format(
                            name=p["full_name"], time=slot))
