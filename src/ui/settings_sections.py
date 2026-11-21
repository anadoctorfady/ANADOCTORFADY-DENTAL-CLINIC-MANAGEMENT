"""Settings section gating (round 21 item 10).

Lives here, not settings_ui.py, because that file is at the
200-line limit (same pattern as settings_account.py).

The split the owner asked for: the ADMIN sections of Settings --
sync/server, storage (clinic name + folders), backup/restore,
the default-currency choice, and the rename-user frame -- require
the `settings.manage` permission (the admin has it by default;
the admin can GRANT it to a non-admin from the Users tab's
permission tree; grants are local-only, as before). The PERSONAL
sections -- theme, language (top bar), and Change Password (own
password only, the owner's standing rule) -- are never gated.
"""
from src.models.permissions import has_perm
from src.utils.auth import get_current_role, get_current_user


def can_settings_admin():
    """True when the logged-in user holds settings.manage."""
    return has_perm(get_current_user(), "settings.manage",
                    get_current_role())


def toggle_admin_sections(tab, can):
    """Show/hide the settings-admin sections on the Settings tab,
    keeping pack order (each section re-packs right after its
    predecessor). "Packed" is tested via winfo_manager() -- the
    tab may be unmapped inside the notebook, so winfo_ismapped()
    would give the wrong answer."""
    secs = [(tab._sync_wrap, tab._frm_wrap),
            (getattr(tab, "storage_wrap", None), tab._sync_wrap),
            (tab._rn_wrap, tab._tf_wrap)]
    for w, anchor in secs:
        if w is None:
            continue
        if can and w.winfo_manager() != "pack":
            w.pack(fill="x", padx=10, pady=8, after=anchor)
        elif not can and w.winfo_manager() == "pack":
            w.pack_forget()
    if can and tab._brow1.winfo_manager() != "pack":
        tab._brow1.pack(fill="x", padx=10, pady=(8, 0), after=tab._pref2)
    elif not can and tab._brow1.winfo_manager() == "pack":
        tab._brow1.pack_forget()
    if can and tab._cur_wrap.winfo_manager() != "pack":
        tab._cur_label.pack(side="left", padx=8, after=tab._theme_combo)
        tab._cur_wrap.pack(side="left", padx=4, after=tab._cur_label)
        if getattr(tab, "_cur_hint", None) is not None:
            others = [w for w in tab._pref2.winfo_children()
                      if w is not tab._cur_hint
                      and w.winfo_manager() == "pack"]
            tab._cur_hint.pack(side="left", padx=4,
                               before=others[0] if others else None)
    elif not can and tab._cur_wrap.winfo_manager() == "pack":
        tab._cur_label.pack_forget(); tab._cur_wrap.pack_forget()
        if getattr(tab, "_cur_hint", None) is not None:
            tab._cur_hint.pack_forget()
