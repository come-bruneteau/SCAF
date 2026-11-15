"""Local recording sessions; no DCS protocol changes required."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
from typing import TextIO

from core.models.aircraft_state import AircraftState

@dataclass
class FlightSession:
    directory: Path
    session_id: str
    started_at_utc: str
    aircraft_type: str
    packets: int = 0
    missing_sequences: int = 0
    last_sequence: int | None = None
    last_model_time_s: float | None = None
    _handle: TextIO | None = field(default=None, repr=False)

    @classmethod
    def start(cls, base_dir: Path, aircraft_type: str) -> "FlightSession":
        now = datetime.now(timezone.utc)
        session_id = f"{now:%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:8]}"
        directory = base_dir / session_id
        directory.mkdir(parents=True, exist_ok=False)
        session = cls(directory, session_id, now.isoformat(), aircraft_type)
        session._handle = (directory / "telemetry.jsonl").open("w", encoding="utf-8", newline="\n")
        session._write_metadata(completed=False)

        return session

    def append(self, packet: dict, state: AircraftState, received_at_utc: str) -> bool:
        if self._handle is None:
            raise RuntimeError("session is closed")
        
        if self.last_sequence is not None and state.sequence <= self.last_sequence:
            return False  # duplicate/out-of-order; receiver handles session resets
        
        if self.last_sequence is not None:
            self.missing_sequences += max(0, state.sequence - self.last_sequence - 1)

        self._handle.write(json.dumps({"received_at_utc": received_at_utc, "packet": packet}, ensure_ascii=False, allow_nan=False) + "\n")
        self._handle.flush()
        self.packets += 1
        self.last_sequence = state.sequence
        self.last_model_time_s = state.model_time_s

        return True

    def _write_metadata(self, completed: bool) -> None:
        payload = {
            "session_id": self.session_id,
            "started_at_utc": self.started_at_utc,
            "ended_at_utc": datetime.now(timezone.utc).isoformat() if completed else None,
            "aircraft_type": self.aircraft_type,
            "packets": self.packets,
            "missing_sequences": self.missing_sequences,
            "completed": completed,
        }

        (self.directory / "metadata.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
            self._write_metadata(completed=True)
