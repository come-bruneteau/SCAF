"""Local WebSocket broadcast bridge for validated DCS telemetry v1 packets.

The UDP receiver owns this bridge. Consumers don't open a second DCS UDP port.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

try:
    from websockets.asyncio.server import serve
except ImportError:
    from websockets.server import serve  # websockets 11/12 compatibility

LOG = logging.getLogger(__name__)


class LiveTelemetryServer:
    """Broadcast only the newest JSON packet to each connected local client."""

    def __init__(self, host: str = "127.0.0.1", port: int = 50501):
        self.host = host
        self.port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._shutdown = threading.Event()
        self._startup_error: BaseException | None = None
        self._clients: set[asyncio.Queue[str]] = set()
        self._latest: str | None = None

    async def _client(self, websocket: Any) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        self._clients.add(queue)
        if self._latest is not None:
            queue.put_nowait(self._latest)
        try:
            while True:
                await websocket.send(await queue.get())
        except Exception:
            # A closed consumer is expected; it should never stop UDP reception.
            pass
        finally:
            self._clients.discard(queue)

    def _publish_on_loop(self, message: str) -> None:
        self._latest = message
        for queue in tuple(self._clients):
            if queue.full():
                queue.get_nowait()  # Drop stale data rather than delaying the HUD.
            queue.put_nowait(message)

    def publish(self, packet: dict[str, Any]) -> None:
        """Thread-safe, nonblocking publication from the synchronous receiver."""
        loop = self._loop
        if loop and loop.is_running():
            message = json.dumps(packet, allow_nan=False, separators=(",", ":"))
            loop.call_soon_threadsafe(self._publish_on_loop, message)

    async def _run(self) -> None:
        try:
            async with serve(self._client, self.host, self.port, max_size=65536):
                self._ready.set()
                while not self._shutdown.is_set():
                    await asyncio.sleep(0.1)
        except BaseException as exc:
            self._startup_error = exc
            self._ready.set()
            if not isinstance(exc, asyncio.CancelledError):
                LOG.error("SCAF Live server stopped: %s", exc)
        finally:
            self._loop = None

    def _thread_main(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run())
        finally:
            self._loop.close()
            asyncio.set_event_loop(None)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._shutdown.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._thread_main, name="scaf-live-ws", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("Live WebSocket server startup timed out")
        if self._startup_error is not None:
            raise RuntimeError("Cannot start Live WebSocket server") from self._startup_error

    def stop(self) -> None:
        self._shutdown.set()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
