"""Round 44 model tests: semi-automatic update from GitHub
Releases — version compare (equal / older / newer / v-prefix /
malformed), the 24h throttle, dismissed-tag suppression with a
newer tag re-notifying, the asset picked by exact name, download
validation (MZ header + >1 MB), silent failures throughout. The
GUI half lives in test_r44_update_gui. ALL network is mocked;
the real GitHub is never touched. <200 lines."""
import io, json, tempfile, time, urllib.error
from pathlib import Path
from unittest.mock import patch

from src.models import updater
from src.models.database import get_setting, set_setting
from tests.test_templates_edit import isolated_db

FAKE_DL = "https://example.invalid/ANADOCTORFADY_Setup.exe"
INFO = {"tag": "v9.9.9", "version": "9.9.9", "url": FAKE_DL}
BIG_MZ = b"MZ" + b"\x00" * 1_100_000


def _asset(name, url=FAKE_DL):
    return {"name": name, "browser_download_url": url}


def _release(tag="v9.9.9", assets=None):
    if assets is None:
        assets = [_asset("other.exe", "https://example.invalid/o"),
                  _asset(updater.ASSET_NAME),
                  _asset(updater.ASSET_NAME + ".bak")]
    return {"tag_name": tag, "assets": assets}


class _Resp:
    def __init__(self, data=b"", status=200, headers=None):
        self._buf = io.BytesIO(data)
        self.status = status
        self.headers = headers or {}

    def read(self, n=-1):
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fetch(payload, status=200):
    body = payload if isinstance(payload, bytes) else \
        json.dumps(payload).encode()
    return patch("urllib.request.urlopen",
                 return_value=_Resp(body, status=status))


def _due(now):
    set_setting(updater.KEY_LAST_CHECK, str(now - 90000))


def test_version_compare():
    assert updater.parse_version("v2.1.0") == (2, 1, 0)
    assert updater.parse_version("2.10.3") == (2, 10, 3)
    assert updater.parse_version("release-2") is None
    assert updater.parse_version("v2.x") is None
    assert updater.parse_version("") is None
    assert updater.parse_version(None) is None
    assert updater.is_newer("v2.1.0") is False       # equal to app
    assert updater.is_newer("2.1.0") is False        # equal, no v
    assert updater.is_newer("v2.0.9") is False       # older
    assert updater.is_newer("v2.1.1") is True        # newer patch
    assert updater.is_newer("v2.10.0", "2.9.9") is True
    assert updater.is_newer("v3") is True            # short tuple
    assert updater.is_newer("garbage") is False      # malformed
    assert updater.is_newer("") is False


def test_check_throttle_24h():
    with isolated_db():
        now = 1_700_000_000.0
        set_setting(updater.KEY_LAST_CHECK, str(now - 100))
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("must not fetch")):
            assert updater.check_for_update(now=now) is None
        _due(now)
        with _fetch(_release()):
            info = updater.check_for_update(now=now)
        assert info == INFO
        # the attempt itself was recorded (failures throttle too)
        assert float(get_setting(updater.KEY_LAST_CHECK)) == now


def test_check_silent_failures():
    with isolated_db():
        now = 1_700_000_000.0
        _due(now)
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("offline")):
            assert updater.check_for_update(now=now) is None
        _due(now)
        with _fetch(b"", status=404):  # no releases published yet
            assert updater.check_for_update(now=now) is None
        _due(now)
        with _fetch(b"not json"):
            assert updater.check_for_update(now=now) is None
        _due(now)
        with _fetch(_release(tag="v2.1.0")):  # not newer
            assert updater.check_for_update(now=now) is None


def test_dismissed_suppressed_newer_renotifies():
    with isolated_db():
        now = 1_700_000_000.0
        updater.dismiss("v9.9.9")
        _due(now)
        with _fetch(_release("v9.9.9")):
            assert updater.check_for_update(now=now) is None
        _due(now)
        with _fetch(_release("v9.9.10")):
            info = updater.check_for_update(now=now)
        assert info["tag"] == "v9.9.10"


def test_asset_picked_by_exact_name():
    info = updater.pick_release(_release())
    assert info == INFO
    assert updater.pick_release(_release(assets=[
        _asset("ANADOCTORFADY_Setup.exe.bak")])) is None
    assert updater.pick_release({"tag_name": "v1"}) is None
    assert updater.pick_release(None) is None
    assert updater.pick_release({"assets": []}) is None


def test_download_validation():
    dest = Path(tempfile.mkdtemp()) / "setup.exe"
    seen = []
    with patch("urllib.request.urlopen", return_value=_Resp(
            BIG_MZ, headers={"Content-Length": str(len(BIG_MZ))})):
        out = updater.download_installer(
            FAKE_DL, str(dest),
            progress=lambda d, t: seen.append((d, t)))
    assert out == ("ok", str(dest)) and dest.exists()
    assert seen[-1] == (len(BIG_MZ), len(BIG_MZ))
    assert updater.validate_installer(str(dest)) is True
    with patch("urllib.request.urlopen",
               return_value=_Resp(b"MZtiny")):
        assert updater.download_installer(FAKE_DL, str(dest)) == \
            ("invalid", None)
    assert not dest.exists()  # tiny file deleted, never launchable
    with patch("urllib.request.urlopen", return_value=_Resp(
            b"PK" + b"\x00" * 1_100_000)):
        assert updater.download_installer(FAKE_DL, str(dest)) == \
            ("invalid", None)
    assert not dest.exists()  # non-MZ deleted too
    with patch("urllib.request.urlopen",
               side_effect=urllib.error.URLError("down")):
        assert updater.download_installer(FAKE_DL, str(dest)) == \
            ("failed", None)
    assert not dest.exists()
    assert updater.validate_installer(str(dest)) is False


