"""
mixer_widgets.py

Defines the visual components (widgets) for the mixer UI, based on the approved mock-up.
This includes the detailed channel strip, stereo pairs, and group widgets.
"""
import alsa_backend
import math
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QFontMetrics, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSizePolicy, QPushButton, QSpacerItem
)

# --- Custom Palette from Mock-up ---
Colors = {
    "background": QColor("#2d3748"),
    "fader_bg": QColor("#222b3c"),
    "fader_track": QColor("#1a202c"),
    "text_light": QColor("#cbd5e0"),
    "text_primary": QColor("#FFD700"),
    "button_bg": QColor("#4a5568"),
    "active_red": QColor("#f08080"),
    "active_yellow": QColor("#fffacd"),
    "active_blue": QColor("#87ceeb"),
    "marker": QColor("#a0aec0"),
    "group_bg": QColor("#38475a"),  # e.g. softer blue, lighter than background
}
Colors["marker"].setAlphaF(0.2) # Softer 50% translucency
Colors["group_bg"].setAlphaF(0.2)  # 20% opaque

class PanBox(QWidget):
    """
    A horizontal pan control: -100 (L) ... 0 (C) ... +100 (R)
    Shows a dynamic label: Lxx, C, or Rxx
    """
    valueChanged = pyqtSignal(int)
    def __init__(self, value=0, parent=None):
        super().__init__(parent)
        self._value = value
        self.setMinimumHeight(36)
        self.setMaximumHeight(40)
        self.setMinimumWidth(80)
        self.setMaximumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._dragging = False

    def value(self):
        return self._value

    def setValue(self, v):
        v = max(-100, min(100, int(v)))
        if self._value != v:
            self._value = v
            self.valueChanged.emit(v)
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        rect = self.rect().adjusted(10, 10, -10, -10)
        # Draw track
        p.setPen(QPen(Colors['fader_track'], 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 9, 9)

        # Draw dynamic pan label (Lxx, C, Rxx)
        font = QFont("Inter", 9, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(Colors['text_primary'])
        metrics = QFontMetrics(font)
        if self._value == 0:
            pan_str = "C"
        elif self._value < 0:
            pan_str = f"L{abs(self._value)}"
        else:
            pan_str = f"R{self._value}"
        x_label = rect.center().x() - metrics.horizontalAdvance(pan_str)//2
        p.drawText(int(x_label), rect.top() - 2, pan_str)

        # Draw handle
        x_pos = rect.left() + ((self._value + 100) / 200.0) * rect.width()
        handle_rect = QRect(int(x_pos) - 8, rect.top() + 8, 16, rect.height() - 16)
        p.setBrush(Colors['active_blue'])
        p.setPen(QPen(Colors['active_blue'], 1))
        p.drawRoundedRect(handle_rect, 6, 6)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._set_from_pos(event.position().x())
    def mouseMoveEvent(self, event):
        if self._dragging:
            self._set_from_pos(event.position().x())
    def mouseReleaseEvent(self, event):
        self._dragging = False
    def _set_from_pos(self, x):
        rect = self.rect().adjusted(10, 10, -10, -10)
        rel = (x - rect.left()) / rect.width()
        rel = max(0, min(1, rel))
        value = int(rel * 200 - 100)
        self.setValue(value)

class ElidedLabel(QWidget):
    """ A custom widget to display vertical, elided text that correctly sizes itself. """
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.font = QFont("Inter", 10, QFont.Weight.Bold)
        self.fm = QFontMetrics(self.font)
        # The width of the vertical text becomes the height of the widget
        self.text_width = self.fm.horizontalAdvance(self.text)
        self.setMinimumSize(self.sizeHint())

    def sizeHint(self):
        # The hint for this widget is rotated: width is font height, height is text length
        return QSize(self.fm.height(), self.text_width + 10) # Add padding

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Colors["text_light"])
        painter.setFont(self.font)

        # Center the rotation point
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-90)
        # Translate back to draw
        painter.translate(-self.height() / 2, -self.width() / 2)

        # Draw text centered in the new coordinate system
        rect = QRect(0, 0, self.height(), self.width())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)
        painter.end()


class Fader(QWidget):
    """ A custom fader widget with a precisely aligned 0dB marker. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setValue(70)
        self.slider.setStyleSheet(f"""
            QSlider::groove:vertical {{
                background: {Colors['fader_track'].name()};
                width: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:vertical {{
                background: {Colors['active_red'].name()};
                height: 10px;
                width: 24px;
                margin: 0 -8px;
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.slider)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(Colors["marker"])

        # Correctly align the marker with the center of the fader handle
        # A value of 70 is at 30% from the top.
        # The center of a 10px handle at that position is at (height * 0.3) + 5px
        # So we draw our 10px line starting at (height * 0.3) to align perfectly
        marker_y = int(self.height() * 0.3)
        marker_x = 0
        marker_w = int(self.width() / 2)

        p.drawRoundedRect(marker_x, marker_y, marker_w, 10, 3, 3)
        p.end()


class ChannelStrip(QWidget):
    def __init__(self, channel_name, functions=None, is_output=False, parent=None, crosspoints=None, linked=True):
        super().__init__(parent)
        self.channel_name = channel_name
        self.is_output = is_output
        self.crosspoints = crosspoints or {}  # dict of {'L->L':..., ...}
        self.linked = linked

        self.setMinimumSize(100, 260)
        self.setMaximumWidth(140)

        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(8, 12, 8, 12)
        v_layout.setSpacing(10)

        controls_area = QWidget()
        controls_layout = QHBoxLayout(controls_area)
        controls_layout.setContentsMargins(0,0,0,0)
        controls_layout.setSpacing(10)

        self.fader = Fader()
        controls_layout.addWidget(self.fader)

        self.fader.slider.setValue(self.get_alsa_value())
        self.fader.slider.valueChanged.connect(self.on_fader_change)

        control_axis_widget = QWidget()
        control_axis_layout = QVBoxLayout(control_axis_widget)
        control_axis_layout.setContentsMargins(0,0,0,0)
        control_axis_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Function buttons (48V, PAD, etc)
        self.function_buttons = []
        top_buttons_layout = QVBoxLayout()
        if functions:
            for func_ctrl in functions:
                btn = QPushButton(func_ctrl.split()[-1])
                btn.setCheckable(True)
                btn.setToolTip(func_ctrl)
                btn.clicked.connect(lambda checked, fc=func_ctrl: self.set_function_control(fc, checked))
                top_buttons_layout.addWidget(btn)
                self.function_buttons.append((btn, func_ctrl))
        control_axis_layout.addLayout(top_buttons_layout)
        control_axis_layout.addStretch()

        self.name_label = ElidedLabel(self.channel_name)
        control_axis_layout.addWidget(self.name_label, alignment=Qt.AlignmentFlag.AlignCenter)
        control_axis_layout.addStretch()

        bottom_buttons_layout = QVBoxLayout()
        btn_mute = QPushButton("M")
        btn_solo = QPushButton("S")
        bottom_buttons_layout.addWidget(btn_mute)
        bottom_buttons_layout.addWidget(btn_solo)
        control_axis_layout.addLayout(bottom_buttons_layout)

        controls_layout.addWidget(control_axis_widget)
        v_layout.addWidget(controls_area, stretch=1)

        # PAN AREA (dynamic, created below)
        self.pan_area = QWidget()
        self.pan_layout = QHBoxLayout(self.pan_area)
        self.pan_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.pan_area)

        self.db_label = QLabel("0.0")
        self.db_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(self.db_label)

        self.fader.slider.setValue(self.get_alsa_value())
        self.fader.slider.valueChanged.connect(self.on_fader_change)

        self.set_button_styles()
        # self.setup_pan_widgets()   # No longer needed; see below

    def show_individual_pan(self, show=True):
        # Remove old pan widget if present
        for i in reversed(range(self.pan_layout.count())):
            item = self.pan_layout.takeAt(i)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        if show:
            self.indiv_panbox = PanBox(0)
            self.pan_layout.addWidget(self.indiv_panbox, alignment=Qt.AlignmentFlag.AlignCenter)
            # Connect panbox signal to handler
            self.indiv_panbox.valueChanged.connect(self.on_indiv_pan_changed)
        else:
            self.indiv_panbox = None

    def on_indiv_pan_changed(self, value):
        """
        TotalMixFX-style pan law for unlinked mono strip.
        - Fader stays fixed at user-set value.
        - Pan splits fader value between main and crosspoint ALSA controls.
        """
        import math  # Only if not already imported at top
        fader = self.fader.slider.value()
        pan = max(-100, min(100, value))
        pan_norm = pan / 100  # -1 to 1

        if self.channel_name.endswith("AN1"):
            main = self.channel_name
            cross = self.crosspoints.get("L->R")
            main_vol = int(fader * math.cos((pan_norm + 1) * (math.pi / 4)))
            cross_vol = int(fader * math.sin((pan_norm + 1) * (math.pi / 4)))
        else:
            main = self.channel_name
            cross = self.crosspoints.get("R->L")
            main_vol = int(fader * math.cos((1 - pan_norm) * (math.pi / 4)))
            cross_vol = int(fader * math.sin((1 - pan_norm) * (math.pi / 4)))

        alsa_backend.set_volume(main, max(0, min(100, main_vol)))
        if cross:
            alsa_backend.set_volume(cross, max(0, min(100, cross_vol)))

    def get_alsa_value(self):
        try:
            return alsa_backend.get_volume(self.channel_name)
        except Exception:
            return 0

    def set_alsa_value(self, value):
        try:
            alsa_backend.set_volume(self.channel_name, value)
        except Exception:
            pass

    def on_fader_change(self, value):
        self.set_alsa_value(value)
        self.db_label.setText(f"{value}")

    def set_function_control(self, func_ctrl, checked):
        try:
            alsa_backend.set_volume(func_ctrl, int(checked))
        except Exception:
            pass

    def set_button_styles(self):
        btn_style = f"""
            QPushButton {{
                background-color: #4a5568;
                color: #cbd5e0;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                min-width: 32px;
                max-width: 32px;
                min-height: 24px;
                max-height: 24px;
            }}
            QPushButton:checked {{
                background-color: #f08080;
                color: white;
            }}
        """
        self.setStyleSheet(self.styleSheet() + btn_style)

        for btn in self.findChildren(QPushButton):
            if btn.text() == "S":
                btn.setStyleSheet(btn.styleSheet() + f"QPushButton:checked {{ background-color: #fffacd; color: black; }}")
            if btn.text() == "L":
                btn.setStyleSheet(btn.styleSheet() + f"QPushButton:checked {{ background-color: #87ceeb; }}")

from PyQt6.QtGui import QIcon  # Add this import at the top if not present

class StereoPairStrip(QWidget):
    def __init__(self, lname, rname, functions=None, parent=None):
        super().__init__(parent)
        self.linked = True  # Initial default

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        hpair = QHBoxLayout()
        hpair.setContentsMargins(0, 0, 0, 0)
        hpair.setSpacing(2)

        crosspoints = {
            'L->L': lname,
            'L->R': lname[:-1] + rname[-1],
            'R->L': rname[:-1] + lname[-1],
            'R->R': rname,
        }

        self.left_strip = ChannelStrip(lname, functions, crosspoints=crosspoints, linked=self.linked)
        self.right_strip = ChannelStrip(rname, functions, crosspoints=crosspoints, linked=self.linked)

        # Mono detection (after strips are created!)
        left_cross = self.left_strip.crosspoints.get('L->R')
        right_cross = self.right_strip.crosspoints.get('R->L')
        mono_detected = False
        if left_cross and alsa_backend.get_volume(left_cross) > 0:
            mono_detected = True
        if right_cross and alsa_backend.get_volume(right_cross) > 0:
            mono_detected = True

        # --- PAN ROW (always present, swap what's visible)
        self.pan_row = QHBoxLayout()
        self.pan_row.setContentsMargins(0, 0, 0, 0)
        self.pan_row.setSpacing(8)

        self.pair_panbox = PanBox(0)
        self.left_panbox = PanBox(0)
        self.right_panbox = PanBox(0)

        # Linked: connect single panbox as before
        self.pair_panbox.valueChanged.connect(self.on_pair_pan_changed)
        # Unlinked: connect each panbox to channel strip logic
        self.left_panbox.valueChanged.connect(self.left_strip.on_indiv_pan_changed)
        self.right_panbox.valueChanged.connect(self.right_strip.on_indiv_pan_changed)

        # Add all three, hide/show as needed
        self.pan_row.addWidget(self.pair_panbox, stretch=2)
        self.pan_row.addWidget(self.left_panbox, stretch=1)
        self.pan_row.addWidget(self.right_panbox, stretch=1)
        layout.addLayout(self.pan_row)

        # Fader block
        hpair.addWidget(self.left_strip)
        hpair.addWidget(self.right_strip)
        layout.addLayout(hpair)

        # --- Link button with SVG icon ---
        self.link_btn = QPushButton()
        self.link_btn.setCheckable(True)
        self.link_btn.setToolTip("Stereo Link: Move both faders together")
        self.link_btn.setMinimumSize(32, 24)
        self.link_btn.setMaximumSize(32, 24)
        self.link_btn.setIcon(QIcon("icons/link.svg"))
        self.link_btn.setIconSize(QSize(22, 22))
        self.link_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5568;
                border-radius: 6px;
                min-width: 32px; max-width: 32px;
                min-height: 24px; max-height: 24px;
            }
            QPushButton:checked {
                background-color: #87ceeb !important;
            }
        """)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.link_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.link_btn.clicked.connect(self.on_link_clicked)
        self.left_strip.fader.slider.valueChanged.connect(self._left_fader_moved)
        self.right_strip.fader.slider.valueChanged.connect(self._right_fader_moved)

        # Set initial link state based on ALSA
        if mono_detected:
            self.link_btn.setChecked(False)
            self.on_link_clicked(False)
        else:
            self.link_btn.setChecked(True)
            self.on_link_clicked(True)

    def on_link_clicked(self, checked):
        self.linked = checked
        self.pair_panbox.setVisible(self.linked)
        self.left_panbox.setVisible(not self.linked)
        self.right_panbox.setVisible(not self.linked)
        self.left_strip.show_individual_pan(False)
        self.right_strip.show_individual_pan(False)

        if checked:
            # Stereo: zero crosspoints
            left_cross = self.left_strip.crosspoints.get('L->R')
            right_cross = self.right_strip.crosspoints.get('R->L')
            if left_cross:
                alsa_backend.set_volume(left_cross, 0)
            if right_cross:
                alsa_backend.set_volume(right_cross, 0)
        else:
            # Unlinked: set default pans so image/sound doesn't change
            self.left_panbox.setValue(-100)   # Hard left (only to L out)
            self.right_panbox.setValue(100)   # Hard right (only to R out)

    def _left_fader_moved(self, value):
        if self.linked and self.right_strip.fader.slider.value() != value:
            self.right_strip.fader.slider.blockSignals(True)
            self.right_strip.fader.slider.setValue(value)
            self.right_strip.fader.slider.blockSignals(False)
            self.right_strip.set_alsa_value(value)
            self.right_strip.db_label.setText(f"{value}")

    def _right_fader_moved(self, value):
        if self.linked and self.left_strip.fader.slider.value() != value:
            self.left_strip.fader.slider.blockSignals(True)
            self.left_strip.fader.slider.setValue(value)
            self.left_strip.fader.slider.blockSignals(False)
            self.left_strip.set_alsa_value(value)
            self.left_strip.db_label.setText(f"{value}")

    def on_pair_pan_changed(self, value):
        # Pan should not change the main fader's ALSA volume!
        # If you have matrix routing/crosspoint, set those here. Otherwise, do nothing.
        left_cross = self.left_strip.crosspoints.get('L->R')
        right_cross = self.right_strip.crosspoints.get('R->L')
        # In linked mode, crosspoints should always be zero.
        if left_cross:
            alsa_backend.set_volume(left_cross, 0)
        if right_cross:
            alsa_backend.set_volume(right_cross, 0)
        # Optionally, if you have actual matrix output controls, set their levels for balance here.
        # Otherwise, DO NOTHING regarding main channel volumes!

class MixerGroupWidget(QWidget):
    def __init__(self, group_name, pair_list, func_map, parent=None):
        super().__init__(parent)
        v_layout = QVBoxLayout()
        v_layout.setSpacing(8)
        v_layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(group_name)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Inter", 11, QFont.Weight.Normal))
        lbl.setStyleSheet(f"color:{Colors['text_light'].name()}; padding: 4px;")
        v_layout.addWidget(lbl)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(12)

        def is_main_channel(channel):
            parts = channel.split('-')
            return len(parts) == 3 and parts[1] == parts[2]

        for l, r in pair_list:
            print("Creating fader for:", l, r)
            h_layout.addWidget(StereoPairStrip(l, r, func_map))

        v_layout.addLayout(h_layout)

        # Wrap everything in a "card"
        card = GroupCardWidget(QWidget())
        card.layout().addLayout(v_layout)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.addWidget(card)


class GroupCardWidget(QWidget):
    def __init__(self, content_widget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)  # Padding inside the card
        layout.addWidget(content_widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg_color = Colors["group_bg"]
        rect = self.rect().adjusted(0, 0, -1, -1)
        p.setBrush(bg_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 18, 18)
        p.end()

class OutputFaderWidget(QWidget):
    def __init__(self, lout, rout, parent=None):
        super().__init__(parent)
        v_layout = QVBoxLayout(self)
        v_layout.setSpacing(8)
        v_layout.setContentsMargins(0, 0, 0, 0)

        # --- Unified group box with same style as input groups
        box = QWidget(self)
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(8)
        box_layout.setContentsMargins(24, 10, 24, 10)  # Same as input group boxes
        box.setStyleSheet("""
            background-color: rgba(76, 35, 40, 0.17);
            border-radius: 32px;
        """)

        # --- Label
        lbl = QLabel("OUTPUT")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("color:#FFD7D7; padding: 4px;")
        box_layout.addWidget(lbl)

        # --- Stereo pair: same layout as groups
        h_layout = QHBoxLayout()
        h_layout.setSpacing(2)
        h_layout.setContentsMargins(0, 0, 0, 0)

        # No output-specific width/height!
        self.left_out_strip = ChannelStrip(lout)
        self.right_out_strip = ChannelStrip(rout)

        # Hide unused buttons
        for btn in self.left_out_strip.findChildren(QPushButton) + self.right_out_strip.findChildren(QPushButton):
            btn.setVisible(False)

        h_layout.addWidget(self.left_out_strip)
        h_layout.addWidget(self.right_out_strip)
        box_layout.addLayout(h_layout)

        # --- Link button
        self.linked = True
        self.link_btn = QPushButton("🔗")
        self.link_btn.setCheckable(True)
        self.link_btn.setChecked(self.linked)
        self.link_btn.setToolTip("Stereo Link: Move both output faders together")
        self.link_btn.setMinimumSize(32, 24)
        self.link_btn.setMaximumSize(32, 24)
        self.link_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5568;
                color: #cbd5e0;
                border-radius: 6px;
                font-size: 18px;
                min-width: 32px; max-width: 32px;
                min-height: 24px; max-height: 24px;
            }
            QPushButton:checked,
            QPushButton:checked:hover,
            QPushButton:checked:focus {
                background-color: #FFD7D7 !important;
                color: black !important;
            }
        """)
        self.link_btn.clicked.connect(self.on_link_clicked)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.link_btn)
        btn_row.addStretch(1)
        box_layout.addLayout(btn_row)

        v_layout.addWidget(box, stretch=1)
        self.setLayout(v_layout)

        # --- Link logic
        self.left_out_strip.fader.slider.valueChanged.connect(self._left_fader_moved)
        self.right_out_strip.fader.slider.valueChanged.connect(self._right_fader_moved)

    def on_link_clicked(self, checked):
        self.linked = checked

    def _left_fader_moved(self, value):
        if self.linked and self.right_out_strip.fader.slider.value() != value:
            self.right_out_strip.fader.slider.blockSignals(True)
            self.right_out_strip.fader.slider.setValue(value)
            self.right_out_strip.fader.slider.blockSignals(False)
            self.right_out_strip.set_alsa_value(value)
            self.right_out_strip.db_label.setText(f"{value}")

    def _right_fader_moved(self, value):
        if self.linked and self.left_out_strip.fader.slider.value() != value:
            self.left_out_strip.fader.slider.blockSignals(True)
            self.left_out_strip.fader.slider.setValue(value)
            self.left_out_strip.fader.slider.blockSignals(False)
            self.left_out_strip.set_alsa_value(value)
            self.left_out_strip.db_label.setText(f"{value}")
