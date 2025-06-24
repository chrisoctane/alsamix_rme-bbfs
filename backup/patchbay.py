import sys
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsWidget, QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem
)
from PyQt6.QtGui import QBrush, QColor, QPen, QFont, QPainter, QFontMetrics
from PyQt6.QtCore import Qt, QRectF, QTimer

import alsa_backend
from alsaaudio import Mixer


class PatchbayChannel(QGraphicsWidget):
    WIDTH = 210
    HEIGHT = 170
    HANDLE_WIDTH = 24
    HANDLE_COLOR = QColor("#aaa")
    HANDLE_TEXT_COLOR = QColor("#FFD700")
    FADER_BAR_WIDTH = 28
    OUTPUT_LABEL_COLOR = QColor("#18192b")  # dark, for outputs
    NONFADER_LABEL_COLOR = QColor("#ffc9c9")  # slightly darker pastel red
    FADER_LABEL_COLOR = QColor("#394050")
    LABEL_RADIUS = 10

    def __init__(self, ctl_name, mixer, show_fader=True):
        super().__init__()
        self.ctl_name = ctl_name
        self.mixer = mixer
        self.is_output = ctl_name.startswith("Main-Out") or ctl_name.startswith("OUT")
        self.is_nonfader = not show_fader

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1)
        self.setGeometry(QRectF(0, 0, self.WIDTH, self.HEIGHT))

        label_bar_height = 32

        # Drag handle: fills from top to bottom, flush with label background
        self.handle_rect = QGraphicsRectItem(0, 0, self.HANDLE_WIDTH, self.HEIGHT, self)
        self.handle_rect.setBrush(QBrush(self.HANDLE_COLOR))
        self.handle_rect.setPen(QPen(Qt.PenStyle.NoPen))
        self.handle_rect.setZValue(1)

        # Label color selection
        if self.is_output:
            label_color = self.OUTPUT_LABEL_COLOR
        elif self.is_nonfader:
            label_color = self.NONFADER_LABEL_COLOR
        else:
            label_color = self.FADER_LABEL_COLOR

        self.label_bg_item = QGraphicsRectItem(self.HANDLE_WIDTH, 0, self.WIDTH - self.HANDLE_WIDTH, label_bar_height, self)
        self.label_bg_item.setBrush(QBrush(label_color))
        self.label_bg_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.label_bg_item.setZValue(-1)

        # SINGLE-LINE, ELIDED, CENTERED LABEL
        label_font = QFont("Sans", 10, QFont.Weight.Medium)
        self.label = QGraphicsTextItem(self)
        self.label.setFont(label_font)
        if self.is_nonfader:
            self.label.setDefaultTextColor(QColor("#2b2222"))
        else:
            self.label.setDefaultTextColor(QColor("#FFE066"))
        fm = QFontMetrics(label_font)
        max_label_width = self.WIDTH - self.HANDLE_WIDTH - 10  # 10px margin
        safe_text = ctl_name.replace('\n', ' ')
        elided = fm.elidedText(safe_text, Qt.TextElideMode.ElideRight, max_label_width)
        self.label.setPlainText(elided)
        label_bounding = self.label.boundingRect()
        label_x = self.HANDLE_WIDTH + (self.WIDTH - self.HANDLE_WIDTH - label_bounding.width()) / 2
        label_y = (label_bar_height - label_bounding.height()) / 2
        self.label.setPos(label_x, label_y)

        self.handle_text = QGraphicsTextItem("⠿", self)
        self.handle_text.setDefaultTextColor(self.HANDLE_TEXT_COLOR)
        self.handle_text.setFont(QFont("Sans", 16))
        handle_text_bbox = self.handle_text.boundingRect()
        handle_text_x = self.HANDLE_WIDTH/2 - handle_text_bbox.width()/2
        handle_text_y = self.HEIGHT/2 - handle_text_bbox.height()/2
        self.handle_text.setPos(handle_text_x, handle_text_y)
        self.handle_text.setZValue(2)

        self.show_fader = show_fader
        self.fader_value = 0
        try:
            self.fader_value = mixer.getvolume()[0]
        except Exception:
            pass

        if self.show_fader:
            # Fader: centered horizontally after handle
            fader_x = self.HANDLE_WIDTH + (self.WIDTH - self.HANDLE_WIDTH - self.FADER_BAR_WIDTH) / 2
            self.fader_bg = QGraphicsRectItem(fader_x, label_bar_height + 8, self.FADER_BAR_WIDTH, 110, self)
            self.fader_bg.setBrush(QBrush(QColor("#222")))
            self.fader_bg.setPen(QPen(QColor("#444")))

            # Fader bar with 50% opacity, rounded corners
            blue = QColor("#3f7fff")
            blue.setAlphaF(0.5)  # 50% opacity
            fader_val_y = label_bar_height + 8 + 107 * (1 - self.fader_value / 100)
            self.fader_bar = QGraphicsRectItem(
                fader_x, fader_val_y, self.FADER_BAR_WIDTH, 3 + 107 * (self.fader_value / 100), self)
            self.fader_bar.setBrush(QBrush(blue))
            self.fader_bar.setPen(QPen(Qt.PenStyle.NoPen))
            self.fader_bar.setZValue(2)
        else:
            self.fader_bg = None
            self.fader_bar = None

        # Value text centered at bottom, under fader or under label
        value_font = QFont("Sans", 9)
        self.value_text = QGraphicsTextItem(str(int(self.fader_value)), self)
        self.value_text.setFont(value_font)
        self.value_text.setDefaultTextColor(QColor("#555" if self.is_nonfader else "#fff"))
        if self.show_fader:
            self.value_text.setTextWidth(self.FADER_BAR_WIDTH)
            self.value_text.setPos(
                fader_x,
                self.fader_bg.rect().bottom() + 4
            )
        else:
            self.value_text.setTextWidth(self.WIDTH)
            self.value_text.setPos(0, self.HEIGHT - 28)

    def wheelEvent(self, event):
        if not self.show_fader:
            return
        steps = event.delta() // 120
        modifiers = event.modifiers()
        fine = 1 if modifiers & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier) else 5
        new_value = min(max(self.fader_value + steps * fine, 0), 100)
        self.fader_value = new_value
        self.updateFader()
        try:
            self.mixer.setvolume(int(self.fader_value))
        except Exception:
            pass
        event.accept()

    def updateFader(self):
        if self.fader_bar is not None:
            label_bar_height = 32
            fader_x = self.HANDLE_WIDTH + (self.WIDTH - self.HANDLE_WIDTH - self.FADER_BAR_WIDTH) / 2
            self.fader_bar.setRect(
                fader_x,
                label_bar_height + 8 + 107 * (1 - self.fader_value / 100),
                self.FADER_BAR_WIDTH,
                3 + 107 * (self.fader_value / 100)
            )
            self.value_text.setPos(self.fader_bg.rect().left(), self.fader_bg.rect().bottom() + 4)
        self.value_text.setPlainText(str(int(self.fader_value)))

    def paint(self, painter, option, widget):
        # Draw rounded channel outline if selected
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isSelected():
            pen = QPen(QColor("#FFD700"), 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = self.boundingRect()
            painter.drawRoundedRect(r, 12, 12)
        super().paint(painter, option, widget)

class PatchbayView(QGraphicsView):
    def __init__(self, card_index):
        super().__init__()
        self.card = card_index
        self.scene = QGraphicsScene(0, 0, 1800, 2000)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.items = []
        self.scene.view = self
        self.populate_items()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_from_alsa)
        self.timer.start(300)
        self._panning = False
        self._zoom = 1.0

    def populate_items(self):
        self.scene.clear()
        self.items = []
        self.scene.view = self

        controls = alsa_backend.list_mixer_controls(self.card)
        specials = ["Emphasis", "Mask", "PAD", "48V", "Sens.", "Sample Clock", "IEC958"]
        x, y = 0, 0
        for ctl in controls:
            mix = Mixer(control=ctl, cardindex=self.card)
            try:
                val = mix.getvolume()[0]
            except Exception:
                val = None

            show_fader = (
                val is not None and val != 137578
                and not any(kw in ctl for kw in specials)
            )
            item = PatchbayChannel(ctl, mix, show_fader=show_fader)
            item.setPos(x, y)
            x += PatchbayChannel.WIDTH + 24
            if x > (PatchbayChannel.WIDTH + 24) * 8:
                x = 0
                y += PatchbayChannel.HEIGHT + 16
            self.scene.addItem(item)
            self.items.append(item)
        self.update_scene_rect()

    def update_scene_rect(self):
        """Set scene rectangle to fit all items with a margin."""
        rect = self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
        self.scene.setSceneRect(rect)

    def sync_from_alsa(self):
        for it in self.items:
            try:
                alsa_val = it.mixer.getvolume()[0]
                if int(it.fader_value) != alsa_val:
                    it.fader_value = alsa_val
                    it.updateFader()
            except Exception:
                pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)
        self.update_scene_rect()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom *= 1.1
            else:
                self._zoom /= 1.1
            self.resetTransform()
            self.scale(self._zoom, self._zoom)
            event.accept()
        else:
            super().wheelEvent(event)
