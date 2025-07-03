#!/usr/bin/env python3
"""
Mute/Solo Manager - Global mute and solo state management
- Manages mute and solo states across all tabs and patchbay
- Provides bidirectional synchronization
- Handles ALSA control integration for mute/solo
- Implements global solo logic (mute all other channels when any is soloed)
"""

import alsaaudio
from typing import Dict, List, Set, Optional, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


@dataclass
class MuteSoloState:
    """Represents the mute/solo state of a channel."""
    muted: bool = False
    soloed: bool = False
    pre_mute_volume: int = 50  # Store volume before mute
    pre_solo_muted: bool = False  # Store mute state before solo was applied
    explicit_mute: bool = False  # True if user explicitly muted
    explicit_solo: bool = False  # True if user explicitly soloed


class MuteSoloManager(QObject):
    """Global manager for mute and solo states across all channels."""
    
    # Signals for UI updates
    mute_state_changed = pyqtSignal(str, bool)  # channel_name, muted
    solo_state_changed = pyqtSignal(str, bool)  # channel_name, soloed
    volume_changed = pyqtSignal(str, int)  # channel_name, volume
    flash_state_changed = pyqtSignal(bool)  # True when flashing should be on
    state_changed = pyqtSignal()
    
    def __init__(self, card_index: int = 1):
        super().__init__()
        self.card_index = card_index
        
        # Channel states: {channel_name: MuteSoloState}
        self.channel_states: Dict[str, MuteSoloState] = {}
        
        # ALSA mixers: {channel_name: alsaaudio.Mixer}
        self.mixers: Dict[str, alsaaudio.Mixer] = {}
        
        # Solo state tracking
        self.soloed_channels: Set[str] = set()
        self.muted_channels: Set[str] = set()
        self.any_soloed = False
        self.any_muted = False
        
        # Callbacks for UI updates
        self.ui_update_callbacks: List[Callable] = []
        
        # Flashing timer for solo visual feedback
        self.flash_timer = QTimer()
        self.flash_timer.timeout.connect(self._toggle_flash)
        self.flash_timer.setInterval(250)  # 250ms interval for faster flashing
        self.flash_on = False
        
        # Initialize with all available channels
        self._initialize_channels()
    
    def _initialize_channels(self):
        """Initialize all available ALSA channels."""
        import alsa_backend
        controls = alsa_backend.list_mixer_controls(self.card_index)
        
        for ctl_name in controls:
            try:
                mixer = alsaaudio.Mixer(control=ctl_name, cardindex=self.card_index)
                self.mixers[ctl_name] = mixer
                
                # Get initial volume
                try:
                    initial_volume = mixer.getvolume()[0]
                except:
                    initial_volume = 50
                
                # Initialize state
                self.channel_states[ctl_name] = MuteSoloState(
                    muted=False,
                    soloed=False,
                    pre_mute_volume=initial_volume,
                    pre_solo_muted=False
                )
                
            except Exception as e:
                print(f"[WARNING] Failed to initialize mixer for {ctl_name}: {e}")
    
    def register_ui_callback(self, callback: Callable):
        """Register a callback for UI updates."""
        self.ui_update_callbacks.append(callback)
    
    def _notify_ui_update(self):
        """Notify all registered UI callbacks of state changes."""
        for callback in self.ui_update_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"[ERROR] UI callback failed: {e}")
    
    def set_mute(self, channel_name: str, muted: bool, skip_alsa: bool = False, explicit: bool = True, batch: bool = False):
        """Set mute state for a channel. If batch=True, do not emit state_changed; caller must emit after batch."""
        if channel_name not in self.channel_states:
            print(f"[WARNING] Channel {channel_name} not found in mute/solo manager")
            return
        state = self.channel_states[channel_name]
        if state.muted == muted and state.explicit_mute == explicit:
            return  # No change
        if muted:
            if channel_name in self.mixers:
                try:
                    current_volume = self.mixers[channel_name].getvolume()[0]
                    state.pre_mute_volume = current_volume
                    if not skip_alsa:
                        self.mixers[channel_name].setvolume(0)
                except Exception as e:
                    print(f"[ERROR] Failed to mute {channel_name}: {e}")
            state.muted = True
            self.muted_channels.add(channel_name)
            if explicit:
                state.explicit_mute = True
        else:
            if channel_name in self.mixers:
                try:
                    if not skip_alsa:
                        self.mixers[channel_name].setvolume(state.pre_mute_volume)
                except Exception as e:
                    print(f"[ERROR] Failed to unmute {channel_name}: {e}")
            state.muted = False
            self.muted_channels.discard(channel_name)
            if explicit:
                state.explicit_mute = False
        self.any_muted = len(self.muted_channels) > 0
        if (self.any_soloed or self.any_muted) and not self.flash_timer.isActive():
            self.flash_timer.start()
        elif not self.any_soloed and not self.any_muted and self.flash_timer.isActive():
            self.flash_timer.stop()
            self.flash_on = False
            self.flash_state_changed.emit(False)
        if not self.any_soloed:
            state.pre_solo_muted = state.muted
        # Always emit per-channel signal for UI responsiveness
        self.mute_state_changed.emit(channel_name, muted)
        self.volume_changed.emit(channel_name, state.pre_mute_volume if not muted else 0)
        self._notify_ui_update()
        if not batch:
            self.state_changed.emit()
    
    def set_solo(self, channel_name: str, soloed: bool, skip_alsa: bool = False, explicit: bool = True, batch: bool = False):
        """Set solo state for a channel. If batch=True, do not emit state_changed; caller must emit after batch."""
        if channel_name not in self.channel_states:
            print(f"[WARNING] Channel {channel_name} not found in mute/solo manager")
            return
        state = self.channel_states[channel_name]
        if state.soloed == soloed and state.explicit_solo == explicit:
            return  # No change
        if soloed:
            if not self.any_soloed:
                for ch_name, ch_state in self.channel_states.items():
                    ch_state.pre_solo_muted = ch_state.muted
            self.soloed_channels.add(channel_name)
            state.soloed = True
            if explicit:
                state.explicit_solo = True
        else:
            self.soloed_channels.discard(channel_name)
            state.soloed = False
            if explicit:
                state.explicit_solo = False
        self.any_soloed = len(self.soloed_channels) > 0
        # Always emit per-channel signal for UI responsiveness
        self.solo_state_changed.emit(channel_name, soloed)
        self._apply_solo_logic(skip_alsa, batch=True)
        if (self.any_soloed or self.any_muted) and not self.flash_timer.isActive():
            self.flash_timer.start()
        elif not self.any_soloed and not self.any_muted and self.flash_timer.isActive():
            self.flash_timer.stop()
            self.flash_on = False
            self.flash_state_changed.emit(False)
        self._notify_ui_update()
        if not batch:
            self.state_changed.emit()
    
    def _toggle_flash(self):
        """Toggle the flash state for solo visual feedback."""
        self.flash_on = not self.flash_on
        self.flash_state_changed.emit(self.flash_on)
    
    def _apply_solo_logic(self, skip_alsa: bool = False, batch: bool = False):
        """Apply global solo logic: mute all non-soloed input channels when any are soloed. If batch=True, only emit state_changed once after all changes."""
        for channel_name, state in self.channel_states.items():
            is_main_output = channel_name.startswith("Main-Out")
            if self.any_soloed:
                if is_main_output:
                    should_be_muted = state.muted
                else:
                    should_be_muted = not state.soloed
            else:
                should_be_muted = state.pre_solo_muted
            self.set_mute(channel_name, should_be_muted, skip_alsa, explicit=False, batch=True)
        if batch:
            self.state_changed.emit()
    
    def get_mute_state(self, channel_name: str) -> bool:
        """Get mute state for a channel."""
        return self.channel_states.get(channel_name, MuteSoloState()).muted
    
    def get_solo_state(self, channel_name: str) -> bool:
        """Get solo state for a channel."""
        return self.channel_states.get(channel_name, MuteSoloState()).soloed
    
    def get_effective_mute_state(self, channel_name: str) -> bool:
        """Get effective mute state (considering solo logic)."""
        # Check if this is a main output channel
        is_main_output = channel_name.startswith("Main-Out")
        
        if self.any_soloed and not is_main_output:
            # For input channels: mute if not soloed
            return not self.get_solo_state(channel_name)
        else:
            # For main outputs or when no solo: use actual mute state
            return self.get_mute_state(channel_name)
    
    def get_pre_mute_volume(self, channel_name: str) -> int:
        """Get the volume that was stored before muting."""
        return self.channel_states.get(channel_name, MuteSoloState()).pre_mute_volume
    
    def update_volume(self, channel_name: str, volume: int, skip_alsa: bool = False):
        """Update volume for a channel (updates pre_mute_volume if muted)."""
        if channel_name not in self.channel_states:
            return
        
        state = self.channel_states[channel_name]
        
        if state.muted:
            # If muted, just update the stored volume
            state.pre_mute_volume = volume
        else:
            # If not muted, update ALSA
            if channel_name in self.mixers and not skip_alsa:
                try:
                    self.mixers[channel_name].setvolume(volume)
                except Exception as e:
                    print(f"[ERROR] Failed to update volume for {channel_name}: {e}")
        
        # Emit signal
        self.volume_changed.emit(channel_name, volume)
    
    def clear_all_solo(self):
        """Clear all solo states."""
        soloed_channels = list(self.soloed_channels)
        for channel_name in soloed_channels:
            self.set_solo(channel_name, False)
    
    def get_all_states(self) -> Dict[str, MuteSoloState]:
        """Get all channel states for saving/loading."""
        return self.channel_states.copy()
    
    def set_all_states(self, states: Dict[str, MuteSoloState]):
        """Set all channel states for loading."""
        for channel_name, state in states.items():
            if channel_name in self.channel_states:
                self.channel_states[channel_name] = state
                # Update UI
                self.mute_state_changed.emit(channel_name, state.muted)
                self.solo_state_changed.emit(channel_name, state.soloed)
        
        # Reapply solo logic
        self._apply_solo_logic(skip_alsa=True)
        
        # Update UI
        self._notify_ui_update()


# Global instance
_mute_solo_manager: Optional[MuteSoloManager] = None

def get_mute_solo_manager(card_index: int = 1) -> MuteSoloManager:
    """Get the global mute/solo manager instance."""
    global _mute_solo_manager
    if _mute_solo_manager is None:
        _mute_solo_manager = MuteSoloManager(card_index)
    return _mute_solo_manager 