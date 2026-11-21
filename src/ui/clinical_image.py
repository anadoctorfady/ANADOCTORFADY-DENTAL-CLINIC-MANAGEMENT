"""Clinical page -> scans upload entry (Job 7b, round 12).

Calls Agent E's importable entry point directly:
  src.ui.scans_tab.upload_image(parent, patient_file, current_user,
                                description, lang) -> saved path | None
(file dialog -> copy into scans/<file_number>/ -> register_scan).

It ALSO switches the clinical history notebook to the Scans tab
first, so even if the direct call fails or the user cancels, the
user still lands on the Scans tab where the big upload button lives.
After a successful upload the clinical view is refreshed so the new
scan appears in the Scans tree, and the Scans tab is re-selected
(the refresh rebuilds the scans frame).
"""
from src.ui.scans_tab import upload_image


def _select_scans(tab):
    """Switch the history notebook to the Scans tab, if possible."""
    nb = getattr(tab, "history_nb", None)
    scans_frame = getattr(tab, "scans_frame", None)
    if nb is not None and scans_frame is not None:
        try:
            nb.select(scans_frame)
            return True
        except Exception:
            pass
    return False


def open_add_image(tab):
    """Open the scans upload for the selected patient, from the
    clinical page. Returns True when a file was saved."""
    if not tab._need():
        return False
    lang = getattr(tab.app, "lang", "en")
    fid = tab.app.current_patient["file_number"]
    _select_scans(tab)  # fallback landing spot, before the dialog
    try:
        saved = upload_image(tab, fid, current_user=tab.current_user,
                             lang=lang)
    except Exception:
        saved = None
    if not saved:
        return False
    try:
        tab.app.refresh_clinical()
    except Exception:
        pass
    _select_scans(tab)  # refresh rebuilds the scans frame; stay on it
    return True
