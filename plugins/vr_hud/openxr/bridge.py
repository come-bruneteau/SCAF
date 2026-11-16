"""Bridge validated SCAF WebSocket telemetry to the in-process OpenXR HUD.

The OpenXR layer must never block DCS rendering on a WebSocket connection.
We therefore forward the latest data via a small, local UDP datagram.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import socket
import struct
import time

from core.models.aircraft_state import AircraftState, TelemetryValidationError

MAGIC = b"SHD1"
MAGIC_V2 = b"SHD2"
MISSING = -(2**31)
FORMAT = "<4sIiiii"  # magic, sequence, speed_kmh, altitude_m, fuel_kg, normal_g_centi
SIZE = struct.calcsize(FORMAT)
FORMAT_V2 = "<4sIiiiiii"  # SHD2, sequence, speed, altitude, fuel, normal G, pitch, bank
SIZE_V2 = struct.calcsize(FORMAT_V2)
LOG = logging.getLogger("scaf.vr_hud.openxr")


def as_int(value: float | None, scale: float = 1.0) -> int:
    if value is None or not math.isfinite(value):
        return MISSING
    rounded = round(value * scale)
    return max(MISSING + 1, min(2**31 - 1, rounded))


def encode_state(state: AircraftState, packet: dict | None = None) -> bytes:
    fuel = state.fuel_internal_kg
    if fuel is not None and state.fuel_external_kg is not None:
        fuel += state.fuel_external_kg
    fields = (state.sequence & 0xFFFFFFFF, as_int(state.indicated_airspeed_kmh),
              as_int(state.altitude_asl_m), as_int(fuel), as_int(state.normal_g, 100))
    attitude = (packet or {}).get("data", {}).get("attitude")
    if isinstance(attitude, dict):
        # DCS exports Euler angles in radians; the HUD wire format uses centidegrees.
        pitch = as_int(attitude.get("pitch_rad"), 18000 / math.pi)
        bank = as_int(attitude.get("bank_rad"), 18000 / math.pi)
        return struct.pack(FORMAT_V2, MAGIC_V2, *fields, pitch, bank)
    return struct.pack(FORMAT, MAGIC, *fields)


async def forward_live(uri: str, destination: tuple[str, int], retry_seconds: float) -> None:
    try:
        from websockets.asyncio.client import connect
    except ImportError:
        from websockets.client import connect

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        while True:
            try:
                LOG.info("Connexion au noyau SCAF : %s", uri)
                async with connect(uri, open_timeout=3, max_size=65536) as websocket:
                    LOG.info("Connecté. Diffusion locale UDP sur %s:%d", *destination)
                    async for raw in websocket:
                        try:
                            packet = json.loads(raw)
                            state = AircraftState.from_packet(packet)
                        except (ValueError, TypeError, TelemetryValidationError) as exc:
                            LOG.warning("Paquet ignoré : %s", exc)
                            continue
                        sender.sendto(encode_state(state, packet), destination)
            except Exception as exc:
                # DCS/SCAF Core may start after the bridge; reconnection is expected.
                LOG.warning("WebSocket indisponible (%s). Nouvelle tentative dans %.1f s.", exc, retry_seconds)
            await asyncio.sleep(retry_seconds)


async def demo(destination: tuple[str, int]) -> None:
    """Send unmistakably synthetic moving values, without starting DCS."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sequence = 0
        started = time.monotonic()
        while True:
            elapsed = time.monotonic() - started
            sequence += 1
            speed = 480 + 35 * math.sin(elapsed / 3)
            altitude = 2400 + 80 * math.sin(elapsed / 7)
            fuel = 3750 - elapsed * 0.1
            g = 1.0 + 0.4 * math.sin(elapsed / 2)
            pitch = 10 * math.sin(elapsed / 5)
            bank = 23 * math.sin(elapsed / 4)
            sender.sendto(struct.pack(FORMAT_V2, MAGIC_V2, sequence, round(speed), round(altitude),
                                      round(fuel), round(100 * g), round(pitch * 100),
                                      round(bank * 100)), destination)
            await asyncio.sleep(0.2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pont SCAF WebSocket -> HUD OpenXR local")
    parser.add_argument("--ws", default="ws://127.0.0.1:50501", help="Serveur Live de SCAF Core")
    parser.add_argument("--port", type=int, default=50502, help="Port UDP local du module OpenXR")
    parser.add_argument("--retry", type=float, default=1.0, help="Délai de reconnexion WebSocket en secondes")
    parser.add_argument("--demo", action="store_true", help="Valeurs simulées pour tester le rendu sans DCS")
    args = parser.parse_args()
    if not (1 <= args.port <= 65535) or args.retry <= 0:
        parser.error("Le port et le délai de reconnexion doivent être valides")
    logging.basicConfig(level=logging.INFO, format="[SCAF VR] %(message)s")
    destination = ("127.0.0.1", args.port)
    try:
        asyncio.run(demo(destination) if args.demo else forward_live(args.ws, destination, args.retry))
    except KeyboardInterrupt:
        print("\n[SCAF VR] Pont arrêté")


if __name__ == "__main__":
    main()
