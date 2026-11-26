"""Round 49 (section E): tooth numbers out of built-in templates.

INVENTORY (r49, verified by scanning both seed files char by char):
phrases_seed.json and specialties.json contain NO digit characters
at all - no standalone FDI number (Latin or Arabic-Indic) exists in
any seed text, so NO seed text was changed and the literal OLD->NEW
maps below are legitimately EMPTY. The tooth numbers the owner saw
therefore live in rows already stored in existing clinic DBs (seeded
by older builds / typed once and auto-learned), cleaned below.

MIGRATION DESIGN (seed-derived, exact-match only): a stored row is
an old built-in ONLY when removing its standalone FDI tokens yields
EXACTLY a current seed text (phrases: same category; specialty
templates: same specialty+category pair, is_custom=0 rows only).
Anything else - user-typed / auto-learned phrases, custom templates
- is never touched, even if it contains a tooth number. UNIQUE
collisions delete the stale row instead of failing. Idempotent
(cleaned rows no longer match) and cheap (digit-free rows skipped).

OVERRIDES: user_templates.json overrides are keyed by the ORIGINAL
seed (category, en, ar) - specialty_templates.find_override. A key
that cleans to a current seed pair is rewritten to that pair
(new_en/new_ar/deleted kept), so a user's earlier edit of a seed
template is NOT orphaned; the store is plain JSON, so it is fully
possible. Hooks: phrases.seed_if_empty() and specialty_templates.
ensure_tables() call the cleanups below, exception-guarded there.
"""
import json, re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
PHRASES_SEED = DATA / "phrases_seed.json"
SPECIALTIES_SEED = DATA / "specialties.json"
OVERRIDES_FILE = DATA / "user_templates.json"

FDI = set(range(11, 19)) | set(range(21, 29)) | set(range(31, 39)) | set(range(41, 49)) \
    | set(range(51, 56)) | set(range(61, 66)) | set(range(71, 76)) | set(range(81, 86))
_DIGITS = "0-9\u0660-\u0669\u06f0-\u06f9"
_TO_LATIN = {}
for _i in range(10):
    _TO_LATIN[chr(0x660 + _i)] = str(_i)
    _TO_LATIN[chr(0x6F0 + _i)] = str(_i)
_TOKEN_RE = re.compile(r"(?<![%s])([%s]{2})(?![%s])" % (_DIGITS, _DIGITS, _DIGITS))
_ANY_DIGIT_RE = re.compile(r"[%s]" % _DIGITS)
_SPACE_PUNCT_RE = re.compile(r"\s+([.,;:!?\u060c\u061b\u061f])")
_WS_RE = re.compile(r"\s+")

# Literal OLD->NEW maps for seeds changed by r49: NONE (see docstring).
PHRASE_OLD_TO_NEW = {}
SPECIALTY_OLD_TO_NEW = {}

def _token_value(tok):
    return int("".join(_TO_LATIN.get(ch, ch) for ch in tok))

def clean_text(text):
    """`text` with every STANDALONE FDI tooth number removed (Latin,
    Arabic-Indic and Extended Arabic-Indic digits) and the spacing /
    punctuation tidied. Non-FDI numbers (years, doses, 'type 2') and
    numbers inside larger numbers are kept verbatim."""
    s = text or ""
    if not _ANY_DIGIT_RE.search(s):
        return s
    s = _TOKEN_RE.sub(lambda m: "" if _token_value(m.group(1)) in FDI else m.group(1), s)
    s = _SPACE_PUNCT_RE.sub(r"\1", s)
    return _WS_RE.sub(" ", s).strip(" -").strip()

def _phrase_seeds():
    """{category: {seed text, ...}} from phrases_seed.json ({} on error)."""
    try:
        data = json.loads(PHRASES_SEED.read_text(encoding="utf-8"))
        return {cat: {str(t).strip() for t in items} for cat, items in data.items()}
    except Exception:
        return {}

def _specialty_seeds():
    """({(specialty, category): {(en, ar), ...}}, {category: {(en, ar)}})."""
    by_sc, by_cat = {}, {}
    try:
        data = json.loads(SPECIALTIES_SEED.read_text(encoding="utf-8"))
        for sp in data.get("specialties", []):
            for cat, items in (sp.get("phrases") or {}).items():
                pair_set = by_sc.setdefault((sp.get("id", ""), cat), set())
                for ph in items:
                    pair = ((ph.get("en") or "").strip(), (ph.get("ar") or "").strip())
                    pair_set.add(pair)
                    by_cat.setdefault(cat, set()).add(pair)
    except Exception:
        pass
    return by_sc, by_cat

_CAT_NORM = {"symptom": "symptoms", "procedure": "procedures"}

def cleanup_phrases(conn=None):
    """Rewrite reusable_phrases rows that are old (numbered) built-in
    seeds to their cleaned seed text; delete on UNIQUE collision.
    Returns the number of rows changed. Never touches other rows."""
    seeds = _phrase_seeds()
    if not seeds:
        return 0
    own = conn is None
    if own:
        from src.models.database import get_connection
        conn = get_connection()
    changed = 0
    try:
        rows = [dict(r) for r in conn.execute("SELECT id, category, text FROM reusable_phrases")]
    except Exception:
        if own:
            conn.close()
        return 0
    for r in rows:
        text = r["text"] or ""
        if not _ANY_DIGIT_RE.search(text):
            continue
        cleaned = clean_text(text)
        if cleaned == text or cleaned not in seeds.get(r["category"], set()):
            continue
        clash = conn.execute("SELECT id FROM reusable_phrases WHERE category=? AND text=? AND id<>?",
                             (r["category"], cleaned, r["id"])).fetchone()
        if clash:
            conn.execute("DELETE FROM reusable_phrases WHERE id=?", (r["id"],))
        else:
            conn.execute("UPDATE reusable_phrases SET text=? WHERE id=?", (cleaned, r["id"]))
        changed += 1
    if changed:
        conn.commit()
    if own:
        conn.close()
    return changed

def cleanup_specialty(conn):
    """Same migration for specialty_templates seeded rows (is_custom=0
    only; custom rows untouched). Returns rows changed."""
    by_sc, _by_cat = _specialty_seeds()
    if not by_sc:
        return 0
    changed = 0
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, specialty, category, text_en, text_ar FROM specialty_templates WHERE is_custom=0")]
    except Exception:
        return 0
    for r in rows:
        en, ar = r["text_en"] or "", r["text_ar"] or ""
        if not (_ANY_DIGIT_RE.search(en) or _ANY_DIGIT_RE.search(ar)):
            continue
        pair = (clean_text(en), clean_text(ar))
        if pair == (en, ar) or pair not in by_sc.get((r["specialty"], r["category"]), set()):
            continue
        clash = conn.execute(
            "SELECT id FROM specialty_templates WHERE specialty=? AND category=? AND text_en=? AND text_ar=? AND id<>?",
            (r["specialty"], r["category"], pair[0], pair[1], r["id"])).fetchone()
        if clash:
            conn.execute("DELETE FROM specialty_templates WHERE id=?", (r["id"],))
        else:
            conn.execute("UPDATE specialty_templates SET text_en=?, text_ar=? WHERE id=?",
                         (pair[0], pair[1], r["id"]))
        changed += 1
    if changed:
        conn.commit()
    return changed

def cleanup_overrides(path=None):
    """Rewrite override KEYS (original seed en/ar) that clean to a
    current seed pair, keeping new_en/new_ar/deleted. Returns count."""
    path = Path(path) if path else OVERRIDES_FILE
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return 0
    if not _ANY_DIGIT_RE.search(raw):
        return 0  # cheap no-op: no numbered key can exist
    try:
        data = json.loads(raw)
        ovs = data.get("overrides", []) if isinstance(data, dict) else []
    except Exception:
        return 0
    _by_sc, by_cat = _specialty_seeds()
    out, seen, changed = [], set(), 0
    for o in ovs:
        if isinstance(o, dict):
            en, ar = o.get("en") or "", o.get("ar") or ""
            pair = (clean_text(en), clean_text(ar))
            cat = _CAT_NORM.get(o.get("category") or "", o.get("category") or "")
            if pair != (en, ar) and pair in by_cat.get(cat, set()):
                o = {**o, "en": pair[0], "ar": pair[1]}
                changed += 1
            key = (o.get("category"), o.get("en"), o.get("ar"))
            if key in seen:
                continue  # two old keys cleaned to one seed: keep first
            seen.add(key)
        out.append(o)
    if changed:
        path.write_text(json.dumps({"overrides": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    return changed

def run_all(conn=None):
    """All three cleanups; returns (phrases, specialty, overrides)."""
    return cleanup_phrases(conn), (cleanup_specialty(conn) if conn is not None else 0), cleanup_overrides()
