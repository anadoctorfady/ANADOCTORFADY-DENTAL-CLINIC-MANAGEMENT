"""Round 46 (owner purge, 2026-11-23): the old chat app's name
(English and Arabic) and any complete Syrian phone number --
real or fictional, in ASCII or Arabic-Indic digits -- are banned
from the shipped tree. The owner widened the round-45 rule
himself: remove the word and the number "even if empty or not
real", because every clinic has its own number and its own
contact channel.

The legacy-key scenario in the round-45 tests stays truthful (an
old database really does carry a settings row under that key
name) by assembling the word/key from parts; absence assertions
reference it the same way.

One distinction is deliberate and documented here so it is never
"fixed" by mistake: src/models/patient_norms.normalize_phone()
keeps its country-prefix stripping LOGIC -- bare prefix constants
in code, never a complete number. That is search behaviour for
Syrian patients, not a stored or displayed sample number, and
removing it would break phone search for the owner's own clinic.
This guard therefore bans complete-number forms (a prefix
followed by subscriber digits) and the two known digit
sequences, not the prefix logic. Every pattern below is
assembled by concatenation so this file itself stays clean.

Round 49 (owner decision, Section B): the appointment-reminder
feature necessarily names the messaging service inside its OWN
files. The purge was aimed at the app's public CONTACT channel,
which stays as decided in round 45 and is NOT exempt. For the
reminder feature's files below, only the word checks are waived;
every digit-sequence and complete-number ban still applies to
them in full.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_BINARY = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc", ".db",
           ".zip", ".pdf", ".bak", ".ttf", ".woff", ".woff2", ".exe"}
_CC = "9" + "63"
_W_EN = "whats" + "app"
_W_AR = "واتس" + "اب"
_D_REAL = "944" + "234" + "456"
_D_FICT = "991" + "234" + "567"
_D_REAL_AR = "٩٤٤" + "٢٣٤" + "٤٥٦"
_D_FICT_AR = "٩٩١" + "٢٣٤" + "٥٦٧"
_COMPLETE = re.compile("(?:" + "\\+" + _CC + "|" + "00" + _CC + ")"
                       + "\\d" + "|" + _CC + "9" + "\\d{8}")
_W = "whats" + "app"
_WORD_EXEMPT = {
    "src/models/" + _W + ".py", "src/models/" + _W + "_send.py",
    "src/config/" + _W + "_guide.py", "src/config/strings_r49_wa.py",
    "src/ui/settings_" + _W + ".py", "src/ui/settings_ui.py",
    "src/ui/shell.py", "tests/test_r49_" + _W + ".py",
}


def _scan():
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
        text = p.read_text(encoding="utf-8", errors="ignore")
        low = text.lower()
        exempt = str(rel).replace("\\", "/") in _WORD_EXEMPT
        found = None
        for pat in (() if exempt else (_W_EN,)) + (_D_REAL, _D_FICT):
            if pat in low:
                found = "word-or-sequence"
                break
        if found is None and (_D_REAL_AR in text or _D_FICT_AR in text
                              or (not exempt and _W_AR in text)):
            found = "arabic-form"
        if found is None and _COMPLETE.search(text):
            found = "complete-number"
        if found:
            hits.append((str(rel), found))
    return hits


def test_no_banned_word_or_syrian_number_in_tree():
    hits = _scan()
    assert not hits, f"banned content still present: {hits}"
