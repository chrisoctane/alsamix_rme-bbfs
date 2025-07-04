"""
main.py

Launches the main mixer window (outputs tabs).
"""

import sys
from PyQt6.QtWidgets import QApplication
from outputs import OutputsTabs

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = OutputsTabs()
    win.setWindowTitle("Babyface Pro FS Mixer")
    win.resize(1450, 500)
    win.show()
    sys.exit(app.exec())
