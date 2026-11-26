"""Round 49 Section G strings: the Statistics dashboard.
Keys prefixed "stats.". Coordinator merges into strings.py with:
from src.config.strings_r49_stats import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
Until merged, finance_stats reads through stats_t() below (this
module first, then t()). EN values carry no Arabic; AR values carry
no Latin except units/numbers."""

EN = {
    "stats.tab": "Statistics",
    "stats.title": "Statistics",
    "stats.period": "Period",
    "stats.this_month": "This month",
    "stats.last_month": "Last month",
    "stats.custom": "Custom",
    "stats.from": "From",
    "stats.to": "To",
    "stats.refresh": "Refresh",
    "stats.by_count": "Top treatments by count",
    "stats.by_income": "Top treatments by income",
    "stats.income_vs_expenses": "Income vs expenses",
    "stats.monthly": "Income vs expenses by month",
    "stats.income": "Income",
    "stats.expenses": "Expenses",
    "stats.net": "Net",
    "stats.operating": "Operating expenses",
    "stats.lab": "Lab costs",
    "stats.salaries": "Salaries",
    "stats.expenses_total": "Total expenses",
    "stats.no_data": "No data in this period",
    "stats.admin_only": "Statistics are admin-only.",
    "stats.sessions": "sessions",
}

AR = {
    "stats.tab": "الإحصائيات",
    "stats.title": "الإحصائيات",
    "stats.period": "الفترة",
    "stats.this_month": "هذا الشهر",
    "stats.last_month": "الشهر الماضي",
    "stats.custom": "مخصص",
    "stats.from": "من",
    "stats.to": "إلى",
    "stats.refresh": "تحديث",
    "stats.by_count": "أكثر العلاجات عدداً",
    "stats.by_income": "أكثر العلاجات دخلاً",
    "stats.income_vs_expenses": "الدخل مقابل المصروفات",
    "stats.monthly": "الدخل مقابل المصروفات شهرياً",
    "stats.income": "الدخل",
    "stats.expenses": "المصروفات",
    "stats.net": "الصافي",
    "stats.operating": "المصروفات التشغيلية",
    "stats.lab": "تكاليف المختبر",
    "stats.salaries": "الرواتب",
    "stats.expenses_total": "إجمالي المصروفات",
    "stats.no_data": "لا توجد بيانات في هذه الفترة",
    "stats.admin_only": "الإحصائيات للمدير فقط.",
    "stats.sessions": "جلسات",
}


def stats_t(key, lang="en"):
    """Round-49 stats string: this module first, then t()."""
    from src.config.strings import t
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
