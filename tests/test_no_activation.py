"""Guard: activation was removed (owner decision 2026-11-05) and must
never come back. Scans only .py files under src/ — the word "activation"
also appears legitimately in drug data (e.g. clopidogrel activation in
src/data/interactions.json), which is medical text, not app activation."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DELETED = ["src/models/activation.py", "src/ui/activation_ui.py",
           "tools/generate_activation.py", "activation_secret.EXAMPLE.txt",
           "ACTIVATION.md", "tests/test_activation.py"]
BANNED = ("activation", "hmac", "machine_id")


def test_activation_files_deleted():
    for rel in DELETED:
        assert not (ROOT / rel).exists(), f"{rel} still exists"


def test_no_activation_code_in_src():
    for p in sorted((ROOT / "src").rglob("*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore").lower()
        for word in BANNED:
            assert word not in text, f"{p} contains {word!r}"


def test_shell_goes_straight_to_login():
    shell = (ROOT / "src/ui/shell.py").read_text(encoding="utf-8")
    assert "_show_login" in shell
    assert "ActivationWindow" not in shell
    assert "is_activated" not in shell
