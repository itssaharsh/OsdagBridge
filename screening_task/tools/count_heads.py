"""Count longtable heads in a generated report .tex (KEEP_TMP build folder or the
.tex written next to the PDF): longtables, repeated heads (a non-empty block
between \\endfirsthead and \\endhead, or an \\endhead alone), "(continued)"
captions, empty continued heads and "Continued on next page" feet.

Usage: python tools/count_heads.py REPORT.tex [MORE.tex ...]
"""
import re, sys
for path in sys.argv[1:]:
    tex = open(path).read()
    tables = re.findall(r"\\begin\{longtable\}(.*?)\\end\{longtable\}", tex, re.S)
    rep = cont = foot = empty = 0
    for t in tables:
        if r"\endhead" in t:
            pre = t.split(r"\endhead")[0]
            block = pre.split(r"\endfirsthead")[1] if r"\endfirsthead" in pre else pre
            if block.strip():
                rep += 1
                if "(continued)" in block: cont += 1
            else:
                empty += 1
        if r"\endfoot" in t: foot += 1
    print(f"{path.split('/')[-1]}: longtables {len(tables)}, repeated head {rep} (with '(continued)' caption {cont}), "
          f"empty continued head {empty}, 'Continued on next page' foot {foot}")
