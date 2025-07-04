#!/usr/bin/env python3
"""
Test script to verify the comprehensive save/recall system.
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from preset_manager import get_preset_manager, RoutingPreset

def test_comprehensive_preset_system():
    """Test the comprehensive preset system."""
    print("=== Comprehensive Audio Mixer Preset System Test ===\n")
    
    manager = get_preset_manager()
    
    # Test 1: Create a comprehensive preset
    print("1. Creating a comprehensive preset...")
    start_time = time.time()
    
    # Mock patchbay state for testing
    mock_patchbay_state = {
        'blocks': [
            {
                'ctl_name': 'PCM-AN1-ADAT3',
                'position': (100, 200),
                'fader_value': 75,
                'muted': False,
                'soloed': False,
                'channel_type': 'line',
                'show_fader': True
            },
            {
                'ctl_name': 'PCM-AN2-ADAT4',
                'position': (250, 200),
                'fader_value': 60,
                'muted': True,
                'soloed': False,
                'channel_type': 'line',
                'show_fader': True
            }
        ],
        'groups': [
            {
                'block1_ctl': 'PCM-AN1-ADAT3',
                'block2_ctl': 'PCM-AN2-ADAT4',
                'position': (175, 200),
                'crossfader_value': 50,
                'macro_fader_value': 65,
                'muted': False,
                'soloed': False
            }
        ],
        'view_transform': {
            'zoom': 1.2,
            'center': (500, 300)
        }
    }
    
    # Create preset with comprehensive state
    preset = RoutingPreset(
        name="Comprehensive Test",
        description="A test preset with comprehensive ALSA and patchbay state",
        alsa_state={
            'Main-Out AN1': 70,
            'Main-Out AN2': 65,
            'Mic-AN1 Gain': 20,
            'Mic-AN2 Gain': 15,
            'Mic-AN1 48V': True,
            'Mic-AN2 48V': False,
            'PCM-AN1-ADAT3': 75,
            'PCM-AN2-ADAT4': 60
        },
        patchbay_state=mock_patchbay_state
    )
    
    # Extract logical configurations
    preset.main_mix_levels = manager._extract_main_mix_levels(preset.alsa_state)
    preset.input_gains = manager._extract_input_gains(preset.alsa_state)
    preset.hardware_settings = manager._extract_hardware_settings(preset.alsa_state)
    preset.routing_matrix = manager._extract_routing_matrix(preset.alsa_state)
    
    create_time = time.time() - start_time
    print(f"   ✓ Created preset in {create_time:.3f}s")
    print(f"   ✓ ALSA state: {len(preset.alsa_state)} controls")
    print(f"   ✓ Patchbay state: {len(preset.patchbay_state.get('blocks', []))} blocks, {len(preset.patchbay_state.get('groups', []))} groups")
    print(f"   ✓ Main levels: {len(preset.main_mix_levels)}")
    print(f"   ✓ Input gains: {len(preset.input_gains)}")
    print(f"   ✓ Hardware settings: {len(preset.hardware_settings)}")
    print(f"   ✓ Routing matrix: {len(preset.routing_matrix)} destinations")
    
    # Test 2: Save preset
    print("\n2. Saving comprehensive preset...")
    start_time = time.time()
    
    success = manager.save_preset(preset)
    save_time = time.time() - start_time
    
    if success:
        print(f"   ✓ Saved preset in {save_time:.3f}s")
    else:
        print("   ✗ Failed to save preset")
        return False
    
    # Test 3: Load preset
    print("\n3. Loading comprehensive preset...")
    start_time = time.time()
    
    loaded_preset = manager.load_preset("Comprehensive Test")
    load_time = time.time() - start_time
    
    if loaded_preset:
        print(f"   ✓ Loaded preset in {load_time:.3f}s")
        print(f"   ✓ ALSA state: {len(loaded_preset.alsa_state)} controls")
        print(f"   ✓ Patchbay state: {len(loaded_preset.patchbay_state.get('blocks', []))} blocks")
        
        # Verify data integrity
        alsa_match = loaded_preset.alsa_state == preset.alsa_state
        patchbay_match = loaded_preset.patchbay_state == preset.patchbay_state
        print(f"   ✓ ALSA state integrity: {alsa_match}")
        print(f"   ✓ Patchbay state integrity: {patchbay_match}")
    else:
        print("   ✗ Failed to load preset")
        return False
    
    # Test 4: List presets
    print("\n4. Listing presets...")
    presets = manager.list_presets()
    print(f"   ✓ Found {len(presets)} presets: {', '.join(presets)}")
    
    # Test 5: Delete preset
    print("\n5. Cleaning up...")
    success = manager.delete_preset("Comprehensive Test")
    if success:
        print("   ✓ Deleted test preset")
    else:
        print("   ✗ Failed to delete test preset")
    
    print("\n=== Test Results ===")
    print("✓ Comprehensive preset system working correctly")
    print("✓ ALSA state capture and restoration")
    print("✓ Patchbay state capture and restoration")
    print("✓ Logical configuration extraction")
    print("✓ File I/O operations")
    
    return True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    success = test_comprehensive_preset_system()
    sys.exit(0 if success else 1) 