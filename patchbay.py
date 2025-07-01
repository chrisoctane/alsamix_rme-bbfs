import sys
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsWidget, QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem,
    QSlider, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QGraphicsProxyWidget
)
from PyQt6.QtGui import QBrush, QColor, QPen, QFont, QPainter, QFontMetrics
from PyQt6.QtCore import Qt, QRectF, QTimer, QPointF

import alsa_backend
from alsaaudio import Mixer
import math
from config import *


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

        # Grouping functionality
        self.snapped_blocks = set()
        self.is_snap_target = False

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
            
        # Check if mouse is over the fader area
        pos = event.pos()
        fader_rect = self.fader_bg.rect()
        if not fader_rect.contains(pos):
            # Mouse is not over the fader, ignore the event
            event.ignore()
            return
            
        steps = event.delta() // 120
        modifiers = event.modifiers()
        fine = 1 if modifiers & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier) else 5
        new_value = min(max(self.fader_value + steps * fine, 0), 100)
        self.fader_value = new_value
        self.updateFader()
        
        # Update group controls if in a group
        self._update_group_controls_from_fader()
        
        event.accept()
        
    def _update_group_controls_from_fader(self):
        """Update group controls (crossfader, macro) when individual fader changes."""
        if len(self.snapped_blocks) == 0:
            return
            
        # Find the group container
        scene = self.scene()
        if not scene:
            return
            
        for item in scene.items():
            if hasattr(item, 'blocks') and self in item.blocks:
                # This is our group container
                if hasattr(item, '_on_individual_fader_changed'):
                    item._on_individual_fader_changed(self)
                break

    def updateFader(self, skip_change_event=False):
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
        
        # Update ALSA if not skipping change event
        if not skip_change_event:
            try:
                self.mixer.setvolume(int(self.fader_value))
            except Exception:
                pass

    def paint(self, painter, option, widget):
        # Draw rounded channel outline if selected
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isSelected():
            pen = QPen(QColor("#FFD700"), 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = self.boundingRect()
            painter.drawRoundedRect(r, 12, 12)
        elif self.is_snap_target:
            # Draw snap target highlighting
            pen = QPen(QColor("#FFD700"), 3, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = self.boundingRect()
            painter.drawRoundedRect(r, 12, 12)
        super().paint(painter, option, widget)

    def add_to_group(self, other_block):
        """Add this block to a group with another block."""
        if other_block not in self.snapped_blocks:
            self.snapped_blocks.add(other_block)
            other_block.snapped_blocks.add(self)

    def remove_from_group(self, other_block):
        """Remove this block from a group with another block."""
        self.snapped_blocks.discard(other_block)
        other_block.snapped_blocks.discard(self)

    def get_all_grouped_blocks(self):
        """Get all blocks in the same group as this block."""
        if not self.snapped_blocks:
            return {self}
        
        visited = set()
        to_visit = {self}
        group = set()
        
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            group.add(current)
            to_visit.update(current.snapped_blocks - visited)
        
        return group

    def update_group_state(self):
        """Update the visual state based on group membership."""
        if self.snapped_blocks:
            self.setZValue(2)
        else:
            self.setZValue(1)
            
    def mousePressEvent(self, event):
        """Handle mouse press events for fader interaction."""
        if not self.show_fader:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            fader_rect = self.fader_bg.rect()
            if fader_rect.contains(pos):
                self._handle_fader_click(pos.y() - fader_rect.y())
                # Update group controls if in a group
                self._update_group_controls_from_fader()
        super().mousePressEvent(event)
        
    def _handle_fader_click(self, y_offset):
        """Handle fader click to set volume."""
        fader_height = 107  # Height of the fader area
        value = max(0, min(100, (fader_height - y_offset) / fader_height * 100))
        self.fader_value = value
        self.updateFader()


class GroupContainer(QGraphicsWidget):
    """Container widget that holds grouped channels and manages their movement together."""
    HANDLE_WIDTH = GROUP_HANDLE_WIDTH
    HANDLE_COLOR = GROUP_HANDLE_COLOR
    HANDLE_HOVER_COLOR = GROUP_HANDLE_HOVER_COLOR
    HANDLE_TEXT_COLOR = GROUP_HANDLE_TEXT_COLOR
    CORNER_RADIUS = GROUP_CORNER_RADIUS
    OUTLINE_COLOR = GROUP_OUTLINE_COLOR
    OUTLINE_WIDTH = GROUP_OUTLINE_WIDTH

    def __init__(self, blocks, parent=None):
        super().__init__(parent)
        self.blocks = list(blocks)
        self._block_offsets = {}
        self._updating_controls = False
        self.macro_fader_value = None
        
        # Setup graphics item
        self.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(10)
        
        # Setup layout and controls
        self._setup_layout()
        self._setup_controls()
        
        # Only create crossfader and macro fader for 2-block groups
        if len(self.blocks) == 2:
            self._setup_crossfader()
            self._setup_macro_fader()

    def _setup_layout(self):
        """Calculate bounding rect and store block offsets."""
        if not self.blocks:
            print("[ERROR] No blocks provided to GroupContainer")
            return
            
        try:
            # Check if all blocks are still in the scene
            for block in self.blocks:
                if not block.scene():
                    print(f"[ERROR] Block {block.ctl_name} not in scene")
                    return
                    
            min_x = min(block.pos().x() for block in self.blocks)
            min_y = min(block.pos().y() for block in self.blocks)
            self.setPos(min_x - self.HANDLE_WIDTH, min_y)
            
            print(f"[DEBUG] Group container positioned at {self.pos()}")
            
            # Store initial block positions relative to the group
            content_start_x = self.pos().x() + self.HANDLE_WIDTH
            for block in self.blocks:
                offset = block.pos() - QPointF(content_start_x, self.pos().y())
                self._block_offsets[block] = offset
                # Lock the blocks in place and hide grab handles
                block.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsMovable, False)
                block.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsSelectable, False)
                block.setZValue(0)
                
                # Hide the grab handle for grouped blocks
                if hasattr(block, 'handle_rect'):
                    block.handle_rect.setVisible(False)
                if hasattr(block, 'handle_text'):
                    block.handle_text.setVisible(False)
            
            # Calculate group size
            group_width = sum(block.WIDTH for block in self.blocks) + (len(self.blocks)-1)*10
            group_height = max(block.HEIGHT for block in self.blocks)
            self.setGeometry(QRectF(0, 0, group_width + self.HANDLE_WIDTH + 50, group_height + 80))
            
            print(f"[DEBUG] Group container geometry: {self.geometry()}")
            
            # Position blocks within the group
            self._update_block_positions()
            
        except Exception as e:
            print(f"[ERROR] Failed to setup group layout: {e}")
            raise
        
    def _update_block_positions(self):
        """Update all block positions to match the group container."""
        content_start_x = self.pos().x() + self.HANDLE_WIDTH
        for block in self.blocks:
            if block in self._block_offsets:
                new_block_pos = content_start_x + self._block_offsets[block].x()
                new_block_pos_y = self.pos().y() + self._block_offsets[block].y()
                block.setPos(new_block_pos, new_block_pos_y)

    def _setup_controls(self):
        pass

    def _setup_crossfader(self):
        if len(self.blocks) != 2:
            return
        self.crossfader = QSlider(Qt.Orientation.Horizontal)
        self.crossfader.setRange(0, 100)
        self.crossfader.setValue(50)
        self.crossfader.setFixedSize(120, 20)
        self.crossfader.setStyleSheet("""
            QSlider::groove:horizontal { background: #222; height: 8px; border-radius: 4px; }
            QSlider::handle:horizontal { background: #3f7fff; width: 16px; height: 16px; margin: -4px 0; border-radius: 8px; }
        """)
        self.crossfader_proxy = QGraphicsProxyWidget(self)
        self.crossfader_proxy.setWidget(self.crossfader)
        # Center the crossfader horizontally
        crossfader_x = (self.geometry().width() - 120) / 2
        crossfader_y = self.geometry().height() - 60
        self.crossfader_proxy.setPos(crossfader_x, crossfader_y)
        self.crossfader.valueChanged.connect(self._on_crossfader_changed)
        self.crossfader_label = QGraphicsTextItem("Crossfader", self)
        self.crossfader_label.setFont(QFont("Sans", 8))
        self.crossfader_label.setDefaultTextColor(QColor("#fff"))
        self.crossfader_label.setPos(crossfader_x, crossfader_y - 15)

    def _setup_macro_fader(self):
        if len(self.blocks) != 2:
            return
        self.macro_fader = QSlider(Qt.Orientation.Vertical)
        self.macro_fader.setRange(0, 100)
        self.macro_fader.setValue(100)
        self.macro_fader.setFixedSize(20, 80)
        self.macro_fader.setStyleSheet("""
            QSlider::groove:vertical { background: #222; width: 8px; border-radius: 4px; }
            QSlider::handle:vertical { background: #ff3f7f; height: 10px; width: 16px; margin: 0 -4px; border-radius: 3px; }
        """)
        self.macro_proxy = QGraphicsProxyWidget(self)
        self.macro_proxy.setWidget(self.macro_fader)
        # Position macro fader on the right side, centered vertically
        macro_x = self.geometry().width() - 30  # 30 pixels from right edge
        macro_y = (self.geometry().height() - 80) / 2  # Center vertically
        self.macro_proxy.setPos(macro_x, macro_y)
        self.macro_fader.valueChanged.connect(self._on_macro_fader_changed)
        self.macro_fader_value = 100
        self.macro_label = QGraphicsTextItem("Macro", self)
        self.macro_label.setFont(QFont("Sans", 8))
        self.macro_label.setDefaultTextColor(QColor("#fff"))
        self.macro_label.setPos(macro_x - 5, macro_y + 85)

    def _on_macro_fader_changed(self, value):
        if len(self.blocks) == 2 and not self._updating_controls:
            self._updating_controls = True
            self.macro_fader_value = value
            try:
                # Get current crossfader position
                crossfader_pos = 50
                if self.crossfader:
                    crossfader_pos = self.crossfader.value()
                
                # Calculate pan ratios (constant-power law)
                pan = crossfader_pos / 100.0
                left_ratio = math.cos(pan * math.pi / 2)
                right_ratio = math.sin(pan * math.pi / 2)
                
                # Apply macro level while preserving pan relationship
                left_volume = int(value * left_ratio)
                right_volume = int(value * right_ratio)
                left_volume = min(max(left_volume, 0), 100)
                right_volume = min(max(right_volume, 0), 100)
                
                # Update left block
                if hasattr(self.blocks[0], 'fader_value'):
                    self.blocks[0].fader_value = left_volume
                    self.blocks[0].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[0], 'mixer'):
                        self.blocks[0].mixer.setvolume(left_volume)
                
                # Update right block
                if hasattr(self.blocks[1], 'fader_value'):
                    self.blocks[1].fader_value = right_volume
                    self.blocks[1].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[1], 'mixer'):
                        self.blocks[1].mixer.setvolume(right_volume)
                        
            except Exception as e:
                print(f"Macro fader update failed: {e}")
            finally:
                self._updating_controls = False

    def _on_crossfader_changed(self, value):
        if len(self.blocks) == 2 and not self._updating_controls:
            self._updating_controls = True
            try:
                # Calculate pan ratios (constant-power law)
                pan = value / 100.0
                macro_level = self.macro_fader_value if self.macro_fader_value is not None else 100
                left_ratio = math.cos(pan * math.pi / 2)
                right_ratio = math.sin(pan * math.pi / 2)
                
                # Apply crossfader while respecting macro level
                left_volume = int(macro_level * left_ratio)
                right_volume = int(macro_level * right_ratio)
                left_volume = min(max(left_volume, 0), 100)
                right_volume = min(max(right_volume, 0), 100)
                
                # Update left block
                if hasattr(self.blocks[0], 'fader_value'):
                    self.blocks[0].fader_value = left_volume
                    self.blocks[0].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[0], 'mixer'):
                        self.blocks[0].mixer.setvolume(left_volume)
                
                # Update right block
                if hasattr(self.blocks[1], 'fader_value'):
                    self.blocks[1].fader_value = right_volume
                    self.blocks[1].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[1], 'mixer'):
                        self.blocks[1].mixer.setvolume(right_volume)
                        
            except Exception as e:
                print(f"Crossfader update failed: {e}")
            finally:
                self._updating_controls = False

    def _on_individual_fader_changed(self, changed_block):
        if len(self.blocks) != 2 or self._updating_controls:
            return
        self._updating_controls = True
        try:
            left_current = self.blocks[0].fader_value
            right_current = self.blocks[1].fader_value
            total_volume = left_current + right_current
            if total_volume > 0:
                crossfader_pos = int((right_current / total_volume) * 100)
            else:
                crossfader_pos = 50
            if self.crossfader:
                self.crossfader.blockSignals(True)
                self.crossfader.setValue(int(crossfader_pos))
                self.crossfader.blockSignals(False)
            if self.macro_fader:
                self.macro_fader.blockSignals(True)
                self.macro_fader.setValue(int(total_volume))
                self.macro_fader.blockSignals(False)
                self.macro_fader_value = int(total_volume)
        except Exception as e:
            print(f"Individual fader update failed: {e}")
        finally:
            self._updating_controls = False

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        pen = QPen(self.OUTLINE_COLOR, self.OUTLINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawRoundedRect(self.boundingRect(), self.CORNER_RADIUS, self.CORNER_RADIUS)
        handle_rect = QRectF(0, 0, self.HANDLE_WIDTH, self.geometry().height())
        painter.setBrush(QBrush(self.HANDLE_COLOR))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(handle_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
        painter.setPen(QPen(self.HANDLE_TEXT_COLOR))
        painter.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        painter.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, "G")

    def hoverMoveEvent(self, event):
        handle_rect = QRectF(0, 0, self.HANDLE_WIDTH, self.geometry().height())
        if handle_rect.contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        handle_rect = QRectF(0, 0, self.HANDLE_WIDTH, self.geometry().height())
        if handle_rect.contains(event.pos()):
            print(f"Group handle pressed at {event.pos()}")
            # Store the initial position for dragging
            self._drag_start_pos = event.scenePos()
            self._drag_start_group_pos = self.pos()
            # Set dragging flag to prevent group recreation
            if hasattr(self.scene(), 'view'):
                self.scene().view._dragging_group = True
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_start_pos'):
            # Calculate the movement delta in scene coordinates
            delta = event.scenePos() - self._drag_start_pos
            new_pos = self._drag_start_group_pos + delta
            
            print(f"Moving group from {self.pos()} to {new_pos}")
            
            # Move the group container
            self.setPos(new_pos)
            
            # Update all block positions to follow the group
            self._update_block_positions()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # Clean up drag state
        if hasattr(self, '_drag_start_pos'):
            delattr(self, '_drag_start_pos')
        if hasattr(self, '_drag_start_group_pos'):
            delattr(self, '_drag_start_group_pos')
        # Clear dragging flag
        if hasattr(self.scene(), 'view'):
            self.scene().view._dragging_group = False
        super().mouseReleaseEvent(event)

    def cleanup(self):
        """Restore blocks to their original state when group is destroyed."""
        for block in self.blocks:
            # Restore grab handles
            if hasattr(block, 'handle_rect'):
                block.handle_rect.setVisible(True)
            if hasattr(block, 'handle_text'):
                block.handle_text.setVisible(True)
            
            # Restore movement and selection
            block.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsMovable, True)
            block.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsSelectable, True)
            block.setZValue(1)


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
        
        # Group management
        self.group_containers = []
        
        # Snap settings
        self.SNAP_THRESHOLD = 20
        self.SNAP_ALIGN_THRESHOLD = 30
        self.MIN_ORTHOGONAL_OVERLAP = 10
        
        self.populate_items()
        # Don't start timer automatically - let the parent control polling
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
        self.clear_snap_highlighting()

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)
        
        # Update snap highlighting for selected items
        for item in self.scene.selectedItems():
            if isinstance(item, PatchbayChannel):
                self.update_snap_highlighting(item)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)
        
        # Check for snapping opportunities
        for item in self.scene.selectedItems():
            if isinstance(item, PatchbayChannel):
                self.check_for_snapping(item)
        
        # Only update group widgets if we're not currently dragging a group
        # This prevents groups from snapping back to their original position
        if not hasattr(self, '_dragging_group'):
            self.update_group_widgets()
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

    def check_for_snapping(self, dragged_item):
        """Check for snapping opportunities and apply them."""
        candidates = self.get_snap_candidates(dragged_item)
        
        for candidate in candidates:
            if candidate not in dragged_item.snapped_blocks:
                # Snap the items together
                dragged_item.add_to_group(candidate)
                dragged_item.update_group_state()
                candidate.update_group_state()
                
                # Don't update group widgets here - let mouseReleaseEvent handle it
                break

    def get_snap_candidates(self, dragged_item):
        """Get potential snap candidates for the dragged item."""
        candidates = []
        dragged_rect = dragged_item.boundingRect()
        dragged_pos = dragged_item.pos()
        
        for item in self.scene.items():
            if not isinstance(item, PatchbayChannel) or item == dragged_item:
                continue
                
            candidate_rect = item.boundingRect()
            candidate_pos = item.pos()
            
            # Check if items are close enough to snap
            if self._can_snap(dragged_rect, dragged_pos, candidate_rect, candidate_pos):
                candidates.append(item)
                
        return candidates

    def _can_snap(self, rect1, pos1, rect2, pos2):
        """Check if two rectangles can snap together."""
        # Calculate centers
        center1 = pos1 + rect1.center()
        center2 = pos2 + rect2.center()
        
        # Check horizontal snap
        if abs(center1.x() - center2.x()) < self.SNAP_ALIGN_THRESHOLD:
            # Check vertical overlap
            y1_min, y1_max = pos1.y(), pos1.y() + rect1.height()
            y2_min, y2_max = pos2.y(), pos2.y() + rect2.height()
            
            overlap = min(y1_max, y2_max) - max(y1_min, y2_min)
            if overlap > self.MIN_ORTHOGONAL_OVERLAP:
                return True
                
        # Check vertical snap
        if abs(center1.y() - center2.y()) < self.SNAP_ALIGN_THRESHOLD:
            # Check horizontal overlap
            x1_min, x1_max = pos1.x(), pos1.x() + rect1.width()
            x2_min, x2_max = pos2.x(), pos2.x() + rect2.width()
            
            overlap = min(x1_max, x2_max) - max(x1_min, x2_min)
            if overlap > self.MIN_ORTHOGONAL_OVERLAP:
                return True
                
        return False

    def update_snap_highlighting(self, dragged_item):
        """Update snap highlighting for the dragged item."""
        self.clear_snap_highlighting()
        
        candidates = self.get_snap_candidates(dragged_item)
        for candidate in candidates:
            candidate.is_snap_target = True
            candidate.update()

    def clear_snap_highlighting(self):
        """Clear all snap highlighting."""
        for item in self.scene.items():
            if isinstance(item, PatchbayChannel):
                item.is_snap_target = False
                item.update()

    def clear_group_widgets(self):
        """Clear all group containers."""
        for container in self.group_containers:
            # Clean up the container to restore blocks to their original state
            container.cleanup()
            self.scene.removeItem(container)
        self.group_containers.clear()

    def update_group_widgets(self):
        """Update group containers based on current block groupings."""
        self.clear_group_widgets()
        self.create_group_containers()

    def create_group_containers(self):
        """Create group containers for snapped blocks."""
        processed_blocks = set()
        created_groups = 0
        
        print(f"[DEBUG] Starting group container creation. Total items in scene: {len(self.scene.items())}")
        
        for item in self.scene.items():
            if not isinstance(item, PatchbayChannel):
                continue
                
            if item in processed_blocks:
                continue
                
            # Get all blocks in this group
            group_blocks = item.get_all_grouped_blocks()
            
            # Only create containers for groups with 2+ blocks
            if len(group_blocks) >= 2:
                # Check if any blocks in this group are already processed
                if any(block in processed_blocks for block in group_blocks):
                    print(f"[DEBUG] Skipping group - some blocks already processed")
                    continue
                    
                print(f"Creating group container for {len(group_blocks)} blocks")
                try:
                    # Create group container
                    container = GroupContainer(group_blocks)
                    self.scene.addItem(container)
                    self.group_containers.append(container)
                    
                    # Mark all blocks as processed
                    processed_blocks.update(group_blocks)
                    created_groups += 1
                    print(f"[SUCCESS] Group container created for {len(group_blocks)} blocks")
                except Exception as e:
                    print(f"[ERROR] Failed to create GroupContainer: {e}")
                    # Don't mark blocks as processed if container creation failed
        
        print(f"[DEBUG] Group container creation complete. Created {created_groups} groups, processed {len(processed_blocks)} blocks")
