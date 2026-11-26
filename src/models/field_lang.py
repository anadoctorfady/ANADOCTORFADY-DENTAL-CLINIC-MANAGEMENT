"""Round 43: PER-PLACE template language.

Round 31 made the template language ONE global setting
(template_lang: app|ar|en). The owner now wants the choice in
EVERY place templates are offered, independently per place: each
clinical field (complaint / symptom / diagnosis / procedure /
service / note), the patient-form disease + allergy pickers,
referral templates, and the Template Manager per browsed
category.

Resolution for a place: its persisted override
(template_lang_field_<key> = "ar" | "en") when set, else the
round-31 global default (specialty_templates'
effective_template_lang). Keys are normalised like the template
DB categories (symptom -> symptoms, procedure -> procedures), so
the picker, the manager and every dialog share ONE choice per
category. <200 lines."""
from src.models.database import get_setting, set_setting
from src.models.specialty_templates import effective_template_lang

_NORM = {"symptom": "symptoms", "procedure": "procedures"}


def field_lang_key(category):
    """The settings-key suffix for a template category/place."""
    c = (category or "").strip().lower()
    return _NORM.get(c, c) or "general"


def field_template_lang(category):
    """'ar' | 'en' for one place: its override, else the default."""
    raw = (get_setting(f"template_lang_field_{field_lang_key(category)}",
                       "") or "").strip().lower()
    return raw if raw in ("ar", "en") else effective_template_lang()


def set_field_template_lang(category, lang):
    """Persist one place's choice ('ar' | 'en'); any other value
    clears the override, returning the place to the default."""
    set_setting(f"template_lang_field_{field_lang_key(category)}",
                lang if lang in ("ar", "en") else "")
