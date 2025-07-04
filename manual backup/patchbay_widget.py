#!/usr/bin/env python3
"""
Patchbay Widget - Wrapper for PatchbayView with layout management
- Combines patchbay view with save/load layout buttons
- Integrates with layout manager
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from patchbay import PatchbayView
from layout_manager import LayoutManager
from layout_dialog import LayoutDialog


class PatchbayWidget(QWidget):
    """Wrapper widget that combines patchbay view with layout management."""
    
    def __init__(self, card_index: int = 1):
        super().__init__()
        self.card_index = card_index
        self.layout_manager = LayoutManager()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top toolbar with layout management buttons
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-bottom: 1px solid #555;
            }
        """)
        
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        # Title
        title = QLabel("Patchbay Layout")
        title.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFD700;")
        toolbar_layout.addWidget(title)
        
        toolbar_layout.addStretch()
        
        # Layout management buttons
        self.save_btn = QPushButton("Save Layout")
        self.save_btn.clicked.connect(self.show_save_dialog)
        self.save_btn.setStyleSheet("""
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
        """)
        toolbar_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton("Load Layout")
        self.load_btn.clicked.connect(self.show_load_dialog)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #44aa44;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #338833;
            }
            QPushButton:pressed {
                background-color: #226622;
            }
        """)
        toolbar_layout.addWidget(self.load_btn)
        
        layout.addWidget(toolbar)
        
        # Patchbay view
        self.patchbay_view = PatchbayView(self.card_index)
        layout.addWidget(self.patchbay_view)
    
    def show_save_dialog(self):
        """Show the save layout dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Save Layout")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Enter layout name...")
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # Description input
        layout.addWidget(QLabel("Description:"))
        desc_edit = QTextEdit()
        desc_edit.setMaximumHeight(100)
        desc_edit.setPlaceholderText("Enter layout description...")
        layout.addWidget(desc_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Connect buttons
        def save_layout():
            name = name_edit.text().strip()
            description = desc_edit.toPlainText().strip()
            
            if not name:
                QMessageBox.warning(dialog, "Error", "Please enter a layout name.")
                return
            
            # Check if layout already exists
            existing_layouts = self.layout_manager.list_layouts()
            if name in existing_layouts:
                reply = QMessageBox.question(
                    dialog,
                    "Overwrite Layout",
                    f"Layout '{name}' already exists. Overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Create and save layout
            layout_obj = self.layout_manager.create_layout_from_patchbay(
                self.patchbay_view,
                name,
                description
            )
            
            if self.layout_manager.save_layout(layout_obj):
                QMessageBox.information(dialog, "Success", f"Layout '{name}' saved successfully.")
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Error", f"Failed to save layout '{name}'.")
        
        save_btn.clicked.connect(save_layout)
        cancel_btn.clicked.connect(dialog.reject)
        
        # Set focus to name field
        name_edit.setFocus()
        
        dialog.exec()
    
    def show_load_dialog(self):
        """Show the load layout dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Layout")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Layout list
        layout.addWidget(QLabel("Available Layouts:"))
        layout_list = QListWidget()
        layout.addWidget(layout_list)
        
        # Populate list
        layouts = self.layout_manager.list_layouts()
        for layout_name in layouts:
            item = QListWidgetItem(layout_name)
            layout_list.addItem(item)
        
        # Buttons
        button_layout = QHBoxLayout()
        load_btn = QPushButton("Load")
        delete_btn = QPushButton("Delete")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(load_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Connect buttons
        def load_selected():
            item = layout_list.currentItem()
            if not item:
                QMessageBox.warning(dialog, "Error", "Please select a layout to load.")
                return
            
            layout_name = item.text()
            
            # Confirm loading
            reply = QMessageBox.question(
                dialog,
                "Load Layout",
                f"Load layout '{layout_name}'? This will replace the current patchbay arrangement.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.load_layout(layout_name)
                dialog.accept()
        
        def delete_selected():
            item = layout_list.currentItem()
            if not item:
                QMessageBox.warning(dialog, "Error", "Please select a layout to delete.")
                return
            
            layout_name = item.text()
            
            # Confirm deletion
            reply = QMessageBox.question(
                dialog,
                "Delete Layout",
                f"Delete layout '{layout_name}'? This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.layout_manager.delete_layout(layout_name):
                    # Remove from list
                    layout_list.takeItem(layout_list.row(item))
                    QMessageBox.information(dialog, "Success", f"Layout '{layout_name}' deleted.")
                else:
                    QMessageBox.warning(dialog, "Error", f"Failed to delete layout '{layout_name}'.")
        
        load_btn.clicked.connect(load_selected)
        delete_btn.clicked.connect(delete_selected)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def load_layout(self, layout_name: str):
        """Load a specific layout."""
        layout = self.layout_manager.load_layout(layout_name)
        if layout:
            success = self.layout_manager.apply_layout_to_patchbay(
                layout, self.patchbay_view
            )
            if success:
                # Update the scene rect after loading
                self.patchbay_view.update_scene_rect()
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to apply layout '{layout_name}'."
                )
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                f"Could not load layout '{layout_name}'."
            )
    
    def save_current_layout(self, name: str, description: str = ""):
        """Save the current patchbay state as a layout."""
        layout = self.layout_manager.create_layout_from_patchbay(
            self.patchbay_view,
            name,
            description
        )
        return self.layout_manager.save_layout(layout) 