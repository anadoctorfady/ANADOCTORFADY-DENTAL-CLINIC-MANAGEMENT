"""Round 41 strings: the dental chart's jaw-selection shortcut
buttons (item 3). EN + AR dicts with a local reader (same pattern
as strings_r40): prefer these dicts, then EN, then t()."""
from src.config.strings import t

EN = {
    "chart.select_all": "Select all teeth",
    "chart.select_upper": "Upper jaw only",
    "chart.select_lower": "Lower jaw only",
}

AR = {
    "chart.select_all": "اختيار كل الأسنان",
    "chart.select_upper": "الفك العلوي فقط",
    "chart.select_lower": "الفك السفلي فقط",
}


def r41_t(key, lang="en"):
    """Round-41 string: this module first, then t()."""
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
