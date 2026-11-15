"""SCAF DCS UDP receiver: parse, validate, record, dispatch."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import socket

from core.models.aircraft_state import AircraftState, TelemetryValidationError
from core.models.session import FlightSession
from core.networking.dispatcher import Dispatcher
from core.networking.live_server import LiveTelemetryServer

HOST = "127.0.0.1"
PORT = 50500


def format_value(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def log_state(state: AircraftState) -> None:
    print(
        f"#{state.sequence} {state.aircraft_type} | "
        f"IAS: {format_value(state.indicated_airspeed_kmh)} km/h | "
        f"Altitude: {format_value(state.altitude_asl_m)} m | "
        f"Fuel: {format_value(state.fuel_internal_kg)} kg | "
        f"Normal G (Y): {format_value(state.normal_g)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="SCAF DCS telemetry receiver")
    parser.add_argument("--sessions-dir", type=Path, default=Path("data/sessions"))
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--live-port", type=int, default=50501)
    parser.add_argument("--no-live", action="store_true", help="Disable WebSocket streaming")
    args = parser.parse_args()

    dispatcher = Dispatcher()
    dispatcher.subscribe("aircraft.state", log_state)
    session: FlightSession | None = None
    live = None if args.no_live else LiveTelemetryServer(port=args.live_port)
    if live:
        live.start()
        print(f"[SCAF] Live WebSocket: ws://127.0.0.1:{args.live_port}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((args.host, args.port))
        server.settimeout(0.5)
        print(f"[SCAF] Listening on {args.host}:{args.port}")
        try:
            while True:
                try:
                    raw, _source = server.recvfrom(65535)
                except socket.timeout:
                    continue
                received_at = datetime.now(timezone.utc).isoformat()
                try:
                    packet = json.loads(raw.decode("utf-8"), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {c}")))
                    state = AircraftState.from_packet(packet)
                except (UnicodeDecodeError, ValueError, TelemetryValidationError) as exc:
                    print(f"[SCAF] Discarded invalid packet: {exc}")
                    continue

                reset = session is not None and (
                    state.aircraft_type != session.aircraft_type
                    or (session.last_model_time_s is not None and state.model_time_s < session.last_model_time_s)
                    or (session.last_sequence is not None and state.sequence < session.last_sequence)
                )
                if reset:
                    session.close()
                    session = None
                if session is None:
                    session = FlightSession.start(args.sessions_dir, state.aircraft_type)
                    print(f"[SCAF] Session started: {session.session_id}")
                if not session.append(packet, state, received_at):
                    continue
                dispatcher.publish("aircraft.state", state)
                if live:
                    live.publish(packet)
        except KeyboardInterrupt:
            print("\n[SCAF] Receiver stopped")
        finally:
            if session is not None:
                session.close()
                print(f"[SCAF] Session saved: {session.directory}")
            if live:
                live.stop()


if __name__ == "__main__":
    main()
