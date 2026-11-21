"""No architecture-specific code: app must build/run on x86 and x64."""
import struct
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
BANNED = ["program files", "syswow64", "system32", "win64", "amd64", "x86_64"]
def test_no_arch_specific_code():
    assert struct.calcsize("P") in (4, 8)  # 4 = 32-bit, 8 = 64-bit
    for p in list(ROOT.glob("main.py")) + list((ROOT / "src").rglob("*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore").lower()
        for bad in BANNED:
            assert bad not in text, f"{p}: contains {bad!r}"
def test_no_platform_specific_wheels():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert ".whl" not in req and "win_amd64" not in req and "win32" not in req
    assert "sys_platform" not in req and "platform_machine" not in req
