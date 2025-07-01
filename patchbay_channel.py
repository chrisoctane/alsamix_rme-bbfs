"""
PatchbayChannel - Individual channel block for the patchbay interface.
"""

import sys
from PyQt6.QtWidgets import QGraphicsWidget, QGraphicsRectItem, QGraphicsTextItem, QGraphicsProxyWidget, QSlider
from PyQt6.QtGui import QBrush, QColor, QPen, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QRectF, QPointF
from config import *


class PatchbayChannel(QGraphicsWidget):
    """Individual channel block for the patchbay interface."""
    
    WIDTH = CHANNEL_WIDTH
    HEIGHT = CHANNEL_HEIGHT
    HANDLE_WIDTH = HANDLE_WIDTH
    HANDLE_COLOR = HANDLE_COLOR
    HANDLE_TEXT_COLOR = HANDLE_TEXT_COLOR
    FADER_BAR_WIDTH = FADER_BAR_WIDTH
    OUTPUT_LABEL_COLOR = OUTPUT_LABEL_COLOR
    NONFADER_LABEL_COLOR = NONFADER_LABEL_COLOR
    FADER_LABEL_COLOR = FADER_LABEL_COLOR
    LABEL_RADIUS = LABEL_RADIUS
    BUTTON_SIZE = BUTTON_SIZE

    def __init__(self, ctl_name, mixer, show_fader=True):
        super().__init__()
        self.ctl_name = ctl_name
        self.mixer = mixer
        self.is_output = ctl_name.startswith("Main-Out") or ctl_name.startswith("OUT")
        
        # Grouping state
        self.snapped_blocks = set()
        self.is_snap_target = False
        self._drag_start_pos = None
        self._is_dragging = False

        # Mute and Solo state
        self.muted = False
        self.soloed = False
        self.pre_mute_volume = 0

        # Setup graphics item flags
        self.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1)
        self.setGeometry(QRectF(0, 0, self.WIDTH, self.HEIGHT))

        self.is_nonfader = not show_fader
        self.show_fader = show_fader
        self.fader_value = 0
        
        # Initialize volume from ALSA
        self._init_volume()
        
        # Create UI elements
        self._create_handle()
        self._create_label()
        self._create_fader()
        self._create_buttons()
        self._create_value_display()

    def _init_volume(self):
        """Initialize volume from ALSA mixer."""
        try:
            self.fader_value = self.mixer.getvolume()[0]
            self.pre_mute_volume = self.fader_value
        except Exception:
            pass

    def _create_handle(self):
        """Create the drag handle on the left side."""
        self.handle = QGraphicsRectItem(0, 0, self.HANDLE_WIDTH, self.HEIGHT, self)
        self.handle.setBrush(QBrush(self.HANDLE_COLOR))
        self.handle.setPen(QPen(Qt.PenStyle.NoPen))

        # Handle text
        self.handle_text = QGraphicsTextItem("⠿", self)
        self.handle_text.setDefaultTextColor(self.HANDLE_TEXT_COLOR)
        self.handle_text.setFont(QFont("Sans", 16))
        handle_text_bbox = self.handle_text.boundingRect()
        handle_text_x = self.HANDLE_WIDTH/2 - handle_text_bbox.width()/2
        handle_text_y = self.HEIGHT/2 - handle_text_bbox.height()/2
        self.handle_text.setPos(handle_text_x, handle_text_y)
        self.handle_text.setZValue(2)

    def _create_label(self):
        """Create the label bar at the top."""
        label_bar_height = 32
        label_bg_color = (
            self.OUTPUT_LABEL_COLOR if self.is_output
            else self.NONFADER_LABEL_COLOR if self.is_nonfader
            else self.FADER_LABEL_COLOR
        )
        
        self.label_bg = QGraphicsRectItem(
            self.HANDLE_WIDTH, 0, self.WIDTH - self.HANDLE_WIDTH, label_bar_height, self
        )
        self.label_bg.setBrush(QBrush(label_bg_color))
        self.label_bg.setPen(QPen(Qt.PenStyle.NoPen))

        # Label text
        label_font = QFont("Sans", 10, QFont.Weight.Bold)
        self.label = QGraphicsTextItem(self)
        self.label.setFont(label_font)
        
        if self.is_nonfader:
            self.label.setDefaultTextColor(QColor("#2b2222"))
        else:
            self.label.setDefaultTextColor(QColor("#FFE066"))
            
        fm = QFontMetrics(label_font)
        max_label_width = self.WIDTH - self.HANDLE_WIDTH - 10
        safe_text = self.ctl_name.replace('\n', ' ')
        elided = fm.elidedText(safe_text, Qt.TextElideMode.ElideRight, max_label_width)
        self.label.setPlainText(elided)
        
        label_bounding = self.label.boundingRect()
        label_x = self.HANDLE_WIDTH + (self.WIDTH - self.HANDLE_WIDTH - label_bounding.width()) / 2
        label_y = (label_bar_height - label_bounding.height()) / 2
        self.label.setPos(label_x, label_y)

    def _create_fader(self):
        """Create the fader slider."""
        if not self.show_fader:
            self.fader_slider = None
            self.fader_proxy = None
            return

        # Create vertical slider
        self.fader_slider = QSlider(Qt.Orientation.Vertical)
        self.fader_slider.setRange(0, 100)
        self.fader_slider.setValue(int(self.fader_value))
        self.fader_slider.setFixedSize(28, 110)
        self.fader_slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: #222;
                width: 8px;
                border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: #3f7fff;
                height: 10px;
                width: 24px;
                margin: 0 -8px;
                border-radius: 3px;
            }
        """)
        
        # Create proxy widget
        self.fader_proxy = QGraphicsProxyWidget(self)
        self.fader_proxy.setWidget(self.fader_slider)
        fader_x = self.HANDLE_WIDTH + (self.WIDTH - self.HANDLE_WIDTH - 28) / 2
        self.fader_proxy.setPos(fader_x, 40)  # 32 (label height) + 8
        self.fader_proxy.setZValue(2)
        
        # Connect slider
        self.fader_slider.valueChanged.connect(self.on_fader_changed)

    def _create_buttons(self):
        """Create mute and solo buttons."""
        button_y = self.HEIGHT - 30
        button_spacing = 25
        
        # Mute button
        mute_x = self.HANDLE_WIDTH + 10
        self.mute_button = QGraphicsRectItem(mute_x, button_y, self.BUTTON_SIZE, self.BUTTON_SIZE, self)
        self.mute_button.setBrush(QBrush(MUTE_COLOR))
        self.mute_button.setPen(QPen(QColor("#333")))
        
        self.mute_text = QGraphicsTextItem("M", self)
        self.mute_text.setFont(QFont("Sans", 8, QFont.Weight.Bold))
        self.mute_text.setDefaultTextColor(QColor("#fff"))
        mute_text_bbox = self.mute_text.boundingRect()
        self.mute_text.setPos(
            mute_x + (self.BUTTON_SIZE - mute_text_bbox.width()) / 2, 
            button_y + (self.BUTTON_SIZE - mute_text_bbox.height()) / 2
        )
        
        # Solo button
        solo_x = mute_x + button_spacing
        self.solo_button = QGraphicsRectItem(solo_x, button_y, self.BUTTON_SIZE, self.BUTTON_SIZE, self)
        self.solo_button.setBrush(QBrush(SOLO_COLOR))
        self.solo_button.setPen(QPen(QColor("#333")))
        
        self.solo_text = QGraphicsTextItem("S", self)
        self.solo_text.setFont(QFont("Sans", 8, QFont.Weight.Bold))
        self.solo_text.setDefaultTextColor(QColor("#fff"))
        solo_text_bbox = self.solo_text.boundingRect()
        self.solo_text.setPos(
            solo_x + (self.BUTTON_SIZE - solo_text_bbox.width()) / 2, 
            button_y + (self.BUTTON_SIZE - solo_text_bbox.height()) / 2
        )

    def _create_value_display(self):
        """Create the value display text."""
        value_font = QFont("Sans", 9)
        self.value_text = QGraphicsTextItem(str(int(self.fader_value)), self)
        self.value_text.setFont(value_font)
        self.value_text.setDefaultTextColor(QColor("#555" if self.is_nonfader else "#fff"))
        
        if self.show_fader:
            # Position under fader
            value_y = 160  # Below fader area
        else:
            # Position under label
            value_y = 50  # Below label area
            
        value_bbox = self.value_text.boundingRect()
        value_x = self.HANDLE_WIDTH + (self.WIDTH - self.HANDLE_WIDTH - value_bbox.width()) / 2
        self.value_text.setPos(value_x, value_y)

    # Group management methods
    def add_to_group(self, other_block):
        """Add another block to this block's group."""
        if other_block != self:
            self.snapped_blocks.add(other_block)
            other_block.snapped_blocks.add(self)

    def remove_from_group(self, other_block):
        """Remove another block from this block's group."""
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

    def get_bounds(self):
        """Get the bounding rectangle of this block."""
        return self.boundingRect()

    # ALSA operations
    def safe_alsa_operation(self, operation, default_value=None):
        """Safely execute an ALSA operation with error handling."""
        try:
            return operation()
        except Exception as e:
            print(f"ALSA operation failed for {self.ctl_name}: {e}")
            return default_value

    # Event handlers
    def wheelEvent(self, event):
        """Handle mouse wheel events for volume control."""
        if not self.show_fader:
            return
            
        delta = event.angleDelta().y()
        current_value = self.fader_slider.value()
        
        if delta > 0:
            new_value = min(current_value + 1, 100)
        else:
            new_value = max(current_value - 1, 0)
            
        self.fader_slider.setValue(new_value)
        event.accept()

    def updateFader(self, skip_change_event=False):
        """Update fader slider value."""
        if self.fader_slider and not skip_change_event:
            self.fader_slider.blockSignals(True)
            self.fader_slider.setValue(int(self.fader_value))
            self.fader_slider.blockSignals(False)
        
        self.value_text.setPlainText(str(int(self.fader_value)))

    def update_group_state(self):
        """Update the visual state based on group membership."""
        if self.snapped_blocks:
            self.setZValue(2)
        else:
            self.setZValue(1)

    # Mute/Solo functionality
    def toggle_mute(self):
        """Toggle mute state."""
        if self.muted:
            # Unmute
            self.muted = False
            self.fader_value = self.pre_mute_volume
            self.mute_button.setBrush(QBrush(MUTE_COLOR))
            self.safe_alsa_operation(lambda: self.mixer.setvolume(self.fader_value))
        else:
            # Mute
            self.muted = True
            self.pre_mute_volume = self.fader_value
            self.fader_value = 0
            self.mute_button.setBrush(QBrush(MUTE_ACTIVE_COLOR))
            self.safe_alsa_operation(lambda: self.mixer.setvolume(0))
        
        self.updateFader()

    def toggle_solo(self):
        """Toggle solo state."""
        self.soloed = not self.soloed
        self.solo_button.setBrush(QBrush(SOLO_ACTIVE_COLOR if self.soloed else SOLO_COLOR))

    # Mouse event handlers
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self._is_dragging = False
            
            # Check if clicking on mute/solo buttons
            pos = event.pos()
            if self._is_in_mute_button(pos):
                self.toggle_mute()
                event.accept()
                return
            elif self._is_in_solo_button(pos):
                self.toggle_solo()
                event.accept()
                return
        
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
            self._is_dragging = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self._drag_start_pos is not None:
            delta = event.pos() - self._drag_start_pos
            if delta.manhattanLength() > 5:
                self._is_dragging = True
                # Notify parent view about dragging
                scene = self.scene()
                if scene:
                    view = scene.views()[0] if scene.views() else None
                    if hasattr(view, 'check_for_snapping'):
                        view.check_for_snapping(self)
        
        super().mouseMoveEvent(event)

    def _is_in_mute_button(self, pos):
        """Check if position is within mute button bounds."""
        button_rect = QRectF(
            self.HANDLE_WIDTH + 10, 
            self.HEIGHT - 30, 
            self.BUTTON_SIZE, 
            self.BUTTON_SIZE
        )
        return button_rect.contains(pos)

    def _is_in_solo_button(self, pos):
        """Check if position is within solo button bounds."""
        button_rect = QRectF(
            self.HANDLE_WIDTH + 35, 
            self.HEIGHT - 30, 
            self.BUTTON_SIZE, 
            self.BUTTON_SIZE
        )
        return button_rect.contains(pos)

    # Painting
    def paint(self, painter, option, widget):
        """Custom painting for selection and snap highlighting."""
        super().paint(painter, option, widget)
        
        if self.isSelected():
            pen = QPen(SELECTION_COLOR, SELECTION_WIDTH)
            painter.setPen(pen)
            painter.drawRoundedRect(self.boundingRect(), BLOCK_CORNER_RADIUS, BLOCK_CORNER_RADIUS)
        
        if self.is_snap_target:
            pen = QPen(SNAP_TARGET_COLOR, SNAP_TARGET_WIDTH)
            painter.setPen(pen)
            painter.drawRoundedRect(self.boundingRect(), BLOCK_CORNER_RADIUS, BLOCK_CORNER_RADIUS)

    # Fader change handling
    def on_fader_changed(self, value):
        """Handle fader value changes."""
        if self.muted:
            return
            
        self.fader_value = value
        self.value_text.setPlainText(str(value))
        
        # Update ALSA
        self.safe_alsa_operation(lambda: self.mixer.setvolume(value))
        
        # Update group controls if in a group
        self._update_group_controls_from_fader()

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