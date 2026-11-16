"""Tests for VR-005 SHD1/SHD2 packets; no DCS or VR headset required."""
import math
import struct
import unittest

from core.models.aircraft_state import AircraftState, TelemetryValidationError
from plugins.vr_hud.openxr.bridge import (
    FORMAT, FORMAT_V2, MAGIC, MAGIC_V2, SIZE, SIZE_V2, encode_state,
)


def packet():
    return {
        'protocol': 'scaf.telemetry', 'version': 1, 'type': 'aircraft.state',
        'sequence': 22, 'timestamp': 4.2, 'aircraft': {'type': 'Su-25T'},
        'data': {'speed_mps': 100, 'altitude_m': 2300,
                 'fuel_internal_kg': 1100, 'fuel_external_kg': None,
                 'acceleration_g': {'x': 0, 'y': 1, 'z': 0},
                 'position': {'lat_deg': None, 'lon_deg': None, 'alt_m': None}}
    }


class BridgeTests(unittest.TestCase):
    def test_legacy(self):
        p = packet()
        raw = encode_state(AircraftState.from_packet(p), p)
        self.assertEqual(len(raw), SIZE)
        self.assertEqual(struct.unpack(FORMAT, raw), (MAGIC, 22, 360, 2300, 1100, 100))

    def test_attitude(self):
        p = packet()
        p['data']['attitude'] = {'pitch_rad': math.radians(10), 'bank_rad': math.radians(-25)}
        raw = encode_state(AircraftState.from_packet(p), p)
        self.assertEqual(len(raw), SIZE_V2)
        self.assertEqual(struct.unpack(FORMAT_V2, raw),
                         (MAGIC_V2, 22, 360, 2300, 1100, 100, 1000, -2500))

    def test_reject_invalid_attitude(self):
        p = packet()
        p['data']['attitude'] = {'pitch_rad': float('nan'), 'bank_rad': 0.0}
        with self.assertRaises(TelemetryValidationError):
            AircraftState.from_packet(p)


if __name__ == '__main__':
    unittest.main()
