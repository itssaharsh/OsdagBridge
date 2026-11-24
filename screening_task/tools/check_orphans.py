"""Find table heads left alone at the bottom of a page: the last 'Table N.N:' caption
on a page that is followed by nothing but its header line (and the footer)."""
import re, subprocess, sys
pdf = sys.argv[1]
pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
orphans = []
for p in range(1, pages + 1):
    t = subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    body = [l for l in lines if not l.startswith("Osdag |") and "Rev 0" not in l and "Continued on next page" not in l and "Software default value" not in l]
    idx = [i for i, l in enumerate(body) if re.match(r"Table [\d.]+:", l)]
    if idx and len(body) - idx[-1] <= 3 and "(continued)" not in body[idx[-1]]:
        orphans.append((p, body[idx[-1]][:50]))
print("orphaned heads:", orphans if orphans else "none")
