# SCAF — DCS Plugins

**Flight Telemetry, Mission Analysis, Aircraft Automation & Virtual Reality**

SCAF is an open-source project developed as part of a first-year engineering academic project at the **École Nationale Supérieure de Cognitique (ENSC)**, Bordeaux INP, France, during the 2026–2027 academic year.

The project aims to extend **Digital Combat Simulator (DCS World)** through modular software components for real-time aircraft telemetry, post-flight analysis, mission planning, aircraft automation, and virtual reality.

The architecture emphasizes **modularity, interoperability, maintainability, and reusability**, allowing future students and contributors to develop additional features independently.

The project uses generic technologies and established standards whenever possible, including Lua, Python, UDP, WebSocket, and OpenXR.

---

## Project Objectives

SCAF focuses on four main areas:

- **Flight Data Acquisition:** Collect and process aircraft telemetry in real time.
- **Flight Analysis:** Record simulation sessions and generate detailed reports containing flight statistics, graphs, and trajectories.
- **Mission Planning and Automation:** Analyze mission feasibility and explore automated aircraft and drone behaviors.
- **Virtual Reality:** Develop an augmented flight information display compatible with VR headsets.

The project also supports academic investigations into pilot performance, cognitive workload, and human–machine interaction.

## Architecture

SCAF follows a modular architecture built around a shared Python core.

```text
                       DCS World
                           |
                      Lua Export
                           |
                      UDP :50500
                           |
                           v
                    SCAF Core
                ┌──────────┴──────────┐
                |                     |
           Networking              Protocol
                |                     |
                └──────────┬──────────┘
                           |
                    Aircraft State
                           |
                       Dispatcher
                           |
              ┌────────────┼─────────────┐
              |            |             |
              v            v             v
         Recording      Live Stream   Future Modules
              |            |
              v            v
         Flight Report   WebSocket :50501
              |            |
              v            v
         Graphs / PDF     VR HUD
                           |
                      OpenKneeboard
                           |
                         OpenXR
                           |
                       VR Headset
```

### SCAF Core

The core provides the common infrastructure required by all plugins:

- DCS telemetry acquisition through Lua
- UDP message reception
- JSON protocol validation
- Aircraft state normalization
- Message dispatching
- Session recording and metadata management
- Local WebSocket streaming
- Aircraft-specific configurations

All plugins should communicate through the core whenever possible instead of implementing their own DCS data acquisition systems.

## Repository Structure

```text
SCAF/
├── ai/
│   ├── reinforcement_learning/
│   └── multi_agent/
│
├── core/
│   ├── aircraft/
│   ├── dcs/
│   │   └── lua/
│   │       └── Export.lua
│   ├── models/
│   ├── networking/
│   └── protocol/
│
├── plugins/
│   ├── flight_report/
│   ├── mission_automation/
│   ├── mission_validator/
│   └── vr_hud/
│
├── docs/
├── examples/
├── tests/
├── tools/
├── README.md
└── LICENSE
```

Each plugin contains its own `README.md` explaining its architecture, installation, configuration, and usage.

## Plugins

### Flight Report

**Status: Functional**

The Flight Report plugin generates detailed reports from recorded DCS simulation sessions.

Features include:

- Flight duration and distance analysis
- Airspeed and altitude statistics
- Fuel consumption analysis
- Normal G-force measurements
- Flight trajectory visualization
- CSV and JSON exports
- Automatic PDF report generation

The plugin operates independently of DCS by processing previously recorded sessions.

**Documentation:** [Flight Report](plugins/flight_report/README.md)

### VR HUD

**Status: Windows and OpenKneeboard integration validated — headset testing pending**

The VR HUD plugin provides an additional flight information interface.

Currently implemented:

- Real-time aircraft telemetry display
- Recorded session playback
- Local WebSocket communication
- Configurable graphical interface
- Windows window capture through OpenKneeboard
- Automatic reconnection and stale-data handling

Displayed information includes:

- Airspeed
- Altitude
- Fuel
- Normal G-force

The target VR headset is the **Meta Quest 3**.

Future developments include a hybrid display combining:

- **Head-locked elements:** Information displayed relative to the pilot's head.
- **World-locked elements:** Navigation markers and aircraft information associated with positions in the simulated world.

The current implementation uses OpenKneeboard for VR window integration. Native head-locked rendering and world-locked 3D markers are not yet implemented.

**Documentation:** [VR HUD](plugins/vr_hud/README.md)

### Mission Validator

**Status: Planned**

The Mission Validator will analyze flight plans against measurable constraints.

Planned capabilities include:

- Fuel requirements and safety reserves
- Flight range analysis
- Aircraft-specific operational constraints
- Route feasibility
- G-force constraints
- Payload and mission configuration checks

The objective is to support mission preparation through deterministic analysis and explainable results.

**Documentation:** [Mission Validator](plugins/mission_validator/README.md)

### Mission Automation

**Status: Planned — Separate collaborative development**

The Mission Automation plugin will explore automated aircraft coordination using DCS scripting capabilities.

Planned functionalities include:

- Aircraft waypoint navigation
- Formation coordination
- Drone following behavior
- Autonomous mission tasks
- Multi-aircraft coordination

Future research may explore reinforcement learning and multi-agent decision-making within the simulation environment.

**Documentation:** [Mission Automation](plugins/mission_automation/README.md)

---

## Requirements

### Software

| Component | Requirement |
|---|---|
| Operating system | Windows |
| Flight simulator | DCS World (Steam or Standalone) |
| Programming languages | Python 3, Lua |
| Networking | Local UDP and WebSocket |
| VR integration | OpenKneeboard and a compatible OpenXR runtime |
| VR headset | Meta Quest 3 (current development target) |
| Version control | Git |

Python dependencies are managed separately for each component through its `requirements.txt` file.

### Hardware

- Computer capable of running DCS World
- Keyboard and mouse or compatible flight controls
- VR-ready PC and compatible headset for VR functionality

A VR headset is **not required** for telemetry acquisition, session recording, or flight report generation.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/come-bruneteau/SCAF.git
cd SCAF
```

### 2. Install Python dependencies

From the repository root:

```powershell
python -m pip install -r core/networking/requirements.txt
python -m pip install -r plugins/flight_report/requirements.txt
python -m pip install -r plugins/vr_hud/requirements.txt
```

### 3. Configure DCS

Install the Lua exporter in the DCS user scripts directory:

```text
Saved Games/
└── DCS/
    └── Scripts/
        └── Export.lua
```

The source file is maintained at:

```text
core/dcs/lua/Export.lua
```

Copy the exporter into the appropriate DCS user directory.

If an `Export.lua` file already exists, integrate the SCAF code without overwriting existing third-party integrations.

The default UDP endpoint is:

```text
127.0.0.1:50500
```

### 4. Start the SCAF Core

```powershell
python -m core.networking.receiver
```

The core receives DCS telemetry, processes packets, and records flight sessions.

Its local WebSocket service is available at:

```text
ws://127.0.0.1:50501
```

### 5. Launch DCS

Start a DCS mission using a supported aircraft.

SCAF will begin receiving telemetry when the simulator exports valid aircraft data.

## Flight Report Usage

Recorded flight sessions are stored under:

```text
data/
└── sessions/
    └── SESSION_ID/
        ├── metadata.json
        └── telemetry.jsonl
```

To generate a flight report:

```powershell
python -m plugins.flight_report.python.src.generate_report "data/sessions/SESSION_ID"
```

The generated outputs include a PDF report, graphs, and exported session statistics.

## VR HUD Usage

### Replay Mode

Replay data from a recorded DCS session:

```powershell
python -m plugins.vr_hud.python.src.main "data/sessions/SESSION_ID"
```

### Live Mode

Start the SCAF Core first, then launch:

```powershell
python -m plugins.vr_hud.python.src.main --live
```

### OpenKneeboard Integration

1. Start the SCAF HUD.
2. Open OpenKneeboard.
3. Add a Window Capture tab.
4. Select the SCAF HUD window.
5. Configure the VR placement and scaling.
6. Launch DCS in VR with a compatible headset.

OpenKneeboard capture has been validated on Windows. The complete Meta Quest 3 integration remains subject to headset testing.

---

## Communication Protocol

The project uses a versioned JSON telemetry protocol.

```json
{
  "protocol": "scaf.telemetry",
  "version": 1,
  "type": "aircraft.state",
  "sequence": 42,
  "timestamp": 12.4,
  "aircraft": {
    "type": "Su-25T"
  },
  "data": {
    "speed_mps": 125.8,
    "altitude_m": 2400.0,
    "fuel_internal_kg": 1800.0,
    "acceleration_g": {
      "x": 0.0,
      "y": 1.0,
      "z": 0.0
    }
  }
}
```

*Example values are illustrative.*

The protocol supports normalized units, optional measurements, aircraft identification, and message sequencing.

Detailed documentation is available in `core/protocol/`.

## Development and Testing

The project uses Python's `unittest` framework for automated testing.

Run the test suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

Changes should be tested before being merged.

Recommended commit convention:

```text
feat: add a feature
fix: correct a bug
docs: update documentation
refactor: improve code structure
test: add or update tests
chore: update project tooling
```

## Project Roadmap

| Component | Status |
|---|---|
| Lua → Python UDP bridge | Completed |
| Real-time aircraft telemetry | Completed |
| Centralized telemetry processing | Completed |
| Flight session recording | Completed |
| PDF flight reports | Completed |
| VR HUD replay mode | Completed |
| VR HUD live mode | Completed |
| OpenKneeboard desktop capture | Completed |
| Meta Quest 3 in-game verification | Pending |
| Head-locked HUD | Planned |
| World-locked markers | Planned |
| Mission Validator | Planned |
| Mission Automation | Planned |
| Reinforcement learning | Exploratory |

Status descriptions refer to the project's current development and testing progress, not production certification.

## Academic Context

SCAF is developed within the 2026–2027 multidisciplinary engineering project at ENSC.

The academic work combines:

- Flight simulation and pilot training
- Software engineering
- Human–computer interaction
- Cognitive workload analysis
- Experimental observation and evaluation

The software components are intended to support measurable experimentation, reproducible analysis, and future development by other students.

## Contributing

Contributions are welcome.

When adding or modifying a plugin:

1. Follow the shared SCAF architecture.
2. Prefer existing core services over duplicate implementations.
3. Document the plugin in its own `README.md`.
4. Include relevant tests.
5. Maintain compatibility with the shared protocol.

## License

This project is distributed under the terms of the [MIT License](LICENSE).

## Disclaimer

SCAF is an independent academic and experimental project.

It is not affiliated with or officially endorsed by Eagle Dynamics, Meta, Thales, or their respective partners.

DCS World and the names of third-party products remain the property of their respective owners.

The software is intended for simulation, research, and educational purposes. It is not designed or certified for real-world aircraft operation or safety-critical flight decisions.
