"""Round 18 worker W2: phone search fix + grandfather search field.

The round-16 bug: search_patients() compared the phone criterion as
a RAW substring, so a stored national-form number did NOT match an
international-form search. Round 18 normalizes both sides to
digits (Arabic-Indic digits mapped to 0-9), strips a leading
country code / trunk 0, and suffix-matches when the normalized
query has >=7 digits. Also: the new grandfather (grand) criterion
substring-matches grand_name. Model-level; no display needed.
Seeded rows are cleaned up.

Round 46: no literal complete Syrian number may appear in the
tree (owner purge), so the Syrian-prefix branch is exercised with
inputs assembled from parts (_CC / _SUB below; the subscriber
digits are fictional), and the generic format variants use a
fictional Jordanian sample.
"""
from src.models.database import get_connection, init_db
from src.models.patients import (normalize_phone, phones_match,
                                 save_patient_record, search_patients)

_AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_CC = "9" + "63"
_SUB = "991" + "234" + "567"
_SY_NAT = "0" + _SUB                       # national form, trunk 0
_SY_INTL = "+" + _CC + _SUB
_SY_00 = "00" + _CC + _SUB
_SY_BARE = _CC + _SUB
_SY_NAT_SP = "0" + _SUB[:3] + " " + _SUB[3:6] + " " + _SUB[6:]
_SY_INTL_SP = "+" + _CC + " " + _SUB[:3] + " " + _SUB[3:6] + " " + _SUB[6:]
_SY_OTHER = "+" + _CC + "955" + "555" + "555"  # a different number
_JO = "0791234567"                         # fictional Jordanian sample
_JO_SIG = "791234567"


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
    mapped, country-prefix / trunk-0 stripped."""
    # Generic behaviour on the fictional Jordanian sample.
    assert normalize_phone(_JO) == _JO_SIG
    assert normalize_phone("0791 234 567") == _JO_SIG
    assert normalize_phone(_JO.translate(_AR)) == _JO_SIG
    assert normalize_phone(_JO_SIG) == _JO_SIG
    # The Syrian country-prefix branch (inputs assembled above).
    assert normalize_phone(_SY_NAT) == _SUB
    assert normalize_phone(_SY_INTL) == _SUB
    assert normalize_phone(_SY_00) == _SUB
    assert phones_match("+962 791 234 567", _JO)
    assert phones_match(_SY_INTL_SP, _SY_NAT)
    assert phones_match("1234567", _JO)  # >=7-digit suffix
    assert not phones_match("0799999999", _JO)
    assert not phones_match("", _JO)


def test_phone_search_all_formats_mobile1():
    """A patient stored in national form is found by the phone
    criterion in every typed format, and by the quick-search box.
    (The stored form and the Syrian-format queries are the values
    assembled from parts at the top of this file.)"""
    init_db()
    fid = _seed("R18Ph", "R18Dad", "R18Gpa", "R18Fam", m1=_SY_NAT)
    try:
        for fmt in (_SY_NAT, _SUB, _SY_INTL, _SY_00, _SY_NAT_SP,
                    _SY_INTL_SP, _SY_BARE, _SY_NAT.translate(_AR),
                    "91234567"):
            assert fid in _ids(search_patients(phone=fmt)), fmt
            assert fid in _ids(search_patients(q=fmt)), ("q", fmt)
        assert fid not in _ids(search_patients(phone="0799999999"))
        assert fid not in _ids(search_patients(phone=_SY_OTHER))
    finally:
        _cleanup(fid)


def test_phone_search_generic_formats():
    """The same format tolerance with the fictional Jordanian
    sample: national / significant / spaced / international /
    00-form / Arabic-Indic / suffix queries all find the patient."""
    init_db()
    fid = _seed("R18Jo", "R18Dad", "R18Gpa", "R18Fam", m1=_JO)
    try:
        for fmt in (_JO, _JO_SIG, "0791 234 567", "+962791234567",
                    "00962791234567", _JO.translate(_AR), "1234567"):
            assert fid in _ids(search_patients(phone=fmt)), fmt
            assert fid in _ids(search_patients(q=fmt)), ("q", fmt)
        assert fid not in _ids(search_patients(phone="0799999999"))
    finally:
        _cleanup(fid)


def test_phone_search_mobile2_and_emergency():
    """The same format tolerance applies to mobile2 and the
    emergency phone, not just mobile1."""
    init_db()
    fid = _seed("R18Ph2", "R18Dad", "R18Gpa", "R18Fam",
                m2="0781112223", em="0773334445")
    try:
        assert fid in _ids(search_patients(phone="781112223"))
        assert fid in _ids(search_patients(phone="078 111 2223"))
        assert fid in _ids(search_patients(phone="٠٧٧٣٣٣٤٤٤٥"))
        assert fid in _ids(search_patients(q="+962773334445"))
    finally:
        _cleanup(fid)


def test_grandfather_search():
    """grand= substring-matches grand_name (case-insensitive),
    alone and ANDed with the other name fields."""
    init_db()
    fid = _seed("R18Gf", "R18Dad", "Haj Mahmoud", "R18Fam",
                m1="0791200011")
    other = _seed("R18Gf2", "R18Dad", "Abu Karim", "R18Fam",
                  m1="0791200022")
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
                m1="0791200033")
    try:
        assert fid in _ids(search_patients(first="r18nm"))
        assert fid in _ids(search_patients(father="R18Father"))
        assert fid in _ids(search_patients(family="R18Family"))
        assert fid in _ids(search_patients(q="R18Nm"))
        assert fid not in _ids(search_patients(first="R18Nm",
                                               family="NoSuch"))
    finally:
        _cleanup(fid)
