"""
Configuration constants for the RME Babyface Pro FS mixer application.
"""

from PyQt6.QtGui import QColor

# Snap and Group Settings
SNAP_THRESHOLD = 20  # pixels - increased for easier snapping
SNAP_ALIGN_THRESHOLD = 30  # pixels for alignment within snap
MIN_ORTHOGONAL_OVERLAP = 10  # pixels required for snap on orthogonal axis

# Visual Settings
GROUP_OUTLINE_COLOR = QColor("#3f7fff")
SNAP_TARGET_COLOR = QColor("#FFD700")
SELECTION_COLOR = QColor("#FFD700")
GROUP_OUTLINE_WIDTH = 3
SNAP_TARGET_WIDTH = 3
SELECTION_WIDTH = 3
GROUP_CORNER_RADIUS = 12
BLOCK_CORNER_RADIUS = 8

# Mute/Solo Colors
MUTE_COLOR = QColor("#ff4444")
SOLO_COLOR = QColor("#44ff44")
MUTE_ACTIVE_COLOR = QColor("#ff0000")
SOLO_ACTIVE_COLOR = QColor("#00ff00")

# Channel Block Settings
CHANNEL_WIDTH = 210
CHANNEL_HEIGHT = 200
HANDLE_WIDTH = 24
HANDLE_COLOR = QColor("#aaa")
HANDLE_TEXT_COLOR = QColor("#FFD700")
FADER_BAR_WIDTH = 28
BUTTON_SIZE = 20

# Label Colors
OUTPUT_LABEL_COLOR = QColor("#18192b")  # dark, for outputs
NONFADER_LABEL_COLOR = QColor("#ffc9c9")  # slightly darker pastel red
FADER_LABEL_COLOR = QColor("#394050")
LABEL_RADIUS = 10

# Group Container Settings
GROUP_HANDLE_WIDTH = 24
GROUP_HANDLE_COLOR = QColor("#aaa")
GROUP_HANDLE_HOVER_COLOR = QColor("#FFD700")
GROUP_HANDLE_TEXT_COLOR = QColor("#222")
GROUP_CORNER_RADIUS = 12

# Layout Settings
DEFAULT_WINDOW_WIDTH = 1450
DEFAULT_WINDOW_HEIGHT = 500
ALSA_POLLING_INTERVAL = 0.5  # seconds

# File Settings
DEFAULT_LAYOUT_FILENAME = "patchbay_layout.json" 