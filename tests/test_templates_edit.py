"""Job 2 (2026-11-09): editable, single-language templates (model).
Seed edits/deletes live as overrides in user_templates.json (the seed
file is never touched; round 21: delete = tombstone, hiding removed);
the picker/manager show ONE language only. DB work runs on an isolated
temp copy (never the live DB); overrides go to a temp JSON file."""
import contextlib, hashlib, importlib, json, os, sqlite3, tempfile
from pathlib import Path
from src.models import specialty_templates as tpl
from src.models.database import get_connection, get_setting, set_setting
import src.models.database as DBmod
import src.models.backup_validate as BV
from src.models.database import init_db
from src.ui.phrase_picker import combined_templates

ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = ROOT / "src" / "data" / "specialties.json"
CATS = ("complaint", "symptom", "diagnosis", "procedure")
_TMP = Path(tempfile.mkdtemp(prefix="templates_edit_"))
SEED_EN, SEED_AR = "Toothache when chewing", "ألم في السن عند المضغ"

@contextlib.contextmanager
def isolated_db():
    db_path = _TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        q = Path(str(db_path) + suf)
        if q.exists(): q.unlink()
    old_db, old_bv = DBmod.DB, BV.DB
    DBmod.DB, BV.DB = db_path, db_path
    try:
        init_db(); yield
    finally:
        DBmod.DB, BV.DB = old_db, old_bv

@contextlib.contextmanager
def tmp_overrides():
    fd, path = tempfile.mkstemp(suffix=".json", prefix="user_templates_")
    os.close(fd)
    Path(path).write_text('{"overrides": []}', encoding="utf-8")
    old = tpl.USER_TEMPLATES_FILE
    tpl.USER_TEMPLATES_FILE = Path(path)
    try:
        yield Path(path)
    finally:
        tpl.USER_TEMPLATES_FILE = old
        try: Path(path).unlink()
        except OSError: pass

def _md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()

def test_seed_override_persists_across_restart():
    before = _md5(SEED_FILE)
    with tmp_overrides() as tmp:
        rec = tpl.set_seed_override("complaint", SEED_EN, SEED_AR, new_en="TEST_OVERRIDE_EN_XYZ")
        assert rec and rec.get("new_en") == "TEST_OVERRIDE_EN_XYZ"
        assert _md5(SEED_FILE) == before  # seed file never edited in place
        assert any(o.get("new_en") == "TEST_OVERRIDE_EN_XYZ"
                   for o in json.loads(tmp.read_text(encoding="utf-8"))["overrides"])
        import src.models.specialty_templates as tpl2
        importlib.reload(tpl2)
        tpl2.USER_TEMPLATES_FILE = tmp
        rows = tpl2.seed_templates("complaint", "en")
        assert any(r["text"] == "TEST_OVERRIDE_EN_XYZ" and r["edited"] for r in rows)
        assert not any(r["text"] == SEED_EN.upper() for r in rows)
        assert tpl2.clear_seed_override("complaint", SEED_EN, SEED_AR) is True
        assert any(r["text"] == SEED_EN.upper() for r in tpl2.seed_templates("complaint", "en"))
        assert _md5(SEED_FILE) == before

def test_delete_seed_and_restore_builtins():
    # Round 21 supersedes the old hide spec: Delete tombstones a seed
    # (deleted=true); there is no Show hidden anywhere, the legacy
    # include_hidden flag is ignored, a legacy hidden=true override
    # counts as deleted, and Restore built-in templates (category
    # level) brings the seed back. clear_seed_override still works.
    with tmp_overrides(), isolated_db():
        conn = get_connection()
        try:
            assert any(r["text"] == SEED_EN.upper() for r in tpl.effective_pool(conn, "complaint", "en"))
            rec = tpl.delete_seed("complaint", SEED_EN, SEED_AR)
            assert rec and rec.get("deleted") is True
            assert not any(r["text"] == SEED_EN.upper() for r in tpl.effective_pool(conn, "complaint", "en"))
            assert not any(r["text"] == SEED_EN.upper() for r in tpl.seed_templates("complaint", "en"))
            # Legacy flag: even include_hidden=True never resurrects it.
            assert not any(r["text"] == SEED_EN.upper() for r in tpl.effective_pool(conn, "complaint", "en", include_hidden=True))
            assert tpl.restore_builtin_templates("complaint") == 1
            assert any(r["text"] == SEED_EN.upper() for r in tpl.effective_pool(conn, "complaint", "en"))
            # Legacy hidden=true override = deleted too.
            tpl.set_seed_override("complaint", SEED_EN, SEED_AR, hidden=True)
            assert not any(r["text"] == SEED_EN.upper() for r in tpl.effective_pool(conn, "complaint", "en"))
        finally:
            conn.close()
        assert tpl.clear_seed_override("complaint", SEED_EN, SEED_AR) is True
        conn = get_connection()
        try:
            assert any(r["text"] == SEED_EN.upper() for r in tpl.effective_pool(conn, "complaint", "en"))
            assert tpl.restore_builtin_templates("complaint") == 0  # nothing left to restore
        finally:
            conn.close()

def test_single_language_display():
    with tmp_overrides(), isolated_db():
        conn = get_connection()
        try:
            for lang in ("en", "ar"):
                for cat in CATS:
                    rows = tpl.effective_pool(conn, cat, lang)
                    assert rows, (cat, lang)
                    for r in rows:
                        shown = r["en"] if lang == "en" else r["ar"]
                        other = r["ar"] if lang == "en" else r["en"]
                        exp = shown or other
                        if lang == "en":
                            exp = exp.upper()  # round 18: EN templates display ALL CAPS
                        assert r["text"] == exp  # exactly one side
                        assert " — " not in r["text"]
        finally:
            conn.close()
        for lang in ("en", "ar"):
            for cat in CATS:
                for r in combined_templates(cat, "", lang=lang):
                    assert " — " not in r["display"], (cat, lang, r["display"])

def test_template_lang_setting_choice_r31():
    # Round 31 item 5 supersedes round 17: the persisted
    # 'template_lang' setting (app|ar|en, default app) CHOOSES the
    # template language; mode "app" reproduces round 17 exactly and
    # legacy/junk values ("auto", "", "bogus") read as "app".
    with tmp_overrides(), isolated_db():
        prev_lang, prev_tpl = get_setting("language", "en"), get_setting("template_lang", "app")
        try:
            conn = get_connection()
            try:
                set_setting("language", "en")
                set_setting("template_lang", "ar")
                assert tpl.resolve_template_lang() == "ar"
                rows = tpl.effective_pool(conn, "complaint")
                assert any(r["text"] == SEED_AR for r in rows)
                assert not any(r["text"] == SEED_EN.upper() for r in rows)
                set_setting("language", "ar")
                set_setting("template_lang", "en")
                assert tpl.resolve_template_lang() == "en"
                rows = tpl.effective_pool(conn, "complaint")
                assert any(r["text"] == SEED_EN.upper() for r in rows)
                assert not any(r["text"] == SEED_AR for r in rows)
                set_setting("template_lang", "")
                assert tpl.resolve_template_lang() == "ar"
                set_setting("template_lang", "bogus")
                assert tpl.resolve_template_lang() == "ar"
                set_setting("template_lang", "app")
                set_setting("language", "en")
                assert tpl.resolve_template_lang() == "en"
            finally:
                conn.close()
        finally:
            set_setting("language", prev_lang if prev_lang is not None else "en")
            set_setting("template_lang", prev_tpl if prev_tpl is not None else "app")

def test_custom_template_delete_outright():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    tpl.ensure_tables(conn)
    tid = tpl.add_template(conn, "general", "complaint", "TEST_CUSTOM_DEL_XYZ", "اختبار حذف", created_by="fady")
    assert tid
    assert tpl.delete_template(conn, tid) is True
    assert not [r for r in tpl.list_templates(conn, category="complaint") if r["id"] == tid]
    conn.close()
