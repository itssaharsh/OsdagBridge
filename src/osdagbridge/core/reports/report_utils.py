from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_DEPTH,
    KEY_TS_NO_OF_GIRDERS
)
from osdagbridge.core.reports.styles import CAPTION, FIGURES


def _tex(value):
    """Escape a Python value for safe LaTeX embedding."""
    s = str(value) if value is not None else ''
    if not s:
        return r''
    # Normalise non-ASCII glyphs from section designations (e.g. "∠ 100 ⅹ 100ⅹ 10")
    # that pdflatex cannot render.
    for uni, ascii_ in [('∠', 'L'), ('ⅹ', 'x'), ('×', 'x')]:
        s = s.replace(uni, ascii_)
    s = s.replace('\\', r'\textbackslash{}')
    for ch, esc in [('&', r'\&'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'),
                    ('{', r'\{'), ('}', r'\}'),          
                    ('_', r'\_\allowbreak{}'),            
                    ('~', r'\textasciitilde{}'), ('^', r'\^{}')]:
        s = s.replace(ch, esc)
    s = s.replace(':', r':\allowbreak{}')
    # pdflatex cannot print these glyphs directly (they appear in check names).
    for uni, math in [('≤', r'$\leq$'), ('≥', r'$\geq$')]:
        s = s.replace(uni, math)
    return s


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val in ("", None):
        return ""
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """
    Retrieve all girder labels and member IDs from backend keys.

    Usage Example:
    --------------------------
    girder_entries = get_girder_entries(bridge.input_dict)
    
    # 1. Fallback handling (if backend hasn't populated keys yet)
    if not girder_entries:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1))
        girder_entries = [(f"Girder {i}", f"M1") for i in range(1, n + 1)]
        
    # 2. Get total number of girders safely
    n_girders = len(girder_entries)
    
    # 3. Iterate over the girders to build table rows
    for lbl, mid in girder_entries:
        # lbl will be e.g., "G1", mid will be e.g., "G1M1"
        # Access girder specific keys dynamically:
        # val = input_dict.get(f"{KEY_MP_GIRDER_DEPTH}.{lbl}.{mid}")
        pass

    Returns:
        List[Tuple[str, str]]
    """
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0))

    entries = []

    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def _placeholder_box(text, width=None):
    """Framed box shown instead of a figure whose image is missing.

    It ends with \\par, so two placeholders never share a line (two boxes of
    0.97 of the text width side by side ran off the page in Chapter 4).
    """
    width = width or FIGURES["placeholder_width"]
    return (r'\noindent\fbox{\parbox{' + width + '}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + text + r' ]}' + '\n'
            r'}}\par')


def _fig_or_placeholder(path, caption, width=None):
    """Embed figure if path is provided (file already copied to assets), else show placeholder box.
    path is the relative path as pdflatex will see it (e.g. 'assets/plan.png').
    """
    width = width or FIGURES["summary_width"]
    if path:
        p = path.replace('\\', '/')
        return (r'\begin{figure}[H]' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[width=' + width + ']{' + p + '}\n'
                r'\caption*{' + caption + '}\n'
                r'\end{figure}')
    return (r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            + _placeholder_box(caption) + '\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}')


def _fig_embed(path, caption, width=r'\textwidth', height=None, label=None, numbered=False):
    """Embed a figure from ``path`` (relative to the LaTeX build folder).

    ``numbered=True`` gives a numbered caption (\\caption, "Figure 5.1") that
    can carry a ``label`` for \\ref; otherwise the caption is unnumbered
    (\\caption*), as for the analysis plots. Without a path an fbox placeholder
    is shown. Gaps and the caption font come from styles.FIGURES / CAPTION.
    """
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        cap = (r'\caption{' if numbered else r'\caption*{') + caption + '}'
        if numbered and label:
            cap += r'\label{' + label + '}'
        return (r'\begin{figure}[H]' + '\n'
                r'\captionsetup{font=' + CAPTION["figure_font"] + '}\n'
                r'\vspace{' + FIGURES["embed_top_gap"] + '}\n'
                r'\centering' + '\n'
                r'\includegraphics[' + opts + ']{' + p + '}\n'
                r'\vspace{' + FIGURES["embed_caption_gap"] + '}\n'
                + cap + '\n'
                r'\vspace{' + FIGURES["embed_bottom_gap"] + '}\n'
                r'\end{figure}')
    return _placeholder_box(caption)
