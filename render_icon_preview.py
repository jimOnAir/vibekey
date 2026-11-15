#!/usr/bin/env python3
# PROTOTYPE: preview the chosen icon (glossy circle + U) at sheet sizes.
#   QT_QPA_PLATFORM=offscreen python3 render_icon_preview.py
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from prototype_panel_picker import draw_app_icon

app = QApplication([])
cell = 160
sheet = QPixmap(cell * 3, int(cell * 1.9))
sheet.fill(QColor("#eceef0"))
p = QPainter(sheet)
x = 0
for label, bg in (("128 px", None), ("64 px", None), ("tray 32 px", "#1d1f24")):
    size = 128 if label.startswith("128") else (64 if label.startswith("64") else 32)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    draw_app_icon(pm)
    if bg:
        p.fillRect(x + int(cell * 0.18), int(cell * 1.06), int(cell * 0.64), 52, QColor(bg))
        p.drawPixmap(x + int(cell * 0.40), int(cell * 1.12), pm)
    else:
        p.drawPixmap(int(x + cell * 0.11), int(cell * 0.06), pm)
    p.setPen(QColor("#333"))
    p.setFont(QFont("sans", 13, QFont.Bold))
    p.drawText(x, int(cell * 1.0), cell, 28, Qt.AlignCenter, label)
    x += cell
p.end()
sheet.save("icon_glossy_circle.png")
print("wrote icon_glossy_circle.png")
sys.exit(0)
