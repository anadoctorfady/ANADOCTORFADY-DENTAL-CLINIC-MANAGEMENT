"""Print preview window (round 16, worker C; r18 invoice; r24 referral).

show_print_preview(parent, title, build_pdf_fn, lang): build_pdf_fn(lang)
-> pathlib.Path to a PDF in the requested single language (the app
language by default). The preview opens BEFORE anything is saved or
printed and offers Print (system print), Save PDF and Cancel. No PDF
renderer: the preview shows the report's plain-text content — via the
optional preview_text(lang) callable, else extraction from the PDF
itself. `header_extra(win)` (round 18): a caller's extra control row
under the language row (the invoice's Detailed / Summary). <200 lines.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from src.config.strings_r16_print import pp_t
from src.config.theme import current, finance_current
from src.reports.pdf_common import reports_dir, clinic_name as _clinic_name
from src.reports.report_files import (extract_pdf_text, pdf_page_count, print_pdf_file, save_pdf_copy)
from src.ui.rounded import rounded_button


class PrintPreview(tk.Toplevel):
    """Modal preview: language choice, text, page info, Print/Save/Cancel."""

    def __init__(self, parent, title, build_pdf_fn, lang="en",
                 preview_text=None, header_extra=None):
        th = current()
        super().__init__(parent)
        self._build = build_pdf_fn
        self._preview_text = preview_text
        self.lang_var = tk.StringVar(value=lang or "en")
        self.pdf_path = None
        self.title(f"{pp_t('pp.title', self.lang_var.get())} — {title}")
        self.configure(bg=th["bg"]); self.geometry("640x560"); self.transient(parent)
        top = tk.Frame(self, bg=th["bg"])
        top.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(top, text=pp_t("pp.language", self.lang_var.get()),
                 bg=th["bg"], fg=th["text"],
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        for code, label in (("en", "English"), ("ar", "العربية")):
            tk.Radiobutton(top, text=label, variable=self.lang_var,
                           value=code, bg=th["bg"], fg=th["text"],
                           selectcolor=th["card"],
                           command=self._on_lang).pack(side="left", padx=6)
        if header_extra is not None:
            header_extra(self)  # round 18: caller's extra control row
        self.info = tk.Label(self, bg=th["bg"], fg=th["muted"], font=("Segoe UI", 9))
        self.info.pack(fill="x", padx=12)
        # Buttons FIRST (side=bottom) or the text frame squeezes them.
        btns = tk.Frame(self, bg=th["bg"])
        btns.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        th_btn = finance_current()["btn_text"]
        rounded_button(btns, text=pp_t("pp.print", self.lang_var.get()),
                       bg=th["accent"], fg=th_btn,
                       command=self._on_print).pack(side="left", padx=(0, 6))
        rounded_button(btns, text=pp_t("pp.save_pdf", self.lang_var.get()),
                       bg=th["accent"], fg=th_btn,
                       command=self._on_save).pack(side="left", padx=6)
        rounded_button(btns, text=pp_t("pp.cancel", self.lang_var.get()),
                       bg=th["muted"], fg=th_btn,
                       command=self.destroy).pack(side="right")
        wrap = tk.Frame(self, bg=th["bg"])
        wrap.pack(fill="both", expand=True, padx=12, pady=6)
        bar = tk.Scrollbar(wrap)
        bar.pack(side="right", fill="y")
        self.text = tk.Text(wrap, bg=th["panel"], fg=th["text"],
                            font=("Segoe UI", 10), wrap="word",
                            yscrollcommand=bar.set, state="disabled")
        self.text.pack(side="left", fill="both", expand=True)
        bar.config(command=self.text.yview)
        self._rebuild(self.lang_var.get())
        self.grab_set()

    def _lines(self, lang):
        """Preview lines: caller's text rendering, else PDF extraction."""
        if callable(self._preview_text):
            try:
                out = self._preview_text(lang)
                if isinstance(out, str):
                    return out.splitlines()
                return [" — ".join(str(x) for x in item if x)
                        if isinstance(item, (list, tuple)) else str(item)
                        for item in out]
            except Exception:
                pass
        if self.pdf_path and Path(self.pdf_path).exists():
            txt = extract_pdf_text(self.pdf_path)
            if txt.strip():
                return txt.splitlines()
        return [pp_t("pp.no_text", lang)]

    def _rebuild(self, lang):
        """(Re)generate the PDF in `lang` and refresh text + info."""
        try:
            self.pdf_path = Path(self._build(lang)); err = None
        except Exception as e:
            self.pdf_path = None; err = str(e)
        lines = [f"{pp_t('pp.build_failed', lang)} {err}"] if err else self._lines(lang)
        self.text.configure(state="normal"); self.text.delete("1.0", tk.END)
        self.text.insert("1.0", "\n".join(lines)); self.text.configure(state="disabled")
        if self.pdf_path and Path(self.pdf_path).exists():
            kb = max(1, Path(self.pdf_path).stat().st_size // 1024)
            self.info.configure(text=pp_t("pp.info", lang).format(pages=pdf_page_count(self.pdf_path), kb=kb))
        else:
            self.info.configure(text="")

    def _on_lang(self): self._rebuild(self.lang_var.get())

    def _on_print(self):
        if not self.pdf_path: return
        status, msg = print_pdf_file(self.pdf_path); lang = self.lang_var.get()
        if status == "ok":
            messagebox.showinfo(pp_t("pp.print_done", lang), Path(self.pdf_path).name); self.destroy()  # R25: file NAME only, never the storage path
        elif status == "no-printer":
            messagebox.showwarning(pp_t("pp.print_failed", lang), pp_t("pp.no_printer", lang))
        else:
            messagebox.showerror(pp_t("pp.print_failed", lang), msg or "")

    def _on_save(self):
        if not self.pdf_path: return
        lang = self.lang_var.get()
        dest = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialdir=str(reports_dir()), initialfile=Path(self.pdf_path).name)
        if not dest: return
        try:
            out = save_pdf_copy(self.pdf_path, dest_path=dest)
        except Exception as e:
            messagebox.showerror(pp_t("pp.print_failed", lang), str(e)); return
        messagebox.showinfo(pp_t("pp.saved", lang), Path(out).name); self.destroy()  # R25: file NAME only, never the storage path


def show_print_preview(parent, title, build_pdf_fn, lang="en",
                       preview_text=None, header_extra=None):
    """Open the print preview window; returns the Toplevel."""
    return PrintPreview(parent, title, build_pdf_fn, lang, preview_text=preview_text, header_extra=header_extra)


def open_patient_preview(app):
    """Patient-PDF preview for App.print_pdf (temp folder)."""
    import tempfile
    from src.models.database import get_connection
    from src.reports.pdf_report import create_patient_pdf
    from src.reports.report_text import patient_preview_lines
    fid = app.current_patient["file_number"]
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
    pat = dict(cur.fetchone())
    def all_rows(tbl):
        cur.execute(f"SELECT * FROM {tbl} WHERE patient_file=?", (fid,)); return [dict(r) for r in cur.fetchall()]
    data = {k: all_rows(k) for k in ["complaints", "diagnoses", "procedures", "financials", "xrays"]}
    conn.close()
    tmp = tempfile.mkdtemp(prefix="anadoctorfady_preview_"); teeth = app.chart_teeth()
    def build(lang): return create_patient_pdf(pat, data["complaints"], data["diagnoses"], data["procedures"], data["financials"], data["xrays"], language=lang, user_name=app.current_user, tooth_selection=teeth, out_dir=tmp)
    def lines(lang): return patient_preview_lines(pat, data["complaints"], data["diagnoses"], data["procedures"], data["financials"], data["xrays"], language=lang, tooth_selection=teeth)
    return show_print_preview(app, pat.get("full_name", ""), build,
                              getattr(app, "lang", "en"), preview_text=lines)


def open_invoice_preview(app, parent=None):
    """Round 18 (item 8): invoice preview — round-16 preview + a
    Detailed / Summary choice row (header_extra); temp folder."""
    import tempfile
    from src.config.strings_r18_invoice import inv_t
    from src.reports.invoice_pdf import (build_invoice_pdf,
                                         invoice_preview_lines, invoice_data)
    fid = app.current_patient["file_number"]
    pat, rows, totals = invoice_data(fid)
    lang0 = getattr(app, "lang", "en"); clinic = _clinic_name()
    state = {"kind": "detailed"}
    tmp = tempfile.mkdtemp(prefix="anadoctorfady_invoice_")
    def build(lang): return build_invoice_pdf(pat, rows, totals, state["kind"], lang, clinic, tmp, user_name=getattr(app, "current_user", "fady"))
    def lines(lang): return invoice_preview_lines(pat, rows, totals, state["kind"], lang, clinic)
    def extra(win):
        th = current(); row = tk.Frame(win, bg=th["bg"]); row.pack(fill="x", padx=12, pady=(2, 0))
        tk.Label(row, text=inv_t("inv.kind", lang0), bg=th["bg"], fg=th["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        var = tk.StringVar(master=win, value="detailed"); win.kind_var = var
        for val in ("detailed", "summary"):
            tk.Radiobutton(row, text=inv_t("inv." + val, lang0), variable=var, value=val, bg=th["bg"], fg=th["text"], selectcolor=th["card"],
                           command=lambda: (state.__setitem__("kind", var.get()), win._rebuild(win.lang_var.get()))).pack(side="left", padx=6)
    title = f"{inv_t('inv.title', lang0)} — {pat.get('full_name', '')}"
    return show_print_preview(parent or app, title, build, lang0, preview_text=lines, header_extra=extra)


def open_referral_preview(app, referral_id, parent=None):
    """Round 24 (item 1): referral preview — the round-16 preview
    flow (language defaults to the app language; Print / Save PDF /
    Cancel); temp folder until Save/Print. None for an unknown id."""
    import tempfile
    from src.config.strings_r19_referral import tr as _rt
    from src.reports.referral_pdf import build_referral_pdf, referral_data, referral_preview_lines
    data = referral_data(referral_id)
    if data is None:
        return None
    pat, ref = data
    lang0 = getattr(app, "lang", "en")
    tmp = tempfile.mkdtemp(prefix="anadoctorfady_referral_")
    def build(lang): return build_referral_pdf(pat, ref, lang=lang, out_path=tmp, user_name=getattr(app, "current_user", "fady"))
    def lines(lang): return referral_preview_lines(pat, ref, lang)
    title = f"{_rt('refer.pdf_title', lang0)} — {pat.get('full_name', '')}"
    return show_print_preview(parent or app, title, build, lang0, preview_text=lines)
