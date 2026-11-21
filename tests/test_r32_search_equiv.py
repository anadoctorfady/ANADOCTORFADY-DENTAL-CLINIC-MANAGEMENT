"""Round 32: SQL search/find_duplicate == OLD fetchall semantics.

The REFERENCE copies below are the pre-round-32 implementations
(from round32_gate/tree_before/src/models/patients.py), operating
on the same DB with fetchall + Python filtering. The NEW indexed
SQL implementations must return identical results (order included)
over a seeded randomized patient set: Arabic hamza/alef variants
(NOT folded -- norm_name is strip+casefold only), teh/heh and
yeh/alef-maksura variants, mixed-case Latin, phones in 09.. /
+963.. / 00963.. / Arabic-Indic / spaced / dashed / short / "0" /
NULL / empty forms, ~5% soft-deleted, NULL name parts. Seeded rows
(file_number >= 920000) are deleted again after each test.
"""
import random
from src.models.database import get_connection, init_db
from src.models.patient_norms import (ensure_patient_norms, norm_name,
                                      phones_match)
from src.models.patients import find_duplicate, search_patients

_PHONES = ("mobile1", "mobile2", "emergency_phone")
BASE, BASE2 = 920000, 930000


def _old_find_duplicate(first, father, last, exclude_file=None):
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT file_number, first_name, father_name, "
                "last_name, deleted FROM patients")
    want = (norm_name(first), norm_name(father), norm_name(last))
    found = None
    for r in cur.fetchall():
        got = (norm_name(r["first_name"]), norm_name(r["father_name"]),
               norm_name(r["last_name"]))
        if got == want and not r["deleted"] \
                and r["file_number"] != exclude_file:
            found = r["file_number"]; break
    conn.close(); return found


def _old_has(q, first, father, grand, family, phone):
    return any((v or "").strip() for v in (q, first, father, grand, family, phone))


def _old_search(q=None, first=None, father=None, grand=None, family=None,
                phone=None, current_file=None, limit=500):
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT file_number, full_name, first_name, father_name,"
                " grand_name, last_name, mobile1, mobile2,"
                " emergency_phone, deleted FROM patients"
                " ORDER BY file_number DESC")
    rows = [dict(r) for r in cur.fetchall() if not r["deleted"]]
    conn.close()
    if not _old_has(q, first, father, grand, family, phone):
        if current_file is None:
            return []
        return [r for r in rows if r["file_number"] == current_file][:1]
    qn = norm_name(q)
    names = tuple((norm_name(v), c) for v, c in ((first, "first_name"),
                  (father, "father_name"), (grand, "grand_name"),
                  (family, "last_name")))
    out = []
    for r in rows:
        if qn and qn not in norm_name(r["full_name"]) \
                and qn not in str(r["file_number"]) \
                and not any(phones_match(q, r[c]) for c in _PHONES):
            continue
        if any(v and v not in norm_name(r[c]) for v, c in names):
            continue
        if phone and not any(phones_match(phone, r[c]) for c in _PHONES):
            continue
        out.append({"file_number": r["file_number"],
                    "full_name": r["full_name"], "mobile1": r["mobile1"] or ""})
        if len(out) >= limit:
            break
    return out


_AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
FIRST = ["أحمد", "احمد", "إبراهيم", "ابراهيم", "محمد", "Sara", "sara", "SARA",
         "John", "Mona", "منى", "على", "علي", "فاطمة", "خالد", "Khaled",
         "Omar", "عمر", "Layla", "ليلى", None, ""]
FATHER = ["محمد", "Mohammed", "علي", "Ali", "حسن", "Hassan", "عمر", "Omar",
          "خالد", "سعيد", "Saeed", None, ""]
GRAND = ["حاج محمود", "Abu Karim", "سعيد", "Saeed", "حسن", None, "", "Karim"]
FAMILY = ["الحسن", "حسن", "Hassan", "Saleh", "صالح", "Nasser", "ناصر",
          "المصري", "Al-Masri", "Haddad", "حداد", None, ""]


def _phone(rng):
    base = "09" + "".join(rng.choice("0123456789") for _ in range(8))
    style = rng.randrange(9)
    if style == 0: return base
    if style == 1: return "+963" + base[1:]
    if style == 2: return "00963" + base[1:]
    if style == 3: return base.translate(_AR)
    if style == 4: return base[:4] + " " + base[4:7] + " " + base[7:]
    if style == 5: return base[:5] + "-" + base[5:]
    if style == 6: return rng.choice(["12345", "4423", "0", "123", ""])
    if style == 7: return None
    return base[2:]


def _seed(base, count=300):
    rng = random.Random(32032); rows = []
    for i in range(count):
        f, fa, g, la = (rng.choice(FIRST), rng.choice(FATHER),
                        rng.choice(GRAND), rng.choice(FAMILY))
        full = " ".join(p for p in (f, fa, g, la) if p) or None
        rows.append((base + 100 + i, f, fa, g, la, full, _phone(rng),
                     _phone(rng), _phone(rng),
                     rng.choice([0, 0, 0, 0, 0, 0, 0, 0, 1, None])))
    rows += [(base, "DeletedOnlyR32", "DelDad", "DelGrand", "DelFam",
              "DeletedOnlyR32 DelDad DelGrand DelFam", "0911111111",
              None, None, 1),
             (base + 1, "ZeroPhoneR32", "ZeroDad", None, "ZeroFam",
              "ZeroPhoneR32 ZeroDad ZeroFam", "0", None, None, 0),
             (base + 2, None, None, None, None, None, None, None, None, 0),
             (base + 3, "NoFullR32", "NFDad", "", "NFFam", None,
              "0933333333", "", None, None)]
    conn = get_connection()
    conn.executemany("INSERT INTO patients(file_number,first_name,"
                     "father_name,grand_name,last_name,full_name,mobile1,"
                     "mobile2,emergency_phone,deleted)"
                     " VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit(); ensure_patient_norms(conn); conn.close()
    return rows


def _cleanup(*bases):
    conn = get_connection()
    for b in bases:
        conn.execute("DELETE FROM patients WHERE file_number>=?"
                     " AND file_number<?", (b, b + 10000))
    conn.commit(); conn.close()


def test_search_equivalence_battery():
    init_db(); rows = _seed(BASE)
    try:
        queries = [{}, {"current_file": BASE + 1}, {"current_file": BASE},
                   {"current_file": 999999999}, {"q": "أحمد"}, {"q": "احمد"},
                   {"q": "sara"}, {"q": "SARA"}, {"q": "حسن"}, {"q": "9200"},
                   {"q": "+963"}, {"q": "٠٩٤٤"}, {"first": "أحمد"},
                   {"first": "احمد"}, {"first": "sArA"}, {"father": "محمد"},
                   {"grand": "حاج"}, {"family": "Hassan"}, {"family": "حسن"},
                   {"first": "Sara", "family": "Hassan"},
                   {"first": "Sara", "family": "NoSuchR32"},
                   {"phone": "+963944234456"}, {"phone": "44234456"},
                   {"phone": "4423"}, {"phone": "٠٩٤٤٢٣٤٤٥٦"},
                   {"phone": "0"}, {"phone": "123"},
                   {"phone": " ", "first": "Sara"}, {"phone": "0999999999"},
                   {"first": "DeletedOnlyR32"}, {"q": "DeletedOnlyR32"},
                   {"q": "ZeroPhoneR32"}, {"q": "9999999"},
                   {"first": "NoFullR32"}, {"q": "NoFullR32"},
                   {"father": "NFDad", "family": "NFFam"},
                   {"first": "Sara", "phone": "4423"}, {"q": "على"},
                   {"q": "علي"}, {"family": "ة"}, {"grand": "karim"}]
        assert len(queries) >= 25
        for kw in queries:
            new, old = search_patients(**kw), _old_search(**kw)
            assert new == old, (kw, new[:5], old[:5])
        sample = rows[10]
        triples = [("DeletedOnlyR32", "DelDad", "DelFam"),
                   ("ZeroPhoneR32", "ZeroDad", "ZeroFam"),
                   (" zerophoner32 ", "ZERODAD", "ZeroFam"),
                   ("NoFullR32", "NFDad", "NFFam"), ("NobodyR32", "X", "Y"),
                   (None, None, None), (sample[1], sample[2], sample[4])]
        for t in triples:
            assert find_duplicate(*t) == _old_find_duplicate(*t), t
            got = _old_find_duplicate(*t)
            assert find_duplicate(*t, exclude_file=got) == \
                _old_find_duplicate(*t, exclude_file=got), (t, got)
        assert find_duplicate("ZeroPhoneR32", "ZeroDad", "ZeroFam",
                              exclude_file=BASE + 1) is None
    finally:
        _cleanup(BASE)


def test_search_limit_equivalence():
    init_db(); conn = get_connection()
    conn.executemany("INSERT INTO patients(file_number,first_name,"
                     "father_name,last_name,full_name,mobile1,deleted)"
                     " VALUES(?,?,?,?,?,?,0)",
                     [(BASE2 + i, "LimitR32", "LimDad", "LimitFamR32",
                       "LimitR32 LimDad LimitFamR32", "0912000000")
                      for i in range(520)])
    conn.commit(); ensure_patient_norms(conn); conn.close()
    try:
        for kw in ({"family": "LimitFamR32"}, {"q": "LimitR32"},
                   {"family": "LimitFamR32", "limit": 10}):
            new, old = search_patients(**kw), _old_search(**kw)
            assert new == old and len(new) == kw.get("limit", 500), kw
    finally:
        _cleanup(BASE2)
