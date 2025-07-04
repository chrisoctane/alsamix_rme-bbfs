#!/usr/bin/env python3
"""
Patchbay2 - Simple, clean patchbay system
- Rubber band canvas with draggable blocks
- Magnetic snapping (2 blocks per group max)
- Group widgets with faders, macro, and crossfader
- Hide individual channels when grouped
- Right-click to ungroup
"""

import sys
from typing import Optional, List
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsWidget, QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem,
    QSlider, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QGraphicsProxyWidget, QApplication, QMainWindow, QPushButton
)
from PyQt6.QtGui import QBrush, QColor, QPen, QFont, QPainter, QFontMetrics, QWheelEvent, QMouseEvent, QPainterPath
from PyQt6.QtWidgets import QGraphicsSceneWheelEvent, QGraphicsSceneMouseEvent
from PyQt6.QtCore import Qt, QRectF, QTimer, QPointF, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QStyleOptionSlider

import alsa_backend
import math
import alsaaudio
from oval_slider import OvalGrooveSlider


class ChannelBlock(QGraphicsWidget):
    """Individual channel block that can be dragged and snapped."""
    
    WIDTH = 120
    HEIGHT = 120  # Increased to match group widget
    
    def __init__(self, ctl_name: str, mixer: alsaaudio.Mixer, show_fader: bool = True):
        super().__init__()
        self.ctl_name = ctl_name
        self.mixer = mixer
        self.show_fader = show_fader
        
        # Get initial volume from ALSA
        try:
            self.fader_value = mixer.getvolume()[0]
        except:
            self.fader_value = 50
        
        # Determine channel type for control buttons
        self.channel_type = self._determine_channel_type(ctl_name)
        self.control_buttons = []
        
        # Mute/Solo state
        self.muted = False
        self.soloed = False
        self.pre_mute_volume = self.fader_value  # Store volume before mute
        

        
        # Setup graphics
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(1)
        self.setGeometry(QRectF(0, 0, self.WIDTH, self.HEIGHT))
        
        # Create main label - match group widget font size
        label_font = QFont("Sans", 7, QFont.Weight.Bold)  # Match group widget font size
        self.label = QGraphicsTextItem(ctl_name, self)
        self.label.setFont(label_font)
        self.label.setDefaultTextColor(QColor("#FFD700"))  # Gold like group widget
        
        # Center the label at top
        label_rect = self.label.boundingRect()
        label_x = (self.WIDTH - label_rect.width()) / 2
        label_y = 5
        self.label.setPos(label_x, label_y)
        
        # Value display - create first (moved up to ensure it exists before fader)
        value_font = QFont("Sans", 7)  # Match group volume indicator font size
        self.value_text = QGraphicsTextItem(str(int(self.fader_value)), self)
        self.value_text.setFont(value_font)
        self.value_text.setDefaultTextColor(QColor("#3f7fff"))  # Blue like crossfader
        
        # Create fader/value before control buttons (matches patchbay2.py)
        if self.show_fader:
            self._create_fader()
        else:
            value_rect = self.value_text.boundingRect()
            value_x = (self.WIDTH - value_rect.width()) / 2
            self.value_text.setPos(value_x, self.HEIGHT - 25)
        
        # Create controls
        self._create_control_buttons()
        
        # Group state
        self.current_group = None
        self.left_edge_straight = False
        self.right_edge_straight = False
        
        # Animation properties for corner straightening
        self.corner_radius = 12.0  # More rounded corners to match modern design
        
        # Visual properties
        self.is_output = ctl_name.startswith("Main-Out") or ctl_name.startswith("OUT")
        self.is_nonfader = not show_fader
        
        # Background colors will be handled in paint() method for rounded corners
        # Remove the square QGraphicsRectItem background
        
        # Use full ALSA control name for display
        display_name = ctl_name
        
        # Connect to mute_solo_manager state_changed signal
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        manager.state_changed.connect(self.update_mute_solo_state)

    
    def _determine_channel_type(self, ctl_name: str) -> str:
        """Determine the type of channel based on control name."""
        if 'AN1' in ctl_name or 'AN2' in ctl_name:
            return 'mic'  # Analog inputs - need 48V, PAD, sensitivity
        elif 'ADAT' in ctl_name and ctl_name.endswith(('ADAT3', 'ADAT4', 'ADAT5', 'ADAT6', 'ADAT7', 'ADAT8')):
            return 'line'  # ADAT line inputs - need sensitivity chooser
        elif 'ADAT' in ctl_name:
            return 'digital'  # Digital ADAT - basic controls
        elif 'Main-Out' in ctl_name or 'OUT' in ctl_name:
            return 'output'  # Output channels
        else:
            return 'generic'  # Generic channels
    
    def _create_control_buttons(self):
        """Create channel-specific control buttons."""
        if not self.show_fader:
            return  # No buttons for non-fader channels
        
        button_size = 20  # Was 14
        button_gap = 4   # Better separation
        start_x = 8      # Left side with gap
        start_y = 42     # Below label, above value
        
        if self.channel_type == 'mic':
            # Mic channels: Mute, Solo, 48V, PAD (2x2 grid)
            self._create_button("M", start_x, start_y, "#ff4444", "Mute")  # Red
            self._create_button("S", start_x, start_y + button_size + button_gap, "#44ff44", "Solo")  # Green
            self._create_button("48V", start_x + button_size + button_gap, start_y, "#ffaa00", "48V Phantom")  # Orange
            self._create_button("PAD", start_x + button_size + button_gap, start_y + button_size + button_gap, "#aa44ff", "PAD")  # Purple
            
        elif self.channel_type == 'line':
            # Line channels: Mute, Solo, Sensitivity (vertical stack + one to right)
            self._create_button("M", start_x, start_y, "#ff4444", "Mute")
            self._create_button("S", start_x, start_y + button_size + button_gap, "#44ff44", "Solo")
            self._create_button("SENS", start_x + button_size + button_gap, start_y, "#4488ff", "Sensitivity")  # Blue
            
        elif self.channel_type == 'digital':
            # Digital channels: Mute, Solo (vertical stack)
            self._create_button("M", start_x, start_y, "#ff4444", "Mute")
            self._create_button("S", start_x, start_y + button_size + button_gap, "#44ff44", "Solo")
            
        elif self.channel_type == 'output':
            # Output channels: Mute, Monitor (vertical stack)
            self._create_button("M", start_x, start_y, "#ff4444", "Mute")
            self._create_button("MON", start_x, start_y + button_size + button_gap, "#ffff44", "Monitor")  # Yellow
            
        else:
            # Generic channels: Mute, Solo (vertical stack)
            self._create_button("M", start_x, start_y, "#ff4444", "Mute")
            self._create_button("S", start_x, start_y + button_size + button_gap, "#44ff44", "Solo")
    
    def _create_button(self, text: str, x: float, y: float, color: str, tooltip: str):
        """Create a small rounded control button."""
        button_size = 20  # Was 14
        
        # Create rounded button using custom painting in a proxy widget
        button = QPushButton(text)
        button.setFixedSize(button_size, button_size)
        button.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Set initial state based on current mute/solo state
        is_active = False
        if text == "M":
            is_active = self.muted
        elif text == "S":
            is_active = self.soloed
        
        # Choose color based on state
        if is_active:
            if text == "M":
                active_color = "#ff0000"  # Bright red for active mute
            else:  # Solo
                active_color = "#00ff00"  # Bright green for active solo
        else:
            active_color = color
        
        # When setting style for mute/solo buttons, always use button.width()//2 for border-radius
        button.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                background-color: {active_color};
                color: white;
                border: 2px solid #333;
                border-radius: {button.width()//2}px;
                font-size: 6px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {active_color}aa;
                border: 2px solid #666;
            }}
            QPushButton:pressed {{
                background-color: {active_color}77;
            }}
        """)
        
        # Add click handlers for mute and solo buttons
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        if text == "M":
            button.clicked.connect(self._on_mute_clicked)
            manager.flash_state_changed.connect(self._update_mute_flash)
        elif text == "S":
            button.clicked.connect(self._on_solo_clicked)
            manager.flash_state_changed.connect(self._update_solo_flash)
        
        # Add button to scene via proxy with transparent background
        button_proxy = QGraphicsProxyWidget(self)
        button_proxy.setWidget(button)
        button_proxy.setPos(x, y)
        button_proxy.setAutoFillBackground(False)
        from PyQt6.QtGui import QPalette
        palette = button_proxy.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        button_proxy.setPalette(palette)
        
        # Store references
        self.control_buttons.append((button_proxy, button, tooltip))
    
    def _create_fader(self):
        """Create the fader using QSlider for consistent styling."""
        gap = 15
        block_height = self.HEIGHT
        fader_height = 100
        fader_x = self.WIDTH - 20 - gap  # Right side with gap
        fader_y_centered = (block_height - fader_height) // 2

        # Create QSlider with same styling as group widgets
        self.fader_slider = OvalGrooveSlider(Qt.Orientation.Vertical, handle_color="#3f7fff", groove_color="#222")
        self.fader_slider.setRange(0, 100)
        self.fader_slider.setValue(self.fader_value)
        self.fader_slider.setFixedSize(20, fader_height)
        self.fader_slider.valueChanged.connect(self._on_fader_changed)

        # Add slider to graphics scene via proxy
        self.fader_proxy = QGraphicsProxyWidget(self)
        self.fader_proxy.setWidget(self.fader_slider)
        self.fader_proxy.setPos(fader_x, fader_y_centered)

        # Value readout stacked vertically to the left of fader
        value_rect = self.value_text.boundingRect()
        value_x = fader_x - value_rect.width() - 6  # 6px gap to left of fader
        value_y = fader_y_centered + (fader_height - value_rect.height()) / 2
        self.value_text.setPos(value_x, value_y)
    
    def _on_fader_changed(self, value: int):
        """Handle fader value changes."""
        self.fader_value = value
        # Update ALSA hardware
        try:
            self.mixer.setvolume(value)
        except Exception as e:
            print(f"[ERROR] Failed to set ALSA volume for {self.ctl_name}: {e}")
        
        # Update display
        self.value_text.setPlainText(str(value))
    
    def update_fader(self, skip_alsa: bool = False):
        """Update the fader display."""
        if self.show_fader and hasattr(self, 'fader_slider'):
            # Update slider value without triggering valueChanged signal
            self.fader_slider.blockSignals(True)
            self.fader_slider.setValue(int(self.fader_value))
            self.fader_slider.blockSignals(False)
        
        self.value_text.setPlainText(str(int(self.fader_value)))
        
        if not skip_alsa:
            try:
                self.mixer.setvolume(int(self.fader_value))
            except Exception:
                pass
    
    def mousePressEvent(self, event: Optional[QGraphicsSceneMouseEvent]):
        """Handle mouse press events."""
        if event and event.button() == Qt.MouseButton.RightButton and self.current_group:
            # Right-click to ungroup
            self.current_group.ungroup()
            event.accept()
        elif event and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for ungrouping."""
        if event and (event.key() == Qt.Key.Key_U or event.key() == Qt.Key.Key_Delete) and self.current_group:
            # U key or Delete key to ungroup when part of a group
            self.current_group.ungroup()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def paint(self, painter: Optional[QPainter], option, widget):
        """Custom painting for selection highlighting and corner animation."""
        if not painter:
            return
            
        painter.setBackgroundMode(Qt.BGMode.OpaqueMode)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded background with selective corner straightening
        painter.setPen(QPen(QColor("#FFD700"), 2 if self.isSelected() else 1))
        
        # Use different background colors based on channel type
        if self.is_output:
            bg_color = QColor("#4a2a2a")  # Soft red for main outputs
        else:
            bg_color = QColor("#2e3036")  # Lighter Bitwig-style dark grey for inputs
        
        painter.setBrush(QBrush(bg_color))
        
        # Create custom rounded rectangle with selective corners
        rect = self.boundingRect()
        if self.left_edge_straight or self.right_edge_straight:
            # Custom path for selective corner rounding
            path = QPainterPath()
            
            # Start from top-left, going clockwise
            top_left_radius = 0 if self.left_edge_straight else self.corner_radius
            top_right_radius = 0 if self.right_edge_straight else self.corner_radius
            bottom_right_radius = 0 if self.right_edge_straight else self.corner_radius
            bottom_left_radius = 0 if self.left_edge_straight else self.corner_radius
            
            # Top edge
            path.moveTo(rect.left() + top_left_radius, rect.top())
            path.lineTo(rect.right() - top_right_radius, rect.top())
            
            # Top-right corner
            if top_right_radius > 0:
                path.arcTo(rect.right() - 2*top_right_radius, rect.top(), 
                          2*top_right_radius, 2*top_right_radius, 90, -90)
            
            # Right edge
            path.lineTo(rect.right(), rect.bottom() - bottom_right_radius)
            
            # Bottom-right corner
            if bottom_right_radius > 0:
                path.arcTo(rect.right() - 2*bottom_right_radius, rect.bottom() - 2*bottom_right_radius,
                          2*bottom_right_radius, 2*bottom_right_radius, 0, -90)
            
            # Bottom edge
            path.lineTo(rect.left() + bottom_left_radius, rect.bottom())
            
            # Bottom-left corner
            if bottom_left_radius > 0:
                path.arcTo(rect.left(), rect.bottom() - 2*bottom_left_radius,
                          2*bottom_left_radius, 2*bottom_left_radius, 270, -90)
            
            # Left edge
            path.lineTo(rect.left(), rect.top() + top_left_radius)
            
            # Top-left corner
            if top_left_radius > 0:
                path.arcTo(rect.left(), rect.top(),
                          2*top_left_radius, 2*top_left_radius, 180, -90)
            
            path.closeSubpath()
            painter.drawPath(path)
        else:
            # Standard rounded rectangle
            painter.drawRoundedRect(rect, self.corner_radius, self.corner_radius)
        
        # Draw selection highlight if selected
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFD700"), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.boundingRect().adjusted(1, 1, -1, -1), self.corner_radius, self.corner_radius)
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse release for potential grouping."""
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, '_dragging') and self._dragging:
            self._dragging = False
            
            # Check for edge-snapping grouping
            scene = self.scene()
            if scene and not self.current_group:
                snap_distance = 30
                my_pos = self.pos()
                my_rect = QRectF(my_pos.x(), my_pos.y(), 120, 120)
                
                # Check for blocks to snap to
                for item in scene.items():
                    if isinstance(item, ChannelBlock) and item != self and not item.current_group:
                        other_pos = item.pos()
                        other_rect = QRectF(other_pos.x(), other_pos.y(), 120, 120)
                        
                        # Check for left edge snapping (my right edge to their left edge)
                        vertical_overlap = min(my_rect.bottom(), other_rect.bottom()) - max(my_rect.top(), other_rect.top())
                        if (abs(my_rect.right() - other_rect.left()) < snap_distance and
                            abs(my_rect.center().y() - other_rect.center().y()) < snap_distance and
                            vertical_overlap >= 1):
                            # Snap to left edge
                            target_pos = QPointF(other_rect.left() - 120, other_rect.y())
                            self.setPos(target_pos)
                            # Set edge straightening for both blocks
                            self.right_edge_straight = True
                            item.left_edge_straight = True
                            # Create group
                            self._create_group(item, 'left')
                            break
                        # Check for right edge snapping (my left edge to their right edge)
                        elif (abs(my_rect.left() - other_rect.right()) < snap_distance and
                              abs(my_rect.center().y() - other_rect.center().y()) < snap_distance and
                              vertical_overlap >= 1):
                            # Snap to right edge
                            target_pos = QPointF(other_rect.right(), other_rect.y())
                            self.setPos(target_pos)
                            # Set edge straightening for both blocks
                            self.left_edge_straight = True
                            item.right_edge_straight = True
                            # Create group
                            self._create_group(item, 'right')
                            break
                
                # Trigger repaint for both blocks to show corner changes
                self.update()
        
        super().mouseReleaseEvent(event)
    
    def _create_group(self, other_block: 'ChannelBlock', position: str) -> None:
        """Create a group with another block."""
        if self.current_group or other_block.current_group:
            return
            
        scene = self.scene()
        if not scene:
            return
            
        print(f"[DEBUG] Creating group: {self.ctl_name} + {other_block.ctl_name}")
        
        # Position the group widget to cover both blocks seamlessly
        if position == 'left':
            # I'm on the left, other is on the right
            group_pos = self.pos()
            left_block, right_block = self, other_block
        else:
            # I'm on the right, other is on the left  
            group_pos = other_block.pos()
            left_block, right_block = other_block, self
        
        # Create group widget - get mixer from the scene's view
        scene_view = None
        for view in scene.views():
            if isinstance(view, PatchbayView):
                scene_view = view
                break
        
        if scene_view:
            group = GroupWidget(left_block, right_block, scene_view)
            group.setPos(group_pos)
            scene.addItem(group)
        
        # Hide the individual blocks (but keep them for ungrouping)
        self.hide()
        other_block.hide()
        
        # Set group references
        self.current_group = group
        other_block.current_group = group

    def wheelEvent(self, event: Optional[QGraphicsSceneWheelEvent]):
        """Handle mouse wheel for fader control."""
        if not event or not self.show_fader or self.current_group:
            return
            
        delta = event.delta()
        direction = 1 if delta > 0 else -1
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            step_size = 1
        else:
            step_size = 5
        new_value = min(max(self.fader_value + direction * step_size, 0), 100)
        self.fader_value = new_value
        self.update_fader()
        event.accept()

    def _on_mute_clicked(self):
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        new_mute_state = not manager.get_mute_state(self.ctl_name)
        manager.set_mute(self.ctl_name, new_mute_state, explicit=True)
        self.update_mute_solo_state()

    def _on_solo_clicked(self):
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        new_solo_state = not manager.get_solo_state(self.ctl_name)
        manager.set_solo(self.ctl_name, new_solo_state, explicit=True)
        self.update_mute_solo_state()

    def _update_button_states(self):
        for button_proxy, button, tooltip in self.control_buttons:
            if tooltip in ("Group Mute", "Mute"):
                is_active = self.muted
                color = "#ff0000" if is_active else "#888888"
            elif tooltip in ("Group Solo", "Solo"):
                is_active = self.soloed
                color = "#ffe066" if is_active else "#888888"
            else:
                continue
            button.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    background-color: {color};
                    color: white;
                    border: 2px solid #333;
                    border-radius: {button.width()//2}px;
                    font-size: 6px;
                    font-weight: bold;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {color}aa;
                    border: 2px solid #666;
                }}
                QPushButton:pressed {{
                    background-color: {color}77;
                }}
            """)

    def _update_mute_flash(self, flash_on: bool):
        if not self.muted:
            self._update_button_states()
            return
        if hasattr(self, 'explicit_mute') and self.explicit_mute:
            # Solid red for explicit mute
            for button_proxy, button, tooltip in self.control_buttons:
                if tooltip in ("Group Mute", "Mute"):
                    color = "#ff0000"
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            background-color: {color};
                            color: white;
                            border: 2px solid #333;
                            border-radius: {button.width()//2}px;
                            font-size: 6px;
                            font-weight: bold;
                            padding: 0px;
                        }}
                        QPushButton:hover {{
                            background-color: {color}aa;
                            border: 2px solid #666;
                        }}
                        QPushButton:pressed {{
                            background-color: {color}77;
                        }}
                    """)
            return
        # Flashing for mute-by-solo-logic
        for button_proxy, button, tooltip in self.control_buttons:
            if tooltip in ("Group Mute", "Mute"):
                color = "#ff0000" if flash_on else "#660000"
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        background-color: {color};
                        color: white;
                        border: 2px solid #333;
                        border-radius: {button.width()//2}px;
                        font-size: 6px;
                        font-weight: bold;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {color}aa;
                        border: 2px solid #666;
                    }}
                    QPushButton:pressed {{
                        background-color: {color}77;
                    }}
                """)

    def _update_solo_flash(self, flash_on: bool):
        if not self.soloed:
            self._update_button_states()
            return
        for button_proxy, button, tooltip in self.control_buttons:
            if tooltip in ("Group Solo", "Solo"):
                color = "#ffe066" if flash_on else "#7a6a00"
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        background-color: {color};
                        color: white;
                        border: 2px solid #333;
                        border-radius: {button.width()//2}px;
                        font-size: 6px;
                        font-weight: bold;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {color}aa;
                        border: 2px solid #666;
                    }}
                    QPushButton:pressed {{
                        background-color: {color}77;
                    }}
                """)

    def update_mute_solo_state(self):
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        self.muted = manager.get_mute_state(self.ctl_name)
        self.soloed = manager.get_solo_state(self.ctl_name)
        # Store explicit mute state for correct flashing logic
        self.explicit_mute = False
        if self.ctl_name in manager.channel_states:
            self.explicit_mute = manager.channel_states[self.ctl_name].explicit_mute
        self._update_button_states()


class GroupWidget(QGraphicsWidget):
    """Group widget that contains controls for grouped channels."""
    
    def __init__(self, block1: ChannelBlock, block2: ChannelBlock, view: 'PatchbayView'):
        super().__init__()
        self.block1 = block1
        self.block2 = block2
        self.view = view
        
        # Setup graphics
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(10)
        
        # Calculate size and position
        self._setup_geometry()
        
        # Create controls
        self._create_controls()
        
        # Connect signals
        self.crossfader.valueChanged.connect(self._on_crossfader_changed)
        self.macro_fader.valueChanged.connect(self._on_macro_fader_changed)
        
        # Initialize faders based on current block values
        self._initialize_from_blocks()
        
        # Hide individual blocks
        self.block1.current_group = self
        self.block2.current_group = self
        self.block1.hide()
        self.block2.hide()
        
        # Initialize mute/solo state from global manager
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        self.muted = manager.get_mute_state(self.block1.ctl_name)
        self.soloed = manager.get_solo_state(self.block1.ctl_name)
        
        # Connect to mute_solo_manager state_changed signal
        manager.state_changed.connect(self.update_mute_solo_state)
    
    def mousePressEvent(self, event: Optional[QGraphicsSceneMouseEvent]):
        """Handle mouse press events for ungrouping."""
        if event and event.button() == Qt.MouseButton.RightButton:
            # Right-click to ungroup
            self.ungroup()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for ungrouping."""
        if event and (event.key() == Qt.Key.Key_U or event.key() == Qt.Key.Key_Delete):
            # U key or Delete key to ungroup
            self.ungroup()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def wheelEvent(self, event: Optional[QGraphicsSceneWheelEvent]):
        """Handle mouse wheel for group fader control."""
        print(f"[DEBUG] GroupWidget.wheelEvent called")
        if not event:
            return
            
        # Check if mouse is over crossfader or macro fader
        mouse_pos = event.pos()
        
        # Check crossfader area
        crossfader_rect = QRectF(55, 85, 140, 20)  # Approximate crossfader position
        if crossfader_rect.contains(mouse_pos):
            print(f"[DEBUG] Wheel event over crossfader")
            delta = event.delta()
            direction = 1 if delta > 0 else -1
            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                step_size = 1
            else:
                step_size = 5
            new_value = min(max(self.crossfader.value() + direction * step_size, 0), 100)
            print(f"[DEBUG] Crossfader: old_value={self.crossfader.value()}, new_value={new_value}")
            self.crossfader.setValue(new_value)
            event.accept()
            return
            
        # Check macro fader area
        macro_rect = QRectF(205, 30, 20, 60)  # Approximate macro fader position
        if macro_rect.contains(mouse_pos):
            print(f"[DEBUG] Wheel event over macro fader")
            delta = event.delta()
            direction = 1 if delta > 0 else -1
            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                step_size = 1
            else:
                step_size = 5
            new_value = min(max(self.macro_fader.value() + direction * step_size, 0), 100)
            print(f"[DEBUG] Macro fader: old_value={self.macro_fader.value()}, new_value={new_value}")
            self.macro_fader.setValue(new_value)
            event.accept()
            return
        
        # If not over any fader, ignore the event
        event.ignore()
    
    def _setup_geometry(self):
        """Setup the group widget geometry for seamless coverage."""
        # For seamless appearance, position group widget to exactly cover both blocks
        # Determine which block is on the left
        pos1 = self.block1.scenePos()
        pos2 = self.block2.scenePos()
        
        if pos1.x() < pos2.x():
            left_pos = pos1
            left_y = pos1.y()
        else:
            left_pos = pos2
            left_y = pos2.y()
        
        # Size to be exactly double a single channel
        width = 240  # Exactly 2 * ChannelBlock.WIDTH
        height = 120  # Same as individual blocks
        
        # Position to cover both blocks seamlessly (starting from leftmost block)
        self.setPos(left_pos.x(), left_y)
        self.setGeometry(QRectF(0, 0, width, height))
    
    def _create_controls(self):
        """Create the group controls."""
        # Channel names centered at top on two lines - use full ALSA names
        width = self.geometry().width()
        gap = 15
        height = self.geometry().height()
        
        # First channel name - top line (full ALSA name)
        channel1_name = QGraphicsTextItem(self.block1.ctl_name, self)
        channel1_name.setDefaultTextColor(QColor("#FFD700"))
        channel1_name.setFont(QFont("Sans", 7, QFont.Weight.Bold))  # Smaller font for longer names
        
        # Center first line
        name1_rect = channel1_name.boundingRect()
        name1_x = (width - name1_rect.width()) / 2
        channel1_name.setPos(name1_x, 8)
        
        # Second channel name - second line (full ALSA name)
        channel2_name = QGraphicsTextItem(self.block2.ctl_name, self)
        channel2_name.setDefaultTextColor(QColor("#FFD700"))
        channel2_name.setFont(QFont("Sans", 7, QFont.Weight.Bold))  # Smaller font for longer names
        
        # Center second line
        name2_rect = channel2_name.boundingRect()
        name2_x = (width - name2_rect.width()) / 2
        channel2_name.setPos(name2_x, 22)
        
        # Crossfader (horizontal) - match macro fader height for width
        self.crossfader = OvalGrooveSlider(Qt.Orientation.Horizontal, handle_color="#3f7fff", groove_color="#222")
        self.crossfader.setRange(0, 100)
        self.crossfader.setValue(50)
        macro_height = 100
        self.crossfader.setFixedSize(macro_height, 20)
        
        crossfader_proxy = QGraphicsProxyWidget(self)
        crossfader_proxy.setWidget(self.crossfader)
        crossfader_x = (width - macro_height) / 2
        crossfader_y = height - 20 - gap
        crossfader_proxy.setPos(crossfader_x, crossfader_y)
        
        # Macro fader (vertical) - make taller
        self.macro_fader = OvalGrooveSlider(Qt.Orientation.Vertical, handle_color="#ff3f7f", groove_color="#222")
        self.macro_fader.setRange(0, 100)
        self.macro_fader.setValue(100)
        self.macro_fader.setFixedSize(20, macro_height)
        
        macro_proxy = QGraphicsProxyWidget(self)
        macro_proxy.setWidget(self.macro_fader)
        macro_x = width - 20 - gap  # Right side with gap
        group_height = self.geometry().height()
        macro_y_centered = (group_height - macro_height) // 2
        macro_proxy.setPos(macro_x, macro_y_centered)
        
        # Volume indicators stacked vertically to the left of macro fader
        self.vol1_text = QGraphicsTextItem("100", self)
        self.vol1_text.setDefaultTextColor(QColor("#3f7fff"))
        self.vol1_text.setFont(QFont("Sans", 7))
        self.vol2_text = QGraphicsTextItem("100", self)
        self.vol2_text.setDefaultTextColor(QColor("#ff3f7f"))
        self.vol2_text.setFont(QFont("Sans", 7))
        vol1_rect = self.vol1_text.boundingRect()
        vol2_rect = self.vol2_text.boundingRect()
        vol_x = macro_x - vol1_rect.width() - 6  # 6px gap to left of macro fader
        vol1_y = macro_y_centered + (macro_height - (vol1_rect.height() + vol2_rect.height() + 4)) / 2
        vol2_y = vol1_y + vol1_rect.height() + 4  # 4px gap between values
        self.vol1_text.setPos(vol_x, vol1_y)
        self.vol2_text.setPos(vol_x, vol2_y)
        
        # No labels needed for crossfader and macro fader
        
        # Add control buttons for the group based on block types
        self._create_group_buttons()
    
    def _initialize_from_blocks(self):
        """Initialize group faders and displays based on current block values."""
        # Get current block values
        val1 = self.block1.fader_value
        val2 = self.block2.fader_value
        
        # Calculate macro fader level (average of both blocks)
        macro_level = (val1 + val2) // 2
        
        # Calculate crossfader position based on relative levels
        if val1 + val2 > 0:  # Avoid division by zero
            # Use inverse of the pan law to calculate crossfader position
            total = val1 + val2
            if total > 0:
                ratio = val1 / total
                # Convert ratio to crossfader position (0-100)
                # This is a simplified calculation - the exact math depends on the pan law used
                crossfader_pos = int(ratio * 100)
            else:
                crossfader_pos = 50
        else:
            crossfader_pos = 50
        
        # Update group faders without triggering signals
        self.macro_fader.blockSignals(True)
        self.crossfader.blockSignals(True)
        
        self.macro_fader.setValue(macro_level)
        self.crossfader.setValue(crossfader_pos)
        
        self.macro_fader.blockSignals(False)
        self.crossfader.blockSignals(False)
        
        # Update volume displays
        self.vol1_text.setPlainText(str(val1))
        self.vol2_text.setPlainText(str(val2))
    
    def _create_group_buttons(self):
        """Create control buttons for the group based on the channel types."""
        # Determine what buttons to show based on both blocks
        has_mic = (self.block1.channel_type == 'mic' or self.block2.channel_type == 'mic')
        has_line = (self.block1.channel_type == 'line' or self.block2.channel_type == 'line')
        has_output = (self.block1.channel_type == 'output' or self.block2.channel_type == 'output')
        
        button_size = 20
        button_gap = 4
        start_x = 8  # Left side with gap
        start_y = 45  # Below channel names, above sliders
        
        self.control_buttons = []
        
        # Always add mute and solo for groups
        self._create_group_button("M", start_x, start_y, "#ff4444", "Group Mute")
        self._create_group_button("S", start_x, start_y + button_size + button_gap, "#44ff44", "Group Solo")
        
        # Add specific buttons based on channel types
        if has_mic:
            self._create_group_button("48V", start_x + button_size + button_gap, start_y, "#ffaa00", "48V Phantom")
            self._create_group_button("PAD", start_x + button_size + button_gap, start_y + button_size + button_gap, "#aa44ff", "PAD")
        elif has_line:
            self._create_group_button("SENS", start_x + button_size + button_gap, start_y, "#4488ff", "Sensitivity")
        elif has_output:
            self._create_group_button("MON", start_x + button_size + button_gap, start_y, "#ffff44", "Monitor")
    
    def _create_group_button(self, text: str, x: float, y: float, color: str, tooltip: str):
        """Create a control button for the group."""
        button_size = 20
        button = QPushButton(text)
        button.setFixedSize(button_size, button_size)
        button.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        button.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                background-color: {color};
                color: white;
                border: 2px solid #333;
                border-radius: {button.width()//2}px;
                font-size: 6px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {color}aa;
                border: 2px solid #666;
            }}
            QPushButton:pressed {{
                background-color: {color}77;
            }}
        """)
        # Add click handlers for mute and solo buttons
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        if text == "M":
            button.clicked.connect(self._on_mute_clicked)
            manager.flash_state_changed.connect(self._update_mute_flash)
        elif text == "S":
            button.clicked.connect(self._on_solo_clicked)
            manager.flash_state_changed.connect(self._update_solo_flash)
        button_proxy = QGraphicsProxyWidget(self)
        button_proxy.setWidget(button)
        button_proxy.setPos(x, y)
        button_proxy.setAutoFillBackground(False)
        from PyQt6.QtGui import QPalette
        palette = button_proxy.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        button_proxy.setPalette(palette)
        self.control_buttons.append((button_proxy, button, tooltip))

    def _on_mute_clicked(self):
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        current_mute = manager.get_mute_state(self.block1.ctl_name)
        new_mute_state = not current_mute
        for block in [self.block1, self.block2]:
            manager.set_mute(block.ctl_name, new_mute_state, explicit=True)
        self.update_mute_solo_state()

    def _on_solo_clicked(self):
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        current_solo = manager.get_solo_state(self.block1.ctl_name)
        new_solo_state = not current_solo
        for block in [self.block1, self.block2]:
            manager.set_solo(block.ctl_name, new_solo_state, explicit=True)
        self.update_mute_solo_state()

    def _on_crossfader_changed(self, value: int):
        """Handle crossfader changes."""
        # Calculate pan ratios (constant-power law)
        pan = value / 100.0
        left_ratio = math.cos(pan * math.pi / 2)
        right_ratio = math.sin(pan * math.pi / 2)
        
        # Get macro level
        macro_level = self.macro_fader.value()
        
        # Apply to blocks
        left_volume = int(macro_level * left_ratio)
        right_volume = int(macro_level * right_ratio)
        
        self.block1.fader_value = left_volume
        self.block1.update_fader()  # Update ALSA volume
        self.block2.fader_value = right_volume
        self.block2.update_fader()  # Update ALSA volume
        
        # Update volume displays
        self.vol1_text.setPlainText(str(left_volume))
        self.vol2_text.setPlainText(str(right_volume))
    
    def _on_macro_fader_changed(self, value: int):
        """Handle macro fader changes."""
        # Get crossfader position
        crossfader_pos = self.crossfader.value()
        
        # Calculate pan ratios
        pan = crossfader_pos / 100.0
        left_ratio = math.cos(pan * math.pi / 2)
        right_ratio = math.sin(pan * math.pi / 2)
        
        # Apply to blocks
        left_volume = int(value * left_ratio)
        right_volume = int(value * right_ratio)
        
        self.block1.fader_value = left_volume
        self.block1.update_fader()  # Update ALSA volume
        self.block2.fader_value = right_volume
        self.block2.update_fader()  # Update ALSA volume
        
        # Update volume displays
        self.vol1_text.setPlainText(str(left_volume))
        self.vol2_text.setPlainText(str(right_volume))
    
    def ungroup(self):
        """Ungroup the blocks and restore them."""
        
        # Restore corner rounding for both blocks
        self.block1.left_edge_straight = False
        self.block1.right_edge_straight = False
        self.block2.left_edge_straight = False  
        self.block2.right_edge_straight = False
        
        # Show individual blocks
        self.block1.current_group = None
        self.block2.current_group = None
        self.block1.show()
        self.block2.show()
        
        # Position blocks seamlessly where the group was (240px group -> 2x 120px blocks)
        group_pos = self.scenePos()
        self.block1.setPos(group_pos.x(), group_pos.y())         # Left block at group position
        self.block2.setPos(group_pos.x() + 120, group_pos.y())  # Right block immediately adjacent
        
        # Trigger repaint to show restored corners
        self.block1.update()
        self.block2.update()
        
        # Remove from view's groups list
        if hasattr(self.view, 'groups') and self in self.view.groups:
            self.view.groups.remove(self)
        
        # Remove from scene
        scene = self.scene()
        if scene:
            scene.removeItem(self)

    def paint(self, painter: Optional[QPainter], option, widget):
        """Paint the group widget."""
        if not painter:
            return
            
        painter.setBackgroundMode(Qt.BGMode.OpaqueMode)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Check if either block is a main output
        is_output_group = self.block1.is_output or self.block2.is_output
        
        # Draw background
        painter.setPen(QPen(QColor("#FFD700"), 2))
        if is_output_group:
            painter.setBrush(QBrush(QColor("#4a2a2a")))  # Soft red for output groups
        else:
            painter.setBrush(QBrush(QColor("#2e3036")))  # Lighter Bitwig-style dark grey for input groups
        painter.drawRoundedRect(self.boundingRect(), 12, 12)

    def _update_button_states(self):
        for button_proxy, button, tooltip in self.control_buttons:
            if tooltip in ("Group Mute", "Mute"):
                is_active = self.muted
                color = "#ff0000" if is_active else "#888888"
            elif tooltip in ("Group Solo", "Solo"):
                is_active = self.soloed
                color = "#ffe066" if is_active else "#888888"
            else:
                continue
            button.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    background-color: {color};
                    color: white;
                    border: 2px solid #333;
                    border-radius: {button.width()//2}px;
                    font-size: 6px;
                    font-weight: bold;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {color}aa;
                    border: 2px solid #666;
                }}
                QPushButton:pressed {{
                    background-color: {color}77;
                }}
            """)

    def _update_mute_flash(self, flash_on: bool):
        if not self.muted:
            self._update_button_states()
            return
        if hasattr(self, 'explicit_mute') and self.explicit_mute:
            # Solid red for explicit mute
            for button_proxy, button, tooltip in self.control_buttons:
                if tooltip in ("Group Mute", "Mute"):
                    color = "#ff0000"
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            background-color: {color};
                            color: white;
                            border: 2px solid #333;
                            border-radius: {button.width()//2}px;
                            font-size: 6px;
                            font-weight: bold;
                            padding: 0px;
                        }}
                        QPushButton:hover {{
                            background-color: {color}aa;
                            border: 2px solid #666;
                        }}
                        QPushButton:pressed {{
                            background-color: {color}77;
                        }}
                    """)
            return
        # Flashing for mute-by-solo-logic
        for button_proxy, button, tooltip in self.control_buttons:
            if tooltip in ("Group Mute", "Mute"):
                color = "#ff0000" if flash_on else "#660000"
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        background-color: {color};
                        color: white;
                        border: 2px solid #333;
                        border-radius: {button.width()//2}px;
                        font-size: 6px;
                        font-weight: bold;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {color}aa;
                        border: 2px solid #666;
                    }}
                    QPushButton:pressed {{
                        background-color: {color}77;
                    }}
                """)

    def _update_solo_flash(self, flash_on: bool):
        if not self.soloed:
            self._update_button_states()
            return
        for button_proxy, button, tooltip in self.control_buttons:
            if tooltip in ("Group Solo", "Solo"):
                color = "#ffe066" if flash_on else "#7a6a00"
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        background-color: {color};
                        color: white;
                        border: 2px solid #333;
                        border-radius: {button.width()//2}px;
                        font-size: 6px;
                        font-weight: bold;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {color}aa;
                        border: 2px solid #666;
                    }}
                    QPushButton:pressed {{
                        background-color: {color}77;
                    }}
                """)

    def update_mute_solo_state(self):
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        self.muted = manager.get_mute_state(self.block1.ctl_name)
        self.soloed = manager.get_solo_state(self.block1.ctl_name)
        # Store explicit mute state for correct flashing logic
        self.explicit_mute = False
        if self.block1.ctl_name in manager.channel_states:
            self.explicit_mute = manager.channel_states[self.block1.ctl_name].explicit_mute
        self._update_button_states()


class PatchbayView(QGraphicsView):
    """Main patchbay view with rubber band selection and magnetic snapping."""
    
    def __init__(self, card_index: int):
        super().__init__()
        self.card = card_index
        self.graphics_scene = QGraphicsScene(0, 0, 2000, 2000)
        self.setScene(self.graphics_scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        # Snap settings
        self.SNAP_DISTANCE = 30
        self.groups: List[GroupWidget] = []
        
        # Store blocks by control name for easy lookup
        self.blocks: Dict[str, ChannelBlock] = {}
        
        # Mouse state
        self._panning = False
        self._zoom = 1.0
        self._pan_start = QPointF()
        
        self.populate_blocks()
    
    def populate_blocks(self):
        """Create blocks for all ALSA channels."""
        controls = alsa_backend.list_mixer_controls(self.card)
        
        # Use all available controls instead of test subset
        available_controls = controls
        
        specials = ["Emphasis", "Mask", "PAD", "48V", "Sens.", "Sample Clock", "IEC958"]
        
        x, y = 50, 50
        blocks_created = 0
        
        for ctl in available_controls:
            try:
                mix = alsaaudio.Mixer(control=ctl, cardindex=self.card)
                val = mix.getvolume()[0]
                
                show_fader = (
                    val is not None and val != 137578
                    and not any(kw in ctl for kw in specials)
                )
                
                block = ChannelBlock(ctl, mix, show_fader=show_fader)
                block.setPos(x, y)
                
                self.graphics_scene.addItem(block)
                self.blocks[ctl] = block  # Store in blocks dictionary
                blocks_created += 1
                
                x += ChannelBlock.WIDTH + 30
                if x > 800:
                    x = 50
                    y += ChannelBlock.HEIGHT + 30
                    
            except Exception as e:
                print(f"[ERROR] Failed to create block for {ctl}: {e}")
        
        print(f"[INFO] Created {blocks_created} channel blocks")
        self.update_scene_rect()
    
    def update_scene_rect(self):
        """Update scene rectangle to fit all items."""
        rect = self.graphics_scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
        self.graphics_scene.setSceneRect(rect)
    
    def mousePressEvent(self, event: Optional[QMouseEvent]):
        """Handle mouse press events."""
        if event and event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = QPointF(event.pos())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: Optional[QMouseEvent]):
        """Handle mouse move events."""
        if event and self._panning:
            delta = QPointF(event.pos()) - self._pan_start
            self._pan_start = QPointF(event.pos())
            h_scrollbar = self.horizontalScrollBar()
            v_scrollbar = self.verticalScrollBar()
            if h_scrollbar:
                h_scrollbar.setValue(h_scrollbar.value() - int(delta.x()))
            if v_scrollbar:
                v_scrollbar.setValue(v_scrollbar.value() - int(delta.y()))
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: Optional[QMouseEvent]):
        """Handle mouse release events."""
        if event and event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().mouseReleaseEvent(event)
        
        # Check for snapping
        for item in self.graphics_scene.selectedItems():
            if isinstance(item, ChannelBlock):
                self.check_for_snapping(item)
        
        self.update_scene_rect()
    
    def wheelEvent(self, event: Optional[QWheelEvent]):
        """Handle mouse wheel for zooming."""
        if event and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
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
    
    def check_for_snapping(self, dragged_block: ChannelBlock):
        """Check if the dragged block should snap to another block."""
        dragged_rect = dragged_block.sceneBoundingRect()
        for item in self.graphics_scene.items():
            if isinstance(item, ChannelBlock) and item != dragged_block:
                # Check if this block is already in a group
                if item.current_group:
                    continue
                item_rect = item.sceneBoundingRect()
                
                # Check for edge-to-edge contact (at least 1px overlap on edges)
                # Horizontal edges: left edge of one touches right edge of other
                left_touches_right = abs(dragged_rect.left() - item_rect.right()) <= 1
                right_touches_left = abs(dragged_rect.right() - item_rect.left()) <= 1
                
                # Vertical edges: top edge of one touches bottom edge of other
                top_touches_bottom = abs(dragged_rect.top() - item_rect.bottom()) <= 1
                bottom_touches_top = abs(dragged_rect.bottom() - item_rect.top()) <= 1
                
                # Check for actual edge contact (not just area overlap)
                horizontal_contact = (left_touches_right or right_touches_left) and (
                    dragged_rect.top() < item_rect.bottom() and 
                    dragged_rect.bottom() > item_rect.top()
                )
                
                vertical_contact = (top_touches_bottom or bottom_touches_top) and (
                    dragged_rect.left() < item_rect.right() and 
                    dragged_rect.right() > item_rect.left()
                )
                
                if horizontal_contact or vertical_contact:
                    if not dragged_block.current_group:
                        self.create_group(dragged_block, item)
                    break
    
    def create_group(self, block1: ChannelBlock, block2: ChannelBlock):
        """Create a new group with two blocks."""
        
        # Create group widget
        group = GroupWidget(block1, block2, self)
        self.graphics_scene.addItem(group)
        self.groups.append(group)
        
        # Position blocks side-by-side for seamless transition
        pos1 = block1.scenePos()
        pos2 = block2.scenePos()
        center_x = (pos1.x() + pos2.x()) / 2
        center_y = (pos1.y() + pos2.y()) / 2
        
        # Animate blocks to side-by-side positions (120px apart)
        left_x = center_x - 60   # Left block position (half width from center)
        right_x = center_x + 60  # Right block position (half width from center)
        
        self._animate_block_to_position(block1, left_x, center_y)
        self._animate_block_to_position(block2, right_x, center_y)
    
    def _animate_block_to_position(self, block: ChannelBlock, x: float, y: float):
        """Animate a block to a new position."""
        animation = QPropertyAnimation(block, b"pos")
        animation.setDuration(300)
        animation.setStartValue(block.pos())
        animation.setEndValue(QPointF(x, y))
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()

    def serialize_state(self):
        """Serialize the current patchbay state to a dict."""
        state = {
            'blocks': [],
            'groups': [],
            'view_transform': {
                'zoom': self._zoom,
                'center': (self.mapToScene(self.viewport().rect().center()).x(),
                          self.mapToScene(self.viewport().rect().center()).y())
            }
        }
        
        # Serialize individual blocks
        for item in self.graphics_scene.items():
            if isinstance(item, ChannelBlock):
                block_state = {
                    'ctl_name': item.ctl_name,
                    'position': (item.pos().x(), item.pos().y()),
                    'fader_value': item.fader_value,
                    'muted': item.muted,
                    'soloed': item.soloed,
                    'channel_type': item.channel_type,
                    'show_fader': item.show_fader
                }
                state['blocks'].append(block_state)
        
        # Serialize groups
        for group in self.groups:
            group_state = {
                'block1_ctl': group.block1.ctl_name,
                'block2_ctl': group.block2.ctl_name,
                'position': (group.pos().x(), group.pos().y()),
                'crossfader_value': group.crossfader.value(),
                'macro_fader_value': group.macro_fader.value(),
                'muted': group.muted,
                'soloed': group.soloed
            }
            state['groups'].append(group_state)
        
        return state

    def deserialize_state(self, state):
        """Restore the patchbay state from a dict."""
        try:
            # Clear existing state
            self.graphics_scene.clear()
            self.groups.clear()
            self.blocks.clear()  # Clear the blocks dictionary
            
            # Restore view transform
            if 'view_transform' in state:
                transform = state['view_transform']
                self._zoom = transform.get('zoom', 1.0)
                self.resetTransform()
                self.scale(self._zoom, self._zoom)
                
                center = transform.get('center', (0, 0))
                self.centerOn(center[0], center[1])
            
            # Restore blocks
            if 'blocks' in state:
                for block_state in state['blocks']:
                    ctl_name = block_state['ctl_name']
                    try:
                        mixer = alsaaudio.Mixer(control=ctl_name, cardindex=self.card)
                        block = ChannelBlock(ctl_name, mixer, block_state.get('show_fader', True))
                        
                        # Set position
                        pos = block_state.get('position', (0, 0))
                        block.setPos(pos[0], pos[1])
                        
                        # Set fader value
                        fader_value = block_state.get('fader_value', 50)
                        block.fader_value = fader_value
                        if hasattr(block, 'fader') and block.fader:
                            block.fader.setValue(fader_value)
                        
                        # Set mute/solo state
                        block.muted = block_state.get('muted', False)
                        block.soloed = block_state.get('soloed', False)
                        block.update_mute_solo_state()
                        
                        # Add to scene and blocks list
                        self.graphics_scene.addItem(block)
                        self.blocks[ctl_name] = block
                        
                    except Exception as e:
                        print(f"[WARNING] Failed to restore block {ctl_name}: {e}")
            
            # Restore groups
            if 'groups' in state:
                for group_state in state['groups']:
                    block1_ctl = group_state['block1_ctl']
                    block2_ctl = group_state['block2_ctl']
                    
                    if block1_ctl in self.blocks and block2_ctl in self.blocks:
                        block1 = self.blocks[block1_ctl]
                        block2 = self.blocks[block2_ctl]
                        
                        # Create group
                        group = GroupWidget(block1, block2, self)
                        
                        # Set position
                        pos = group_state.get('position', (0, 0))
                        group.setPos(pos[0], pos[1])
                        
                        # Set fader values
                        crossfader_value = group_state.get('crossfader_value', 50)
                        macro_fader_value = group_state.get('macro_fader_value', 50)
                        group.crossfader.setValue(crossfader_value)
                        group.macro_fader.setValue(macro_fader_value)
                        
                        # Set mute/solo state
                        group.muted = group_state.get('muted', False)
                        group.soloed = group_state.get('soloed', False)
                        group.update_mute_solo_state()
                        
                        # Add to scene and groups list
                        self.graphics_scene.addItem(group)
                        self.groups.append(group)
            
            self.update_scene_rect()
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to deserialize patchbay state: {e}")
            return False


# Custom QSlider with oval groove and circular handle
class OvalGrooveSlider(QSlider):
    def __init__(self, orientation, handle_color="#3f7fff", groove_color="#222", parent=None):
        super().__init__(orientation, parent)
        self.handle_color = handle_color
        self.groove_color = groove_color
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    
    def wheelEvent(self, event):
        """Override wheelEvent to forward to parent."""
        # Ignore the event so it propagates to the parent (ChannelBlock)
        event.ignore()
        return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        # Groove geometry
        if self.orientation() == Qt.Orientation.Vertical:
            groove_w = 16
            groove_h = self.height() - 12
            groove_x = (self.width() - groove_w) // 2
            groove_y = 6
            groove_rect = QRectF(groove_x, groove_y, groove_w, groove_h)
            radius = groove_w / 2
        else:
            groove_h = 16
            groove_w = self.width() - 12
            groove_x = 6
            groove_y = (self.height() - groove_h) // 2
            groove_rect = QRectF(groove_x, groove_y, groove_w, groove_h)
            radius = groove_h / 2

        # Draw groove (oval)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.groove_color))
        painter.drawRoundedRect(groove_rect, radius, radius)

        # Draw handle (circle)
        handle_size = 16
        if self.orientation() == Qt.Orientation.Vertical:
            slider_min = groove_y
            slider_max = groove_y + groove_h - handle_size
            val = (self.maximum() - self.value()) / (self.maximum() - self.minimum()) if self.maximum() != self.minimum() else 0
            handle_y = slider_min + val * (slider_max - slider_min)
            handle_x = (self.width() - handle_size) // 2
            handle_rect = QRectF(handle_x, handle_y, handle_size, handle_size)
        else:
            slider_min = groove_x
            slider_max = groove_x + groove_w - handle_size
            val = (self.value() - self.minimum()) / (self.maximum() - self.minimum()) if self.maximum() != self.minimum() else 0
            handle_x = slider_min + val * (slider_max - slider_min)
            handle_y = (self.height() - handle_size) // 2
            handle_rect = QRectF(handle_x, handle_y, handle_size, handle_size)

        painter.setBrush(QColor(self.handle_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(handle_rect)

        # Draw focus/disabled if needed
        if not self.isEnabled():
            painter.setBrush(QColor(0, 0, 0, 80))
            painter.drawEllipse(handle_rect)

        painter.end()


def main():
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Patchbay2 - Simple Grouping")
    window.setGeometry(100, 100, 1400, 900)
    
    # Create central widget
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    # Create layout
    layout = QVBoxLayout(central_widget)
    
    # Create patchbay view
    patchbay = PatchbayView(1)  # Use card 1
    layout.addWidget(patchbay)
    
    # Show window
    window.show()
    
    # Start the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 