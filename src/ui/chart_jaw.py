"""Round 41 (item 3): jaw-selection shortcut buttons for the
dental chart. Three buttons in the chart header — select ALL
teeth of both jaws, the UPPER jaw only, or the LOWER jaw only —
acting on whichever chart is displayed (permanent or deciduous),
through the chart's existing selection model: the same
`selected` set a tooth click toggles, the same refresh, and the
same on_select callback the session entry reads. Kept out of
dental_chart.py for its 200-line cap. <200 lines."""
import tkinter as tk

from src.config.strings_r41 import r41_t
from src.config.theme import current
from src.ui.rounded import rounded_button
from src.utils.helpers import PERMANENT, DECIDUOUS

SCOPES = ("all", "upper", "lower")


def jaw_sets(chart):
    """(upper, lower) FDI string sets of the chart's CURRENT type,
    sliced exactly as DentalChartFrame.refresh builds the jaws
    (permanent: first 16 upper / last 16 lower; deciduous 10/10)."""
    nums = PERMANENT if chart.tooth_type.get() == "دائم" else DECIDUOUS
    half = len(nums) // 2
    return set(nums[:half]), set(nums[half:])


def select_jaw(chart, scope):
    """Replace the chart selection with one jaw scope ('all' =
    both jaws) and notify exactly like a tooth click does.
    Round 43 (owner): pressing the button whose set is ALREADY the
    exact selection toggles it OFF -- selection cleared, the entry
    tooth box emptied via on_select([]), and the chart's optional
    on_jaw_clear hook (set by the clinical tab) scrubs that set's
    auto-inserted numbers out of the four clinical fields, so no
    manual removal is needed. Any other press sets the scope."""
    upper, lower = jaw_sets(chart)
    target = {"all": upper | lower, "upper": upper,
              "lower": lower}[scope]
    if chart.selected == target:
        chart.selected = set()
        chart.refresh()
        if chart.on_select:
            chart.on_select([], chart.tooth_type.get())
        hook = getattr(chart, "on_jaw_clear", None)
        if hook is not None:
            hook(sorted(target))
        return
    chart.selected = target
    chart.refresh()
    if chart.on_select:
        chart.on_select(sorted(chart.selected), chart.tooth_type.get())


def build_buttons(chart, hdr):
    """The three shortcut buttons, packed into the chart header;
    stored on chart.jaw_buttons {scope: button} for tests."""
    th = current()
    btns = {}
    for scope in SCOPES:
        b = rounded_button(hdr, text=r41_t(f"chart.select_{scope}",
                                           chart.lang),
                           bg=th["card"], fg=th["text"],
                           command=lambda s=scope: select_jaw(chart, s))
        b.pack(side="left", padx=(8, 0))
        btns[scope] = b
    chart.jaw_buttons = btns
    return btns
