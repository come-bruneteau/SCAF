"""Tests for the local live stream, independent of DCS and Qt."""
import asyncio
import json
import socket
import time
import unittest

from core.networking.live_server import LiveTelemetryServer
from plugins.vr_hud.python.src.live_source import LiveSource

PACKET = {
    "protocol": "scaf.telemetry", "version": 1, "type": "aircraft.state",
    "sequence": 1, "timestamp": 2.0, "aircraft": {"type": "Su-25T"},
    "data": {"speed_mps": 125.0, "altitude_m": 2400.0,
        "fuel_internal_kg": 3775.0, "fuel_external_kg": None,
        "acceleration_g": {"x": 0.0, "y": 4.71, "z": 0.0},
        "position": {"lat_deg": None, "lon_deg": None, "alt_m": None}}
}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LiveTests(unittest.TestCase):
    def test_server_broadcasts_packet(self):
        from websockets.asyncio.client import connect
        port = free_port()
        server = LiveTelemetryServer(port=port)
        server.start()
        async def check():
            async with connect(f"ws://127.0.0.1:{port}") as ws:
                server.publish(PACKET)
                raw = await asyncio.wait_for(ws.recv(), timeout=2)
                return json.loads(raw)
        try:
            result = asyncio.run(check())
            self.assertEqual(result["sequence"], 1)
        finally:
            server.stop()

    def test_client_reconnect_and_stale(self):
        port = free_port()
        client = LiveSource(f"ws://127.0.0.1:{port}", stale_after=0.25)
        client.start()  # starts before receiver exists
        server = LiveTelemetryServer(port=port)
        server.start()
        try:
            result = {}
            until = time.monotonic() + 4
            while time.monotonic() < until:
                server.publish(PACKET)
                result = client.read()
                if result.get("sequence") == 1:
                    break
                time.sleep(0.05)
            self.assertEqual(result.get("sequence"), 1)
            time.sleep(0.4)
            self.assertEqual(client.read(), {})
        finally:
            client.stop()
            server.stop()
