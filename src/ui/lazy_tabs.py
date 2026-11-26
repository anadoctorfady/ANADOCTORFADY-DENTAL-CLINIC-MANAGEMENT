"""Lazy notebook tabs (Round 51).

The shell used to construct every tab (Appointments, Finance,
Settings, Users, About) before the login window could paint, and
again on every language/theme rebuild -- most of the startup and
toggle cost. Now _main registers each with a placeholder frame in
the notebook (same position, same title); the real tab is built
on first use: attribute access on the App (App.__getattr__) or
opening its notebook page (App._on_tab_changed). (Round 52
removed the R51 after_idle completion chain: it rebuilt every
tab inside each language/theme toggle's settle window.)
Clinical stays eager: it is the default page and patient
selection loads into it.
"""
import tkinter as tk


def register(app, nb, name, cls, text, bg, **kw):
    ph = tk.Frame(nb, bg=bg)
    nb.add(ph, text=text)
    app._lazy_tabs[name] = (cls, ph, text, kw)


def build(app, name):
    """Construct the real tab over its placeholder; returns the
    existing tab when it was already built."""
    spec = app._lazy_tabs.pop(name, None)
    if spec is None:
        return app.__dict__[name]
    cls, ph, text, kw = spec
    nb = app.notebook
    idx = nb.index(ph)
    was_selected = nb.select() == str(ph)
    tab = cls(nb, app, **kw)
    nb.forget(ph)
    # After the forget, inserting at the old last index is out of
    # bounds -- the final tab goes back in at "end".
    nb.insert(idx if idx < len(nb.tabs()) else "end", tab, text=text)
    ph.destroy()
    app.__dict__[name] = tab
    if was_selected:
        # R52: forgetting the SELECTED placeholder makes Tk pick
        # another page and post <<NotebookTabChanged>> for it --
        # left alone, that event cascade-built every remaining
        # placeholder and stranded the selection on the last one
        # (Users). Re-assert the selection on the real tab; the
        # queued event then finds a built page and stops.
        nb.select(tab)
    if name == "users":
        tab.refresh()  # _main used to refresh the user list at build
    return tab


def build_next(app):
    """after_idle chain: build one pending tab per idle pass."""
    try:
        if not app._lazy_tabs:
            return
        build(app, next(iter(app._lazy_tabs)))
        if app._lazy_tabs:
            app.after_idle(lambda: build_next(app))
    except Exception:
        pass


def ensure_selected(app):
    """Build the tab whose placeholder page is currently shown."""
    try:
        sel = app.notebook.select()
        for name, spec in list(app._lazy_tabs.items()):
            if str(spec[1]) == sel:
                build(app, name)
                return
    except Exception:
        pass
