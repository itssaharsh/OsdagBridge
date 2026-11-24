"""Find table text printed inside the footer area (below the last text line
limit), e.g. a multirow label like 'G4' that spilled past the page bottom."""
import re, subprocess, sys
pdf = sys.argv[1]
out = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True).stdout
hits = []
for pno, page in enumerate(out.split("<page ")[1:], 1):
    words = re.findall(r'yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">([^<]*)</word>', page)
    footer_y = max((float(y) for y, _, w in words if w == "Osdag"), default=None)
    if footer_y is None:
        continue
    for y, ymax, w in words:
        if re.fullmatch(r"G\d+|G\d+-G\d+", w) and float(y) > footer_y - 25:
            hits.append((pno, w))
print("labels in footer:", hits if hits else "none")
