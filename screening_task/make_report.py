"""Headless OsdagBridge run: load an .osi, run the design, write the PDF report.

Usage: python make_report.py INPUT.osi OUTPUT_DIR FILE_STEM
Used to produce Report_Before.pdf / Report_After.pdf from identical inputs.
"""
import datetime
import logging
import sys
import time

import yaml
import contextlib
import os
import tempfile

# KEEP_TMP=dir keeps the LaTeX build directory (log, images) for inspection.
if os.environ.get("KEEP_TMP"):
    _keep = os.environ["KEEP_TMP"]
    os.makedirs(_keep, exist_ok=True)
    tempfile.TemporaryDirectory = lambda *a, **k: contextlib.nullcontext(_keep)

from osdagbridge.core.bridge_types.plate_girder.defaults import solve_extend_basic_input_dict
from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
from osdagbridge.core.reports.report_generator import (
    ReportMetadata, ReportOptions, ReportRequest,
)

logging.basicConfig(level=logging.WARNING)

osi, out_dir, stem = sys.argv[1], sys.argv[2], sys.argv[3]
with open(osi) as fh:
    data = yaml.safe_load(fh)
solve_extend_basic_input_dict(data)

t0 = time.time()
bridge = PlateGirderBridge()
bridge.set_input(data)
bridge.design()
print(f"design finished in {time.time() - t0:.1f}s", file=sys.stderr)

sections = ["exec_summary", "project_info", "input_parameters", "loads", "analysis",
            "design_checks", "drawings", "quantities", "standards", "design_log_window", "references"]
request = ReportRequest(
    metadata=ReportMetadata(
        project_name="30 m Plate Girder Bridge (screening task)", project_location="Pune, Maharashtra",
        designer="Saharsh Tibrewala", client="FOSSEE", company="FOSSEE, IIT Bombay",
        group_name="FOSSEE, IIT Bombay", subtitle="Rev 0", job_number="WI-2026-01",
        report_date=datetime.date.today().isoformat(), reviewer="",
    ),
    options=ReportOptions(sections=sections, include_figures=True, include_toc=True, include_pdf=True),
    output_dir=out_dir,
    file_stem=stem,
)
result = bridge.generate_design_report(request, cad_generator={})
print(result)
