"""Round 23 item 3: the chart shows WHAT was done on each tooth.
On top of the round-16 tick, a treated tooth now carries a count
badge (xN), a hover tooltip with its full procedure history
(date + text, ALL entries, newest first) and a click popup
(double-click / tick-badge click) listing the same history.
Pinned here in the real ClinicalTab against the isolated DB copy:
treated state + badge, tooltip content + live tooltip window,
click-popup content, untreated tooth = no mark, patient with no
procedures = nothing, deciduous chart, refresh after a new save,
patient switch clearing. GUI tests skip with no display."""
import tkinter as tk
from datetime import datetime
from src.models.database import get_connection, init_db
from src.ui import chart_status
from src.ui.chart_tooltip import popup_text, tooth_history, tooltip_text
from src.utils.helpers import DECIDUOUS
from tests.test_clinical_save_gate import _build_tab, _cleanup, _seed_patient

def _seed(fid, teeth, text, date="2026-11-10", table="procedures"):
    conn = get_connection(); cur = conn.cursor()
    col = "procedure_done" if table == "procedures" else "diagnosis"
    cur.execute(f"INSERT INTO {table}(patient_file,visit_date,tooth_number,"
                f"{col},author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, date, teeth, text, "fady", datetime.now().isoformat()))
    conn.commit(); conn.close()

def _cleanup_all(*fids):
    for fid in fids:
        try:
            conn = get_connection(); cur = conn.cursor()
            for tbl in ("procedures", "diagnoses"):
                cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
            conn.commit(); conn.close()
        except Exception:
            pass
        _cleanup(fid)

def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

def _labels(widget, text):
    return [w for w in _walk(widget)
            if isinstance(w, tk.Label) and str(w.cget("text")) == text]

def _switch(tab, fid, name):
    tab.app.current_patient = {"file_number": fid, "full_name": name}
    tab.load(fid)


def test_r23_tooth_history_query_exact_tooth_match():
    init_db(); fid = _seed_patient()
    try:
        _seed(fid, "16,17", "Root canal", "2026-11-10")
        _seed(fid, "16", "Crown fitted", "2026-11-12")
        _seed(fid, "11", "Pulpitis", "2026-11-11", table="diagnoses")
        hist = tooth_history(fid, "16")
        assert [h["text"] for h in hist] == ["Crown fitted", "Root canal"], hist
        assert hist[0]["date"] == "2026-11-12" and hist[1]["date"] == "2026-11-10"
        assert tooth_history(fid, "17")[0]["text"] == "Root canal"
        assert tooth_history(fid, "1") == []  # exact token, not substring
        assert tooth_history(fid, "18") == [] and tooth_history(None, "16") == []
        txt = tooltip_text(fid, "16")
        assert "Root canal" in txt and "2026-11-10" in txt and "Crown fitted" in txt
        assert popup_text(fid, "16") == txt
        assert "Pulpitis" in tooltip_text(fid, "11")  # diagnoses surface too
    finally:
        _cleanup_all(fid)


def test_r23_chart_marks_tooltip_and_popup():
    init_db(); fid = _seed_patient()
    _seed(fid, "16", "Root canal", "2026-11-10")
    _seed(fid, "16", "Crown fitted", "2026-11-12")
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup_all(fid); print("SKIP (no display)"); return
    try:
        tab.load(fid); root.update(); chart = tab.chart
        # (a) persistent mark: treated state + tick + count badge.
        assert chart.get_treated() == ["16"]
        assert _labels(chart.tooth_cells["16"], "✓"), "no tick on 16"
        assert _labels(chart.tooth_cells["16"], "×2"), "no count badge on 16"
        assert chart.get_treated_details()["16"][0]["text"] == "Crown fitted"
        # Untreated tooth: no mark, no tooltip, no popup.
        assert not _labels(chart.tooth_cells["11"], "✓")
        assert not _labels(chart.tooth_cells["11"], "×1")
        assert chart.tooltip_text_for("11") == ""
        assert chart.show_tooth_history("11") is None
        # (b) tooltip content function + live tooltip window.
        tip_txt = chart.tooltip_text_for("16")
        assert "Root canal" in tip_txt and "2026-11-10" in tip_txt
        assert "Crown fitted" in tip_txt and "2026-11-12" in tip_txt

        class _Ev: x_root, y_root = 120, 120
        chart_status.show_tip(chart, _Ev(), "16"); root.update()
        assert chart._tip.win is not None, "hover tooltip did not open"
        shown = [str(w.cget("text")) for w in _walk(chart._tip.win)
                 if isinstance(w, tk.Label)]
        assert any("Root canal" in s for s in shown), shown
        chart._tip.hide(); root.update(); assert chart._tip.win is None
        # (c) click popup: lists the tooth's procedures with dates.
        win = chart.show_tooth_history("16"); root.update()
        assert win is not None and win.winfo_exists()
        texts = [w.get("1.0", tk.END) for w in _walk(win) if isinstance(w, tk.Text)]
        assert texts and "Root canal" in texts[0] and "2026-11-12" in texts[0]
        win.destroy(); root.update()
        # Plain click still toggles selection (round-16 behaviour).
        chart.toggle("16"); root.update()
        assert chart.get_selection()[0] == ["16"]
        assert chart.get_treated() == ["16"]  # mark survives the rebuild
    finally:
        root.destroy(); _cleanup_all(fid)


def test_r23_no_procedures_no_marks_and_switch_clears():
    init_db(); fid_a, fid_b = _seed_patient(), _seed_patient()
    _seed(fid_a, "16", "Root canal")
    root, tab = _build_tab(fid_a)
    if tab is None:
        _cleanup_all(fid_a, fid_b); print("SKIP (no display)"); return
    try:
        tab.load(fid_a); root.update()
        assert tab.chart.get_treated() == ["16"]
        _switch(tab, fid_b, "Patient B"); root.update()
        # Patient isolation: B has no procedures -> no marks at all.
        assert tab.chart.get_treated() == []
        assert tab.chart.get_treated_details() == {}
        assert tab.chart.tooltip_text_for("16") == ""
        assert tab.chart.show_tooth_history("16") is None
        assert not _labels(tab.chart.tooth_cells["16"], "✓")
        _switch(tab, fid_a, "Patient A"); root.update()  # back: A's marks only
        assert tab.chart.get_treated() == ["16"]
        assert "Root canal" in tab.chart.tooltip_text_for("16")
    finally:
        root.destroy(); _cleanup_all(fid_a, fid_b)


def test_r23_refresh_after_new_procedure_saved():
    init_db(); fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup_all(fid); print("SKIP (no display)"); return
    try:
        tab.load(fid); root.update()
        assert tab.chart.get_treated() == []
        _seed(fid, "26", "Extraction", "2026-11-15")
        # Save visit reaches the chart via load()/refresh_chart_status.
        chart_status.refresh_chart_status(tab); root.update()
        assert tab.chart.get_treated() == ["26"]
        assert _labels(tab.chart.tooth_cells["26"], "×1")
        assert "Extraction" in tab.chart.tooltip_text_for("26")
    finally:
        root.destroy(); _cleanup_all(fid)


def test_r23_deciduous_chart_treated_tooth():
    init_db(); fid = _seed_patient()
    _seed(fid, "54", "Pulpotomy", "2026-11-09")
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup_all(fid); print("SKIP (no display)"); return
    try:
        tab.load(fid); root.update(); chart = tab.chart
        chart.tooth_type.set("لبني"); chart.refresh(); root.update()
        assert set(chart.tooth_cells) == set(DECIDUOUS)
        assert chart.get_treated() == ["54"]
        assert _labels(chart.tooth_cells["54"], "✓")
        assert _labels(chart.tooth_cells["54"], "×1")
        assert "Pulpotomy" in chart.tooltip_text_for("54")
        assert "2026-11-09" in chart.tooltip_text_for("54")
        assert not _labels(chart.tooth_cells["51"], "✓")
        win = chart.show_tooth_history("54"); root.update()
        assert win is not None and win.winfo_exists(); win.destroy()
    finally:
        root.destroy(); _cleanup_all(fid)


def test_r23_tick_colour_contrast_both_themes():
    """Tick/badge fg on the cell bg >= 4.5:1 in both modes, as must
    the tooltip text on its panel background."""
    from src.config.theme import DARK, LIGHT

    def ratio(fg, bg):
        def lum(hexs):
            rgb = [int(hexs[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            rgb = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
            return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
        hi, lo = max(lum(fg), lum(bg)), min(lum(fg), lum(bg))
        return (hi + 0.05) / (lo + 0.05)

    # _title_fg resolves via the GLOBAL mode: light -> #7A3F16,
    # dark -> the dark accent. Check each mode's real pair.
    assert ratio("#7A3F16", LIGHT["bg"]) >= 4.5, ratio("#7A3F16", LIGHT["bg"])
    assert ratio(DARK["accent"], DARK["bg"]) >= 4.5
    assert ratio(LIGHT["text"], LIGHT["panel"]) >= 4.5
    assert ratio(DARK["text"], DARK["panel"]) >= 4.5
