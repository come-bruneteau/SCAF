"""VR-005 wire-format compatibility and source patch tests (no VR runtime required)."""
import math
import struct
import unittest
from plugins.vr_hud.openxr.bridge import (FORMAT, FORMAT_V2, MAGIC, MAGIC_V2,
                                          SIZE, SIZE_V2, encode_state)
from core.models.aircraft_state import AircraftState, TelemetryValidationError
from plugins.vr_hud.openxr.apply_vr005 import upgrade_export, upgrade_model, upgrade_schema


def sample():
    return {
        'protocol': 'scaf.telemetry', 'version': 1, 'type': 'aircraft.state',
        'sequence': 22, 'timestamp': 4.2, 'aircraft': {'type': 'Su-25T'},
        'data': {'speed_mps': 100, 'altitude_m': 2300, 'fuel_internal_kg': 1100,
                 'fuel_external_kg': None, 'acceleration_g': {'x': 0, 'y': 1, 'z': 0},
                 'position': {'lat_deg': None, 'lon_deg': None, 'alt_m': None}}
    }


class VR005Tests(unittest.TestCase):
    def test_legacy_wire_format(self):
        packet = sample()
        data = encode_state(AircraftState.from_packet(packet), packet)
        self.assertEqual(len(data), SIZE)
        self.assertEqual(struct.unpack(FORMAT, data), (MAGIC, 22, 360, 2300, 1100, 100))

    def test_attitude_wire_format(self):
        packet = sample()
        packet['data']['attitude'] = {'pitch_rad': math.radians(10),
                                      'bank_rad': math.radians(-25)}
        data = encode_state(AircraftState.from_packet(packet), packet)
        self.assertEqual(len(data), SIZE_V2)
        self.assertEqual(struct.unpack(FORMAT_V2, data),
                         (MAGIC_V2, 22, 360, 2300, 1100, 100, 1000, -2500))

    def test_reject_bad_attitude(self):
        packet = sample()
        packet['data']['attitude'] = {'pitch_rad': float('nan'), 'bank_rad': 0.0}
        with self.assertRaises(TelemetryValidationError):
            AircraftState.from_packet(packet)

    def test_patch_functions_are_idempotent(self):
        minimal_export = "    local location = self_data.LatLongAlt or {}\n" + \
            "            '}' ..\n        '}},'" # Deliberate mismatch: must fail safely.
        with self.assertRaises(RuntimeError):
            upgrade_export(minimal_export)
        self.assertIn('optional', upgrade_model(
            'def _fields(mapping: dict[str, Any], required: set[str], name: str) -> None:\n'
            '    unknown = mapping.keys() - required\n'
            '_fields(data, {"speed_mps", "altitude_m", "fuel_internal_kg", "fuel_external_kg", "acceleration_g", "position"}, "data")'))
        schema = '{"properties":{"data":{"properties":{}}}}'
        self.assertIn('"attitude"', upgrade_schema(schema))

if __name__ == '__main__':
    unittest.main()
