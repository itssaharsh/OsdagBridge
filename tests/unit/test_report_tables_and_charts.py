"""Tests for the report post-processing (latex_tables), charts and styles."""

import os

from osdagbridge.core.reports import latex_tables, report_charts, styles

TABLE = r"""
\begin{longtable}{|C{2.5cm}|L{3cm}|>{\centering\arraybackslash}p{4.0cm}|}
\caption{\textbf{Stiffener Checks}}
\hline
\textbf{Girder} & \textbf{Check} & \textbf{Status} \\[\rowpad]
\hline
\multirow{2}{*}{\makecell{G1}} & Web & PASS \\[\rowpad]
\cline{2-3}
 & Flange & PASS \\[\rowpad]
\hline
\end{longtable}
"""


def test_column_count_handles_nested_braces():
    assert latex_tables.column_count(r"|C{2.5cm}|L{3cm}|>{\centering\arraybackslash}p{4.0cm}|") == 3
    assert latex_tables.column_count(r"|L{5.5cm}|p{10.0cm}|") == 2


def test_header_is_repeated_on_every_page():
    out = latex_tables.repeat_longtable_headers(TABLE)
    assert out.count(r"\textbf{Girder} & \textbf{Check}") == 2  # first head + continued head
    assert r"\endfirsthead" in out and r"\endhead" in out
    assert r"\caption{\textbf{Stiffener Checks}}\\" in out
    assert r"\caption[]{\textbf{Stiffener Checks} (continued)}\\" in out
    assert r"\multicolumn{3}{r}{\continuednote}\\" in out


def test_tables_with_their_own_head_are_untouched():
    table = TABLE.replace(r"\hline" + "\n" + r"\multirow", r"\hline\endhead" + "\n" + r"\multirow", 1)
    assert latex_tables.repeat_longtable_headers(table) == table


def test_header_less_table_gets_terminated_caption_but_no_repeated_row():
    table = r"""\begin{longtable}{|L{5cm}|p{10cm}|}
\caption{\textbf{Deck Slab}}
\hline
Effective span & 2100 mm \\[\rowpad]
\hline
\end{longtable}"""
    out = latex_tables.repeat_longtable_headers(table)
    assert r"\caption{\textbf{Deck Slab}}\\" in out
    assert out.count("Effective span") == 1


def test_transform_is_idempotent():
    once = latex_tables.finalize_tables(TABLE)
    assert latex_tables.finalize_tables(once) == once


def test_multirow_groups_cannot_break_across_pages():
    out = latex_tables.keep_row_groups_together(TABLE)
    assert r"Web & PASS \\*[\rowpad]" in out           # row inside the G1 group
    assert r"\groupcline{2-3}" in out                  # and no break after its rule
    assert r"\def\groupcline" in styles.latex_style_block()
    assert r"Flange & PASS \\[\rowpad]" in out          # last row of the group stays breakable


def test_styles_block_defines_every_macro_the_chapters_use():
    block = styles.latex_style_block()
    for macro in (r"\rowpad", r"\tablegap", r"\smallgap", r"\statusfail", r"\statuspass",
                  r"\compactcols", r"\narrowcols", r"\tightcols", r"\tallrows", r"\continuednote"):
        assert r"\newcommand{" + macro + "}" in block or r"\newcommand{" + macro + "}[1]" in block, macro
    assert "footskip=" in styles.geometry_options()
    assert styles.ur_cell(1.2) == r"\statusfail{1.20}"
    assert styles.ur_cell(0.5) == "0.50"
    assert styles.status_cell(None) == "---"


def test_charts_are_written(tmp_path):
    points = [
        report_charts.URPoint("Steel Plate Girders", "Moment", 0.72),
        report_charts.URPoint("Steel Plate Girders", "Fatigue", 1.12),
        report_charts.URPoint("Concrete Deck Slab", "Punching", 0.40),
        report_charts.URPoint("Cross Bracing", "Compression", 0.31),
        report_charts.URPoint("End Diaphragms", "Moment", None),
    ]
    paths = [
        report_charts.utilization_chart(points, str(tmp_path)),
        report_charts.element_summary_chart(points, str(tmp_path)),
        report_charts.steel_tonnage_chart({"steel_girders_wt_total": "40.12",
                                           "bracing_diag_wt_total": "2.50"}, str(tmp_path)),
        report_charts.concrete_rebar_chart({"concrete_deck_vol_total": "70.5",
                                            "rebar_deck_wt_total": "8.2"}, str(tmp_path)),
    ]
    for path in paths:
        assert path and os.path.getsize(path) > 1000


def test_charts_skip_when_there_is_no_data(tmp_path):
    assert report_charts.utilization_chart([report_charts.URPoint("Cross Bracing", "Tension", None)], str(tmp_path)) is None
    assert report_charts.steel_tonnage_chart({"steel_girders_wt_total": "N.A."}, str(tmp_path)) is None
