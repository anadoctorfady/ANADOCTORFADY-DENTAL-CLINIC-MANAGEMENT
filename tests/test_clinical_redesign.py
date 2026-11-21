"""Clinical redesign (Items 5+6+13, 2026-11-08): combined template pool,
no specialty picker, silent clipboard, prescriptions merged into the
clinical page, About tab, dental-chart dark contrast, finance contrast.
GUI tests skip gracefully when no display is available."""
import tkinter as tk
from pathlib import Path

from src.models.specialties import all_phrases, load_specialties
from src.ui.phrase_picker import combined_templates
from src.ui.clinical import ClinicalTab
from src.ui.about_tab import AboutTab
from src.config.settings import ABOUT_EN, ABOUT_AR, WHATSAPP

ROOT = Path(__file__).resolve().parent.parent

SPEC_MARKERS = {  # (specialty id, complaint EN) - each must be in the pool
    "orthodontics": "Crooked teeth",
    "oral_surgery": "Wisdom tooth pain",
    "endodontics": "Severe throbbing tooth pain",
    "pediatric": "My child has tooth pain",
    "periodontics": "Bleeding gums when brushing",
    "implantology": "Missing tooth",
    "prosthodontics": "Broken crown",
    "general": "Toothache when chewing",
}


def test_combined_pool_contains_all_specialties():
    specs = load_specialties()
    assert len(specs) == 8
    pool = all_phrases("complaint")
    assert len(pool) >= 40, f"combined complaint pool too small: {len(pool)}"
    texts = {en for en, _ar in pool}
    for spec_id, marker in SPEC_MARKERS.items():
        assert marker in texts, f"{spec_id} phrase missing from combined pool: {marker}"
    for cat in ("symptom", "diagnosis", "procedure"):
        assert len(all_phrases(cat)) >= 30, cat
    # The picker dialog searches the same combined pool.
    rows = combined_templates("complaint", "braces")
    assert any("braces" in r["display"].lower() for r in rows)
    assert any("CROOKED TEETH" in r["display"] for r in combined_templates("complaint", "Crooked"))  # round 18: EN display ALL CAPS


def test_no_specialty_picker_ui_remains():
    assert not (ROOT / "src" / "ui" / "specialty_picker.py").exists()
    clinical_src = (ROOT / "src" / "ui" / "clinical.py").read_text(encoding="utf-8")
    assert "specialty_picker" not in clinical_src
    assert "get_specialty" not in clinical_src
    assert "Specialty" not in clinical_src
    for name in ("clinical_tables.py", "clinical_finance.py", "clinical_lists.py",
                 "phrase_picker.py", "prescriptions.py", "shell.py"):
        src = (ROOT / "src" / "ui" / name).read_text(encoding="utf-8")
        assert "Copy row" not in src, name
        assert "نسخ الصف" not in src, name


def _stub_app():
    class FakeApp:
        lang = "en"
        current_patient = None
        current_user = "fady"
        current_role = "admin"
        def chart_teeth(self):
            return []
        def refresh_clinical(self):
            pass
    return FakeApp()


def _build_tab():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    try:
        tab = ClinicalTab(root, _stub_app())
        tab.pack()
        root.update_idletasks()
        return root, tab
    except Exception:
        root.destroy()
        raise


def _walk(widget):
    yield widget
    for ch in widget.winfo_children():
        yield from _walk(ch)


def test_clinical_layout_chart_top_procedures_rx_below():
    root, tab = _build_tab()
    if tab is None:
        print("SKIP test_clinical_layout (no display)")
        return
    try:
        assert hasattr(tab, "chart") and tab.chart is not None
        assert hasattr(tab, "rx_section") and tab.rx_section is not None
        assert tab.rx is tab.rx_section
        # One small picker button beside EACH of the 4 fields.
        # Round 19: quarter-width one-row tables make the picker
        # button ICON-ONLY ("📋") - the full "Templates" text would
        # clip; it is still the same Templates picker button.
        assert set(tab.picker_buttons) == {"complaint", "symptom", "diagnosis", "procedure"}
        for btn in tab.picker_buttons.values():
            assert "📋" in btn.cget("text")
        # Round 20: the clinical patient-name header is REMOVED
        # (owner: it duplicated the shell's far-left info panel,
        # now the single patient-info display). The tab carries no
        # name widget; a patient refresh must still run cleanly.
        assert not hasattr(tab, "lbl_pat_name")
        tab.app.current_patient = {"full_name": "Ahmed Mohammed Ali Hassan",
                                   "file_number": 1, "mobile1": "0944000111",
                                   "birth_date_greg": "1990-05-15"}
        tab._refresh_patient_panel()
        # Order on the page: chart above the fields, Rx section below them.
        assert tab.chart.winfo_rooty() < tab.txt_complaint.winfo_rooty()
        assert tab.txt_procedure.winfo_rooty() < tab.rx_section.winfo_rooty()
        # No specialty-picker widget and no copy-row button anywhere.
        for w in _walk(tab):
            txt = str(w.cget("text")) if "text" in w.keys() else ""
            assert "Specialty" not in txt and "التخصص" not in txt, txt
            if isinstance(w, tk.Button):
                assert "Copy row" not in txt and "نسخ الصف" not in txt, txt
                assert "copy" not in txt.lower(), txt
        # Clipboard multi-paste still bound, silently (Ctrl+Shift+V).
        from src.ui.clipboard_picker import CLIPBOARD_BINDING, paste_items_into
        for name in ("complaint", "symptom", "diagnosis", "procedure",
                     "sess_total", "cost_paid", "notes"):  # R38: see test_clipboard_multi
            assert name in tab.clipboard_fields, name
            assert tab.clipboard_fields[name].bind(CLIPBOARD_BINDING), name
        tab.txt_complaint.delete("1.0", tk.END)
        assert paste_items_into(tab.txt_complaint, ["line A", "line B"]) is True
        assert tab.txt_complaint.get("1.0", tk.END).strip() == "line A\nline B"
    finally:
        root.destroy()


def test_about_tab_exists_and_prescriptions_tab_removed():
    shell_src = (ROOT / "src" / "ui" / "shell.py").read_text(encoding="utf-8")
    assert "AboutTab" in shell_src
    assert "About" in shell_src
    assert "PrescriptionsTab(nb" not in shell_src
    assert "self.rx" not in shell_src
    assert "iconphoto" in shell_src
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_about_tab_exists (no display)")
        return
    root.withdraw()
    try:
        tab = AboutTab(root, _stub_app())
        tab.pack()
        root.update_idletasks()
        texts = [str(w.cget("text")) for w in _walk(tab)
                 if isinstance(w, (tk.Label, tk.Button)) and str(w.cget("text")).strip()]
        joined = "\n".join(texts)
        assert "Dr Fady Abdulkafy Dadoush" in joined
        assert "د. فادي عبد الكافي دعدوش" in joined
        assert WHATSAPP in joined
        assert "Contact via WhatsApp only" in joined
        assert "ANADOCTORFADY" in joined
    finally:
        root.destroy()
