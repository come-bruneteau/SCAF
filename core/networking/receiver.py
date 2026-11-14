
"""
SCAF-DCS Telemetry
UDP Receiver - Initial communication test
"""

import socket

HOST = "127.0.0.1"
PORT = 50500


def main():
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    server.bind((HOST, PORT))

    print("[SCAF] UDP receiver started")
    print(f"[SCAF] Listening on {HOST}:{PORT}")
    print("[SCAF] Waiting for DCS...\n")

    try:
        while True:
            data, address = server.recvfrom(4096)

            message = data.decode("utf-8")

            print(f"[DCS] {message}")

    except KeyboardInterrupt:
        print("\n[SCAF] Receiver stopped")

    finally:
        server.close()


if __name__ == "__main__":
    main()
