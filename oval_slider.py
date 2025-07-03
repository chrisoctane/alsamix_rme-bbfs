from PyQt6.QtWidgets import QSlider, QStyleOptionSlider
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QRectF

class OvalGrooveSlider(QSlider):
    def __init__(self, orientation, handle_color="#3f7fff", groove_color="#222", parent=None):
        super().__init__(orientation, parent)
        self.handle_color = handle_color
        self.groove_color = groove_color
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def wheelEvent(self, event):
        # Consistent shift+wheel for fine increments, else normal step
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            step = 1
        else:
            step = 5
        num_steps = event.angleDelta().y() // 120
        if num_steps != 0:
            new_value = self.value() + num_steps * step
            new_value = max(self.minimum(), min(self.maximum(), new_value))
            self.setValue(new_value)
            event.accept()
        else:
            super().wheelEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        handle_size = 16
        if self.orientation() == Qt.Orientation.Vertical:
            groove_w = 16
            groove_h = self.height() - 12
            groove_x = (self.width() - groove_w) // 2
            groove_y = 6
            groove_rect = QRectF(groove_x, groove_y, groove_w, groove_h)
            radius = groove_w / 2
            slider_min = groove_y
            slider_max = groove_y + groove_h - handle_size
            val = (self.maximum() - self.value()) / (self.maximum() - self.minimum()) if self.maximum() != self.minimum() else 0
            handle_y = slider_min + val * (slider_max - slider_min)
            handle_x = (self.width() - handle_size) // 2
            handle_rect = QRectF(handle_x, handle_y, handle_size, handle_size)
        else:
            groove_h = 16
            groove_w = self.width() - 20
            groove_x = 10
            groove_y = (self.height() - groove_h) // 2
            groove_rect = QRectF(groove_x, groove_y, groove_w, groove_h)
            radius = groove_h / 2
            slider_min = groove_x
            slider_max = groove_x + groove_w - handle_size
            val = (self.value() - self.minimum()) / (self.maximum() - self.minimum()) if self.maximum() != self.minimum() else 0
            handle_x = slider_min + val * (slider_max - slider_min)
            handle_y = (self.height() - handle_size) // 2
            if handle_y + handle_size > self.height():
                handle_y = self.height() - handle_size
            if handle_y < 0:
                handle_y = 0
            handle_rect = QRectF(handle_x, handle_y, handle_size, handle_size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.groove_color))
        painter.drawRoundedRect(groove_rect, radius, radius)
        painter.setBrush(QColor(self.handle_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(handle_rect)
        if not self.isEnabled():
            painter.setBrush(QColor(0, 0, 0, 80))
            painter.drawEllipse(handle_rect)
        painter.end() 