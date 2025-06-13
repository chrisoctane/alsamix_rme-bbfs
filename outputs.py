# outputs.py
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QToolButton, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
import alsa_backend

CARD_INDEX = 1

# List of output pairs (customize as needed for your Babyface Pro FS)
OUTPUT_PAIRS = [
    ("AN1", "AN2"),
    ("PH3", "PH4"),
    ("AS1", "AS2"),
    ("ADAT3", "ADAT4"),
    ("ADAT5", "ADAT6"),
    ("ADAT7", "ADAT8"),
]

class MixerFaderPair(QWidget):
    """Fader + pan + link + mute + solo for a source-to-output pair."""
    def __init__(self, ctl_l, ctl_r, cardindex=1):
        super().__init__()
        self.ctl_l, self.ctl_r = ctl_l, ctl_r
        self.cardindex = cardindex
        self.linked = False
        self.muted = False
        self.soloed = False

        self.slider_l = QSlider(Qt.Orientation.Vertical)
        self.slider_r = QSlider(Qt.Orientation.Vertical)
        self.slider_l.setRange(0, 100)
        self.slider_r.setRange(0, 100)
        self.slider_l.setValue(alsa_backend.get_volume(ctl_l, cardindex))
        self.slider_r.setValue(alsa_backend.get_volume(ctl_r, cardindex))

        self.slider_l.valueChanged.connect(self.on_left_changed)
        self.slider_r.valueChanged.connect(self.on_right_changed)

        # Pan sliders: -50 (left) to +50 (right)
        self.pan_l = QSlider(Qt.Orientation.Horizontal)
        self.pan_l.setRange(-50, 50)
        self.pan_l.setValue(0)
        self.pan_r = QSlider(Qt.Orientation.Horizontal)
        self.pan_r.setRange(-50, 50)
        self.pan_r.setValue(0)
        # (Pan logic would be applied in software/driver. Here, just UI.)

        # Link, mute, solo
        self.btn_link = QToolButton(); self.btn_link.setText("🔗")
        self.btn_link.setCheckable(True)
        self.btn_link.toggled.connect(self.update_link)
        self.btn_mute = QToolButton(); self.btn_mute.setText("M"); self.btn_mute.setCheckable(True)
        self.btn_mute.toggled.connect(self.toggle_mute)
        self.btn_solo = QToolButton(); self.btn_solo.setText("S"); self.btn_solo.setCheckable(True)
        self.btn_solo.toggled.connect(self.toggle_solo)

        # Layout
        col_l = QVBoxLayout()
        col_l.addWidget(QLabel(ctl_l)); col_l.addWidget(self.slider_l); col_l.addWidget(self.pan_l)
        col_r = QVBoxLayout()
        col_r.addWidget(QLabel(ctl_r)); col_r.addWidget(self.slider_r); col_r.addWidget(self.pan_r)
        col_controls = QVBoxLayout()
        col_controls.addWidget(self.btn_link)
        col_controls.addWidget(self.btn_mute)
        col_controls.addWidget(self.btn_solo)
        h = QHBoxLayout(self)
        h.addLayout(col_l)
        h.addLayout(col_controls)
        h.addLayout(col_r)
        self.setLayout(h)

    def update_link(self, checked):
        self.linked = checked
        self.btn_link.setStyleSheet("background: #888800;" if checked else "")
        if checked:
            # Link sliders
            val = self.slider_l.value()
            self.slider_r.blockSignals(True); self.slider_r.setValue(val); self.slider_r.blockSignals(False)

    def on_left_changed(self, val):
        alsa_backend.set_volume(self.ctl_l, val, self.cardindex)
        if self.linked:
            self.slider_r.blockSignals(True); self.slider_r.setValue(val); self.slider_r.blockSignals(False)
            alsa_backend.set_volume(self.ctl_r, val, self.cardindex)

    def on_right_changed(self, val):
        alsa_backend.set_volume(self.ctl_r, val, self.cardindex)
        if self.linked:
            self.slider_l.blockSignals(True); self.slider_l.setValue(val); self.slider_l.blockSignals(False)
            alsa_backend.set_volume(self.ctl_l, val, self.cardindex)

    def toggle_mute(self, checked):
        # UI only: actual mute logic to be applied in global state later
        self.muted = checked
        if checked:
            self.slider_l.blockSignals(True); self.slider_l.setValue(0); self.slider_l.blockSignals(False)
            self.slider_r.blockSignals(True); self.slider_r.setValue(0); self.slider_r.blockSignals(False)
        # Unmute: does NOT restore previous value (simple version)
        # Full logic can be added!

    def toggle_solo(self, checked):
        self.soloed = checked
        # UI only: actual solo logic to be applied in parent class later

class OutputTabs(QWidget):
    """Tabs with one output pair per tab, faders for all routed inputs."""
    def __init__(self, cardindex=1):
        super().__init__()
        self.tabs = QTabWidget()
        vbox = QVBoxLayout(self); vbox.addWidget(self.tabs)
        self.setLayout(vbox)
        self.cardindex = cardindex
        self.populate_tabs()

    def populate_tabs(self):
        routing = alsa_backend.all_routes(self.cardindex)
        for left, right in OUTPUT_PAIRS:
            tab = QWidget()
            vbox = QVBoxLayout(tab)
            scroll = QScrollArea()
            cont = QWidget(); hbox = QHBoxLayout(cont)
            hbox.setSpacing(12)
            # For this output pair, find all controls matching (src, left) and (src, right)
            sources_left = [(ctl, src) for (ctl, src) in routing.get(left, [])]
            sources_right = [(ctl, src) for (ctl, src) in routing.get(right, [])]
            # Pair them by src name (if exists for both)
            used = set()
            for ctl_l, src_l in sources_left:
                # Try to find matching src in right side
                match = next(((ctl_r, src_r) for (ctl_r, src_r) in sources_right if src_r == src_l), None)
                if match:
                    ctl_r, src_r = match
                    fader = MixerFaderPair(ctl_l, ctl_r, cardindex=self.cardindex)
                    hbox.addWidget(fader)
                    used.add(ctl_r)
                else:
                    # No stereo pair, just add left as mono
                    fader = MixerFaderPair(ctl_l, None, cardindex=self.cardindex)
                    hbox.addWidget(fader)
            # Add right-only monos (not paired above)
            for ctl_r, src_r in sources_right:
                if ctl_r not in used:
                    fader = MixerFaderPair(None, ctl_r, cardindex=self.cardindex)
                    hbox.addWidget(fader)
            hbox.addStretch()
            cont.setLayout(hbox)
            scroll.setWidget(cont); scroll.setWidgetResizable(True)
            vbox.addWidget(scroll)
            self.tabs.addTab(tab, f"{left}/{right}")
