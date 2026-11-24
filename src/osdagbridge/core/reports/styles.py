"""Report styling: the single source of truth for how the design report looks.

Every visual setting of the OsdagBridge PDF report lives here: page geometry,
fonts, colours, captions, chapter headings, the table of contents, the title
page, table padding and widths, header/footer theme, status colouring, figure
sizes and the matplotlib look of the generated charts.

How the rest of the report uses it
----------------------------------
* ``report_generator`` builds the preamble, the title page and the table of
  contents from these values (``geometry_options``, ``caption_setup``,
  ``chapter_heading_block``, ``latex_style_block``, ``header_footer_block``,
  ``toc_block``, ``TITLE_PAGE``).
* ``latex_style_block`` defines LaTeX macros that the chapter files use instead
  of hard-coded values:

  =====================  ==================================================
  Macro                  Meaning
  =====================  ==================================================
  ``\\rowpad``            extra space after every table row (``\\\\[\\rowpad]``)
  ``\\formulagap``        line gap inside a stacked formula cell
  ``\\formulafont``       font size of a stacked formula cell
  ``\\tablegap`` ...      one macro per entry of ``SPACING`` (vertical gaps)
  ``\\statusfail{x}``     colour for failing values (FAIL, UR > 1)
  ``\\statuspass{x}``     colour for passing values
  ``\\compactcols``       column padding presets (also ``\\narrowcols``,
                         ``\\tightcols``) and ``\\tallrows``
  ``\\flushlefttables``   longtables start at the left margin
  ``\\densetablefont``    font size for very wide tables
  ``\\continuednote``     "Continued on next page" foot of a longtable
  =====================  ==================================================

* Chapter modules format PASS / FAIL and UR cells with the Python helpers at
  the end of this file (``status_cell``, ``status_text_cell``, ``warn_cell``,
  ``ur_cell``), and figure sizes come from ``FIGURES``.
* Column widths. The ``p``/``C``/``L``/``R`` widths written in the chapter
  files are proportions, not final sizes: ``latex_tables.fit_tables_to_width``
  adds the column padding (``TABLE['col_sep']`` or the active preset) and the
  rules, and scales the widths down proportionally whenever a table would be
  wider than the text block (``text_width_pt()``, computed from ``PAGE``).
* ``report_charts`` takes its colours and fonts from ``CHART``.
"""

from __future__ import annotations

import re

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
    # fancyhdr needs at least 17.5pt for the 12pt running header.
    "head_height": "18pt",
    "head_sep": "12pt",
    "foot_skip": "0.5in",
    "line_stretch": 1.15,
    # Extra stretch TeX may use before it lets a line run into the margin
    # (long code references such as "Cl.208.2/208.3" in running text).
    "emergency_stretch": "2em",
}

# Paper sizes (width, height) for text_width_pt().
PAPER_SIZES = {
    "a4paper": ("210mm", "297mm"),
    "letterpaper": ("8.5in", "11in"),
    "a5paper": ("148mm", "210mm"),
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
    "caption_label": "bf",             # \captionsetup labelfont ("Table 3.1:")
    "dense_table": r"\footnotesize",   # wide multi-column tables (Chapter 4)
    "formula": r"\footnotesize",       # stacked formulas inside a table cell
}

# ── Captions (caption package) ───────────────────────────────────────────────
CAPTION = {
    "label_font": FONTS["caption_label"],
    "justification": "raggedright",
    "single_line_check": "false",
    "format": "plain",
    "above_skip": "2pt",   # \abovecaptionskip
    "below_skip": "2pt",   # \belowcaptionskip
    "figure_font": "small",  # captions of charts and embedded plots (_fig_embed)
}

# ── Chapter headings and table of contents ───────────────────────────────────
HEADINGS = {
    "chapter_format": r"\normalfont\Large\bfseries\centering",
    "chapter_label_sep": "1em",
    "chapter_space_before": "-30pt",
    "chapter_space_after": "10pt",
    # Unnumbered headings set by hand (Executive Summary, Table of Contents).
    "unnumbered_title": r"\centering\Large\bfseries",
}

TOC = {
    "title": "Table of Contents",
    "depth": 2,
    "space_before_title": "0pt",
    "chapter_gap": "2pt",
    # (left indent, label width) per level
    "chapter": ("1.5em", "1.5em"),
    "section": ("3.8em", "2.3em"),
    "subsection": ("7.0em", "3.2em"),
}

# ── Title page ───────────────────────────────────────────────────────────────
TITLE_PAGE = {
    "top_gap": "1.5cm",
    "logo_left_width": r"0.6\textwidth",
    "logo_right_width": r"0.35\textwidth",
    "logo_right_height": "2.2cm",
    "logo_gap": "1cm",
    "title_size": r"\Huge",
    "title_gap": "0.3cm",
    "subtitle_size": r"\large",
    "subtitle_gap": "1.5cm",
    "doc_type_size": r"\Large",
    "doc_type_gap": "1.5cm",
    "info_label_width": "4cm",
    "info_value_width": "10cm",
}

# ── Tables ───────────────────────────────────────────────────────────────────
TABLE = {
    "col_sep": "6pt",            # default \tabcolsep
    "col_sep_compact": "3.5pt",  # wide tables (Bill of Materials, design summaries)
    "col_sep_narrow": "4pt",     # girder property tables (Chapters 2 and 5)
    "col_sep_tight": "3pt",      # nine-column analysis summary (Chapter 4)
    "array_stretch": "1.12",
    "array_stretch_tall": "1.25",  # rows with stacked (\makecell) headers
    "extra_row_height": "0.6pt",
    "row_pad": "6pt",            # space after each row: \\[\rowpad]
    "formula_gap": "3pt",        # between the lines of a stacked formula cell
    "rule_width": "0.5pt",
    "lt_pre": "0pt",             # space before a longtable
    "lt_post": "6pt",            # space after a longtable
    "lt_left": r"\fill",         # longtables are centred ...
    "lt_right": r"\fill",
    "lt_left_flush": "0pt",      # ... except after \flushlefttables
    # An ordinary (non-breaking) table only starts on the current page if at
    # least this many lines are left. Longtables get no \needspace: it breaks
    # their head / continued-head logic (see latex_tables.py).
    "needspace_lines": 6,
    "continued_caption": "(continued)",
    "continued_note": "Continued on next page",
    # A continued caption ("Table 5.1: <title> (continued)") longer than this
    # many characters is shortened so that it stays on one line.
    "continued_caption_chars": 78,
    # A \multirow group of up to this many rows is kept on one page; a taller
    # group may break (its label is top-aligned, so it stays in the first row).
    "keep_together_rows": 16,
    # Vertical alignment of \multirow group labels in the table body.
    "group_label_valign": "t",
    # Slack left when a table is scaled to the text width.
    "fit_margin": "1pt",
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
    "headrule_gap": "2pt",     # below the header rule
    "note_raise": "-20pt",     # lifts the "* Software default value" note above the rule
    "note_gap": "4pt",         # between that note and the footer rule
    "footrule_raise": "-8pt",  # footer rule position when there is no note
    "footrule_gap": "6pt",     # between the footer rule and the footer text
}

# ── Figures ──────────────────────────────────────────────────────────────────
FIGURES = {
    "chart_width": r"0.95\textwidth",          # Section 5.5 UR charts
    "chart_width_small": r"0.85\textwidth",    # Chapter 7 quantity charts
    "drawing_width": r"0.85\textwidth",        # Chapter 6 drawings
    "drawing_cell_width": r"0.31\textwidth",   # Chapter 6 three-across views
    "summary_width": r"0.9\textwidth",         # Executive Summary figures
    "analysis_plot_width": r"0.75\textwidth",  # Chapter 4 envelope plots
    "placeholder_width": r"0.97\textwidth",    # box shown when an image is missing
    "placeholder_cell_width": r"0.95\linewidth",
    "embed_top_gap": "-0.5em",                 # _fig_embed: above the image
    "embed_caption_gap": "0.5em",              # _fig_embed: image to caption
    "embed_bottom_gap": "-0.5em",              # _fig_embed: below the caption
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
    "bar_edge_width": 0.5,
    "pair_bar_width": 0.55,  # the two bars of the concrete vs reinforcement chart
    "limit_line_width": 1.2,
    # The UR axis stops at this value; a bar above it is drawn up to the cap
    # (hatched) and labelled with its real value, so one extreme UR does not
    # flatten every other bar.
    "ur_axis_cap": 2.0,
    "ur_cap_hatch": "///",
    # Characters per line of a check label on the x axis before it wraps.
    "label_wrap_chars": 11,
}


# ── Lengths ──────────────────────────────────────────────────────────────────

_PT_PER = {"pt": 1.0, "in": 72.27, "cm": 72.27 / 2.54, "mm": 72.27 / 25.4,
           "bp": 72.27 / 72.0, "pc": 12.0}


def length_pt(value: str) -> float:
    """A TeX length such as ``'1in'``, ``'2.5cm'`` or ``'6pt'`` in points."""
    m = re.fullmatch(r"\s*(-?\d*\.?\d+)\s*(pt|in|cm|mm|bp|pc)\s*", str(value))
    if not m:
        raise ValueError(f"not an absolute TeX length: {value!r}")
    return float(m.group(1)) * _PT_PER[m.group(2)]


def text_width_pt() -> float:
    """Width of the text block in points: paper width minus the side margins."""
    paper_width = PAPER_SIZES[PAGE["paper"]][0]
    return length_pt(paper_width) - length_pt(PAGE["margin_left"]) - length_pt(PAGE["margin_right"])


def col_sep_presets() -> dict:
    """\\tabcolsep in points for each column-padding macro (and the default)."""
    return {
        "default": length_pt(TABLE["col_sep"]),
        "compactcols": length_pt(TABLE["col_sep_compact"]),
        "narrowcols": length_pt(TABLE["col_sep_narrow"]),
        "tightcols": length_pt(TABLE["col_sep_tight"]),
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


def caption_setup() -> str:
    """\\captionsetup and caption skips (after \\usepackage{caption})."""
    c = CAPTION
    return (
        "\\captionsetup{\n"
        f"    labelfont={c['label_font']},\n"
        f"    justification={c['justification']},\n"
        f"    singlelinecheck={c['single_line_check']},\n"
        f"    format={c['format']}\n"
        "}\n"
        rf"\setlength{{\abovecaptionskip}}{{{c['above_skip']}}}" "\n"
        rf"\setlength{{\belowcaptionskip}}{{{c['below_skip']}}}"
    )


def chapter_heading_block() -> str:
    """titlesec format of numbered chapters (after \\usepackage{titlesec})."""
    h = HEADINGS
    return (rf"\titleformat{{\chapter}}[block]{{{h['chapter_format']}}}{{\thechapter}}"
            rf"{{{h['chapter_label_sep']}}}{{}}" "\n"
            rf"\titlespacing*{{\chapter}}{{0pt}}{{{h['chapter_space_before']}}}{{{h['chapter_space_after']}}}")


def unnumbered_title(text: str) -> str:
    """A centred, unnumbered heading line (Executive Summary)."""
    return "{" + HEADINGS["unnumbered_title"] + " " + text + r"\par}"


def toc_block() -> str:
    """titletoc entry styles and the table of contents itself."""
    t, h = TOC, HEADINGS
    lines = [
        rf"\setcounter{{tocdepth}}{{{t['depth']}}}",
        rf"\titlecontents{{chapter}}[{t['chapter'][0]}]",
        rf"  {{\normalfont\vspace{{{t['chapter_gap']}}}}}",
        rf"  {{\contentslabel{{{t['chapter'][1]}}}}}",
        rf"  {{\hspace*{{-{t['chapter'][1]}}}}}",
        r"  {\hfill\contentspage}",
    ]
    for level in ("section", "subsection"):
        indent, label = t[level]
        lines += [
            rf"\titlecontents{{{level}}}[{indent}]",
            r"  {\normalfont}",
            rf"  {{\contentslabel{{{label}}}}}",
            rf"  {{\hspace*{{-{label}}}}}",
            r"  {\hfill\contentspage}",
        ]
    lines += [
        r"\newpage",
        rf"\renewcommand{{\contentsname}}{{{h['unnumbered_title']} {t['title']}}}",
        # The contents title sits higher than a numbered chapter title would.
        r"\begingroup",
        rf"\titlespacing*{{\chapter}}{{0pt}}{{{t['space_before_title']}}}{{{h['chapter_space_after']}}}",
        r"\tableofcontents",
        r"\endgroup",
    ]
    return "\n".join(lines)


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
        rf"\setlength{{\LTleft}}{{{t['lt_left']}}}",
        rf"\setlength{{\LTright}}{{{t['lt_right']}}}",
        rf"\setlength{{\arrayrulewidth}}{{{t['rule_width']}}}",
        rf"\setlength{{\extrarowheight}}{{{t['extra_row_height']}}}",
        rf"\newcommand{{\rowpad}}{{{t['row_pad']}}}",
        rf"\newcommand{{\formulagap}}{{{t['formula_gap']}}}",
        rf"\newcommand{{\formulafont}}{{{FONTS['formula']}}}",
        rf"\newcommand{{\compactcols}}{{\setlength{{\tabcolsep}}{{{t['col_sep_compact']}}}}}",
        rf"\newcommand{{\narrowcols}}{{\setlength{{\tabcolsep}}{{{t['col_sep_narrow']}}}}}",
        rf"\newcommand{{\tightcols}}{{\setlength{{\tabcolsep}}{{{t['col_sep_tight']}}}}}",
        rf"\newcommand{{\tallrows}}{{\renewcommand{{\arraystretch}}{{{t['array_stretch_tall']}}}}}",
        (rf"\newcommand{{\flushlefttables}}{{\setlength{{\LTleft}}{{{t['lt_left_flush']}}}"
         rf"\setlength{{\LTright}}{{\fill}}}}"),
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
        rf"      \vspace{{{hf['note_raise']}}}%" "\n"
        rf"      \hbox to \headwidth{{\textcolor{{black}}{{{note}}}\hfil}}%" "\n"
        rf"      \vspace{{{hf['note_gap']}}}%" "\n"
        r"    }{%" "\n"
        rf"      \vspace{{{hf['footrule_raise']}}}%" "\n"
        r"    }%" "\n"
        rf"    {rule} \vspace{{{hf['footrule_gap']}}}%" "\n"
        r"  }"
    )
    running = (
        r"  \fancyhf{}" "\n"
        rf"  \fancyhead[L]{{{project} $|$ {job}}}" "\n"
        rf"  \fancyhead[R]{{{date} $|$ {version}}}" "\n"
        rf"  \fancyfoot[L]{{{hf['footer_left']}}}" "\n"
        rf"  \fancyfoot[R]{{{hf['footer_right']}}}" "\n"
        rf"  \renewcommand{{\headrule}}{{{rule} \vspace{{{hf['headrule_gap']}}}}}" "\n"
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
        rf"  \renewcommand{{\footrule}}{{\vspace{{{hf['footrule_raise']}}}{rule} \vspace{{{hf['footrule_gap']}}}}}" "\n"
        "}\n"
    )


# ── Python helpers shared by the chapter modules ─────────────────────────────

UR_LIMIT = 1.0

STATUS = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "missing": "---"}


def status_cell(ok: bool | None) -> str:
    """PASS / FAIL text for a table cell; '---' when the check did not run."""
    if ok is None:
        return STATUS["missing"]
    return rf"\statuspass{{{STATUS['pass']}}}" if ok else rf"\statusfail{{{STATUS['fail']}}}"


def warn_cell() -> str:
    """The WARN status of the interaction checks (0.90 <= UR < 1.00)."""
    return STATUS["warn"]


def status_text_cell(text) -> str:
    """A status string computed by the design engine (e.g. 'PASS', 'FAIL (fatigue)').

    Text containing FAIL is coloured as a failure; an empty value is '---'.
    """
    s = "" if text is None else str(text).strip()
    if not s:
        return STATUS["missing"]
    return rf"\statusfail{{{s}}}" if STATUS["fail"] in s.upper() else rf"\statuspass{{{s}}}"


def ur_cell(value, digits: int = 2) -> str:
    """Utilization ratio formatted for a table; values above 1.0 are coloured."""
    try:
        ur = float(value)
    except (TypeError, ValueError):
        return ""
    text = f"{ur:.{digits}f}"
    return rf"\statusfail{{{text}}}" if ur > UR_LIMIT else text
