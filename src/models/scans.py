"""Patient scans: CBCT (.dcm), intraoral 3D (.stl/.ply/.obj), 2D images.
HONEST LIMITS: Tkinter cannot render 3D scans or DICOM volumes. Only 2D images
preview inside the app; 3D files open externally. pydicom is OPTIONAL. <150 lines."""
import struct
from datetime import datetime
from pathlib import Path

SCAN_TYPES = ("cbct", "intraoral", "image2d", "other")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".tif", ".gif"}
MESH_EXTS = {".stl", ".ply", ".obj"}
# Legacy bilingual constants kept for import compat only; round 17
# user-visible text comes from msg_3d()/msg_no_pydicom() (one language).
MSG_3D = ("3D view is not possible inside the app - use Open externally / "
          "العرض ثلاثي الأبعاد غير ممكن داخل التطبيق - استخدم «فتح خارجياً»")
MSG_NO_PYDICOM = ("pydicom not installed - install pydicom to preview slices / "
                  "pydicom غير مثبّت - ثبّته لمعاينة الشرائح")
_3D = {"en": "3D view is not possible inside the app - use Open externally",
       "ar": "العرض ثلاثي الأبعاد غير ممكن داخل التطبيق - استخدم «فتح خارجياً»"}
_NOP = {"en": "pydicom not installed - install pydicom to preview slices",
        "ar": "pydicom غير مثبّت - ثبّته لمعاينة الشرائح"}
def _lang(lang):
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"
def _m(en, ar, lang):
    return ar if _lang(lang) == "ar" else en
def msg_3d(lang=None):
    return _3D[_lang(lang)]
def msg_no_pydicom(lang=None):
    return _NOP[_lang(lang)]


def ensure_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS patient_scans(id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INT, scan_type TEXT, file_path TEXT, description TEXT, upload_date TEXT,
        uploaded_by TEXT, FOREIGN KEY(patient_id) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    conn.commit()


def register_scan(conn, patient_id, scan_type, file_path, description, uploaded_by):
    """Register an uploaded scan. Returns the new row id."""
    if scan_type not in SCAN_TYPES:
        raise ValueError(f"scan_type must be one of {SCAN_TYPES}")
    cur = conn.cursor()
    cur.execute("""INSERT INTO patient_scans(patient_id, scan_type, file_path, description, upload_date, uploaded_by) VALUES(?,?,?,?,?,?)""",
        (patient_id, scan_type, str(file_path), description or "", datetime.now().isoformat(timespec="seconds"), uploaded_by or ""))
    conn.commit()
    return cur.lastrowid


def list_scans(conn, patient_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM patient_scans WHERE patient_id=? "
                "ORDER BY upload_date DESC", (patient_id,))
    return [dict(r) for r in cur.fetchall()]


def delete_scan(conn, scan_id):
    """Delete the DB row only (caller may delete the file too)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM patient_scans WHERE id=?", (scan_id,)); conn.commit()
    return cur.rowcount > 0


def _dcm_detail(path, lang=None):
    try:
        import pydicom
    except Exception:
        return msg_no_pydicom(lang)
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True)
        parts = [f"{k}: {getattr(ds, k, '')}" for k in
                 ("PatientName", "StudyDate", "Modality") if getattr(ds, k, "")]
        return "; ".join(parts) if parts else _m("DICOM file (no header info)", "ملف DICOM (لا معلومات ترويسة)", lang)
    except Exception as e:
        return _m(f"Could not read DICOM with pydicom: {e}", f"تعذّرت قراءة الملف: {e}", lang)


def _stl_detail(path, lang=None):
    unread = _m("STL file - triangle count unreadable", "ملف STL - تعذّرت قراءة عدد المثلثات", lang)
    try:
        data = Path(path).read_bytes()
        is_ascii = data[:5] == b"solid" and b"facet" in data[:512]
        n = (data.count(b"facet normal") if is_ascii else
             struct.unpack("<I", data[80:84])[0] if len(data) >= 84 else -1)
        if n < 0:
            return unread
        kind = _m("ASCII STL", "STL نصي", lang) if is_ascii else _m("Binary STL", "STL ثنائي", lang)
        return _m(f"{kind} - {n} triangle(s)", f"{kind} - {n} مثلث", lang)
    except Exception:
        pass
    return unread


def _mesh_detail(path, lang=None):
    ext = Path(path).suffix.lower()
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
        if ext == ".ply":
            v = f = 0
            for p in (ln.split() for ln in lines):
                if len(p) == 3 and p[0] == "element" and p[1] == "vertex":
                    v = int(p[2])
                if len(p) == 3 and p[0] == "element" and p[1] == "face":
                    f = int(p[2])
            return _m(f"PLY - {v} vertices, {f} faces", f"PLY - {v} نقطة، {f} وجه", lang)
        v = sum(1 for ln in lines if ln.startswith("v "))
        f = sum(1 for ln in lines if ln.startswith("f "))
        return _m(f"OBJ - {v} vertices, {f} faces", f"OBJ - {v} نقطة، {f} وجه", lang)
    except Exception:
        return _m("3D mesh file - counts unreadable", "ملف شبكي ثلاثي الأبعاد - تعذّرت قراءة العدد", lang)


def _image_detail(path, lang=None):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return _m(f"{im.format or 'Image'} {im.width}x{im.height} px",
                      f"صورة {im.width}×{im.height}", lang)
    except Exception:
        return _m("Image file - dimensions unreadable", "ملف صورة - تعذّرت قراءة الأبعاد", lang)


def scan_info(file_path, lang=None):
    """Never raises: {kind, size_bytes, exists, detail} for any file.
    detail is single-language (lang=None -> the app language)."""
    p = Path(file_path)
    info = {"kind": p.suffix.lower().lstrip(".") or "other", "exists": p.exists(),
            "size_bytes": p.stat().st_size if p.exists() else 0,
            "detail": _m("File not found", "الملف غير موجود", lang)}
    if not info["exists"]:
        return info
    ext = p.suffix.lower()
    try:
        handlers = {".dcm": _dcm_detail, ".stl": _stl_detail,
                    ".ply": _mesh_detail, ".obj": _mesh_detail}
        handlers.update({e: _image_detail for e in IMAGE_EXTS})
        stored = lambda _p, _l=None: _m("File stored - no preview info",
                                        "ملف محفوظ - لا معلومات معاينة", lang)
        info["detail"] = handlers.get(ext, stored)(file_path, lang)
    except Exception as e:  # last-resort guard: never crash on bad files
        info["detail"] = _m(f"Unreadable file: {e}", f"ملف غير قابل للقراءة: {e}", lang)
    return info


def preview_available(file_path, lang=None):
    """(bool, message). True only for 2D images, or .dcm when pydicom+numpy
    exist. The message is single-language (lang=None -> app language)."""
    p = Path(file_path)
    if not p.exists():
        return False, _m("File not found", "الملف غير موجود", lang)
    ext = p.suffix.lower()
    if ext in MESH_EXTS:
        return False, msg_3d(lang)
    if ext == ".dcm":
        try:
            import pydicom, numpy  # noqa: F401
            return True, _m("CBCT slice preview available with pydicom", "معاينة الشرائح متاحة", lang)
        except Exception:
            return False, msg_no_pydicom(lang)
    if ext in IMAGE_EXTS:
        try:
            from PIL import Image
            with Image.open(p) as im:
                im.verify()
            return True, _m("2D image preview available", "معاينة الصورة متاحة", lang)
        except Exception:
            return False, _m("Image cannot be displayed", "تعذّرت معاينة الصورة", lang)
    return False, _m("No preview for this file type - use Open externally", "لا معاينة لهذا النوع - استخدم «فتح خارجياً»", lang)
