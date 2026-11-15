"""PySide6 prototype HUD. No direct OpenXR injection."""
from __future__ import annotations

import math
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

ACCENT = QColor("#74F7CD")
DIM = QColor("#82B7A9")


def display_number(value, digits=0, scale=1.0, suffix="") -> str:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return "--"
    return f"{value * scale:.{digits}f}{suffix}"


class HudWindow(QWidget):
    def __init__(self, *, capture=True, width=960, height=540):
        super().__init__()
        self.capture = capture
        self.packet = {}
        self.setWindowTitle("SCAF HUD — Window Capture")
        self.resize(width, height)
        self.setMinimumSize(640, 360)
        # Important: a normal taskbar-visible window is most compatible with
        # Windows Graphics Capture / OpenKneeboard Window Capture.
        if not capture:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_packet(self, packet: dict) -> None:
        self.packet = packet
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        scale_x = self.width() / 960
        scale_y = self.height() / 540
        painter.scale(scale_x, scale_y)
        if self.capture:
            painter.fillRect(QRectF(0, 0, 960, 540), QColor("#07131B"))
        else:
            painter.fillRect(QRectF(0, 0, 960, 540), QColor(7, 19, 27, 45))

        data = self.packet.get("data") or {}
        aircraft = self.packet.get("aircraft") or {}
        acceleration = data.get("acceleration_g") or {}
        fuel_inside = data.get("fuel_internal_kg")
        fuel_outside = data.get("fuel_external_kg")
        fuel_total = (fuel_inside + fuel_outside
                      if isinstance(fuel_inside, (int, float)) and isinstance(fuel_outside, (int, float))
                      else fuel_inside)
        self._text(painter, 38, 38, "SCAF  /  HUD DE VOL", 16, DIM)
        self._text(painter, 38, 64, str(aircraft.get("type", "AUCUN AVION")), 14, DIM)
        self._text(painter, 725, 38, "RELECTURE  •  EXPÉRIMENTAL", 12, DIM)
        self._metric(painter, 55, 135, "VITESSE INDIQUÉE", display_number(data.get("speed_mps"), scale=3.6), "km/h")
        self._metric(painter, 700, 135, "ALTITUDE (NIVEAU MER)", display_number(data.get("altitude_m")), "m")
        self._metric(painter, 55, 425, "MASSE CARBURANT", display_number(fuel_total, digits=1), "kg")
        self._metric(painter, 700, 425, "FACTEUR DE CHARGE", display_number(acceleration.get("y"), digits=2), "G")

        pen = QPen(ACCENT)
        pen.setWidthF(2.2)
        painter.setPen(pen)
        painter.drawLine(420, 270, 465, 270)
        painter.drawLine(495, 270, 540, 270)
        painter.drawLine(480, 210, 480, 255)
        painter.drawLine(480, 285, 480, 330)
        painter.drawEllipse(467, 257, 26, 26)
        painter.setPen(QPen(DIM, 1.3))
        for yy in (203, 237, 303, 337):
            painter.drawLine(325, yy, 390, yy)
            painter.drawLine(570, yy, 635, yy)
        self._text(painter, 480, 385, "DÉMO : AFFICHAGE FIXÉ AU CASQUE", 12, DIM, centered=True)
        self._text(painter, 480, 510, "AUCUN REPÈRE ANCRÉ DANS LE MONDE POUR CETTE VERSION", 11, DIM, centered=True)
        painter.end()

    def _text(self, painter, x, y, value, size, color, centered=False):
        painter.setFont(QFont("Consolas", size, QFont.Weight.DemiBold))
        painter.setPen(color)
        if centered:
            painter.drawText(QRectF(x - 240, y - 22, 480, 32), Qt.AlignmentFlag.AlignCenter, value)
        else:
            painter.drawText(x, y, value)

    def _metric(self, painter, x, y, title, value, unit):
        self._text(painter, x, y, title, 12, DIM)
        self._text(painter, x, y + 52, f"{value} {unit}", 29, ACCENT)
