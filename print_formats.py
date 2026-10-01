  #!/usr/bin/env python3
"""
print_formats.py - Report formatting, HTML/PDF/image rendering, and print execution.

No Flask routes; used by bridge.py. Uses bridge_services for open_serial_locked and probe_and_choose_port.
"""

import base64
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from html import unescape

import serial

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

import bridge_services

_logger = None
_config = {}


def init(app, config):
    """Store logger and config."""
    global _logger, _config
    _logger = app.logger
    _config = dict(config)


def _reports_dir():
    return _config.get("REPORTS_DIR") or pathlib.Path("/media/usb_internal/reports")


def _a4_port():
    return _config.get("A4_PORT", "/dev/ttyAMA4")


def _a4_baud():
    return _config.get("A4_BAUD", 9600)


def _thermal_port():
    return _config.get("THERMAL_PORT", "/dev/ttyAMA3")


def _thermal_baud():
    return _config.get("THERMAL_BAUD", 9600)


def _min_free_gb():
    return float(_config.get("MIN_FREE_GB", 4.0))


# ----- Report generation -----

def convert_a4_to_thermal_layout(text, width=48):
    """
    Convert A4 text report (70 chars) to thermal layout (48 chars).
    Wraps long lines at word boundaries when possible, adjusts separators, collapses extra blank lines.
    """
    if not text:
        return ""
    lines = text.splitlines()
    out = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                out.append("")
                prev_blank = True
            continue
        prev_blank = False
        # Separator lines (= or -)
        # For this project we remove separators entirely in thermal layout
        # (they tend to wrap/duplicate and look like "extra ===/---" noise).
        stripped = line.strip()
        if stripped and len(stripped) >= 10 and all(c in '=-' for c in stripped):
            continue
        # Regular lines - wrap at width, prefer word boundaries
        while len(line) > width:
            chunk = line[:width]
            last_space = chunk.rfind(' ')
            if last_space > width // 2:
                out.append(line[:last_space].rstrip())
                line = line[last_space:].lstrip()
            else:
                out.append(chunk)
                line = line[width:].lstrip() if line[width:].strip() else line[width:]
        if line:
            out.append(line)
    return "\n".join(out)


def generate_text_report(report_data, txt_path, layout='a4'):
    """
    Generate a plain text report from report data.
    layout: 'a4' for 70-char width, 'thermal' for 48-char width.
    """
    try:
        width = 70 if layout == 'a4' else 48
        txt_path = pathlib.Path(txt_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            # Separators: use blank lines for both A4 and thermal (no ==== or ----)
            line = "\n"
            thin_line = "\n"

            def format_dt(dt_str):
                """Format ISO-ish datetime into 'DD-MM-YYYY HH:MM' (avoid noisy raw strings)."""
                if not dt_str:
                    return 'N/A'
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
                    return dt.strftime('%d-%m-%Y %H:%M:%S')
                except Exception:
                    return str(dt_str)

            def format_duration_hhmmss(seconds_val):
                """Format numeric seconds into HH:MM:SS; otherwise return as string/N/A."""
                try:
                    if seconds_val is None:
                        return 'N/A'
                    # Accept stringified numbers too
                    s = float(seconds_val)
                    if s < 0:
                        return 'N/A'
                    s = int(round(s))
                    h = s // 3600
                    m = (s % 3600) // 60
                    ss = s % 60
                    return f"{h:02d}:{m:02d}:{ss:02d}"
                except Exception:
                    return str(seconds_val) if seconds_val is not None else 'N/A'
            factory_settings = report_data.get('factorySettings') or {}
            company_name = factory_settings.get('companyName') or report_data.get('companyName') or 'N/A'
            model_no = factory_settings.get('modelNo') or report_data.get('modelNo') or 'N/A'
            serial_no = factory_settings.get('serialNo') or report_data.get('serialNo') or 'N/A'
            location = factory_settings.get('companyLocation') or report_data.get('location') or 'N/A'
            instrument_id = factory_settings.get('instrumentId') or report_data.get('instrumentId') or 'N/A'
            last_validation = factory_settings.get('lastValidationDate') or report_data.get('lastValidationDate') or 'N/A'
            next_validation = factory_settings.get('nextValidationDate') or report_data.get('nextValidationDate') or 'N/A'
            rtype = (report_data.get('type') or '').strip().lower()
            subtype_raw = (report_data.get('validationSubtype') or '').strip().lower()
            report_name = (report_data.get('name') or '').strip().lower()
            report_status = (report_data.get('status') or '').strip().upper()
            is_calibration = (
                rtype == 'calibration'
                or subtype_raw == 'calibration'
                or report_name.startswith('calibration')
                or report_status.startswith('CALIBRATED')
            )
            is_validation = rtype == 'validation' and not is_calibration

            if is_calibration:
                operator = report_data.get('operatorName') or report_data.get('operator') or 'N/A'
                operator_id = report_data.get('operatorId') or report_data.get('employeeId') or report_data.get('username') or 'N/A'
                def _fmt_c(val):
                    return f"{float(val):.2f}C" if isinstance(val, (int, float)) else 'N/A'
                f.write(line)
                if layout == 'thermal':
                    f.write("RAISE LAB EQUIPMENT\n")
                    f.write("Tablet Disintegration Tester\n")
                    f.write(thin_line)
                    f.write(f"{company_name}\n")
                    f.write("CALIBRATION REPORT\n")
                else:
                    f.write(f"{'RAISE LAB EQUIPMENT':^{width}}\n")
                    f.write(f"{'Tablet Disintegration Tester':^{width}}\n")
                    f.write(thin_line)
                    f.write(f"{company_name:^{width}}\n")
                    f.write(f"{'CALIBRATION REPORT':^{width}}\n")
                f.write(thin_line)
                if layout == 'thermal':
                    f.write(f"Model No     : {model_no}\n")
                    f.write(f"Serial No    : {serial_no}\n")
                    f.write(f"Location     : {location}\n")
                    f.write(f"Instrument No: {instrument_id}\n")
                else:
                    label_width = 20
                    value_width = (width - label_width - 3) // 2
                    f.write(f"Model No            : {model_no:<{value_width}} Serial No          : {serial_no}\n")
                    f.write(f"Location            : {location:<{value_width}} Instrument No      : {instrument_id}\n")
                f.write(thin_line)
                label_width = 35 if layout != 'thermal' else 20
                f.write(f"{'Bath':<{label_width}}: Shared bath\n")
                f.write(f"{'Sensor Reading':<{label_width}}: {_fmt_c(report_data.get('setTemperature'))}\n")
                f.write(f"{'Measured Temperature':<{label_width}}: {_fmt_c(report_data.get('measuredTemperature'))}\n")
                f.write(f"{'Offset':<{label_width}}: {_fmt_c(report_data.get('calibrationOffset'))}\n")
                f.write(f"{'Deviation':<{label_width}}: {_fmt_c(report_data.get('deviation'))}\n")
                f.write(f"{'Status':<{label_width}}: {report_data.get('status') or 'CALIBRATED & PASSED'}\n")
                f.write(f"{'Date & Time':<{label_width}}: {format_dt(report_data.get('createdAt'))}\n")
                f.write(line)
                f.write(f"Operator            : {operator}\n")
                f.write(f"Employee ID         : {operator_id}\n")
                f.write(f"Remarks:\n\n")
                f.write(thin_line)
                f.write(f"Approved By:\n")
                f.write(line)
            elif is_validation:
                subtype = report_data.get('validationSubtype') or 'temp'
                subtype_text = 'STROKE' if subtype == 'stroke' else 'TEMP'
                basket = report_data.get('basket') or report_data.get('beaker') or 1
                operator = report_data.get('operatorName') or report_data.get('operator') or 'N/A'
                operator_id = report_data.get('operatorId') or report_data.get('employeeId') or report_data.get('username') or 'N/A'
                f.write(line)
                if layout == 'thermal':
                    f.write("RAISE LAB EQUIPMENT\n")
                    f.write("Tablet Disintegration Tester\n")
                    f.write(thin_line)
                    f.write(f"{company_name}\n")
                    f.write(f"VALIDATION REPORT - {subtype_text}\n")
                else:
                    f.write(f"{'RAISE LAB EQUIPMENT':^{width}}\n")
                    f.write(f"{'Tablet Disintegration Tester':^{width}}\n")
                    f.write(thin_line)
                    f.write(f"{company_name:^{width}}\n")
                    f.write(f"{'VALIDATION REPORT - ' + subtype_text:^{width}}\n")
                f.write(thin_line)
                if layout == 'thermal':
                    f.write(f"Model No     : {model_no}\n")
                    f.write(f"Serial No    : {serial_no}\n")
                    f.write(f"Location     : {location}\n")
                    f.write(f"Instrument No: {instrument_id}\n")
                    f.write(f"Last Valid   : {last_validation}\n")
                    f.write(f"Next Valid   : {next_validation}\n")
                else:
                    label_width = 20
                    value_width = (width - label_width - 3) // 2
                    f.write(f"Model No            : {model_no:<{value_width}} Serial No          : {serial_no}\n")
                    f.write(f"Location            : {location:<{value_width}} Instrument No      : {instrument_id}\n")
                    f.write(f"Last Validation Date: {last_validation:<{value_width}} Next Validation Due: {next_validation}\n")
                f.write(thin_line)
                label_width = 35 if layout != 'thermal' else 20
                if subtype == 'stroke':
                    f.write(f"{'Basket/Beaker':<{label_width}}: Basket {basket}\n")
                    f.write(f"{'Validation Type':<{label_width}}: Stroke\n")
                    strokes_per_min = report_data.get('strokesPerMin')
                    f.write(f"{'Strokes/Min':<{label_width}}: {strokes_per_min if strokes_per_min is not None else 'N/A'} strokes/min\n")
                    f.write(f"{'Required Range':<{label_width}}: 29-31 strokes/min\n")
                    f.write(f"{'Status':<{label_width}}: {report_data.get('status') or 'PASSED'}\n")
                    f.write(f"{'Date & Time':<{label_width}}: {format_dt(report_data.get('createdAt'))}\n")
                else:
                    f.write(f"{'Basket/Beaker':<{label_width}}: Basket {basket}\n")
                    f.write(f"{'Validation Type':<{label_width}}: Temperature\n")
                    min_temp = report_data.get('minTemp')
                    max_temp = report_data.get('maxTemp')
                    max_deviation = report_data.get('maxDeviation') or report_data.get('deviation')
                    f.write(f"{'Min Temp':<{label_width}}: {f'{min_temp:.2f}' if min_temp is not None else 'N/A'}C\n")
                    f.write(f"{'Max Temp':<{label_width}}: {f'{max_temp:.2f}' if max_temp is not None else 'N/A'}C\n")
                    f.write(f"{'Max Deviation':<{label_width}}: {f'{max_deviation:.2f}' if max_deviation is not None else 'N/A'}C\n")
                    f.write(f"{'Status':<{label_width}}: {report_data.get('status') or 'PASSED'}\n")
                    f.write(f"{'Date & Time':<{label_width}}: {format_dt(report_data.get('createdAt'))}\n")
                f.write(line)
                f.write(f"Operator            : {operator}\n")
                f.write(f"Employee ID         : {operator_id}\n")
                f.write(f"Remarks:\n\n")
                f.write(thin_line)
                f.write(f"Approved By:\n")
                f.write(line)
            else:
                tested_basket = report_data.get('basket') or 1
                product1 = report_data.get('productName1') or report_data.get('product') or 'N/A'
                batch1 = report_data.get('batch1') or report_data.get('batch') or 'N/A'
                product2 = report_data.get('productName2') or 'N/A'
                batch2 = report_data.get('batch2') or 'N/A'
                operator = report_data.get('operatorName') or report_data.get('operator') or 'N/A'
                operator_id = report_data.get('operatorId') or report_data.get('employeeId') or report_data.get('username') or 'N/A'
                mode = report_data.get('mode') or 'N/A'
                set_temp = report_data.get('setTemperature')
                set_temp_str = f"{set_temp:.1f}" if set_temp is not None else 'N/A'
                # Extra metrics available from test reports
                min_temp = report_data.get('minTemp')
                max_temp = report_data.get('maxTemp')
                duration_sec = report_data.get('durationSeconds')
                if duration_sec is None and report_data.get('testStartTime') and report_data.get('testEndTime'):
                    from datetime import datetime
                    try:
                        start = datetime.fromisoformat(report_data['testStartTime'].replace('Z', '+00:00'))
                        end = datetime.fromisoformat(report_data['testEndTime'].replace('Z', '+00:00'))
                        duration_sec = int((end - start).total_seconds())
                    except Exception:
                        duration_sec = report_data.get('duration') or 0
                elif duration_sec is None:
                    duration_sec = report_data.get('duration') or 0
                h, m, s = int(duration_sec // 3600), int((duration_sec % 3600) // 60), int(duration_sec % 60)
                duration_str = f"{h:02d}:{m:02d}:{s:02d}"
                is_dual = bool(
                    report_data.get("isDualSession")
                    and report_data.get("dualBasket1")
                    and report_data.get("dualBasket2")
                )
                f.write(line)
                if layout == 'thermal':
                    f.write("RAISE LAB EQUIPMENT\n")
                    f.write("Tablet Disintegration Tester\n")
                    f.write(thin_line)
                    f.write(f"{company_name}\n")
                    f.write("TEST REPORT\n")
                else:
                    f.write(f"{'RAISE LAB EQUIPMENT':^{width}}\n")
                    f.write(f"{'Tablet Disintegration Tester':^{width}}\n")
                    f.write(thin_line)
                    f.write(f"{company_name:^{width}}\n")
                    f.write(f"{'TEST REPORT':^{width}}\n")
                f.write(thin_line)
                if layout == 'thermal':
                    f.write(f"Model No     : {model_no}\n")
                    f.write(f"Serial No    : {serial_no}\n")
                    f.write(f"Location     : {location}\n")
                    f.write(f"Instrument No: {instrument_id}\n")
                    f.write(f"Last Valid   : {last_validation}\n")
                    f.write(f"Next Valid   : {next_validation}\n")
                else:
                    label_width = 20
                    value_width = (width - label_width - 3) // 2
                    f.write(f"Model No            : {model_no:<{value_width}} Serial No          : {serial_no}\n")
                    f.write(f"Location            : {location:<{value_width}} Instrument No      : {instrument_id}\n")
                    f.write(f"Last Validation Date: {last_validation:<{value_width}} Next Validation Due: {next_validation}\n")
                f.write(thin_line)
                label_width = 35 if layout != 'thermal' else 20
                if is_dual:
                    f.write(f"RECIPE INFORMATION\n")
                    f.write(thin_line)
                    f.write(f"{'Recipe Name':<{label_width}}: {product1}\n")
                    f.write(f"{'Batch Number':<{label_width}}: {batch1}\n")
                    f.write(thin_line)
                    f.write("TEST DETAILS\n")
                    f.write(thin_line)
                    f.write(f"{'Mode':<{label_width}}: {mode}\n")
                    f.write(f"{'Set Temperature':<{label_width}}: {set_temp_str}C\n")
                    if mode == 'timer' and report_data.get('setDuration'):
                        set_dur = report_data['setDuration']
                        d1, d2, d3 = int(set_dur // 3600), int((set_dur % 3600) // 60), int(set_dur % 60)
                        f.write(f"{'Set Duration':<{label_width}}: {d1:02d}:{d2:02d}:{d3:02d}\n")
                    f.write(f"{'Test Duration':<{label_width}}: {duration_str}\n")
                    f.write(f"{'Test Status':<{label_width}}: {report_data.get('status') or 'Completed'}\n")
                    shared_start = format_dt(report_data.get('testStartTime') or report_data.get('startTime') or report_data.get('createdAt'))
                    shared_end = format_dt(report_data.get('testEndTime') or report_data.get('endTime') or report_data.get('completedAt'))
                    f.write(f"{'Start Time':<{label_width}}: {shared_start}\n")
                    f.write(f"{'End Time':<{label_width}}: {shared_end}\n")
                    if report_data.get("remarks"):
                        f.write(f"{'Remarks':<{label_width}}: {report_data['remarks']}\n")
                    f.write(thin_line)

                def _write_dual_basket_subsection(sub, basket_label):
                    smode = sub.get("mode") or "N/A"
                    sbasket_cfg = int(sub.get("basketConfig") or 0)
                    stested = sub.get("basket")
                    if stested is None:
                        stested = 1 if "1" in basket_label else 2

                    f.write(f"{basket_label}\n")
                    f.write(thin_line)
                    f.write(f"{'Basket Config':<{label_width}}: {sbasket_cfg}\n")

                    vessel_times = sub.get("vesselTimes") or {}
                    if smode == "manual":
                        if (not vessel_times) and sbasket_cfg > 0:
                            hole_times = sub.get("holeCompletionTimes") or {}
                            built = {}
                            for vessel_num in range(1, int(sbasket_cfg) + 1):
                                key_str = str(vessel_num)
                                raw = hole_times.get(key_str)
                                if raw is None:
                                    raw = hole_times.get(vessel_num)
                                built[key_str] = format_duration_hhmmss(raw)
                            vessel_times = built

                    if smode == "manual" and vessel_times and sbasket_cfg > 0:
                        f.write(thin_line)
                        f.write(f"TUBE COMPLETION TIMES — {basket_label}\n")
                        f.write(thin_line)
                        f.write(f"Basket {stested} - {sbasket_cfg} Tube{'s' if sbasket_cfg > 1 else ''}\n\n")
                        for vessel_num in range(1, sbasket_cfg + 1):
                            vessel_time = vessel_times.get(str(vessel_num)) or vessel_times.get(vessel_num) or "N/A"
                            if layout == "thermal":
                                f.write(f"Tube {vessel_num} : {vessel_time}\n")
                            else:
                                f.write(f"  Tube {vessel_num:2d}                      : {vessel_time}\n")

                if is_dual:
                    sub1 = report_data.get("dualBasket1") or {}
                    sub2 = report_data.get("dualBasket2") or {}
                    _write_dual_basket_subsection(sub1, "BASKET 1")
                    _write_dual_basket_subsection(sub2, "BASKET 2")
                else:
                    f.write(f"TEST DETAILS\n")
                    f.write(thin_line)
                    if tested_basket == 2 or str(tested_basket) == "2":
                        disp_product = product2 if (product2 and str(product2).strip() and product2 != "N/A") else product1
                        disp_batch = batch2 if (batch2 and str(batch2).strip() and batch2 != "N/A") else batch1
                    else:
                        disp_product = product1
                        disp_batch = batch1
                    f.write(f"{'Recipe Name':<{label_width}}: {disp_product}\n")
                    f.write(f"{'Batch Number':<{label_width}}: {disp_batch}\n")
                    f.write(f"{'Mode':<{label_width}}: {mode}\n")
                    f.write(f"{'Set Temperature':<{label_width}}: {set_temp_str}C\n")
                    # Include min/max temperatures when available
                    if min_temp is not None:
                        try:
                            f.write(f"{'Min Temperature':<{label_width}}: {float(min_temp):.1f}C\n")
                        except Exception:
                            f.write(f"{'Min Temperature':<{label_width}}: {min_temp}\n")
                    if max_temp is not None:
                        try:
                            f.write(f"{'Max Temperature':<{label_width}}: {float(max_temp):.1f}C\n")
                        except Exception:
                            f.write(f"{'Max Temperature':<{label_width}}: {max_temp}\n")
                    if mode == 'timer' and report_data.get('setDuration'):
                        set_dur = report_data['setDuration']
                        sh, sm, ss = int(set_dur // 3600), int((set_dur % 3600) // 60), int(set_dur % 60)
                        f.write(f"{'Set Duration':<{label_width}}: {sh:02d}:{sm:02d}:{ss:02d}\n")
                    f.write(f"{'Test Duration':<{label_width}}: {duration_str}\n")
                    f.write(f"{'Test Status':<{label_width}}: {report_data.get('status') or 'Completed'}\n")

                    start_time_str = format_dt(report_data.get('testStartTime') or report_data.get('startTime') or report_data.get('createdAt'))
                    end_time_str = format_dt(report_data.get('testEndTime') or report_data.get('endTime') or report_data.get('completedAt'))
                    f.write(f"{'Start Time':<{label_width}}: {start_time_str}\n")
                    f.write(f"{'End Time':<{label_width}}: {end_time_str}\n")
                    if report_data.get('remarks'):
                        f.write(f"{'Remarks':<{label_width}}: {report_data['remarks']}\n")
                    vessel_times = report_data.get('vesselTimes') or {}
                    basket_config = report_data.get('basketConfig') or 0
                    # Always show basket configuration
                    f.write(f"{'Basket Config':<{label_width}}: {basket_config}\n")
                    # Vessel completion times: manual mode only (timer mode has no per-vessel times)
                    if mode == 'manual':
                        if (not vessel_times) and basket_config > 0:
                            hole_times = report_data.get('holeCompletionTimes') or {}
                            built = {}
                            for vessel_num in range(1, int(basket_config) + 1):
                                key_str = str(vessel_num)
                                raw = hole_times.get(key_str)
                                if raw is None:
                                    raw = hole_times.get(vessel_num)
                                built[key_str] = format_duration_hhmmss(raw)
                            vessel_times = built

                    if mode == 'manual' and vessel_times and basket_config > 0:
                        f.write(thin_line)
                        f.write(f"TUBE COMPLETION TIMES\n")
                        f.write(thin_line)
                        f.write(f"Basket {tested_basket} - {basket_config} Tube{'s' if basket_config > 1 else ''}\n\n")
                        for vessel_num in range(1, basket_config + 1):
                            vessel_time = vessel_times.get(str(vessel_num)) or vessel_times.get(vessel_num) or 'N/A'
                            # Compact format for thermal so time stays on same line as tube name
                            if layout == 'thermal':
                                f.write(f"Tube {vessel_num} : {vessel_time}\n")
                            else:
                                f.write(f"  Tube {vessel_num:2d}                      : {vessel_time}\n")
                f.write(thin_line)
                f.write(f"Operated By            : {operator}\n")
                f.write(f"Employee ID           : {operator_id}\n\n")
                f.write(f"Remarks:\n\n")
                f.write(thin_line)
                f.write(f"Approved By:\n")
                f.write(line)
        _logger.info("[TEXT REPORT] Generated text report (%s layout): %s", layout, txt_path)
    except Exception as e:
        _logger.exception("[TEXT REPORT] Error generating text report: %s", e)
        raise


def get_free_gb(path: pathlib.Path) -> float:
    """Return free space for the filesystem of path in GB."""
    st = os.statvfs(str(path))
    return (st.f_bavail * st.f_frsize) / (1024 ** 3)


def enforce_fifo_reports():
    """Delete oldest PDFs from REPORTS_DIR until free space >= MIN_FREE_GB."""
    rep_dir = _reports_dir()
    if not rep_dir.exists():
        return
    free_gb = get_free_gb(rep_dir)
    if free_gb >= _min_free_gb():
        return
    files = [f for f in rep_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]
    files.sort(key=lambda f: f.stat().st_mtime)
    for f in files:
        try:
            _logger.warning("FIFO delete: %s", f)
            f.unlink()
        except Exception as e:
            _logger.error("Failed to delete %s: %s", f, e)
        free_gb = get_free_gb(rep_dir)
        if free_gb >= _min_free_gb():
            break


def _save_bytes_to_file(b64_or_bytes, dest_path):
    """Accept base64 str or raw bytes and save to file."""
    if isinstance(b64_or_bytes, str):
        b = base64.b64decode(b64_or_bytes)
    else:
        b = b64_or_bytes
    pathlib.Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(b)
    return dest_path


def html_to_pdf_with_wkhtmltopdf(html_text, out_pdf_path):
    """Fallback using wkhtmltopdf; raises on failure."""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        tmp.write(html_text.encode("utf-8"))
        tmp.flush()
        tmpname = tmp.name
    try:
        subprocess.check_call(["wkhtmltopdf", "--enable-local-file-access", tmpname, str(out_pdf_path)])
    finally:
        try:
            os.unlink(tmpname)
        except Exception:
            pass
    return out_pdf_path


def pdf_to_image_paths(pdf_path, dpi=150):
    """Convert PDF to image(s). Returns list of image file paths."""
    rep_dir = _reports_dir()
    out_images = []
    if convert_from_path:
        try:
            images = convert_from_path(str(pdf_path), dpi=dpi)
            for i, img in enumerate(images):
                p = rep_dir / f"{pathlib.Path(pdf_path).stem}_page{i+1}_{uuid.uuid4().hex}.png"
                img.save(p, format="PNG")
                out_images.append(str(p))
            return out_images
        except Exception as e:
            _logger.warning("[PDF_TO_IMAGE] pdf2image failed: %s, trying fallback", e)
    try:
        tmp_dir = tempfile.mkdtemp(prefix="pdf2img_")
        tmp_prefix = os.path.join(tmp_dir, "page")
        subprocess.check_call(["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), tmp_prefix])
        for f in sorted(pathlib.Path(tmp_dir).glob("page*.png")):
            dest = rep_dir / f.name
            shutil.move(str(f), str(dest))
            out_images.append(str(dest))
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass
        return out_images
    except Exception as e:
        _logger.error("[PDF_TO_IMAGE] pdftoppm fallback failed: %s", e)
        raise RuntimeError(f"PDF to image conversion failed: {e}") from e


def ensure_reports_dir():
    """Ensure REPORTS_DIR exists."""
    _reports_dir().mkdir(parents=True, exist_ok=True)


def render_html_to_pdf_or_image(html=None, pdf_b64=None, out_format="png", dpi=150):
    """Accept html or pdf_b64; return list of image paths (PNG in REPORTS_DIR)."""
    ensure_reports_dir()
    rep_dir = _reports_dir()
    working_pdf = None
    try:
        if html:
            working_pdf = rep_dir / f"report_{int(time.time())}_{uuid.uuid4().hex}.pdf"
            try:
                from weasyprint import HTML
                HTML(string=html).write_pdf(str(working_pdf))
            except ImportError:
                _logger.info("[RENDER] WeasyPrint not available, using wkhtmltopdf")
                html_to_pdf_with_wkhtmltopdf(html, working_pdf)
            except Exception as e:
                _logger.warning("[RENDER] WeasyPrint failed: %s, trying wkhtmltopdf", e)
                html_to_pdf_with_wkhtmltopdf(html, working_pdf)
        elif pdf_b64:
            working_pdf = rep_dir / f"report_{int(time.time())}_{uuid.uuid4().hex}.pdf"
            _save_bytes_to_file(pdf_b64, working_pdf)
        else:
            raise ValueError("No html or pdf_b64 provided")
        images = pdf_to_image_paths(working_pdf, dpi=dpi)
        return images
    except Exception as e:
        _logger.exception("[RENDER] Failed to render HTML/PDF to image: %s", e)
        raise


def render_html_to_dotmatrix_text(html: str, width: int = 70) -> str:
    """Convert HTML to plain text for dot-matrix; wrap to width."""
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    html = re.sub(r'</?(p|div|tr|li|h1|h2|h3|h4|h5|h6)[^>]*>', '\n', html, flags=re.I)
    html = re.sub(r'</th>\s*<th[^>]*>', '\t', html, flags=re.I)
    html = re.sub(r'</td>\s*<td[^>]*>', '\t', html, flags=re.I)
    html = re.sub(r'</th>', '\t', html, flags=re.I)
    html = re.sub(r'<th[^>]*>', '', html, flags=re.I)
    html = re.sub(r'</td>', '\t', html, flags=re.I)
    html = re.sub(r'<td[^>]*>', '', html, flags=re.I)
    text = re.sub(r'<[^>]+>', '', html)
    text = unescape(text)
    lines = []
    for para in text.splitlines():
        para = re.sub(r'[ \t]+', ' ', para).strip()
        if not para:
            lines.append('')
            continue
        while len(para) > width:
            idx = para.rfind(' ', 0, width)
            if idx <= 0:
                idx = width
            lines.append(para[:idx].rstrip())
            para = para[idx:].lstrip()
        if para:
            lines.append(para)
    return '\r\n'.join(lines) + '\r\n'


def html_to_plain_text(html):
    """Simple HTML to text."""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser").get_text("\n")
    except Exception:
        text = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.S | re.I)
        text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+\n', '\n', text)
        return text.strip()


# ----- Print helpers: ESC/POS and send -----

def pil_to_escpos_raster_bytes(img, width_pixels: int):
    """Convert PIL image to ESC/POS raster format bytes."""
    if Image is None:
        raise RuntimeError("PIL required for raster printing")
    img = img.convert("L")
    w, h = img.size
    if w != width_pixels:
        new_h = int(h * (width_pixels / w))
        img = img.resize((width_pixels, new_h), Image.LANCZOS)
        w, h = img.size
    bw = img.point(lambda p: 0 if p > 127 else 1, '1')
    m, xL = 0, (w // 8) & 0xFF
    xH = ((w // 8) >> 8) & 0xFF
    yL, yH = h & 0xFF, (h >> 8) & 0xFF
    header = bytes([0x1d, 0x76, 0x30, m, xL, xH, yL, yH])
    row_bytes = w // 8
    raw = bw.tobytes()
    out = bytearray(header)
    for row in range(h):
        start = row * row_bytes
        out.extend(raw[start:start + row_bytes])
    return bytes(out)


def send_escpos_raster(port, baud, img, width_pixels=384, chunk_size=1024, pause=0.05):
    """Open serial and send ESC/POS raster bytes in chunks."""
    raster = pil_to_escpos_raster_bytes(img, width_pixels)
    if int(baud) <= 9600:
        chunk_size = 512
        pause = 0.08
    with bridge_services.open_serial_locked(port, baud, timeout=2) as ser:
        ser.write(b'\x1b\x40')
        ser.flush()
        time.sleep(0.05)
        for i in range(0, len(raster), chunk_size):
            ser.write(raster[i:i+chunk_size])
            ser.flush()
            if i + chunk_size < len(raster):
                time.sleep(pause)
        ser.write(b'\n' * 4)
        ser.write(b'\x1d\x56\x00')
        ser.flush()
        time.sleep(0.1)


def send_text_to_thermal(port, baud, text, encoding_candidates=('utf-8', 'cp437'), line_delay=0.02, chunk_chars=40):
    """Send plain text to thermal with encoding fallback; uses open_serial_locked (not ESP lock)."""
    with bridge_services.open_serial_locked(port, baud, timeout=2) as s:
        s.write(b'\x1b\x40')
        s.flush()
        time.sleep(0.05)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        for line in text.split('\n'):
            if not line:
                s.write(b'\n')
                s.flush()
                time.sleep(0.01)
                continue
            for i in range(0, len(line), chunk_chars):
                chunk = line[i:i+chunk_chars]
                sent = False
                for enc in encoding_candidates:
                    try:
                        b = chunk.encode(enc, errors='replace')
                        s.write(b)
                        s.flush()
                        sent = True
                        break
                    except Exception:
                        continue
                if not sent:
                    s.write(chunk.encode('utf-8', errors='replace'))
                    s.flush()
                s.write(b'\n')
                s.flush()
                time.sleep(line_delay)
        s.write(b'\n' * 3)
        s.flush()


def send_text_to_thermal_port(port, baud, text):
    """Send plain text to thermal in safe chunks; uses open_serial_locked."""
    encoding_candidates = ('utf-8', 'cp437', 'latin-1')
    with bridge_services.open_serial_locked(port, baud, timeout=2) as s:
        s.write(b'\x1b\x40')
        s.flush()
        time.sleep(0.05)
        for line in text.splitlines():
            if not line:
                s.write(b'\n')
                s.flush()
                time.sleep(0.01)
                continue
            for i in range(0, len(line), 40):
                seg = line[i:i+40]
                sent = False
                for enc in encoding_candidates:
                    try:
                        s.write(seg.encode(enc, errors='replace'))
                        s.flush()
                        sent = True
                        break
                    except Exception:
                        continue
                if not sent:
                    s.write(seg.encode('utf-8', errors='replace'))
                    s.flush()
                s.write(b'\n')
                s.flush()
                time.sleep(0.02)
        s.write(b'\n' * 4)
        s.flush()


def send_raster_to_thermal(pil_img, port, baud):
    """Legacy wrapper for send_escpos_raster."""
    w = int(os.getenv("THERMAL_WIDTH", "384"))
    send_escpos_raster(port, baud, pil_img, width_pixels=w)
    return True


def print_a4_fallback_text_send(text: str, port=None, baud=None):
    """Send plain text to A4 UART with chunking and ESC/POS init."""
    if port is None:
        port = _a4_port()
    if baud is None:
        baud = _a4_baud()
    if not text.endswith('\n'):
        text += '\n'
    data = text + '\r\n\x0c'
    chunk_size, delay = 512, 0.06
    init_seq = b'\x1b\x40'
    with bridge_services.open_serial_locked(port, baud, timeout=1) as ser:
        ser.write(init_seq)
        ser.flush()
        time.sleep(0.05)
        b = data.encode('utf-8', errors='replace')
        for i in range(0, len(b), chunk_size):
            ser.write(b[i:i+chunk_size])
            ser.flush()
            if i + chunk_size < len(b):
                time.sleep(delay)
        ser.write(b'\n\n')
        ser.flush()
        time.sleep(0.05)
    return True

 
def print_thermal_chunked(text: str, port=None, baud=None, paper_width=384):
    """Send text to thermal with chunked writes and safe encoding."""
    if port is None:
        port = _thermal_port()
    if baud is None:
        baud = _thermal_baud()
    if not text.endswith("\n"):
        text += "\n\n\n"
    encoding_candidates = ['utf-8', 'cp437', 'latin-1']
    chunk_size = 128
    base_delay = 0.08 if int(baud) <= 9600 else 0.04
    init_seq = b'\x1b\x40'
    feed_and_cut = b'\n' * 6 + b'\x1dV\x01'
    encoded_ok = None
    used_encoding = None
    for enc in encoding_candidates:
        try:
            encoded_ok = text.encode(enc)
            used_encoding = enc
            break
        except Exception:
            continue
    if encoded_ok is None:
        encoded_ok = text.encode('utf-8', errors='replace')
        used_encoding = 'utf-8-replace'
    with bridge_services.open_serial_locked(port, baud, timeout=2) as ser:
        _logger.info("[THERMAL] Sending using encoding %s chunk_size=%d to %s", used_encoding, chunk_size, port)
        ser.write(init_seq)
        ser.flush()
        time.sleep(0.06)
        for i in range(0, len(encoded_ok), chunk_size):
            ser.write(encoded_ok[i:i+chunk_size])
            ser.flush()
            if i + chunk_size < len(encoded_ok):
                time.sleep(base_delay)
        try:
            ser.write(feed_and_cut)
            ser.flush()
        except Exception as e:
            _logger.exception("[THERMAL] final feed write failed: %s", e)
    return True


def print_a4_via_uart(pdf_path: pathlib.Path):
    """Deprecated: stream PDF bytes to UART. Use print_a4_pdf_raster or print_a4_fallback_text_send."""
    ser = bridge_services.open_serial(_a4_port(), _a4_baud())
    if not ser:
        raise Exception(f"RS232 port {_a4_port()} not available")
    try:
        with open(pdf_path, "rb") as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                ser.write(chunk)
    finally:
        ser.close()


def print_thermal_text(text: str, paper_width: int = 384):
    """Deprecated: use print_thermal_chunked."""
    ser = bridge_services.open_serial(_thermal_port(), _thermal_baud())
    if not ser:
        raise Exception(f"Thermal port {_thermal_port()} not available")
    try:
        ser.write(b"\x1b@")
        ser.write(b"\n")
        ser.flush()
        chunk_size, delay = 512, 0.04
        b = text.encode('utf-8', errors='replace')
        for i in range(0, len(b), chunk_size):
            ser.write(b[i:i+chunk_size])
            ser.flush()
            if i + chunk_size < len(b):
                time.sleep(delay)
        ser.write(b"\n" * 3)
        ser.write(b"\x1dV\x01")
        ser.flush()
    finally:
        ser.close()


def print_a4_pdf_raster(pdf_path: pathlib.Path, port=None, baud=None):
    """Print A4 PDF via raster mode (PDF -> image -> ESC/POS)."""
    if port is None:
        port = _a4_port()
    if baud is None:
        baud = _a4_baud()
    pdf_abs = pathlib.Path(pdf_path).absolute()
    if not pdf_abs.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_abs}")
    if not os.access(str(pdf_abs), os.R_OK):
        raise FileNotFoundError(f"PDF not readable: {pdf_abs}")
    _logger.info("[A4 PRINT] mode = raster, PDF: %s", pdf_abs)
    dpi = 200
    try:
        images = pdf_to_image_paths(pdf_abs, dpi=dpi)
        if not images:
            raise RuntimeError("PDF conversion produced no images")
    except Exception as e:
        _logger.error("[A4 PRINT] PDF to image failed: %s", e)
        raise RuntimeError(f"PDF to image conversion failed: {e}") from e
    try:
        port_to_use = bridge_services.probe_and_choose_port(port, candidates=[port, _a4_port(), '/dev/ttyAMA4', '/dev/ttyUSB0'])
    except FileNotFoundError:
        raise FileNotFoundError(f"A4 printer port not found: {port}") from None
    if Image is None:
        raise RuntimeError("PIL/Pillow required for raster printing")
    target_width_px = int(8.27 * dpi)
    try:
        with bridge_services.open_serial_locked(port_to_use, baud, timeout=2) as ser:
            ser.write(b'\x1b\x40')
            ser.flush()
            time.sleep(0.05)
            for page_idx, img_path in enumerate(images):
                _logger.info("[A4 PRINT] Sending page %d/%d: %s", page_idx + 1, len(images), img_path)
                img = Image.open(img_path)
                if img.width != target_width_px:
                    new_h = int(img.height * (target_width_px / img.width))
                    img = img.resize((target_width_px, new_h), Image.LANCZOS)
                raster_bytes = pil_to_escpos_raster_bytes(img, target_width_px)
                chunk_size, pause = (512, 0.08) if int(baud) <= 9600 else (1024, 0.05)
                for i in range(0, len(raster_bytes), chunk_size):
                    ser.write(raster_bytes[i:i+chunk_size])
                    ser.flush()
                    if i + chunk_size < len(raster_bytes):
                        time.sleep(pause)
                if page_idx < len(images) - 1:
                    ser.write(b'\x0c')
                    ser.flush()
                    time.sleep(0.1)
            ser.write(b'\n' * 4)
            ser.write(b'\x0c')
            ser.flush()
            time.sleep(0.1)
        _logger.info("[A4 PRINT] Raster print completed successfully")
        return True
    except Exception as e:
        _logger.exception("[A4 PRINT] Raster send failed: %s", e)
        raise


def print_a4_pdf_text_fallback(pdf_path: pathlib.Path, port=None, baud=None, width_chars=70):
    """Print A4 PDF using text extraction fallback."""
    if port is None:
        port = _a4_port()
    if baud is None:
        baud = _a4_baud()
    pdf_abs = pathlib.Path(pdf_path).absolute()
    if not pdf_abs.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_abs}")
    _logger.warning("[A4 PRINT] Text fallback – layout may differ")
    _logger.info("[A4 PRINT] mode = text-fallback, PDF: %s", pdf_abs)
    text = ""
    try:
        outtxt = str(pdf_abs) + '.txt'
        subprocess.check_call(['pdftotext', str(pdf_abs), outtxt], timeout=10)
        with open(outtxt, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        try:
            os.unlink(outtxt)
        except Exception:
            pass
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        _logger.error("[A4 PRINT] Text extraction failed: %s", e)
        raise RuntimeError(f"Text extraction from PDF failed: {e}") from e
    if not text.strip():
        raise RuntimeError("No text extracted from PDF")
    try:
        port_to_use = bridge_services.probe_and_choose_port(port, candidates=[port, _a4_port(), '/dev/ttyAMA4', '/dev/ttyUSB0'])
    except FileNotFoundError:
        raise FileNotFoundError(f"A4 printer port not found: {port}") from None
    print_a4_fallback_text_send(text, port=port_to_use, baud=baud)
    return True
 