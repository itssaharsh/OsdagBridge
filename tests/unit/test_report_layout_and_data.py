"""Tests for the table heads, table widths, group labels, charts and live-load data of the report."""

import math
import re
import shutil
import subprocess

import pytest
from matplotlib.figure import Figure

from osdagbridge.core.reports import chap5, chap7, latex_tables, report_charts, styles
from osdagbridge.core.reports.chap2 import _girder_dim_mm
from osdagbridge.core.reports.chap3 import _VEHICLE_KEYS, _is_selected, _live_load_tables
from osdagbridge.core.reports.report_utils import _fig_embed, _fig_or_placeholder
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.codes.keyfile import kN
from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV, KEY_CARRIAGEWAY_WIDTH, KEY_LL_CUSTOM_VEHICLES, KEY_LL_ECCENTRICITY,
    KEY_LL_IRC_70R_TRACKED, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE, KEY_LL_IRC_CLASS_SV, KEY_MP_GIRDER_DEPTH, KEY_SPAN,
)

HEADER = r"\textbf{Girder} & \textbf{Check} & \textbf{Status} \\[\rowpad]"
ROWS = r"""G1 & Web & PASS \\[\rowpad]
\hline
G2 & Flange & PASS \\[\rowpad]
\hline"""


def _longtable(head, rows=ROWS, spec=r"|C{2.5cm}|L{3cm}|C{2cm}|"):
    return r"\begin{longtable}{" + spec + "}\n" + head + "\n" + rows + "\n" + r"\end{longtable}"


# ── Table heads (scope item 1) ───────────────────────────────────────────────

def test_empty_continued_head_is_treated_as_missing():
    # Table 2.8 had \endfirsthead immediately followed by an empty \endhead.
    head = r"\caption{\textbf{Girder Restraint}}\\" + "\n\\hline\n" + HEADER + "\n\\hline\n\\endfirsthead\n\\endhead\n"
    out = latex_tables.finalize_tables(_longtable(head))
    first, rest = out.split(r"\endfirsthead")
    continued = rest.split(r"\endhead")[0]
    assert HEADER in first and HEADER in continued
    assert r"\caption[]{\textbf{Girder Restraint}~(continued)}\\" in continued
    assert r"\continuednote" in out and r"\endfoot" in out


def test_own_head_without_continued_caption_gets_caption_and_foot():
    # Table 4.1 defines both heads itself but no "(continued)" caption or foot.
    head = (r"\caption{\textbf{Summary of Maximum Demands}}\\" "\n\\hline\n" + HEADER + "\n\\hline\n\\endfirsthead\n"
            "\\hline\n" + HEADER + "\n\\hline\n\\endhead\n")
    out = latex_tables.finalize_tables(_longtable(head))
    continued = out.split(r"\endfirsthead")[1].split(r"\endhead")[0]
    assert r"\caption[]{\textbf{Summary of Maximum Demands}~(continued)}\\" in continued
    assert out.count(HEADER) == 2  # the table's own heads, not a third copy
    assert r"\multicolumn{3}{r}{\continuednote}\\" in out and r"\endlastfoot" in out
    assert latex_tables.finalize_tables(out) == out


def test_long_title_is_shortened_in_the_continued_caption():
    title = r"\textbf{Girder Section Properties (Final Optimized / User-selected)}"
    short = latex_tables.continued_caption(title)
    assert short == r"\textbf{Girder Section Properties}~(continued)"
    long_title = r"\textbf{" + "Very Long Words " * 8 + "}"
    cut = latex_tables.continued_caption(long_title)
    assert cut.endswith(r"\ldots}~(continued)")
    assert latex_tables._visible_length(cut) + len("Table 5.12: ") <= styles.TABLE["continued_caption_chars"]
    assert latex_tables.continued_caption(r"\textbf{Stiffener Checks}") == r"\textbf{Stiffener Checks}~(continued)"


def test_caption_ending_in_row_break_does_not_stop_the_report():
    tex = r"\begin{longtable}{|c|}\caption{Title\\}\hline \textbf{a}\\ \hline x\\ \hline\end{longtable}"
    out = latex_tables.finalize_tables(tex)
    assert r"\endhead" in out and out.count(r"\textbf{a}") == 2
    assert latex_tables._read_group(r"{a\\}b", 0) == 5
    assert latex_tables._read_group(r"{a\}b}", 0) == 6


def test_a_table_that_cannot_be_parsed_is_left_unchanged():
    broken = r"\begin{longtable}{|c|}\caption{Broken {title}\hline \textbf{a}\\ \hline x\\ \hline\end{longtable}"
    good = _longtable(r"\caption{\textbf{Good}}" + "\n\\hline\n" + HEADER + "\n\\hline")
    out = latex_tables.finalize_tables(broken + "\n" + good)
    assert out.startswith(broken)
    assert r"\caption[]{\textbf{Good}~(continued)}\\" in out


def test_header_needs_every_cell_bold():
    assert latex_tables.is_bold_header(HEADER)
    assert latex_tables.is_bold_header(r"\textbf{} & \textbf{Element} \\")
    assert latex_tables.is_bold_header(
        r"\multirow{2}{*}{\makecell{\textbf{Load Case/}\\\textbf{Comb.}}} & \multicolumn{2}{c|}{\textbf{BM}}\\"
        r" \cline{2-3} & \makecell{\textbf{Max}\\\textbf{(kNm)}} & \textbf{Girder}\\")
    assert not latex_tables.is_bold_header(r"\textbf{Main reinforcement} & 12.5 mm \\")
    # A key/value table whose first data row starts with a bold cell keeps it as data.
    table = _longtable(r"\caption{\textbf{Deck}}" "\n\\hline\n" r"\textbf{Span} & 2100 mm & ok \\" "\n\\hline")
    out = latex_tables.repeat_longtable_headers(table)
    assert out.count("2100 mm") == 1


def test_column_count_expands_repeats():
    assert latex_tables.column_count(r"|*{3}{c|}") == 3
    assert latex_tables.column_count(r"|l|*{2}{p{2cm}|}r|") == 4


def test_header_less_table_keeps_its_top_rule_in_the_head():
    # The body must start with a row, so longtable's start check measures it.
    table = _longtable(r"\caption{\textbf{Stiffener Design Summary}}" "\n\\hline\n" + ROWS.split("\\hline")[0])
    table = table.replace(r"\begin{longtable}{|C{2.5cm}|L{3cm}|C{2cm}|}", r"\begin{longtable}{|C{2.5cm}|L{3cm}|C{2cm}|}")
    out = latex_tables.repeat_longtable_headers(table.replace("G1 & Web", "G1 & \\textnormal{Web}"))
    body = out.split(r"\endlastfoot")[1]
    assert body.lstrip().startswith("G1")
    assert out.split(r"\endfirsthead")[0].rstrip().endswith(r"\hline")


# ── Table widths (scope item 2) ──────────────────────────────────────────────

def _total_width(spec, col_sep):
    widths = [styles.length_pt(w) for w in re.findall(r"[pCLR]\{([\d.]+cm)\}", spec)]
    return sum(widths) + len(widths) * 2 * col_sep + spec.count("|") * styles.length_pt(styles.TABLE["rule_width"])


def test_text_width_and_head_height_come_from_the_page_settings():
    assert styles.text_width_pt() == pytest.approx(452.97, abs=0.05)  # A4, 1in side margins
    assert styles.PAGE["head_height"] == "18pt"


def test_too_wide_tables_are_scaled_to_the_text_width():
    spec = r"|L{4.6cm}|C{2.2cm}|C{3.6cm}|L{5.0cm}|"
    sep = styles.col_sep_presets()["default"]
    assert _total_width(spec, sep) > styles.text_width_pt()
    fitted = latex_tables.fit_column_spec(spec, sep)
    assert _total_width(fitted, sep) <= styles.text_width_pt()
    old = [float(w) for w in re.findall(r"\{([\d.]+)cm\}", spec)]
    new = [float(w) for w in re.findall(r"\{([\d.]+)cm\}", fitted)]
    assert [round(n / o, 2) for n, o in zip(new, old)] == [round(new[0] / old[0], 2)] * 4  # proportional
    assert latex_tables.fit_column_spec(r"|L{5.5cm}|L{8.5cm}|", sep) == r"|L{5.5cm}|L{8.5cm}|"
    assert latex_tables.fit_column_spec(r"|c|c|p{13cm}|", sep) == r"|c|c|p{13cm}|"  # natural widths: unknown


def test_fit_uses_the_active_column_padding_preset():
    spec = r"|C{1.6cm}|C{3.6cm}|C{2.4cm}|C{2.0cm}|C{2.1cm}|C{1.7cm}|C{1.5cm}|"
    default = latex_tables.fit_tables_to_width(r"\begin{longtable}{" + spec + "}x\\end{longtable}")
    compact = latex_tables.fit_tables_to_width(
        r"\begingroup\compactcols\begin{longtable}{" + spec + "}x\\end{longtable}\\endgroup"
        r"\begin{longtable}{" + spec + "}x\\end{longtable}")
    d_spec = re.search(r"longtable\}\{([^\n]*?)\}x", default).group(1)
    c_spec = re.search(r"longtable\}\{([^\n]*?)\}x", compact).group(1)
    presets = styles.col_sep_presets()
    assert _total_width(d_spec, presets["default"]) <= styles.text_width_pt()
    assert _total_width(c_spec, presets["compactcols"]) <= styles.text_width_pt()
    assert _total_width(c_spec, presets["default"]) > _total_width(d_spec, presets["default"])
    # After \endgroup the default padding applies again.
    assert compact.rstrip().endswith(r"\begin{longtable}{" + d_spec + r"}x\end{longtable}")


# ── Group labels (scope item 2) ──────────────────────────────────────────────

def _group(label, n):
    rows = [r"\multirow{" + str(n) + r"}{*}{\makecell{" + label + r"}} & row 0 & v \\[\rowpad]"]
    rows += [r"\cline{2-3}" + "\n" + f" & row {k} & v " + r"\\[\rowpad]" for k in range(1, n)]
    return "\n".join(rows) + "\n\\hline"


def test_group_labels_are_top_aligned_and_short_groups_kept_together():
    small = _group("G1", 3)
    big = _group("G2", styles.TABLE["keep_together_rows"] + 1)
    out = latex_tables.keep_row_groups_together(_longtable(r"\hline" "\n" + HEADER + "\n\\hline", small + "\n" + big))
    assert r"\multirow[t]{3}" in out and r"\multirow[t]{" + str(styles.TABLE["keep_together_rows"] + 1) in out
    g1, g2 = out.split("G2")
    assert r"\groupcline{2-3}" in g1 and r"\\*[\rowpad]" in g1
    assert r"\groupcline" not in g2 and r"\\*" not in g2  # a tall group may break


@pytest.mark.skipif(not (shutil.which("pdflatex") and shutil.which("pdftotext")), reason="needs pdflatex and pdftotext")
def test_group_taller_than_a_page_keeps_its_label_out_of_the_footer(tmp_path):
    from osdagbridge.core.reports.report_generator import preamble
    table = _longtable(r"\caption{\textbf{Tall Group}}" "\n\\hline\n" + HEADER + "\n\\hline", _group("G1", 47))
    tex = preamble("Test", "T-1", "2026-11-24") + latex_tables.finalize_tables(table) + "\n\\end{document}\n"
    (tmp_path / "t.tex").write_text(tex)
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "t.tex"], cwd=tmp_path, capture_output=True, timeout=120)
    bbox = subprocess.run(["pdftotext", "-bbox", str(tmp_path / "t.pdf"), "-"], capture_output=True, text=True).stdout
    pages = bbox.split("<page ")[1:]
    assert len(pages) >= 2  # the group really is taller than one page
    text_bottom = 841.89 - styles.length_pt(styles.PAGE["margin_bottom"]) * 72 / 72.27
    labels = []
    for pno, page in enumerate(pages, 1):
        words = [(float(y0), float(y1), w) for y0, y1, w in
                 re.findall(r'yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">([^<]*)</word>', page)]
        footer_top = min((y0 for y0, _y1, w in words if w == "Osdag"), default=1e9)
        for y0, y1, w in words:
            if w == "G1":
                labels.append((pno, y0))
            if y0 < footer_top - 4 and w not in ("*", "Software", "default", "value"):
                assert y1 <= text_bottom + 4, (pno, w, y1)  # nothing below the text block
        if pno == 1:
            first_row = min((y0 for y0, _y1, w in words if w == "row"), default=None)
    assert first_row is not None, "the table must start on the first page"
    assert len(labels) == 1 and labels[0][0] == 1
    assert abs(labels[0][1] - first_row) < 3  # printed in the group's first row


# ── Figures and charts (scope items 4 and 5) ─────────────────────────────────

def test_chart_figures_are_numbered_and_labelled():
    tex = _fig_embed("images/x.pdf", "Caption text", label="fig:x", numbered=True)
    assert r"\caption{Caption text}\label{fig:x}" in tex and r"\caption*" not in tex
    assert r"\caption*{Plot}" in _fig_embed("images/p.png", "Plot")
    assert _fig_embed(None, "Missing").rstrip().endswith(r"\par")
    assert r"\par" in _fig_or_placeholder(None, "Missing")


def test_ur_chart_captions_reference_the_summary_table(tmp_path):
    points = [report_charts.URPoint("Steel Plate Girders", "Moment", 0.5)]
    tex = chap5._ur_charts(points, str(tmp_path / "images"))
    assert tex.count(r"Table~\ref{tab:overall-summary}") == 2
    assert r"\label{fig:ur-governing}" in tex and r"\label{fig:ur-by-check}" in tex


def test_a_failing_chart_is_left_out_and_the_report_goes_on(tmp_path, monkeypatch):
    def broken(*_args, **_kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(chap7, "steel_tonnage_chart", broken)
    tex = chap7._quantity_charts({"concrete_deck_vol_total": "63", "rebar_deck_wt_total": "7.56"},
                                 str(tmp_path / "images"))
    assert "fig:concrete-rebar" in tex and "fig:steel-tonnage" not in tex
    monkeypatch.setattr(chap5, "element_summary_chart", broken)
    tex = chap5._ur_charts([report_charts.URPoint("Cross Bracing", "Tension", 0.3)], str(tmp_path / "images"))
    assert "fig:ur-by-check" in tex and "fig:ur-governing" not in tex


def _panel(values):
    fig = Figure()
    ax = fig.subplots()
    report_charts._ur_panel(ax, [f"c{i}" for i in range(len(values))], values, "t")
    return ax


def test_ur_axis_is_capped_and_extreme_values_keep_their_label():
    ax = _panel([0.4, 0.8, 1e6, math.inf])
    cap = styles.CHART["ur_axis_cap"]
    assert ax.get_ylim()[1] == pytest.approx(cap * 1.22)
    bars = ax.patches
    assert bars[2].get_height() == cap and bars[3].get_height() == cap
    assert bars[2].get_hatch() and bars[3].get_hatch() and not bars[0].get_hatch()
    texts = [t.get_text() for t in ax.texts]
    assert "1000000.00" in texts and "\u221e" in texts and "0.80" in texts


def test_value_labels_stay_off_the_limit_line():
    for value in (0.9, 0.94, 0.97, 1.0, 1.03):
        ax = _panel([value, 0.2])
        top = ax.get_ylim()[1]
        label = next(t for t in ax.texts if t.get_text() == f"{value:.2f}")
        y = label.get_position()[1]
        if label.get_va() == "top":  # inside the bar, below its top
            assert y < value and y - 0.075 * top > 0
        else:
            assert not (y <= styles.UR_LIMIT <= y + 0.075 * top)


def test_infinite_ur_is_a_failing_bar_not_missing(tmp_path):
    only_inf = [report_charts.URPoint("End Diaphragms", "Moment", math.inf)]
    assert report_charts.utilization_chart(only_inf, str(tmp_path))
    assert report_charts._bar_colors([math.inf]) == [styles.CHART["fail_color"]]


def test_concrete_and_reinforcement_share_one_mass_axis(tmp_path, monkeypatch):
    figures = []
    monkeypatch.setattr(report_charts, "_save", lambda fig, out_dir, name: figures.append(fig) or "x.pdf")
    report_charts.concrete_rebar_chart({"concrete_deck_vol_total": "63.00", "concrete_deck_wt_total": "157.50",
                                        "rebar_deck_wt_total": "7.56"}, str(tmp_path))
    (ax,) = figures[0].axes  # one axis, no twin
    heights = [bar.get_height() for bar in ax.patches]
    assert heights == [157.5, 7.56]
    assert "120 kg/m" in ax.get_title()
    # Without the take-off weight, the mass comes from the IRC 6 Cl. 203 unit weight.
    assert report_charts._concrete_mass({}, 10.0) == pytest.approx(25.0)


def test_steel_tonnage_title_names_what_the_total_covers(tmp_path, monkeypatch):
    figures = []
    monkeypatch.setattr(report_charts, "_save", lambda fig, out_dir, name: figures.append(fig) or "x.pdf")
    report_charts.steel_tonnage_chart({"steel_girders_wt_total": "32.89", "bracing_diag_wt_total": "0.47"},
                                      str(tmp_path))
    assert "girders + cross bracing: 33.36 MT" in figures[0].axes[0].get_title()


# ── Load and geometry tables (scope item 3) ──────────────────────────────────

def test_braking_force_counts_every_lane_beyond_two():
    class_a = sum(IRC6_2017.cl_204_1_ClassA_vehicle()["wheel_loads"])
    class_70r = sum(IRC6_2017.cl_204_1_Class70R_vehicle_wheel()["wheel_loads"])
    for lanes in (1, 2, 3, 4, 6):
        expected = 0.20 * class_a + 0.05 * class_70r * max(lanes - 2, 0)
        assert IRC6_2017.cl_211_2_braking_force(lanes) == pytest.approx(round(expected, 3))


def _rows(tex):
    return [[c.strip() for c in line.split("&")] for line in tex.splitlines() if " & " in line and "textbf" not in line]


def test_vehicle_rows_follow_the_loading_tab_labels_order_and_parsing():
    inputs = {KEY_SPAN: 30, KEY_CARRIAGEWAY_WIDTH: 7.5, KEY_LL_IRC_CLASS_FATIGUE: "yes",
              KEY_LL_IRC_70R_WHEELED: True, KEY_LL_IRC_CLASS_A: "True", KEY_LL_IRC_AA_WHEELED: "False",
              KEY_LL_IRC_70R_TRACKED: "No", KEY_LL_IRC_CLASS_SV: 0,
              KEY_LL_CUSTOM_VEHICLES: [{"name": "Class X Crane"}]}
    tex = _live_load_tables(inputs)
    names = [r[0] for r in _rows(tex) if r[0].startswith("Class")]
    assert names == ["Class A", "Class 70R Wheeled", "Class Fatigue", "Class X Crane (custom)"]
    assert [label for _k, label, _t, _c in _VEHICLE_KEYS] == [
        "Class A", "Class AA Wheeled", "Class AA Tracked", "Class 70R Wheeled", "Class 70R Tracked",
        "Class 70R Bogie", "Class SV", "Class Fatigue"]
    assert not _is_selected({"k": "False"}, "k") and _is_selected({"k": "checked"}, "k")


def test_impact_factor_is_the_one_the_analysis_applied_with_the_irc_value_in_a_note():
    inputs = {KEY_SPAN: 30, KEY_CARRIAGEWAY_WIDTH: 7.5, KEY_LL_IRC_CLASS_A: True,
              KEY_LL_IRC_70R_WHEELED: True, KEY_LL_IRC_AA_WHEELED: True}
    tex = _live_load_tables(inputs)
    rows = {r[0]: r for r in _rows(tex)}
    applied = f"{1 + IRC6_2017.cl_208_3_impact_factor(30):.3f}"  # as analyser.py applies it
    assert rows["Class A"][2] == rows["Class 70R Wheeled"][2] == applied == "1.100"
    assert rows["Class A"][3].startswith("Applied in the grillage analysis")
    assert rows["Class AA Wheeled"][2] == "1.207"  # not loaded by the analysis: IRC 6 value
    note = re.sub(r"\s+", " ", tex.split(r"\end{longtable}")[1])
    assert "1.207 for Class A (Cl. 208.2)" in note and "1.207 for Class 70R Wheeled (Cl. 208.3)" in note


def test_braking_rows_follow_the_loading_tab():
    none_selected = _live_load_tables({KEY_SPAN: 30, KEY_CARRIAGEWAY_WIDTH: 7.5})
    braking = next(r for r in _rows(none_selected) if r[0].startswith("Braking force (longitudinal)"))
    assert braking[1] == "Not applied"
    inputs = {KEY_SPAN: 30, KEY_CARRIAGEWAY_WIDTH: 7.5, KEY_LL_IRC_70R_TRACKED: True,
              KEY_BL_IRC_CLASS_SV: False, KEY_LL_ECCENTRICITY: "1.2"}
    rows = {r[0]: r for r in _rows(_live_load_tables(inputs))}
    value = IRC6_2017.cl_211_2_braking_force(2) / kN
    assert rows["Braking force (longitudinal)"][1] == f"{value:.2f}"
    assert "Class A train" in rows["Braking force (longitudinal)"][3]
    assert rows["Braking from Class SV"][1] == "Not selected"
    assert rows["Braking force eccentricity above the deck top"][1:3] == ["1.2", "m"]
    wide = _live_load_tables({KEY_SPAN: 30, KEY_CARRIAGEWAY_WIDTH: 14.0, KEY_LL_IRC_CLASS_A: True})
    assert "per lane beyond two" in wide


def test_girder_dimensions_are_printed_in_mm():
    key = f"{KEY_MP_GIRDER_DEPTH}.G1.M1"
    assert _girder_dim_mm({key: 1.67}, key) == "1670"
    assert _girder_dim_mm({key: 0.022}, key) == "22"
    assert _girder_dim_mm({key: 1670.0}, key) == "1670"  # already in mm
    assert _girder_dim_mm({}, key) == ""


# ── Central style module (scope item 6) ──────────────────────────────────────

def test_style_module_supplies_captions_headings_and_status_cells():
    assert "labelfont=" + styles.FONTS["caption_label"] in styles.caption_setup()
    assert r"\titleformat{\chapter}" in styles.chapter_heading_block()
    assert r"\widecols" not in styles.latex_style_block()
    assert r"\flushlefttables" in styles.latex_style_block()
    assert styles.status_cell(True) == r"\statuspass{PASS}"
    assert styles.status_cell(False) == r"\statusfail{FAIL}"
    assert styles.status_text_cell("FAIL (fatigue)") == r"\statusfail{FAIL (fatigue)}"
    assert styles.status_text_cell("") == "---"
