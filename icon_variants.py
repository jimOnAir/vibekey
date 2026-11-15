#!/usr/bin/env python3
# PROTOTYPE: render tray-icon variants for vibekey (purple drop + "u", point
# down, "u" centered on the icon box). Offscreen — run:
#   QT_QPA_PLATFORM=offscreen python3 icon_variants.py
# Writes icons/variant_<X>_<32|128>.png and icons_contact.png (a labelled sheet).

import os
import sys

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

PURPLE = QColor("#7c3aed")
PURPLE_HI = QColor("#8b5cf6")
PURPLE_LO = QColor("#6d28d9")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "icons")


def paint_drop(p, s, cx, cy, top, tip, bulb_r, brush, pen=None):
    """point-down teardrop inside the circle at (cx, cy+?) — bulb center given."""
    if pen is None:
        p.setPen(Qt.NoPen)
    else:
        p.setPen(pen)
        p.setBrush(Qt.NoBrush if brush is None else brush)
        # stroked drop: circle + tangent lines to tip
        p.drawEllipse(QPointF(cx, cy), bulb_r, bulb_r)
        import math
        d = tip - cy
        half = math.asin(min(1.0, bulb_r / d)) if d > bulb_r else 0
        for sgn in (-1, 1):
            a = math.radians(90 + math.degrees(half) * sgn)
            tx, ty = cx + bulb_r * math.cos(math.radians(-90 + math.degrees(half) * sgn * -1)), cy
            pass
        # simpler: polygon approximating tangents
        p.drawLine(QPointF(cx - bulb_r * 0.97, cy + bulb_r * 0.25), QPointF(cx, tip))
        p.drawLine(QPointF(cx + bulb_r * 0.97, cy + bulb_r * 0.25), QPointF(cx, tip))
        return
    p.setBrush(brush)
    import math
    p.drawPolygon([QPointF(cx, tip), QPointF(cx - bulb_r * 0.93, cy + bulb_r * 0.22),
                   QPointF(cx + bulb_r * 0.93, cy + bulb_r * 0.22)])
    p.drawEllipse(QPointF(cx, cy), bulb_r, bulb_r)


def u_glyph(p, s, color, cx, cy, scale=1.0, bold=True):
    p.setPen(color)
    f = QFont("sans", int(s * 0.42 * scale), QFont.Bold if bold else QFont.Normal)
    p.setFont(f)
    r = s * 0.75
    p.drawText(QRectF(cx - r / 2, cy - r / 2 - s * 0.02 * scale, r, r), Qt.AlignCenter, "u")


def variant_a(pm):  # classic: solid purple drop, white u at icon center
    s = pm.width()
    p = QPainter(pm)
    paint_drop(p, s, 16 / 32 * s, 13.5 / 32 * s, 2 / 32 * s, 30 / 32 * s, 10.5 / 32 * s, PURPLE)
    u_glyph(p, s, QColor("white"), s / 2, s / 2)
    p.end()


def variant_b(pm):  # badge: purple rounded square, white drop, purple u
    s = pm.width()
    p = QPainter(pm)
    p.setPen(Qt.NoPen)
    p.setBrush(PURPLE)
    p.drawRoundedRect(s * 0.06, s * 0.06, s * 0.88, s * 0.88, s * 0.22, s * 0.22)
    paint_drop(p, s, 16 / 32 * s, 13.5 / 32 * s, 2.5 / 32 * s, 29 / 32 * s, 10 / 32 * s, QColor("white"))
    u_glyph(p, s, PURPLE, s / 2, s / 2)
    p.end()


def variant_c(pm):  # gradient drop, white u, subtle deeper tip
    s = pm.width()
    p = QPainter(pm)
    g = __import__("PySide6.QtGui", fromlist=["QLinearGradient"]).QLinearGradient(0, 0, 0, s)
    g.setColorAt(0, PURPLE_HI)
    g.setColorAt(1, PURPLE_LO)
    paint_drop(p, s, 16 / 32 * s, 13.5 / 32 * s, 2 / 32 * s, 30 / 32 * s, 10.5 / 32 * s, g)
    u_glyph(p, s, QColor("white"), s / 2, s / 2)
    p.end()


def variant_d(pm):  # outline drop, purple u — light trays
    s = pm.width()
    p = QPainter(pm)
    pen = QPen(PURPLE, max(2.0, s * 0.08), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(16 / 32 * s, 15.5 / 32 * s), 9 / 32 * s, 9 / 32 * s)
    p.drawLine(QPointF(16 / 32 * s - 8.6 / 32 * s, 17.5 / 32 * s), QPointF(16 / 32 * s, 29 / 32 * s))
    p.drawLine(QPointF(16 / 32 * s + 8.6 / 32 * s, 17.5 / 32 * s), QPointF(16 / 32 * s, 29 / 32 * s))
    u_glyph(p, s, PURPLE, s / 2, s * 0.47)
    p.end()


def variant_e(pm):  # circle badge: purple disc, white drop small, u centered on icon
    s = pm.width()
    p = QPainter(pm)
    p.setPen(Qt.NoPen)
    p.setBrush(PURPLE)
    p.drawEllipse(s * 0.03, s * 0.03, s * 0.94, s * 0.94)
    paint_drop(p, s, 16 / 32 * s, 13 / 32 * s, 3.5 / 32 * s, 27.5 / 32 * s, 9 / 32 * s, QColor("white"))
    u_glyph(p, s, PURPLE, s / 2, s / 2, scale=0.9)
    p.end()


def variant_f(pm):  # glossy drop: A + highlight sheen on the bulb
    s = pm.width()
    variant_a(pm)
    p = QPainter(pm)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 70))
    p.drawEllipse(QRectF(s * 0.22, s * 0.12, s * 0.30, s * 0.20))
    p.end()


def variant_g(pm):  # two-tone: deeper tip under the bulb
    s = pm.width()
    p = QPainter(pm)
    p.setPen(Qt.NoPen)
    p.setBrush(PURPLE_LO)
    p.drawPolygon([QPointF(16 / 32 * s, 30 / 32 * s), QPointF(6.7 / 32 * s, 16.2 / 32 * s),
                   QPointF(25.3 / 32 * s, 16.2 / 32 * s)])
    p.setBrush(PURPLE)
    p.drawEllipse(QPointF(16 / 32 * s, 13.5 / 32 * s), 10.5 / 32 * s, 10.5 / 32 * s)
    u_glyph(p, s, QColor("white"), s / 2, s / 2)
    p.end()


def variant_i(pm):  # "u" drips into the tip: small drip line ties glyph to drop
    s = pm.width()
    paint_drop(p := QPainter(pm), s, 16 / 32 * s, 13.5 / 32 * s, 2 / 32 * s, 30 / 32 * s, 10.5 / 32 * s, PURPLE)
    u_glyph(p, s, QColor("white"), s / 2, s * 0.46, scale=0.92)
    pen = p.pen()
    p.setPen(QPen(QColor(255, 255, 255, 220), max(1.6, s * 0.055), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(s / 2, s * 0.66), QPointF(s / 2, s * 0.74))
    p.setPen(pen)
    p.end()


def variant_j(pm):  # punched-out "u": transparent negative space in the drop
    s = pm.width()
    p = QPainter(pm)
    paint_drop(p, s, 16 / 32 * s, 13.5 / 32 * s, 2 / 32 * s, 30 / 32 * s, 10.5 / 32 * s, PURPLE)
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    f = QFont("sans", int(s * 0.42), QFont.Bold)
    p.setFont(f)
    p.setPen(QColor(0, 0, 0, 255))
    p.drawText(QRectF(s / 2 - s * 0.375, s / 2 - s * 0.375, s * 0.75, s * 0.75), Qt.AlignCenter, "u")
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.end()


def variant_l(pm):  # white rim: legible on light AND dark trays
    s = pm.width()
    p = QPainter(pm)
    for r, cx, tip, brush in ((12.3, 16.0, 31.5, QColor("white")), (10.5, 16.0, 30.0, PURPLE)):
        paint_drop(p, s, cx / 32 * s, 13.5 / 32 * s, 1 / 32 * s, tip / 32 * s, r / 32 * s, brush)
    u_glyph(p, s, QColor("white"), s / 2, s / 2)
    p.end()


def variant_n(pm):  # tilted drop, upright u — a bit of motion
    s = pm.width()
    tmp = QPixmap(s, s)
    tmp.fill(Qt.transparent)
    t = QPainter(tmp)
    t.setRenderHint(QPainter.Antialiasing)
    paint_drop(t, s, 16 / 32 * s, 13.5 / 32 * s, 2 / 32 * s, 30 / 32 * s, 10.5 / 32 * s, PURPLE)
    t.end()
    p = QPainter(pm)
    p.translate(s / 2, s / 2)
    p.rotate(-14)
    p.drawPixmap(-s / 2, -s / 2, tmp)
    p.resetTransform()
    u_glyph(p, s, QColor("white"), s / 2, s / 2)
    p.end()


VARIANTS = {"A": ("classic drop", variant_a), "B": ("badge square", variant_b),
            "C": ("gradient drop", variant_c), "D": ("outline drop", variant_d),
            "E": ("circle badge", variant_e),
            "F": ("glossy drop", variant_f), "G": ("two-tone tip", variant_g),
            "I": ("u drips to tip", variant_i), "J": ("punched-out u", variant_j),
            "L": ("white rim", variant_l), "N": ("tilted drop", variant_n)}


def main():
    keys = sys.argv[1] if len(sys.argv) > 1 else "ABCDE"
    out = sys.argv[2] if len(sys.argv) > 2 else "icons_contact.png"
    sel = {k: VARIANTS[k] for k in keys}
    os.makedirs(OUT, exist_ok=True)
    app = QApplication([])
    cell = 128
    sheet = QPixmap(cell * len(sel), int(cell * 1.35))
    sheet.fill(QColor("#eceef0"))
    p = QPainter(sheet)
    p.setRenderHint(QPainter.Antialiasing)
    for i, (k, (name, fn)) in enumerate(sel.items()):
        for size in (32, 128):
            icon = QPixmap(size, size)
            icon.fill(Qt.transparent)
            p2 = QPainter(icon)
            p2.setRenderHint(QPainter.Antialiasing)
            p2.end()
            fn(icon)
            icon.save(os.path.join(OUT, f"variant_{k}_{size}.png"))
            if size == 128:
                x = i * cell
                p.drawPixmap(x + int(cell * 0.12), int(cell * 0.08), icon)
                p.setPen(QColor("#333"))
                p.setFont(QFont("sans", 12, QFont.Bold))
                p.drawText(x, cell + 4, cell, 30, Qt.AlignCenter, f"{k} {name}")
                p.fillRect(x + int(cell * 0.28), cell + 38, int(cell * 0.44), 40, QColor("#1d1f24"))
                p.drawPixmap(x + int(cell * 0.42), cell + 42, icon.scaled(32, 32))
    p.end()
    sheet.save(os.path.join(HERE, out))
    print("wrote", os.path.join(HERE, out))


if __name__ == "__main__":
    main()
