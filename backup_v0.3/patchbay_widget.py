#!/usr/bin/env python3
"""
Patchbay Widget - Wrapper for PatchbayView with layout management
- Combines patchbay view with save/load layout buttons
- Integrates with layout manager
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from patchbay import PatchbayView
from layout_manager import LayoutManager


class PatchbayWidget(QWidget):
    """Wrapper widget that combines patchbay view with layout management."""
    
    def __init__(self, card_index: int = 1):
        super().__init__()
        self.card_index = card_index
        self.layout_manager = LayoutManager()
        self.current_layout_name = "default"  # Track current layout
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Simple title bar
        title_bar = QFrame()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-bottom: 1px solid #555;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        
        # Title
        title = QLabel("Patchbay")
        title.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFD700;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # Info label
        info_label = QLabel("Use Presets button to manage layouts")
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        title_layout.addWidget(info_label)
        
        layout.addWidget(title_bar)
        
        # Patchbay view
        self.patchbay_view = PatchbayView(self.card_index)
        layout.addWidget(self.patchbay_view)

    def serialize_state(self):
        """Serialize the current patchbay state to a dict."""
        if hasattr(self, 'patchbay_view') and hasattr(self.patchbay_view, 'serialize_state'):
            return self.patchbay_view.serialize_state()
        return {}

    def deserialize_state(self, state):
        """Restore the patchbay state from a dict."""
        if hasattr(self, 'patchbay_view') and hasattr(self.patchbay_view, 'deserialize_state'):
            return self.patchbay_view.deserialize_state(state)
        return False

    
 