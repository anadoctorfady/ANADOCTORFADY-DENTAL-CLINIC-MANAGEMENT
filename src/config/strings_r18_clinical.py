"""Round 18 clinical strings (2026-11-14).

Sticky save bar + repositioned history section (items 5 + 6).
ONLY EN and AR dicts + the r18_t() reader -- nothing else. UI code
reads these via r18_t(), which prefers these dicts and falls back
to t(), so the UI is correct before and after the coordinator wires
them into src.config.strings. Every key needs EN + AR, one language
per value (total language purity).
"""
from src.config.strings import t

EN = {
    'r18.clinical.history_heading': 'History — what was done',
}

AR = {
    'r18.clinical.history_heading': 'السجل — ما تم إنجازه',
}


def r18_t(key, lang="en"):
    """Round-18 string: prefer this module's dicts, then EN, then t()."""
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
