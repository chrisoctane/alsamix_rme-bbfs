#!/usr/bin/env python3
"""
Professional Audio Mixer Preset Manager
- Saves/loads routing matrices, main mix levels, ALSA state, and patchbay state
- Uses logical configurations instead of UI widget positions
- Fast, efficient, and professional approach
"""

import json
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import alsa_backend


@dataclass
class RoutingPreset:
    """Represents a professional audio mixer preset."""
    name: str
    description: str
    version: str = "2.0"
    
    # Main mix levels (like real mixers)
    main_mix_levels: Dict[str, int] = None
    input_gains: Dict[str, int] = None
    mute_states: Dict[str, bool] = None
    solo_states: Dict[str, bool] = None
    hardware_settings: Dict[str, Any] = None
    routing_matrix: Dict[str, Dict[str, int]] = None
    
    # Complete state capture
    alsa_state: Dict[str, int] = None  # All ALSA control values
    patchbay_state: Dict = None  # Complete patchbay state (positions, groups, faders, etc.)
    
    def __post_init__(self):
        """Initialize default values."""
        if self.main_mix_levels is None:
            self.main_mix_levels = {}
        if self.input_gains is None:
            self.input_gains = {}
        if self.mute_states is None:
            self.mute_states = {}
        if self.solo_states is None:
            self.solo_states = {}
        if self.hardware_settings is None:
            self.hardware_settings = {}
        if self.routing_matrix is None:
            self.routing_matrix = {}
        if self.alsa_state is None:
            self.alsa_state = {}
        if self.patchbay_state is None:
            self.patchbay_state = {}


class PresetManager:
    """Manages professional audio mixer presets."""
    
    def __init__(self, preset_dir: str = "presets"):
        self.preset_dir = Path(preset_dir)
        self.preset_dir.mkdir(exist_ok=True)
    
    def create_preset_from_current_state(self, name: str, description: str = "", patchbay_widget=None) -> RoutingPreset:
        """Create a preset from the current system state."""
        print(f"[INFO] Creating preset from current state: {name}")
        
        # Get ALSA state
        alsa_state = self._capture_alsa_state()
        
        # Get patchbay state
        patchbay_state = {}
        if patchbay_widget and hasattr(patchbay_widget, 'serialize_state'):
            patchbay_state = patchbay_widget.serialize_state()
        
        # Create preset with comprehensive state
        preset = RoutingPreset(
            name=name,
            description=description,
            alsa_state=alsa_state,
            patchbay_state=patchbay_state
        )
        
        # Extract logical configurations from ALSA state
        preset.main_mix_levels = self._extract_main_mix_levels(alsa_state)
        preset.input_gains = self._extract_input_gains(alsa_state)
        preset.hardware_settings = self._extract_hardware_settings(alsa_state)
        preset.routing_matrix = self._extract_routing_matrix(alsa_state)
        
        print(f"[INFO] Created preset with {len(preset.main_mix_levels)} main levels, {len(preset.input_gains)} input gains")
        print(f"[INFO] ALSA state: {len(alsa_state)} controls, Patchbay state: {len(patchbay_state)} items")
        
        return preset
    
    def _capture_alsa_state(self) -> Dict[str, int]:
        """Capture all ALSA control values."""
        alsa_state = {}
        try:
            controls = alsa_backend.list_mixer_controls()
            for control in controls:
                try:
                    value = alsa_backend.get_volume(control)
                    alsa_state[control] = value
                except Exception as e:
                    print(f"[WARNING] Failed to get value for {control}: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to capture ALSA state: {e}")
        return alsa_state
    
    def _extract_main_mix_levels(self, alsa_state: Dict[str, int]) -> Dict[str, int]:
        """Extract main mix levels from ALSA state."""
        main_levels = {}
        for control, value in alsa_state.items():
            if control.startswith('Main-Out '):
                main_levels[control] = value
        return main_levels
    
    def _extract_input_gains(self, alsa_state: Dict[str, int]) -> Dict[str, int]:
        """Extract input gains from ALSA state."""
        input_gains = {}
        for control, value in alsa_state.items():
            if 'Gain' in control and ('Mic-' in control or 'Line-' in control):
                input_gains[control] = value
        return input_gains
    
    def _extract_hardware_settings(self, alsa_state: Dict[str, int]) -> Dict[str, Any]:
        """Extract hardware settings from ALSA state."""
        hardware_settings = {}
        for control, value in alsa_state.items():
            if any(keyword in control for keyword in ['48V', 'PAD', 'IEC958', 'Sample Clock']):
                hardware_settings[control] = value
        return hardware_settings
    
    def _extract_routing_matrix(self, alsa_state: Dict[str, int]) -> Dict[str, Dict[str, int]]:
        """Extract routing matrix from ALSA state."""
        routing_matrix = {}
        for control, value in alsa_state.items():
            if '-' in control and not control.startswith('Main-Out'):
                # Parse routing control (e.g., "PCM-AN1-ADAT3")
                parts = control.split('-')
                if len(parts) >= 3:
                    source = f"{parts[0]}-{parts[1]}"
                    destination = parts[2]
                    if source not in routing_matrix:
                        routing_matrix[source] = {}
                    routing_matrix[source][destination] = value
        return routing_matrix
    
    def apply_preset(self, preset: RoutingPreset, progress_callback: Optional[Callable] = None, patchbay_widget=None) -> bool:
        """Apply a preset to the system."""
        print(f"[INFO] Applying preset: {preset.name}")
        
        try:
            # Apply ALSA state
            if preset.alsa_state:
                self._apply_alsa_state(preset.alsa_state, progress_callback)
            
            # Apply patchbay state
            if preset.patchbay_state and patchbay_widget and hasattr(patchbay_widget, 'deserialize_state'):
                patchbay_widget.deserialize_state(preset.patchbay_state)
            
            print(f"[INFO] Successfully applied preset: {preset.name}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to apply preset {preset.name}: {e}")
            return False
    
    def _apply_alsa_state(self, alsa_state: Dict[str, int], progress_callback: Optional[Callable] = None):
        """Apply ALSA state to the system."""
        total_controls = len(alsa_state)
        current = 0
        
        for control, value in alsa_state.items():
            try:
                alsa_backend.set_volume(control, value)
                current += 1
                if progress_callback:
                    progress_callback(current, total_controls, f"Applying {control}")
            except Exception as e:
                print(f"[WARNING] Failed to set {control} to {value}: {e}")
    
    def save_preset(self, preset: RoutingPreset) -> bool:
        """Save a preset to disk."""
        try:
            preset_path = self.preset_dir / f"{preset.name}.json"
            with open(preset_path, 'w') as f:
                json.dump(asdict(preset), f, indent=2)
            print(f"[INFO] Saved preset: {preset.name}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save preset {preset.name}: {e}")
            return False
    
    def load_preset(self, name: str) -> Optional[RoutingPreset]:
        """Load a preset from disk."""
        try:
            preset_path = self.preset_dir / f"{name}.json"
            if not preset_path.exists():
                return None
            
            with open(preset_path, 'r') as f:
                data = json.load(f)
            
            # Handle version compatibility
            if data.get('version') == '1.0':
                # Convert old format to new format
                preset = RoutingPreset(
                    name=data['name'],
                    description=data.get('description', ''),
                    main_mix_levels=data.get('main_mix_levels', {}),
                    input_gains=data.get('input_gains', {}),
                    hardware_settings=data.get('hardware_settings', {}),
                    routing_matrix=data.get('routing_matrix', {}),
                    alsa_state={},  # Will be reconstructed from other fields
                    patchbay_state={}  # Will be empty for old presets
                )
            else:
                # New format
                preset = RoutingPreset(**data)
            
            return preset
        except Exception as e:
            print(f"[ERROR] Failed to load preset {name}: {e}")
            return None
    
    def list_presets(self) -> List[str]:
        """List all available presets."""
        presets = []
        for preset_file in self.preset_dir.glob("*.json"):
            presets.append(preset_file.stem)
        return sorted(presets)
    
    def delete_preset(self, name: str) -> bool:
        """Delete a preset."""
        try:
            preset_path = self.preset_dir / f"{name}.json"
            if preset_path.exists():
                preset_path.unlink()
                print(f"[INFO] Deleted preset: {name}")
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Failed to delete preset {name}: {e}")
            return False
    
    def create_default_presets(self):
        """Create default presets for new installations."""
        default_presets = [
            ("Default", "Default system configuration"),
            ("Live Performance", "Optimized for live performance"),
            ("Studio Recording", "Optimized for studio recording"),
        ]
        
        for name, description in default_presets:
            preset = RoutingPreset(name=name, description=description)
            self.save_preset(preset)


# Global instance
_preset_manager = None

def get_preset_manager() -> PresetManager:
    """Get the global preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager 