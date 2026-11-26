"""Scrollable page scaffold (R52): the canvas + scrollbar +
content-host pattern the Settings and Statistics pages use,
factored out for the Users page (whose permissions tree alone
needs ~950px at Arabic row heights, so on shorter windows its
bottom used to be cut off with no way to reach it).

Returns (canvas, host): pack content into host; the canvas
tracks the host's size as the scroll region and stretches it
to the canvas width; the mouse wheel scrolls the canvas.
"""
import tkinter as tk
from tkinter import ttk


def make_scroll_page(parent, bg):
    from src.ui.wheel_scroll import bind_canvas_wheel
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    host = tk.Frame(canvas, bg=bg)
    win = canvas.create_window((0, 0), window=host, anchor="nw")
    host.bind("<Configure>",
              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",
                lambda e: canvas.itemconfigure(win, width=e.width))
    bind_canvas_wheel(canvas)
    return canvas, host
