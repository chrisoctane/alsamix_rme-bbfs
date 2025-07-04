#!/usr/bin/env python3
"""
Professional Audio Mixer Preset Dialog
- Simple, fast preset management like real audio software
- Focuses on logical configurations, not UI layouts
- Always includes patchbay layout with presets
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QTextEdit, QProgressBar,
    QMessageBox, QGroupBox, QGridLayout, QSplitter, QWidget, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from preset_manager import get_preset_manager


class PresetDialog(QDialog):
    """Professional preset management dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preset_manager = get_preset_manager()
        self.setup_ui()
        self.refresh_preset_list()
        
        # Create default presets if none exist
        if not self.preset_manager.list_presets():
            self.preset_manager.create_default_presets()
            self.refresh_preset_list()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Mixer Presets")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - preset list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Preset list
        list_group = QGroupBox("Available Presets")
        list_layout = QVBoxLayout(list_group)
        
        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self.on_preset_selected)
        list_layout.addWidget(self.preset_list)
        
        # Preset buttons
        button_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Load Preset")
        self.load_button.clicked.connect(self.load_selected_preset)
        self.load_button.setEnabled(False)
        
        self.save_button = QPushButton("Save Current")
        self.save_button.clicked.connect(self.save_current_preset)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_selected_preset)
        self.delete_button.setEnabled(False)
        
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.delete_button)
        
        list_layout.addLayout(button_layout)
        left_layout.addWidget(list_group)
        
        # Right side - preset details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Preset details
        details_group = QGroupBox("Preset Details")
        details_layout = QGridLayout(details_group)
        
        details_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        details_layout.addWidget(self.name_edit, 0, 1)
        
        details_layout.addWidget(QLabel("Description:"), 1, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        details_layout.addWidget(self.description_edit, 1, 1)
        
        right_layout.addWidget(details_group)
        
        # Preset contents
        contents_group = QGroupBox("Preset Contents")
        contents_layout = QVBoxLayout(contents_group)
        
        self.contents_label = QLabel("Select a preset to view its contents")
        self.contents_label.setWordWrap(True)
        contents_layout.addWidget(self.contents_label)
        
        right_layout.addWidget(contents_group)
        
        # Load options
        options_group = QGroupBox("Load Options")
        options_layout = QVBoxLayout(options_group)
        
        self.load_patchbay_checkbox = QCheckBox("Load patchbay layout with preset")
        self.load_patchbay_checkbox.setToolTip("Always loads the corresponding patchbay layout")
        self.load_patchbay_checkbox.setChecked(True)  # Default to checked and disabled
        self.load_patchbay_checkbox.setEnabled(False)  # Always enabled, can't disable
        options_layout.addWidget(self.load_patchbay_checkbox)
        
        right_layout.addWidget(options_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_button)
        
        layout.addLayout(bottom_layout)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 300])
        
        # Set up timer for progress updates
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.current_operation = 0
        self.total_operations = 0
    
    def refresh_preset_list(self):
        """Refresh the preset list."""
        self.preset_list.clear()
        presets = self.preset_manager.list_presets()
        
        for preset_name in presets:
            item = QListWidgetItem(preset_name)
            self.preset_list.addItem(item)
    
    def on_preset_selected(self, item):
        """Handle preset selection."""
        preset_name = item.text()
        preset = self.preset_manager.load_preset(preset_name)
        
        if preset:
            self.name_edit.setText(preset.name)
            self.description_edit.setPlainText(preset.description)
            
            # Show preset contents
            contents = []
            if preset.alsa_state:
                contents.append(f"ALSA Controls: {len(preset.alsa_state)} total")
            if preset.main_mix_levels:
                contents.append(f"Main Mix Levels: {len(preset.main_mix_levels)} outputs")
            if preset.input_gains:
                contents.append(f"Input Gains: {len(preset.input_gains)} inputs")
            if preset.hardware_settings:
                contents.append(f"Hardware Settings: {len(preset.hardware_settings)} settings")
            if preset.routing_matrix:
                contents.append(f"Routing Matrix: {len(preset.routing_matrix)} destinations")
            if preset.patchbay_state:
                blocks = preset.patchbay_state.get('blocks', [])
                groups = preset.patchbay_state.get('groups', [])
                contents.append(f"Patchbay: {len(blocks)} blocks, {len(groups)} groups")
            
            if contents:
                self.contents_label.setText("\n".join(contents))
            else:
                self.contents_label.setText("No settings in this preset")
            
            # Enable buttons
            self.load_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.contents_label.setText("Failed to load preset")
            self.load_button.setEnabled(False)
            self.delete_button.setEnabled(False)
    
    def load_selected_preset(self):
        """Load the selected preset."""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
        
        preset_name = current_item.text()
        preset = self.preset_manager.load_preset(preset_name)
        
        if not preset:
            QMessageBox.warning(self, "Error", f"Failed to load preset: {preset_name}")
            return
        
        # Show progress dialog
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        def progress_callback(current, total, message):
            if total > 0:
                progress = int((current / total) * 100)
                self.progress_bar.setValue(progress)
                self.progress_bar.setFormat(f"{message} ({current}/{total})")
        
        # Get patchbay widget
        patchbay_widget = None
        try:
            from outputs import OutputsTabs
            outputs_tabs = self.parent()
            if hasattr(outputs_tabs, 'patchbay_view'):
                patchbay_widget = outputs_tabs.patchbay_view
        except Exception as e:
            print(f"[WARNING] Could not get patchbay widget: {e}")
        
        # Apply the preset (includes ALSA and patchbay state)
        success = self.preset_manager.apply_preset(preset, progress_callback, patchbay_widget)
        
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Success", f"Preset '{preset_name}' loaded successfully!")
        else:
            QMessageBox.warning(self, "Error", f"Failed to apply preset: {preset_name}")
    
    def save_current_preset(self):
        """Save current state as a new preset."""
        name = self.name_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a preset name")
            return
        
        # Check if preset already exists
        existing_presets = self.preset_manager.list_presets()
        if name in existing_presets:
            reply = QMessageBox.question(
                self, "Overwrite Preset",
                f"Preset '{name}' already exists. Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Get patchbay widget
        patchbay_widget = None
        try:
            from outputs import OutputsTabs
            outputs_tabs = self.parent()
            if hasattr(outputs_tabs, 'patchbay_view'):
                patchbay_widget = outputs_tabs.patchbay_view
        except Exception as e:
            print(f"[WARNING] Could not get patchbay widget: {e}")
        
        # Create preset from current state (includes ALSA and patchbay state)
        preset = self.preset_manager.create_preset_from_current_state(name, description, patchbay_widget)
        
        # Save the preset
        if self.preset_manager.save_preset(preset):
            QMessageBox.information(self, "Success", f"Preset '{name}' saved successfully!")
            self.refresh_preset_list()
        else:
            QMessageBox.warning(self, "Error", f"Failed to save preset: {name}")
    
    def delete_selected_preset(self):
        """Delete the selected preset."""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
        
        preset_name = current_item.text()
        
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Are you sure you want to delete preset '{preset_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.preset_manager.delete_preset(preset_name):
                QMessageBox.information(self, "Success", f"Preset '{preset_name}' deleted successfully!")
                self.refresh_preset_list()
                self.contents_label.setText("Select a preset to view its contents")
                self.load_button.setEnabled(False)
                self.delete_button.setEnabled(False)
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete preset: {preset_name}")
    
    def update_progress(self):
        """Update progress bar (placeholder for future enhancements)."""
        pass


def show_preset_dialog(parent=None):
    """Show the preset dialog."""
    dialog = PresetDialog(parent)
    dialog.exec() 