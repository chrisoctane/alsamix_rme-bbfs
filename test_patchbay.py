#!/usr/bin/env python3
"""
Test script for patchbay functionality
"""

import sys
from PyQt6.QtWidgets import QApplication
from patchbay import PatchbayView

def test_patchbay():
    """Test basic patchbay functionality"""
    app = QApplication(sys.argv)
    
    # Create patchbay view
    patchbay = PatchbayView(card_index=1)
    patchbay.setWindowTitle("Patchbay Test")
    patchbay.resize(1200, 800)
    patchbay.show()
    
    print("Patchbay test window opened. Test the following:")
    print("1. Drag channels around")
    print("2. Snap channels together")
    print("3. Use mute/solo buttons")
    print("4. Test group widgets")
    print("5. Save/load layout")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_patchbay()) 