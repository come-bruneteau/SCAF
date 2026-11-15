# SCAF VR HUD

A head-locked **desktop HUD prototype** for replaying the SCAF flight telemetry already recorded by DCS. The application is intended for **OpenKneeboard Window Capture** tests in DCS / Quest 3. It is **not** a native OpenXR layer and **does not** yet render world-locked markers.

## Installation (Windows, from repository root)

```powershell
python -m pip install -r plugins/vr_hud/requirements.txt
```

## Run

Without Qt, verify the replay JSONL first:

```powershell
python -m plugins.vr_hud.python.src.main "data/sessions/YOUR_SESSION_ID" --check
```

Launch the standard, taskbar-visible **Window Capture** mode:

```powershell
python -m plugins.vr_hud.python.src.main "data/sessions/YOUR_SESSION_ID"
```

Other options: `--speed 1.5`, `--no-loop`, `--overlay` (transparent frameless desktop test; can be incompatible with Window Capture).

## Telemetry

- indicated airspeed (`speed_mps`) converted to km/h
- altitude above sea level (`altitude_m`) in meters
- fuel internal + external (`fuel_internal_kg`, `fuel_external_kg`) in kg, **not a fuel percentage**
- normal acceleration `acceleration_g.y` in G (verify against in-game instrument)

Missing fields are displayed as `--`; no value is fabricated. No network access or changes to `Export.lua` are needed.

## Testing without VR

```powershell
python -m unittest discover -s tests -p "test_vr_hud_replay.py" -v
```

## Quest 3 / OpenKneeboard test checklist

1. Install OpenKneeboard from https://openkneeboard.com/.
2. Keep this HUD window running and visible in the Windows taskbar; **do not use `--overlay` initially**.
3. Add a **Window Capture** tab targeting **SCAF HUD — Window Capture**. Capture the client area if available.
4. Verify the live-updating window *in OpenKneeboard on desktop* before launching DCS.
5. Launch DCS in VR with Quest 3; set OpenKneeboard's VR API to OpenXR/Auto as appropriate.
6. Check if the panel appears and updates in the headset, then adjust its size/position.
7. If it does not appear, review https://openkneeboard.com/troubleshooting/steamvr-or-openxr/ and https://openkneeboard.com/troubleshooting/window-capture-compatibility/.

**Limitations:** OpenKneeboard is an overlay/panel, not true head-locked optical HMD nor world-locked symbology. Window Capture may not update when the captured window is fully occluded. Capturing transparent frameless windows can fail. This build is replay only; live IPC is planned for a later iteration.
