"""Semi-automatic update (round 44, owner-approved design): at
most once per 24 hours the app quietly asks GitHub Releases for
the latest ANADOCTORFADY release; when its tag is strictly newer
than APP_VERSION and was not dismissed, the UI offers a one-click
download + install. This module is the model half: it never shows
UI and never raises, and nothing here downloads or launches on
its own — the download happens only from the dialog's button
(src/ui/update_ui.py), after the user's click.

The repo path is hardcoded ON PURPOSE: it is this app's own
public home and its one update source. (The Firebase stats URL
stays a setting — a stranger's build must never route stats to
the owner's database; updates are the opposite case.)
"""
import json
import os
import tempfile
import threading
import time
import urllib.request

from src.models.database import get_setting, set_setting
from src.models.telemetry import APP_VERSION

RELEASES_LATEST_URL = (
    "https://api.github.com/repos/anadoctorfady/"
    "ANADOCTORFADY-DENTAL-CLINIC-MANAGEMENT/releases/latest")
ASSET_NAME = "ANADOCTORFADY_Setup.exe"
CHECK_INTERVAL_SECONDS = 24 * 3600  # at most one check per day
FETCH_TIMEOUT = 5
DOWNLOAD_TIMEOUT = 30
MIN_INSTALLER_BYTES = 1_000_000  # a real setup is far larger
KEY_LAST_CHECK = "update_last_check"
KEY_DISMISSED = "update_dismissed_tag"
_CHUNK = 65536


def parse_version(tag):
    """'v2.10.3' -> (2, 10, 3). None for anything malformed."""
    if not tag or not isinstance(tag, str):
        return None
    s = tag.strip()
    if s[:1] in ("v", "V"):
        s = s[1:]
    out = []
    for part in s.split("."):
        if not part.isdigit():
            return None
        out.append(int(part))
    return tuple(out) or None


def is_newer(tag, current=APP_VERSION):
    """True only when `tag` parses and is strictly newer."""
    new, cur = parse_version(tag), parse_version(current)
    if new is None or cur is None:
        return False
    n = max(len(new), len(cur))
    return new + (0,) * (n - len(new)) > cur + (0,) * (n - len(cur))


def _last_check_ts():
    try:
        return float(get_setting(KEY_LAST_CHECK) or 0)
    except Exception:
        return 0.0


def is_due(now=None):
    now = time.time() if now is None else now
    return (now - _last_check_ts()) >= CHECK_INTERVAL_SECONDS


def dismissed_tag():
    return (get_setting(KEY_DISMISSED, "") or "").strip()


def dismiss(tag):
    set_setting(KEY_DISMISSED, (tag or "").strip())


def fetch_latest(timeout=FETCH_TIMEOUT):
    """GET the latest-release JSON. None on ANY failure (offline,
    HTTP error, bad JSON) — the caller stays silent."""
    req = urllib.request.Request(RELEASES_LATEST_URL, headers={
        "User-Agent": "ANADOCTORFADY-updater",
        "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def pick_release(release):
    """From a latest-release JSON dict -> {"tag", "version", "url"}
    for the asset named exactly ASSET_NAME, else None."""
    if not isinstance(release, dict):
        return None
    tag = release.get("tag_name") or ""
    for asset in release.get("assets") or []:
        if isinstance(asset, dict) and asset.get("name") == ASSET_NAME:
            url = asset.get("browser_download_url") or ""
            if tag and url:
                return {"tag": tag, "url": url,
                        "version": tag.lstrip("vV")}
    return None


def check_for_update(now=None):
    """One throttled check: the pick_release dict when a strictly
    newer, undismissed release exists, else None. The attempt
    timestamp is recorded BEFORE the fetch, so failures also
    respect the once-per-24h cap. Never raises."""
    try:
        now = time.time() if now is None else now
        if not is_due(now):
            return None
        set_setting(KEY_LAST_CHECK, str(now))
        info = pick_release(fetch_latest())
        if not info or not is_newer(info["tag"]):
            return None
        if info["tag"] == dismissed_tag():
            return None
        return info
    except Exception:
        return None


def validate_installer(path):
    """A real installer: exists, > 1 MB, starts with 'MZ'."""
    try:
        if os.path.getsize(path) <= MIN_INSTALLER_BYTES:
            return False
        with open(path, "rb") as f:
            return f.read(2) == b"MZ"
    except Exception:
        return False


def default_dest():
    return os.path.join(tempfile.gettempdir(),
                        "ANADOCTORFADY_Setup_update.exe")


def _remove(path):
    try:
        os.remove(path)
    except Exception:
        pass


def download_installer(url, dest=None, progress=None):
    """Stream `url` to `dest` (called ONLY after the user's click
    in the update dialog). Returns ("ok", dest) | ("failed", None)
    | ("invalid", None); a partial or invalid file is always
    deleted. progress(done, total) fires per chunk; total is None
    when the server sent no Content-Length."""
    dest = dest or default_dest()
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "ANADOCTORFADY-updater"})
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            try:
                total = int(resp.headers.get("Content-Length"))
            except Exception:
                total = None
            done = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(_CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
    except Exception:
        _remove(dest)
        return ("failed", None)
    if not validate_installer(dest):
        _remove(dest)
        return ("invalid", None)
    return ("ok", dest)


def check_async(on_found):
    """Daemon-thread check (mirrors telemetry.maybe_send_async):
    on_found(info) fires only for a newer undismissed release.
    Never raises."""
    def _work():
        try:
            info = check_for_update()
            if info and on_found:
                on_found(info)
        except Exception:
            pass
    threading.Thread(target=_work, daemon=True).start()
