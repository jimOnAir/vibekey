#!/usr/bin/env python3
# PROTOTYPE — throwaway code that answers one question (ticket 0005):
#   "What should the vibekey Panel & picker look like on KDE?"
# Three radically different variants, switchable from the floating pill at the
# bottom of the screen (◀ ▶ buttons or F2/F3). No daemon, no persistence, fake
# state (see the pill's "state" button for the full dump).
#
# Run:  python3 prototype_panel_picker.py [--variant=A|B|C]
#
# Variant A "drawn keypad" — the panel draws the device; press a control on the
#   drawing (preview glows), Edit… opens the grouped-tile picker on the right.
# Variant B "list editor"  — ordinary KDE settings window; a table of the six
#   Controls, picker is a dialog; knob modes are a reorderable list.
# Variant C "tray HUD"     — no window at all: frameless dark popover, chips
#   instead of a drawing, Knob mode as a segmented control, double-click a chip
#   to edit inline.
#
# Simulate rules everywhere: hold a button ≥400 ms for the knob long-press
# (Enter); Preview checked → nothing "runs", events only report.

import json
import sys

from PySide6.QtCore import Qt, QElapsedTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMessageBox, QPushButton, QStatusBar,
    QSystemTrayIcon, QToolButton, QVBoxLayout, QWidget,
)

LONG_MS = 400
MODES = ["Scroll", "Sessions", "Volume"]
SESSIONS = ["ses_7f2… gpu-monitor", "ses_41a… vibekey", "ses_9c3… meta"]

CONTROLS = [
    ("voice", "Voice key"),
    ("confirm", "✓ Confirm"),
    ("cancel", "✕ Cancel"),
    ("knob_press", "Knob press"),
    ("knob_l", "Knob turn ◀"),
    ("knob_r", "Knob turn ▶"),
]

PRESET_GROUPS = {
    "Agent": ["Next Session", "Previous Session", "Interrupt (API/Esc)", "Focus Host"],
    "Dictation": ["Push-to-talk (handy)"],
    "Keys": ["Enter", "Escape", "custom combo…"],
    "Media / System": ["Volume ±", "Brightness ±", "Play / Pause", "Mute", "custom command…"],
}


class Model:
    def __init__(self):
        self.assign = {
            "voice": "Push-to-talk (handy)",
            "confirm": "Agent: next Session",
            "cancel": "Agent: interrupt",
            "knob_press": "Knob: cycle mode",
            "knob_long": "Enter",
            "knob_l": None,
            "knob_r": None,
        }
        self.modes = list(MODES)
        self.mode_i = 0
        self.preview = True
        self.cursor = -1
        self.battery = 78
        self.log = []

    def mode(self):
        return self.modes[self.mode_i]

    def shown(self, ctl):
        if ctl in ("knob_l", "knob_r"):
            d = "prev" if ctl == "knob_l" else "next"
            return {"Scroll": f"Scroll {d}", "Sessions": f"Session {d}",
                    "Volume": f"Volume {d}"}.get(self.mode(), self.mode())
        if ctl == "knob_press":
            return f"cycle mode → {', '.join(self.modes)} (long-press: Enter)"
        return self.assign.get(ctl, "?")

    def dump(self):
        return json.dumps(vars(self), indent=2, default=str)

    def event(self, kind, detail=""):
        verb = "WOULD RUN" if self.preview else "RAN (sim)"
        if kind == "mode_cycle":
            self.mode_i = (self.mode_i + 1) % len(self.modes)
            line = f"Knob press → mode: {self.mode()}   [{verb}: announce via notify + tray]"
        elif kind == "knob_long":
            line = f"Knob long-press ({detail}) → Enter   [{verb}]   ← permission prompts"
        elif kind in ("knob_l", "knob_r"):
            if self.mode() == "Sessions":
                step = 1 if kind == "knob_r" else -1
                self.cursor = (self.cursor + step) % len(SESSIONS)
                line = (f"{kind} → Ring {self.cursor+1}/{len(SESSIONS)}: {SESSIONS[self.cursor]}"
                        f"   [{verb}: raise Host]")
            else:
                line = f"{kind} → {self.shown(kind)}   [{verb}]"
        else:
            line = f"{detail} → {self.shown(detail)}   [{verb}]"
        self.log.append(line)
        return line


class SimButton(QPushButton):
    """press/hold/release capture; double-click optionally opens the editor."""

    def __init__(self, model, key, label, edit=None, parent=None):
        super().__init__(label, parent)
        self.model, self.key, self.edit = model, key, edit
        self.timer = QElapsedTimer()
        self.pressed.connect(self.timer.start)
        self.released.connect(self._up)

    def _up(self):
        ms = self.timer.elapsed()
        if self.key == "knob_press" and ms >= LONG_MS:
            return self.fired("knob_long", f"{ms} ms")
        if self.key == "knob_press":
            return self.fired("mode_cycle")
        self.fired(self.key)

    def mouseDoubleClickEvent(self, e):
        if self.edit:
            self.edit(self.key, self.text())
        else:
            super().mouseDoubleClickEvent(e)

    def fired(self, kind, detail=""):
        line = self.model.event(kind, detail)
        win = self.window()
        if hasattr(win, "set_status"):
            win.set_status(line)
        if hasattr(win, "refresh"):
            win.refresh()


class PickerDialog(QDialog):
    def __init__(self, ctl_label, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Pick an action — {ctl_label}")
        self.chosen = None
        lay = QVBoxLayout(self)
        for group, items in PRESET_GROUPS.items():
            lay.addWidget(QLabel(f"<b>{group}</b>"))
            row = QHBoxLayout()
            for it in items:
                b = QPushButton(it)
                b.clicked.connect(lambda _, s=it: self.pick(s))
                row.addWidget(b)
            lay.addLayout(row)
        for placeholder, tag in (("custom command (bash -c)…", "command"),
                                 ("key combo, e.g. ctrl+shift+t (xdotool)…", "combo")):
            row = QHBoxLayout()
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            b = QPushButton("Use")
            b.clicked.connect(lambda _, t=tag, e=e: self.pick_custom(t, e))
            row.addWidget(e)
            row.addWidget(b)
            lay.addLayout(row)
        if current:
            lay.addWidget(QLabel(f"<i>current: {current}</i>"))

    def pick(self, s):
        if s.endswith("…"):
            return self.pick_custom("value", QLineEdit())
        self.chosen = s
        self.accept()

    def pick_custom(self, tag, field):
        text = field.text().strip() if isinstance(field, QLineEdit) else ""
        if not text:
            text, ok = QInputDialog.getText(self, "Custom", f"{tag}:")
            if not ok or not text.strip():
                return
        self.chosen = f"custom {tag}: {text.strip()}"
        self.accept()


class BaseWindow(QMainWindow):
    NAME = ""

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.setStatusBar(QStatusBar())
        self.status_line = QLabel("fake events land here — press a Control (hold ≥400 ms on the knob)")
        self.statusBar().addWidget(self.status_line, 1)

    def set_status(self, line):
        self.status_line.setText(line)

    def preview_check(self):
        cb = QCheckBox("Preview (nothing runs)")
        cb.setChecked(self.model.preview)
        cb.toggled.connect(lambda v: setattr(self.model, "preview", v))
        return cb

    def edit_assignment(self, key, label):
        dlg = PickerDialog(label, self.model.assign.get(key), self)
        if dlg.exec() and dlg.chosen:
            self.model.assign[key] = dlg.chosen
            self.set_status(f"assigned {label} → {dlg.chosen}")
            self.refresh()

    def refresh(self):
        pass


class VariantA(BaseWindow):
    """Drawn keypad, left; assignment overview (picker via dialog), right."""

    NAME = "A — drawn keypad"

    def __init__(self, model):
        super().__init__(model)
        self.setWindowTitle("Vibekey (PROTOTYPE A)")
        self.resize(700, 400)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        top = QHBoxLayout()
        self.topinfo = QLabel()
        top.addWidget(self.topinfo, 1)
        top.addWidget(self.preview_check())
        outer.addLayout(top)

        body = QHBoxLayout()
        outer.addLayout(body)

        pad = QFrame()
        pad.setFixedSize(300, 320)
        pad.setStyleSheet(
            "QFrame{background:#1d1f24;border-radius:16px}"
            "QPushButton{background:#2b2e36;color:#e8e8ea;border-radius:10px;"
            "padding:10px;font-size:13px}QPushButton:pressed{background:#3d84f6;color:white}")
        pg = QGridLayout(pad)
        ed = self.edit_assignment
        pg.addWidget(SimButton(model, "voice", "◉ Voice", ed), 0, 0, 1, 3)
        pg.addWidget(SimButton(model, "confirm", "✓", ed), 1, 0)
        pg.addWidget(SimButton(model, "knob_press", "◎\npress / hold", ed), 1, 1)
        pg.addWidget(SimButton(model, "cancel", "✕", ed), 1, 2)
        pg.addWidget(SimButton(model, "knob_l", "⟲ ◀", ed), 2, 0)
        pg.addWidget(SimButton(model, "knob_r", "▶ ⟳", ed), 2, 2)
        body.addWidget(pad)

        ovl = QVBoxLayout()
        body.addLayout(ovl, 1)
        ovl.addWidget(QLabel("<b>Assignments</b> — single click simulates, double-click edits"))
        self.ov_rows = {}
        for key, label in CONTROLS:
            row = QHBoxLayout()
            lab = QLabel()
            lab.setMinimumWidth(260)
            row.addWidget(lab, 1)
            eb = QPushButton("Edit…")
            eb.clicked.connect(lambda _, k=key, l=label: self.edit_assignment(k, l))
            row.addWidget(eb)
            ovl.addLayout(row)
            self.ov_rows[key] = lab
        ovl.addStretch(1)
        self.refresh()

    def refresh(self):
        ring = SESSIONS[self.model.cursor] if self.model.cursor >= 0 else "—"
        self.topinfo.setText(f"<b>Knob mode: {self.model.mode()}</b> · Ring at: {ring} · 🔋 {self.model.battery}%")
        for key, label in CONTROLS:
            self.ov_rows[key].setText(f"<b>{label}</b><br><span style='color:#777'>{self.model.shown(key)}</span>")


class VariantB(BaseWindow):
    """Ordinary settings window: table + dialog picker + reorderable knob modes."""

    NAME = "B — list editor"

    def __init__(self, model):
        super().__init__(model)
        self.setWindowTitle("Vibekey (PROTOTYPE B)")
        self.resize(720, 420)
        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        head = QHBoxLayout()
        self.topinfo = QLabel()
        head.addWidget(self.topinfo, 1)
        head.addWidget(self.preview_check())
        lay.addLayout(head)

        grid = QGridLayout()
        lay.addLayout(grid, 1)
        self.rows = {}
        for c, h in enumerate(("Control", "Assignment", "Simulate (hold ≥400 ms on knob)")):
            grid.addWidget(QLabel(f"<b>{h}</b>"), 0, c)
        for r, (key, label) in enumerate(CONTROLS, 1):
            grid.addWidget(QLabel(f"<b>{label}</b>"), r, 0)
            lab = QLabel()
            grid.addWidget(lab, r, 1)
            grid.addWidget(SimButton(model, key, "⏺", self.edit_assignment), r, 2)
            eb = QPushButton("Edit…")
            eb.clicked.connect(lambda _, k=key, l=label: self.edit_assignment(k, l))
            grid.addWidget(eb, r, 3)
            self.rows[key] = lab

        modebox = QHBoxLayout()
        modebox.addWidget(QLabel("<b>Knob modes</b>\ncycle order:"))
        self.modes = QListWidget()
        self.modes.setMaximumHeight(80)
        self.modes.setSelectionMode(QListWidget.SingleSelection)
        modebox.addWidget(self.modes, 1)
        for text, fn in (("↑", -1), ("↓", 1), ("add mode", 0), ("remove", 0)):
            b = QPushButton(text)
            b.clicked.connect(lambda _, f=fn, t=text: self.mode_op(f, t))
            modebox.addWidget(b)
        lay.addLayout(modebox)
        self.reload_modes()
        self.refresh()

    def mode_op(self, delta, text):
        i = self.modes.currentRow()
        if text == "add mode":
            self.model.modes.append("new mode")
        elif text == "remove" and 0 <= i < len(self.model.modes) and len(self.model.modes) > 1:
            self.model.modes.pop(i)
        elif 0 <= i < len(self.model.modes) and 0 <= i + delta < len(self.model.modes):
            self.model.modes[i], self.model.modes[i + delta] = self.model.modes[i + delta], self.model.modes[i]
        self.model.mode_i = min(self.model.mode_i, len(self.model.modes) - 1)
        self.reload_modes()
        self.refresh()

    def reload_modes(self):
        cur = self.model.mode()
        self.modes.clear()
        for m in self.model.modes:
            QListWidgetItem(f"{m}{' ⟵' if m == cur else ''}", self.modes)
        self.modes.setCurrentRow(self.model.modes.index(cur) if cur in self.model.modes else 0)

    def refresh(self):
        ring = SESSIONS[self.model.cursor] if self.model.cursor >= 0 else "—"
        self.topinfo.setText(f"<b>Knob mode: {self.model.mode()}</b> · Ring at: {ring} · 🔋 {self.model.battery}%")
        for key, lab in self.rows.items():
            lab.setText(self.model.shown(key))


class VariantC(BaseWindow):
    """Frameless dark tray-HUD: segmented Knob mode, chips, inline edit strip."""

    NAME = "C — tray HUD"

    def __init__(self, model):
        super().__init__(model)
        self.setWindowTitle("Vibekey HUD (PROTOTYPE C)")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(
            "QMainWindow,QWidget{background:#16171b;color:#dcdce0}"
            "QToolButton,QPushButton{background:#26293f;border-radius:6px;padding:6px;color:#dcdce0}"
            "QToolButton:checked{background:#3d84f6;color:white}"
            "QPushButton:pressed{background:#3d84f6}"
            "QLineEdit{background:#22242a;border:1px solid #33363f;border-radius:4px;padding:4px;color:#dcdce0}")
        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(10, 8, 10, 8)

        head = QHBoxLayout()
        self.segs = []
        for m in MODES:
            b = QToolButton()
            b.setText(m)
            b.setCheckable(True)
            b.clicked.connect(lambda _, mm=m: self.pick_mode(mm))
            self.segs.append(b)
            head.addWidget(b)
        head.addStretch(1)
        self.batt = QLabel()
        head.addWidget(self.batt)
        lay.addLayout(head)

        chips = QGridLayout()
        for i, (key, label) in enumerate(CONTROLS):
            b = SimButton(model, key, label.replace("Knob ", ""),
                          lambda k, t: self.open_inline(k))
            b.setFixedHeight(46)
            chips.addWidget(b, i // 3, i % 3)
        lay.addLayout(chips)

        self.strip = QLabel()
        self.strip.setWordWrap(True)
        lay.addWidget(self.strip)
        self.edit_row = QHBoxLayout()
        self.edit_field = QLineEdit()
        self.edit_field.setPlaceholderText("type action, Enter to assign")
        self.edit_field.returnPressed.connect(self.apply_inline)
        self.edit_row.addWidget(self.edit_field)
        self.edit_field.hide()
        lay.addLayout(self.edit_row)
        self.editing = None

        self.toast = QLabel("")
        self.toast.setWordWrap(True)
        self.toast.setStyleSheet("color:#7fb2ff")
        lay.addWidget(self.toast)
        lay.addWidget(self.preview_check())
        self.move(1140, 40)
        self.refresh()

    def pick_mode(self, m):
        if m not in self.model.modes:
            self.model.modes.append(m)
        self.model.mode_i = self.model.modes.index(m)
        self.model.log.append(f"HUD segmented → mode: {m}")
        self.refresh()

    def open_inline(self, key):
        self.editing = key
        self.edit_field.show()
        self.edit_field.setText(self.model.shown(key))
        self.refresh()

    def apply_inline(self):
        if self.editing and self.edit_field.text().strip():
            self.model.assign[self.editing] = self.edit_field.text().strip()
            self.editing = None
            self.edit_field.hide()
            self.refresh()

    def refresh(self):
        for b in self.segs:
            b.setChecked(b.text() == self.model.mode())
        self.batt.setText(f"🔋 {self.model.battery}%")
        self.strip.setText(
            "<i>click chip = simulate · double-click = edit inline</i><br>"
            + " · ".join(f"{lbl.split(' ')[0]}: {self.model.shown(k)}" for k, lbl in CONTROLS[:3]))
        self.toast.setText(self.model.log[-1] if self.model.log else "")


class App:
    VARIANTS = {"A": VariantA, "B": VariantB, "C": VariantC}

    def __init__(self, app, model, start):
        self.app, self.model, self.cur = app, model, start
        self.win = None
        self.pill = self.make_pill()
        self.show(start)
        for seq, fn in ((QKeySequence("F2"), self.prev), (QKeySequence("F3"), self.next)):
            sc = QShortcut(seq, self.pill)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(fn)
        self.tray = self.make_tray()

    def show(self, key):
        self.cur = key
        if self.win:
            self.win.close()
        self.win = self.VARIANTS[key](self.model)
        self.win.show()
        names = "  ".join(f"{'▶ ' if k == key else ''}{k}" for k in self.VARIANTS)
        self.pill_label.setText(f" vibekey PROTOTYPE  {names}   {self.VARIANTS[key].NAME}  ")
        self.pill.adjustSize()
        scr = QApplication.primaryScreen().availableGeometry()
        self.pill.move(scr.center().x() - self.pill.width() // 2, scr.bottom() - self.pill.height() - 24)

    def next(self):
        ks = list(self.VARIANTS)
        self.show(ks[(ks.index(self.cur) + 1) % len(ks)])

    def prev(self):
        ks = list(self.VARIANTS)
        self.show(ks[(ks.index(self.cur) - 1) % len(ks)])

    def make_pill(self):
        pill = QFrame()
        pill.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        pill.setStyleSheet("QFrame{background:#000;border-radius:14px}"
                           "QPushButton,QLabel{color:#fff;border:none;background:transparent;font-size:13px}")
        lay = QHBoxLayout(pill)
        self.pill_label = QLabel()
        b1, b2, st = QPushButton("◀"), QPushButton("▶"), QPushButton("state")
        b1.clicked.connect(self.prev)
        b2.clicked.connect(self.next)
        st.clicked.connect(lambda: QMessageBox.information(None, "fake state", self.model.dump()))
        for w in (b1, self.pill_label, b2, st):
            lay.addWidget(w)
        pill.adjustSize()
        scr = QApplication.primaryScreen().availableGeometry()
        pill.move(scr.center().x() - pill.width() // 2, scr.bottom() - pill.height() - 24)
        pill.show()
        return pill

    def make_tray(self):
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setBrush(QColor("#3d84f6"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(3, 3, 26, 26)
        p.setPen(QColor("white"))
        p.setFont(QFont("sans", 10, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "VK")
        p.end()
        icon = QIcon(pm)
        self.app.setWindowIcon(icon)
        tray = QSystemTrayIcon(icon, self.app)
        menu = QMenu()
        for k, cls in self.VARIANTS.items():
            act = QAction(f"show {cls.NAME}", menu)
            act.triggered.connect(lambda _, kk=k: self.show(kk))
            menu.addAction(act)
        menu.addSeparator()
        quit_act = QAction("quit (throwaway)", menu)
        quit_act.triggered.connect(self.app.quit)
        menu.addAction(quit_act)
        tray.setContextMenu(menu)
        tray.setToolTip("vibekey PROTOTYPE — fake device")
        tray.showMessage("vibekey prototype", "A/B/C switchable from the black pill at the bottom",
                         QSystemTrayIcon.MessageIcon.Information, 5000)
        tray.show()
        return tray


def main():
    start = "A"
    for a in sys.argv:
        if a.startswith("--variant="):
            start = a.split("=", 1)[1].upper()
    app = QApplication(sys.argv)
    app.setApplicationName("vibekey-prototype")
    model = Model()
    App(app, model, start if start in App.VARIANTS else "A")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
