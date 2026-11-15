# Flight Report Plugin

Offline post-flight analysis for SCAF-DCS. Reads **unmodified** `telemetry.jsonl` produced by the central SCAF receiver and writes a PDF, figures, CSV and JSON summary.

## Setup

From the repository root (Windows PowerShell):

```powershell
python -m pip install -r plugins/flight_report/requirements.txt
```

## Generate a report

```powershell
python -m plugins.flight_report.python.src.generate_report "data/sessions/SESSION_ID"
```

Optional output directory:

```powershell
python -m plugins.flight_report.python.src.generate_report "data/sessions/SESSION_ID" --output-dir "data/reports/demo"
```

Expected inputs in session directory:

- `telemetry.jsonl`: one JSON object per line, with `packet` and optionally `received_at_utc`; protocol `scaf.telemetry`, version `1`, type `aircraft.state`.
- `metadata.json`: optional session metadata, including `completed`.

Outputs (under `SESSION/report/` by default):

- `flight_report.pdf`: summary and plots
- `summary.json`: machine-readable summary and data-quality checks
- `telemetry.csv`: flattened flight telemetry
- `speed.png`, `altitude.png`, `fuel.png`, `g_force.png`, `track.png` (when data is available)

## Notes and limitations

- Works without DCS running; no network access required.
- Data is evaluated against **simulation timestamps**; system receipt timestamps are preserved in CSV.
- Speed is DCS *indicated* airspeed in m/s converted to km/h for display.
- "Normal G" uses the exported acceleration **Y** component; cross-check with cockpit instrumentation before treating it as verified.
- Track is a latitude/longitude ground trace, not a cartographic basemap or a full 3-D flight path.
- The computed ground distance is an estimate based on valid, plausible adjacent coordinates, not a certified flown distance.
- No flight safety score, stall threshold, or aircraft-dependent limits are invented.
- Incomplete sessions are explicitly marked as incomplete. Malformed JSONL lines are skipped and counted.
- The `data/` folder should remain excluded from Git unless a sanitized sample is intentionally committed.
