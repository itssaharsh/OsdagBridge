"""Charts embedded in the design report (Section 5.5 and Chapter 7).

Each function draws one figure with matplotlib (Agg canvas, no display
needed), saves it as a vector PDF next to the other report images, and
returns the path for ``\\includegraphics``. Colours, fonts and sizes come from
``styles.CHART``.

* ``utilization_chart``: Utilization Ratio (UR = Demand / Capacity) of every
  check, one panel per primary element (plate girders, deck slab, cross
  bracing, end diaphragms), with a red dashed line at UR = 1.0.
* ``element_summary_chart``: the governing (highest) UR of each element.
* ``steel_tonnage_chart`` and ``concrete_rebar_chart``: material quantities
  from the Chapter 7 bill of materials.

UR axes stop at ``CHART['ur_axis_cap']``: a larger UR, or an infinite one
(zero capacity), is drawn as a hatched failing bar up to the cap and labelled
with its real value, so one extreme value does not flatten the other bars.
Value labels are placed so that they never sit on the UR = 1.0 line.
"""

from __future__ import annotations

import math
import os
import textwrap
from dataclasses import dataclass

# The object-oriented API with an Agg canvas is used instead of pyplot: the
# desktop app draws its own plots with the QtAgg backend and builds the report
# in a worker thread, so the report must not switch the global backend
# (matplotlib.use / pyplot), create pyplot figures off the main thread, or
# change the global rcParams that the app's plots also read.
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .styles import CHART, UR_LIMIT

ELEMENTS = ("Steel Plate Girders", "Concrete Deck Slab", "Cross Bracing", "End Diaphragms")


@dataclass(frozen=True)
class URPoint:
    element: str  # one of ELEMENTS
    check: str    # short label, e.g. "Moment"
    ur: float | None  # None when the check is not available; inf for zero capacity


def _figure(width: float, height: float) -> Figure:
    fig = Figure(figsize=(width, height), dpi=CHART["dpi"])
    FigureCanvasAgg(fig)
    return fig


def _axes_style(ax) -> None:
    """Fonts, spines and colours for one axes, set on the axes itself."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for spine in ax.spines.values():
        spine.set_edgecolor(CHART["edge_color"])
    ax.tick_params(labelsize=CHART["font_size"], colors=CHART["edge_color"])
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(CHART["font_family"])
    ax.xaxis.label.set_fontfamily(CHART["font_family"])
    ax.yaxis.label.set_fontfamily(CHART["font_family"])
    ax.xaxis.label.set_fontsize(CHART["font_size"])
    ax.yaxis.label.set_fontsize(CHART["font_size"])
    ax.title.set_fontfamily(CHART["font_family"])
    ax.title.set_fontsize(CHART["title_size"])


def _finite(value) -> float | None:
    """A quantity that can be drawn: a finite, non-negative number, else None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _ur_value(value) -> float | None:
    """A UR that can be drawn: a non-negative number, ``inf`` included (zero capacity)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or number < 0:
        return None
    return number


def _bar_colors(values):
    return [CHART["missing_color"] if v is None
            else CHART["fail_color"] if v > UR_LIMIT
            else CHART["pass_color"] for v in values]


def _save(fig, out_dir: str, name: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name + ".pdf")
    fig.savefig(path, bbox_inches="tight")
    return path.replace("\\", "/")


def tex_path(path: str, out_dir: str) -> str:
    """Path of a chart for \\includegraphics, relative to the LaTeX build folder.

    The report writes charts into ``<build folder>/images`` and runs pdflatex in
    the build folder, so ``images/<name>.pdf`` always resolves, also when the
    build folder is given as a relative path.
    """
    return os.path.basename(os.path.normpath(out_dir)) + "/" + os.path.basename(path)


def _ur_label(value: float) -> str:
    if math.isinf(value):
        return "∞"
    return f"{value:.2f}"


def _wrap(label: str) -> str:
    return "\n".join(textwrap.wrap(label, CHART["label_wrap_chars"])) or label


def _set_check_labels(ax, labels) -> None:
    """x labels: wrapped and level for up to 4 checks, slanted (not wrapped) for more.

    Wrapped labels must stay level: slanted multi-line labels run into their
    neighbours. Beyond 8 checks the labels are steeper and smaller.
    """
    n = len(labels)
    if n <= 4:
        ax.set_xticklabels([_wrap(label) for label in labels], rotation=0, ha="center",
                           fontfamily=CHART["font_family"], fontsize=CHART["font_size"])
        return
    angle, size = (30, CHART["font_size"]) if n <= 8 else (60, CHART["font_size"] - 1)
    ax.set_xticklabels(labels, rotation=angle, ha="right", rotation_mode="anchor",
                       fontfamily=CHART["font_family"], fontsize=size)


def _label_position(height: float, top: float):
    """(y, va, inside) for a bar's value label so that it stays clear of UR = 1.0.

    The label normally sits just above the bar. When that would put it on the
    UR = 1.0 line, it goes inside a tall enough bar, otherwise just above the
    line.
    """
    pad, text_h = 0.015 * top, 0.075 * top
    y = height + pad
    if y - pad <= UR_LIMIT <= y + text_h + pad:
        if height - pad - text_h >= 0.05 * top:
            return height - pad, "top", True
        return UR_LIMIT + 2 * pad, "bottom", False
    return y, "bottom", False


def _ur_panel(ax, labels, values, title):
    values = [_ur_value(v) for v in values]
    cap = CHART["ur_axis_cap"]
    drawable = [v for v in values if v is not None]
    peak = max([UR_LIMIT] + [min(v, cap) for v in drawable])
    top = peak * 1.22
    heights = [0.0 if v is None else min(v, cap) for v in values]
    capped = [v is not None and v > cap for v in values]
    bars = ax.bar(range(len(labels)), heights, color=_bar_colors(values),
                  edgecolor=CHART["edge_color"], linewidth=CHART["bar_edge_width"], zorder=3)
    for bar, is_capped in zip(bars, capped):
        if is_capped:
            bar.set_hatch(CHART["ur_cap_hatch"])
    ax.axhline(UR_LIMIT, color=CHART["limit_color"], linestyle="--", linewidth=CHART["limit_line_width"],
               zorder=4, label=f"UR = {UR_LIMIT:.1f}")
    ax.set_ylim(0, top)
    ax.set_xticks(range(len(labels)))
    ax.set_ylabel("Utilization Ratio")
    ax.set_title(title, fontweight="bold")
    ax.grid(axis="y", color=CHART["grid_color"], zorder=0)
    for bar, value, height in zip(bars, values, heights):
        text = "n/a" if value is None else _ur_label(value)
        y, va, inside = _label_position(height, top)
        ax.text(bar.get_x() + bar.get_width() / 2, y, text, ha="center", va=va,
                fontsize=CHART["font_size"] - 1, fontfamily=CHART["font_family"],
                color="white" if inside else CHART["edge_color"],
                fontweight="bold" if inside else "normal", zorder=5)
    _axes_style(ax)
    _set_check_labels(ax, labels)  # after _axes_style, which resets the tick label size


def utilization_chart(points: list[URPoint], out_dir: str, name: str = "ur_by_element") -> str | None:
    """2 x 2 panels, one per primary element; returns None if there is no UR at all."""
    if not any(_ur_value(p.ur) is not None for p in points):
        return None
    fig = _figure(CHART["figure_width_in"], 6.6)
    axes = fig.subplots(2, 2)
    for ax, element in zip(axes.flat, ELEMENTS):
        rows = [p for p in points if p.element == element]
        if not rows or all(_ur_value(p.ur) is None for p in rows):
            ax.set_title(element, fontweight="bold")
            ax.text(0.5, 0.5, "No utilization checks\navailable for this element",
                    ha="center", va="center", transform=ax.transAxes, color=CHART["edge_color"],
                    fontfamily=CHART["font_family"], fontsize=CHART["font_size"])
            ax.set_xticks([])
            ax.set_yticks([])
            _axes_style(ax)
            continue
        _ur_panel(ax, [p.check for p in rows], [p.ur for p in rows], element)
    handles, labels = [], []
    for ax in axes.flat:
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            break
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    if handles:
        fig.legend(handles, [labels[0] + " (limit)"], loc="lower center", frameon=False,
                   prop={"family": CHART["font_family"], "size": CHART["font_size"]})
    return _save(fig, out_dir, name)


def element_summary_chart(points: list[URPoint], out_dir: str, name: str = "ur_governing") -> str | None:
    """Governing (maximum) UR of each primary element."""
    governing = []
    for element in ELEMENTS:
        values = [_ur_value(p.ur) for p in points if p.element == element]
        values = [v for v in values if v is not None]
        governing.append(max(values) if values else None)
    if all(v is None for v in governing):
        return None
    fig = _figure(CHART["figure_width_in"], 3.2)
    ax = fig.subplots()
    _ur_panel(ax, list(ELEMENTS), governing, "Governing Utilization Ratio by Element")
    ax.set_xticklabels(ELEMENTS, rotation=0, ha="center", fontfamily=CHART["font_family"])
    ax.legend(loc="upper right", frameon=False,
              prop={"family": CHART["font_family"], "size": CHART["font_size"]})
    fig.tight_layout()
    return _save(fig, out_dir, name)


def steel_tonnage_chart(quantities: dict, out_dir: str, name: str = "steel_tonnage") -> str | None:
    """Structural steel weight (MT) of girders, cross bracing and end diaphragms."""
    girders = _finite(quantities.get("steel_girders_wt_total"))
    bracing_parts = [_finite(quantities.get(k)) for k in
                     ("bracing_top_wt_total", "bracing_bot_wt_total", "bracing_diag_wt_total")]
    bracing = sum(v for v in bracing_parts if v is not None) if any(v is not None for v in bracing_parts) else None
    diaphragms = _finite(quantities.get("end_diaphragm_wt_total"))
    labels = ["Girders", "Cross Bracing", "End Diaphragms"]
    values = [girders, bracing, diaphragms]
    if all(v is None for v in values):
        return None
    fig = _figure(CHART["figure_width_in"] * 0.62, 3.2)
    ax = fig.subplots()
    colors = [CHART["steel_color"] if v is not None else CHART["missing_color"] for v in values]
    heights = [v or 0.0 for v in values]
    bars = ax.bar(labels, heights, color=colors, edgecolor=CHART["edge_color"],
                  linewidth=CHART["bar_edge_width"], zorder=3)
    top = max(heights) * 1.2 or 1.0
    ax.set_ylim(0, top)
    for bar, value in zip(bars, values):
        text = "not in\ntake-off" if value is None else f"{value:.2f} MT"
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + top * 0.02, text,
                ha="center", va="bottom", fontsize=CHART["font_size"] - 1,
                fontfamily=CHART["font_family"])
    included = [label.lower() for label, value in zip(labels, values) if value is not None]
    total = sum(v for v in values if v is not None)
    ax.set_ylabel("Weight (MT)")
    ax.set_title(f"Structural Steel Tonnage\n({' + '.join(included)}: {total:.2f} MT)", fontweight="bold")
    ax.grid(axis="y", color=CHART["grid_color"], zorder=0)
    _axes_style(ax)
    fig.tight_layout()
    return _save(fig, out_dir, name)


def _concrete_mass(quantities: dict, volume: float | None) -> float | None:
    """Deck concrete mass in MT: Table 7.1's weight, else volume x IRC 6 Cl. 203 unit weight."""
    mass = _finite(quantities.get("concrete_deck_wt_total"))
    if mass is not None or volume is None:
        return mass
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    return volume * IRC6_2017.cl_203_dead_load()["concrete_cement_reinforced"]  # t/m3


def concrete_rebar_chart(quantities: dict, out_dir: str, name: str = "concrete_vs_rebar") -> str | None:
    """Deck concrete and reinforcement as mass (MT) on one axis; the steel ratio (kg/m3) in the title."""
    volume = _finite(quantities.get("concrete_deck_vol_total"))
    concrete = _concrete_mass(quantities, volume)
    rebar = _finite(quantities.get("rebar_deck_wt_total"))
    if concrete is None and rebar is None:
        return None
    fig = _figure(CHART["figure_width_in"] * 0.62, 3.2)
    ax = fig.subplots()
    values = [concrete, rebar]
    heights = [v or 0.0 for v in values]
    colors = [CHART["concrete_color"] if concrete is not None else CHART["missing_color"],
              CHART["rebar_color"] if rebar is not None else CHART["missing_color"]]
    bars = ax.bar(["Concrete (deck)", "Reinforcement"], heights, width=CHART["pair_bar_width"], color=colors,
                  edgecolor=CHART["edge_color"], linewidth=CHART["bar_edge_width"], zorder=3)
    top = max(heights) * 1.25 or 1.0
    ax.set_ylim(0, top)
    texts = ["n/a" if concrete is None else f"{concrete:.2f} MT"
             + (f"\n({volume:.2f} m$^3$)" if volume is not None else ""),
             "n/a" if rebar is None else f"{rebar:.2f} MT"]
    for bar, text in zip(bars, texts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + top * 0.02, text,
                ha="center", va="bottom", fontsize=CHART["font_size"] - 1,
                fontfamily=CHART["font_family"])
    ax.set_ylabel("Mass (MT)")
    title = "Deck Concrete vs Reinforcement (mass)"
    if volume and rebar is not None:
        title += f"\nReinforcement ratio {rebar * 1000 / volume:.0f} kg/m$^3$ of concrete"
    ax.set_title(title, fontweight="bold")
    ax.grid(axis="y", color=CHART["grid_color"], zorder=0)
    _axes_style(ax)
    fig.tight_layout()
    return _save(fig, out_dir, name)
