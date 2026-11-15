#!/usr/bin/env python3
"""vibekey-panel: the PySide6 tray Panel (spec §8 — Variant A "drawn device").

Visual source of truth: prototype/panel-picker @ 3c26e5e (ticket 5) — the
device art, hit zones, line icons, header strip and status-line language are
ported, not redesigned. The Panel talks to the Daemon only through the file
protocol (spec §3): reads state.json, heartbeats `preview`, edits config.json
exclusively by invoking vibekey-config, and sends a consented Manage lights
request by dropping the one-shot manage_lights file.
"""

import json
import os
import subprocess
import sys
import time

from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer, QPointF, QRectF, QSize
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QPlainTextEdit, QPushButton, QSlider,
    QStatusBar, QSystemTrayIcon, QVBoxLayout, QWidget,
)

# ---------------------------------------------------------------------------
# paths (spec §9 layout works both installed and from the repo checkout)
# ---------------------------------------------------------------------------

CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "vibekey")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
STATE_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "vibekey", "state.json")
MANAGE_LIGHTS_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "vibekey", "manage_lights")
PREVIEW_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "vibekey", "preview")
AUTOSTART_FILE = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                              "autostart", "vibekey-panel.desktop")
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))   # /usr/lib/vibekey | repo root
ACTIONS_PATH = os.path.join(PACKAGE_DIR, "actions.json")
VIBEKEY_CONFIG = os.path.join(PACKAGE_DIR, "bin", "vibekey-config")
HANDY_STORES = [
    # verified against the installed handy 0.10.0 on this box (2026-11-15):
    # tauri-plugin-store lives in the DATA dir, not the config dir.
    os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
                 "com.pais.handy", "settings_store.json"),
    os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                 "com.pais.handy", "settings_store.json"),
]
HANDY_STORE = HANDY_STORES[0]


def handy_store_path():
    for path in HANDY_STORES:
        if os.path.exists(path):
            return path
    return HANDY_STORE

LONG_MS = 400
ENTRY_FIELDS = ("behavior", "dir", "command", "keys", "release_command", "release_keys", "scroll")

# zone key -> (slot, caption) mirroring the physical device (spec §8)
ZONES = [
    ("knob", None, "Knob — press: cycle Knob mode · hold ≥400 ms: Enter (fixed)"),
    ("voice", "key1", "Voice key"),
    ("confirm", "key2", "✓ Confirm"),
    ("cancel", "key3", "✕ Cancel"),
]
CAPTIONS = {zone: caption for zone, _slot, caption in ZONES}
SLOT_OF = {zone: slot for zone, slot, _caption in ZONES}
EDITABLE_SLOTS = [("key1", "Voice key"), ("key2", "✓ Confirm"), ("key3", "✕ Cancel")]

MODE_LABELS = {"scroll": "Scroll", "sessions": "Sessions", "volume": "Volume"}


def read_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data
    except (OSError, ValueError):
        return fallback


def run_vibekey_config(*args):
    try:
        proc = subprocess.run([VIBEKEY_CONFIG] + list(args), capture_output=True, timeout=5.0, check=False)
        if proc.returncode != 0:
            return False, proc.stderr.decode("utf-8", errors="replace").strip()
        return True, proc.stdout.decode("utf-8", errors="replace")
    except OSError as error:
        return False, str(error)


# ---------------------------------------------------------------------------
# audio input probe — Panel-side only, the Daemon never touches audio (spec §3)
# ---------------------------------------------------------------------------

def parse_source_states(text):
    """{source_name: muted} parsed from `pactl list sources` blocks (Name:/Mute:
    lines per block). Sink monitors appear here too — filter with `.monitor`."""
    states, name = {}, None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Name:"):
            name = s.split(":", 1)[1].strip()
        elif s.startswith("Mute:") and name:
            states[name] = s.split(":", 1)[1].strip() == "yes"
    return states


def mic_verdict(states, default):
    """('ok'|'missing'|'muted', detail) from source states + the default source."""
    inputs = [n for n in states if not n.endswith(".monitor")]
    if not inputs:
        return "missing", ""
    if states.get(default, False) or all(states[n] for n in inputs):
        return "muted", default or inputs[0]
    return "ok", default or inputs[0]


_MIC_CACHE = [0.0, "unknown", ""]   # (checked_at, state, detail)


def mic_status(ttl=5.0):
    """('ok'|'missing'|'muted'|'unknown', detail) — is a usable microphone
    there? Panel-side only, the Daemon never touches audio (spec §3). Cached so
    the Panel poll and the tray timer share one probe. A hardware mic switch or
    an unplugged 3.5 mm plug is invisible to PipeWire on this audio hardware
    (no jack detection) — software mute and total absence are not, and warn.
    'unknown' (no pactl, dead server) never warns."""
    now = time.monotonic()
    if now - _MIC_CACHE[0] >= ttl:
        state, detail = "unknown", ""
        try:
            proc = subprocess.run(["pactl", "list", "sources"],
                                  capture_output=True, text=True, timeout=2.0, check=False)
            if proc.returncode == 0:
                states = parse_source_states(proc.stdout)
                default = ""
                try:   # older pactl lacks get-default-source; pactl info has it too
                    dproc = subprocess.run(["pactl", "get-default-source"],
                                           capture_output=True, text=True, timeout=2.0, check=False)
                    default = dproc.stdout.strip()
                    if dproc.returncode != 0 or not default:
                        iproc = subprocess.run(["pactl", "info"], capture_output=True,
                                               text=True, timeout=2.0, check=False)
                        for line in iproc.stdout.splitlines():
                            if line.startswith("Default Source:"):
                                default = line.split(":", 1)[1].strip()
                except (OSError, subprocess.TimeoutExpired):
                    pass
                state, detail = mic_verdict(states, default)
        except (OSError, subprocess.TimeoutExpired):
            pass
        _MIC_CACHE[0], _MIC_CACHE[1], _MIC_CACHE[2] = now, state, detail
    return _MIC_CACHE[1], _MIC_CACHE[2]


# ---------------------------------------------------------------------------
# Prototype art, ported verbatim from prototype_panel_picker.py (ticket 5)
# ---------------------------------------------------------------------------

INK = "#55585e"  # engraved-cap graphite, matches the drawn caps


def _pen(color, w):
    return QPen(QColor(color), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _arcs(p, s, color, r=10.4, rot=0.0):
    """the AU05 cap motif: two open arcs (split circle); rot turns the gap."""
    import math
    k = s / 28.0
    p.setPen(_pen(color, 2.2 * k))
    p.setBrush(Qt.NoBrush)
    cx = cy = 14 * k
    rr = r * k
    for a0, a1 in ((112.0 + rot, 248.0 + rot), (68.0 + rot, -68.0 + rot)):
        prev = None
        steps = 14
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            pt = QPointF(cx + rr * math.cos(a), cy - rr * math.sin(a))
            if prev is not None:
                p.drawLine(prev, pt)
            prev = pt


def draw_mic(p, s, color):
    """mic cap: wide capsule, shallow smile-yoke, short tail; no foot."""
    k = s / 28.0
    p.setPen(_pen(color, 1.9 * k)); p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(11.0 * k, 4.7 * k, 6.0 * k, 11.0 * k, 3.0 * k, 3.0 * k)
    path = QPainterPath(); path.moveTo(9.5 * k, 13.7 * k)
    path.cubicTo(9.5 * k, 20.0 * k, 18.5 * k, 20.0 * k, 18.5 * k, 13.7 * k)
    p.drawPath(path)
    p.drawLine(QPointF(14 * k, 18.5 * k), QPointF(14 * k, 21.2 * k))


def draw_check(p, s, color):
    """accept cap: V-check between the two arcs, long arm through the gap."""
    k = s / 28.0
    _arcs(p, s, color, rot=-45.0)
    p.setPen(_pen(color, 2.6 * k)); p.setBrush(Qt.NoBrush)
    path = QPainterPath(QPointF(10.6 * k, 14.2 * k))
    path.lineTo(13.2 * k, 17.0 * k); path.lineTo(17.8 * k, 10.6 * k)
    p.drawPath(path)


def draw_cross(p, s, color):
    """cancel cap: cross between the two arcs, gap on the diagonal."""
    k = s / 28.0
    _arcs(p, s, color, rot=-45.0)
    p.setPen(_pen(color, 2.2 * k))
    p.drawLine(QPointF(11.6 * k, 11.6 * k), QPointF(16.4 * k, 16.4 * k))
    p.drawLine(QPointF(16.4 * k, 11.6 * k), QPointF(11.6 * k, 16.4 * k))


def draw_turn(cw):
    def fn(p, s, color):
        import math
        k = s / 28.0
        cx = cy = 14 * k; r = 8.0 * k
        a0 = 60.0 if cw else 120.0
        span = -300.0 if cw else 300.0
        pts = []
        steps = 30
        for i in range(steps + 1):
            a = math.radians(a0 + span * i / steps)
            pts.append(QPointF(cx + r * math.cos(a), cy - r * math.sin(a)))
        p.setPen(_pen(color, 3.0 * k))
        for i in range(steps):
            p.drawLine(pts[i], pts[i + 1])
        last, prev = pts[-1], pts[-2]
        dx, dy = last.x() - prev.x(), last.y() - prev.y()
        L = math.hypot(dx, dy) or 1.0
        dx, dy = dx / L, dy / L
        px, py = -dy, dx
        h, w = 7.5 * k, 4.6 * k
        p.setPen(Qt.NoPen); p.setBrush(QColor(color))
        p.drawPolygon([QPointF(last.x() + dx * h, last.y() + dy * h),
                       QPointF(last.x() + px * w, last.y() + py * w),
                       QPointF(last.x() - px * w, last.y() - py * w)])
    return fn


def line_icon(fn, px=28):
    """QIcon with normal (graphite) + active (white) pixmaps. Render at the
    exact px — a stylesheet'd QPushButton ignores setIconSize (ticket 5 gotcha)."""
    normal = QPixmap(px, px); normal.fill(Qt.transparent)
    p = QPainter(normal); p.setRenderHint(QPainter.Antialiasing); fn(p, px, INK); p.end()
    active = QPixmap(px, px); active.fill(Qt.transparent)
    p = QPainter(active); p.setRenderHint(QPainter.Antialiasing); fn(p, px, "#ffffff"); p.end()
    ic = QIcon()
    ic.addPixmap(normal, QIcon.Normal)
    ic.addPixmap(active, QIcon.Active)
    return ic


def draw_app_icon(pm):
    """The chosen icon: glossy purple circle with a white centered 'U'."""
    s = pm.width()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QRadialGradient(s * 0.36, s * 0.30, s * 0.95, s * 0.36, s * 0.30)
    g.setColorAt(0.0, QColor("#9d7bf7"))
    g.setColorAt(0.55, QColor("#7c3aed"))
    g.setColorAt(1.0, QColor("#5f27c9"))
    p.setPen(QPen(QColor("#4c1ea6"), max(1.0, s * 0.04)))
    p.setBrush(g)
    p.drawEllipse(s * 0.055, s * 0.055, s * 0.89, s * 0.89)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 66))
    p.drawEllipse(QRectF(s * 0.17, s * 0.11, s * 0.66, s * 0.34))
    p.setPen(QColor("white"))
    p.setFont(QFont("sans", int(s * 0.44), QFont.Bold))
    p.drawText(QRectF(0, -s * 0.03, s, s), Qt.AlignCenter, "U")
    p.end()


def _disc_badge(p, size, glyph):
    """Dark corner disc (bottom-left) carrying the Knob-mode glyph; the
    warning dot lives opposite (top-right) so the two never collide."""
    d = size * 0.52
    x, y = size * 0.02, size * 0.46
    p.setPen(QPen(QColor("#ffffff"), max(1.0, size * 0.045)))
    p.setBrush(QColor("#2c2e33"))
    p.drawEllipse(QRectF(x, y, d, d))
    glyph(p, QRectF(x, y, d, d))


def _glyph_scroll(p, r):
    cx, half = r.center().x(), r.width() * 0.16
    p.setPen(_pen("#ffffff", max(1.0, r.width() * 0.11)))
    y = r.top() + r.height() * 0.32
    p.drawLine(QPointF(cx - half, y + half * 0.8), QPointF(cx, y))
    p.drawLine(QPointF(cx, y), QPointF(cx + half, y + half * 0.8))
    y2 = r.bottom() - r.height() * 0.32
    p.drawLine(QPointF(cx - half, y2 - half * 0.8), QPointF(cx, y2))
    p.drawLine(QPointF(cx, y2), QPointF(cx + half, y2 - half * 0.8))


def _glyph_sessions(p, r):
    p.setPen(_pen("#ffffff", max(1.0, r.width() * 0.09)))
    p.setBrush(Qt.NoBrush)
    rect = QRectF(r.left() + r.width() * 0.18, r.top() + r.height() * 0.22,
                  r.width() * 0.64, r.height() * 0.56)
    p.drawRoundedRect(rect, 1.5, 1.5)
    y = rect.top() + rect.height() * 0.30
    p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))


def _glyph_volume(p, r):
    cx, cy = r.center().x(), r.center().y()
    k = r.width()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#ffffff"))
    path = QPainterPath(QPointF(cx - k * 0.16, cy - k * 0.07))
    path.lineTo(cx - k * 0.04, cy - k * 0.07); path.lineTo(cx + k * 0.09, cy - k * 0.19)
    path.lineTo(cx + k * 0.09, cy + k * 0.19); path.lineTo(cx - k * 0.04, cy + k * 0.07)
    path.lineTo(cx - k * 0.16, cy + k * 0.07); path.closeSubpath()
    p.drawPath(path)
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen("#ffffff", max(1.0, k * 0.07)))
    p.drawArc(QRectF(cx + k * 0.02, cy - k * 0.16, k * 0.26, k * 0.32), -60 * 16, 120 * 16)


def _glyph_letter(letter):
    def fn(p, r):
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("sans", int(r.width() * 0.52), QFont.Bold))
        p.drawText(r, Qt.AlignCenter, letter.upper())
    return fn


MODE_GLYPHS = {"scroll": _glyph_scroll, "sessions": _glyph_sessions, "volume": _glyph_volume}


def _glyph_mic_off(p, r):
    """mini mic struck through — microphone not connected (tray warning badge)."""
    p.save()
    p.translate(r.topLeft())
    s = r.width()
    draw_mic(p, s, "#2c2e33")
    p.setPen(_pen("#2c2e33", max(1.0, s * 0.09)))
    p.drawLine(QPointF(s * 0.28, s * 0.74), QPointF(s * 0.74, s * 0.26))
    p.restore()


def app_icon_pixmap(size=32, warn=False, mode_id=None, mode_label=None, mic_off=False):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    draw_app_icon(pm)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    glyph = MODE_GLYPHS.get(mode_id)
    if glyph is None and mode_label:
        glyph = _glyph_letter(mode_label.strip()[:1] or "?")
    if glyph is not None:
        _disc_badge(p, size, glyph)
    p.end()
    if mic_off:  # top-left; the mode disc and the "!" own the bottom corners
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        d = size * 0.42
        p.setPen(QPen(QColor("#ffffff"), max(1, size // 16)))
        p.setBrush(QColor("#e8912d"))
        p.drawEllipse(QRectF(1, 1, d, d))
        _glyph_mic_off(p, QRectF(1 + d * 0.18, 1 + d * 0.18, d * 0.64, d * 0.64))
        p.end()
    if warn:  # tray state conveys Daemon failure states (spec §8)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#ffffff"), max(1, size // 16)))
        p.setBrush(QColor("#e8912d"))
        d = size * 0.42
        p.drawEllipse(QRectF(size - d - 1, size - d - 1, d, d))
        p.setPen(QPen(QColor("#ffffff"), max(1, size // 16)))
        p.setFont(QFont("sans", int(size * 0.22), QFont.Bold))
        p.drawText(QRectF(size - d - 1, size - d - 3, d, d), Qt.AlignCenter, "!")
        p.end()
    return pm


class ZoneButton(QPushButton):
    """Transparent hit zone: single click simulates, double-click edits
    (prototype SimButton pattern — PySide6 QPushButton has no doubleClicked)."""

    def __init__(self, click_cb, edit_cb=None, parent=None):
        super().__init__("", parent)
        self.setFlat(True)
        self._edit_cb = edit_cb
        self.clicked.connect(lambda: click_cb())

    def mouseDoubleClickEvent(self, e):
        if self._edit_cb:
            self._edit_cb()
        else:
            super().mouseDoubleClickEvent(e)


class KeypadWidget(QFrame):
    """The drawn AU05 with transparent hit zones (prototype Variant A, verbatim
    art; zone clicks are always local simulation — spec §10 item 7)."""

    W, H = 470, 150

    def __init__(self, click_cb, edit_cb):
        super().__init__()
        self.setFixedSize(self.W, self.H)
        spec = [  # (zone, line-icon fn, cx, cy, r)
            ("knob", None, 170, 75, 36),
            ("voice", draw_mic, 260, 75, 24),
            ("confirm", draw_check, 320, 75, 24),
            ("cancel", draw_cross, 380, 75, 24),
        ]
        for zone, fn, cx, cy, r in spec:
            b = ZoneButton(lambda z=zone: click_cb(z),
                           None if zone == "knob" else (lambda z=zone: edit_cb(z)), self)
            b.setStyleSheet(
                "QPushButton{background:transparent;border:none}"
                "QPushButton:pressed{background:rgba(61,132,246,150);border-radius:%dpx}" % r)
            if fn:
                px = int(r * 1.1667)
                b.setIcon(line_icon(fn, px))
                b.setIconSize(QSize(px, px))
            b.setGeometry(cx - r, cy - r, 2 * r, 2 * r)
            b.setToolTip(CAPTIONS.get(zone, zone))
        for zone, dx in (("knob_left", -1), ("knob_right", 1)):
            b = ZoneButton(lambda z=zone: click_cb(z), None, self)
            b.setStyleSheet("QPushButton{background:transparent;border:none}"
                            "QPushButton:pressed{background:rgba(61,132,246,70);border-radius:10px}")
            b.setIcon(line_icon(draw_turn(dx > 0), 22))
            b.setIconSize(QSize(22, 22))
            b.setGeometry(170 + dx * 54 - 13, 75 - 50, 26, 26)
            b.setToolTip("knob turn " + ("◀" if dx < 0 else "▶") + " (current Knob mode)")

    def paintEvent(self, e):
        import math
        from PySide6.QtGui import QLinearGradient
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.H)
        g.setColorAt(0, QColor("#e9eaec")); g.setColorAt(0.5, QColor("#d8dadc")); g.setColorAt(1, QColor("#c6c8cc"))
        p.setPen(QColor("#b3b5b9")); p.setBrush(g)
        p.drawRoundedRect(6, 6, self.W - 12, self.H - 12, 24, 24)
        # far-end column: speaker mesh, Ulanzi logo, mic slots
        p.setPen(Qt.NoPen); p.setBrush(QColor("#8f9297"))
        for col in range(3):
            for row in range(9):
                p.drawEllipse(12 + col * 4.5, 22 + row * 12, 2.4, 2.4)
        p.setPen(QColor("#7c7f85")); p.setFont(QFont("sans", 7))
        p.drawText(26, 55, 40, 40, Qt.AlignCenter, "Ulanzi")
        p.setPen(Qt.NoPen); p.setBrush(QColor("#9c9ea3"))
        for i in range(5):
            p.drawRoundedRect(72 + i * 7, 66, 3, 18, 1.5, 1.5)
        # knob: recessed ring groove + aluminium dome + grip marks every 90°
        p.setPen(QPen(QColor("#a4a6aa"), 2)); p.setBrush(QColor("#caced3"))
        p.drawEllipse(170 - 46, 75 - 46, 92, 92)
        kg = QRadialGradient(158, 63, 66, 158, 63)
        kg.setColorAt(0, QColor("#ffffff")); kg.setColorAt(0.6, QColor("#e2e4e7")); kg.setColorAt(1, QColor("#c3c6ca"))
        p.setPen(QColor("#aeb0b4")); p.setBrush(kg)
        p.drawEllipse(170 - 40, 75 - 40, 80, 80)
        p.setPen(QPen(QColor("#8f9297"), 1.8))
        for ang in (0, 90, 180, 270):
            x1, y1 = 170 + 32 * math.cos(math.radians(ang)), 75 - 32 * math.sin(math.radians(ang))
            x2, y2 = 170 + 38 * math.cos(math.radians(ang)), 75 - 38 * math.sin(math.radians(ang))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        # square plates with white caps (close-up photos: no 4th key exists)
        for cx in (260, 320, 380):
            p.setPen(QColor("#c3c5c9")); p.setBrush(QColor("#d6d8db"))
            p.drawRoundedRect(cx - 28, 75 - 28, 56, 56, 12, 12)
            p.setPen(QColor("#c0c2c6")); p.setBrush(QColor("#fafafa"))
            p.drawEllipse(cx - 23, 75 - 23, 46, 46)
        # strap hole at the far (right) edge
        p.setPen(QPen(QColor("#9c9ea3"), 1.5)); p.setBrush(QColor("#b9bcc0"))
        p.drawRoundedRect(self.W - 18, 75 - 6, 8, 12, 4, 4)
        p.end()


# ---------------------------------------------------------------------------
# Picker — grouped tiles from the shipped catalogue + custom fields (spec §8)
# ---------------------------------------------------------------------------

class PickerDialog(QDialog):
    def __init__(self, slot_label, current, catalogue, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick an Assignment — %s" % slot_label)
        self.chosen = None          # a config-entry dict, or None
        lay = QVBoxLayout(self)
        groups = {}
        for preset in catalogue.get("presets") or []:
            if isinstance(preset, dict) and preset.get("id"):
                groups.setdefault(preset.get("group") or "Other", []).append(preset)
        for group, presets in groups.items():
            lay.addWidget(QLabel("<b>%s</b>" % group))
            grid = QGridLayout()
            for i, preset in enumerate(presets):
                b = QPushButton(preset.get("label") or preset["id"])
                if preset.get("description"):
                    b.setToolTip(preset["description"])
                b.clicked.connect(lambda _, pr=preset: self.pick_preset(pr))
                grid.addWidget(b, i // 3, i % 3)
            lay.addLayout(grid)
        for placeholder, kind in (("custom command (bash -c)…", "command"),
                                  ("key combo, e.g. ctrl+shift+t (xdotool)…", "keys")):
            row = QHBoxLayout()
            e = QLineEdit(); e.setPlaceholderText(placeholder)
            b = QPushButton("Use")
            b.clicked.connect(lambda _, k=kind, le=e: self.pick_custom(k, le.text()))
            row.addWidget(e); row.addWidget(b)
            lay.addLayout(row)
        row = QHBoxLayout()
        clear = QPushButton("Clear this Assignment")
        clear.clicked.connect(self.pick_clear)
        row.addWidget(clear)
        lay.addLayout(row)
        if current:
            lay.addWidget(QLabel("<i>current: %s</i>" % json.dumps(current, ensure_ascii=False)))

    def pick_preset(self, preset):
        entry = {"preset": preset["id"], "label": str(preset.get("label") or preset["id"])}
        for field in ENTRY_FIELDS:
            value = preset.get(field)
            if isinstance(value, str) and value:
                entry[field] = value
        self.chosen = entry
        self.accept()

    def pick_custom(self, kind, text):
        text = (text or "").strip()
        if not text:
            text, ok = QInputDialog.getText(self, "Custom", "%s:" % kind)
            if not ok or not text.strip():
                return
            text = text.strip()
        self.chosen = {"label": "Custom %s" % kind, kind: text}
        self.accept()

    def pick_clear(self):
        self.chosen = {}
        self.accept()


# ---------------------------------------------------------------------------
# The Panel window
# ---------------------------------------------------------------------------

class PanelWindow(QMainWindow):
    def __init__(self, tray):
        super().__init__()
        self.tray = tray
        self.state = read_json(STATE_PATH, {}) or {}
        self.config = read_json(CONFIG_PATH, {}) or {}
        self.catalogue = read_json(ACTIONS_PATH, {}) or {}
        self.last_shown = None
        self.setWindowTitle("vibekey")
        self.resize(880, 460)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        top = QHBoxLayout()
        self.topinfo = QLabel()
        top.addWidget(self.topinfo, 1)
        self.preview_cb = QCheckBox("Preview (nothing runs)")
        self.preview_cb.setChecked(True)          # default on (spec §8)
        self.preview_cb.toggled.connect(self.preview_toggled)
        top.addWidget(self.preview_cb)
        outer.addLayout(top)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("color:#c0392b;")
        outer.addWidget(self.banner)

        body = QHBoxLayout()
        outer.addLayout(body)

        # left: the drawn device + handy card
        left = QVBoxLayout()
        body.addLayout(left)
        left.addWidget(KeypadWidget(self.zone_clicked, self.edit_assignment))
        self.assign_line = QLabel()
        self.assign_line.setWordWrap(True)
        left.addWidget(self.assign_line)
        left.addWidget(self.build_handy_card())
        left.addStretch(1)
        body.addLayout(left)

        # right: assignments overview + lighting + autostart
        right = QVBoxLayout()
        body.addLayout(right, 1)
        right.addWidget(QLabel("<b>Assignments</b> — click the drawing to simulate, double-click to edit"))
        self.rows = {}
        for slot, label in EDITABLE_SLOTS:
            row = QHBoxLayout()
            lab = QLabel(); lab.setMinimumWidth(300); lab.setWordWrap(True)
            row.addWidget(lab, 1)
            eb = QPushButton("Edit…")
            eb.clicked.connect(lambda _, s=slot, l=label: self.edit_assignment(s))
            row.addWidget(eb)
            right.addLayout(row)
            self.rows[slot] = lab
        knob_row = QHBoxLayout()
        knob_lab = QLabel("<b>Knob</b><br><span style='color:#777'>press: cycle Knob mode · "
                          "long-press: Enter (fixed)</span>")
        knob_row.addWidget(knob_lab, 1)
        right.addLayout(knob_row)

        right.addWidget(self.build_lighting_box())
        autostart_row = QHBoxLayout()
        self.autostart_cb = QCheckBox("Launch at login")
        self.autostart_cb.setChecked(os.path.exists(AUTOSTART_FILE))
        self.autostart_cb.toggled.connect(self.autostart_toggled)
        autostart_row.addWidget(self.autostart_cb)
        self.enable_btn = QPushButton("Enable vibekeyd service")
        self.enable_btn.clicked.connect(self.enable_unit)
        autostart_row.addWidget(self.enable_btn)
        autostart_row.addStretch(1)
        right.addLayout(autostart_row)
        right.addStretch(1)

        self.setStatusBar(QStatusBar())
        self.status_line = QLabel("waiting for the Daemon…")
        self.statusBar().addWidget(self.status_line, 1)

        # state.json: watcher + 1 s poll (spec §3 — the Daemon rewrites in place,
        # same inode, so the watch survives; the poll covers a replaced file)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_state)
        self.poll_timer.start(1000)
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(lambda _p: self.poll_state())
        self._watch_state()
        self.poll_state(force=True)

        # preview heartbeat while shown (spec §3)
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self.heartbeat)
        self.heartbeat_timer.start(2000)

    # ---- heartbeat / preview --------------------------------------------------

    def heartbeat(self):
        if self.isVisible() and self.preview_cb.isChecked():
            self._write(PREVIEW_PATH, "open")
        else:
            self._write(PREVIEW_PATH, "closed")

    def preview_toggled(self, _checked):
        self.heartbeat()

    @staticmethod
    def _write(path, text):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError:
            pass

    def hideEvent(self, e):
        self._write(PREVIEW_PATH, "closed")
        super().hideEvent(e)

    def closeEvent(self, e):
        self._write(PREVIEW_PATH, "closed")
        super().closeEvent(e)

    # ---- state / config polling -------------------------------------------------

    def _watch_state(self):
        try:
            if os.path.exists(STATE_PATH) and STATE_PATH not in self.watcher.files():
                self.watcher.addPath(STATE_PATH)
        except (RuntimeError, OSError):
            pass

    def poll_state(self, force=False):
        data = read_json(STATE_PATH, None)
        if isinstance(data, dict):
            changed = force or data.get("updated") != self.state.get("updated")
            self.state = data
            if changed:
                self.refresh()
        self._watch_state()

    def refresh(self):
        st = self.state
        mode = (st.get("knob_mode") or {}).get("label") or "—"
        battery = st.get("battery")
        batt = "🔋 %d%%%s" % (battery["percent"], "⚡" if battery.get("charging") else "") if battery else ""
        self.topinfo.setText("<b>Knob mode: %s</b> · turn position: %s · %s"
                             % (mode, st.get("knob_position", 0), batt))

        access = st.get("access")
        problem = st.get("error") or ""
        if access == "denied":
            problem = ("No permission to read the Dongle — run <b>gpasswd -a $USER vibekey</b> "
                       "and re-login (spec §9).")
        last_error = (st.get("lighting") or {}).get("last_error") or st.get("last_error") or ""
        self.banner.setText(problem or last_error or "")
        self.banner.setVisible(bool(problem or last_error))

        # an idle status line would say "waiting for the Daemon…" even while the
        # Daemon is alive and reporting — when it is, say what is actually missing
        if not st.get("connected"):
            self.set_status({"absent": "Daemon is up — but the Dongle is not on USB (plug it in)",
                             "denied": "Daemon is up — no permission to read the Dongle (see Troubleshooting)",
                             "unexpected": "Dongle interface layout changed — Daemon refused to grab it",
                             "stopped": "Daemon is shutting down…"}.get(access, "Daemon not connected yet"))

        config = read_json(CONFIG_PATH, {}) or {}
        if config != self.config:
            self.config = config
        buttons = config.get("buttons") or {}
        for slot, _label in EDITABLE_SLOTS:
            entry = buttons.get(slot) or {}
            shown = entry.get("label") or ("—" if not entry else "?")
            self.rows[slot].setText("<b>%s</b><br><span style='color:#777'>%s</span>"
                                    % (dict(EDITABLE_SLOTS)[slot], shown))

        # narrate the newest Daemon event (WOULD RUN vs RAN, spec §8)
        last = st.get("last")
        if last and last.get("at") != self.last_shown:
            self.last_shown = last.get("at")
            verb = "WOULD RUN" if last.get("preview") else "RAN"
            action = last.get("action") or self.assignment_for(last.get("slot"))
            self.set_status("%s → %s   [%s: %s]" % (last.get("label", "?"), action, verb, last.get("slot") or "-"))

        self.refresh_handy_card()
        self.refresh_lighting()
        if not self.unit_enabled():
            self.enable_btn.show()
        else:
            self.enable_btn.hide()
        self.tray.update_icon(self.state)

    def assignment_for(self, slot):
        return ((self.config.get("buttons") or {}).get(slot) or {}).get("label", "?")

    def set_status(self, line):
        self.status_line.setText(line)

    # ---- zone simulation ----------------------------------------------------------

    def zone_clicked(self, zone):
        caption = CAPTIONS.get(zone) or {
            "knob_left": "Knob turn ◀", "knob_right": "Knob turn ▶"}[zone]
        if zone == "knob":
            detail = "cycle Knob mode (long-press = Enter)"
        elif zone in ("knob_left", "knob_right"):
            detail = "current Knob mode's turn action"
        else:
            detail = self.assignment_for(SLOT_OF.get(zone))
        self.set_status("%s → %s   [RAN (sim)]" % (caption, detail))

    def edit_assignment(self, zone_or_slot):
        # accepts a drawing zone ("confirm") or a slot name ("key2")
        slot = SLOT_OF.get(zone_or_slot) or (zone_or_slot if zone_or_slot in dict(EDITABLE_SLOTS) else None)
        if not slot:
            return
        dlg = PickerDialog(dict(EDITABLE_SLOTS).get(slot, slot),
                           (self.config.get("buttons") or {}).get(slot), self.catalogue, self)
        if not dlg.exec():
            return
        if dlg.chosen is None:
            return
        if dlg.chosen == {}:
            ok, err = run_vibekey_config("set-button", slot, "null")
        else:
            ok, err = run_vibekey_config("set-button", slot, json.dumps(dlg.chosen, ensure_ascii=False))
        self.set_status(("assigned %s → %s" % (slot, dlg.chosen.get("label", "(cleared)")))
                        if ok else "config write failed: %s" % err)
        self.poll_config()

    def poll_config(self):
        self.config = read_json(CONFIG_PATH, {}) or {}
        self.refresh()

    # ---- handy card (read-only apart from the consented Fix handy button) ------

    def build_handy_card(self):
        box = QGroupBox("handy")
        lay = QVBoxLayout(box)
        self.handy_mic = QLabel()   # audio input line mirrors the tray mic badge
        lay.addWidget(self.handy_mic)
        self.handy_rows = {}
        for key, text in (("keyboard_implementation", "keyboard_implementation = tauri"),
                          ("shortcut_activation", "shortcut_activation = push_to_talk"),
                          ("always_on_microphone", "always_on_microphone = true"),
                          ("overlay_style", "overlay_style = none")):
            lab = QLabel(text)
            lay.addWidget(lab)
            self.handy_rows[key] = (lab, text)
        self.handy_chord = QLabel()
        self.handy_chord.setWordWrap(True)
        lay.addWidget(self.handy_chord)
        self.handy_fix = QPushButton("Fix handy")
        self.handy_fix.setToolTip("Write the Dictation chord into handy's bindings — only on click")
        self.handy_fix.clicked.connect(self.fix_handy)
        self.handy_fix.hide()
        lay.addWidget(self.handy_fix)
        snippet = QPlainTextEdit()
        snippet.setReadOnly(True)
        snippet.setFixedHeight(110)
        snippet.setPlainText(
            "handy Settings → recommended for vibekey:\n"
            "  push to talk · Parakeet TDT v3 (Q8 ≈1.3 GB, fast CPU) ·\n"
            "  Canary 180M (smaller) · whisper-* (accurate, slower) ·\n"
            "  always_on_microphone ON · overlay OFF · Typing Tool: xdotool")
        lay.addWidget(snippet)
        self.handy_box = box
        return box

    @staticmethod
    def _chord_of(bindings):
        """handy stores bindings.transcribe as an object with current_binding
        (handy settings.rs:1712) — tolerate the plain-string shape too."""
        t = (bindings or {}).get("transcribe")
        if isinstance(t, dict):
            return t.get("current_binding")
        return t if isinstance(t, str) else None

    def handy_store(self):
        """The inner settings map — verified shape (handy 0.10.0, this box):
        the store file nests everything under a top-level "settings" object."""
        data = read_json(handy_store_path(), None)
        if isinstance(data, dict):
            inner = data.get("settings")
            return inner if isinstance(inner, dict) else data
        return {}

    def refresh_handy_card(self):
        mic_state, mic_detail = mic_status()
        if mic_state == "ok":
            self.handy_mic.setText("✓ audio input: %s" % mic_detail)
        elif mic_state == "muted":
            self.handy_mic.setText("<span style='color:#c0392b'>✗ microphone is muted (%s)"
                                   " — Dictation records nothing</span>" % mic_detail)
        elif mic_state == "missing":
            self.handy_mic.setText("<span style='color:#c0392b'>✗ microphone not connected"
                                   " — Dictation will not work</span>")
        else:
            self.handy_mic.setText("· audio input: unknown (pactl unavailable)")
        store = self.handy_store()
        recommended = {"keyboard_implementation": "tauri", "shortcut_activation": "push_to_talk",
                       "always_on_microphone": True, "overlay_style": None}
        for key, (lab, text) in self.handy_rows.items():
            if not store:
                mark, tip = "·", "%s — not set (fine if it is the app default)" % text
            else:
                value = store.get(key)
                ok = (value == recommended[key] or
                      (recommended[key] is None and value in (None, "none", "")))
                mark = "✓" if ok else "✗"
                tip = "%s   %s%s" % (text, "", "" if ok else "(detected: %r)" % (value,))
            lab.setText("%s %s" % (mark, tip))
        chord = ((self.config.get("buttons") or {}).get("key1") or {}).get("keys") or "ctrl+alt+space"
        bindings = store.get("bindings") or {}
        handy_chord = self._chord_of(bindings)
        if handy_chord and handy_chord != chord:
            self.handy_chord.setText("<span style='color:#c0392b'>handy's chord is %r but the "
                                     "Dictation Preset uses %r</span>" % (handy_chord, chord))
            self.handy_fix.show()
        else:
            self.handy_chord.setText("chord: %s" % (handy_chord or chord))
            self.handy_fix.hide()

    def fix_handy(self):
        chord = ((self.config.get("buttons") or {}).get("key1") or {}).get("keys") or "ctrl+alt+space"
        path = handy_store_path()
        raw = read_json(path, None)
        if not isinstance(raw, dict):
            self.set_status("handy's settings_store.json not found — nothing to fix")
            return
        settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else raw
        bindings = settings.get("bindings") or {}
        transcribe = bindings.get("transcribe")
        if isinstance(transcribe, dict):
            transcribe["current_binding"] = chord
        else:
            transcribe = chord
        bindings["transcribe"] = transcribe
        settings["bindings"] = bindings
        if settings is not raw:
            raw["settings"] = settings
        tmp = path + ".vibekey.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(raw, handle, indent=2)
            os.replace(tmp, path)
            self.set_status("handy's transcribe chord set to %s (restart handy to apply)" % chord)
        except OSError as error:
            self.set_status("could not write handy's config: %s" % error)
        self.refresh_handy_card()

    # ---- Lighting section (spec §8/§5.5) -------------------------------------

    def build_lighting_box(self):
        box = QGroupBox("Lighting")
        lay = QVBoxLayout(box)
        self.light_checks = {}
        for key, label in (("mode_ring", "Knob-mode ring indicator"),
                           ("fail_blink", "Failure blink on the culprit keycap"),
                           ("low_battery", "Low-battery ring breathe")):
            cb = QCheckBox(label)
            cb.toggled.connect(lambda _v: self.save_lighting())
            lay.addWidget(cb)
            self.light_checks[key] = cb
        srow = QHBoxLayout()
        srow.addWidget(QLabel("Brightness"))
        self.bright = QSlider(Qt.Horizontal)
        self.bright.setRange(0, 100)
        self.bright.setValue(100)
        self.bright.valueChanged.connect(lambda _v: self.save_lighting())
        srow.addWidget(self.bright, 1)
        lay.addLayout(srow)
        self.device_mode_line = QLabel()
        self.device_mode_line.setWordWrap(True)
        lay.addWidget(self.device_mode_line)
        self.manage_btn = QPushButton("Manage lights")
        self.manage_btn.setToolTip("Set the AU05's Device lighting mode to Working so vibekeyd's "
                                   "ring and keycap lighting become visible (consented)")
        self.manage_btn.clicked.connect(self.manage_lights)
        self.manage_btn.hide()
        lay.addWidget(self.manage_btn)
        self.lighting_box = box
        return box

    def refresh_lighting(self):
        lighting = self.config.get("lighting") or {}
        for key, cb in self.light_checks.items():
            cb.blockSignals(True)
            cb.setChecked(lighting.get(key, True) is not False)
            cb.blockSignals(False)
        self.bright.blockSignals(True)
        self.bright.setValue(int(round(float(lighting.get("brightness", 1.0)) * 100)))
        self.bright.blockSignals(False)
        device_mode = (self.state.get("lighting") or {}).get("device_mode", "unknown")
        if device_mode in (0, 1):
            label = "Always Off" if device_mode == 0 else "Always On"
            self.device_mode_line.setText("Device lighting mode: %s — vibekeyd's lighting is idle." % label)
            self.device_mode_line.show()
            self.manage_btn.show()
        elif device_mode == "unknown":
            # spec §5.5: optimistic — while unknown the Panel shows no line, no button
            self.device_mode_line.hide()
            self.manage_btn.hide()
        elif device_mode == "disabled":
            self.device_mode_line.setText("Lighting off — vibekeyd sends the device no lighting traffic.")
            self.device_mode_line.show()
            self.manage_btn.hide()
        else:
            self.device_mode_line.setText("Device lighting mode: Working.")
            self.device_mode_line.show()
            self.manage_btn.hide()

    def save_lighting(self):
        merged = self.config.get("lighting") or {}
        for key, cb in self.light_checks.items():
            merged[key] = cb.isChecked()
        merged["brightness"] = self.bright.value() / 100.0
        ok, err = run_vibekey_config("set", "lighting", json.dumps(merged))
        self.set_status("lighting saved" if ok else "lighting save failed: %s" % err)
        self.poll_config()

    def manage_lights(self):
        try:
            os.makedirs(os.path.dirname(MANAGE_LIGHTS_PATH), exist_ok=True)
            with open(MANAGE_LIGHTS_PATH, "w", encoding="utf-8") as handle:
                handle.write("manage")
            self.set_status("Manage lights requested — waiting for the device to ack…")
        except OSError as error:
            self.set_status("could not request Manage lights: %s" % error)

    # ---- unit / autostart -------------------------------------------------------

    @staticmethod
    def unit_enabled():
        try:
            proc = subprocess.run(["systemctl", "--user", "is-enabled", "vibekeyd"],
                                  capture_output=True, timeout=3.0, check=False)
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return True

    def enable_unit(self):
        try:
            proc = subprocess.run(["systemctl", "--user", "enable", "--now", "vibekeyd"],
                                  capture_output=True, timeout=10.0, check=False)
            self.set_status("vibekeyd enabled" if proc.returncode == 0
                            else "enable failed: %s" % proc.stderr.decode(errors="replace"))
        except (OSError, subprocess.TimeoutExpired) as error:
            self.set_status("enable failed: %s" % error)

    def autostart_toggled(self, checked):
        entry = ("[Desktop Entry]\nType=Application\nName=vibekey Panel\nExec=vibekey-panel\n"
                 "Icon=vibekey\nTerminal=false\nX-KDE-autostart-phase=2\n")
        try:
            if checked:
                os.makedirs(os.path.dirname(AUTOSTART_FILE), exist_ok=True)
                with open(AUTOSTART_FILE, "w", encoding="utf-8") as handle:
                    handle.write(entry)
            else:
                os.unlink(AUTOSTART_FILE)
        except OSError as error:
            self.set_status("autostart change failed: %s" % error)


# ---------------------------------------------------------------------------
# Tray application
# ---------------------------------------------------------------------------

class TrayApp:
    def __init__(self, app):
        self.app = app
        self.mic = "unknown"
        app.setApplicationName("vibekey-panel")
        icon = self.build_icon(False)
        app.setWindowIcon(icon)
        self.window = PanelWindow(self)
        tray = QSystemTrayIcon(icon, app)
        menu = QMenu()
        act_show = QAction("Show/Hide vibekey Panel", menu)
        act_show.triggered.connect(self.toggle_window)
        menu.addAction(act_show)
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(app.quit)
        menu.addAction(act_quit)
        tray.setContextMenu(menu)
        tray.setToolTip("vibekey — AU05 control surface")
        tray.activated.connect(lambda reason: self.show_window() if reason == QSystemTrayIcon.Trigger else None)
        self.tray = tray
        self.update_icon(self.window.state)   # tray starts already showing the current Knob mode
        tray.show()
        # audio watcher: the tray is the always-visible surface, so it carries the
        # "no microphone" warning (owner ask 2026-11-15); pactl answers in ms
        self.mic_timer = QTimer()
        self.mic_timer.timeout.connect(self.poll_mic)
        self.mic_timer.start(5000)
        self.poll_mic()

    def poll_mic(self):
        state, _detail = mic_status()
        if state != self.mic:
            self.mic = state
            self.update_icon(self.window.state)
        if self.window.isVisible():
            self.window.refresh_handy_card()   # keep the card's mic line honest

    def build_icon(self, problem, mode_id=None, mode_label=None, mic_off=False):
        icon = QIcon()
        for size in (22, 32):
            icon.addPixmap(app_icon_pixmap(size, warn=problem, mode_id=mode_id,
                                           mode_label=mode_label, mic_off=mic_off))
        return icon

    def update_icon(self, state):
        tray = getattr(self, "tray", None)   # may be called during construction
        if tray is None:
            return
        problem = bool(state.get("error")) or state.get("access") == "denied" or bool(state.get("last_error"))
        mode = state.get("knob_mode") or {}
        label = mode.get("label")
        tip = "vibekey — AU05 control surface"
        if label:
            tip += " · Knob mode: %s" % label
        mic_off = self.mic in ("missing", "muted")
        if mic_off:
            tip += " · microphone " + ("muted" if self.mic == "muted" else "not connected")
        if problem:
            tip += " · see the Panel (attention badge)"
        tray.setIcon(self.build_icon(problem, mode.get("id"), label, mic_off))
        tray.setToolTip(tip)

    def toggle_window(self):
        if self.window.isVisible():
            self.window.hide()
        else:
            self.show_window()

    def show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()


def main():
    app = QApplication(sys.argv)
    TrayApp(app)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
