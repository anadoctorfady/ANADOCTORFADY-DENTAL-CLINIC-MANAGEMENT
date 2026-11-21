"""Round 16 clinical strings: EN/AR parity (same rule as the round-15
strings test -- format-only strings may be identical)."""
import re

from src.config.strings_r16_clinical import AR as R16_AR, EN as R16_EN


def test_r16_clinical_strings_bilingual():
    assert set(R16_EN) == set(R16_AR) and R16_EN
    for key in R16_EN:
        assert R16_EN[key].strip() and R16_AR[key].strip(), key
        words = re.sub(r"\{[^}]*\}", "", R16_EN[key])
        if re.search(r"[A-Za-z\u0600-\u06FF]", words):
            assert R16_EN[key] != R16_AR[key], key
