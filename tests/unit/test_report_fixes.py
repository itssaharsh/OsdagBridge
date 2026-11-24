"""Tests for fixes found while reviewing the report changes."""

import math

import matplotlib
import pytest

from osdagbridge.core.reports import report_charts
from osdagbridge.core.reports.chap3 import _live_load_tables
from osdagbridge.core.reports.report_generator import _header_text
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.common import (
    KEY_LL_IRC_70R_TRACKED, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_AA_WHEELED, KEY_SPAN,
)


@pytest.mark.parametrize("span, tracked, expected", [
    (4.0, True, 0.25), (7.0, True, 0.175), (9.0, True, 0.10), (30.0, True, 0.10),
    (7.0, False, 0.25), (23.0, False, 0.25), (30.0, False, round(9 / 43.5, 3)),
])
def test_cl_208_3_separates_wheeled_and_tracked_vehicles(span, tracked, expected):
    assert IRC6_2017.cl_208_3_impact_factor(span, tracked=tracked) == expected


def test_cl_208_3_without_vehicle_type_is_unchanged_for_existing_callers():
    assert IRC6_2017.cl_208_3_impact_factor(30.0) == 0.10


def test_live_load_table_shows_different_factors_for_wheeled_and_tracked():
    # No carriageway width: no vehicle is matched to the analysis, so every row
    # shows the IRC 6 Cl. 208.3 value for its vehicle type.
    tex = _live_load_tables({KEY_SPAN: 30, KEY_LL_IRC_70R_WHEELED: True,
                             KEY_LL_IRC_AA_WHEELED: True, KEY_LL_IRC_70R_TRACKED: True})
    rows = {line.split("&")[0].strip(): line.split("&")[2].strip()
            for line in tex.splitlines() if line.startswith("Class ")}
    assert rows["Class 70R Wheeled"] == rows["Class AA Wheeled"] == "1.207"
    assert rows["Class 70R Tracked"] == "1.100"


def test_long_project_name_is_shortened_in_the_header():
    name = "Widening and strengthening of the plate girder bridge over the Mula-Mutha river"
    text = _header_text(name, 50)
    assert text.endswith(r"\ldots{}") and len(text) < 60
    assert _header_text("Short name", 50) == "Short name"


def test_charts_leave_matplotlib_global_state_alone(tmp_path):
    backend = matplotlib.get_backend()
    rc = dict(matplotlib.rcParams)
    points = [report_charts.URPoint("Steel Plate Girders", "Moment", 0.8)]
    assert report_charts.utilization_chart(points, str(tmp_path))
    assert report_charts.element_summary_chart(points, str(tmp_path))
    assert matplotlib.get_backend() == backend
    assert dict(matplotlib.rcParams) == rc


def test_nan_values_are_drawn_as_not_available(tmp_path):
    points = [report_charts.URPoint("Steel Plate Girders", "Moment", 0.8),
              report_charts.URPoint("Steel Plate Girders", "Shear", math.inf),
              report_charts.URPoint("End Diaphragms", "Moment", math.nan)]
    assert report_charts.utilization_chart(points, str(tmp_path))
    assert report_charts.element_summary_chart(points, str(tmp_path))
    only_bad = [report_charts.URPoint("Cross Bracing", "Tension", math.nan)]
    assert report_charts.utilization_chart(only_bad, str(tmp_path)) is None
    assert report_charts.steel_tonnage_chart({"steel_girders_wt_total": "inf"}, str(tmp_path)) is None


def test_chart_paths_are_relative_to_the_latex_build_folder(tmp_path):
    out_dir = str(tmp_path / "images")
    path = report_charts.utilization_chart([report_charts.URPoint("Cross Bracing", "Tension", 0.5)], out_dir)
    assert report_charts.tex_path(path, out_dir) == "images/ur_by_element.pdf"
    assert report_charts.tex_path(path, out_dir + "/") == "images/ur_by_element.pdf"
