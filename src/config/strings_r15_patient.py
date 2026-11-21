"""Round 15 patient-save strings (2026-11-10).

Grandfather is now OPTIONAL on the patient form, so the old
'All name fields required!' message can no longer name the fields
that are actually missing. This module adds the field-naming
message; the field labels themselves reuse the existing keys
patient.first_name / patient.father / patient.last_family.

ONLY EN and AR dicts -- nothing else. Merged into src.config.strings
(t()) by strings.py (coordinator wires the merge). Every key needs
EN + AR. Placeholder {fields} is the comma-joined list of the
missing field labels in the user's language.
"""
EN = {
    'patient.err_names_missing': 'Missing required name field(s): {fields}',
}
AR = {
    'patient.err_names_missing': 'حقول الاسم المطلوبة مفقودة: {fields}',
}
