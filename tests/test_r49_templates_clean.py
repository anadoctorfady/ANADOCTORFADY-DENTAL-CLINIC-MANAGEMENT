"""Round 49, section E: tooth numbers out of built-in templates.

Seed inventory finding: phrases_seed.json + specialties.json contain
NO digit characters at all, so (a) pins that purity with an
independent standalone-FDI detector (Latin + Arabic-Indic digits),
and (b)/(c) verify the stored-row migration in
src/models/template_cleanup.py: rows seeded by older builds whose
text is exactly a current seed plus a standalone FDI number are
rewritten to the cleaned seed; user rows and custom templates are
never touched; UNIQUE collisions delete the stale row; overrides
keyed by an old seed text are re-keyed, not orphaned.
"""
import json, re, sqlite3
from pathlib import Path

from src.models import phrases, specialty_templates as tpl
from src.models import template_cleanup as tc
from src.models.database import get_connection

DATA = Path(__file__).resolve().parent.parent / "src" / "data"
FDI = {str(n) for n in list(range(11, 19)) + list(range(21, 29))
       + list(range(31, 39)) + list(range(41, 49)) + list(range(51, 56))
       + list(range(61, 66)) + list(range(71, 76)) + list(range(81, 86))}
_DIG = {chr(0x660 + i): str(i) for i in range(10)}
_DIG.update({chr(0x6F0 + i): str(i) for i in range(10)})

def _has_fdi(text):
    norm = "".join(_DIG.get(ch, ch) for ch in text or "")
    return any(m.group(1) in FDI for m in re.finditer(r"(?<!\d)(\d{2})(?!\d)", norm))

def _all_seed_texts():
    out = []
    phrases_data = json.loads((DATA / "phrases_seed.json").read_text(encoding="utf-8"))
    for cat, items in phrases_data.items():
        out += [(f"phrases:{cat}", t) for t in items]
    specs = json.loads((DATA / "specialties.json").read_text(encoding="utf-8"))
    for sp in specs["specialties"]:
        for cat, items in sp["phrases"].items():
            for ph in items:
                out.append((f"{sp['id']}:{cat}:en", ph.get("en", "")))
                out.append((f"{sp['id']}:{cat}:ar", ph.get("ar", "")))
    return out

def test_seed_purity_no_fdi_tokens():
    texts = _all_seed_texts()
    assert len(texts) > 300  # both seed files really scanned
    bad = [(loc, t) for loc, t in texts if _has_fdi(t)]
    assert bad == [], f"seed texts still carrying FDI numbers: {bad}"

def test_clean_text_units():
    assert tc.clean_text("Pain in tooth 46") == "Pain in tooth"
    assert tc.clean_text("ألم في السن 46") == "ألم في السن"
    assert tc.clean_text("ألم في السن ٤٦ الأمامي") == "ألم في السن الأمامي"
    assert tc.clean_text("ألم في السن ٨٥") == "ألم في السن"
    assert tc.clean_text("Type 2 diabetes") == "Type 2 diabetes"
    assert tc.clean_text("Dose 500 mg twice daily") == "Dose 500 mg twice daily"
    assert tc.clean_text("Review in 2024 please") == "Review in 2024 please"
    assert tc.clean_text("Class II malocclusion") == "Class II malocclusion"
    assert tc.clean_text("Visit 146 done") == "Visit 146 done"

def _phrase_rows(conn):
    return sorted((r["category"], r["text"]) for r in
                  conn.execute("SELECT category, text FROM reusable_phrases"))

def test_migration_phrases_on_db_copy():
    phrases.ensure_tables()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM reusable_phrases")
        ins = "INSERT INTO reusable_phrases(category,text,usage_count,last_used) VALUES(?,?,1,'2026-01-01')"
        conn.execute(ins, ("complaint", "Persistent pain in front tooth 46"))
        conn.execute(ins, ("complaint", "ألم مستمر في السن ٤٦ الأمامي"))
        conn.execute(ins, ("diagnosis", "Deep caries 36"))   # collision pair
        conn.execute(ins, ("diagnosis", "Deep caries"))
        conn.execute(ins, ("complaint", "Patient says tooth 46 hurts at night"))  # user row
        conn.commit()
        phrases.seed_if_empty()  # hook: cleanup_phrases()
        rows = _phrase_rows(conn)
        assert ("complaint", "Persistent pain in front tooth") in rows
        assert ("complaint", "ألم مستمر في السن الأمامي") in rows
        assert ("diagnosis", "Deep caries") in rows
        assert ("diagnosis", "Deep caries 36") not in rows
        assert rows.count(("diagnosis", "Deep caries")) == 1  # collision: stale deleted
        assert ("complaint", "Patient says tooth 46 hurts at night") in rows  # byte-identical
        assert not any(_has_fdi(t) and ("tooth" in t.lower() or "السن" in t)
                       for _c, t in rows if t != "Patient says tooth 46 hurts at night")
        snap = _phrase_rows(conn)
        phrases.seed_if_empty()  # second run: no-op
        assert _phrase_rows(conn) == snap
    finally:
        conn.execute("DELETE FROM reusable_phrases"); conn.commit(); conn.close()
        phrases.seed_if_empty()  # restore full seeds for other tests

def _mem():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row; return conn

def test_migration_specialty_templates():
    conn = _mem()
    tpl.ensure_tables(conn)  # seeds all built-in pairs
    ins = ("INSERT INTO specialty_templates(specialty,category,text_en,text_ar,is_custom)"
           " VALUES(?,?,?,?,?)")
    # Collision: numbered copy of an already-seeded pair -> deleted.
    conn.execute(ins, ("general", "complaint", "Toothache 46 when chewing",
                       "ألم في السن 46 عند المضغ", 0))
    # Update path: remove the seed row, leave only its numbered copy.
    conn.execute("DELETE FROM specialty_templates WHERE specialty='endodontics'"
                 " AND category='diagnosis' AND text_en='Cracked tooth'")
    conn.execute(ins, ("endodontics", "diagnosis", "Cracked tooth 11", "سن متشقق ١١", 0))
    # Custom row with a tooth number: never touched.
    conn.execute(ins, ("general", "complaint", "My custom tooth 46 note", "ملاحظة 46 خاصة", 1))
    conn.commit()
    tpl.ensure_tables(conn)  # hook: cleanup_specialty()
    rows = [dict(r) for r in conn.execute("SELECT * FROM specialty_templates")]
    pairs = [(r["text_en"], r["text_ar"]) for r in rows]
    assert ("Toothache when chewing", "ألم في السن عند المضغ") in pairs
    assert not any("46" in (r["text_en"] or "") and not r["is_custom"] for r in rows)
    assert ("Cracked tooth", "سن متشقق") in pairs  # updated in place
    custom = [r for r in rows if r["is_custom"]]
    assert custom and custom[0]["text_en"] == "My custom tooth 46 note"
    assert custom[0]["text_ar"] == "ملاحظة 46 خاصة"
    snap = sorted((r["specialty"], r["category"], r["text_en"], r["text_ar"], r["is_custom"]) for r in rows)
    tpl.ensure_tables(conn)  # second run: no-op
    rows2 = [dict(r) for r in conn.execute("SELECT * FROM specialty_templates")]
    assert sorted((r["specialty"], r["category"], r["text_en"], r["text_ar"], r["is_custom"]) for r in rows2) == snap
    conn.close()

def test_override_rekeyed_and_still_applies():
    tmp = Path("/tmp/r49_e/user_templates_test.json")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps({"overrides": [
        {"category": "complaint", "en": "Toothache 46 when chewing",
         "ar": "ألم في السن 46 عند المضغ", "new_en": "Edited ache note"},
        {"category": "complaint", "en": "Random user thing 46", "ar": "شيء 46"},
    ]}, ensure_ascii=False, indent=1), encoding="utf-8")
    old_tpl, old_tc = tpl.USER_TEMPLATES_FILE, tc.OVERRIDES_FILE
    tpl.USER_TEMPLATES_FILE = tmp; tc.OVERRIDES_FILE = tmp
    try:
        tpl.ensure_tables(_mem())  # hook: cleanup_overrides()
        ov = tpl.find_override("complaint", "Toothache when chewing", "ألم في السن عند المضغ")
        assert ov is not None and ov.get("new_en") == "Edited ache note"  # not orphaned
        assert tpl.find_override("complaint", "Toothache 46 when chewing",
                                 "ألم في السن 46 عند المضغ") is None
        other = tpl.find_override("complaint", "Random user thing 46", "شيء 46")
        assert other is not None  # non-seed key untouched
        pool = tpl.seed_templates("complaint", "en")
        assert any(r["en"] == "Edited ache note" for r in pool)  # edit still applies
        assert tc.cleanup_overrides() == 0  # idempotent
    finally:
        tpl.USER_TEMPLATES_FILE = old_tpl; tc.OVERRIDES_FILE = old_tc
        tmp.unlink(missing_ok=True)
