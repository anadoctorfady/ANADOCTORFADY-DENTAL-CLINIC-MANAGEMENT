"""Specialty templates: seeds (is_custom=0, specialties.json) merged with
custom rows (is_custom=1). Seeds are NEVER edited in place: edits/deletes
live as OVERRIDES in user_templates.json. Templates follow the doctor's
template_lang choice (R31: app|ar|en, default app). Round 21: hiding
REMOVED - a deleted seed is a tombstone override, shown nowhere."""
import json, re, sqlite3
from pathlib import Path
from src.models.database import get_setting, set_setting
from src.models.specialties import load_specialties, phrases_for
USER_TEMPLATES_FILE = Path(__file__).resolve().parent.parent / "data" / "user_templates.json"
def ensure_tables(conn):
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS specialty_templates(
        id INTEGER PRIMARY KEY AUTOINCREMENT, specialty TEXT, category TEXT,
        text_en TEXT, text_ar TEXT, is_custom INT DEFAULT 0,
        created_by TEXT DEFAULT '',
        UNIQUE(specialty, category, text_en, text_ar))""")
    c.execute("""CREATE TABLE IF NOT EXISTS custom_specialties(
        id TEXT PRIMARY KEY, name_en TEXT, name_ar TEXT)""")
    n = c.execute("SELECT COUNT(*) FROM specialty_templates").fetchone()[0]
    if n == 0:
        for sp in load_specialties():
            for cat, items in (sp.get("phrases") or {}).items():
                for ph in items:
                    c.execute("INSERT OR IGNORE INTO specialty_templates(specialty,category,text_en,text_ar,is_custom) VALUES(?,?,?,?,0)", (sp["id"], cat, ph.get("en", ""), ph.get("ar", "")))
    conn.commit()
    try:  # R49-E: strip tooth numbers from stored built-in seeds + override keys
        from src.models.template_cleanup import cleanup_specialty, cleanup_overrides; cleanup_specialty(conn); cleanup_overrides()
    except Exception: pass
def _rows(cur):
    return [dict(r) for r in cur.fetchall()]
def list_templates(conn, specialty=None, category=None):
    """Seeded + custom templates, optionally filtered. [dict]"""
    ensure_tables(conn)
    sql, args, conds = "SELECT * FROM specialty_templates", [], []
    if specialty: conds.append("specialty=?"); args.append(specialty)
    if category: conds.append("category=?"); args.append(category)
    if conds: sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY is_custom, specialty, category, id"
    return _rows(conn.cursor().execute(sql, args))
def add_template(conn, specialty, category, text_en, text_ar, created_by=""):
    """Add a custom phrase. Returns id, or None if text is empty."""
    text_en, text_ar = (text_en or "").strip(), (text_ar or "").strip()
    if not text_en and not text_ar: return None
    ensure_tables(conn)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO specialty_templates(specialty,category,text_en,text_ar,is_custom,created_by) VALUES(?,?,?,?,1,?)",
              (specialty, category, text_en, text_ar, created_by or ""))
    conn.commit()
    r = c.execute("SELECT id FROM specialty_templates WHERE specialty=? AND category=? AND text_en=? AND text_ar=?", (specialty, category, text_en, text_ar)).fetchone()
    return r["id"] if r else None
def update_template(conn, template_id, text_en=None, text_ar=None, category=None, specialty=None):
    """Edit a CUSTOM template only (seeded rows are protected). Returns bool."""
    ensure_tables(conn)
    row = conn.cursor().execute("SELECT * FROM specialty_templates WHERE id=?", (template_id,)).fetchone()
    if not row or not row["is_custom"]: return False
    sets, args = [], []
    for col, val in (("text_en", text_en), ("text_ar", text_ar),
                     ("category", category), ("specialty", specialty)):
        if val is not None: sets.append(f"{col}=?"); args.append(val)
    if not sets: return False
    args.append(template_id)
    conn.cursor().execute(f"UPDATE specialty_templates SET {', '.join(sets)} WHERE id=?", args)
    conn.commit()
    return True
def delete_template(conn, template_id):
    """Delete a CUSTOM template only (seeded rows are protected). Returns bool."""
    ensure_tables(conn)
    row = conn.cursor().execute("SELECT * FROM specialty_templates WHERE id=?", (template_id,)).fetchone()
    if not row or not row["is_custom"]: return False
    conn.cursor().execute("DELETE FROM specialty_templates WHERE id=?", (template_id,))
    conn.commit()
    return True
def _slug(name_en):
    return re.sub(r"[^a-z0-9]+", "_", (name_en or "").lower()).strip("_") or "custom"
def add_specialty(conn, name_en, name_ar):
    """Add a whole new custom specialty. Returns its slug id."""
    name_en, name_ar = (name_en or "").strip(), (name_ar or "").strip()
    if not name_en or not name_ar: return None
    ensure_tables(conn)
    slug, base, i = _slug(name_en), _slug(name_en), 2
    c = conn.cursor()
    while c.execute("SELECT 1 FROM custom_specialties WHERE id=?", (slug,)).fetchone():
        slug = f"{base}_{i}"; i += 1
    c.execute("INSERT INTO custom_specialties(id,name_en,name_ar) VALUES(?,?,?)", (slug, name_en, name_ar))
    conn.commit()
    return slug
def list_custom_specialties(conn):
    ensure_tables(conn)
    return _rows(conn.cursor().execute("SELECT * FROM custom_specialties ORDER BY name_en"))
def list_all_specialties(conn):
    """Built-in (is_custom=0) + custom (is_custom=1) specialties."""
    ensure_tables(conn)
    out = [{"id": s["id"], "name_en": s["name_en"], "name_ar": s["name_ar"], "is_custom": 0} for s in load_specialties()]
    out += [{**s, "is_custom": 1} for s in list_custom_specialties(conn)]
    return out
# --- Seed overrides in src/data/user_templates.json: {"overrides": [{"category",
# "en", "ar", "new_en"?, "new_ar"?, "deleted"?}]}; identity (category, en, ar).
def load_user_overrides():
    try:
        data = json.loads(USER_TEMPLATES_FILE.read_text(encoding="utf-8"))
        ovs = data.get("overrides", []) if isinstance(data, dict) else []
        return [o for o in ovs if isinstance(o, dict)]
    except Exception:
        return []
def _save_overrides(overrides):
    USER_TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True); USER_TEMPLATES_FILE.write_text(json.dumps({"overrides": overrides}, ensure_ascii=False, indent=1), encoding="utf-8")
def find_override(category, en, ar):
    return next((o for o in load_user_overrides() if (o.get("category"), o.get("en"), o.get("ar")) == (category, en, ar)), None)
def _is_deleted(ov):  # Round 21 `deleted` and legacy `hidden` both tombstone.
    return bool(ov and (ov.get("deleted") or ov.get("hidden")))
def set_seed_override(category, en, ar, new_en=None, new_ar=None, hidden=None, deleted=None):
    """Upsert a seed override: new_en/new_ar replace that side only (None
    keeps the current side); deleted=True tombstones (`hidden` = legacy
    alias). A no-op (no change, not deleted) removes the override."""
    if hidden is not None: deleted = hidden
    cur = find_override(category, en, ar) or {}
    ovs = [o for o in load_user_overrides() if (o.get("category"), o.get("en"), o.get("ar")) != (category, en, ar)]
    rec = {"category": category, "en": en or "", "ar": ar or ""}
    for key, val, seed in (("new_en", new_en, en), ("new_ar", new_ar, ar)):
        v = (val or "").strip() if val is not None else (cur.get(key) or "")
        if v and v != (seed or ""): rec[key] = v
    if deleted or (deleted is None and _is_deleted(cur)): rec["deleted"] = True
    if len(rec) == 3:
        _save_overrides(ovs)
        return None
    ovs.append(rec)
    _save_overrides(ovs)
    return rec
def delete_seed(category, en, ar):  # Round 21: tombstone a built-in seed.
    return set_seed_override(category, en, ar, deleted=True)
def clear_seed_override(category, en, ar):
    """Drop the override: the seed shows its original text again."""
    ovs = load_user_overrides()
    kept = [o for o in ovs if (o.get("category"), o.get("en"), o.get("ar")) != (category, en, ar)]
    if len(kept) == len(ovs): return False
    _save_overrides(kept); return True
def restore_builtin_templates(category):
    """Round 21: clear ALL overrides (edits + tombstones) for one category,
    restoring its built-ins to factory state. Returns the count cleared."""
    ovs = load_user_overrides()
    kept = [o for o in ovs if o.get("category") != category]
    if len(kept) == len(ovs): return 0
    _save_overrides(kept); return len(ovs) - len(kept)
# Round 31 (item 5): persisted setting template_lang = "app"
# (default, = round-17 behaviour) | "ar" | "en"; legacy "auto" = "app".
def template_lang_mode():
    raw = (get_setting("template_lang", "app") or "app").strip().lower()
    return raw if raw in ("ar", "en") else "app"
def set_template_lang_mode(mode):
    set_setting("template_lang", mode if mode in ("ar", "en") else "app")
def effective_template_lang(app_lang=None):
    """THE central resolver: mode ar/en wins; mode app = app language."""
    mode = template_lang_mode()
    if mode in ("ar", "en"): return mode
    app = app_lang or get_setting("language", "en") or "en"
    return "ar" if app == "ar" else "en"
def resolve_template_lang(app_lang=None):  # compat alias (R17 name)
    return effective_template_lang(app_lang)
def _one(en, ar, lang):
    from src.models.phrases import single_language_text, template_display_text
    side = ((en if lang == "en" else ar) or (ar if lang == "en" else en) or "").strip()
    return template_display_text(single_language_text(side, lang) if " / " in side else side, lang)  # R18: caps after lang selection
def seed_templates(category, lang="en", include_hidden=False):
    """Seed pool after overrides (edits applied, tombstoned dropped). `include_hidden` legacy/ignored (R21)."""
    ovs = {(o.get("category"), o.get("en"), o.get("ar")): o for o in load_user_overrides()}
    out, seen = [], set()
    for sp in load_specialties():
        for en, ar in phrases_for(sp.get("id", ""), category):
            key = (en.strip().lower(), ar.strip())
            if key in seen or not (en or ar): continue
            seen.add(key)
            o = ovs.get((category, en, ar))
            if _is_deleted(o): continue
            eff_en, eff_ar = (o or {}).get("new_en") or en, (o or {}).get("new_ar") or ar
            out.append({"specialty": sp.get("id", ""), "category": category, "en": eff_en, "ar": eff_ar, "text": _one(eff_en, eff_ar, lang), "is_custom": False, "seed_en": en, "seed_ar": ar, "edited": bool(o and (o.get("new_en") or o.get("new_ar"))), "hidden": False, "deleted": False})
    return out
def effective_pool(conn, category, lang=None, include_hidden=False):
    """Seed pool (overrides applied) + custom DB rows, one language, deduped. `include_hidden` legacy/ignored (R21)."""
    lang = lang or resolve_template_lang()
    out, seen = [], set()
    for r in seed_templates(category, lang):
        if r["text"] and r["text"].lower() not in seen:
            seen.add(r["text"].lower()); out.append(r)
    try:
        rows = list_templates(conn, category={"symptom": "symptoms", "procedure": "procedures"}.get(category, category))
    except Exception:
        rows = []
    for r in rows:
        if not r.get("is_custom"): continue  # seeds already came from seed_templates()
        txt = _one(r.get("text_en") or "", r.get("text_ar") or "", lang)
        if txt and txt.lower() not in seen:
            seen.add(txt.lower())
            out.append({"specialty": r.get("specialty") or "general", "category": r.get("category") or category,
                        "en": r.get("text_en") or "", "ar": r.get("text_ar") or "", "text": txt, "is_custom": True,
                        "edited": False, "hidden": False, "deleted": False, "id": r.get("id")})
    return out
