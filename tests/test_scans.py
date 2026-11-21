"""Phase 3 scans: registration, metadata, honest 3D/DICOM limits.
Runs with plain python (no pytest needed) and with pydicom NOT installed."""
import sqlite3
import sys
import tempfile
from pathlib import Path

from src.models.scans import (delete_scan, ensure_tables, list_scans,
                              preview_available, register_scan, scan_info)

_MISSING = object()


def _mem_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_scan_registration():
    conn = _mem_conn()
    ensure_tables(conn)
    sid = register_scan(conn, 1, "cbct", "/tmp/fake.dcm", "CBCT test", "fady")
    assert sid
    rows = list_scans(conn, 1)
    assert len(rows) == 1 and rows[0]["scan_type"] == "cbct"
    assert rows[0]["description"] == "CBCT test"
    assert list_scans(conn, 999) == []
    assert delete_scan(conn, sid) is True
    assert list_scans(conn, 1) == []
    assert delete_scan(conn, sid) is False
    conn.close()
    try:
        register_scan(conn, 1, "bogus", "/tmp/x", "", "fady")
        raise AssertionError("invalid scan_type should raise")
    except ValueError:
        pass


def test_image_metadata():
    with tempfile.TemporaryDirectory() as td:
        from PIL import Image
        p = Path(td) / "test.png"
        Image.new("RGB", (120, 80), "white").save(p)
        info = scan_info(str(p))
        assert info["exists"] is True and info["size_bytes"] > 0
        assert "120" in info["detail"] and "80" in info["detail"], info
        ok, msg = preview_available(str(p))
        assert ok is True, msg


def test_fake_stl():
    stl = ("solid test\n facet normal 0 0 1\n  outer loop\n"
           "   vertex 0 0 0\n   vertex 1 0 0\n   vertex 0 1 0\n"
           "  endloop\n endfacet\nendsolid test\n")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "jaw.stl"
        p.write_text(stl, encoding="utf-8")
        info = scan_info(str(p))  # must not crash
        assert info["exists"] is True and info["size_bytes"] > 0
        assert "1" in info["detail"], info  # 1 triangle parsed
        ok, msg = preview_available(str(p))
        assert ok is False and "3D" in msg, msg


def test_mesh_counts():
    with tempfile.TemporaryDirectory() as td:
        ply = Path(td) / "a.ply"
        ply.write_text("ply\nformat ascii 1.0\nelement vertex 4\n"
                       "element face 2\nend_header\n", encoding="utf-8")
        assert "4" in scan_info(str(ply))["detail"]
        assert preview_available(str(ply))[0] is False
        obj = Path(td) / "b.obj"
        obj.write_text("v 0 0 0\nv 1 0 0\nf 1 2\n", encoding="utf-8")
        assert "2" in scan_info(str(obj))["detail"]
        assert preview_available(str(obj))[0] is False


def test_missing_pydicom_graceful():
    # Fake DICOM: must never raise, with or without pydicom installed.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "scan.dcm"
        p.write_bytes(b"not a real dicom file")
        old = sys.modules.get("pydicom", _MISSING)
        sys.modules["pydicom"] = None  # forces ImportError on import
        try:
            info = scan_info(str(p))
        finally:
            if old is _MISSING:
                sys.modules.pop("pydicom", None)
            else:
                sys.modules["pydicom"] = old
        assert isinstance(info, dict) and info["exists"] is True
        assert "pydicom" in info["detail"].lower(), info
        ok, msg = preview_available(str(p))
        assert ok is False and "pydicom" in msg.lower(), msg
        # Same file with pydicom importable (if installed) still must not raise.
        info2 = scan_info(str(p))
        assert isinstance(info2, dict)


def test_missing_file():
    info = scan_info("/tmp/does_not_exist_anadoctorfady_xyz.dcm")
    assert info["exists"] is False and info["size_bytes"] == 0
    ok, _msg = preview_available("/tmp/does_not_exist_anadoctorfady_xyz.png")
    assert ok is False
