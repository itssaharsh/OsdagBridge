"""Shared helpers for the PDF checks: words and text runs of every page, and the
text-block geometry of the report. Needs poppler-utils (pdftotext, pdftohtml)."""
import re
import subprocess
import xml.etree.ElementTree as ET

PT_PER = {"pt": 72.0 / 72.27, "bp": 1.0, "in": 72.0, "cm": 72.0 / 2.54, "mm": 72.0 / 25.4}


def length_bp(value):
    """'1.2in' / '2cm' / '18pt' in PDF points (bp)."""
    m = re.fullmatch(r"\s*(\d*\.?\d+)\s*(pt|bp|in|cm|mm)\s*", value)
    if not m:
        raise ValueError(f"bad length {value!r}")
    return float(m.group(1)) * PT_PER[m.group(2)]


def words(pdf):
    """[(page_no, page_width, page_height, [(xmin, ymin, xmax, ymax, text), ...]), ...]"""
    out = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True, check=True).stdout
    pages = []
    for pno, chunk in enumerate(out.split("<page ")[1:], 1):
        w, h = (float(v) for v in re.match(r'width="([\d.]+)" height="([\d.]+)"', chunk).groups())
        items = [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in re.findall(
            r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', chunk)]
        pages.append((pno, w, h, items))
    return pages


def runs(pdf):
    """Text runs with fonts: [(page_no, page_height, [(top, left, width, height, bold, text), ...]), ...]"""
    xml = subprocess.run(["pdftohtml", "-xml", "-i", "-q", "-zoom", "1", "-stdout", pdf],
                         capture_output=True, text=True, check=True).stdout
    root = ET.fromstring(xml)
    pages, fonts = [], {}
    for page in root.iter("page"):
        # A fontspec is written once, on the first page that uses the font.
        fonts.update({f.get("id"): f.get("family", "") for f in page.iter("fontspec")})
        items = []
        for t in page.iter("text"):
            text = "".join(t.itertext()).strip()
            if not text:
                continue
            family = fonts.get(t.get("font"), "")
            bold = bool(re.search(r"CMBX|Bold|bx", family))
            items.append((int(t.get("top")), int(t.get("left")), int(t.get("width")),
                          int(t.get("height")), bold, text))
        pages.append((int(page.get("number")), int(float(page.get("height"))), items))
    return pages


def is_footer_or_header(text):
    """Running header / footer text of the report (not body text)."""
    return bool(re.search(r"Osdag|FOSSEE|Indian|Institute|Technology|Bombay|^Page$|^of$|^\|$|Software|default|value|^\*$", text)) \
        or bool(re.fullmatch(r"\d+", text))
