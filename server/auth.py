"""ANADOCTORFADY sync server - password helpers (stdlib only).

Hashing: SHA-256 over (salt + password), salt = secrets.token_hex(16).
Default admin: fady / 1234, role admin, center_id 'main' - created only
when the users table is empty. Password policy: every user changes ONLY
their own password (POST /auth/change-password with old_password); only
an admin may change another user's password (same endpoint, username
given, no old_password needed). Deleting users: DELETE /users/<name>,
admin only, and the last remaining admin cannot be deleted.
No activation code lives here or anywhere.
"""
import hashlib
import secrets

DEFAULT_ADMIN_USER = "fady"
DEFAULT_ADMIN_PASS = "1234"
DEFAULT_ADMIN_ROLE = "admin"
DEFAULT_ADMIN_CENTER = "main"


def hash_password(password, salt=None):
    """Return (password_hash, salt). Salt is generated if not given."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + str(password)).encode("utf-8"))
    return digest.hexdigest(), salt


def verify_password(password, salt, password_hash):
    """True iff password matches the stored salt + hash."""
    if not password or not salt or not password_hash:
        return False
    digest = hashlib.sha256((salt + str(password)).encode("utf-8"))
    return digest.hexdigest() == password_hash


def set_user_password(conn, username, new_password):
    """Set a user's password (new hash+salt). True if the user exists."""
    pw_hash, salt = hash_password(new_password)
    cur = conn.execute("UPDATE users SET password_hash=?, salt=? WHERE username=?",
                       (pw_hash, salt, username))
    conn.commit()
    return cur.rowcount > 0


def change_user_password(conn, actor, target, old_password, new_password):
    """Policy: anyone changes ONLY their own password (old_password
    required); only an admin may change another user's (no old_password).
    Returns (status, error_or_None)."""
    if len(new_password or "") < 4:
        return 400, "new password too short (min 4 chars)"
    row = conn.execute("SELECT password_hash, salt FROM users WHERE username=?",
                       (target,)).fetchone()
    if not row:
        return 404, "user not found / المستخدم غير موجود"
    if target != actor["username"]:
        if actor.get("role") != "admin":
            return 403, "admin only / للمدراء فقط"
    elif not verify_password(old_password or "", row[1], row[0]):
        return 401, "wrong old password / كلمة السر القديمة خاطئة"
    set_user_password(conn, target, new_password)
    return 200, None


def valid_username(name):
    """Username rule: 3-32 chars, no spaces or '/' (it appears in URLs)."""
    n = name or ""
    return 3 <= len(n) <= 32 and not any(c.isspace() or c == "/" for c in n)


def rename_user(conn, actor, old_username, new_username):
    """Rename a user. ADMIN ONLY - even renaming oneself needs the admin
    role. Password, role and center_id stay unchanged; the user logs in
    with the NEW name + the SAME password. Historical sync/attendance
    records keep the OLD author name (not rewritten). (status, error)."""
    if (actor or {}).get("role") != "admin":
        return 403, "admin only / للمدراء فقط"
    if not valid_username(new_username):
        return 400, "invalid new username (3-32 chars, no spaces) / اسم مستخدم جديد غير صالح"
    row = conn.execute("SELECT username FROM users WHERE username=?",
                       (old_username,)).fetchone()
    if not row:
        return 404, "user not found / المستخدم غير موجود"
    taken = conn.execute("SELECT 1 FROM users WHERE username=?",
                         (new_username,)).fetchone()
    if taken:
        return 409, "username already exists / الاسم مستخدم مسبقاً"
    conn.execute("UPDATE users SET username=? WHERE username=?",
                 (new_username, old_username))
    conn.commit()
    return 200, None


def delete_user(conn, username):
    """Delete a user; refuses the last remaining admin. (ok, error)."""
    row = conn.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        return False, "user not found / المستخدم غير موجود"
    if row[0] == "admin" and conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] <= 1:
        return False, "cannot delete the last admin / لا يمكن حذف آخر مدير"
    conn.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    return True, ""


def create_default_admin(conn):
    """Create fady/1234 (admin, center 'main') if users table is empty.

    Returns True if the admin was created, False if users already exist.
    """
    row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    if row and row[0] > 0:
        return False
    pw_hash, salt = hash_password(DEFAULT_ADMIN_PASS)
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, role,"
        " center_id, created_at) VALUES (?,?,?,?,?,"
        " datetime('now'))",
        (DEFAULT_ADMIN_USER, pw_hash, salt,
         DEFAULT_ADMIN_ROLE, DEFAULT_ADMIN_CENTER))
    conn.commit()
    return True
