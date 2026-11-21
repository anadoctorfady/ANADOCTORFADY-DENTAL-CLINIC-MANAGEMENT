"""Round 30 (Worker C): pharmacological CLASS token helpers for
user-added drugs.

The token source is the medications data itself: the distinct
non-empty `class` values across src/data/medications.json (via
utils.medications.list_medications, which already merges the
user file) UNION the legacy CLASSES keys in models.interactions
(NSAID / Penicillin -- both already present as data tokens, kept
in the union so the list stays correct if the data changes).
The dialog's `category` is deliberately NOT a matching key (broad
categories false-link); it is used ONLY to ORDER the picker:
classes that occur under the chosen category come first."""
from src.utils.medications import (get_medication, list_medications,
    list_user_medications)


def class_tokens():
    """All tracked class tokens, sorted: distinct non-empty
    `class` values in the medications data + legacy CLASSES keys
    (src/models/interactions.py)."""
    toks = {str(m.get("class", "")).strip() for m in list_medications()}
    toks.discard("")
    try:
        from src.models.interactions import CLASSES
        toks |= set(CLASSES.keys())
    except Exception:
        pass
    return sorted(toks)


def classes_for_category(category):
    """Class tokens that actually occur under `category` in the
    medications data (a clean category->classes mapping exists:
    every seed drug carries both fields)."""
    cat = str(category or "").strip()
    if not cat or cat == "All":
        return set()
    return {str(m.get("class", "")).strip()
            for m in list_medications()
            if m.get("category") == cat and str(m.get("class", "")).strip()}


def ordered_class_tokens(category=None):
    """Picker order: the chosen category's classes first (sorted),
    then every remaining token (sorted). No category -> all sorted."""
    first = classes_for_category(category)
    rest = [tok for tok in class_tokens() if tok not in first]
    return sorted(first) + rest


def is_user_drug(generic):
    """True when `generic` names a drug from the user-medications
    store (medications.py has no source/origin field -- presence
    in list_user_medications() IS the distinction)."""
    g = str(generic or "").strip().lower()
    if not g:
        return False
    return any(str(u.get("generic_en", "")).strip().lower() == g
               for u in list_user_medications())


def is_unclassified_user_drug(generic):
    """True for a user-added drug whose stored class is empty:
    the alert engines key on class, so its checks are limited
    to exact-name matches (round-30 item 3c)."""
    if not is_user_drug(generic):
        return False
    med = get_medication(generic)
    return med is not None and not str(med.get("class", "") or "").strip()
