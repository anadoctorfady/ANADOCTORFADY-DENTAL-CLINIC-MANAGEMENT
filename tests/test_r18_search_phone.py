"""Round 18 worker W2: phone search fix + grandfather search field.

The round-16 bug: search_patients() compared the phone criterion as
a RAW substring, so stored "0944234456" did NOT match a search for
"+963944234456" or "0944 234 456". Round 18 normalizes both sides
to digits (Arabic-Indic digits mapped to 0-9), strips a leading
country code (963 / 00963) / trunk 0, and suffix-matches when the
normalized query has >=7 digits. Also: the new grandfather (grand)
criterion substring-matches grand_name. Model-level; no display
needed. Seeded rows are cleaned up.
"""
from src.models.database import get_connection, init_db
from src.models.patients import (normalize_phone, phones_match,
                                 save_patient_record, search_patients)


def _seed(first, father, grand, last, m1="", m2="", em=""):
    return save_patient_record({
        "first_name": first, "father_name": father, "grand_name": grand,
        "last_name": last,
        "full_name": " ".join(p for p in (first, father, grand, last) if p),
        "birth_date_greg": "1990-05-15", "birth_date_hijri": "",
        "age_years": 0, "age_months": 0, "age_days": 0, "age_total_days": 0,
        "age_hijri_years": 0, "age_hijri_months": 0, "age_hijri_days": 0,
        "mobile1": m1, "mobile2": m2, "emergency_phone": em,
        "address": "", "nationality": "Syrian", "current_medications": "",
        "allergies": "", "diseases": ""})


def _cleanup(*fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _ids(rows):
    return [r["file_number"] for r in rows]


def test_normalize_phone_rule():
    """The normalization rule itself: digits only, Arabic-Indic
    mapped, 00963 / 963 / trunk-0 stripped."""
    assert normalize_phone("0944234456") == "944234456"
    assert normalize_phone("+963944234456") == "944234456"
    assert normalize_phone("00963944234456") == "944234456"
    assert normalize_phone("0944 234 456") == "944234456"
    assert normalize_phone("944234456") == "944234456"
    assert normalize_phone("٠٩٤٤٢٣٤٤٥٦") == "944234456"
    assert phones_match("+963 944 234 456", "0944234456")
    assert phones_match("44234456", "0944234456")  # >=7-digit suffix
    assert not phones_match("0999999999", "0944234456")
    assert not phones_match("", "0944234456")


def test_phone_search_all_formats_mobile1():
    """A patient stored as 0944234456 is found by the phone
    criterion in every typed format, and by the quick-search box."""
    init_db()
    fid = _seed("R18Ph", "R18Dad", "R18Gpa", "R18Fam", m1="0944234456")
    try:
        for fmt in ("0944234456", "944234456", "+963944234456",
                    "00963944234456", "0944 234 456", "+963 944 234 456",
                    "963944234456", "٠٩٤٤٢٣٤٤٥٦", "44234456"):
            assert fid in _ids(search_patients(phone=fmt)), fmt
            assert fid in _ids(search_patients(q=fmt)), ("q", fmt)
        assert fid not in _ids(search_patients(phone="0999999999"))
        assert fid not in _ids(search_patients(phone="+963955555555"))
    finally:
        _cleanup(fid)


def test_phone_search_mobile2_and_emergency():
    """The same format tolerance applies to mobile2 and the
    emergency phone, not just mobile1."""
    init_db()
    fid = _seed("R18Ph2", "R18Dad", "R18Gpa", "R18Fam",
                m2="0933111222", em="0955333444")
    try:
        assert fid in _ids(search_patients(phone="+963933111222"))
        assert fid in _ids(search_patients(phone="0933 111 222"))
        assert fid in _ids(search_patients(phone="٠٩٥٥٣٣٣٤٤٤"))
        assert fid in _ids(search_patients(q="+963955333444"))
    finally:
        _cleanup(fid)


def test_grandfather_search():
    """grand= substring-matches grand_name (case-insensitive),
    alone and ANDed with the other name fields."""
    init_db()
    fid = _seed("R18Gf", "R18Dad", "Haj Mahmoud", "R18Fam",
                m1="0912000111")
    other = _seed("R18Gf2", "R18Dad", "Abu Karim", "R18Fam",
                  m1="0912000222")
    try:
        assert fid in _ids(search_patients(grand="Mahmoud"))
        assert fid in _ids(search_patients(grand="haj mahmoud"))
        assert fid in _ids(search_patients(grand="Mahm"))
        assert other not in _ids(search_patients(grand="Mahmoud"))
        assert fid in _ids(search_patients(first="R18Gf",
                                           grand="Mahmoud"))
        assert fid not in _ids(search_patients(first="R18Gf",
                                               grand="Karim"))
    finally:
        _cleanup(fid, other)


def test_other_name_fields_still_work():
    """first / father / family criteria are unchanged by round 18."""
    init_db()
    fid = _seed("R18Nm", "R18Father", "R18Gpa", "R18Family",
                m1="0912000333")
    try:
        assert fid in _ids(search_patients(first="r18nm"))
        assert fid in _ids(search_patients(father="R18Father"))
        assert fid in _ids(search_patients(family="R18Family"))
        assert fid in _ids(search_patients(q="R18Nm"))
        assert fid not in _ids(search_patients(first="R18Nm",
                                               family="NoSuch"))
    finally:
        _cleanup(fid)
