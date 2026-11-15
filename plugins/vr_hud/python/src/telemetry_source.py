"""Offline replay of SCAF session JSONL (no external dependencies)."""
from __future__ import annotations

import json
import time
from bisect import bisect_right
from pathlib import Path


class ReplaySource:
    """Read an archived flight and expose its most recent packet by model time."""

    def __init__(self, session_path: str | Path, *, speed: float = 1.0, loop: bool = True):
        if speed <= 0:
            raise ValueError("Replay speed must be positive")
        path = Path(session_path)
        if path.is_dir():
            path = path / "telemetry.jsonl"
        self.path = path
        self.speed = speed
        self.loop = loop
        self.packets: list[dict] = []
        self.timestamps: list[float] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}") from exc
            packet = record.get("packet", record)
            if (not isinstance(packet, dict)
                    or packet.get("protocol") != "scaf.telemetry"
                    or packet.get("version") != 1
                    or packet.get("type") != "aircraft.state"):
                continue
            t = packet.get("timestamp")
            if isinstance(t, (int, float)) and not isinstance(t, bool):
                self.packets.append(packet)
                self.timestamps.append(float(t))
        if not self.packets:
            raise ValueError(f"No valid aircraft.state packets in {path}")
        ordered = sorted(zip(self.timestamps, self.packets), key=lambda p: p[0])
        self.timestamps, self.packets = map(list, zip(*ordered))
        self.start = self.timestamps[0]
        self.duration = max(0.0, self.timestamps[-1] - self.start)
        self.started_at = time.monotonic()

    def at_elapsed(self, elapsed_seconds: float) -> dict:
        elapsed = max(0, elapsed_seconds) * self.speed
        if self.loop and self.duration > 0:
            elapsed %= self.duration
        else:
            elapsed = min(elapsed, self.duration)
        target = self.start + elapsed
        index = max(0, bisect_right(self.timestamps, target) - 1)
        return self.packets[index]

    def read(self) -> dict:
        return self.at_elapsed(time.monotonic() - self.started_at)
