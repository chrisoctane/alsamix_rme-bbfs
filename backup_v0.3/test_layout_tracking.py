#!/usr/bin/env python3
"""
Test script to verify layout tracking functionality.
"""

import sys
from PyQt6.QtWidgets import QApplication
from layout_manager import get_layout_manager
from patchbay_widget import PatchbayWidget

def test_layout_tracking():
    """Test that layout tracking works correctly."""
    print("=== Testing Layout Tracking ===\n")
    
    # Create a patchbay widget
    patchbay_widget = PatchbayWidget()
    print(f"1. Initial current_layout_name: {patchbay_widget.current_layout_name}")
    
    # Test get_current_layout_name
    layout_manager = get_layout_manager()
    current_name = layout_manager.get_current_layout_name(patchbay_widget)
    print(f"2. Layout manager reports current layout: {current_name}")
    
    # Change the current layout name
    patchbay_widget.current_layout_name = "test_layout"
    print(f"3. Changed current_layout_name to: {patchbay_widget.current_layout_name}")
    
    # Test get_current_layout_name again
    current_name = layout_manager.get_current_layout_name(patchbay_widget)
    print(f"4. Layout manager reports current layout: {current_name}")
    
    # Test with patchbay_view attribute
    patchbay_widget.patchbay_view.current_layout_name = "nested_layout"
    print(f"5. Set nested current_layout_name to: {patchbay_widget.patchbay_view.current_layout_name}")
    
    current_name = layout_manager.get_current_layout_name(patchbay_widget)
    print(f"6. Layout manager reports current layout: {current_name}")
    
    print("\n✅ Layout tracking test completed!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_layout_tracking() 