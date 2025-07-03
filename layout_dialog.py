#!/usr/bin/env python3
"""
Layout Dialog for Patchbay
- Save current layout with name and description
- Load existing layouts
- Delete layouts
- List all available layouts
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QGroupBox,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from layout_manager import LayoutManager, PatchbayLayout


class LayoutDialog(QDialog):
    """Dialog for managing patchbay layouts."""
    
    layout_loaded = pyqtSignal(str)  # Signal emitted when a layout is loaded
    
    def __init__(self, layout_manager: LayoutManager, patchbay_view=None, parent=None):
        super().__init__(parent)
        self.layout_manager = layout_manager
        self.patchbay_view = patchbay_view
        self.setup_ui()
        self.refresh_layout_list()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Patchbay Layout Manager")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Create splitter for left/right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel: Layout list and actions
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        
        # Layout list
        list_group = QGroupBox("Available Layouts")
        list_layout = QVBoxLayout(list_group)
        
        self.layout_list = QListWidget()
        self.layout_list.itemClicked.connect(self.on_layout_selected)
        list_layout.addWidget(self.layout_list)
        
        # List action buttons
        list_buttons = QHBoxLayout()
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self.load_selected_layout)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_selected_layout)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_layout_list)
        
        list_buttons.addWidget(self.load_btn)
        list_buttons.addWidget(self.delete_btn)
        list_buttons.addWidget(self.refresh_btn)
        list_layout.addLayout(list_buttons)
        
        left_layout.addWidget(list_group)
        splitter.addWidget(left_panel)
        
        # Right panel: Save new layout
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        
        save_group = QGroupBox("Save Current Layout")
        save_layout = QVBoxLayout(save_group)
        
        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter layout name...")
        name_layout.addWidget(self.name_edit)
        save_layout.addLayout(name_layout)
        
        # Description input
        save_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("Enter layout description...")
        save_layout.addWidget(self.desc_edit)
        
        # Save button
        self.save_btn = QPushButton("Save Layout")
        self.save_btn.clicked.connect(self.save_current_layout)
        save_layout.addWidget(self.save_btn)
        
        right_layout.addWidget(save_group)
        right_layout.addStretch()
        
        # Bottom buttons
        bottom_buttons = QHBoxLayout()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        bottom_buttons.addStretch()
        bottom_buttons.addWidget(self.close_btn)
        
        layout.addLayout(bottom_buttons)
        
        splitter.setSizes([300, 300])
        
        # Ensure both panels are visible
        splitter.setMinimumWidth(600)
        splitter.setMinimumHeight(400)
        
        # Set styles
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #3f7fff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2d5fcc;
            }
            QPushButton:pressed {
                background-color: #1f4faa;
            }
            QPushButton:disabled {
                background-color: #666;
            }
            QListWidget {
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #2a2a2a;
                color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #3f7fff;
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
                background-color: #2a2a2a;
                color: white;
            }
            QLabel {
                color: white;
            }
        """)
    
    def refresh_layout_list(self):
        """Refresh the list of available layouts."""
        self.layout_list.clear()
        layouts = self.layout_manager.list_layouts()
        
        for layout_name in layouts:
            item = QListWidgetItem(layout_name)
            self.layout_list.addItem(item)
        
        # Update button states
        self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = self.layout_list.currentItem() is not None
        self.load_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def on_layout_selected(self, item):
        """Handle layout selection."""
        self.update_button_states()
    
    def load_selected_layout(self):
        """Load the selected layout."""
        item = self.layout_list.currentItem()
        if not item:
            return
        
        layout_name = item.text()
        
        # Confirm loading
        reply = QMessageBox.question(
            self,
            "Load Layout",
            f"Load layout '{layout_name}'? This will replace the current patchbay arrangement.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.layout_loaded.emit(layout_name)
            self.accept()
    
    def delete_selected_layout(self):
        """Delete the selected layout."""
        item = self.layout_list.currentItem()
        if not item:
            return
        
        layout_name = item.text()
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Layout",
            f"Delete layout '{layout_name}'? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.layout_manager.delete_layout(layout_name):
                self.refresh_layout_list()
                QMessageBox.information(self, "Success", f"Layout '{layout_name}' deleted.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete layout '{layout_name}'.")
    
    def save_current_layout(self):
        """Save the current patchbay state as a new layout."""
        name = self.name_edit.text().strip()
        description = self.desc_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a layout name.")
            return
        
        # Check if layout already exists
        existing_layouts = self.layout_manager.list_layouts()
        if name in existing_layouts:
            reply = QMessageBox.question(
                self,
                "Overwrite Layout",
                f"Layout '{name}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Create layout from current patchbay state
        if self.patchbay_view:
            layout = self.layout_manager.create_layout_from_patchbay(
                self.patchbay_view,
                name,
                description
            )
            
            if self.layout_manager.save_layout(layout):
                self.refresh_layout_list()
                self.name_edit.clear()
                self.desc_edit.clear()
                QMessageBox.information(self, "Success", f"Layout '{name}' saved successfully.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to save layout '{name}'.")
        else:
            QMessageBox.warning(self, "Error", "No patchbay view available.") 