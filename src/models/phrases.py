"""Reusable phrases memory: auto-learns what the doctor wrote before.
Categories: complaint, symptom, diagnosis, procedure, service, note,
disease, referral (round 19: disease + referral merge-seeded like note).
Seeded on first use from src/data/phrases_seed.json. The seed file
holds each phrase ONCE per language (an EN block + an AR block per
category, never an 'EN / AR' pair in one string); round 17 language
purity is enforced at read time by single_language_text() /
search_phrases(lang=...): the picker only ever shows and inserts
text in the app language. Round 18: template_display_text() is the
display/insert transform AFTER language selection - EN templates
are shown + inserted in ALL CAPS, AR (no case) passes unchanged;
stored text is NEVER rewritten. The 'note' category is merge-seeded
on every seed_if_empty() so existing installs receive new note
phrases too (the table is never empty again after first install)."""
import json, re
from datetime import datetime
from pathlib import Path
from src.models.database import get_connection
CATEGORIES = ("complaint", "symptom", "diagnosis", "procedure", "service", "note", "disease", "referral", "allergy")
SEED = Path(__file__).resolve().parent.parent / "data" / "phrases_seed.json"
_AR_RE = re.compile(r"[\u0600-\u06FF]")
_LA_RE = re.compile(r"[A-Za-z]")
_AR_STRIP = re.compile(r"[\u0640\u064B-\u0652\u0670]")
_AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ئ": "ء", "ؤ": "ء"})
def normalize_search_text(text):
    """Round 21 search normalizer (shared): strip Arabic diacritics/tatweel, fold hamza/ة/ى variants, lower Latin."""
    return _AR_STRIP.sub("", text or "").translate(_AR_MAP).lower().strip()
def search_text_matches(candidate, query):
    q = normalize_search_text(query)
    return not q or q in normalize_search_text(candidate)
def _latin_words(text):
    """Latin words that are real wording (short all-caps acronyms like
    CBCT count as data, not wording)."""
    return [w for w in re.findall(r"[A-Za-z]+", text or "")
            if not (len(w) <= 4 and w.isupper())]
def single_language_text(text, lang):
    """`text` reduced to ONE language ('en'/'ar'), or '' when it is
    purely the other language. A stored bilingual pair 'EN / AR'
    (legacy rows, pasted text) is SPLIT and only the `lang` side is
    returned; neutral text (digits/symbols only) passes in both."""
    s = (text or "").strip()
    if not s:
        return ""
    if " / " in s:
        parts = [p.strip() for p in s.split(" / ") if p.strip()]
        if len(parts) > 1 and any(_AR_RE.search(p) for p in parts) \
                and any(_LA_RE.search(p) for p in parts):
            for p in parts:
                if lang == "ar" and _AR_RE.search(p):
                    return p
                if lang == "en" and not _AR_RE.search(p) and _LA_RE.search(p):
                    return p
    has_ar, has_la = bool(_AR_RE.search(s)), bool(_LA_RE.search(s))
    if not has_ar and not has_la:
        return s  # neutral: numbers / symbols only
    if lang == "ar":
        return s if has_ar and not _latin_words(s) else ""
    return s if not has_ar else ""
def template_display_text(text, lang):
    """Round 18 display/insert transform, applied ONLY after the
    single-language selection: EN -> ALL CAPS (owner rule: every
    English ready-made template/phrase is displayed and inserted in
    capital letters); AR has no case and passes through unchanged,
    as does any other lang. Storage always keeps the original case."""
    s = text or ""
    return s.upper() if lang == "en" else s
def _now():
    return datetime.now().isoformat(timespec="seconds")
def ensure_tables():
    conn = get_connection(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS reusable_phrases(
        id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, text TEXT,
        usage_count INT DEFAULT 1, last_used TEXT, is_favorite INT DEFAULT 0,
        specialty TEXT DEFAULT 'general',
        UNIQUE(category, text))""")
    try:
        c.execute("ALTER TABLE reusable_phrases ADD COLUMN specialty TEXT DEFAULT 'general'")
    except Exception:
        pass  # already exists
    c.execute("CREATE INDEX IF NOT EXISTS idx_phr_cat ON reusable_phrases(category, usage_count DESC)")
    c.execute("""CREATE TABLE IF NOT EXISTS clipboard_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, copied_at TEXT)""")
    conn.commit(); conn.close()
def _merge_category_seeds(c, category):
    """Idempotent merge-seed for ONE category: inserts any seed
    phrases missing from an ALREADY-seeded DB (INSERT OR IGNORE on
    UNIQUE(category,text)); runs on every seed_if_empty() so existing
    installs receive new phrases for merge-seeded categories."""
    try:
        data = json.loads(SEED.read_text(encoding="utf-8"))
    except Exception:
        return 0
    added = 0
    for t in data.get(category, []):
        t = str(t).strip()
        if len(t) >= 3:
            c.execute("INSERT OR IGNORE INTO reusable_phrases(category,text,usage_count,last_used) VALUES(?,?,1,?)", (category, t, _now()))
            added += c.rowcount if c.rowcount and c.rowcount > 0 else 0
    return added
def _merge_note_seeds(c):
    """Idempotent merge-seed for category 'note' ONLY (round 18):
    kept as a named wrapper over _merge_category_seeds(). Round 19
    extends the same pattern to 'disease' + 'referral' (see
    seed_if_empty). Other categories keep seed-when-empty."""
    return _merge_category_seeds(c, "note")
def seed_if_empty():
    ensure_tables()
    try:  # R49-E: strip tooth numbers from stored built-in seeds (never breaks seeding)
        from src.models.template_cleanup import cleanup_phrases; cleanup_phrases()
    except Exception: pass
    conn = get_connection(); c = conn.cursor()
    n = c.execute("SELECT COUNT(*) FROM reusable_phrases").fetchone()[0]
    if n:
        _merge_note_seeds(c); _merge_category_seeds(c, "disease"); _merge_category_seeds(c, "referral"); _merge_category_seeds(c, "allergy"); conn.commit()
        n = c.execute("SELECT COUNT(*) FROM reusable_phrases").fetchone()[0]
        conn.close(); return n
    try:
        data = json.loads(SEED.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    total = 0
    for cat, items in data.items():
        for t in items:
            t = str(t).strip()
            if len(t) >= 3:
                c.execute("INSERT OR IGNORE INTO reusable_phrases(category,text,usage_count,last_used) VALUES(?,?,1,?)", (cat, t, _now())); total += 1
    conn.commit(); conn.close(); return total
def save_phrase(category, text, specialty="general"):
    """Auto-learn: dedupe, bump usage_count if seen before. Returns id or None.
    specialty tags the phrase (default 'general'); the UNIQUE(category,text)
    key keeps one row per text, so a re-save keeps the first specialty."""
    text = (text or "").strip()
    if len(text) < 3 or category not in CATEGORIES:
        return None
    seed_if_empty()
    conn = get_connection(); c = conn.cursor()
    c.execute("""INSERT INTO reusable_phrases(category,text,usage_count,last_used,specialty)
        VALUES(?,?,1,?,?) ON CONFLICT(category,text) DO UPDATE SET
        usage_count=usage_count+1, last_used=excluded.last_used""", (category, text, _now(), specialty or "general"))
    conn.commit()
    r = c.execute("SELECT id FROM reusable_phrases WHERE category=? AND text=?", (category, text)).fetchone()
    conn.close(); return r["id"] if r else None
def _rows(cur):
    return [dict(r) for r in cur.fetchall()]
def search_phrases(category, query="", limit=20, specialty=None, lang=None):
    """Search reusable phrases; specialty=None means no specialty filter.
    lang='en'/'ar' (round 17): every returned row's text is reduced to
    that ONE language via single_language_text() and other-language
    rows are dropped, so the picker can never show or insert the other
    language. lang=None keeps the legacy unfiltered behaviour."""
    seed_if_empty()
    conn = get_connection(); c = conn.cursor()
    q = (query or "").strip()
    ar_q = bool(q and _AR_RE.search(q))  # R21: SQL LIKE misses hamza-less Arabic; filter in Python instead
    sql = "SELECT * FROM reusable_phrases WHERE category=?"
    args = [category]
    if specialty:
        sql += " AND specialty=?"; args.append(specialty)
    if q and not ar_q:
        sql += " AND text LIKE ?"; args.append(f"%{q}%")
    sql += " ORDER BY is_favorite DESC, usage_count DESC, last_used DESC LIMIT ?"
    args.append(500 if ar_q else (limit * 10 if lang else limit))  # headroom for lang/normalized filtering
    try:
        c.execute(sql, args)
    except Exception:  # very old DB without the specialty column
        sql = "SELECT * FROM reusable_phrases WHERE category=?"
        args = [category]
        if q and not ar_q:
            sql += " AND text LIKE ?"; args.append(f"%{q}%")
        sql += " ORDER BY is_favorite DESC, usage_count DESC, last_used DESC LIMIT ?"
        args.append(500 if ar_q else (limit * 10 if lang else limit))
        c.execute(sql, args)
    rows = _rows(c); conn.close()
    if lang:
        out = []
        for r in rows:
            # Language selection FIRST, caps transform AFTER (round 18).
            r["text"] = template_display_text(single_language_text(r["text"], lang), lang)
            if r["text"]:
                out.append(r)
        rows = [r for r in out if search_text_matches(r["text"], q)][:limit] if ar_q else out[:limit]
    elif ar_q:
        rows = [r for r in rows if search_text_matches(r["text"], q)][:limit]
    return rows
def list_top(category, limit=10, specialty=None, lang=None):
    return search_phrases(category, "", limit, specialty, lang=lang)
def delete_phrase(pid):
    conn = get_connection(); c = conn.cursor(); c.execute("DELETE FROM reusable_phrases WHERE id=?", (pid,)); conn.commit(); conn.close()
def toggle_favorite(pid):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE reusable_phrases SET is_favorite=CASE WHEN is_favorite=1 THEN 0 ELSE 1 END WHERE id=?", (pid,)); conn.commit(); conn.close()
def get_categories():
    return list(CATEGORIES)
def count_phrases():
    seed_if_empty()
    conn = get_connection(); c = conn.cursor(); n = c.execute("SELECT COUNT(*) FROM reusable_phrases").fetchone()[0]; conn.close(); return n
