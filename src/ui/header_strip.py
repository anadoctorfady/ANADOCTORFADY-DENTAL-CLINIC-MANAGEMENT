"""Round-55 header-strip grid (patient_info.py builds it).

The strip is EXACTLY 3 ROWS x 5 columns across the full main
area. _GRID is (row, col, colspan, label key, patient-row key or
None, kind) in display order; Diseases spans 2 columns because
it is the long list. Father / grandfather / family are NOT in
the grid (removed by earlier instruction, still standing).

Colours: each cell carries its own vivid pastel from the settled
palette, in the (row*2+col) rotation, so no two neighbours --
before, after, above, below -- ever share a colour; the Balance
cell is the neutral Warm Sand. Dark text #2C241D in both themes.
"""
from src.config.strings_r18_patients import tr
from src.ui.vivid_rows import PALETTE

_GRID = ((0, 0, 1, "patient_info.name", "full_name", "name"),
         (0, 1, 1, "patient_info.age", None, "age"),
         (0, 2, 1, "patient_info.birth_date", None, "birth"),
         (0, 3, 1, "patient_info.hijri", None, "hijri"),
         (0, 4, 1, "patient_info.nationality", "nationality", "field"),
         (1, 0, 1, "patient_info.mobile1", "mobile1", "field"),
         (1, 1, 1, "patient_info.mobile2", "mobile2", "field"),
         (1, 2, 1, "patient_info.emergency", "emergency_phone", "field"),
         (1, 3, 1, "patient_info.address", "address", "field"),
         (1, 4, 1, "patient_info.balance", None, "balance"),
         (2, 0, 2, "patient_info.diseases", "diseases", "field"),
         (2, 2, 1, "patient_info.meds", "current_medications", "field"),
         (2, 3, 1, "patient_info.allergies", "allergies", "field"),
         (2, 4, 1, "patient_info.adherence", None, "adherence"))
NEUTRAL = "#F6F1E9"  # Warm Sand: the Balance cell (neighbours are pastel)


def cell_bg(row, col):
    """Background for the strip cell at (row, col): the Balance
    cell is neutral, every other cell cycles the pastel palette
    with a +2 row offset, so all four neighbours of every cell
    differ (pinned in test_r55_header_adherence)."""
    return NEUTRAL if (row, col) == (1, 4) else PALETTE[(row * 2 + col) % len(PALETTE)]


def birth_lines(row, lang):
    """Birth data as THREE values: Age / Birth date / Hijri.
    Hijri is RE-DERIVED from the Gregorian value in `lang` (never
    the stored birth_date_hijri string)."""
    raw = row.get("birth_date_greg") or ""
    birth, hijri = raw, ""
    try:
        from src.utils.hijri_age import format_birth_date, format_hijri_date
        birth = format_birth_date(birth); hijri = format_hijri_date(raw, lang)
    except Exception:
        pass
    age = tr("patient_info.age_fmt", lang).format(
        y=row.get("age_years") or 0, m=row.get("age_months") or 0,
        d=row.get("age_days") or 0)
    return [age, birth or "—", hijri or "—"]
