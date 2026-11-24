"""Report styling: the single source of truth for how the design report looks.

Every visual setting of the OsdagBridge PDF report lives here: page geometry,
fonts, colours, table padding, header/footer theme, status colouring, figure
sizes and the matplotlib look of the generated charts.

How the rest of the report uses it
----------------------------------
* ``report_generator.preamble`` builds the LaTeX preamble from these values
  (``geometry_options``, ``latex_style_block``, ``header_footer_block``).
* ``latex_style_block`` defines LaTeX macros that the chapter files use instead
  of hard-coded values:

  ==================  =====================================================
  Macro               Meaning
  ==================  =====================================================
  ``\\rowpad``         extra space after every table row (``\\\\[\\rowpad]``)
  ``\\tablegap`` ...   one macro per entry of ``SPACING`` (vertical gaps)
  ``\\statusfail{x}``  colour for failing values (FAIL, UR > 1)
  ``\\statuspass{x}``  colour for passing values
  ``\\compactcols``    column padding presets (also ``\\narrowcols``,
                      ``\\tightcols``, ``\\widecols``) and ``\\tallrows``
  ``\\densetablefont``  font size for very wide tables
  ==================  =====================================================

* Chapter modules import the Python helpers below (``status_cell``,
  ``ur_cell``) so PASS/FAIL and UR formatting is identical everywhere.
* ``report_charts`` takes its colours and fonts from ``CHART``.

To restyle the whole report, change a value here and regenerate; no chapter
file needs to be edited.
"""

from __future__ import annotations

# ── Page ─────────────────────────────────────────────────────────────────────
PAGE = {
    "paper": "a4paper",
    "font_size": "12pt",
    "margin_left": "1in",
    "margin_right": "1in",
    "margin_top": "1in",
    # The footer rule, the "* Software default value" note and the footer text
    # all sit below the text block. A slightly larger bottom margin and an
    # explicit footskip keep table rows from running into them.
    "margin_bottom": "1.2in",
    "head_height": "15pt",
    "head_sep": "12pt",
    "foot_skip": "0.5in",
    "line_stretch": 1.15,
}

# ── Colours (HTML hex, no '#') ───────────────────────────────────────────────
COLORS = {
    "osdagGreen": "91B014",   # Osdag brand green: rules, chart accents
    "statusFail": "C62828",   # failing checks, UR > 1.0
    "statusPass": "000000",   # passing checks stay black for print
    "mutedText":  "555555",   # "continued" notes
    "logWarning": "0000FF",   # design log (Chapter 9): warnings
    "logError":   "C62828",   # design log: errors
    "logInfo":    "91B014",   # design log: info
}

# ── Fonts ────────────────────────────────────────────────────────────────────
FONTS = {
    "footer_note_size": r"\footnotesize",
    "continued_size": r"\footnotesize",
    "caption_label": "bf",
    "dense_table": r"\footnotesize",   # wide multi-column tables (Chapter 4)
}

# ── Tables ───────────────────────────────────────────────────────────────────
TABLE = {
    "col_sep": "6pt",            # default \tabcolsep
    "col_sep_compact": "3.5pt",  # wide tables (Bill of Materials, design summaries)
    "col_sep_wide": "8pt",       # two-column parameter tables
    "col_sep_narrow": "4pt",     # girder property tables (Chapters 2 and 5)
    "col_sep_tight": "3pt",      # nine-column analysis summary (Chapter 4)
    "array_stretch": "1.12",
    "array_stretch_tall": "1.25",  # rows with stacked (\makecell) headers
    "extra_row_height": "0.6pt",
    "row_pad": "6pt",            # space after each row: \\[\rowpad]
    "rule_width": "0.5pt",
    "lt_pre": "0pt",             # space before a longtable
    "lt_post": "6pt",            # space after a longtable
    # An ordinary (non-breaking) table only starts on the current page if at
    # least this many lines are left. Longtables get no \needspace: it breaks
    # their head / continued-head logic (see latex_tables.py).
    "needspace_lines": 6,
    "continued_caption": "(continued)",
    "continued_note": "Continued on next page",
}

# ── Vertical spacing ─────────────────────────────────────────────────────────
# Every \vspace used by the chapter files, by role. Each becomes a macro of the
# same name in the preamble (e.g. "tablegap" -> \tablegap).
SPACING = {
    "tablegap":   "1em",    # before a table
    "mediumgap":  "0.8em",  # between a table and the next block
    "notegap":    "0.6em",  # before a table note
    "smallgap":   "0.4em",  # between a heading and its table
    "captiongap": "0.3em",  # between a caption line and its table
    "tinygap":    "4pt",    # inside figure blocks
    "blockgap":   "0.4cm",  # between input-parameter blocks (Chapter 2)
    "loggap":     "0.5cm",  # before the design log (Chapter 9)
    "largegap":   "0.8cm",  # before a new group of tables (Chapter 2)
    "sectiongap": "2.2em",  # before a girder-wise table group (Chapter 2)
}

# ── Header / footer ──────────────────────────────────────────────────────────
HEADER_FOOTER = {
    "rule_color": "osdagGreen",
    "rule_thickness": "1pt",
    # Longest project name / job number shown in the running header; longer
    # ones end in "..." so the left header never runs into the right one.
    "max_project_chars": 50,
    "max_job_chars": 20,
    "footer_left": r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay",
    "footer_right": r"Page \thepage\ of \pageref{LastPage}",
    "default_value_note": r"* Software default value",
}

# ── Figures ──────────────────────────────────────────────────────────────────
FIGURES = {
    "chart_width": r"0.95\textwidth",
    "chart_width_half": r"0.85\textwidth",
}

# ── Charts (matplotlib) ──────────────────────────────────────────────────────
CHART = {
    "font_family": "DejaVu Sans",
    "font_size": 9,
    "title_size": 10,
    "dpi": 200,
    "pass_color": "#" + COLORS["osdagGreen"],
    "fail_color": "#" + COLORS["statusFail"],
    "limit_color": "#" + COLORS["statusFail"],
    "edge_color": "#333333",
    "grid_color": "#DDDDDD",
    "steel_color": "#5E7D12",
    "concrete_color": "#9E9E9E",
    "rebar_color": "#8D5524",
    "missing_color": "#BDBDBD",
    "figure_width_in": 7.2,
}


# ── LaTeX generated from the values above ───────────────────────────────────

def geometry_options() -> str:
    """Options for \\usepackage[...]{geometry}."""
    p = PAGE
    return (f"{p['paper']}, left={p['margin_left']}, right={p['margin_right']}, "
            f"top={p['margin_top']}, bottom={p['margin_bottom']}, "
            f"headheight={p['head_height']}, headsep={p['head_sep']}, footskip={p['foot_skip']}")


def color_definitions() -> str:
    return "\n".join(rf"\definecolor{{{name}}}{{HTML}}{{{hexcode}}}" for name, hexcode in COLORS.items())


# \cline inside a \multirow group, without a page-break point after the rule.
# Same as colortbl's \@cline, with \nobreak before the closing negative skip.
GROUP_CLINE = r"""\makeatletter
\def\groupcline#1{\@groupcline#1\@nil}
\def\@groupcline#1-#2\@nil{%
  \omit
  \@multicnt#1%
  \advance\@multispan\m@ne
  \ifnum\@multicnt=\@ne\@firstofone{&\omit}\fi
  \@multicnt#2%
  \advance\@multicnt-#1%
  \advance\@multispan\@ne
  {\CT@arc@\leaders\hrule\@height\arrayrulewidth\hfill}%
  \cr
  \noalign{\nobreak\vskip-\arrayrulewidth}}
\makeatother"""


def latex_style_block() -> str:
    """Colours, table settings and the macros the chapter files use."""
    t = TABLE
    lines = [
        "% ---- Generated from osdagbridge/core/reports/styles.py ----",
        color_definitions(),
        rf"\setlength{{\tabcolsep}}{{{t['col_sep']}}}",
        rf"\renewcommand{{\arraystretch}}{{{t['array_stretch']}}}",
        rf"\setlength{{\LTpre}}{{{t['lt_pre']}}}",
        rf"\setlength{{\LTpost}}{{{t['lt_post']}}}",
        rf"\setlength{{\arrayrulewidth}}{{{t['rule_width']}}}",
        rf"\setlength{{\extrarowheight}}{{{t['extra_row_height']}}}",
        rf"\newcommand{{\rowpad}}{{{t['row_pad']}}}",
        rf"\newcommand{{\compactcols}}{{\setlength{{\tabcolsep}}{{{t['col_sep_compact']}}}}}",
        rf"\newcommand{{\narrowcols}}{{\setlength{{\tabcolsep}}{{{t['col_sep_narrow']}}}}}",
        rf"\newcommand{{\tightcols}}{{\setlength{{\tabcolsep}}{{{t['col_sep_tight']}}}}}",
        rf"\newcommand{{\widecols}}{{\setlength{{\tabcolsep}}{{{t['col_sep_wide']}}}}}",
        rf"\newcommand{{\tallrows}}{{\renewcommand{{\arraystretch}}{{{t['array_stretch_tall']}}}}}",
        rf"\newcommand{{\densetablefont}}{{{FONTS['dense_table']}}}",
        r"\newcommand{\statusfail}[1]{\textcolor{statusFail}{#1}}",
        r"\newcommand{\statuspass}[1]{\textcolor{statusPass}{#1}}",
        rf"\newcommand{{\continuednote}}{{{FONTS['continued_size']}\textit{{\textcolor{{mutedText}}{{{t['continued_note']}}}}}}}",
    ]
    lines += [rf"\newcommand{{\{name}}}{{\vspace{{{value}}}}}" for name, value in SPACING.items()]
    lines += [GROUP_CLINE]
    lines += [
        "% Keep an ordinary table off the bottom of a page unless enough room is",
        "% left. Longtables repeat their head and keep it with the first row.",
        rf"\BeforeBeginEnvironment{{table}}{{\needspace{{{t['needspace_lines']}\baselineskip}}}}",
        "% ------------------------------------------------------------",
    ]
    return "\n".join(lines)


def header_footer_block(project: str, job: str, date: str, version: str) -> str:
    """fancyhdr page styles (main, plain, firstpage) in the report theme.

    The arguments must already be LaTeX-escaped.
    """
    hf = HEADER_FOOTER
    rule = rf"\color{{{hf['rule_color']}}}\hrule width\headwidth height {hf['rule_thickness']}"
    note = rf"{FONTS['footer_note_size']}\textit{{{hf['default_value_note']}}}"
    footrule = (
        r"\renewcommand{\footrule}{%" "\n"
        r"    \ifbool{hasSDonPage}{%" "\n"
        r"      \vspace{-20pt}%" "\n"
        rf"      \hbox to \headwidth{{\textcolor{{black}}{{{note}}}\hfil}}%" "\n"
        r"      \vspace{4pt}%" "\n"
        r"    }{%" "\n"
        r"      \vspace{-8pt}%" "\n"
        r"    }%" "\n"
        rf"    {rule} \vspace{{6pt}}%" "\n"
        r"  }"
    )
    running = (
        r"  \fancyhf{}" "\n"
        rf"  \fancyhead[L]{{{project} $|$ {job}}}" "\n"
        rf"  \fancyhead[R]{{{date} $|$ {version}}}" "\n"
        rf"  \fancyfoot[L]{{{hf['footer_left']}}}" "\n"
        rf"  \fancyfoot[R]{{{hf['footer_right']}}}" "\n"
        rf"  \renewcommand{{\headrule}}{{{rule} \vspace{{2pt}}}}" "\n"
        f"  {footrule}\n"
    )
    return (
        "\\fancypagestyle{main}{\n" + running + "}\n"
        "\\fancypagestyle{plain}{\n" + running + "}\n"
        "\\fancypagestyle{firstpage}{\n"
        "  \\fancyhf{}\n"
        "  \\renewcommand{\\headrulewidth}{0pt}\n"
        rf"  \fancyfoot[L]{{{hf['footer_left']}}}" "\n"
        rf"  \fancyfoot[R]{{{hf['footer_right']}}}" "\n"
        rf"  \renewcommand{{\footrule}}{{\vspace{{-8pt}}{rule} \vspace{{6pt}}}}" "\n"
        "}\n"
    )


# ── Python helpers shared by the chapter modules ─────────────────────────────

UR_LIMIT = 1.0


def status_cell(ok: bool | None) -> str:
    """PASS / FAIL text for a table cell; '---' when the check did not run."""
    if ok is None:
        return "---"
    return r"\statuspass{PASS}" if ok else r"\statusfail{FAIL}"


def ur_cell(value, digits: int = 2) -> str:
    """Utilization ratio formatted for a table; values above 1.0 are coloured."""
    try:
        ur = float(value)
    except (TypeError, ValueError):
        return ""
    text = f"{ur:.{digits}f}"
    return rf"\statusfail{{{text}}}" if ur > UR_LIMIT else text
