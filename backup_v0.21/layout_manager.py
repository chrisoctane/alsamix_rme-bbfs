#!/usr/bin/env python3
"""
Layout Manager for Patchbay
- Save/load patchbay layouts in JSON format
- Store block positions, groups, and channel states
- Support multiple session types
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class BlockLayout:
    """Represents the layout state of a single channel block."""
    ctl_name: str
    x: float
    y: float
    fader_value: int
    muted: bool
    soloed: bool
    show_fader: bool
    channel_type: str


@dataclass
class GroupLayout:
    """Represents the layout state of a group widget."""
    block1_name: str
    block2_name: str
    x: float
    y: float
    macro_fader_value: int
    crossfader_value: int
    muted: bool
    soloed: bool


@dataclass
class PatchbayLayout:
    """Complete patchbay layout including blocks and groups."""
    name: str
    description: str
    blocks: List[BlockLayout]
    groups: List[GroupLayout]
    version: str = "1.0"


class LayoutManager:
    """Manages saving and loading of patchbay layouts."""
    
    def __init__(self, layouts_dir: str = "layouts"):
        self.layouts_dir = Path(layouts_dir)
        self.layouts_dir.mkdir(exist_ok=True)
    
    def save_layout(self, layout: PatchbayLayout) -> bool:
        """Save a layout to a JSON file."""
        try:
            filename = f"{layout.name.replace(' ', '_').lower()}.json"
            filepath = self.layouts_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(asdict(layout), f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving layout: {e}")
            return False
    
    def load_layout(self, name: str) -> Optional[PatchbayLayout]:
        """Load a layout from a JSON file."""
        try:
            filename = f"{name.replace(' ', '_').lower()}.json"
            filepath = self.layouts_dir / filename
            
            if not filepath.exists():
                return None
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Reconstruct the layout object
            blocks = [BlockLayout(**block_data) for block_data in data.get('blocks', [])]
            groups = [GroupLayout(**group_data) for group_data in data.get('groups', [])]
            
            return PatchbayLayout(
                name=data['name'],
                description=data.get('description', ''),
                blocks=blocks,
                groups=groups,
                version=data.get('version', '1.0')
            )
        except Exception as e:
            print(f"Error loading layout: {e}")
            return None
    
    def list_layouts(self) -> List[str]:
        """List all available layout names."""
        layouts = []
        for filepath in self.layouts_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    layouts.append(data.get('name', filepath.stem))
            except:
                layouts.append(filepath.stem)
        return sorted(layouts)
    
    def delete_layout(self, name: str) -> bool:
        """Delete a layout file."""
        try:
            filename = f"{name.replace(' ', '_').lower()}.json"
            filepath = self.layouts_dir / filename
            
            if filepath.exists():
                filepath.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting layout: {e}")
            return False
    
    def create_layout_from_patchbay(self, patchbay_view, name: str, description: str = "") -> PatchbayLayout:
        """Create a layout object from the current patchbay state."""
        from mute_solo_manager import get_mute_solo_manager
        manager = get_mute_solo_manager()
        
        blocks = []
        groups = []
        
        # Collect all blocks
        for item in patchbay_view.graphics_scene.items():
            if hasattr(item, 'ctl_name'):  # ChannelBlock
                # Get mute/solo state from global manager
                muted = manager.get_mute_state(item.ctl_name)
                soloed = manager.get_solo_state(item.ctl_name)
                
                block_layout = BlockLayout(
                    ctl_name=item.ctl_name,
                    x=item.x(),
                    y=item.y(),
                    fader_value=item.fader_value,
                    muted=muted,
                    soloed=soloed,
                    show_fader=item.show_fader,
                    channel_type=item.channel_type
                )
                blocks.append(block_layout)
            
            elif hasattr(item, 'block1') and hasattr(item, 'block2'):  # GroupWidget
                # Get mute/solo state from global manager for first block
                muted = manager.get_mute_state(item.block1.ctl_name)
                soloed = manager.get_solo_state(item.block1.ctl_name)
                
                group_layout = GroupLayout(
                    block1_name=item.block1.ctl_name,
                    block2_name=item.block2.ctl_name,
                    x=item.x(),
                    y=item.y(),
                    macro_fader_value=item.macro_fader.value(),
                    crossfader_value=item.crossfader.value(),
                    muted=muted,
                    soloed=soloed
                )
                groups.append(group_layout)
        
        return PatchbayLayout(
            name=name,
            description=description,
            blocks=blocks,
            groups=groups
        )
    
    def apply_layout_to_patchbay(self, layout: PatchbayLayout, patchbay_view) -> bool:
        """Apply a layout to the patchbay view."""
        try:
            # Clear existing groups first
            groups_to_remove = []
            for item in patchbay_view.graphics_scene.items():
                if hasattr(item, 'block1') and hasattr(item, 'block2'):
                    groups_to_remove.append(item)
            
            for group in groups_to_remove:
                group.ungroup()
            
            # Apply block positions and states
            for block_layout in layout.blocks:
                # Find the corresponding block in the scene
                for item in patchbay_view.graphics_scene.items():
                    if hasattr(item, 'ctl_name') and item.ctl_name == block_layout.ctl_name:
                        # Set position
                        item.setPos(block_layout.x, block_layout.y)
                        
                        # Set fader value
                        if hasattr(item, 'fader_value'):
                            item.fader_value = block_layout.fader_value
                            item.update_fader(skip_alsa=True)
                        
                        # Set mute/solo states using global manager
                        from mute_solo_manager import get_mute_solo_manager
                        manager = get_mute_solo_manager()
                        manager.set_mute(block_layout.ctl_name, block_layout.muted, skip_alsa=True, explicit=True)
                        manager.set_solo(block_layout.ctl_name, block_layout.soloed, skip_alsa=True, explicit=True)
                        
                        break
            
            # Create groups
            for group_layout in layout.groups:
                # Find the two blocks
                block1 = None
                block2 = None
                
                for item in patchbay_view.graphics_scene.items():
                    if hasattr(item, 'ctl_name'):
                        if item.ctl_name == group_layout.block1_name:
                            block1 = item
                        elif item.ctl_name == group_layout.block2_name:
                            block2 = item
                
                if block1 and block2:
                    # Create the group
                    patchbay_view.create_group(block1, block2)
                    
                    # Find the created group and set its properties
                    for item in patchbay_view.graphics_scene.items():
                        if (hasattr(item, 'block1') and hasattr(item, 'block2') and
                            item.block1 == block1 and item.block2 == block2):
                            
                            # Set group position
                            item.setPos(group_layout.x, group_layout.y)
                            
                            # Set fader values
                            item.macro_fader.setValue(group_layout.macro_fader_value)
                            item.crossfader.setValue(group_layout.crossfader_value)
                            
                            # Set mute/solo states using global manager
                            from mute_solo_manager import get_mute_solo_manager
                            manager = get_mute_solo_manager()
                            manager.set_mute(group_layout.block1_name, group_layout.muted, skip_alsa=True, explicit=True)
                            manager.set_solo(group_layout.block1_name, group_layout.soloed, skip_alsa=True, explicit=True)
                            manager.set_mute(group_layout.block2_name, group_layout.muted, skip_alsa=True, explicit=True)
                            manager.set_solo(group_layout.block2_name, group_layout.soloed, skip_alsa=True, explicit=True)
                            
                            break
            
            return True
        except Exception as e:
            print(f"Error applying layout: {e}")
            return False 