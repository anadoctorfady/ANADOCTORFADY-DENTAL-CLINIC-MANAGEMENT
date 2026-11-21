"""Finance re-auth gate: the Finances tab needs a password re-check
(day-1 requirement, screenshot issue 6). GUI-free so it is unit-testable.

The unlock flag lives ONLY on the instance (in memory, never written to
disk or settings): a fresh instance (app restart) starts locked, and
lock() (called on logout) re-locks it for the next login.

Round 12 (Job 9b): 15-minute auto-lock. is_unlocked() goes False once
TIMEOUT_SECONDS (900 = 15 min) have passed WITHOUT ANY finance
activity. Any finance activity resets the timer via touch() (called
from the finance view: opening the tab, changing a total toggle,
adding a record, calculating). touch() never unlocks a locked gate.
"""
import time
from src.config.strings import t
from src.utils.auth import verify

TIMEOUT_SECONDS = 900  # 15 minutes of no finance activity -> re-lock


class FinanceGate:
    """In-memory session lock for the Finances tab."""

    def __init__(self, verify_fn=None):
        self._unlocked = False
        self._verify = verify_fn or verify
        self._last_activity = None  # monotonic seconds of last activity

    @property
    def is_unlocked(self):
        if not self._unlocked:
            return False
        if self._last_activity is None:
            return False
        if time.monotonic() - self._last_activity > TIMEOUT_SECONDS:
            self._unlocked = False
            self._last_activity = None
            return False
        return True

    def touch(self):
        """Record finance activity: resets the 15-minute timer. A
        locked gate stays locked — touch() never unlocks."""
        if self._unlocked:
            self._last_activity = time.monotonic()

    def try_unlock(self, username, password):
        """True + unlocked on correct credentials; stays locked otherwise."""
        ok = bool(username and password) and bool(
            self._verify(username, password))
        self._unlocked = ok
        self._last_activity = time.monotonic() if ok else None
        return ok

    def lock(self):
        self._unlocked = False
        self._last_activity = None


def prompt_texts(lang="en"):
    """Translated texts for the finance re-auth prompt (the unlock
    dialog itself lives in finance_views.py): title, prompt, the
    Unlock button label and the wrong-password message."""
    return {"title": t("dlg.fg_title", lang),
            "prompt": t("dlg.fg_prompt", lang),
            "unlock": t("dlg.fg_unlock", lang),
            "wrong": t("dlg.fg_wrong", lang)}


def require_auth(gate, username, password):
    """One-shot helper: try to unlock `gate`; returns True on success."""
    return gate.try_unlock(username, password)
