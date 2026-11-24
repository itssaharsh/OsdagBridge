# Screening task: LaTeX Report Generator Refactoring & Enhancements

FOSSEE Osdag Winter Internship 2026, software development task.
Saharsh Tibrewala, B.Tech CSE (AI), Vishwakarma Institute of Technology, Pune.

The code changes are in `src/osdagbridge/core/reports/`, plus one helper in
`src/osdagbridge/core/utils/codes/irc6_2017.py`, on the branch
`report-generator-enhancements`, based on `dev` at `d74f56d`.
`Technical_Changes.pdf` explains each change, why it was made and how it was checked.

## What changed

| # | Task item | Where |
|---|-----------|-------|
| 1 | Every longtable repeats its column header on every page, with a "(continued)" caption and a "Continued on next page" foot | `latex_tables.py` |
| 2 | Layout: every table is scaled to the text width; multirow group labels are top-aligned and short groups stay on one page; page geometry set explicitly | `latex_tables.py`, `styles.py` |
| 3 | Live loads split into three tables (vehicles, associated forces, footway) that follow Additional Inputs > Loading | `chap3.py` |
| 4 | Numbered utilization ratio charts in Section 5.5, per element and per check, with a UR = 1.0 line | `report_charts.py`, `chap5.py` |
| 5 | Numbered material quantity charts in Chapter 7: steel tonnage, concrete vs reinforcement mass | `report_charts.py`, `chap7.py` |
| 6 | Central style system: page, fonts, captions, headings, title page, table padding and widths, spacing, header and footer, figures, charts | `styles.py` |

Section 8 of the write-up lists the fixes made after a review of the first
version: Table 2.8 and Table 4.1 heads, table widths, the chart cross-reference
and numbering, Table 2.7 units, the impact factor and braking rows of Chapter 3,
the charts, and the headless run that skipped the cross-bracing design.

## Results on the same input (`baseline_30m.osi`, 30 m span, Pune)

Both reports are headless runs of `make_report.py` (same steps as the GUI's
Load Input, Design and Create Design Report; see below).

| Check | Before (`dev`) | After (this branch) |
|-------|----------------|---------------------|
| LaTeX errors in the pdflatex log | 139 | 0 |
| Overfull `\hbox` warnings (tables or text past the margin) | 59 | 0 |
| Longtables that repeat their column header on later pages | 1 of 49 | 51 of 51 |
| Words printed right of the text block (`tools/check_footer.py`) | 267 | 0 |
| Pages that start with table rows but no head (`tools/check_heads.py`) | 9 | 0 |
| Body text below the text block, e.g. "G4" on the footer (`tools/check_footer.py`) | 1 (page 28) | 0 |
| Unit tests | 3 pass | 52 pass |

## Files

| File | What it is |
|------|------------|
| `Report_Before.pdf` | report from the unmodified `dev` code |
| `Report_After.pdf` | report from this branch, made the same way as `Report_Before.pdf` (headless, same `.osi`) |
| `Report_After_GUI.pdf` | report from this branch made in the GUI (File > Create Design Report), as in the video |
| `Technical_Changes.pdf` / `.md` | technical write-up with before/after screenshots |
| `baseline_30m.osi` | the input file used for both reports |
| `make_report.py` | headless run: load `.osi`, design, write the PDF report |
| `tools/check_footer.py` | finds body text below the text block (e.g. a row label on the footer) or right of it |
| `tools/check_heads.py` | finds pages that start with table rows but no table head |
| `tools/check_tables2.py` | finds a "(continued)" head on the same page as the table's first head |
| `tools/check_orphans.py` | finds a caption and header left alone at the bottom of a page |
| `tools/count_heads.py` | counts longtables, repeated heads and feet in a generated `.tex` |
| `tools/pdfpages.py` | shared helpers of the PDF checks |
| `logs/` | pdflatex logs (before and after, as .txt), error and warning counts, pytest output, PDF check output |

## Reproduce

```bash
# from the repository root, inside the osdagbridge conda environment
python -m pytest tests/unit -q                      # 52 passed

# headless report from this branch
cd screening_task
KEEP_TMP=build_after python make_report.py baseline_30m.osi out Report_After
grep -c '^!' build_after/Report_After.log           # 0
grep -c 'Overfull' build_after/Report_After.log     # 0

# the same for dev: a checkout of dev next to the repository, on PYTHONPATH
git worktree add ../../osdag_dev dev
KEEP_TMP=build_before PYTHONPATH=../../osdag_dev/src python make_report.py baseline_30m.osi out Report_Before
grep -c '^!' build_before/Report_Before.log         # 139

python tools/check_footer.py out/Report_After.pdf                       # all "none"
python tools/check_heads.py out/Report_After.pdf                        # none
python tools/check_footer.py out/Report_Before.pdf --bottom-margin 1in  # G4 on page 28
python tools/count_heads.py out/Report_Before.tex out/Report_After.tex
```

`make_report.py` runs everything inside `main()` behind an
`if __name__ == "__main__"` guard. Stage 7 of the design (cross bracing and end
diaphragms) sends its member designs to a process pool whose workers re-import
the main module; without the guard each worker ran the script again and died,
so the earlier headless reports had no bracing results. It also leaves the
report's project location empty, as the report dialog does, so the location and
its weather data come from the `.osi` file.

The check scripts call `pdftotext` and `pdftohtml` from poppler-utils
(`sudo apt install poppler-utils`).
