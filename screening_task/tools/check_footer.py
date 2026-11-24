"""Find body text outside the text block: below its bottom edge (in the footer
band) or right of its right edge (in the margin).

The text block comes from the page geometry: by default the report's
(styles.PAGE: 1in side margins, 1.2in bottom margin); pass --bottom-margin 1in
for a report built with the old dev geometry. The running footer (the footer
line and the "* Software default value" note above its rule) is not body text.
Also lists girder labels (G1, G1-G2 ...) found in the footer band, as before.

Usage: python tools/check_footer.py REPORT.pdf [--bottom-margin 1.2in] [--side-margin 1in]
"""
import argparse
import re

from pdfpages import is_footer_or_header, length_bp, words

TOL = 4.0  # bp: descenders of the last line (g, y, parentheses) and rounding


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--bottom-margin", default="1.2in")
    ap.add_argument("--side-margin", default="1in")
    args = ap.parse_args()
    bottom, side = length_bp(args.bottom_margin), length_bp(args.side_margin)
    below, right, labels = [], [], []
    for pno, width, height, items in words(args.pdf):
        text_bottom, text_right = height - bottom, width - side
        for x0, y0, x1, y1, t in items:
            if t in ("\x88", "\u2022"):
                continue  # list bullet: poppler reports the whole font box for it
            if y1 > text_bottom + TOL and not is_footer_or_header(t):
                below.append((pno, t))
            if re.fullmatch(r"G\d+|G\d+-G\d+", t) and y1 > text_bottom + TOL:
                labels.append((pno, t))
            if x1 > text_right + TOL:
                right.append((pno, t))
    print("body text below the text block:", below if below else "none")
    print("text right of the text block:", right[:20] if right else "none",
          f"({len(right)} words)" if len(right) > 20 else "")
    print("labels in footer:", labels if labels else "none")


if __name__ == "__main__":
    main()
