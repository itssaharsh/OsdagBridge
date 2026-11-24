"""Find pages that start with table rows but no table head.

The first body line of each page (below the running header) is a table row
when it holds two or more text runs set apart like table columns. Such a line
is a proper continued head when it is a "Table N.N: ... (continued)" caption
or when every run on it is bold (a repeated column header). Otherwise the page
continues a table without its head, which is what the old Table 2.8 did.

Usage: python tools/check_heads.py REPORT.pdf
"""
import re
import sys

from pdfpages import is_footer_or_header, runs

COLUMN_GAP = 14  # pt between runs on one line that marks separate table columns
SAME_LINE = 3    # pt


def first_body_line(items, page_height):
    body = [r for r in items if not is_footer_or_header(r[5]) or r[0] > 80]
    # The running header is the topmost line; skip it.
    header_top = min((r[0] for r in items), default=0)
    body = [r for r in body if r[0] > header_top + SAME_LINE and r[0] < page_height - 90]
    if not body:
        return []
    top = min(r[0] for r in body)
    return sorted((r for r in body if abs(r[0] - top) <= SAME_LINE), key=lambda r: r[1])


def main():
    pdf = sys.argv[1]
    missing = []
    for pno, height, items in runs(pdf)[1:]:
        line = first_body_line(items, height)
        if len(line) < 2:
            continue
        gaps = [b[1] - (a[1] + a[2]) for a, b in zip(line, line[1:])]
        if max(gaps) < COLUMN_GAP:
            continue  # ordinary text line
        text = " ".join(r[5] for r in line)
        if re.match(r"(Table|Figure)\s+[\d.]+:", text) or all(r[4] for r in line):
            continue
        if re.match(r"\d+(\.\d+)*$", line[0][5]) or line[0][5][:1] in "[\u2022\x88" or text.startswith("Note:"):
            continue  # numbered heading, figure placeholder, list bullet or table note
        missing.append((pno, text[:60]))
    print("pages starting with table rows but no head:", missing if missing else "none")


if __name__ == "__main__":
    main()
