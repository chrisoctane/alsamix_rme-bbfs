#!/usr/bin/env python3
"""
Create default patchbay layouts that correspond to the preset names.
"""

import json
from pathlib import Path
from layout_manager import LayoutManager, PatchbayLayout, BlockLayout, GroupLayout

def create_default_layouts():
    """Create default patchbay layouts."""
    layout_manager = LayoutManager()
    
    # Default layout - clean, organized arrangement
    default_blocks = [
        BlockLayout("Main-Out AN1", 50, 50, 70, False, False, True, "output"),
        BlockLayout("Main-Out AN2", 200, 50, 70, False, False, True, "output"),
        BlockLayout("Main-Out PH3", 350, 50, 50, False, False, True, "output"),
        BlockLayout("Main-Out PH4", 500, 50, 50, False, False, True, "output"),
        BlockLayout("Mic-AN1 Gain", 50, 200, 0, False, False, True, "mic"),
        BlockLayout("Mic-AN2 Gain", 200, 200, 0, False, False, True, "mic"),
        BlockLayout("Line-IN3 Gain", 350, 200, 0, False, False, True, "line"),
        BlockLayout("Line-IN4 Gain", 500, 200, 0, False, False, True, "line"),
    ]
    
    default_layout = PatchbayLayout(
        name="default",
        description="Default patchbay layout - clean and organized",
        blocks=default_blocks,
        groups=[],
        version="1.0"
    )
    
    # Live layout - optimized for live performance
    live_blocks = [
        BlockLayout("Main-Out AN1", 50, 50, 80, False, False, True, "output"),
        BlockLayout("Main-Out AN2", 200, 50, 80, False, False, True, "output"),
        BlockLayout("Main-Out PH3", 350, 50, 60, False, False, True, "output"),
        BlockLayout("Main-Out PH4", 500, 50, 60, False, False, True, "output"),
        BlockLayout("Mic-AN1 Gain", 50, 200, 20, False, False, True, "mic"),
        BlockLayout("Mic-AN2 Gain", 200, 200, 20, False, False, True, "mic"),
        BlockLayout("Line-IN3 Gain", 350, 200, 0, False, False, True, "line"),
        BlockLayout("Line-IN4 Gain", 500, 200, 0, False, False, True, "line"),
    ]
    
    live_layout = PatchbayLayout(
        name="live",
        description="Live performance patchbay layout",
        blocks=live_blocks,
        groups=[],
        version="1.0"
    )
    
    # Studio layout - optimized for studio recording
    studio_blocks = [
        BlockLayout("Main-Out AN1", 50, 50, 60, False, False, True, "output"),
        BlockLayout("Main-Out AN2", 200, 50, 60, False, False, True, "output"),
        BlockLayout("Main-Out PH3", 350, 50, 40, False, False, True, "output"),
        BlockLayout("Main-Out PH4", 500, 50, 40, False, False, True, "output"),
        BlockLayout("Mic-AN1 Gain", 50, 200, 0, False, False, True, "mic"),
        BlockLayout("Mic-AN2 Gain", 200, 200, 0, False, False, True, "mic"),
        BlockLayout("Line-IN3 Gain", 350, 200, 0, False, False, True, "line"),
        BlockLayout("Line-IN4 Gain", 500, 200, 0, False, False, True, "line"),
    ]
    
    studio_layout = PatchbayLayout(
        name="studio",
        description="Studio recording patchbay layout",
        blocks=studio_blocks,
        groups=[],
        version="1.0"
    )
    
    # Save all layouts
    layouts = [default_layout, live_layout, studio_layout]
    
    for layout in layouts:
        if layout_manager.save_layout(layout):
            print(f"[INFO] Created layout: {layout.name}")
        else:
            print(f"[ERROR] Failed to create layout: {layout.name}")
    
    print(f"[INFO] Created {len(layouts)} default layouts")

if __name__ == "__main__":
    create_default_layouts() 