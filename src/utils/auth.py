"""Auth: SHA256, default fady/1234. <200 lines.
Round 17: (ok, message) results are SINGLE-language — every producer
takes lang=None, which resolves to the app language ('language'
setting), so callers that pass no lang still show one language."""
import hashlib
from datetime import datetime
from src.models.database import get_connection
_CURRENT = {"username": None, "role": "doctor"}
def _lang(lang):
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"
def _m(en, ar, lang):
    return ar if _lang(lang) == "ar" else en
def get_user_role(username):
    """Role from users table ('admin'/'doctor'/'nurse'); 'doctor' fallback."""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username=?", (username or "",))
        row = cur.fetchone(); conn.close()
        return (row["role"] or "doctor") if row and row["role"] else "doctor"
    except Exception:
        return "doctor"
def list_doctors():
    """Usernames who can be the treating doctor: role doctor or admin
    (the admin is usually a treating doctor too). Nurses excluded."""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE role IN ('doctor','admin') ORDER BY username")
        rows = [r["username"] for r in cur.fetchall()]; conn.close()
        return rows or ["fady"]
    except Exception:
        return ["fady"]
def set_current_user(username, role=None):
    """Remember who is logged in (username + role) for the session."""
    _CURRENT["username"] = username
    _CURRENT["role"] = role or get_user_role(username)
    return _CURRENT["role"]
def get_current_user():
    return _CURRENT["username"]
def get_current_role():
    return _CURRENT["role"] or "doctor"
def hash_pw(pw):
    return hashlib.sha256(str(pw).encode("utf-8")).hexdigest()
def verify(username, password):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username=?",
                (username.strip(),))
    row = cur.fetchone(); conn.close()
    return bool(row and row["password_hash"] == hash_pw(password))
def get_last_login(username):
    """Previous last_login timestamp for `username` (ISO), or None when
    the user never logged in on this device. Never raises."""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT last_login FROM users WHERE username=?", (username.strip(),))
        row = cur.fetchone(); conn.close()
        return row["last_login"] if row else None
    except Exception:
        return None
def record_login(username):
    """On successful login (Job 6): store now in users.last_login and
    return the PREVIOUS value (None = first login on this device).
    Local DB only, per device. Never raises, never blocks login."""
    prev = get_last_login(username)
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("UPDATE users SET last_login=? WHERE username=?",
                    (datetime.now().isoformat(timespec="seconds"), username.strip()))
        conn.commit(); conn.close()
    except Exception:
        pass
    return prev
def get_all_last_logins():
    """[(username, last_login)] for users who logged in on THIS device,
    most recent first. Local DB only, so the list is per-device by
    construction. Users with NULL last_login (never logged in on this
    device) are OMITTED: the list is "last login on this device", and a
    'never' row per never-logged-in user would only add noise. Never
    raises; [] on any error."""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT username, last_login FROM users"
                    " WHERE last_login IS NOT NULL"
                    " ORDER BY last_login DESC, username")
        rows = [(r["username"], r["last_login"]) for r in cur.fetchall()]
        conn.close(); return rows
    except Exception:
        return []
def valid_username(name):
    """Username rule: 3-32 chars, no spaces or '/' (it appears in URLs)."""
    n = name or ""
    return 3 <= len(n) <= 32 and not any(c.isspace() or c == "/" for c in n)
def list_users():
    """All local users: [(username, role)]. Center is server-side only."""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT username, role FROM users ORDER BY username")
        rows = [(r["username"], r["role"] or "doctor") for r in cur.fetchall()]
        conn.close(); return rows
    except Exception:
        return []
def create_user(current_role, username, password, role="doctor", lang=None):
    """Create a user. ADMIN ONLY. Same username rule as server rename
    (3-32 chars, no spaces); password min 4 chars. Returns (ok, msg)."""
    if (current_role or "doctor") != "admin":
        return False, _m("Only the admin can create users", "إنشاء المستخدمين للمدير فقط", lang)
    if not valid_username(username):
        return False, _m("Invalid username (3-32 chars, no spaces)", "اسم مستخدم غير صالح (3-32 حرفاً، بدون مسافات)", lang)
    if len(password or "") < 4:
        return False, _m("Password too short (min 4)", "كلمة السر قصيرة (4 أحرف على الأقل)", lang)
    if role not in ("admin", "doctor", "nurse"):
        return False, _m("Invalid role", "دور غير صالح", lang)
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM users WHERE username=?", (username,))
    if cur.fetchone()["c"]:
        conn.close(); return False, _m("Username exists", "الاسم مستخدم مسبقاً", lang)
    cur.execute("INSERT INTO users(username, password_hash, role, created_at)"
                " VALUES(?,?,?,datetime('now'))", (username, hash_pw(password), role))
    conn.commit(); conn.close()
    return True, _m("Created", "تم الإنشاء", lang)
def delete_user(current_role, username, lang=None):
    """Delete a user. ADMIN ONLY; the last remaining admin can never be
    deleted. Returns (ok, msg)."""
    if (current_role or "doctor") != "admin":
        return False, _m("Only the admin can delete users", "حذف المستخدمين للمدير فقط", lang)
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close(); return False, _m("User not found", "المستخدم غير موجود", lang)
    if row["role"] == "admin":
        cur.execute("SELECT COUNT(*) c FROM users WHERE role='admin'")
        if cur.fetchone()["c"] <= 1:
            conn.close(); return False, _m("Cannot delete the last admin", "لا يمكن حذف آخر مدير", lang)
    cur.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit(); conn.close()
    return True, _m("Deleted", "تم الحذف", lang)
def rename_user(current_user, current_role, old_username, new_username, lang=None):
    """Rename a user. ADMIN ONLY - even renaming oneself needs the admin
    role. Password and role stay unchanged. Returns (ok, message)."""
    if (current_role or "doctor") != "admin":
        return False, _m("Only the admin can rename users", "إعادة التسمية للمدير فقط", lang)
    if not valid_username(new_username):
        return False, _m("Invalid new username (3-32 chars, no spaces)", "اسم المستخدم الجديد غير صالح (3-32 حرفاً، بدون مسافات)", lang)
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM users WHERE username=?", (old_username,))
    if not cur.fetchone()["c"]:
        conn.close(); return False, _m("User not found", "المستخدم غير موجود", lang)
    cur.execute("SELECT COUNT(*) c FROM users WHERE username=?", (new_username,))
    if cur.fetchone()["c"]:
        conn.close(); return False, _m("Username exists", "الاسم مستخدم مسبقاً", lang)
    cur.execute("UPDATE users SET username=? WHERE username=?", (new_username, old_username))
    conn.commit(); conn.close()
    if _CURRENT["username"] == old_username:
        _CURRENT["username"] = new_username
    return True, _m("Renamed", "تمت إعادة التسمية", lang)
def change(old_user, old_pass, new_user, new_pass, role=None, lang=None):
    if not verify(old_user, old_pass):
        return False, _m("Old credentials invalid", "بيانات الدخول القديمة غير صحيحة", lang)
    if not new_user or not new_pass:
        return False, _m("New fields required", "الحقول الجديدة مطلوبة", lang)
    if new_user != old_user and (role or get_user_role(old_user)) != "admin":
        return False, _m("Only the admin can change usernames", "تغيير الاسم للمدير فقط", lang)
    conn = get_connection(); cur = conn.cursor()
    if new_user != old_user:
        cur.execute("SELECT COUNT(*) c FROM users WHERE username=?", (new_user,))
        if cur.fetchone()["c"]:
            conn.close(); return False, _m("Username exists", "الاسم مستخدم مسبقاً", lang)
    cur.execute("UPDATE users SET username=?, password_hash=? WHERE username=?",
                (new_user, hash_pw(new_pass), old_user))
    conn.commit(); conn.close()
    return True, _m("Updated", "تم التحديث", lang)
