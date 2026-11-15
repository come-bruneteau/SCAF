"""Threaded WebSocket source exposing newest valid aircraft state to Qt polling."""
from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any

from core.models.aircraft_state import AircraftState, TelemetryValidationError

try:
    from websockets.asyncio.client import connect
except ImportError:
    from websockets.client import connect  # websockets 11/12 compatibility


class LiveSource:
    """Qt must call read() on its UI thread; websocket IO stays in a worker."""

    def __init__(self, uri: str = "ws://127.0.0.1:50501", stale_after: float = 2.0):
        self.uri = uri
        self.stale_after = stale_after
        self._lock = threading.Lock()
        self._packet: dict[str, Any] | None = None
        self._updated_at = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="scaf-hud-live")
        self._thread.start()

    def _worker(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                async with connect(self.uri, open_timeout=2, max_size=65536) as ws:
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        try:
                            packet = json.loads(raw)
                            AircraftState.from_packet(packet)
                        except (ValueError, TypeError, TelemetryValidationError):
                            continue
                        with self._lock:
                            self._packet = packet
                            self._updated_at = time.monotonic()
            except Exception:
                # Connection errors are normal before DCS receiver is started.
                # No need to flood the terminal with retry logs.
                pass
            await asyncio.sleep(0.5)

    def read(self) -> dict[str, Any]:
        with self._lock:
            if self._packet is None or time.monotonic() - self._updated_at > self.stale_after:
                return {}  # Prevent showing old flight values as live readings.
            return self._packet

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
