#!/usr/bin/env python3
# PROTOTYPE: offscreen grab of the redrawn keypad (line-art icons check).
#   QT_QPA_PLATFORM=offscreen python3 preview_keypad.py
from PySide6.QtWidgets import QApplication

from prototype_panel_picker import KeypadWidget, Model

app = QApplication([])
w = KeypadWidget(Model(), lambda k, t: None)
w.grab().save("keypad_preview.png")
print("wrote keypad_preview.png")
