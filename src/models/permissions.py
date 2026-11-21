"""Roles & permissions (Phase 4). Pure role functions, no DB access,
plus the Round 12 (Job 10) extra-permission layer.

Roles: admin / doctor / nurse. Bilingual labels EN+AR.
Patient files are shared: every role in the same center sees all
patients of that center; synced records keep author + center_id.

Extra grants (user_grants table, local only — the sync protocol has
no grants kind, so grants do NOT sync; see report): an admin ticks
extra permissions for a user in the Users tab tree. Grants ONLY ADD
to the role default, never remove it:
    has_perm(username, perm) = role default OR grant.
"""
ROLE_LABELS = {
    "admin": ("Admin", "مدير"),
    "doctor": ("Doctor", "طبيب"),
    "nurse": ("Nurse", "ممرضة / ممرض"),
}
# Permission catalog: (group, key, EN label, AR label). Groups render
# as the expandable tree nodes in the admin-only Users tab.
PERM_GROUPS = (
    ("clinical", (("clinical.view", "View patient files", "عرض ملفات المرضى"),
                  ("clinical.edit", "Edit clinical records", "تعديل السجلات السريرية"),
                  ("clinical.delete", "Delete clinical records", "حذف السجلات السريرية"))),
    ("finance", (("finance.view", "View finance", "عرض المالية"),
                 ("finance.edit_amounts", "Edit payment amounts", "تعديل مبالغ المدفوعات"))),
    ("salaries", (("salaries.view", "View salaries", "عرض الرواتب"),)),
    ("users", (("users.manage", "Manage users", "إدارة المستخدمين"),)),
    ("settings", (("settings.manage", "Manage settings", "إدارة الإعدادات"),)),
    ("attendance", (("attendance.view", "View attendance", "عرض الحضور"),
                    ("attendance.register", "Register attendance", "تسجيل الحضور"))),
)
PERM_KEYS = tuple(k for _g, ps in PERM_GROUPS for k, _e, _a in ps)
# Role defaults: which roles hold each permission WITHOUT any grant.
ROLE_DEFAULTS = {
    "clinical.view": {"admin", "doctor", "nurse"},
    "clinical.edit": {"admin", "doctor"},
    "clinical.delete": {"admin"},
    "finance.view": {"admin", "doctor"},
    "finance.edit_amounts": {"admin"},
    "salaries.view": {"admin"},
    "users.manage": {"admin"},
    "settings.manage": {"admin"},
    "attendance.view": {"admin"},
    "attendance.register": {"admin", "doctor", "nurse"},
}
def _role(role):
    return (role or "doctor").strip().lower()
def can_edit_payments(role):
    """Edit payments / المدفوعات: admin only."""
    return _role(role) == "admin"
def finance_scope(role):
    """Finance tab scope: admin -> "full" (center totals), doctor ->
    "own" (only their own income), nurse -> "none" (no finance access)."""
    r = _role(role)
    if r == "admin": return "full"
    if r == "doctor": return "own"
    return "none"
def can_add_payment(role, doctor, current_user):
    """Record a payment: admin -> anyone; doctor -> only for themselves;
    nurse -> anyone (she collects the money; the income is credited to
    the treating doctor, never to who typed the entry)."""
    r = _role(role)
    if r == "admin": return True
    if r == "doctor": return (doctor or "") == (current_user or "")
    if r == "nurse": return True
    return False
def can_edit_clinical(role):
    """Edit clinical notes/diagnoses/procedures: admin + doctor."""
    return _role(role) in ("admin", "doctor")
def can_view_patients(role):
    """View patient files: all roles (same center)."""
    return _role(role) in ("admin", "doctor", "nurse")
def can_manage_users(role):
    """Create/manage users: admin only."""
    return _role(role) == "admin"
def can_manage_salaries(role):
    """Salaries (employees + payments): admin only. Doctors/nurses see
    NO salary data - not even their own salary."""
    return _role(role) == "admin"
def can_delete_records(role):
    """Delete records: admin only."""
    return _role(role) == "admin"
def can_register_attendance(role):
    """Clock in/out: all roles."""
    return _role(role) in ("admin", "doctor", "nurse")
def can_view_attendance(role):
    """View attendance log: admin only."""
    return _role(role) == "admin"
def role_label(role, lang="en"):
    """(EN, AR) label for a role; lang picks one."""
    en, ar = ROLE_LABELS.get(_role(role), ("User", "مستخدم"))
    return ar if lang == "ar" else en
def perm_label(perm, lang="en"):
    """Bilingual label for a permission key; the key itself if unknown."""
    for _g, ps in PERM_GROUPS:
        for k, en, ar in ps:
            if k == perm:
                return ar if lang == "ar" else en
    return perm
def get_user_grants(username):
    """Extra permission keys granted to `username` (local user_grants
    table). Unknown keys are ignored; empty set for unknown users."""
    from src.models.database import get_connection, init_db
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        rows = cur.execute("SELECT perm FROM user_grants WHERE username=?",
                           (username or "",)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return {r[0] for r in rows if r[0] in PERM_KEYS}
def grant_perm(username, perm):
    """Add one extra permission. False for unknown perms / bad names."""
    if perm not in PERM_KEYS or not username or not str(username).strip():
        return False
    from src.models.database import get_connection, init_db
    init_db()
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO user_grants(username, perm) VALUES(?,?)",
                 (username, perm))
    conn.commit(); conn.close()
    return True
def revoke_perm(username, perm):
    """Remove one extra permission. Grants never remove role defaults
    — revoking only removes the EXTRA grant, the role keeps its own."""
    if perm not in PERM_KEYS or not username:
        return False
    from src.models.database import get_connection, init_db
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM user_grants WHERE username=? AND perm=?",
                 (username, perm))
    conn.commit(); conn.close()
    return True
def clear_user_grants(username):
    """Drop ALL extra grants for `username` (called when the user is
    deleted, so a recreated same-name user starts with role defaults)."""
    from src.models.database import get_connection, init_db
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM user_grants WHERE username=?", (username or "",))
    conn.commit(); conn.close()
def has_perm(username, perm, role=None):
    """True when `username` holds `perm`: role default OR extra grant.
    Role is read from the users table when not passed; unknown users
    fall back to the "doctor" role (same as get_user_role)."""
    if perm not in PERM_KEYS:
        return False
    if role is None:
        try:
            from src.utils.auth import get_user_role
            role = get_user_role(username)
        except Exception:
            role = "doctor"
    if _role(role) in ROLE_DEFAULTS.get(perm, set()):
        return True
    return perm in get_user_grants(username)
