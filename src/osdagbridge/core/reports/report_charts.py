"""Charts embedded in the design report (Section 5.5 and Chapter 7).

Each function draws one figure with matplotlib (Agg backend, no display
needed), saves it as a vector PDF next to the other report images, and
returns the path for ``\\includegraphics``. Colours, fonts and sizes come from
``styles.CHART``.

* ``utilization_chart``: Utilization Ratio (UR = Demand / Capacity) of every
  check, one panel per primary element (plate girders, deck slab, cross
  bracing, end diaphragms), with a red dashed line at UR = 1.0.
* ``element_summary_chart``: the governing (highest) UR of each element.
* ``steel_tonnage_chart`` and ``concrete_rebar_chart``: material quantities
  from the Chapter 7 bill of materials.
"""

from __future__ import annotations

import math
import os
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
    ur: float | None  # None when the check is not available


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
    """A UR or quantity that can be drawn: a finite, non-negative number, else None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


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
    the build folder, so ``images/<name>.pdf`` always resolves. An absolute path
    can break pdflatex: a relative build folder, or a Windows temp folder with a
    "~" short name (``C:/Users/JOHNDO~1/...``), where "~" is a LaTeX active
    character.
    """
    return os.path.basename(os.path.normpath(out_dir)) + "/" + os.path.basename(path)


def _ur_panel(ax, labels, values, title):
    values = [_finite(v) for v in values]
    heights = [v if v is not None else 0.0 for v in values]
    bars = ax.bar(range(len(labels)), heights, color=_bar_colors(values),
                  edgecolor=CHART["edge_color"], linewidth=0.5, zorder=3)
    ax.axhline(UR_LIMIT, color=CHART["limit_color"], linestyle="--", linewidth=1.2, zorder=4,
               label=f"UR = {UR_LIMIT:.1f}")
    top = max([UR_LIMIT] + [v for v in values if v is not None]) * 1.18
    ax.set_ylim(0, top)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Utilization Ratio")
    ax.set_title(title, fontweight="bold")
    ax.grid(axis="y", color=CHART["grid_color"], zorder=0)
    for bar, value in zip(bars, values):
        text = "n/a" if value is None else f"{value:.2f}"
        y = bar.get_height() if value is not None else 0.0
        ax.text(bar.get_x() + bar.get_width() / 2, y + top * 0.015, text,
                ha="center", va="bottom", fontsize=CHART["font_size"] - 1,
                fontfamily=CHART["font_family"])
    _axes_style(ax)


def utilization_chart(points: list[URPoint], out_dir: str, name: str = "ur_by_element") -> str | None:
    """2 x 2 panels, one per primary element; returns None if there is no UR at all."""
    if not any(_finite(p.ur) is not None for p in points):
        return None
    fig = _figure(CHART["figure_width_in"], 6.4)
    axes = fig.subplots(2, 2)
    for ax, element in zip(axes.flat, ELEMENTS):
        rows = [p for p in points if p.element == element]
        if not rows or all(_finite(p.ur) is None for p in rows):
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
        values = [_finite(p.ur) for p in points if p.element == element]
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


def _number(value) -> float | None:
    return _finite(value)


def steel_tonnage_chart(quantities: dict, out_dir: str, name: str = "steel_tonnage") -> str | None:
    """Structural steel weight (MT) of girders, cross bracing and end diaphragms."""
    girders = _number(quantities.get("steel_girders_wt_total"))
    bracing_parts = [_number(quantities.get(k)) for k in
                     ("bracing_top_wt_total", "bracing_bot_wt_total", "bracing_diag_wt_total")]
    bracing = sum(v for v in bracing_parts if v is not None) if any(v is not None for v in bracing_parts) else None
    diaphragms = _number(quantities.get("end_diaphragm_wt_total"))
    labels = ["Girders", "Cross Bracing", "End Diaphragms"]
    values = [girders, bracing, diaphragms]
    if all(v is None for v in values):
        return None
    fig = _figure(CHART["figure_width_in"] * 0.62, 3.2)
    ax = fig.subplots()
    colors = [CHART["steel_color"] if v is not None else CHART["missing_color"] for v in values]
    heights = [v or 0.0 for v in values]
    bars = ax.bar(labels, heights, color=colors, edgecolor=CHART["edge_color"], linewidth=0.5, zorder=3)
    top = max(heights) * 1.2 or 1.0
    ax.set_ylim(0, top)
    for bar, value in zip(bars, values):
        text = "not in\ntake-off" if value is None else f"{value:.2f} MT"
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + top * 0.02, text,
                ha="center", va="bottom", fontsize=CHART["font_size"] - 1,
                fontfamily=CHART["font_family"])
    total = sum(v for v in values if v is not None)
    ax.set_ylabel("Weight (MT)")
    ax.set_title(f"Structural Steel Tonnage (total {total:.2f} MT)", fontweight="bold")
    ax.grid(axis="y", color=CHART["grid_color"], zorder=0)
    _axes_style(ax)
    fig.tight_layout()
    return _save(fig, out_dir, name)


def concrete_rebar_chart(quantities: dict, out_dir: str, name: str = "concrete_vs_rebar") -> str | None:
    """Deck concrete volume (m3) next to reinforcement weight (MT), each on its own axis."""
    concrete = _number(quantities.get("concrete_deck_vol_total"))
    rebar = _number(quantities.get("rebar_deck_wt_total"))
    if concrete is None and rebar is None:
        return None
    fig = _figure(CHART["figure_width_in"] * 0.62, 3.2)
    ax_c = fig.subplots()
    ax_r = ax_c.twinx()
    ax_r.spines["right"].set_visible(True)
    c_val, r_val = concrete or 0.0, rebar or 0.0
    bc = ax_c.bar([0], [c_val], width=0.5, color=CHART["concrete_color"],
                  edgecolor=CHART["edge_color"], linewidth=0.5, zorder=3)
    br = ax_r.bar([1], [r_val], width=0.5, color=CHART["rebar_color"],
                  edgecolor=CHART["edge_color"], linewidth=0.5, zorder=3)
    ax_c.set_ylim(0, (c_val * 1.25) or 1.0)
    ax_r.set_ylim(0, (r_val * 1.25) or 1.0)
    ax_c.set_xticks([0, 1])
    ax_c.set_xticklabels(["Concrete (deck)", "Reinforcement"])
    ax_c.set_ylabel("Concrete volume (m$^3$)")
    ax_r.set_ylabel("Reinforcement weight (MT)")
    ax_c.text(0, c_val * 1.03, "n/a" if concrete is None else f"{c_val:.2f} m$^3$", ha="center", va="bottom",
              fontsize=CHART["font_size"], fontfamily=CHART["font_family"])
    ax_r.text(1, r_val * 1.03, "n/a" if rebar is None else f"{r_val:.2f} MT", ha="center", va="bottom",
              fontsize=CHART["font_size"], fontfamily=CHART["font_family"])
    title = "Deck Concrete vs Reinforcement"
    if concrete and rebar:
        title += f"\n({rebar * 1000 / concrete:.0f} kg of steel per m$^3$ of concrete)"
    ax_c.set_title(title, fontweight="bold")
    ax_c.grid(axis="y", color=CHART["grid_color"], zorder=0)
    _ = (bc, br)
    _axes_style(ax_c)
    _axes_style(ax_r)
    ax_r.spines["right"].set_visible(True)
    fig.tight_layout()
    return _save(fig, out_dir, name)
