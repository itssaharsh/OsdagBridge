"""Longtable post-processing for the design report.

Two problems in the generated report come from the same place: the chapter
modules write ``longtable`` environments whose header row is only defined
once, and whose multi-row groups (one girder = several rows with a
``\\multirow`` label) may be split by a page break.

``repeat_longtable_headers``
    Gives every longtable a proper head and foot::

        \\caption{Title}\\\\ <header> \\endfirsthead
        \\caption[]{Title (continued)}\\\\ <header> \\endhead
        \\multicolumn{n}{r}{Continued on next page}\\\\ \\endfoot
        \\endlastfoot

    so the column header row is printed again at the top of every page the
    table continues on. Tables that already define ``\\endhead`` are left
    untouched, and a table is only changed when its first row really is a
    header (it contains ``\\textbf``), so data rows are never repeated.

``keep_row_groups_together``
    Inside a ``\\multirow`` group the rows are separated by ``\\cline`` (the
    group ends with ``\\hline``). Breaking the page between such rows left the
    ``\\multirow`` label (e.g. "G4") printed below the last row, on top of the
    page footer. Those row ends become ``\\\\*`` (longtable's "no page break
    here") and the ``\\cline`` after them becomes ``\\groupcline``, the same
    rule without a break point after it, so a group always stays on one page;
    breaks still happen between groups.

Both functions are applied per chapter by ``report_generator.generate_report``
and are idempotent.

Note on \\needspace: the old preamble ran \\needspace before every longtable.
With a real head (\\endfirsthead / \\endhead) that made longtable break the
page right at the start of some tables: an empty "Continued on next page" foot
was left on one page and the continued head was printed above the first head
on the next. Longtable already keeps its first head together with the first
row, so \\needspace is now only used before ordinary ``table`` environments
(see styles.latex_style_block).
"""

from __future__ import annotations

import re

from .styles import TABLE

_BEGIN = re.compile(r"\\begin\{longtable\}")
_END = r"\end{longtable}"


def _read_group(text: str, start: int, open_ch: str = "{", close_ch: str = "}") -> int:
    """Index just past the balanced group that starts at ``text[start] == open_ch``."""
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "\\":
            continue
        if ch == open_ch and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif ch == close_ch and (i == 0 or text[i - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced group in longtable")


def column_count(spec: str) -> int:
    """Number of columns in a tabular column spec such as ``|C{2cm}|>{\\centering}p{4cm}|``."""
    flat, i = [], 0
    while i < len(spec):
        ch = spec[i]
        if ch == "{":
            i = _read_group(spec, i)
            continue
        flat.append(ch)
        i += 1
    letters = [ch for ch in "".join(flat) if ch.isalpha()]
    # '*{3}{c}' style repeats are not used in the report; count plain letters.
    return len(letters)


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def _transform_table(body: str, spec: str) -> str | None:
    """Return the new table body (everything after the column spec) or None to leave it."""
    if r"\endhead" in body or r"\endfirsthead" in body:
        return None
    i = _skip_ws(body, 0)
    caption = None
    if body.startswith(r"\caption", i):
        j = i + len(r"\caption")
        if body.startswith("[", j):
            j = _read_group(body, j, "[", "]")
        if not body.startswith("{", j):
            return None
        end = _read_group(body, j)
        caption = body[j + 1:end - 1]
        i = _skip_ws(body, end)
        if body.startswith(r"\\", i):  # caption already terminated
            i = _skip_ws(body, i + 2)
        label = re.match(r"\\label\{[^}]*\}", body[i:])
        if label:
            caption += label.group(0)
            i = _skip_ws(body, i + label.end())
    if not body.startswith(r"\hline", i):
        return None
    n_cols = max(column_count(spec), 1)
    cont = TABLE["continued_caption"]
    foot = [rf"\multicolumn{{{n_cols}}}{{r}}{{\continuednote}}\\", r"\endfoot", r"\endlastfoot"]
    header_start = i
    # The header ends at the first \hline that follows a row end (\\).
    row_end = body.find(r"\\", header_start + len(r"\hline"))
    if row_end == -1:
        return None
    header_close = body.find(r"\hline", row_end)
    if header_close == -1:
        return None
    header_end = header_close + len(r"\hline")
    header = body[header_start:header_end].strip()
    if r"\textbf" not in header:
        # The first row is data, not a header, so it must not be repeated. A
        # captioned table still gets a terminated caption (a longtable \caption
        # needs a trailing \\) and a "(continued)" caption with a top rule.
        if caption is None:
            return None
        plain = re.sub(r"\\label\{[^}]*\}", "", caption)
        parts = [rf"\caption{{{caption}}}\\", r"\endfirsthead",
                 rf"\caption[]{{{plain} {cont}}}\\", r"\hline", r"\endhead", *foot]
        return "\n" + "\n".join(parts) + "\n" + body[header_start:]
    rest = body[header_end:]

    parts = []
    if caption is not None:
        parts.append(rf"\caption{{{caption}}}\\")
    parts += [header, r"\endfirsthead", ""]
    if caption is not None:
        plain = re.sub(r"\\label\{[^}]*\}", "", caption)
        parts.append(rf"\caption[]{{{plain} {cont}}}\\")
    parts += [header, r"\endhead", "", *foot]
    return "\n" + "\n".join(parts) + "\n" + rest.lstrip("\n")


def repeat_longtable_headers(tex: str) -> str:
    out, pos = [], 0
    for match in _BEGIN.finditer(tex):
        if match.start() < pos:
            continue
        i = match.end()
        if tex.startswith("[", i):
            i = _read_group(tex, i, "[", "]")
        if not tex.startswith("{", i):
            continue
        spec_end = _read_group(tex, i)
        spec = tex[i + 1:spec_end - 1]
        end = tex.find(_END, spec_end)
        if end == -1:
            break
        new_body = _transform_table(tex[spec_end:end], spec)
        out.append(tex[pos:spec_end])
        out.append(new_body if new_body is not None else tex[spec_end:end])
        pos = end
    out.append(tex[pos:])
    return "".join(out)


# A row end (\\ or \\[len]) followed, after optional whitespace, by \cline{..}:
# the next row belongs to the same \multirow group.
_ROW_BEFORE_CLINE = re.compile(r"\\\\(?!\*)(\[[^\]]*\])?(\s*)\\cline(\{[^}]*\})")


def keep_row_groups_together(tex: str) -> str:
    """Forbid page breaks inside \\multirow groups of every longtable."""
    out, pos = [], 0
    for match in _BEGIN.finditer(tex):
        end = tex.find(_END, match.end())
        if end == -1:
            break
        out.append(tex[pos:match.start()])
        # \\* stops a break after the row. \cline is a row of its own and ends
        # with a negative skip where TeX may break, so it becomes \groupcline
        # (defined in styles.latex_style_block), which forbids that break.
        out.append(_ROW_BEFORE_CLINE.sub(
            lambda m: r"\\*" + (m.group(1) or "") + m.group(2) + r"\groupcline" + m.group(3),
            tex[match.start():end]))
        pos = end
    out.append(tex[pos:])
    return "".join(out)


def finalize_tables(tex: str) -> str:
    return keep_row_groups_together(repeat_longtable_headers(tex))
