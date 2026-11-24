"""Headless OsdagBridge run: load an .osi, run the design, write the PDF report.

Usage: python make_report.py INPUT.osi OUTPUT_DIR FILE_STEM
Used to produce Report_Before.pdf / Report_After.pdf from identical inputs.

The run steps are the ones the desktop app takes after File > Load Input,
Design and File > Create Design Report: solve_extend_basic_input_dict(),
PlateGirderBridge.set_input() + design(), then generate_design_report().

Everything runs inside main(), behind the ``if __name__ == "__main__"`` guard.
Stage 7 (cross bracing and end diaphragm design) sends the member designs to a
process pool (osdagbridge.core.utils.connect.design_pool, forkserver start
method). Each pool worker re-imports the main module; without the guard a
worker would run this whole script again, die, and every bracing design was
reported as "A process in the process pool was terminated abruptly". That is
why the earlier headless reports had no cross-bracing or end-diaphragm results.

KEEP_TMP=dir keeps the LaTeX build folder (.tex, .log, images) in ``dir``.
"""
import contextlib
import datetime
import logging
import os
import sys
import time
from unittest import mock

import yaml


@contextlib.contextmanager
def _keep_build_folder(path):
    """Make generate_report() build in ``path`` instead of a deleted temp folder."""
    if not path:
        yield
        return
    from osdagbridge.core.reports import report_generator
    os.makedirs(path, exist_ok=True)
    with mock.patch.object(report_generator.tempfile, "TemporaryDirectory",
                           lambda *a, **k: contextlib.nullcontext(path)):
        yield


def main(osi, out_dir, stem):
    from osdagbridge.core.bridge_types.plate_girder.defaults import solve_extend_basic_input_dict
    from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
    from osdagbridge.core.reports.report_generator import (
        ReportMetadata, ReportOptions, ReportRequest,
    )

    logging.basicConfig(level=logging.WARNING)

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
    # The same fields the report dialog fills (report_options.build_request):
    # project_location stays empty, so the report reads the location and its
    # weather data (wind speed, seismic zone, shade temperatures) from the
    # .osi's project.location entry, as in the GUI.
    request = ReportRequest(
        metadata=ReportMetadata(
            project_name="30 m Plate Girder Bridge (screening task)", project_location="",
            designer="Saharsh Tibrewala", client="FOSSEE", company="FOSSEE, IIT Bombay",
            group_name="FOSSEE, IIT Bombay", subtitle="Rev 0", job_number="WI-2026-01",
            report_date=datetime.date.today().isoformat(), reviewer="",
        ),
        options=ReportOptions(sections=sections, include_figures=True, include_toc=True, include_pdf=True),
        output_dir=out_dir,
        file_stem=stem,
    )
    with _keep_build_folder(os.environ.get("KEEP_TMP")):
        result = bridge.generate_design_report(request, cad_generator={})
    print(result)
    return 0 if result.pdf_path else 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:4]))
