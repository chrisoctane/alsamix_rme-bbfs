"""
GroupContainer - Container widget for grouped channels with crossfader and macro controls.
"""

import math
from PyQt6.QtWidgets import QGraphicsWidget, QGraphicsRectItem, QGraphicsTextItem, QGraphicsProxyWidget, QSlider
from PyQt6.QtGui import QBrush, QColor, QPen, QFont, QPainter
from PyQt6.QtCore import Qt, QRectF, QPointF
from config import *


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
            return
            
        min_x = min(block.pos().x() for block in self.blocks)
        min_y = min(block.pos().y() for block in self.blocks)
        self.setPos(min_x - self.HANDLE_WIDTH, min_y)
        
        content_start_x = self.pos().x() + self.HANDLE_WIDTH
        for block in self.blocks:
            offset = block.pos() - QPointF(content_start_x, self.pos().y())
            self._block_offsets[block] = offset
            block.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsMovable, False)
            block.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsSelectable, False)
            block.setZValue(0)
        
        group_width = sum(block.WIDTH for block in self.blocks) + (len(self.blocks)-1)*10
        group_height = max(block.HEIGHT for block in self.blocks)
        self.setGeometry(QRectF(0, 0, group_width + self.HANDLE_WIDTH + 50, group_height + 80))
        
        # Immediately update block positions to match container layout
        for block in self.blocks:
            new_block_pos = self.pos() + QPointF(self.HANDLE_WIDTH, 0) + self._block_offsets[block]
            block.setPos(new_block_pos)

    def _setup_controls(self):
        """Setup basic group controls."""
        pass

    def _setup_crossfader(self):
        """Setup crossfader control for 2-block groups."""
        if len(self.blocks) != 2:
            return
            
        # Create crossfader slider
        self.crossfader = QSlider(Qt.Orientation.Horizontal)
        self.crossfader.setRange(0, 100)
        self.crossfader.setValue(50)  # Center position
        self.crossfader.setFixedSize(120, 20)
        self.crossfader.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #222;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3f7fff;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
        """)
        
        # Create proxy widget
        self.crossfader_proxy = QGraphicsProxyWidget(self)
        self.crossfader_proxy.setWidget(self.crossfader)
        crossfader_x = self.geometry().width() - 130
        crossfader_y = self.geometry().height() - 60
        self.crossfader_proxy.setPos(crossfader_x, crossfader_y)
        
        # Connect crossfader
        self.crossfader.valueChanged.connect(self._on_crossfader_changed)
        
        # Crossfader label
        self.crossfader_label = QGraphicsTextItem("Crossfader", self)
        self.crossfader_label.setFont(QFont("Sans", 8))
        self.crossfader_label.setDefaultTextColor(QColor("#fff"))
        label_bbox = self.crossfader_label.boundingRect()
        self.crossfader_label.setPos(crossfader_x, crossfader_y - 15)

    def _setup_macro_fader(self):
        """Setup macro fader control for 2-block groups."""
        if len(self.blocks) != 2:
            return
            
        # Create macro fader slider
        self.macro_fader = QSlider(Qt.Orientation.Vertical)
        self.macro_fader.setRange(0, 100)
        self.macro_fader.setValue(100)  # Full volume
        self.macro_fader.setFixedSize(20, 80)
        self.macro_fader.setStyleSheet("""
            QSlider::groove:vertical {
                background: #222;
                width: 8px;
                border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: #ff3f7f;
                height: 10px;
                width: 16px;
                margin: 0 -4px;
                border-radius: 3px;
            }
        """)
        
        # Create proxy widget
        self.macro_proxy = QGraphicsProxyWidget(self)
        self.macro_proxy.setWidget(self.macro_fader)
        macro_x = self.geometry().width() - 30
        macro_y = 10
        self.macro_proxy.setPos(macro_x, macro_y)
        
        # Connect macro fader
        self.macro_fader.valueChanged.connect(self._on_macro_fader_changed)
        self.macro_fader_value = 100
        
        # Macro fader label
        self.macro_label = QGraphicsTextItem("Macro", self)
        self.macro_label.setFont(QFont("Sans", 8))
        self.macro_label.setDefaultTextColor(QColor("#fff"))
        label_bbox = self.macro_label.boundingRect()
        self.macro_label.setPos(macro_x - 5, macro_y + 85)

    def _on_macro_fader_changed(self, value):
        """Handle macro fader value changes."""
        if len(self.blocks) == 2 and not self._updating_controls:
            self._updating_controls = True
            self.macro_fader_value = value
            
            try:
                crossfader_pos = 50  # Default center
                if self.crossfader:
                    crossfader_pos = self.crossfader.value()
                    
                # Constant-power crossfade law
                pan = crossfader_pos / 100.0
                left_ratio = math.cos(pan * math.pi / 2)
                right_ratio = math.sin(pan * math.pi / 2)
                left_volume = int(value * left_ratio)
                right_volume = int(value * right_ratio)
                left_volume = min(max(left_volume, 0), 100)
                right_volume = min(max(right_volume, 0), 100)
                
                # Update left block volume
                if hasattr(self.blocks[0], 'fader_value'):
                    self.blocks[0].fader_value = left_volume
                    self.blocks[0].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[0], 'mixer'):
                        self.blocks[0].safe_alsa_operation(
                            lambda: self.blocks[0].mixer.setvolume(left_volume)
                        )
                        
                # Update right block volume
                if hasattr(self.blocks[1], 'fader_value'):
                    self.blocks[1].fader_value = right_volume
                    self.blocks[1].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[1], 'mixer'):
                        self.blocks[1].safe_alsa_operation(
                            lambda: self.blocks[1].mixer.setvolume(right_volume)
                        )
                        
            except Exception as e:
                print(f"Macro fader update failed: {e}")
            finally:
                self._updating_controls = False

    def _on_crossfader_changed(self, value):
        """Handle crossfader value changes."""
        if len(self.blocks) == 2 and not self._updating_controls:
            self._updating_controls = True
            
            try:
                # Constant-power crossfade law
                pan = value / 100.0
                macro_level = self.macro_fader_value if self.macro_fader_value is not None else 100
                left_ratio = math.cos(pan * math.pi / 2)
                right_ratio = math.sin(pan * math.pi / 2)
                left_volume = int(macro_level * left_ratio)
                right_volume = int(macro_level * right_ratio)
                left_volume = min(max(left_volume, 0), 100)
                right_volume = min(max(right_volume, 0), 100)
                
                # Update left block volume
                if hasattr(self.blocks[0], 'fader_value'):
                    self.blocks[0].fader_value = left_volume
                    self.blocks[0].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[0], 'mixer'):
                        self.blocks[0].safe_alsa_operation(
                            lambda: self.blocks[0].mixer.setvolume(left_volume)
                        )
                        
                # Update right block volume
                if hasattr(self.blocks[1], 'fader_value'):
                    self.blocks[1].fader_value = right_volume
                    self.blocks[1].updateFader(skip_change_event=True)
                    if hasattr(self.blocks[1], 'mixer'):
                        self.blocks[1].safe_alsa_operation(
                            lambda: self.blocks[1].mixer.setvolume(right_volume)
                        )
                        
            except Exception as e:
                print(f"Crossfader update failed: {e}")
            finally:
                self._updating_controls = False

    def _on_individual_fader_changed(self, changed_block):
        """Handle individual fader changes within the group."""
        if len(self.blocks) != 2 or self._updating_controls:
            return
            
        self._updating_controls = True
        
        try:
            # Get current individual fader values
            left_current = self.blocks[0].fader_value
            right_current = self.blocks[1].fader_value
            total_volume = left_current + right_current
            
            # Calculate crossfader position based on ratio
            if total_volume > 0:
                crossfader_pos = int((right_current / total_volume) * 100)
            else:
                crossfader_pos = 50
                
            # Update crossfader
            if self.crossfader:
                self.crossfader.blockSignals(True)
                self.crossfader.setValue(crossfader_pos)
                self.crossfader.blockSignals(False)
                
            # Update macro fader
            if self.macro_fader:
                self.macro_fader.blockSignals(True)
                self.macro_fader.setValue(total_volume)
                self.macro_fader.blockSignals(False)
                self.macro_fader_value = total_volume
                
        except Exception as e:
            print(f"Individual fader update failed: {e}")
        finally:
            self._updating_controls = False

    def paint(self, painter, option, widget):
        """Custom painting for group container."""
        super().paint(painter, option, widget)
        
        # Draw group outline
        pen = QPen(self.OUTLINE_COLOR, self.OUTLINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawRoundedRect(self.boundingRect(), self.CORNER_RADIUS, self.CORNER_RADIUS)
        
        # Draw handle
        handle_rect = QRectF(0, 0, self.HANDLE_WIDTH, self.geometry().height())
        painter.setBrush(QBrush(self.HANDLE_COLOR))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(handle_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
        
        # Draw handle text
        painter.setPen(QPen(self.HANDLE_TEXT_COLOR))
        painter.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        painter.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, "G")

    def hoverMoveEvent(self, event):
        """Handle hover events for handle highlighting."""
        handle_rect = QRectF(0, 0, self.HANDLE_WIDTH, self.geometry().height())
        if handle_rect.contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        handle_rect = QRectF(0, 0, self.HANDLE_WIDTH, self.geometry().height())
        if handle_rect.contains(event.pos()):
            # Only allow dragging from handle
            super().mousePressEvent(event)
        else:
            # Ignore clicks outside handle
            event.ignore()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Move the container
            new_pos = self.pos() + event.pos() - event.buttonDownPos(Qt.MouseButton.LeftButton)
            self.setPos(new_pos)
            
            # Move all blocks with the container
            for block in self.blocks:
                if block in self._block_offsets:
                    new_block_pos = self.pos() + QPointF(self.HANDLE_WIDTH, 0) + self._block_offsets[block]
                    block.setPos(new_block_pos)
                    
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        super().mouseReleaseEvent(event) 