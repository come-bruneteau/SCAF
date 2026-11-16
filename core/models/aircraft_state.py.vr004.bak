"""Validated representation of the existing SCAF telemetry v1 wire format."""

from dataclasses import dataclass
import math
from typing import Any

class TelemetryValidationError(ValueError):
    """An incoming telemetry packet does not match the v1 contract."""

def _number(value: Any, name: str, *, minimum: float | None = None,
            maximum: float | None = None) -> float | None:
    if value is None:
        return None
    
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TelemetryValidationError(f"{name}: expected number or null")
    
    result = float(value)
    if not math.isfinite(result):
        raise TelemetryValidationError(f"{name}: non-finite value")
    
    if minimum is not None and result < minimum:
        raise TelemetryValidationError(f"{name}: below {minimum}")
    
    if maximum is not None and result > maximum:
        raise TelemetryValidationError(f"{name}: above {maximum}")
    
    return result


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TelemetryValidationError(f"{name}: expected object")
    
    return value


def _fields(mapping: dict[str, Any], required: set[str], name: str) -> None:
    missing = required - mapping.keys()
    unknown = mapping.keys() - required
    
    if missing or unknown:
        raise TelemetryValidationError(
            f"{name}: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )


@dataclass(frozen=True)
class Vector3:
    x: float | None
    y: float | None
    z: float | None

@dataclass(frozen=True)
class GeoPosition:
    lat_deg: float | None
    lon_deg: float | None
    alt_m: float | None

@dataclass(frozen=True)
class AircraftState:
    sequence: int
    model_time_s: float
    aircraft_type: str
    indicated_airspeed_mps: float | None
    altitude_asl_m: float | None
    fuel_internal_kg: float | None
    fuel_external_kg: float | None
    acceleration_g: Vector3
    position: GeoPosition

    @property
    def indicated_airspeed_kmh(self) -> float | None:
        return (self.indicated_airspeed_mps * 3.6
                if self.indicated_airspeed_mps is not None else None)

    @property
    def normal_g(self) -> float | None:
        """Candidate normal load factor (DCS local Y); validate against cockpit G meter."""
        return self.acceleration_g.y

    @classmethod
    def from_packet(cls, packet: dict[str, Any]) -> "AircraftState":
        packet = _mapping(packet, "packet")
        _fields(packet, {"protocol", "version", "type", "sequence", "timestamp", "aircraft", "data"}, "packet")

        if packet["protocol"] != "scaf.telemetry" or type(packet["version"]) is not int or packet["version"] != 1 or packet["type"] != "aircraft.state":
            raise TelemetryValidationError("unsupported protocol/version/type")
        
        seq = packet["sequence"]
        if type(seq) is not int or seq < 1:
            raise TelemetryValidationError("sequence: expected positive integer")
        
        time = _number(packet["timestamp"], "timestamp", minimum=0)
        if time is None:
            raise TelemetryValidationError("timestamp: cannot be null")
        
        aircraft = _mapping(packet["aircraft"], "aircraft")
        _fields(aircraft, {"type"}, "aircraft")
        aircraft_type = aircraft["type"]
        if not isinstance(aircraft_type, str) or not aircraft_type.strip():
            raise TelemetryValidationError("aircraft.type: expected nonempty string")
        
        data = _mapping(packet["data"], "data")
        _fields(data, {"speed_mps", "altitude_m", "fuel_internal_kg", "fuel_external_kg", "acceleration_g", "position"}, "data")
        accel = _mapping(data["acceleration_g"], "acceleration_g")
        pos = _mapping(data["position"], "position")
        _fields(accel, {"x", "y", "z"}, "acceleration_g")
        _fields(pos, {"lat_deg", "lon_deg", "alt_m"}, "position")

        return cls(
            sequence=seq,
            model_time_s=time,
            aircraft_type=aircraft_type,
            indicated_airspeed_mps=_number(data["speed_mps"], "speed_mps", minimum=0),
            altitude_asl_m=_number(data["altitude_m"], "altitude_m"),
            fuel_internal_kg=_number(data["fuel_internal_kg"], "fuel_internal_kg", minimum=0),
            fuel_external_kg=_number(data["fuel_external_kg"], "fuel_external_kg", minimum=0),
            acceleration_g=Vector3(*(_number(accel[k], f"acceleration_g.{k}") for k in ("x", "y", "z"))),
            position=GeoPosition(
                lat_deg=_number(pos["lat_deg"], "lat_deg", minimum=-90, maximum=90),
                lon_deg=_number(pos["lon_deg"], "lon_deg", minimum=-180, maximum=180),
                alt_m=_number(pos["alt_m"], "position.alt_m"),
            ),
        )
