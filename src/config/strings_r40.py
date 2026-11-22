"""Round 40 strings: the single payment place — the overpayment
split note. EN + AR dicts with a local reader (same pattern as
strings_r38): prefer these dicts, then EN, then t().
Placeholders: {amount} {cur}."""
from src.config.strings import t

EN = {
    "pay.split_title": "Part recorded as advance",
    "pay.split_msg": ("The amount paid is more than this session can "
                      "absorb. The excess {amount} {cur} was recorded "
                      "as an advance payment — patient credit (the "
                      "clinic owes the patient)."),
}

AR = {
    "pay.split_title": "سُجّل جزء كمبلغ مقدم",
    "pay.split_msg": ("المبلغ المدفوع أكبر مما تستطيع هذه الجلسة "
                      "استيعابه. سُجّل الفائض {amount} {cur} دفعةً "
                      "مقدمة — رصيد دائن للمريض (العيادة مدينة "
                      "للمريض)."),
}


def r40_t(key, lang="en"):
    """Round-40 string: this module first, then t()."""
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
