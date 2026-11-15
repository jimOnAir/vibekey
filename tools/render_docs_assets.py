#!/usr/bin/env python3
"""tools/render_docs_assets.py — generate docs/images/*.png from the real UI.

Reproducible beauty: the Panel screenshot and the tray-icon grid are rendered
from the shipped widgets/art, not mockups. Run after UI changes:

    QT_QPA_PLATFORM=offscreen python3 tools/render_docs_assets.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(HERE, "panel"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DOCS_IMG = os.path.join(HERE, "docs", "images")

from PySide6.QtCore import Qt, QPointF, QRectF, QSize  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QPalette, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import panel as vkpanel  # noqa: E402


def dark_fusion(app):
    app.setStyle("Fusion")
    pal = QPalette()
    win, base, text = QColor("#31363b"), QColor("#232629"), QColor("#eff0f1")
    pal.setColor(QPalette.Window, win)
    pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, base)
    pal.setColor(QPalette.AlternateBase, win)
    pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, QColor("#4d5358"))
    pal.setColor(QPalette.ButtonText, text)
    pal.setColor(QPalette.ToolTipBase, win)
    pal.setColor(QPalette.ToolTipText, text)
    pal.setColor(QPalette.Highlight, QColor("#7c3aed"))
    pal.setColor(QPalette.HighlightedText, Qt.white)
    pal.setColor(QPalette.Link, QColor("#9d7bf7"))
    pal.setColor(QPalette.PlaceholderText, QColor("#969da3"))
    app.setPalette(pal)


def demo_state(tmp):
    """A plausible live state so the screenshot tells the whole story."""
    state = {
        "version": 1, "pid": 4242, "connected": True, "access": "ok",
        "grabbed": True, "mouse_passthrough": False, "preview": True,
        "knob_position": 12, "knob_mode": {"id": "sessions", "label": "Sessions"},
        "device": {"name": "Ulanzi Vibekey", "inputs": ["AU05 Consumer", "AU05 Mouse", "AU05 Keyboard"],
                   "vendor_channel": True},
        "battery": {"percent": 87, "charging": False, "voltage_mv": 4010, "at": 0},
        "events": 128, "error": "", "updated": "x1",
        "keypad": {"online": True, "at": 0, "via": "query"},
        "power": {"standby_s": 300, "sleep_s": 3600,
                  "enc": {"level": 1, "low": 1600, "high": 1000}, "at": 0},
        "attention": None,
        "lighting": {"device_mode": 2, "last_error": "",
                     "channels": [[0, 10, 2, 7, 2], [0, 10, 2, 7, 2], [0, 10, 2, 7, 2], [1, 10, 2, 7, 8]]},
        "last": {"id": "kbd:0x28", "slot": "key2", "label": "Confirm key", "at": "t1",
                 "action": "session ses_e1fbb97f (wmctrl)", "preview": False},
    }
    config = {
        "grab": True, "battery": True, "aliases": {},
        "knob_modes": ["scroll", "sessions", "volume"],
        "buttons": {
            "key1": {"preset": "dictation_ptt", "label": "Dictation (hold, handy)",
                     "behavior": "dictation.ptt", "keys": "ctrl+alt+space"},
            "key2": {"preset": "key_enter", "label": "Press Enter", "keys": "Return"},
            "key3": {"preset": "session_interrupt", "label": "Interrupt",
                     "behavior": "session.interrupt"},
        },
        "lighting": {"mode_ring": True, "fail_blink": True, "low_battery": True, "brightness": 1.0,
                     "patterns": {"Scroll": "off", "Sessions": "heartbeat:8", "Volume": "breathe:8"}},
    }
    handy = {"settings": {"keyboard_implementation": "tauri", "shortcut_activation": "push_to_talk",
                          "always_on_microphone": True, "overlay_style": "none",
                          "bindings": {"transcribe": {"current_binding": "ctrl+alt+space"}}}}
    with open(vkpanel.STATE_PATH, "w") as h:
        json.dump(state, h)
    with open(vkpanel.CONFIG_PATH, "w") as h:
        json.dump(config, h)
    os.makedirs(os.path.dirname(vkpanel.HANDY_STORES[0]), exist_ok=True)
    with open(vkpanel.HANDY_STORES[0], "w") as h:
        json.dump(handy, h)
    # the screenshot shows a healthy box: a real input device present (the
    # sandbox has no PipeWire socket, so stub the probe deterministically)
    vkpanel.mic_status = lambda ttl=5.0: ("ok", "alsa_input.usb-AU05_AU05_202606031150-00.analog-stereo")


def render_panel(app):
    tray = type("T", (), {"update_icon": lambda s, st: None})()
    win = vkpanel.PanelWindow(tray=tray)
    win.resize(900, 520)
    win.status_line.setText("Confirm key → session ses_e1fbb97f (wmctrl)   [RAN: key2]")
    win.autostart_cb.setChecked(True)
    win.enable_btn.hide()          # the screenshot shows a settled, installed system
    win.show()
    app.processEvents()
    for _ in range(5):
        app.processEvents()
    pm = win.grab()
    pm.save(os.path.join(DOCS_IMG, "panel.png"))
    win.deleteLater()
    print("wrote docs/images/panel.png")


def render_tray_grid(app):
    labels = ["Scroll", "Sessions", "Volume", "custom mode", "attention", "no microphone"]
    modes = [("scroll", "Scroll"), ("sessions", "Sessions"), ("volume", "Volume"),
             (None, "Монитор"), ("sessions", "Sessions"), ("sessions", "Sessions")]
    warns = [False, False, False, False, True, False]
    mics = [False, False, False, False, False, True]
    cell = 44
    img = QImage(len(labels) * cell, cell + 2, QImage.Format_RGB32)
    img.fill(QColor("#232629"))
    p = QPainter(img)
    for i, ((mid, mlabel), warn, mic) in enumerate(zip(modes, warns, mics)):
        pm = vkpanel.app_icon_pixmap(32, warn=warn, mode_id=mid, mode_label=mlabel, mic_off=mic)
        p.drawImage(QRectF(i * cell + 6, 4, 32, 32),
                    pm.toImage().scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    p.end()
    img.save(os.path.join(DOCS_IMG, "tray-modes.png"))
    print("wrote docs/images/tray-modes.png")


def render_glyphs(app):
    """The cap line-art on a dark card — README material."""
    pm = QPixmap(4 * 64, 64)
    pm.fill(QColor("#232629"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    for i, fn in enumerate((vkpanel.draw_mic, vkpanel.draw_check, vkpanel.draw_cross,
                            vkpanel.draw_turn(True))):
        fn(p, 64, "#cdd3d8")
        p.translate(64, 0)
    p.end()
    pm.save(os.path.join(DOCS_IMG, "caps.png"))
    print("wrote docs/images/caps.png")


def main():
    os.makedirs(DOCS_IMG, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="vibekey-docs-")
    os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, "config")
    os.environ["XDG_RUNTIME_DIR"] = os.path.join(tmp, "run")
    os.environ["XDG_DATA_HOME"] = os.path.join(tmp, "data")
    os.makedirs(os.environ["XDG_CONFIG_HOME"] + "/vibekey", exist_ok=True)
    os.makedirs(os.environ["XDG_RUNTIME_DIR"] + "/vibekey", exist_ok=True)
    # recompute module paths for the scratch world
    import importlib
    importlib.reload(vkpanel)
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("vibekey-docs")
    dark_fusion(app)
    demo_state(tmp)
    render_panel(app)
    render_tray_grid(app)
    render_glyphs(app)


if __name__ == "__main__":
    main()
