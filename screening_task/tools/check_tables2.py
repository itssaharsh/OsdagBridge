"""Detect longtable doubled heads: a page whose text contains '<title> (continued)'
and also '<title>' as a first caption (Table N.N: <title> without continued)."""
import re, subprocess, sys
pdf = sys.argv[1]
pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
bad, orphan = [], []
for p in range(1, pages + 1):
    t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
    conts = re.findall(r"(?:Table [\d.]+: )?([^\n]+?) \(continued\)", t)
    for c in conts:
        title = c.split(": ", 1)[-1]
        if re.search(r"Table [\d.]+: " + re.escape(title) + r"\s*\n", t):
            bad.append((p, title[:40]))
print("doubled heads:", bad if bad else "none")
