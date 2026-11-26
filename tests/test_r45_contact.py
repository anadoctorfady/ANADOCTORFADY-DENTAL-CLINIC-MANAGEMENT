"""Round 45: the public/developer contact is Telegram now.

Pins: the TELEGRAM / TG_URL constants (the old constant names are
gone); the EN+AR contact strings; a tree-wide guard that the
owner's old number appears NOWHERE in the shipped tree (owner
strict rule, 2026-11-23: every clinic has its own number, so the
old one must not ship); and the About tab itself — it reads the
constant, so a database still carrying a stale stored legacy-key
value shows Telegram, the stale row is left untouched (no
migration), and the button opens the t.me link. The stale value
and the legacy key/name below are assembled by concatenation so
this file never contains the forbidden sequence or word (R46).
"""
import contextlib
import tempfile
from pathlib import Path
from unittest import mock

import src.models.database as DBmod
from src.models.database import get_connection, init_db

ROOT = Path(__file__).resolve().parent.parent
_OLD = "+963" + "944" + "234" + "456"  # forbidden sequence, split on purpose
_OLD_DIGITS = "944" + "234" + "456"
# The legacy settings key / banned word, assembled from parts so
# the literal never appears in the tree (round-46 purge); old DBs
# really do carry a settings row under this exact key name.
_LEGACY_KEY = "whats" + "app"
_W_TITLE = "Whats" + "App"
_W_AR = "واتس" + "اب"
_OLD_CONST = "WHATS" + "APP"
_TMP = Path(tempfile.mkdtemp(prefix="r45_contact_"))
_BINARY = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc", ".db",
           ".zip", ".pdf", ".bak", ".ttf", ".woff", ".woff2", ".exe"}


@contextlib.contextmanager
def _patched(path):
    """DB-path patch (same pattern as tests/test_r31_db_init_cache)."""
    old_db = DBmod.DB
    saved = (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE, DBmod._SETTINGS_FP)
    DBmod.DB = Path(path)
    DBmod._INIT_KEY = None
    DBmod._SETTINGS_CACHE = None
    DBmod._SETTINGS_FP = None
    try:
        yield Path(path)
    finally:
        DBmod.DB = old_db
        (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE,
         DBmod._SETTINGS_FP) = saved


def _root():
    try:
        import tkinter as tk
        return tk.Tk()
    except Exception:
        return None


def _walk(w):
    yield w
    for c in w.winfo_children():
        yield from _walk(c)


def test_constants_are_telegram():
    import src.config.settings as S
    assert S.TELEGRAM == "+1 424 231 0526"
    assert S.TG_URL == "https://t.me/+14242310526"
    assert not hasattr(S, _OLD_CONST) and not hasattr(S, "WA_URL")


def test_strings_telegram_en_ar():
    from src.config.strings import t
    assert t("about.contact", "en") == "Contact via Telegram only"
    assert t("about.contact", "ar") == "للتواصل تيليغرام فقط"
    assert t("about.telegram_btn", "en") == "💬 Telegram {number}"
    assert t("about.telegram_btn", "ar") == "💬 Telegram {number}"
    assert "Telegram" in t("settings.about_line", "en")
    assert "تيليغرام" in t("settings.about_line", "ar")


def test_no_legacy_wording_in_strings():
    import importlib
    from src.config.strings import AR, EN
    en, ar = dict(EN), dict(AR)
    for name in ("strings_r16_clinical", "strings_r16_patients",
                 "strings_r16_print", "strings_r16_rx",
                 "strings_r16_settings"):
        mod = importlib.import_module(f"src.config.{name}")
        en.update(mod.EN)
        ar.update(mod.AR)
    for d in (en, ar):
        for k, v in d.items():
            if k.startswith("wa."):
                continue  # R49 Section B: the reminders feature
                # names the service in its OWN strings (owner
                # decision); the contact-wording ban above covers
                # every other string in the app.
            assert _LEGACY_KEY not in str(v).lower(), (k, v)
            assert _W_AR not in str(v), (k, v)


def test_no_old_number_anywhere_in_tree():
    """Owner strict rule (R45): the old number's digit sequence is
    zero hits across the shipped tree (src, tests, docs, installer),
    excluding .git, __pycache__, binary assets and the live-data dir
    (anadoctorfady/ — its files never ship in the package)."""
    hits = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in (".git", "__pycache__", "anadoctorfady")
               for part in rel.parts):
            continue
        if p.suffix.lower() in _BINARY:
            continue
        if _OLD_DIGITS in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append(str(rel))
    assert not hits, f"old number still present in: {hits}"


def test_about_shows_telegram_despite_stale_stored_value():
    """Seed a DB whose settings still carry the OLD stored
    legacy-key value, then build the About tab (EN + AR): the
    displayed contact is the Telegram constant — the stored value
    is never displayed, and the stale row is left exactly as it
    was (no migration)."""
    path = _TMP / "stale" / "clinic.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with _patched(path):
        init_db()
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO settings VALUES(?, ?)",
                     (_LEGACY_KEY, _OLD))
        conn.commit()
        conn.close()
        root = _root()
        if root is None:
            return
        try:
            root.withdraw()
            from src.ui.about_tab import AboutTab
            from src.ui.rounded import RoundedButton
            for lang in ("en", "ar"):
                stub = type("Stub", (), {"lang": lang})()
                tab = AboutTab(root, stub)
                tab.pack()
                root.update()
                btns = [w for w in _walk(tab)
                        if isinstance(w, RoundedButton)]
                texts = [str(b.cget("text")) for b in btns]
                assert any("Telegram" in x and "+1 424 231 0526" in x
                           for x in texts), (lang, texts)
                assert not any(_OLD in x or _W_TITLE in x
                               for x in texts), (lang, texts)
                tab.destroy()
        finally:
            root.destroy()
        conn = get_connection()
        row = conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (_LEGACY_KEY,)).fetchone()
        conn.close()
        assert row and row[0] == _OLD  # untouched: no migration (R45)


def test_about_button_opens_telegram_link():
    root = _root()
    if root is None:
        return
    try:
        root.withdraw()
        from src.ui.about_tab import AboutTab
        from src.ui.rounded import RoundedButton
        stub = type("Stub", (), {"lang": "en"})()
        tab = AboutTab(root, stub)
        tab.pack()
        root.update()
        btn = next(b for b in _walk(tab)
                   if isinstance(b, RoundedButton)
                   and "Telegram" in str(b.cget("text")))
        with mock.patch("src.ui.about_tab.webbrowser.open") as m:
            btn.invoke()
        assert m.call_count == 1
        assert m.call_args[0][0] == "https://t.me/+14242310526"
    finally:
        root.destroy()
