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
| 1 | Table headers repeat on every page, with "(continued)" and "Continued on next page" | `latex_tables.py` |
| 2 | Footer overlap and spacing: multirow groups are never split by a page break; page geometry set explicitly | `latex_tables.py`, `styles.py` |
| 3 | Live loads split into three tables: vehicle live loads, forces associated with them (braking, centrifugal), footway live load | `chap3.py` |
| 4 | Utilization ratio charts in Section 5.5, per element and per check, with a UR = 1.0 line | `report_charts.py`, `chap5.py` |
| 5 | Material quantity charts in Chapter 7: steel tonnage, concrete vs reinforcement | `report_charts.py`, `chap7.py` |
| 6 | Central style system for page geometry, colours, fonts, padding, spacing, header and footer, charts | `styles.py` |

A second review fixed four more problems (section 7 of the write-up): the
charts no longer change matplotlib's backend or settings inside the desktop
app, chart paths are relative to the LaTeX build folder, `inf`/`nan` values no
longer stop the report, and long project names no longer run into the header
date. It also found that the Class 70R / AA impact factor ignored the vehicle
type; the report now shows 1.207 for wheeled and 1.100 for tracked vehicles on
a 30 m span.

## Results on the same input (`baseline_30m.osi`, 30 m span, Pune)

| Check | Before (`dev`) | After (this branch) |
|-------|----------------|---------------------|
| LaTeX errors in the pdflatex log | 139 | 0 |
| Girder labels printed in the footer | 1 ("G4", page 28) | 0 |
| Longtables with a repeated header | 2 of 49 | 51 of 51 |
| Unit tests | 3 pass | 25 pass |

## Files

| File | What it is |
|------|------------|
| `Report_Before.pdf` | report from the unmodified `dev` code |
| `Report_After.pdf` | report from this branch, made the same way as `Report_Before.pdf` (headless, same `.osi`) |
| `Report_After_GUI.pdf` | report from this branch made in the GUI (File > Create Design Report), as in the video |
| `Technical_Changes.pdf` / `.md` | technical write-up with before/after screenshots |
| `baseline_30m.osi` | the input file used for both reports |
| `make_report.py` | headless run: load `.osi`, design, write the PDF report |
| `tools/check_footer.py` | finds row labels printed in a page's footer band |
| `tools/check_tables2.py` | finds a "(continued)" head on the same page as the table's first head |
| `tools/check_orphans.py` | finds a caption and header left alone at the bottom of a page |
| `logs/` | pdflatex logs (before and after, as .txt), error counts, pytest output, PDF check output |

## Reproduce

```bash
# from the repository root, inside the osdagbridge conda environment
python -m pytest tests/unit -q

# headless report from this branch
cd screening_task
KEEP_TMP=build_after python make_report.py baseline_30m.osi out Report_After
grep -c '^!' build_after/Report_After.log      # 0

# the same for dev: check out dev in a worktree and point PYTHONPATH at its src/
git worktree add /tmp/osdag_dev dev
KEEP_TMP=build_before PYTHONPATH=/tmp/osdag_dev/src python make_report.py baseline_30m.osi out Report_Before
grep -c '^!' build_before/Report_Before.log    # 139

python tools/check_footer.py out/Report_Before.pdf   # labels in footer: [(28, 'G4')]
python tools/check_footer.py out/Report_After.pdf    # labels in footer: none
```

Values that come out of the design run, such as the railing load, can differ
between a GUI run and a headless run of the same `.osi` file, so the before/after
comparison uses two headless runs.

The check scripts call `pdftotext` from poppler-utils (`sudo apt install poppler-utils`).
