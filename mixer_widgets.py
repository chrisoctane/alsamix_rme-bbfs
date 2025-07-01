"""
mixer_widgets.py

Defines the visual components (widgets) for the mixer UI, based on the approved mock-up.
This includes the detailed channel strip, stereo pairs, and group widgets.
"""
import alsa_backend

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QFontMetrics
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



# --- Simple pan control ---
class PanControl(QWidget):
    def __init__(self, label, initial=0, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.label = QLabel(label)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-100, 100)
        self.slider.setValue(initial)
        self.slider.setMinimumWidth(50)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        self.setLayout(layout)
    def set_value(self, value):
        self.slider.setValue(value)
    def get_value(self):
        return self.slider.value()
    def connect(self, fn):
        self.slider.valueChanged.connect(fn)

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

        # PAN LAYOUT AREA (dynamic)
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
        self.setup_pan_widgets()

    def setup_pan_widgets(self):
        # Remove old
        for i in reversed(range(self.pan_layout.count())):
            item = self.pan_layout.takeAt(i)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        # Linked: no individual pan; shown only on one strip (balance for pair in StereoPairStrip)
        if self.linked:
            self.pan = PanControl("Balance", 0)
            self.pan.connect(self.on_pan_change)
            self.pan_layout.addWidget(self.pan)
        else:
            self.pan = PanControl("Pan", 0)
            self.pan.connect(self.on_pan_change)
            self.pan_layout.addWidget(self.pan)

    def on_pan_change(self, _):
        val = self.pan.get_value()
        if self.linked:
            # Only call ALSA for main outs (pair), not crosspoints
            alsa_backend.set_crosspoint_volume(
                self.crosspoints.get('L->R'), self.crosspoints.get('R->L'),
                self.crosspoints.get('L->L'), self.crosspoints.get('R->R'),
                val, True
            )
        else:
            # Call ALSA for both main and cross (true panning for the strip)
            alsa_backend.set_crosspoint_volume(
                self.crosspoints.get('L->R'), self.crosspoints.get('R->L'),
                self.crosspoints.get('L->L'), self.crosspoints.get('R->R'),
                (val, val), False
            )

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

class StereoPairStrip(QWidget):
    def __init__(self, lname, rname, functions=None, parent=None):
        super().__init__(parent)
        self.linked = True  # Default to stereo linked

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

        hpair.addWidget(self.left_strip)
        hpair.addWidget(self.right_strip)
        layout.addLayout(hpair)

        # --- Link button for the pair ---
        self.link_btn = QPushButton("🔗")
        self.link_btn.setCheckable(True)
        self.link_btn.setChecked(self.linked)
        self.link_btn.setToolTip("Stereo Link: Move both faders together")
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
                background-color: #87ceeb !important;
                color: black !important;
            }
        """)
        self.link_btn.clicked.connect(self.on_link_clicked)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.link_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.setLayout(layout)

        # --- Connect fader changes for linking ---
        self.left_strip.fader.slider.valueChanged.connect(self._left_fader_moved)
        self.right_strip.fader.slider.valueChanged.connect(self._right_fader_moved)

    def on_link_clicked(self, checked):
        self.linked = checked
        # Update ChannelStrips to match link state (also update pan control)
        self.left_strip.linked = checked
        self.right_strip.linked = checked
        self.left_strip.setup_pan_widgets()
        self.right_strip.setup_pan_widgets()

    def _left_fader_moved(self, value):
        if self.linked and self.right_strip.fader.slider.value() != value:
            self.right_strip.fader.slider.blockSignals(True)
            self.right_strip.fader.slider.setValue(value)
            self.right_strip.fader.slider.blockSignals(False)
            self.right_strip.set_alsa_value(value)  # also update ALSA for R channel
            self.right_strip.db_label.setText(f"{value}")

    def _right_fader_moved(self, value):
        if self.linked and self.left_strip.fader.slider.value() != value:
            self.left_strip.fader.slider.blockSignals(True)
            self.left_strip.fader.slider.setValue(value)
            self.left_strip.fader.slider.blockSignals(False)
            self.left_strip.set_alsa_value(value)  # also update ALSA for L channel
            self.left_strip.db_label.setText(f"{value}")


class MixerGroupWidget(QWidget):
    def __init__(self, group_name, pair_list, func_map, parent=None):
        super().__init__(parent)
        # ... existing label and fader layout ...
        v_layout = QVBoxLayout()
        v_layout.setSpacing(8)
        v_layout.setContentsMargins(0, 0, 0, 0)

        # Group label as before...
        lbl = QLabel(group_name)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Inter", 11, QFont.Weight.Normal))
        lbl.setStyleSheet(f"color:{Colors['text_light'].name()}; padding: 4px;")
        v_layout.addWidget(lbl)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(12)
        for l, r in pair_list:
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
