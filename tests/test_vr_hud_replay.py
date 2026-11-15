import json
import tempfile
import unittest
from pathlib import Path
from plugins.vr_hud.python.src.telemetry_source import ReplaySource


def packet(sequence, timestamp):
    return {"protocol": "scaf.telemetry", "version": 1, "type": "aircraft.state", "sequence": sequence, "timestamp": timestamp, "data": {"speed_mps": sequence}}


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "telemetry.jsonl"
        self.path.write_text("\n".join(json.dumps({"received_at_utc": "2026-11-15T00:00:00Z", "packet": packet(i+1, i)}) for i in range(3)), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_start_and_progress(self):
        source = ReplaySource(self.path, loop=False)
        self.assertEqual(source.at_elapsed(0)["sequence"], 1)
        self.assertEqual(source.at_elapsed(1.1)["sequence"], 2)
        self.assertEqual(source.at_elapsed(100)["sequence"], 3)

    def test_loop(self):
        source = ReplaySource(self.path)
        self.assertEqual(source.at_elapsed(2.5)["sequence"], 1)

    def test_invalid_speed(self):
        with self.assertRaises(ValueError):
            ReplaySource(self.path, speed=0)

    def test_empty_log(self):
        self.path.write_text("", encoding="utf-8")
        with self.assertRaises(ValueError):
            ReplaySource(self.path)


if __name__ == "__main__":
    unittest.main()
