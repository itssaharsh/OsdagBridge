# =============================================================================
# Chapter 3: Loads and Load Combinations
# Extracted from report_generator.py — DO NOT add business logic here.
# =============================================================================

from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV,
    KEY_CB_LOAD,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_DAMPING,
    KEY_SL_DEAD_LOAD_MODE,
    KEY_SL_DEAD_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_LIVE_LOAD_MODE,
    KEY_SL_LIVE_LOAD_VALUE,
    KEY_SL_SEISMIC_ZONE,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_TIME_PERIOD,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE,
    KEY_CARRIAGEWAY_WIDTH,
    KEY_TS_NO_OF_FOOTPATHS,
)

from osdagbridge.core.reports.report_utils import _tex, _render_value

def ch3_loads(input_dict):
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

    # Vz / Pz — prefer stored computed values; fall back to IRC6 Table 12
    vz_val = input_dict.get(KEY_WL_HOURLY_MEAN_WIND)
    pz_val = input_dict.get(KEY_WL_HOURLY_WIND_PRESSURE)
    if not vz_val or not pz_val:
        try:
            _vb  = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get('wind_speed')
            _h   = input_dict.get(KEY_WL_AVG_EXPOSED_HEIGHT)
            _ter = {
                "Plain Terrain": "plain",
                "Terrain with Obstructions": "obstructed",
            }.get(str(input_dict.get(KEY_WL_TERRAIN_TYPE, "")).strip(), "plain")
            _res = IRC6_2017.table_12(float(_h), _ter, float(_vb))
            if not vz_val:
                vz_val = _res.get("Vz")
            if not pz_val:
                pz_val = _res.get("Pz")
        except Exception:
            pass
    vz_str = f"{float(vz_val):.2f} m/s" if vz_val not in (None, "") else "N/A"
    pz_str = f"{float(pz_val):.2f} N/m²" if pz_val not in (None, "") else "N/A"

    # Table 3.5 — Seismic: prefer stored computed values; fall back to IRC6 cl_218_5_1
    sl_zone_factor = input_dict.get(KEY_SL_ZONE_FACTOR)
    sl_spectral    = input_dict.get(KEY_SL_SPECTRAL_COEFF)
    sl_ah          = input_dict.get(KEY_SL_HORIZONTAL_COEFF)
    sl_av          = input_dict.get(KEY_SL_VERTICAL_COEFF)
    if not sl_ah or not sl_zone_factor:
        try:
            _zone = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get('seismic_zone')
            _zmap = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}
            _z    = str(_zone).strip().upper()
            if _z.isdigit():
                _z = _zmap.get(_z)
            _smap = {"Type I – Rocky or Hard": 1, "Type II – Medium Soil": 2, "Type III – Soft Soil": 3}
            _st   = _smap.get(str(input_dict.get(KEY_SL_SOIL_TYPE, "")), 1)
            _tp   = input_dict.get(KEY_SL_TIME_PERIOD)
            _damp = input_dict.get(KEY_SL_DAMPING) or "5"
            _dl_v = input_dict.get(KEY_SL_DEAD_LOAD_VALUE)
            _ll_v = input_dict.get(KEY_SL_LIVE_LOAD_VALUE)
            _dead = float(_dl_v) if str(input_dict.get(KEY_SL_DEAD_LOAD_MODE, "")) == "Custom" and _dl_v else 0.0
            _live = float(_ll_v) if str(input_dict.get(KEY_SL_LIVE_LOAD_MODE, "")) == "Custom" and _ll_v else 0.0
            _res  = IRC6_2017.cl_218_5_1(zone=f"Zone {_z}", soil_type=_st, dead_load_kN=_dead,
                        live_load_kN=_live, period_T=float(_tp) if _tp else None,
                        damping_percent=float(_damp))
            if not sl_zone_factor:
                sl_zone_factor = _res.get("Z")
            if not sl_spectral:
                sl_spectral    = _res.get("Sa_g_adjusted")
            if not sl_ah:
                sl_ah          = _res.get("Ah")
            if not sl_av:
                sl_av          = round(_res.get("Ah", 0) * 2 / 3, 4)
        except Exception:
            pass

    def _sl(v, unit=""):
        return f"{float(v):.4f}{unit}" if v not in (None, "") else "N/A"

    # Table 3.6 — Temperature: compute effective bridge temp range from shade temps
    tl_temp_min = tl_temp_max = tl_rise = tl_fall = "N/A"
    try:
        _tmax = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get('shade_temp_max')
        _tmin = input_dict.get(KEY_TL_LOWEST_MIN_TEMP)  or input_dict.get('shade_temp_min')
        if _tmax and _tmin:
            _res    = IRC6_2017.cl_215_2_effective_bridge_temperature(
                          float(_tmax), float(_tmin), 'metallic', False)
            _bt_min = _res.get('T_min', 0)
            _bt_max = _res.get('T_max', 0)
            _mean   = (_bt_max + _bt_min) / 2.0
            tl_temp_min = f"{_bt_min:.2f}"
            tl_temp_max = f"{_bt_max:.2f}"
            tl_rise     = f"{_bt_max - _mean:.2f}"
            tl_fall     = f"{_mean - _bt_min:.2f}"
    except Exception:
        pass

    # --- Table 3.7: Load Combinations (dynamically generated from IRC 6) ---
    _LOAD_LABEL_MAP = {
        'dead_load':         'DL',
        'surfacing':         'SIDL',
        'live_load':         'LL',
        'wind_load':         'WL',
        'thermal_load':      'TL',
        'vehicle_collision': 'VC',
        'barge_impact':      'BI',
        'floating_bodies':   'FB',
        'seismic':           'EQ',
    }

    def _fmt_factors(factors):
        """Format a factors dict into a compact load-case string for the table."""
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):  # permanent load with adding/relieving
                add = val.get('adding')
                rel = val.get('relieving')
                add_s = f"{add:.2f}" if add is not None else '--'
                rel_s = f"{rel:.2f}" if rel is not None else '--'
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue  # skip N/A factors
                parts.append(f"{label}({val:.2f})")
        return ' + '.join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        cases = _fmt_factors(combo['factors'])
        lc_rows.append(
            f"ULS-{i:02d}" + r" & " + cases + r" \\[\rowpad]" + "\n"
            + r"\hline"
        )
    for i, combo in enumerate(sls_combos, start=1):
        cases = _fmt_factors(combo['factors'])
        lc_rows.append(
            f"SLS-{i:02d}" + r" & " + cases + r" \\[\rowpad]" + "\n"
            + r"\hline"
        )

    lc_rows_str = "\n".join(lc_rows)

    live_load_tables = _live_load_tables(input_dict)

    def _or_not_computed(text):
        return text if text not in (None, "") else "Not computed"

    return r"""
\chapter{Loads and Load Combinations}

This section summarizes all loads applied to the bridge and the load combinations considered for analysis and design.

\tablegap
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Dead Load -- Self Weight}}
\hline
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Steel Self-Weight Applied} & """ + (_render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[\rowpad]
\hline
\textnormal{Concrete Deck Weight} & """ + (_render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[\rowpad]
\hline
\textnormal{Self-Weight Factor} & """ + (_render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR)) + r""" \\[\rowpad]
\hline
\end{longtable}

\tablegap
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Dead Load for Surfacing (DW)}}
\hline
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Wearing Course Load} & """ + (_render_value(input_dict, KEY_WC_MATERIAL)) + r""" x """ + (_render_value(input_dict, KEY_WC_THICKNESS)) + r""" \\[\rowpad]
\hline
\textnormal{Additional SIDL (Crash Barrier)} & """ + (_render_value(input_dict, KEY_CB_LOAD)) + r""" kN/m per barrier \\[\rowpad]
\hline
\textnormal{Railing Load} & """ + (_render_value(input_dict, KEY_RL_LOAD_VALUE)) + r""" kN/m\sdstar{} \\[\rowpad]
\hline
\end{longtable}

\tablegap
""" + live_load_tables + r"""

\tablegap
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Wind Load (WL) --- per IRC 6}}
\hline
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Basic Wind Speed, Vb} & """ + (_render_value(input_dict,'wind_speed', ' m/s')) + r""" [from Project Location] \\[\rowpad]
\hline
\textnormal{Terrain Type} & """ + (_render_value(input_dict, KEY_WL_TERRAIN_TYPE)) + r""" \\[\rowpad]
\hline
\textnormal{Average Exposed Height, H (m)} & """ + (_render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, ' m')) + r""" \\[\rowpad]
\hline
\textnormal{Hourly Mean Wind Speed, Vz} & """ + _or_not_computed(vz_str if vz_str != "N/A" else "") + r""" \\[\rowpad]
\hline
\textnormal{Hourly Wind Pressure, Pz} & """ + _or_not_computed(pz_str.replace("N/m²", r"N/m\textsuperscript{2}") if pz_str != "N/A" else "") + r""" \\[\rowpad]
\hline
\textnormal{Transverse Wind Force} & """ + _or_not_computed(_render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, ' kN')) + r""" \\[\rowpad]
\hline
\textnormal{Longitudinal Wind Force} & """ + _or_not_computed(_render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, ' kN')) + r""" \\[\rowpad]
\hline
\textnormal{Vertical Wind Force} & """ + _or_not_computed(_render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, ' kN')) + r""" \\[\rowpad]
\hline
\end{longtable}

\tablegap
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Earthquake Load (EL) --- per IRC 6}}
\hline
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Seismic Zone} & """ + (_render_value(input_dict,'seismic_zone')) + r""" [from Project Location] \\[\rowpad]
\hline
\textnormal{Zone Factor, Z} & """ + (_render_value(input_dict, KEY_SL_ZONE_FACTOR)) + r""" \\[\rowpad]
\hline
\textnormal{Importance Factor, I} & """ + (_render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR)) + r""" \\[\rowpad]
\hline
\textnormal{Type of Soil} & """ + (_render_value(input_dict, KEY_SL_SOIL_TYPE)) + r""" \\[\rowpad]
\hline
\textnormal{Sa/g} & """ + (_render_value(input_dict, KEY_SL_SPECTRAL_COEFF)) + r""" \\[\rowpad]
\hline
\textnormal{Horizontal Seismic Coefficient, Ah} & """ + (_render_value(input_dict, KEY_SL_HORIZONTAL_COEFF)) + r""" \\[\rowpad]
\hline
\textnormal{Vertical Seismic Coefficient, Av} & """ + (_render_value(input_dict, KEY_SL_VERTICAL_COEFF)) + r""" \\[\rowpad]
\hline
\textnormal{Horizontal Seismic Force (longitudinal)} & Not computed \\[\rowpad]
\hline
\textnormal{Horizontal Seismic Force (transverse)} & Not computed \\[\rowpad]
\hline
\end{longtable}

\tablegap
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Temperature Load (TL) --- per IRC 6}}
\hline
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Maximum Shade Temperature} & """ + (_render_value(input_dict,'shade_temp_max')) + r""" $^\circ$C \\[\rowpad]
\hline
\textnormal{Minimum Shade Temperature} & """ + (_render_value(input_dict,'shade_temp_min')) + r""" $^\circ$C \\[\rowpad]
\hline
\textnormal{Effective Bridge Temp. Range} & """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MIN)) + r""" to """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MAX)) + r""" $^\circ$C \\[\rowpad]
\hline
\textnormal{Temperature Rise / Fall for Design} & +""" + (_render_value(input_dict, KEY_TL_TEMP_RISE)) + r""" $^\circ$C / \textminus{}""" + (_render_value(input_dict, KEY_TL_TEMP_FALL)) + r""" $^\circ$C \\[\rowpad]
\hline
\end{longtable}

\tablegap
\begin{longtable}{|C{4.0cm}|p{11.5cm}|}
\caption{\textbf{Load Combinations}}
\hline
\textbf{Combination ID} & \textbf{Load Cases} \\[\rowpad]
\hline
""" + lc_rows_str + r"""
\end{longtable}

\noindent\textit{Note: All IRC 6 load combinations are auto-generated by OsdagBridge. User-defined custom combinations, if any, are appended.}
"""


# ── Live loads (Chapter 3) ───────────────────────────────────────────────────
# Vehicle live loads and the footway live load used to share one table. They
# are now three tables: one row per vehicle selected in Additional Inputs >
# Loading, the forces that come with the carriageway live load, and the
# footway load, each with its unit.

# The Loading tab's vehicle checkboxes, with the tab's labels and in its order
# (ui_fields_additional_input.py, "Vehicles from IRC 6"):
# (input key, label, wheeled/tracked, IRC 6 impact factor clause)
_VEHICLE_KEYS = [
    (KEY_LL_IRC_CLASS_A,       "Class A",           "Wheeled", "208.2"),
    (KEY_LL_IRC_AA_WHEELED,    "Class AA Wheeled",  "Wheeled", "208.3"),
    (KEY_LL_IRC_AA_TRACKED,    "Class AA Tracked",  "Tracked", "208.3"),
    (KEY_LL_IRC_70R_WHEELED,   "Class 70R Wheeled", "Wheeled", "208.3"),
    (KEY_LL_IRC_70R_TRACKED,   "Class 70R Tracked", "Tracked", "208.3"),
    (KEY_LL_IRC_70R_BOGIE,     "Class 70R Bogie",   "Wheeled", "208.3"),
    (KEY_LL_IRC_CLASS_SV,      "Class SV",          "Wheeled", None),
    (KEY_LL_IRC_CLASS_FATIGUE, "Class Fatigue",     "Wheeled", None),
]

# Vehicles of the IRC 6 Table 6A combinations, which the grillage analysis
# places on the carriageway (analyser.vehicle_lane_coordinates), by the
# Loading-tab key of the same vehicle.
_ANALYSIS_VEHICLES = {"ClassA": KEY_LL_IRC_CLASS_A, "Class70R": KEY_LL_IRC_70R_WHEELED}


def _is_selected(input_dict, key):
    """Loading-tab checkbox state, parsed like resolve_live_load_definitions().

    True, or the strings "true" / "yes" / "1" / "checked" (any case), mean
    selected; anything else (False, None, "False", "No", ...) does not.
    """
    raw = input_dict.get(key)
    if raw is None:
        return False
    return raw is True or str(raw).strip().lower() in ("true", "yes", "1", "checked")


def _custom_vehicle_names(input_dict):
    """Names of user-defined vehicles (Additional Inputs > Loading, custom vehicles)."""
    names = []
    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if isinstance(custom, list):
        for item in custom:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())
    return names


def _design_lanes(input_dict):
    """Design lanes: the lane table count if set, else IRC 6 Table 6 from the carriageway width."""
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    lanes = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    try:
        if lanes not in (None, ""):
            return int(lanes)
        return int(IRC6_2017.table_6A(float(input_dict.get(KEY_CARRIAGEWAY_WIDTH)))["design_lanes"])
    except (TypeError, ValueError, KeyError):
        return None


def _analysis_impact_factor(span_m):
    """1 + I that the grillage analysis applies to every vehicle load case.

    Mirrors analyser.add_vehicle_load_cases_from_combinations():
    dla = 1.0 + IRC6_2017.cl_208_3_impact_factor(L), called without the
    vehicle type (the Cl. 208.3 rule for tracked vehicles).
    """
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    return 1.0 + IRC6_2017.cl_208_3_impact_factor(span_m)


def _irc_impact_factor(span_m, clause, kind):
    """1 + I per IRC 6 for the vehicle: Cl. 208.2 (Class A) or Cl. 208.3 by wheeled / tracked."""
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    if clause == "208.2":
        return 1.0 + IRC6_2017.cl_208_2_impact_factor(span_m)
    return 1.0 + IRC6_2017.cl_208_3_impact_factor(span_m, tracked=(kind == "Tracked"))


def _vehicle_table(input_dict, span_m):
    """Rows and note of the vehicle live-load table (see _live_load_tables)."""
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    try:
        combos = IRC6_2017.table_6A(float(input_dict.get(KEY_CARRIAGEWAY_WIDTH)))["vehicle_combinations"]
        in_analysis = {_ANALYSIS_VEHICLES[v] for combo in combos for v in combo if v in _ANALYSIS_VEHICLES}
    except (TypeError, ValueError, KeyError):
        in_analysis = set()
    try:
        applied = _analysis_impact_factor(span_m) if span_m is not None else None
    except Exception:
        applied = None

    rows, differs = [], []
    for key, name, kind, clause in _VEHICLE_KEYS:
        if not _is_selected(input_dict, key):
            continue
        irc = None
        if clause is not None and span_m is not None:
            try:
                irc = _irc_impact_factor(span_m, clause, kind)
            except Exception:
                irc = None
        if key in in_analysis and applied is not None:
            value, basis = f"{applied:.3f}", "Applied in the grillage analysis"
            if irc is not None and abs(irc - applied) > 5e-4:
                differs.append((name, clause, irc))
        elif irc is not None:
            value, basis = f"{irc:.3f}", f"IRC 6 Cl. {clause}"
        else:
            value, basis = "---", "Not computed by OsdagBridge"
        rows.append(f"{_tex(name)} & {kind} & {value} & {basis} \\\\[\\rowpad]\n\\hline")
    for name in _custom_vehicle_names(input_dict):
        rows.append(f"{_tex(name)} (custom) & --- & --- & User-defined vehicle \\\\[\\rowpad]\n\\hline")
    if not rows:
        rows.append(r"\multicolumn{4}{|c|}{No vehicle selected in Additional Inputs $>$ Loading} \\[\rowpad]"
                    "\n\\hline")

    span_txt = f"{span_m:g}" if span_m is not None else "---"
    note = (r"Vehicles as selected in Additional Inputs $>$ Loading; impact factors for a "
            + span_txt + r" m span.")
    if in_analysis and applied is not None:
        loaded = [name for key, name, _k, _c in _VEHICLE_KEYS if key in in_analysis]
        note += (" The grillage analysis loads the carriageway with the IRC 6 Table 6A vehicle "
                 "combinations (" + ", ".join(loaded) + f") and applies $1 + I$ = {applied:.3f} to "
                 r"every vehicle load case (IRC 6 Cl. 208.3, tracked-vehicle value); rows marked "
                 r"``Applied in the grillage analysis'' show that factor.")
    if differs:
        parts = [f"{irc:.3f} for {_tex(name)} (Cl. {clause})" for name, clause, irc in differs]
        note += (" For this span IRC 6 gives " + ", ".join(parts)
                 + "; the analysis does not yet use the vehicle type.")
    return rows, [note]


def _braking_rows(input_dict):
    """Braking rows of the 'Forces Associated with Vehicle Live Load' table."""
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    any_vehicle = (any(_is_selected(input_dict, key) for key, *_ in _VEHICLE_KEYS)
                   or bool(_custom_vehicle_names(input_dict)))
    rows = []
    if not any_vehicle:
        rows.append(r"Braking force (longitudinal) & Not applied & kN & "
                    r"No vehicle selected in Additional Inputs $>$ Loading \\[\rowpad]")
    else:
        lanes = _design_lanes(input_dict)
        braking_kn = braking_t = None
        if lanes:
            try:
                # cl_211_2_braking_force works in the code module's base unit (N).
                from osdagbridge.core.utils.codes.keyfile import kN, t as tonne
                braking_n = IRC6_2017.cl_211_2_braking_force(lanes)
                braking_kn, braking_t = braking_n / kN, braking_n / tonne
            except Exception:
                pass
        train = r"20\% of the Class A train"
        if lanes and lanes > 2:
            train += r" + 5\% of a Class 70R Wheeled train per lane beyond two"
        if braking_kn is not None:
            value = f"{braking_kn:.2f}"
            basis = f"IRC 6 Cl. 211.2: {train}; {lanes} design lane(s) ({braking_t:.2f}~t)"
        else:
            value, basis = "---", f"IRC 6 Cl. 211.2: {train}"
        rows.append(r"Braking force (longitudinal) & " + value + r" & kN & " + basis + r" \\[\rowpad]")
    if KEY_BL_IRC_CLASS_SV in input_dict:
        sv = "Selected" if _is_selected(input_dict, KEY_BL_IRC_CLASS_SV) else "Not selected"
        rows.append(r"Braking from Class SV & " + sv + r" & --- & Option in Additional Inputs $>$ Loading; "
                    r"the Class SV braking force is not computed by OsdagBridge \\[\rowpad]")
    ecc = input_dict.get(KEY_LL_ECCENTRICITY)
    if ecc not in (None, ""):
        try:
            ecc_txt = f"{float(ecc):g}"
        except (TypeError, ValueError):
            ecc_txt = _tex(ecc)
        rows.append(r"Braking force eccentricity above the deck top & " + ecc_txt + r" & m & "
                    r"Additional Inputs $>$ Loading (IRC 6 Cl. 211.3) \\[\rowpad]")
    return rows


def _live_load_tables(input_dict, fp_mode=None, fp_value=None):
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

    if fp_mode is None:
        fp_mode = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "")
    if fp_value is None:
        fp_value = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    try:
        span_m = float(input_dict.get(KEY_SPAN))
    except (TypeError, ValueError):
        span_m = None

    vehicle_rows, vehicle_notes = _vehicle_table(input_dict, span_m)
    force_rows = _braking_rows(input_dict) + [
        r"Centrifugal force & Not applicable & kN & IRC 6 Cl. 212 applies only to horizontally curved "
        r"bridges; OsdagBridge models straight spans \\[\rowpad]"]

    n_footpaths = input_dict.get(KEY_TS_NO_OF_FOOTPATHS) or 0
    try:
        n_footpaths = int(float(n_footpaths))
    except (TypeError, ValueError):
        n_footpaths = 0
    if n_footpaths <= 0:
        footway_rows = (r"Footpaths on the bridge & 0 & --- & Typical section \\[\rowpad]" "\n\\hline\n"
                        r"Footway live load & Not applied & kN/m\textsuperscript{2} & No footpath \\[\rowpad]" "\n\\hline")
    else:
        if str(fp_mode).strip().lower() in ("as per irc 6", "as per irc6", "automatic"):
            try:
                pressure, basis = f"{IRC6_2017.cl_206_1_footway_load():.3f}", "IRC 6 Cl. 206.1"
            except Exception:
                pressure, basis = "---", "IRC 6 Cl. 206.1"
        elif fp_value not in (None, ""):
            pressure, basis = _tex(fp_value), "User-defined"
        else:
            pressure, basis = "---", "---"
        footway_rows = (f"Footpaths on the bridge & {n_footpaths} & --- & Typical section \\\\[\\rowpad]\n\\hline\n"
                        f"Footway live load & {pressure} & kN/m\\textsuperscript{{2}} & {basis} \\\\[\\rowpad]\n\\hline")

    note_lines = "\n".join(r"\noindent\textit{Note: " + n + r"}\par" for n in vehicle_notes)
    return (r"""
\begin{longtable}{|L{4.0cm}|C{2.0cm}|C{2.6cm}|L{6.4cm}|}
\caption{\textbf{Vehicle Live Loads (LL) --- per IRC 6}}
\hline
\textbf{Vehicle Class} & \textbf{Type} & \textbf{Impact Factor, $1 + I$ (--)} & \textbf{Basis} \\
\hline
""" + "\n".join(vehicle_rows) + r"""
\end{longtable}
""" + note_lines + r"""

\tablegap
\begin{longtable}{|L{4.0cm}|C{2.0cm}|C{1.4cm}|L{7.6cm}|}
\caption{\textbf{Forces Associated with Vehicle Live Load}}
\hline
\textbf{Force} & \textbf{Value} & \textbf{Unit} & \textbf{Basis} \\
\hline
""" + "\n\\hline\n".join(force_rows) + r"""
\hline
\end{longtable}
\noindent\textit{Note: The braking force is reported for information; the load combinations of this chapter do not include it.}

\tablegap
\begin{longtable}{|L{4.0cm}|C{2.0cm}|C{1.4cm}|L{7.6cm}|}
\caption{\textbf{Footway Live Load (Pedestrian)}}
\hline
\textbf{Parameter} & \textbf{Value} & \textbf{Unit} & \textbf{Basis} \\
\hline
""" + footway_rows + r"""
\end{longtable}
""")
