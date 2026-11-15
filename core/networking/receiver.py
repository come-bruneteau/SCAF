
import json
import socket
from datetime import datetime, timezone

HOST = "127.0.0.1"
PORT = 50500

def format_value(value, digits=2):
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def main():
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )
    server.bind((HOST, PORT))

    print(f"[SCAF] Listening on {HOST}:{PORT}")

    try:
        while True:
            raw, address = server.recvfrom(65535)

            try:
                packet = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                print(f"[SCAF] Invalid packet: {exc}")
                continue

            if (
                not isinstance(packet, dict)
                or packet.get("protocol") != "scaf.telemetry"
                or packet.get("version") != 1
                or packet.get("type") != "aircraft.state"
            ):
                print("[SCAF] Unsupported packet")
                continue

            data = packet.get("data", {})
            aircraft = packet.get("aircraft", {})
            acceleration = data.get("acceleration_g") or {}

            speed = data.get("speed_mps")
            speed_kmh = speed * 3.6 if speed is not None else None

            print(
                f"[{datetime.now(timezone.utc).isoformat()}] "
                f"#{packet.get('sequence')} "
                f"{aircraft.get('type', 'Unknown')} | "
                f"Speed: {format_value(speed_kmh)} km/h | "
                f"Altitude: {format_value(data.get('altitude_m'))} m | "
                f"Fuel: {format_value(data.get('fuel_internal_kg'))} kg | "
                f"Normal G: {format_value(acceleration.get("y"))} g | "
                f"Accel Z: {format_value(acceleration.get('z'))} g"
                
            )

    except KeyboardInterrupt:
        print("\n[SCAF] Receiver stopped")

    finally:
        server.close()


if __name__ == "__main__":
    main()
