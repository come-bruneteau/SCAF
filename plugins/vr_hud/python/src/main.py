"""SCAF HUD MVP -- standalone desktop application for OpenKneeboard capture."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from .telemetry_source import ReplaySource

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "hud.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prototype SCAF HUD : relecture de vol")
    parser.add_argument("session", help="Dossier de session ou fichier telemetry.jsonl")
    parser.add_argument("--speed", type=float, default=1.0, help="Vitesse de relecture (défaut : 1)")
    parser.add_argument("--no-loop", action="store_true")
    parser.add_argument("--check", action="store_true", help="Vérifier les données sans ouvrir la fenêtre")
    parser.add_argument("--overlay", action="store_true", help="Fenêtre transparente expérimentale (déconseillée avec OpenKneeboard)")
    args = parser.parse_args(argv)
    source = ReplaySource(args.session, speed=args.speed, loop=not args.no_loop)
    print(f"[SCAF HUD] {len(source.packets)} mesures, {source.duration:.2f}s, {source.path}")
    if args.check:
        print(json.dumps(source.packets[0], ensure_ascii=False, indent=2))
        return 0

    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from .renderer import HudWindow
    except ImportError as exc:
        print("Installer PySide6 : python -m pip install -r plugins/vr_hud/requirements.txt", file=sys.stderr)
        raise SystemExit(2) from exc

    config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    app = QApplication(sys.argv[:1])
    window = HudWindow(
        capture=not args.overlay,
        width=config.get("width", 960),
        height=config.get("height", 540),
    )
    timer = QTimer()
    timer.timeout.connect(lambda: window.set_packet(source.read()))
    timer.start(max(16, int(1000 / config.get("refresh_hz", 30))))
    window.set_packet(source.read())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
