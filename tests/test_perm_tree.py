"""Permission tree (Round 12, Job 10): per-user expandable tree of
permission groups with checkboxes granting EXTRA permissions beyond
the role default. has_perm(username, perm) = role default OR grant;
grants never remove a role default. The tree is admin-only (the whole
Users tab is hidden for non-admins). Grants live in user_grants
(local only — the sync protocol has no grants kind). GUI tests live
in tests/test_perm_tree_gui.py."""
from src.models.database import init_db, get_connection
from src.models.permissions import (PERM_GROUPS, PERM_KEYS, ROLE_DEFAULTS,
                                    get_user_grants, grant_perm, revoke_perm,
                                    has_perm, clear_user_grants)


def _setup():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    for u, r in (("pt_doc", "doctor"), ("pt_nurse", "nurse")):
        cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",
                    (u, "x", r))
    conn.commit(); conn.close()


def _teardown():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM user_grants WHERE username IN ('pt_doc','pt_nurse')")
    cur.execute("DELETE FROM users WHERE username IN ('pt_doc','pt_nurse')")
    conn.commit(); conn.close()


def test_catalog_covers_known_groups_and_keys():
    groups = [g for g, _ in PERM_GROUPS]
    for g in ("clinical", "finance", "users", "settings", "attendance", "salaries"):
        assert g in groups, groups
    assert len(PERM_KEYS) == len(set(PERM_KEYS))  # no duplicate keys
    assert "finance.view" in PERM_KEYS and "finance.edit_amounts" in PERM_KEYS
    assert "users.manage" in PERM_KEYS and "salaries.view" in PERM_KEYS
    assert "clinical.delete" in PERM_KEYS and "attendance.view" in PERM_KEYS
    for key in PERM_KEYS:
        assert key in ROLE_DEFAULTS, f"no role default for {key}"


def test_grant_persists_and_has_perm_uses_it():
    _setup()
    try:
        assert get_user_grants("pt_nurse") == set()
        assert has_perm("pt_nurse", "finance.view") is False  # nurse default: none
        assert grant_perm("pt_nurse", "finance.view") is True
        assert "finance.view" in get_user_grants("pt_nurse")
        # Re-read from the DB (fresh connection inside the helper).
        assert has_perm("pt_nurse", "finance.view") is True
        assert revoke_perm("pt_nurse", "finance.view") is True
        assert has_perm("pt_nurse", "finance.view") is False
        # Unknown permissions are refused, never stored.
        assert grant_perm("pt_nurse", "nope.not_a_perm") is False
        assert has_perm("pt_nurse", "nope.not_a_perm") is False
        assert grant_perm("", "finance.view") is False
    finally:
        _teardown()


def test_role_defaults_still_apply_and_grants_never_remove():
    _setup()
    try:
        # Defaults: nurse registers attendance, doctor edits clinical.
        assert has_perm("pt_nurse", "attendance.register") is True
        assert has_perm("pt_doc", "clinical.edit") is True
        assert has_perm("pt_doc", "clinical.delete") is False
        # Revoking a non-grant never removes the role default.
        assert revoke_perm("pt_nurse", "attendance.register") is True
        assert has_perm("pt_nurse", "attendance.register") is True
        # A grant adds; revoking it returns to the default (False here).
        assert grant_perm("pt_doc", "clinical.delete") is True
        assert has_perm("pt_doc", "clinical.delete") is True
        assert revoke_perm("pt_doc", "clinical.delete") is True
        assert has_perm("pt_doc", "clinical.delete") is False
        # Admin keeps admin-only defaults with no grants at all.
        assert has_perm("fady", "users.manage") is True
        assert has_perm("fady", "salaries.view") is True
        # Explicit role param (no DB user needed).
        assert has_perm("ghost", "users.manage", role="admin") is True
        assert has_perm("ghost", "users.manage", role="doctor") is False
    finally:
        _teardown()


def test_clear_user_grants():
    _setup()
    try:
        grant_perm("pt_doc", "finance.edit_amounts")
        grant_perm("pt_doc", "users.manage")
        assert len(get_user_grants("pt_doc")) == 2
        clear_user_grants("pt_doc")
        assert get_user_grants("pt_doc") == set()
        assert has_perm("pt_doc", "finance.edit_amounts") is False
    finally:
        _teardown()

