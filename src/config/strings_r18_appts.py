"""Round 18 appointment-attendance strings (2026-11-14) -- worker W4.

ONLY EN and AR dicts + a tiny tr() lookup, copied from
strings_r16_patients.py. Attendance is COMPUTED at display from the
first procedure-writing time on the appointment day (see
src/models/appointments.attendance_for); the stored appointment
status is never overwritten. Every key has EN + AR and the UI shows
exactly ONE language (total language purity).
"""
EN = {
    'appt.attended': 'Attended',
    'appt.late': 'Late',
    'appt.absent': 'Did not attend',
}
AR = {
    'appt.attended': 'حضر',
    'appt.late': 'تأخر',
    'appt.absent': 'لم يحضر',
}


def tr(key, lang="en"):
    """Translated string for `key`: this module first, then t()."""
    d = AR if lang == "ar" else EN
    if key in d:
        return d[key]
    from src.config.strings import t
    return t(key, lang)


def attendance_label(status, lang="en"):
    """Single-language display text for a computed attendance status
    ('attended' | 'late' | 'absent'); '' for None / unknown (pending
    appointments show no attendance text at all)."""
    if status not in ("attended", "late", "absent"):
        return ""
    return tr(f"appt.{status}", lang)
