"""Round 16 item 10: tooth selection auto-inserts its number into
the procedures field, and the chart SHOWS treated teeth (tick +
accent border + legend). Procedures are stored per tooth in the
procedures / diagnoses tables (tooth_number = comma-joined selected
teeth); teeth_records is never written, so it is not a source here.
GUI tests skip gracefully when no display is available.
"""
import tkinter as tk
from datetime import datetime

from src.models.database import get_connection, init_db
from src.ui.chart_status import treated_teeth
from src.ui.dental_chart import DentalChartFrame
from tests.test_clinical_save_gate import _build_tab, _cleanup, _seed_patient


def _seed_procedure(fid, teeth, text="Root canal", table="procedures"):
    conn = get_connection(); cur = conn.cursor()
    col = "procedure_done" if table == "procedures" else "diagnosis"
    cur.execute(f"INSERT INTO {table}(patient_file,visit_date,tooth_number,"
                f"{col},author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, datetime.now().strftime("%Y-%m-%d"), teeth, text,
                 "fady", datetime.now().isoformat()))
    conn.commit(); conn.close()


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def _labels_with_text(widget, text):
    return [w for w in _walk(widget)
            if isinstance(w, tk.Label) and str(w.cget("text")) == text]


def test_r16_treated_teeth_query():
    fid = _seed_patient()
    try:
        assert treated_teeth(fid) == []
        assert treated_teeth(None) == []
        _seed_procedure(fid, "16,17")
        _seed_procedure(fid, "11", table="diagnoses")
        assert treated_teeth(fid) == ["11", "16", "17"]
    finally:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM procedures WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM diagnoses WHERE patient_file=?", (fid,))
        conn.commit(); conn.close()
        _cleanup(fid)


def test_r16_tooth_selection_inserts_number():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_r16_tooth_selection_inserts_number (no display)")
        return
    try:
        assert tab.txt_procedure.get("1.0", tk.END).strip() == ""
        tab.chart.toggle("16")
        root.update_idletasks()
        assert "16" in tab.txt_procedure.get("1.0", tk.END)
        tab.chart.toggle("17")
        root.update_idletasks()
        txt = tab.txt_procedure.get("1.0", tk.END)
        assert "16" in txt and "17" in txt
        # Toggling a tooth off and on again must not duplicate it.
        tab.chart.toggle("16")
        tab.chart.toggle("16")
        root.update_idletasks()
        txt = tab.txt_procedure.get("1.0", tk.END)
        assert txt.replace(",", " ").split().count("16") == 1, txt
    finally:
        root.destroy()
        _cleanup(fid)


def test_r16_chart_marks_treated_teeth_and_legend():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_r16_chart_marks_treated_teeth (no display)")
        return
    try:
        _seed_procedure(fid, "16,17")
        tab.load(fid)
        root.update()
        assert tab.chart.get_treated() == ["16", "17"]
        # Treated cell: tick label present, number label still exactly
        # the number (the contrast test pins that).
        assert _labels_with_text(tab.chart.tooth_cells["16"], "✓"), "no tick on 16"
        assert _labels_with_text(tab.chart.tooth_cells["16"], "16")
        assert not _labels_with_text(tab.chart.tooth_cells["11"], "✓")
        # Legend present under the chart.
        assert _labels_with_text(tab.chart.area, "✓ Treated tooth")
    finally:
        root.destroy()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM procedures WHERE patient_file=?", (fid,))
        conn.commit(); conn.close()
        _cleanup(fid)


def test_r16_chart_legend_arabic():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_r16_chart_legend_arabic (no display)")
        return
    root.withdraw()
    try:
        frame = DentalChartFrame(root, lang="ar")
        frame.pack()
        root.update_idletasks()
        assert _labels_with_text(frame.area, "✓ سن تم علاجه")
    finally:
        root.destroy()


def test_r16_chart_tooth_map_still_importable():
    from src.ui.dental_chart import display_order, tooth_image_name, tooth_type_for
    assert tooth_type_for("16") == ("molar", "upper")
    assert tooth_type_for("51") == ("incisor", "upper")
    # Round 33 re-pin: per-tooth asset name (was shared "molar_upper.png").
    assert tooth_image_name("16") == "tooth_16.png"
    assert display_order(["11", "12", "21", "22"], "upper") == \
        ["12", "11", "21", "22"]
