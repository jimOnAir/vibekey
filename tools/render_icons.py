#!/usr/bin/env python3
"""tools/render_icons.py — render the hicolor icon set + SVG from the canonical
draw_app_icon() (spec §9; art decided in ticket 5 on prototype/panel-picker).

Run once at development time:  QT_QPA_PLATFORM=offscreen python3 tools/render_icons.py
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(HERE, "panel"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from panel import draw_app_icon  # noqa: E402

SIZES = [16, 22, 24, 32, 48, 64, 128, 256]
OUT = os.path.join(HERE, "panel", "icons")

SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs>
    <radialGradient id="g" cx="0.36" cy="0.30" r="0.95" fx="0.36" fy="0.30">
      <stop offset="0" stop-color="#9d7bf7"/>
      <stop offset="0.55" stop-color="#7c3aed"/>
      <stop offset="1" stop-color="#5f27c9"/>
    </radialGradient>
  </defs>
  <circle cx="64" cy="64" r="57" fill="url(#g)" stroke="#4c1ea6" stroke-width="5"/>
  <ellipse cx="64" cy="34" rx="42" ry="22" fill="#ffffff" opacity="0.26"/>
  <text x="64" y="64" text-anchor="middle" dominant-baseline="central"
        font-family="sans-serif" font-weight="bold" font-size="56" fill="#ffffff">U</text>
</svg>
"""


def main():
    app = QApplication.instance() or QApplication([])
    for size in SIZES:
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        draw_app_icon(pm)
        d = os.path.join(OUT, "%dx%d" % (size, size))
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "vibekey.png")
        assert pm.save(path, "PNG"), path
        print("wrote", path)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "vibekey.svg"), "w", encoding="utf-8") as handle:
        handle.write(SVG)
    print("wrote", os.path.join(OUT, "vibekey.svg"))


if __name__ == "__main__":
    main()
