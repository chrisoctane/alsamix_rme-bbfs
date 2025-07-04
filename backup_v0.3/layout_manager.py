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
    
    def get_current_layout_name(self, patchbay_view) -> Optional[str]:
        """Get the name of the currently loaded layout in the patchbay view."""
        # Check if the patchbay view has a current_layout_name attribute
        if hasattr(patchbay_view, 'current_layout_name'):
            return patchbay_view.current_layout_name
        # If it's a PatchbayWidget, check its patchbay_view
        elif hasattr(patchbay_view, 'patchbay_view') and hasattr(patchbay_view.patchbay_view, 'current_layout_name'):
            return patchbay_view.patchbay_view.current_layout_name
        return "default"  # Default fallback
    
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
    
    def apply_layout_to_patchbay(self, layout: PatchbayLayout, patchbay_view, progress_callback=None) -> bool:
        """Apply a layout to the patchbay view."""
        try:
            print(f"[DEBUG] Starting to apply layout: {layout.name}")
            
            if progress_callback:
                progress_callback(5)  # 5% - Starting
            
            # Temporarily disable UI updates for faster processing
            patchbay_view.setUpdatesEnabled(False)
            patchbay_view.graphics_scene.setSceneRect(patchbay_view.graphics_scene.sceneRect())
            
            # Clear existing groups first
            print("[DEBUG] Clearing existing groups...")
            groups_to_remove = []
            for item in patchbay_view.graphics_scene.items():
                if hasattr(item, 'block1') and hasattr(item, 'block2'):
                    groups_to_remove.append(item)
            
            for group in groups_to_remove:
                try:
                    group.ungroup()
                except Exception as e:
                    print(f"[WARNING] Failed to ungroup: {e}")
            
            if progress_callback:
                progress_callback(10)  # 10% - Groups cleared
            
            # Create a lookup dictionary for blocks to avoid O(n²) search
            print("[DEBUG] Creating block lookup dictionary...")
            block_lookup = {}
            for item in patchbay_view.graphics_scene.items():
                if hasattr(item, 'ctl_name'):
                    block_lookup[item.ctl_name] = item
            
            print(f"[DEBUG] Found {len(block_lookup)} blocks in scene")
            print(f"[DEBUG] Applying {len(layout.blocks)} blocks...")
            
            if progress_callback:
                progress_callback(15)  # 15% - Lookup created
            
            # Batch all mute/solo operations
            from mute_solo_manager import get_mute_solo_manager
            manager = get_mute_solo_manager()
            
            # Prepare all changes in batches to minimize UI updates
            block_positions = []
            fader_updates = []
            mute_states = []
            solo_states = []
            
            # Collect all changes first (no UI updates yet)
            blocks_processed = 0
            for i, block_layout in enumerate(layout.blocks):
                if i % 100 == 0:  # Progress update every 100 blocks
                    print(f"[DEBUG] Progress: {i}/{len(layout.blocks)} blocks processed")
                    if progress_callback:
                        # Progress from 15% to 60% for blocks
                        progress_value = 15 + int((i / len(layout.blocks)) * 45)
                        progress_callback(progress_value)
                
                # Use lookup dictionary instead of searching
                item = block_lookup.get(block_layout.ctl_name)
                if item:
                    # Collect position changes
                    block_positions.append((item, block_layout.x, block_layout.y))
                    
                    # Collect fader changes
                    if hasattr(item, 'fader_value'):
                        fader_updates.append((item, block_layout.fader_value))
                    
                    # Collect mute/solo states
                    mute_states.append((block_layout.ctl_name, block_layout.muted))
                    solo_states.append((block_layout.ctl_name, block_layout.soloed))
                    
                    blocks_processed += 1
                else:
                    # Only warn about missing blocks if there are few of them
                    if len(layout.blocks) < 50 or i < 10:
                        print(f"[WARNING] Block {block_layout.ctl_name} not found in scene")
            
            print(f"[DEBUG] Successfully processed {blocks_processed}/{len(layout.blocks)} blocks")
            
            if progress_callback:
                progress_callback(60)  # 60% - Data collected
            
            # Apply all position changes at once
            print("[DEBUG] Applying positions...")
            for item, x, y in block_positions:
                item.setPos(x, y)
            
            if progress_callback:
                progress_callback(65)  # 65% - Positions applied
            
            # Apply all fader changes at once
            print("[DEBUG] Applying fader values...")
            for item, fader_value in fader_updates:
                item.fader_value = fader_value
                item.update_fader(skip_alsa=True)
            
            if progress_callback:
                progress_callback(70)  # 70% - Faders applied
            
            # Apply all mute/solo states at once (batch mode)
            print("[DEBUG] Applying mute/solo states...")
            for ctl_name, muted in mute_states:
                manager.set_mute(ctl_name, muted, skip_alsa=True, explicit=True, batch=True)
            
            for ctl_name, soloed in solo_states:
                manager.set_solo(ctl_name, soloed, skip_alsa=True, explicit=True, batch=True)
            
            # Single state change emission for all blocks
            manager.state_changed.emit()
            
            if progress_callback:
                progress_callback(75)  # 75% - States applied
            
            if layout.groups:
                print(f"[DEBUG] Creating {len(layout.groups)} groups...")
                
                if progress_callback:
                    progress_callback(80)  # 80% - Starting groups
                
                # Create groups
                groups_processed = 0
                for i, group_layout in enumerate(layout.groups):
                    if progress_callback:
                        # Progress from 80% to 90% for groups
                        progress_value = 80 + int((i / len(layout.groups)) * 10)
                        progress_callback(progress_value)
                    
                    # Use lookup dictionary to find blocks
                    block1 = block_lookup.get(group_layout.block1_name)
                    block2 = block_lookup.get(group_layout.block2_name)
                    
                    if block1 and block2:
                        try:
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
                                    
                                    # Set mute/solo states using global manager (batch mode)
                                    manager.set_mute(group_layout.block1_name, group_layout.muted, skip_alsa=True, explicit=True, batch=True)
                                    manager.set_solo(group_layout.block1_name, group_layout.soloed, skip_alsa=True, explicit=True, batch=True)
                                    manager.set_mute(group_layout.block2_name, group_layout.muted, skip_alsa=True, explicit=True, batch=True)
                                    manager.set_solo(group_layout.block2_name, group_layout.soloed, skip_alsa=True, explicit=True, batch=True)
                                    
                                    groups_processed += 1
                                    break
                        except Exception as e:
                            print(f"[ERROR] Failed to create group for {group_layout.block1_name} + {group_layout.block2_name}: {e}")
                            continue
                    else:
                        print(f"[WARNING] Could not find blocks for group: {group_layout.block1_name} and/or {group_layout.block2_name}")
                
                print(f"[DEBUG] Successfully processed {groups_processed}/{len(layout.groups)} groups")
                
                if progress_callback:
                    progress_callback(90)  # 90% - Groups completed
            
            # Final state change emission
            manager.state_changed.emit()
            
            if progress_callback:
                progress_callback(95)  # 95% - Final state changes
            
            # Re-enable UI updates
            patchbay_view.setUpdatesEnabled(True)
            
            # Set the current layout name
            if hasattr(patchbay_view, 'current_layout_name'):
                patchbay_view.current_layout_name = layout.name
            elif hasattr(patchbay_view, 'patchbay_view') and hasattr(patchbay_view.patchbay_view, 'current_layout_name'):
                patchbay_view.patchbay_view.current_layout_name = layout.name
            
            print(f"[DEBUG] Layout {layout.name} applied successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error applying layout: {e}")
            import traceback
            traceback.print_exc()
            # Make sure to re-enable UI updates even on error
            try:
                patchbay_view.setUpdatesEnabled(True)
            except:
                pass
            return False


def get_layout_manager() -> LayoutManager:
    """Get the global layout manager instance."""
    if not hasattr(get_layout_manager, '_instance'):
        get_layout_manager._instance = LayoutManager()
    return get_layout_manager._instance 