"""Settings - clinic name, paths, language. <200 lines.

Data location (Item 3, 2026-11-08): patient data NEVER lives next to
the EXE any more. Old builds stored clinic.db in anadoctorfady/ NEXT
TO the EXE, so copying/moving the EXE to the Desktop created a NEW
empty database there and all previous data "disappeared". Now the DB,
reports, backups, xrays and scans live in ONE fixed per-user location,
independent of where the EXE sits: Windows %APPDATA%\\ANADOCTORFADY,
Linux $XDG_CONFIG_HOME/ANADOCTORFADY or ~/.config/ANADOCTORFADY,
macOS ~/Library/Application Support/ANADOCTORFADY. The installer puts
the EXE in %LOCALAPPDATA%\\ANADOCTORFADY (a different folder) and
never touches the data folder, so reinstall/upgrade/uninstall can
never delete patient data. A one-time migration (migrate_legacy_data,
run at import) moves an old next-to-EXE database into the new location;
the old copy is only set aside AFTER the new copy is verified (same
size + SQLite header + integrity check) and is never deleted outright.
Test/dev override only: ANADOCTORFADY_DATA_DIR.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
APP_NAME = "ANADOCTORFADY"
SQLITE_HEADER = b"SQLite format 3\x00"
SUBDIRS = ("reports", "backups", "xrays", "scans")
def _exe_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return None
def _legacy_dir():
    # Old location (v2-final and earlier): anadoctorfady/ next to the EXE
    # when frozen, else next to the repo root. Kept only for migration.
    exe = _exe_dir()
    if exe is not None:
        return exe / "anadoctorfady"
    return Path(__file__).resolve().parent.parent.parent / "anadoctorfady"
def _legacy_candidates():
    # Where an old next-to-EXE database may be hiding. The EXE's own
    # folder first (the classic case), then the places owners most often
    # copied the EXE to: Desktop, Downloads, C:\\ANADOCTORFADY.
    seen, out = set(), []
    for cand in [_legacy_dir(), Path.home() / "Desktop" / "anadoctorfady",
                 Path.home() / "Downloads" / "anadoctorfady",
                 Path("C:/ANADOCTORFADY/anadoctorfady")]:
        if str(cand).lower() not in seen:
            seen.add(str(cand).lower()); out.append(cand)
    return out
def _data_dir():
    # Fixed per-user location, independent of where the EXE sits.
    override = os.environ.get("ANADOCTORFADY_DATA_DIR")
    if override:
        return Path(override).expanduser()
    appdata = os.environ.get("APPDATA")  # Windows Roaming profile
    if appdata:
        return Path(appdata) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / APP_NAME
def _is_valid_sqlite(path):
    p = Path(path)
    try:
        if not p.is_file() or p.stat().st_size < 100: return False
        with open(p, "rb") as f: return f.read(16) == SQLITE_HEADER
    except OSError:
        return False
def _verify_db(path):
    # Header + SQLite integrity check, read-only (never creates -wal).
    if not _is_valid_sqlite(path):
        return False
    try:
        conn = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
        try: row = conn.execute("PRAGMA integrity_check").fetchone(); return bool(row and row[0] == "ok")
        finally: conn.close()
    except Exception:
        return False
def _move_folder_files(src_dir, dst_dir):
    # Move every file; on a name collision keep the legacy file (never
    # overwrite existing data). Returns (moved, kept) file names.
    moved, kept = [], []
    if not src_dir.is_dir():
        return moved, kept
    dst_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(src_dir.iterdir()):
        if not item.is_file():
            continue
        if (dst_dir / item.name).exists():
            kept.append(item.name); continue
        try:
            shutil.move(str(item), str(dst_dir / item.name))
            moved.append(item.name)
        except OSError:
            kept.append(item.name)
    return moved, kept
def migrate_legacy_data(legacy_dir=None, data_dir=None):
    """One-time move of an old next-to-EXE database into the fixed
    per-user location. Returns a dict: migrated True/False + reason.
    The old clinic.db is renamed to clinic.db.migrated-<ts>.bak ONLY
    after the new copy passes size + header + integrity verification;
    it is never deleted, so nothing is lost if verification was wrong.
    Runs automatically once at import; safe to call again (no-op when
    the new database already exists or no legacy database is found)."""
    new = Path(data_dir) if data_dir else _data_dir()
    cands = [Path(legacy_dir)] if legacy_dir else _legacy_candidates()
    for legacy in cands:
        if legacy.resolve() == new.resolve():
            return {"migrated": False, "reason": "same_location"}
        old_db, new_db = legacy / "clinic.db", new / "clinic.db"
        if not old_db.exists():
            continue
        if not _is_valid_sqlite(old_db):
            if old_db.stat().st_size == 0:
                continue  # empty placeholder, not a database - keep looking
            return {"migrated": False, "reason": "legacy_db_invalid", "legacy_dir": str(legacy)}
        if new_db.exists():
            if _is_valid_sqlite(new_db):
                return {"migrated": False, "reason": "new_db_exists", "legacy_dir": str(legacy)}
            if new_db.stat().st_size > 0:
                return {"migrated": False, "reason": "new_db_invalid", "legacy_dir": str(legacy)}
            new_db.unlink()  # empty placeholder only - safe to replace
        for name in SUBDIRS: (new / name).mkdir(parents=True, exist_ok=True)
        try:  # checkpoint WAL so the plain file copy holds ALL data
            conn = sqlite3.connect(str(old_db))
            try: conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            finally: conn.close()
        except Exception:
            pass
        shutil.copy2(old_db, new_db)
        if new_db.stat().st_size != old_db.stat().st_size or not _verify_db(new_db):
            try: new_db.unlink()
            except OSError: pass
            return {"migrated": False, "reason": "verification_failed", "legacy_dir": str(legacy)}
        moved = {}
        for name in SUBDIRS:
            moved[name] = _move_folder_files(legacy / name, new / name)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kept_as = legacy / f"clinic.db.migrated-{stamp}.bak"
        try:
            old_db.rename(kept_as)
        except OSError:
            kept_as = None  # new copy is verified; old file stays put
        for suffix in ("-wal", "-shm"):  # stale sidecars, empty after checkpoint
            side = legacy / f"clinic.db{suffix}"
            try:
                if side.exists() and side.stat().st_size == 0:
                    side.unlink()
            except OSError:
                pass
        return {"migrated": True, "reason": "ok", "legacy_dir": str(legacy),
                "data_dir": str(new), "moved_files": moved,
                "legacy_kept_as": str(kept_as) if kept_as else None}
    return {"migrated": False, "reason": "no_legacy_db"}
DATA_DIR = _data_dir()
BASE = DATA_DIR  # compat: old code used BASE as the data root
REPORTS = DATA_DIR / "reports"
BACKUPS = DATA_DIR / "backups"
XRAYS = DATA_DIR / "xrays"
SCANS = DATA_DIR / "scans"
DB = DATA_DIR / "clinic.db"
for d in (REPORTS, BACKUPS, XRAYS, SCANS):
    d.mkdir(parents=True, exist_ok=True)
try:
    MIGRATION = migrate_legacy_data()
except Exception:
    MIGRATION = {"migrated": False, "reason": "error"}
CLINIC = "ANADOCTORFADY"
CLINIC_AR = "عيادة أنا دكتور فادي"
WHATSAPP = "+963944234456"
WA_URL = "https://wa.me/963944234456"
ABOUT_EN = ("This app is completely free and we ask Allah to make it "
    "ongoing charity for the developer Dr Fady Abdulkafy Dadoush and his "
    "parents, brothers, wife and children")
ABOUT_AR = ("هذا التطبيق مجاناً بالكامل و نسأل الله تعالى أن يكون صدقة "
    "جارية عن المطور د. فادي عبد الكافي دعدوش و عن والديه و إخوته و زوجته و أولاده")
DEFAULT_USER, DEFAULT_PASS = "fady", "1234"
def get_setting(key, default=None):
    from src.models.database import get_setting as _g
    return _g(key, default)
def set_setting(key, value):
    from src.models.database import set_setting as _s
    _s(key, value)
def get_theme_mode():
    return get_setting("theme_mode", "light") or "light"
def set_theme_mode(mode):
    set_setting("theme_mode", "dark" if mode == "dark" else "light")
def get_default_currency():
    from src.models.currency import CURRENCIES
    cur = get_setting("default_currency", "SYP") or "SYP"
    return cur if cur in CURRENCIES else "SYP"
def set_default_currency(cur):
    from src.models.currency import CURRENCIES
    set_setting("default_currency", cur if cur in CURRENCIES else "SYP")
