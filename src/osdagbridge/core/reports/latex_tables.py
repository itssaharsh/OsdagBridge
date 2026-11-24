"""Table post-processing for the design report.

The chapter modules write their tables as LaTeX strings. Three problems of the
old report came from those strings, and all three are fixed here, once, for
every table of every chapter (``finalize_tables`` is applied per chapter by
``report_generator.generate_report``):

``repeat_longtable_headers``
    Gives every longtable a proper head and foot::

        \\caption{Title}\\\\ <header> \\endfirsthead
        \\caption[]{Title (continued)}\\\\ <header> \\endhead
        \\multicolumn{n}{r}{Continued on next page}\\\\ \\endfoot
        \\endlastfoot

    so the column header row is printed again at the top of every page the
    table continues on. The first row is only treated as a header when every
    one of its cells is bold, so a data row is never repeated. A table that
    already has ``\\endfirsthead`` / ``\\endhead`` is completed instead: an
    empty continued head is treated as missing, and a full continued head
    without a "(continued)" caption or foot gets them. A long title is
    shortened in the continued caption so that "(continued)" never wraps to a
    line of its own.

``keep_row_groups_together``
    Inside a ``\\multirow`` group the rows are separated by ``\\cline`` (the
    group ends with ``\\hline``). Group labels are made top-aligned
    (``\\multirow[t]``), so the label is printed in the group's first row and
    cannot drift below the last row of a page. Groups of up to
    ``styles.TABLE['keep_together_rows']`` rows are also kept on one page: the
    row ends become ``\\\\*`` (longtable's "no page break here") and the
    ``\\cline`` after them becomes ``\\groupcline``, the same rule without a
    break point after it. A taller group may break; its label stays on top.

``fit_tables_to_width``
    Column widths in the chapter files are proportions. For every longtable
    and tabular whose columns all have absolute widths (``p``/``m``/``b`` and
    the ``C``/``L``/``R`` types of the preamble), the total width is the sum
    of the column widths plus ``2 \\tabcolsep`` per column plus the vertical
    rules. When that is wider than the text block (``styles.text_width_pt``),
    the widths are scaled down proportionally. ``\\tabcolsep`` is the default
    of ``styles.TABLE`` or the preset (``\\compactcols``, ``\\narrowcols``,
    ``\\tightcols``) active where the table starts.

Every transform works table by table and leaves a table unchanged (with a
logged warning) if it cannot parse it, so one unusual table never stops the
report. All transforms are idempotent.

Note on \\needspace: the old preamble ran \\needspace before every longtable.
With a real head (\\endfirsthead / \\endhead) that made longtable break the
page right at the start of some tables: an empty "Continued on next page" foot
was left on one page and the continued head was printed above the first head
on the next. Longtable already keeps its first head together with the first
row, so \\needspace is only used before ordinary ``table`` environments (see
styles.latex_style_block).
"""

from __future__ import annotations

import logging
import re

from . import styles
from .styles import TABLE

logger = logging.getLogger(__name__)

_BEGIN = re.compile(r"\\begin\{longtable\}")
_END = r"\end{longtable}"


# ── Small parsing helpers ────────────────────────────────────────────────────

def _read_group(text: str, start: int, open_ch: str = "{", close_ch: str = "}") -> int:
    """Index just past the balanced group that starts at ``text[start] == open_ch``.

    A backslash escapes the next character, so ``\\{`` and ``\\}`` are not
    counted, while in ``\\\\}`` (a row end followed by a closing brace) the
    brace is.
    """
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced group")


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def _split_top(text: str, sep: str) -> list[str]:
    """Split ``text`` at ``sep`` where it is outside braces (``sep`` is '&' or '\\\\')."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(text):
        if text.startswith(sep, i) and depth == 0 and (sep != "&" or i == 0 or text[i - 1] != "\\"):
            parts.append(text[start:i])
            i += len(sep)
            start = i
            continue
        ch = text[i]
        if ch == "\\" and not text.startswith(sep, i):
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    parts.append(text[start:])
    return parts


def _expand_repeats(spec: str) -> str:
    """Expand ``*{n}{cols}`` repeats in a column spec."""
    out, i = [], 0
    while i < len(spec):
        if spec[i] == "*" and spec.startswith("{", i + 1):
            n_end = _read_group(spec, i + 1)
            body_end = _read_group(spec, n_end)
            n = int(spec[i + 2:n_end - 1].strip())
            out.append(_expand_repeats(spec[n_end + 1:body_end - 1]) * n)
            i = body_end
            continue
        if spec[i] == "{":
            end = _read_group(spec, i)
            out.append(spec[i:end])
            i = end
            continue
        out.append(spec[i])
        i += 1
    return "".join(out)


def column_count(spec: str) -> int:
    """Number of columns in a column spec such as ``|C{2cm}|>{\\centering}p{4cm}|``."""
    spec = _expand_repeats(spec)
    flat, i = [], 0
    while i < len(spec):
        ch = spec[i]
        if ch == "{":
            i = _read_group(spec, i)
            continue
        if ch in "@!<>":
            # @{..} / !{..} are inter-column material, >{..} / <{..} cell code.
            i += 1
            if i < len(spec) and spec[i] == "{":
                i = _read_group(spec, i)
            continue
        flat.append(ch)
        i += 1
    return len([ch for ch in flat if ch.isalpha()])


# ── Header detection ─────────────────────────────────────────────────────────

_WRAPPERS = re.compile(r"\\(multicolumn|multirow|makecell)\*?")
_NOISE = re.compile(r"\\(hline|centering|arraybackslash|raggedright|raggedleft|newline|hfill)\b|"
                    r"\\cline\{[^}]*\}|\[[^\]]*\]|\\\\|\\rowpad|\s")


def _strip_bold(text: str) -> tuple[str, bool]:
    """Remove every ``\\textbf{..}`` group; return the rest and whether bold text was found."""
    out, i, found = [], 0, False
    while i < len(text):
        if text.startswith(r"\textbf", i) and text.startswith("{", _skip_ws(text, i + 7)):
            j = _skip_ws(text, i + 7)
            end = _read_group(text, j)
            if text[j + 1:end - 1].strip():
                found = True
            i = end
            continue
        out.append(text[i])
        i += 1
    return "".join(out), found


def _unwrap(cell: str) -> str:
    """Content of \\multicolumn / \\multirow / \\makecell wrappers (their last argument)."""
    cell = cell.strip()
    while True:
        m = _WRAPPERS.match(cell)
        if not m:
            return cell
        i = _skip_ws(cell, m.end())
        if cell.startswith("[", i):
            i = _skip_ws(cell, _read_group(cell, i, "[", "]"))
        args = []
        while cell.startswith("{", i):
            end = _read_group(cell, i)
            args.append(cell[i + 1:end - 1])
            i = _skip_ws(cell, end)
            if cell.startswith("[", i):  # \multirow[vpos]{n}[bigstruts]{width}{text}
                i = _skip_ws(cell, _read_group(cell, i, "[", "]"))
        if not args or cell[i:].strip():
            return cell
        cell = args[-1].strip()


def is_bold_header(block: str) -> bool:
    """True when every non-empty cell of the header rows in ``block`` is bold."""
    found_bold = False
    for row in _split_top(block, r"\\"):
        for cell in _split_top(row, "&"):
            rest, bold = _strip_bold(_unwrap(cell))
            found_bold = found_bold or bold
            if _NOISE.sub("", rest).strip("{}"):
                return False
    return found_bold


# ── Captions ─────────────────────────────────────────────────────────────────

_LABEL = re.compile(r"\\label\{[^}]*\}")


def _visible_length(tex: str) -> int:
    """Approximate number of printed characters of a caption."""
    s = _LABEL.sub("", tex)
    for src, dst in (("---", "-"), ("--", "-"), ("~", " "), (r"\,", ""), (r"\&", "&"), (r"\%", "%"),
                     (r"\ldots", "..."), ("$", "")):
        s = s.replace(src, dst)
    s = re.sub(r"\\[A-Za-z]+\*?", "", s)
    s = s.replace("{", "").replace("}", "")
    return len(re.sub(r"\s+", " ", s).strip())


def _balanced(text: str) -> bool:
    try:
        return _read_group("{" + text + "}", 0) == len(text) + 2
    except ValueError:
        return False


def continued_caption(caption: str) -> str:
    """Caption text for the continued head: the title, shortened if needed, then "(continued)".

    The printed line is "Table 5.12: <title> (continued)". When it would be
    longer than ``TABLE['continued_caption_chars']`` the title is shortened:
    first a trailing parenthetical is dropped, then whole words are cut and
    replaced by an ellipsis. "(continued)" is joined to the title with a tie.
    """
    cont = TABLE["continued_caption"]
    plain = _LABEL.sub("", caption).strip()
    budget = TABLE["continued_caption_chars"] - len("Table 5.12: ") - len(" " + cont)
    m = re.fullmatch(r"\\textbf\{(.*)\}", plain, re.S)
    head, inner, tail = (r"\textbf{", m.group(1), "}") if m and _balanced(m.group(1)) else ("", plain, "")
    if _visible_length(inner) <= budget:
        return f"{plain}~{cont}"
    short = re.sub(r"\s*\([^(){}]*\)\s*$", "", inner).rstrip(" -:,")
    cut = False
    while _visible_length(short) + (3 if cut else 0) > budget and " " in short.strip():
        short = short.rstrip().rsplit(" ", 1)[0].rstrip(" -:,~")
        cut = True
    if not _balanced(short) or _visible_length(short) + (3 if cut else 0) > budget:
        return cont
    ellipsis = r"\ldots" if cut else ""
    return f"{head}{short}{ellipsis}{tail}~{cont}"


# ── repeat_longtable_headers ─────────────────────────────────────────────────

def _foot(n_cols: int) -> list[str]:
    return [rf"\multicolumn{{{n_cols}}}{{r}}{{\continuednote}}\\", r"\endfoot", r"\endlastfoot"]


def _read_caption(body: str, i: int):
    """Parse ``\\caption[..]{..}`` (+ optional ``\\\\`` and ``\\label``) at ``body[i:]``.

    Returns (caption text including any label, index after it) or (None, i).
    """
    i = _skip_ws(body, i)
    if not body.startswith(r"\caption", i):
        return None, i
    j = i + len(r"\caption")
    if body.startswith("[", j):
        j = _read_group(body, j, "[", "]")
    if not body.startswith("{", j):
        return None, i
    end = _read_group(body, j)
    caption = body[j + 1:end - 1]
    i = _skip_ws(body, end)
    label = re.match(r"\\label\{[^}]*\}", body[i:])
    if label:
        caption += label.group(0)
        i = _skip_ws(body, i + label.end())
    if body.startswith(r"\\", i):  # caption already terminated
        i = _skip_ws(body, i + 2)
    label = re.match(r"\\label\{[^}]*\}", body[i:])
    if label and r"\label" not in caption:
        caption += label.group(0)
        i = _skip_ws(body, i + label.end())
    return caption, i


def _complete_existing_head(body: str, spec: str) -> str | None:
    """A table that already has \\endfirsthead / \\endhead (see module docstring)."""
    efh, eh = body.find(r"\endfirsthead"), body.find(r"\endhead")
    if efh == -1 or eh == -1 or eh < efh:
        return None  # only \endhead: the same head on every page; leave it
    continued = body[efh + len(r"\endfirsthead"):eh]
    if not continued.strip():
        # Empty continued head: the table is effectively head-less on later
        # pages. Drop both markers and treat it like any other table.
        cleaned = body[:efh] + body[eh + len(r"\endhead"):]
        return _transform_plain(cleaned, spec) or cleaned
    if r"\caption" in continued and (r"\endfoot" in body or r"\endlastfoot" in body):
        return None  # already complete
    out = body
    if r"\caption" not in continued:
        caption, _ = _read_caption(body, 0)
        if caption is not None:
            insert = "\n" + rf"\caption[]{{{continued_caption(caption)}}}\\"
            pos = efh + len(r"\endfirsthead")
            out = out[:pos] + insert + out[pos:]
    if r"\endfoot" not in out and r"\endlastfoot" not in out:
        pos = out.find(r"\endhead") + len(r"\endhead")
        out = out[:pos] + "\n" + "\n".join(_foot(max(column_count(spec), 1))) + out[pos:]
    return out


def _transform_plain(body: str, spec: str) -> str | None:
    """A table without \\endfirsthead / \\endhead: build its head and foot."""
    caption, i = _read_caption(body, 0)
    if not body.startswith(r"\hline", i):
        return None
    n_cols = max(column_count(spec), 1)
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
    if not is_bold_header(header[len(r"\hline"):-len(r"\hline")]):
        # The first row is data, not a header, so it must not be repeated. A
        # captioned table still gets a terminated caption (a longtable \caption
        # needs a trailing \\) and a "(continued)" caption with a top rule.
        # The top rule moves into the head: when the body starts with a row,
        # longtable's start-of-table check measures the first row (or the whole
        # first \multirow group) and moves the table to the next page if the
        # caption and that row do not fit, instead of leaving the caption alone
        # at the bottom of the page.
        if caption is None:
            return None
        parts = [rf"\caption{{{caption}}}\\", r"\hline", r"\endfirsthead",
                 rf"\caption[]{{{continued_caption(caption)}}}\\", r"\hline", r"\endhead", *_foot(n_cols)]
        rows = body[header_start + len(r"\hline"):]
        return "\n" + "\n".join(parts) + "\n" + rows.lstrip("\n")
    rest = body[header_end:]
    parts = []
    if caption is not None:
        parts.append(rf"\caption{{{caption}}}\\")
    parts += [header, r"\endfirsthead", ""]
    if caption is not None:
        parts.append(rf"\caption[]{{{continued_caption(caption)}}}\\")
    parts += [header, r"\endhead", "", *_foot(n_cols)]
    return "\n" + "\n".join(parts) + "\n" + rest.lstrip("\n")


def _transform_table(body: str, spec: str) -> str | None:
    """Return the new table body (everything after the column spec) or None to leave it."""
    if r"\endhead" in body or r"\endfirsthead" in body:
        return _complete_existing_head(body, spec)
    return _transform_plain(body, spec)


def _each_longtable(tex: str, transform) -> str:
    """Apply ``transform(body, spec)`` to every longtable; a failure leaves that table alone."""
    out, pos = [], 0
    for match in _BEGIN.finditer(tex):
        if match.start() < pos:
            continue
        end = tex.find(_END, match.end())
        if end == -1:
            break
        try:
            i = match.end()
            if tex.startswith("[", i):
                i = _read_group(tex, i, "[", "]")
            if not tex.startswith("{", i):
                continue
            spec_end = _read_group(tex, i)
            spec = tex[i + 1:spec_end - 1]
            new_body = transform(tex[spec_end:end], spec)
        except Exception as exc:  # one odd table must not stop the report
            logger.warning("longtable left unchanged (%s): %s", transform.__name__, exc)
            continue
        if new_body is None:
            continue
        out.append(tex[pos:spec_end])
        out.append(new_body)
        pos = end
    out.append(tex[pos:])
    return "".join(out)


def repeat_longtable_headers(tex: str) -> str:
    return _each_longtable(tex, _transform_table)


# ── keep_row_groups_together ─────────────────────────────────────────────────

# A row end (\\ or \\[len]) followed, after optional whitespace, by \cline{..}:
# the next row belongs to the same \multirow group.
_ROW_BEFORE_CLINE = re.compile(r"\\\\(?!\*)(\[[^\]]*\])?(\s*)\\cline(\{[^}]*\})")
_MULTIROW = re.compile(r"\\multirow\s*(\[[^\]]*\])?\s*\{\s*(\d+)\s*\}")
_HEAD_END = re.compile(r"\\endlastfoot|\\endfoot|\\endhead|\\endfirsthead")


def _group_rows(body: str, spec: str) -> str:
    """Top-align the \\multirow labels of the table body and protect short groups."""
    head_end = 0
    for m in _HEAD_END.finditer(body):
        head_end = m.end()
    head, rows = body[:head_end], body[head_end:]
    valign = "[" + TABLE["group_label_valign"] + "]"
    out, pos = [], 0
    for m in _MULTIROW.finditer(rows):
        if m.start() < pos:
            continue
        group_end = rows.find(r"\hline", m.end())
        group_end = len(rows) if group_end == -1 else group_end
        group = rows[m.start():group_end]
        if m.group(1) is None:
            group = r"\multirow" + valign + group[len(r"\multirow"):]
        if int(m.group(2)) <= TABLE["keep_together_rows"]:
            # \\* stops a break after the row. \cline is a row of its own and
            # ends with a negative skip where TeX may break, so it becomes
            # \groupcline (styles.GROUP_CLINE), which forbids that break.
            group = _ROW_BEFORE_CLINE.sub(
                lambda r: r"\\*" + (r.group(1) or "") + r.group(2) + r"\groupcline" + r.group(3), group)
        out.append(rows[pos:m.start()])
        out.append(group)
        pos = group_end
    out.append(rows[pos:])
    return head + "".join(out)


def keep_row_groups_together(tex: str) -> str:
    """Top-aligned group labels; no page break inside short \\multirow groups."""
    return _each_longtable(tex, _group_rows)


# ── fit_tables_to_width ──────────────────────────────────────────────────────

_FIXED_COLUMN = "pmbCLR"
_NATURAL_COLUMN = "lcrX"
_EVENTS = re.compile(
    r"\\begingroup\b|\\endgroup\b"
    r"|\\begin\{(?P<begin>[A-Za-z*]+)\}"
    r"|\\end\{(?P<end>[A-Za-z*]+)\}"
    r"|\\(?P<preset>compactcols|narrowcols|tightcols)\b"
    r"|\\setlength\s*\{?\\tabcolsep\}?\s*\{(?P<sep>[^}]*)\}")


def _width_pt(width: str, text_width: float) -> float:
    width = width.strip()
    m = re.fullmatch(r"(\d*\.?\d+)?\s*\\(linewidth|textwidth|columnwidth)", width)
    if m:
        return float(m.group(1) or 1.0) * text_width
    return styles.length_pt(width)


def fit_column_spec(spec: str, col_sep: float, text_width: float | None = None) -> str:
    """Column spec with its absolute widths scaled down to fit ``text_width``.

    Returns ``spec`` unchanged when it already fits, or when a column has no
    fixed width (``l``, ``c``, ``r``, ``X``, ``@{}`` ...), since the width of
    such a table is not known before it is typeset.
    """
    text_width = styles.text_width_pt() if text_width is None else text_width
    original, spec = spec, _expand_repeats(spec)
    rule = styles.length_pt(TABLE["rule_width"])
    widths, rules, i = [], 0, 0  # widths: (start, end, pt) of each width argument
    n_cols = 0
    while i < len(spec):
        ch = spec[i]
        if ch == "|":
            rules += 1
            i += 1
        elif ch in "<>":
            i = _read_group(spec, _skip_ws(spec, i + 1))
        elif ch in "@!":
            return original  # inter-column material of unknown width
        elif ch in _FIXED_COLUMN:
            j = _skip_ws(spec, i + 1)
            end = _read_group(spec, j)
            widths.append((j + 1, end - 1, _width_pt(spec[j + 1:end - 1], text_width)))
            n_cols += 1
            i = end
        elif ch in _NATURAL_COLUMN:
            return original
        else:
            i += 1
    if not widths:
        return original
    content = sum(w for _s, _e, w in widths)
    overhead = n_cols * 2 * col_sep + rules * rule
    if content + overhead <= text_width + 0.1:
        return original
    factor = (text_width - overhead - styles.length_pt(TABLE["fit_margin"])) / content
    if factor <= 0:
        return original
    out, pos = [], 0
    for start, end, w in widths:
        out.append(spec[pos:start])
        out.append(f"{w * factor / styles.length_pt('1cm'):.3f}cm")
        pos = end
    out.append(spec[pos:])
    return "".join(out)


def fit_tables_to_width(tex: str, text_width: float | None = None) -> str:
    """Scale the column widths of every too-wide longtable / tabular (see module docstring)."""
    text_width = styles.text_width_pt() if text_width is None else text_width
    presets = styles.col_sep_presets()
    stack = [presets["default"]]
    out, pos = [], 0
    for m in _EVENTS.finditer(tex):
        if m.start() < pos:
            continue
        token = m.group(0)
        if token.startswith(r"\begingroup"):
            stack.append(stack[-1])
        elif token.startswith(r"\endgroup"):
            if len(stack) > 1:
                stack.pop()
        elif m.group("preset"):
            stack[-1] = presets[m.group("preset")]
        elif m.group("sep") is not None:
            try:
                stack[-1] = styles.length_pt(m.group("sep"))
            except ValueError:
                pass
        elif m.group("end"):
            if len(stack) > 1:
                stack.pop()
        elif m.group("begin"):
            env = m.group("begin")
            col_sep = stack[-1]
            stack.append(col_sep)
            if env not in ("longtable", "tabular"):
                continue
            try:
                i = m.end()
                if tex.startswith("[", i):
                    i = _read_group(tex, i, "[", "]")
                if not tex.startswith("{", i):
                    continue
                spec_end = _read_group(tex, i)
                spec = tex[i + 1:spec_end - 1]
                new_spec = fit_column_spec(spec, col_sep, text_width)
            except Exception as exc:
                logger.warning("table width left unchanged: %s", exc)
                continue
            if new_spec != spec:
                out.append(tex[pos:i + 1])
                out.append(new_spec)
                pos = spec_end - 1
    out.append(tex[pos:])
    return "".join(out)


def finalize_tables(tex: str) -> str:
    """All table transforms, in order (see module docstring)."""
    for transform in (repeat_longtable_headers, keep_row_groups_together, fit_tables_to_width):
        try:
            tex = transform(tex)
        except Exception as exc:  # never lose the chapter because of a transform
            logger.warning("%s skipped: %s", transform.__name__, exc)
    return tex
