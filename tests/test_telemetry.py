import json
import tempfile
import unittest
from pathlib import Path

from core.models.aircraft_state import AircraftState, TelemetryValidationError
from core.models.session import FlightSession
from core.networking.dispatcher import Dispatcher

PACKET = {
    "protocol": "scaf.telemetry", "version": 1, "type": "aircraft.state",
    "sequence": 1, "timestamp": 2.0, "aircraft": {"type": "Su-25T"},
    "data": {
        "speed_mps": 125.0, "altitude_m": 2400.0,
        "fuel_internal_kg": 3775.0, "fuel_external_kg": None,
        "acceleration_g": {"x": 0.0, "y": 4.71, "z": 0.0},
        "position": {"lat_deg": None, "lon_deg": None, "alt_m": None},
    },
}

class TelemetryTests(unittest.TestCase):
    def test_valid_packet(self):
        state = AircraftState.from_packet(PACKET)
        self.assertEqual(state.aircraft_type, "Su-25T")
        self.assertAlmostEqual(state.indicated_airspeed_kmh, 450.0)
        self.assertEqual(state.normal_g, 4.71)

    def test_reject_invalid(self):
        bad = {**PACKET, "version": 2}
        
        with self.assertRaises(TelemetryValidationError):
            AircraftState.from_packet(bad)
        bad2 = json.loads(json.dumps(PACKET))
        bad2["data"]["speed_mps"] = -3

        with self.assertRaises(TelemetryValidationError):
            AircraftState.from_packet(bad2)

    def test_session_and_dispatch(self):
        hits = []
        dispatcher = Dispatcher()
        dispatcher.subscribe("aircraft.state", hits.append)
        state = AircraftState.from_packet(PACKET)

        with tempfile.TemporaryDirectory() as td:
            session = FlightSession.start(Path(td), state.aircraft_type)
            self.assertTrue(session.append(PACKET, state, "2026-11-15T16:00:00+00:00"))
            self.assertFalse(session.append(PACKET, state, "2026-11-15T16:00:00+00:00"))
            dispatcher.publish("aircraft.state", state)
            session.close()
            self.assertEqual(len(hits), 1)
            self.assertEqual(len((session.directory / "telemetry.jsonl").read_text().splitlines()), 1)
            self.assertTrue(json.loads((session.directory / "metadata.json").read_text())["completed"])


if __name__ == "__main__":
    unittest.main()
